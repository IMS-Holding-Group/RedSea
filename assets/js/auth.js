/* تشغيل الصفحة: تحميل المستخدم، رسم الترويسة والذيل، ثم استدعاء دالة الصفحة */
const App = (() => {
  const { el, icon } = UI;
  let me = null;
  const NAV = {
    guest: [['/', 'الرئيسية'], ['/yachts', 'اليخوت']],
    tourist: [['/yachts', 'اليخوت'], ['/my-bookings', 'حجوزاتي']],
    owner: [['/owner-dashboard', 'لوحة التحكم'], ['/owner-yachts', 'يخوتي'], ['/owner-bookings', 'الحجوزات'], ['/owner-maintenance', 'الصيانة'], ['/owner-compliance', 'الامتثال'], ['/fleet-map', 'خريطة الأسطول']],
    marina_manager: [['/marina-dashboard', 'لوحة المرسى'], ['/marina-berths', 'المرابط'], ['/fleet-map', 'الخريطة الحية']],
    provider: [['/provider-dashboard', 'لوحة التحكم'], ['/provider-orders', 'أوامر العمل']],
    admin: [['/admin-dashboard', 'لوحة التحكم'], ['/admin-users', 'المستخدمون'], ['/admin-zones', 'المناطق'], ['/admin-compliance', 'الامتثال'], ['/fleet-map', 'الخريطة'], ['/marina-dashboard', 'المراسي'], ['/admin-audit', 'التدقيق']]
  };
  const HOME = { tourist: '/my-bookings', owner: '/owner-dashboard', marina_manager: '/marina-dashboard', provider: '/provider-dashboard', admin: '/admin-dashboard' };

  async function logout() {
    try {
      await Api.post('/api/auth/logout');
    } catch (e) {
      /* الخروج يكتمل محلياً حتى لو فشل الطلب */
    }
    location.href = '/login';
  }
  function header() {
    const links = NAV[me ? me.role : 'guest'];
    const nav = el('nav', { class: 'nav', 'aria-label': 'التنقل الرئيسي' }, links.map(([href, text]) => el('a', { href, text, class: location.pathname === href ? 'active' : null })));
    const tools = el('div', { class: 'header-tools' });
    if (me) {
      const count = el('span', { class: 'count hidden' });
      tools.append(
        el('a', { class: 'btn btn-ghost btn-icon bell', href: '/notifications', 'aria-label': 'الإشعارات' }, icon('bell'), count),
        el('a', { class: 'user-name', href: '/profile', text: me.full_name }),
        el('button', { class: 'btn btn-secondary btn-sm', type: 'button', onclick: logout }, icon('right-from-bracket'), 'خروج'));
      const refresh = async () => {
        try {
          const n = await Api.get('/api/notifications/unread-count');
          count.textContent = n > 99 ? '99+' : String(n);
          count.classList.toggle('hidden', !n);
        } catch (e) {
          /* تجاهل أخطاء التحديث الدوري */
        }
      };
      refresh();
      setInterval(refresh, 30000);
    } else {
      tools.appendChild(el('a', { class: 'btn btn-sm', href: '/login' }, icon('right-to-bracket'), 'تسجيل الدخول'));
    }
    const toggle = el('button', { class: 'btn btn-ghost btn-icon menu-toggle', type: 'button', 'aria-label': 'القائمة', onclick: () => { nav.classList.toggle('open'); } }, icon('bars'));
    const brand = el('a', { class: 'brand', href: me ? HOME[me.role] : '/' }, el('img', { src: '/assets/images/logo.svg', alt: 'اليخت الأحمر', width: 176, height: 44 }));
    return el('header', { class: 'site-header' }, el('div', { class: 'container' }, brand, nav, tools, toggle));
  }
  function footer() {
    return el('footer', { class: 'site-footer' }, el('div', { class: 'container' },
      el('div', { text: 'منصة اليخت الأحمر لإدارة عمليات اليخوت في البحر الأحمر' })));
  }
  async function start(render) {
    try {
      me = await Api.get('/api/auth/me');
      if (me) { Api.setCsrf(me.csrf); }
    } catch (e) {
      me = null;
    }
    const main = document.getElementById('app');
    document.body.insertBefore(header(), main);
    document.body.appendChild(footer());
    main.appendChild(UI.loading());
    try {
      const content = el('div');
      await render(content, me);
      main.replaceChildren(content);
    } catch (e) {
      if (e.status === 401) {
        location.href = '/login?next=' + encodeURIComponent(location.pathname + location.search);
        return;
      }
      main.replaceChildren(UI.empty(e.message || 'تعذر تحميل الصفحة.', 'triangle-exclamation'));
    }
  }
  return { start, logout, HOME, user: () => me };
})();
