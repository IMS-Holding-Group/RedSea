/* رسوم بيانية بسيطة مبنية يدوياً بـ SVG */
const Charts = (() => {
  const NS = 'http://www.w3.org/2000/svg';
  const W = 640;
  const H = 240;
  const PAD = { top: 16, right: 16, bottom: 34, left: 56 };
  function svgEl(tag, attrs) {
    const n = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([k, v]) => { n.setAttribute(k, v); });
    return n;
  }
  function frame(max, unit) {
    const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img' });
    const innerH = H - PAD.top - PAD.bottom;
    for (let i = 0; i <= 4; i += 1) {
      const y = PAD.top + innerH - (innerH * i) / 4;
      svg.appendChild(svgEl('line', { x1: PAD.left, x2: W - PAD.right, y1: y, y2: y, stroke: '#D9E1EA', 'stroke-width': 1 }));
      const t = svgEl('text', { x: PAD.left - 8, y: y + 4, 'text-anchor': 'end' });
      t.textContent = UI.num(Math.round((max * i) / 4)) + (unit || '');
      svg.appendChild(t);
    }
    return svg;
  }
  function niceMax(values) {
    const m = Math.max(1, ...values);
    const p = Math.pow(10, Math.floor(Math.log10(m)));
    return Math.ceil(m / p) * p;
  }
  function label(svg, x, text) {
    const t = svgEl('text', { x, y: H - 10, 'text-anchor': 'middle' });
    t.textContent = text;
    svg.appendChild(t);
  }
  function bar(container, data, unit) {
    const max = niceMax(data.map((d) => d.value));
    const svg = frame(max, unit);
    const innerW = W - PAD.left - PAD.right;
    const innerH = H - PAD.top - PAD.bottom;
    const step = innerW / data.length;
    data.forEach((d, i) => {
      const h = (d.value / max) * innerH;
      const x = PAD.left + i * step + step * 0.2;
      const rect = svgEl('rect', { x, y: PAD.top + innerH - h, width: step * 0.6, height: Math.max(h, 1), rx: 4, fill: '#13315C' });
      const title = svgEl('title', {});
      title.textContent = `${d.label}: ${UI.num(d.value)}${unit || ''}`;
      rect.appendChild(title);
      svg.appendChild(rect);
      label(svg, x + step * 0.3, d.label);
    });
    container.replaceChildren(svg);
  }
  function line(container, data, unit, color) {
    const max = niceMax(data.map((d) => d.value));
    const svg = frame(max, unit);
    const innerW = W - PAD.left - PAD.right;
    const innerH = H - PAD.top - PAD.bottom;
    const step = data.length > 1 ? innerW / (data.length - 1) : innerW;
    const pts = data.map((d, i) => [PAD.left + i * step, PAD.top + innerH - (d.value / max) * innerH]);
    svg.appendChild(svgEl('polyline', { points: pts.map((p) => p.join(',')).join(' '), fill: 'none', stroke: color || '#C8102E', 'stroke-width': 2.5 }));
    const every = Math.max(1, Math.ceil(data.length / 8));
    data.forEach((d, i) => { if (i % every === 0 || i === data.length - 1) { label(svg, pts[i][0], d.label); } });
    container.replaceChildren(svg);
  }
  return { bar, line };
})();
