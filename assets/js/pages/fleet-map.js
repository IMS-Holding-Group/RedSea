/* الخريطة الحية للأسطول والتنبيهات */
App.start(async (root, me) => {
  const { el, icon } = UI;
  const zones = await Api.get('/api/zones');
  const mapBox = el('div');
  const side = el('div');
  const alertsBox = el('div');
  const legend = el('div', { class: 'legend' }, Object.entries(UI.TEXT.zone).map(([k, t]) => {
    const b = el('b');
    b.style.background = RYMap.ZONE_STYLE[k][0];
    return el('span', {}, b, t);
  }), el('span', {}, icon('location-arrow'), 'يخت'), el('span', {}, el('b', { class: 'stale-box' }), 'إشارة منقطعة'));
  root.append(UI.pageHead(me.role === 'owner' ? 'خريطة أسطولي' : 'الخريطة الحية', 'مواقع اليخوت والمناطق البحرية، وتُحدث كل 10 ثوانٍ'),
    el('div', { class: 'grid grid-2' }, UI.panel(null, mapBox, legend), UI.panel('اليخوت', side)),
    UI.panel('التنبيهات النشطة', alertsBox));
  const map = RYMap.create(mapBox, { center: [21.73, 39.05], zoom: 11, onYachtClick: (y) => { if (y.booking_id) { location.href = `/trip-live?id=${y.booking_id}`; } } });
  map.set('zones', zones);
  let fitted = false;
  async function refresh() {
    const [live, alerts] = await Promise.all([Api.get('/api/tracking/live'), Api.get('/api/alerts?status=active')]);
    live.forEach((y) => { y.tip = [y.name, y.trip ? `رحلة ${y.trip}` : 'راسٍ بلا رحلة', `السرعة ${UI.num(y.speed)} عقدة`, `آخر قراءة ${Dates.text(y.recorded_at)}`].concat(y.alerts.map((a) => UI.TEXT.alert[a.alert_type])); });
    map.set('yachts', live);
    if (!fitted && live.length) {
      map.fit(live.map((y) => [y.lat, y.lng]));
      fitted = true;
    }
    side.replaceChildren(live.length ? UI.table(['اليخت', 'الحالة', 'آخر قراءة', ''], live.map((y) => [
      y.name,
      el('div', {}, y.trip ? UI.badge('booking', 'in_progress') : el('span', { class: 'badge badge-muted', text: 'في المرسى' }), y.stale ? el('span', { class: 'badge badge-warning', text: 'إشارة منقطعة' }) : null, y.alerts.length ? el('span', { class: 'badge badge-danger', text: `${y.alerts.length} تنبيه` }) : null),
      Dates.element(y.recorded_at),
      UI.button('عرض', () => { map.center(y.lat, y.lng, 14); }, 'btn-sm btn-ghost', 'crosshairs')])) : UI.empty('لا توجد مواقع مسجلة بعد.', 'satellite'));
    alertsBox.replaceChildren(alerts.length ? UI.table(['النوع', 'اليخت', 'الخطورة', 'الرسالة', 'الوقت', 'الحالة', ''], alerts.map((a) => [
      UI.TEXT.alert[a.alert_type], a.yacht_name, UI.badge('severity', a.severity), a.message, Dates.element(a.created_at), UI.badge('alertStatus', a.status),
      el('div', { class: 'actions' },
        a.status === 'open' ? UI.button('اطلاع', () => { act(a.id, 'acknowledge'); }, 'btn-sm btn-ghost', 'eye') : null,
        UI.button('حل', () => { act(a.id, 'resolve'); }, 'btn-sm btn-success', 'check'),
        a.latitude ? UI.button('موقع', () => { map.center(a.latitude, a.longitude, 15); }, 'btn-sm btn-ghost', 'location-dot') : null)])) : UI.empty('لا توجد تنبيهات نشطة.', 'circle-check'));
  }
  async function act(id, action) {
    try {
      await Api.post(`/api/alerts/${id}/${action}`);
      await refresh();
    } catch (e) {
      UI.error(e);
    }
  }
  await refresh();
  setInterval(() => { if (!document.hidden) { refresh().catch(() => {}); } }, 10000);
});
