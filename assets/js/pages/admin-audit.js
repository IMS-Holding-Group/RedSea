/* سجل التدقيق */
App.start(async (root) => {
  const { el, icon } = UI;
  const f = el('form', { class: 'filters' }, UI.field({ name: 'action', label: 'الإجراء يحتوي على' }), el('div', { class: 'field' }, el('button', { class: 'btn', type: 'submit' }, icon('filter'), 'تصفية')));
  const list = el('div');
  async function load() {
    const a = UI.read(f).action;
    const rows = await Api.get('/api/admin/audit' + (a ? `?action=${encodeURIComponent(a)}` : ''));
    list.replaceChildren(rows.length ? UI.table(['الوقت', 'المستخدم', 'الإجراء', 'الكيان', 'التفاصيل', 'IP'], rows.map((r) => [
      Dates.element(r.created_at), r.full_name ? el('span', {}, r.full_name, el('div', { class: 'small muted ltr', text: r.email })) : '-',
      el('span', { class: 'ltr', text: r.action }), r.entity ? el('span', { class: 'ltr', text: `${r.entity} #${r.entity_id}` }) : '-', r.details || '-', el('span', { class: 'ltr', text: r.ip_address || '-' })])) : UI.empty('لا توجد سجلات.', 'list'));
  }
  f.addEventListener('submit', (e) => {
    e.preventDefault();
    load().catch(UI.error);
  });
  root.append(UI.pageHead('سجل التدقيق', 'آخر 300 إجراء حساس في النظام'), UI.panel(null, f), list);
  await load();
});
