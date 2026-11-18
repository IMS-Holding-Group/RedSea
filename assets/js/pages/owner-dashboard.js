/* لوحة المالك */
App.start(async (root) => {
  const { el, icon } = UI;
  const d = await Api.get('/api/dashboard/owner');
  const revenue = el('div', { class: 'chart' });
  const avgCompliance = d.yachts.length ? Math.round(d.yachts.reduce((s, y) => s + y.compliance, 0) / d.yachts.length) : 0;
  root.append(
    UI.pageHead('لوحة المالك', 'نظرة شاملة على أسطولك وحجوزاته وصيانته'),
    d.alerts.length ? el('div', { class: 'notice notice-danger' }, icon('triangle-exclamation'), el('span', {}, `لديك ${d.alerts.length} تنبيه مفتوح. `, el('a', { href: '/fleet-map', text: 'افتح الخريطة الحية' }))) : null,
    el('div', { class: 'grid grid-4' },
      UI.stat('اليخوت', d.yachts.length, 'sailboat'),
      UI.stat('رحلات جارية', d.live_trips, 'location-crosshairs'),
      UI.stat('طلبات بانتظار موافقتك', d.pending.length, 'hourglass-half'),
      UI.stat('متوسط الامتثال', `${avgCompliance}%`, 'shield-halved')),
    el('br'),
    el('div', { class: 'grid grid-2' },
      UI.panel('الإيرادات خلال آخر 6 أشهر (ر.س)', revenue),
      UI.panel('طلبات الحجز المعلقة', d.pending.length ? UI.table(['المرجع', 'اليخت', 'البداية'], d.pending.map((b) => [el('span', { class: 'ltr', text: b.reference }), b.yacht_name, Dates.element(b.start_at)])) : UI.empty('لا توجد طلبات معلقة.', 'inbox'),
        el('div', { class: 'actions' }, el('a', { class: 'btn btn-secondary btn-sm', href: '/owner-bookings', text: 'إدارة الحجوزات' })))),
    el('div', { class: 'grid grid-2' },
      UI.panel('أوامر الصيانة المفتوحة', d.orders.length ? UI.table(['المهمة', 'اليخت', 'الأولوية', 'الحالة', 'الاستحقاق'], d.orders.map((w) => [w.title, w.yacht_name, UI.badge('priority', w.priority), UI.badge('wo', w.status), Dates.element(w.due_at, true)])) : UI.empty('لا توجد أوامر مفتوحة.', 'screwdriver-wrench')),
      UI.panel('حالة اليخوت', UI.table(['اليخت', 'الحالة', 'ساعات المحرك', 'الامتثال'], d.yachts.map((y) => [y.name, UI.badge('yacht', y.status), UI.num(y.engine_hours), `${y.compliance}%`])))),
    d.alerts.length ? UI.panel('التنبيهات النشطة', UI.table(['النوع', 'اليخت', 'الخطورة', 'الرسالة', 'الوقت'], d.alerts.map((a) => [UI.TEXT.alert[a.alert_type], a.yacht_name, UI.badge('severity', a.severity), a.message, Dates.element(a.created_at)]))) : null);
  Charts.bar(revenue, d.revenue);
});
