/* صفحة الخطأ العامة */
App.start(async (root, me) => {
  const { el, icon } = UI;
  root.appendChild(el('div', { class: 'panel empty' }, icon('compass'),
    el('h1', { text: 'تعذر عرض الصفحة' }),
    el('p', { text: 'قد تكون الصفحة غير موجودة أو ليست لديك صلاحية للوصول إليها.' }),
    el('a', { class: 'btn', href: me ? App.HOME[me.role] : '/', text: 'العودة' })));
});
