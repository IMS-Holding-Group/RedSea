/* تسجيل الدخول وتسجيل سائح جديد */
App.start(async (root, me) => {
  const { el, icon } = UI;
  const next = UI.qs('next');
  const target = (role) => (next && next.startsWith('/') && !next.startsWith('//') ? next : App.HOME[role]);
  const loginForm = UI.form([
    { name: 'email', label: 'البريد الإلكتروني', type: 'email', required: true, full: true, autocomplete: 'username' },
    { name: 'password', label: 'كلمة السر', type: 'password', required: true, full: true, autocomplete: 'current-password' }
  ], async (d) => {
    const res = await Api.post('/api/auth/login', d);
    location.href = target(res.role);
  }, 'دخول');
  const regForm = UI.form([
    { name: 'full_name', label: 'الاسم الكامل', required: true, full: true },
    { name: 'email', label: 'البريد الإلكتروني', type: 'email', required: true },
    { name: 'phone', label: 'رقم الجوال', required: true, placeholder: '05XXXXXXXX' },
    { name: 'password', label: 'كلمة السر', type: 'password', required: true, full: true, hint: '8 أحرف على الأقل وتحتوي حروفاً وأرقاماً', autocomplete: 'new-password' }
  ], async (d) => {
    await Api.post('/api/auth/register', d);
    UI.ok('تم إنشاء الحساب. يمكنك تسجيل الدخول الآن.');
    showTab('login');
    loginForm.elements.email.value = d.email;
  }, 'إنشاء حساب سائح');
  regForm.classList.add('hidden');
  const tabLogin = el('button', { type: 'button', class: 'active', text: 'تسجيل الدخول' });
  const tabReg = el('button', { type: 'button', text: 'حساب سائح جديد' });
  function showTab(t) {
    tabLogin.classList.toggle('active', t === 'login');
    tabReg.classList.toggle('active', t !== 'login');
    loginForm.classList.toggle('hidden', t !== 'login');
    regForm.classList.toggle('hidden', t === 'login');
  }
  tabLogin.addEventListener('click', () => { showTab('login'); });
  tabReg.addEventListener('click', () => { showTab('reg'); });
  const box = el('div', { class: 'auth-box' }, el('img', { class: 'logo', src: '/assets/images/logo.svg', alt: 'اليخت الأحمر' }), el('div', { class: 'tabs' }, tabLogin, tabReg), loginForm, regForm);
  const side = el('div', { class: 'auth-box' }, el('h2', { text: 'منصة اليخت الأحمر' }),
    el('p', { class: 'muted', text: 'سجل دخولك لإدارة يخوتك ومراسيك وأوامر العمل، أو لحجز رحلتك القادمة ومتابعتها.' }));
  const demos = [['مدير المنصة', 'admin@redyacht.sa'], ['مدير المرسى', 'marina@redyacht.sa'], ['مالك يخت', 'owner@redyacht.sa'], ['مالك يخت ثانٍ', 'owner2@redyacht.sa'], ['سائح', 'tourist@redyacht.sa'], ['مزود خدمة', 'provider@redyacht.sa']];
  const info = await Api.get('/api/auth/csrf');
  Api.setCsrf(info.csrf);
  const dev = info.demo;
  if (dev) {
    const tbl = UI.table(['الدور', 'البريد'], demos.map(([r, e]) => [r, el('span', { class: 'ltr', text: e })]));
    tbl.classList.add('demo-table');
    tbl.querySelectorAll('tbody tr').forEach((tr, i) => {
      tr.addEventListener('click', () => {
        showTab('login');
        loginForm.elements.email.value = demos[i][1];
        loginForm.elements.password.focus();
      });
    });
    side.append(el('h3', { text: 'الحسابات التجريبية' }), el('p', { class: 'small muted', text: 'اضغط على أي حساب لتعبئة البريد، وكلمة السر هي قيمة SEED_DEMO_PASSWORD في ملف .env' }), tbl);
  }
  root.appendChild(el('div', { class: 'auth-wrap' }, box, side));
});
