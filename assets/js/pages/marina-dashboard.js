/* لوحة مدير المرسى: الإشغال والطلبات واليخوت المقيمة */
App.start(async (root) => {
  const { el, icon } = UI;
  const marinas = await Api.get('/api/dashboard/marina');
  root.appendChild(UI.pageHead('لوحة المرسى', 'نسب الإشغال خلال 30 يوماً وطلبات المرابط المعلقة',
    el('a', { class: 'btn', href: '/marina-berths' }, icon('anchor'), 'إدارة المرابط')));
  if (!marinas.length) {
    root.appendChild(UI.empty('لا توجد مراسٍ مسندة إليك.', 'anchor'));
    return;
  }
  const charts = [];
  marinas.forEach((m) => {
    const chart = el('div', { class: 'chart' });
    charts.push([chart, m.occupancy]);
    root.appendChild(UI.panel(`${m.name} - ${m.city}`,
      el('div', { class: 'grid grid-4' }, UI.stat('عدد المرابط', m.berths, 'anchor'), UI.stat('الإشغال اليوم', `${m.today}%`, 'chart-simple'),
        UI.stat('طلبات معلقة', m.pending, 'hourglass-half'), UI.stat('يخوت مقيمة', m.yachts.length, 'sailboat')),
      el('h3', { text: 'نسبة الإشغال اليومية' }), chart,
      m.yachts.length ? UI.table(['اليخت', 'الطول', 'الحالة'], m.yachts.map((y) => [y.name, `${y.length_m} م`, UI.badge('yacht', y.status)])) : null));
  });
  charts.forEach(([c, data]) => { Charts.line(c, data, '%'); });
});
