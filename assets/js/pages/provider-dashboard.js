/* لوحة مزود الخدمة */
App.start(async (root) => {
  const { el, icon } = UI;
  const d = await Api.get('/api/dashboard/provider');
  const services = (d.profile && d.profile.services ? d.profile.services.split(',') : []).map((s) => UI.TEXT.service[s] || s);
  root.append(UI.pageHead(d.profile ? d.profile.company_name : 'لوحة مزود الخدمة', `الخدمات: ${services.join('، ') || '-'}`,
    el('a', { class: 'btn', href: '/provider-orders' }, icon('list-check'), 'أوامر العمل')),
  el('div', { class: 'grid grid-4' }, UI.stat('أوامر متاحة لتقديم عرض', d.available, 'inbox'), UI.stat('أوامر مسندة', d.assigned, 'clipboard-check'),
    UI.stat('قيد التنفيذ', d.in_progress, 'screwdriver-wrench'), UI.stat('مكتملة', d.completed, 'flag-checkered')),
  el('br'),
  el('div', { class: 'grid grid-2' }, UI.stat('إجمالي الإيرادات من الأوامر المكتملة', UI.money(d.revenue), 'sack-dollar'),
    UI.stat('متوسط التقييم', d.profile ? UI.num(d.profile.rating_avg) : '-', 'star')));
});
