/* لوحة مدير المنصة */
App.start(async (root) => {
  const { el, icon } = UI;
  const [d, zones] = await Promise.all([Api.get('/api/dashboard/admin'), Api.get('/api/zones')]);
  const s = d.stats;
  const health = el('span', { class: 'badge badge-muted', text: 'فحص الخادم...' });
  const mapBox = el('div');
  root.append(UI.pageHead('لوحة مدير المنصة', 'مؤشرات التشغيل والامتثال والتنبيهات الحرجة', health),
    el('div', { class: 'grid grid-4' },
      UI.stat('المستخدمون', s.users, 'users'), UI.stat('اليخوت', s.yachts, 'sailboat'), UI.stat('رحلات جارية', s.active_trips, 'location-crosshairs'), UI.stat('حجوزات آخر 30 يوماً', s.bookings_month, 'calendar'),
      UI.stat('وثائق بانتظار المراجعة', s.pending_docs, 'file-circle-question'), UI.stat('تصاريح بانتظار الاعتماد', s.pending_permits, 'stamp'),
      UI.stat('تنبيهات حرجة', s.critical_alerts, 'triangle-exclamation'), UI.stat('حجوزات معلقة بسبب الطقس', s.weather_holds, 'wind')),
    el('br'),
    el('div', { class: 'grid grid-2' },
      UI.panel('مواقع التنبيهات النشطة', mapBox),
      UI.panel('التنبيهات النشطة', d.alerts.length ? UI.table(['النوع', 'اليخت', 'الخطورة', 'الوقت'], d.alerts.map((a) => [UI.TEXT.alert[a.alert_type], a.yacht_name, UI.badge('severity', a.severity), Dates.element(a.created_at)])) : UI.empty('لا توجد تنبيهات.', 'circle-check'),
        el('div', { class: 'actions' }, el('a', { class: 'btn btn-secondary btn-sm', href: '/fleet-map', text: 'إدارة التنبيهات على الخريطة' }), el('a', { class: 'btn btn-ghost btn-sm', href: '/admin-compliance', text: 'مراجعة الوثائق والتصاريح' })))),
    UI.panel('المستخدمون حسب الدور', UI.table(['الدور', 'العدد'], d.by_role.map((r) => [UI.badge('role', r.role), r.c]))));
  const map = RYMap.create(mapBox, { center: [21.73, 39.05], zoom: 10 });
  map.set('zones', zones);
  const pts = d.alerts.filter((a) => a.latitude).map((a) => ({ lat: a.latitude, lng: a.longitude, color: a.severity === 'critical' ? '#C8102E' : '#B7791F', tip: [UI.TEXT.alert[a.alert_type], a.yacht_name, a.message] }));
  map.set('points', pts);
  if (pts.length) { map.fit(pts.map((p) => [p.lat, p.lng])); }
  async function checkHealth() {
    try {
      const h = await Api.get('/api/health');
      health.className = `badge badge-${h.status === 'ok' ? 'success' : 'warning'}`;
      health.textContent = `الخادم يعمل، زمن الاستجابة ${h.response_ms} مللي ثانية`;
    } catch (e) {
      health.className = 'badge badge-danger';
      health.textContent = 'تعذر الاتصال بالخادم';
    }
  }
  checkHealth();
  setInterval(checkHealth, 60000);
});
