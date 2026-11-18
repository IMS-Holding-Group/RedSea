/* الملف الشخصي وتغيير كلمة السر */
App.start(async (root, me) => {
  const { el } = UI;
  const info = UI.form([
    { name: 'full_name', label: 'الاسم الكامل', required: true, value: me.full_name },
    { name: 'phone', label: 'رقم الجوال', value: me.phone }
  ], async (d) => {
    await Api.put('/api/auth/profile', d);
    UI.ok('تم حفظ البيانات.');
  });
  const pwd = UI.form([
    { name: 'current_password', label: 'كلمة السر الحالية', type: 'password', required: true, full: true, autocomplete: 'current-password' },
    { name: 'new_password', label: 'كلمة السر الجديدة', type: 'password', required: true, autocomplete: 'new-password', hint: '8 أحرف على الأقل وتحتوي حروفاً وأرقاماً' },
    { name: 'confirm', label: 'تأكيد كلمة السر', type: 'password', required: true, autocomplete: 'new-password' }
  ], async (d, f) => {
    if (d.new_password !== d.confirm) {
      UI.setError(f, 'confirm', 'كلمتا السر غير متطابقتين.');
      return;
    }
    await Api.put('/api/auth/password', { current_password: d.current_password, new_password: d.new_password });
    f.reset();
    UI.ok('تم تغيير كلمة السر وإنهاء الجلسات الأخرى.');
  }, 'تغيير كلمة السر');
  root.append(UI.pageHead('الملف الشخصي', null),
    el('div', { class: 'grid grid-2' }, UI.panel('البيانات الأساسية', el('p', {}, 'البريد: ', el('span', { class: 'ltr', text: me.email }), ' ', UI.badge('role', me.role)), info), UI.panel('كلمة السر', pwd)));
});
