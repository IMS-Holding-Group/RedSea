/* إدارة المستخدمين */
App.start(async (root, me) => {
  const { el, icon } = UI;
  const roleOpts = Object.entries(UI.LABELS.role).map(([k, v]) => [k, v[0]]);
  const filter = UI.field({ name: 'role', label: 'الدور', type: 'select', options: [['', 'الكل']].concat(roleOpts) });
  const list = el('div');
  async function load() {
    const role = filter.querySelector('select').value;
    const users = await Api.get('/api/admin/users' + (role ? `?role=${role}` : ''));
    list.replaceChildren(UI.table(['الاسم', 'البريد', 'الجوال', 'الدور', 'الحالة', 'آخر دخول', ''], users.map((u) => [
      u.full_name, el('span', { class: 'ltr', text: u.email }), el('span', { class: 'ltr', text: u.phone || '-' }), UI.badge('role', u.role),
      u.is_active ? el('span', { class: 'badge badge-success', text: 'نشط' }) : el('span', { class: 'badge badge-danger', text: 'معطل' }),
      u.last_login_at ? Dates.element(u.last_login_at) : '-',
      el('div', { class: 'actions' }, UI.button('تعديل', () => { edit(u); }, 'btn-sm btn-ghost', 'pen'),
        u.id !== me.id ? UI.button(u.is_active ? 'تعطيل' : 'تفعيل', async () => {
          try {
            await Api.post(`/api/admin/users/${u.id}/toggle`);
            await load();
          } catch (e) {
            UI.error(e);
          }
        }, 'btn-sm btn-ghost', u.is_active ? 'user-slash' : 'user-check') : null)])));
  }
  function edit(u) {
    let close = null;
    const defs = u ? [
      { name: 'full_name', label: 'الاسم', required: true, value: u.full_name },
      { name: 'phone', label: 'الجوال', value: u.phone },
      { name: 'role', label: 'الدور', type: 'select', value: u.role, options: roleOpts }
    ] : [
      { name: 'full_name', label: 'الاسم', required: true },
      { name: 'email', label: 'البريد', type: 'email', required: true },
      { name: 'phone', label: 'الجوال' },
      { name: 'role', label: 'الدور', type: 'select', options: roleOpts },
      { name: 'password', label: 'كلمة السر المؤقتة', type: 'password', required: true, full: true, hint: '8 أحرف على الأقل وتحتوي حروفاً وأرقاماً' }
    ];
    const f = UI.form(defs, async (d) => {
      if (u) {
        await Api.put(`/api/admin/users/${u.id}`, d);
      } else {
        await Api.post('/api/admin/users', d);
      }
      close();
      UI.ok('تم الحفظ.');
      await load();
    });
    close = UI.modal(u ? `تعديل ${u.full_name}` : 'مستخدم جديد', f, []);
  }
  filter.querySelector('select').addEventListener('change', () => { load().catch(UI.error); });
  root.append(UI.pageHead('المستخدمون', 'أنشئ حسابات المالكين ومديري المراسي ومزودي الخدمة', UI.button('مستخدم جديد', () => { edit(null); }, '', 'user-plus')),
    UI.panel(null, el('div', { class: 'filters' }, filter)), list);
  await load();
});
