/* الإشعارات */
App.start(async (root) => {
  const { el, icon } = UI;
  const list = el('div');
  async function load() {
    const rows = await Api.get('/api/notifications');
    list.replaceChildren(rows.length ? el('div', {}, rows.map((n) => el('div', { class: `notif${n.is_read ? '' : ' unread'}` }, icon(n.is_read ? 'envelope-open' : 'envelope'),
      el('div', { class: 'body' }, el('strong', { text: n.title }), el('div', { text: n.body }), el('div', { class: 'small muted' }, Dates.element(n.created_at))),
      el('div', { class: 'actions' },
        n.link ? el('a', { class: 'btn btn-sm btn-secondary', href: n.link, onclick: () => { Api.post(`/api/notifications/${n.id}/read`).catch(() => {}); } }, 'فتح') : null,
        !n.is_read ? UI.button('تمت القراءة', async () => {
          await Api.post(`/api/notifications/${n.id}/read`);
          await load();
        }, 'btn-sm btn-ghost') : null)))) : UI.empty('لا توجد إشعارات.', 'bell'));
  }
  root.append(UI.pageHead('الإشعارات', null, UI.button('تحديد الكل كمقروء', async () => {
    try {
      await Api.post('/api/notifications/read-all');
      await load();
    } catch (e) {
      UI.error(e);
    }
  }, 'btn-secondary', 'check-double')), UI.panel(null, list));
  await load();
});
