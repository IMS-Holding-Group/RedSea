/* خريطة انزلاقية مبنية يدوياً: بلاطات OpenStreetMap + طبقة SVG للمناطق واليخوت، مع بديل دون اتصال */
const RYMap = (() => {
  const TILE = 256;
  const NS = 'http://www.w3.org/2000/svg';
  const MIN_Z = 5;
  const MAX_Z = 17;
  const ZONE_STYLE = { no_anchor: ['#C8102E', 0.3], protected: ['#1E7F4F', 0.25], restricted: ['#B7791F', 0.3], cruising_area: ['#1F5FA8', 0.08] };
  let coastline = null;

  /* إسقاط Web Mercator: يحول خط العرض والطول إلى إحداثيات بكسل عالمية عند مستوى تكبير معين */
  function project(lat, lng, z) {
    const size = TILE * Math.pow(2, z);
    const rad = (lat * Math.PI) / 180;
    return [((lng + 180) / 360) * size, ((1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI) / 2) * size];
  }
  function unproject(x, y, z) {
    const size = TILE * Math.pow(2, z);
    const n = Math.PI - (2 * Math.PI * y) / size;
    return [(180 / Math.PI) * Math.atan(Math.sinh(n)), (x / size) * 360 - 180];
  }
  function svgEl(tag, attrs) {
    const n = document.createElementNS(NS, tag);
    Object.entries(attrs || {}).forEach(([k, v]) => { n.setAttribute(k, v); });
    return n;
  }

  function create(container, opts) {
    const o = Object.assign({ center: [21.73, 39.05], zoom: 12 }, opts || {});
    const state = { center: o.center.slice(), zoom: o.zoom, layers: { zones: [], yachts: [], trail: [], draft: [], points: [] } };
    let tileErrors = 0;
    let tileLoads = 0;
    const tiles = UI.el('div', { class: 'map-tiles' });
    const svg = svgEl('svg', { class: 'map-svg' });
    const tip = UI.el('div', { class: 'map-tip hidden' });
    const status = UI.el('div', { class: 'map-status hidden' });
    const zoomBtn = (text, d) => UI.el('button', { type: 'button', 'aria-label': d > 0 ? 'تكبير' : 'تصغير', text, onclick: () => { setZoom(state.zoom + d); } });
    const controls = UI.el('div', { class: 'map-controls' }, zoomBtn('+', 1), zoomBtn('-', -1));
    const attrib = UI.el('div', { class: 'map-attrib', text: 'بيانات الخريطة من مساهمي OpenStreetMap' });
    container.classList.add('map');
    container.replaceChildren(tiles, svg, controls, status, attrib, tip);
    const cache = new Map();

    const size = () => [container.clientWidth || 600, container.clientHeight || 400];
    function toScreen(lat, lng) {
      const [w, h] = size();
      const [cx, cy] = project(state.center[0], state.center[1], state.zoom);
      const [x, y] = project(lat, lng, state.zoom);
      return [x - cx + w / 2, y - cy + h / 2];
    }
    function toLatLng(sx, sy) {
      const [w, h] = size();
      const [cx, cy] = project(state.center[0], state.center[1], state.zoom);
      return unproject(cx + sx - w / 2, cy + sy - h / 2, state.zoom);
    }
    function setOffline(flag) {
      container.classList.toggle('offline', flag);
      status.textContent = flag ? 'تعذر تحميل الخريطة، يعرض خط الساحل التقريبي' : '';
      status.classList.toggle('hidden', !flag);
      if (flag && !coastline) {
        fetch('/assets/data/coastline.json').then((r) => r.json()).then((d) => {
          coastline = d;
          drawOverlay();
        }).catch(() => { coastline = []; });
      }
    }
    function drawTiles() {
      const [w, h] = size();
      const z = state.zoom;
      const [cx, cy] = project(state.center[0], state.center[1], z);
      const left = cx - w / 2;
      const top = cy - h / 2;
      const max = Math.pow(2, z);
      const needed = new Set();
      for (let tx = Math.floor(left / TILE); tx <= Math.floor((left + w) / TILE); tx += 1) {
        for (let ty = Math.floor(top / TILE); ty <= Math.floor((top + h) / TILE); ty += 1) {
          if (ty < 0 || ty >= max || tx < 0 || tx >= max) { continue; }
          const key = `${z}/${tx}/${ty}`;
          needed.add(key);
          let img = cache.get(key);
          if (!img) {
            img = UI.el('img', { alt: '', draggable: 'false', src: `https://tile.openstreetmap.org/${key}.png` });
            img.addEventListener('load', () => {
              tileLoads += 1;
              if (container.classList.contains('offline')) { setOffline(false); }
            });
            img.addEventListener('error', () => {
              tileErrors += 1;
              if (tileLoads === 0 && tileErrors >= 2) { setOffline(true); }
            });
            cache.set(key, img);
            tiles.appendChild(img);
          }
          img.style.left = `${tx * TILE - left}px`;
          img.style.top = `${ty * TILE - top}px`;
        }
      }
      cache.forEach((img, key) => {
        if (!needed.has(key)) {
          img.remove();
          cache.delete(key);
        }
      });
    }
    function pathFor(points, close) {
      return points.map((p, i) => {
        const [x, y] = toScreen(p[0], p[1]);
        return `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`;
      }).join(' ') + (close ? ' Z' : '');
    }
    function showTip(evt, lines) {
      tip.replaceChildren(...lines.map((l, i) => UI.el(i ? 'div' : 'strong', { text: l })));
      const r = container.getBoundingClientRect();
      tip.style.left = `${Math.min(evt.clientX - r.left + 12, r.width - 270)}px`;
      tip.style.top = `${evt.clientY - r.top + 12}px`;
      tip.classList.remove('hidden');
    }
    const hideTip = () => { tip.classList.add('hidden'); };
    function drawOverlay() {
      const [w, h] = size();
      svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
      svg.replaceChildren();
      if (container.classList.contains('offline') && coastline && coastline.length) {
        svg.appendChild(svgEl('path', { d: pathFor(coastline, false), fill: 'none', stroke: '#6B7C5A', 'stroke-width': 3 }));
      }
      state.layers.zones.forEach((z) => {
        const [color, alpha] = ZONE_STYLE[z.zone_type] || ['#555555', 0.2];
        const p = svgEl('path', { d: pathFor(z.polygon, true), fill: color, 'fill-opacity': alpha, stroke: color, 'stroke-width': 2, 'stroke-dasharray': z.zone_type === 'cruising_area' ? '6 4' : '' });
        p.addEventListener('mousemove', (e) => { showTip(e, [z.name, UI.TEXT.zone[z.zone_type], z.description || '']); });
        p.addEventListener('mouseleave', hideTip);
        svg.appendChild(p);
      });
      if (state.layers.trail.length > 1) {
        svg.appendChild(svgEl('path', { d: pathFor(state.layers.trail, false), fill: 'none', stroke: '#C8102E', 'stroke-width': 3, 'stroke-opacity': 0.8 }));
      }
      if (state.layers.draft.length) {
        svg.appendChild(svgEl('path', { d: pathFor(state.layers.draft, state.layers.draft.length > 2), fill: '#C8102E', 'fill-opacity': 0.15, stroke: '#C8102E', 'stroke-width': 2 }));
        state.layers.draft.forEach((p) => {
          const [x, y] = toScreen(p[0], p[1]);
          svg.appendChild(svgEl('circle', { cx: x, cy: y, r: 5, fill: '#FFFFFF', stroke: '#C8102E', 'stroke-width': 2 }));
        });
      }
      state.layers.points.forEach((p) => {
        const [x, y] = toScreen(p.lat, p.lng);
        const g = svgEl('g', { transform: `translate(${x.toFixed(1)},${y.toFixed(1)})` });
        g.appendChild(svgEl('circle', { r: 8, fill: p.color || '#0B2545', stroke: '#FFFFFF', 'stroke-width': 2 }));
        g.addEventListener('mousemove', (e) => { showTip(e, p.tip || [p.label || '']); });
        g.addEventListener('mouseleave', hideTip);
        svg.appendChild(g);
      });
      state.layers.yachts.forEach((y) => {
        const [x, sy] = toScreen(y.lat, y.lng);
        const alert = y.alerts && y.alerts.length;
        const fill = y.stale ? '#8A94A3' : (alert ? '#C8102E' : '#0B2545');
        const g = svgEl('g', { transform: `translate(${x.toFixed(1)},${sy.toFixed(1)})`, class: 'yacht-marker' });
        if (alert) { g.appendChild(svgEl('circle', { r: 17, fill: '#C8102E', 'fill-opacity': 0.18 })); }
        const boat = svgEl('path', { d: 'M0,-13 L7,6 L0,2 L-7,6 Z', fill, stroke: '#FFFFFF', 'stroke-width': 1.5, transform: `rotate(${y.heading || 0})` });
        g.appendChild(boat);
        const label = svgEl('text', { x: 0, y: 24, 'text-anchor': 'middle', 'font-size': 13, 'font-weight': 600, fill: '#0B2545', stroke: '#FFFFFF', 'stroke-width': 3, 'paint-order': 'stroke', 'font-family': 'IBM Plex Sans Arabic, Tahoma, sans-serif' });
        label.textContent = y.name;
        g.appendChild(label);
        g.addEventListener('mousemove', (e) => { showTip(e, y.tip || [y.name]); });
        g.addEventListener('mouseleave', hideTip);
        if (o.onYachtClick) { g.addEventListener('click', () => { o.onYachtClick(y); }); }
        svg.appendChild(g);
      });
    }
    function render() {
      drawTiles();
      drawOverlay();
    }
    function setZoom(z) {
      state.zoom = Math.max(MIN_Z, Math.min(MAX_Z, z));
      render();
    }

    /* السحب والنقر */
    let drag = null;
    container.addEventListener('pointerdown', (e) => {
      if (e.target.closest('.map-controls')) { return; }
      drag = { x: e.clientX, y: e.clientY, center: project(state.center[0], state.center[1], state.zoom), moved: false };
      container.setPointerCapture(e.pointerId);
    });
    container.addEventListener('pointermove', (e) => {
      if (!drag) { return; }
      const dx = e.clientX - drag.x;
      const dy = e.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 4) {
        drag.moved = true;
        container.classList.add('dragging');
        hideTip();
      }
      if (drag.moved) {
        state.center = unproject(drag.center[0] - dx, drag.center[1] - dy, state.zoom);
        render();
      }
    });
    container.addEventListener('pointerup', (e) => {
      if (drag && !drag.moved && o.onClick && !e.target.closest('.map-controls')) {
        const r = container.getBoundingClientRect();
        o.onClick(toLatLng(e.clientX - r.left, e.clientY - r.top));
      }
      drag = null;
      container.classList.remove('dragging');
    });
    container.addEventListener('wheel', (e) => {
      e.preventDefault();
      setZoom(state.zoom + (e.deltaY < 0 ? 1 : -1));
    }, { passive: false });
    window.addEventListener('resize', render);

    function fit(points) {
      if (!points.length) { return; }
      const lats = points.map((p) => p[0]);
      const lngs = points.map((p) => p[1]);
      state.center = [(Math.min(...lats) + Math.max(...lats)) / 2, (Math.min(...lngs) + Math.max(...lngs)) / 2];
      const [w, h] = size();
      let z = MAX_Z;
      while (z > MIN_Z) {
        const a = project(Math.max(...lats), Math.min(...lngs), z);
        const b = project(Math.min(...lats), Math.max(...lngs), z);
        if (b[0] - a[0] < w * 0.8 && b[1] - a[1] < h * 0.8) { break; }
        z -= 1;
      }
      state.zoom = Math.min(z, 14);
      render();
    }
    requestAnimationFrame(render);
    return {
      set(layer, data) {
        state.layers[layer] = data || [];
        drawOverlay();
      },
      get: (layer) => state.layers[layer],
      center(lat, lng, z) {
        state.center = [lat, lng];
        if (z) { state.zoom = z; }
        render();
      },
      fit,
      render
    };
  }
  return { create, ZONE_STYLE };
})();
