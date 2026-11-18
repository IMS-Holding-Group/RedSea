/* متابعة رحلة على الخريطة الحية مع زر الاستغاثة */
App.start(async (root, me) => {
  const { el, icon } = UI;
  const id = UI.qs('id');
  if (!/^\d+$/.test(id || '')) { throw new Error('الرحلة غير محددة.'); }
  const [b, zones] = await Promise.all([Api.get(`/api/bookings/${id}`), Api.get('/api/zones')]);
  const mapBox = el('div');
  const info = el('div');
  const head = UI.pageHead(`رحلة ${b.yacht_name}`, `المرجع ${b.reference}`);
  const legend = el('div', { class: 'legend' }, Object.entries(UI.TEXT.zone).map(([k, t]) => el('span', {}, colorBox(k), t)));
  function colorBox(k) {
    const box = el('b');
    box.style.background = RYMap.ZONE_STYLE[k][0];
    return box;
  }
  if (me.role === 'tourist' && b.status === 'in_progress') {
    head.appendChild(el('div', { class: 'actions' }, UI.button('نداء استغاثة SOS', sos, 'btn-danger btn-sos', 'life-ring')));
  }
  root.append(head, el('div', { class: 'grid grid-2' }, UI.panel(null, mapBox, legend), UI.panel('حالة الرحلة', info)));
  const map = RYMap.create(mapBox, { center: [21.73, 39.06], zoom: 12 });
  map.set('zones', zones);
  let fitted = false;
  async function refresh() {
    const trail = await Api.get(`/api/tracking/trail/${id}`);
    const pts = trail.points.map((p) => [p.lat, p.lng]);
    map.set('trail', pts);
    let yachtPos = null;
    if (trail.status === 'in_progress') {
      const live = await Api.get('/api/tracking/live');
      yachtPos = live.find((y) => y.yacht_id === trail.yacht_id) || null;
    } else if (trail.points.length) {
      const last = trail.points[trail.points.length - 1];
      yachtPos = { yacht_id: trail.yacht_id, name: b.yacht_name, lat: last.lat, lng: last.lng, speed: last.speed, heading: 0, recorded_at: last.recorded_at, alerts: [] };
    }
    if (yachtPos) {
      yachtPos.tip = [yachtPos.name, `السرعة ${UI.num(yachtPos.speed)} عقدة`, `آخر تحديث ${Dates.text(yachtPos.recorded_at)}`];
      map.set('yachts', [yachtPos]);
    }
    if (!fitted && pts.length) {
      map.fit(pts.concat(yachtPos ? [[yachtPos.lat, yachtPos.lng]] : []));
      fitted = true;
    }
    info.replaceChildren(
      el('p', {}, 'الحالة: ', UI.badge('booking', trail.status)),
      el('p', {}, 'البداية: ', Dates.element(b.start_at)),
      el('p', {}, 'النهاية: ', Dates.element(b.end_at)),
      el('p', { text: `عدد القراءات المسجلة: ${trail.points.length}` }),
      yachtPos ? el('p', {}, 'آخر موقع: ', Dates.element(yachtPos.recorded_at), ` بسرعة ${UI.num(yachtPos.speed)} عقدة`) : el('p', { class: 'muted', text: 'لم تصل قراءات GPS بعد.' }),
      yachtPos && yachtPos.stale ? el('div', { class: 'notice notice-warning' }, icon('satellite-dish'), 'انقطعت إشارة GPS لأكثر من 10 دقائق. سيتم عرض القراءات المؤجلة فور عودة الاتصال.') : null,
      yachtPos && yachtPos.alerts && yachtPos.alerts.length ? el('div', { class: 'notice notice-danger' }, icon('triangle-exclamation'), el('div', {}, yachtPos.alerts.map((a) => el('div', { text: `${UI.TEXT.alert[a.alert_type]}: ${a.message}` })))) : null,
      el('p', { class: 'small muted', text: trail.status === 'in_progress' ? 'يتم التحديث تلقائياً كل 10 ثوانٍ.' : 'الرحلة غير جارية، يعرض المسار المسجل فقط.' }));
    return trail.status;
  }
  async function sos() {
    if (!await UI.confirm('نداء استغاثة', 'سيتم إرسال نداء استغاثة فوري إلى مالك اليخت وإدارة المرسى ومدير المنصة مع موقعك. هل تريد المتابعة؟', 'إرسال النداء', 'btn-danger')) { return; }
    const send = async (coords) => {
      try {
        await Api.post('/api/tracking/sos', coords || {});
        UI.ok('تم إرسال نداء الاستغاثة. سيتم التواصل معك فوراً.');
      } catch (e) {
        UI.error(e);
      }
    };
    if (!navigator.geolocation) {
      send();
      return;
    }
    navigator.geolocation.getCurrentPosition((p) => { send({ lat: p.coords.latitude, lng: p.coords.longitude }); }, () => { send(); }, { timeout: 5000 });
  }
  const status = await refresh();
  if (status === 'in_progress') {
    setInterval(() => { if (!document.hidden) { refresh().catch(() => {}); } }, 10000);
  }
});
