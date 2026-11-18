/* الصفحة الرئيسية */
App.start(async (root, me) => {
  const { el, icon } = UI;
  const marinas = await Api.get('/api/marinas');
  const chart = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  chart.setAttribute('class', 'hero-chart');
  chart.setAttribute('viewBox', '0 0 800 300');
  chart.setAttribute('preserveAspectRatio', 'xMidYMid slice');
  for (let i = 0; i < 9; i += 1) {
    const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    p.setAttribute('d', `M0,${40 + i * 30} C200,${20 + i * 30} 400,${70 + i * 30} 800,${35 + i * 30}`);
    p.setAttribute('fill', 'none');
    p.setAttribute('stroke', i % 3 === 0 ? '#C8102E' : '#5F86B8');
    p.setAttribute('stroke-width', i % 3 === 0 ? 1.4 : 0.8);
    chart.appendChild(p);
  }
  const start = new Date(Date.now() + 26 * 3600000);
  const defaultDate = Dates.toInput(start.toISOString().slice(0, 19), true);
  const search = el('form', { class: 'quick-search filters' },
    UI.field({ name: 'marina_id', label: 'المرسى', type: 'select', options: [['', 'كل المراسي']].concat(marinas.map((m) => [m.id, `${m.name} - ${m.city}`])) }),
    UI.field({ name: 'date', label: 'التاريخ', type: 'date', value: defaultDate }),
    UI.field({ name: 'time', label: 'وقت الانطلاق', type: 'time', value: '09:00' }),
    UI.field({ name: 'hours', label: 'المدة بالساعات', type: 'number', min: 2, max: 12, value: 4 }),
    UI.field({ name: 'guests', label: 'عدد الضيوف', type: 'number', min: 1, max: 200, value: 4 }),
    el('div', { class: 'field' }, el('button', { class: 'btn', type: 'submit' }, icon('magnifying-glass'), 'ابحث عن يخت')));
  search.addEventListener('submit', (e) => {
    e.preventDefault();
    const d = UI.read(search);
    const params = new URLSearchParams({ marina_id: d.marina_id, date: d.date, time: d.time, hours: d.hours, guests: d.guests });
    location.href = '/yachts?' + params.toString();
  });
  const feature = (ic, title, text) => el('div', { class: 'feature' }, el('span', { class: 'icon' }, icon(ic)), el('h3', { text: title }), el('p', { class: 'muted', text: text }));
  root.append(
    el('section', { class: 'hero' }, chart, el('div', { class: 'hero-inner' },
      el('h1', { text: 'رحلات البحر الأحمر تبدأ من قرار آمن' }),
      el('p', { text: 'منصة موحدة تجمع حجز اليخوت بحسب الطقس البحري الفعلي، والتتبع الحي مع مناطق حظر الرسو، وإدارة المرابط والصيانة والامتثال.' })),
    search),
    el('div', { class: 'grid grid-3' },
      feature('cloud-sun-rain', 'حجز مرتبط بالطقس', 'لا تُعرض الرحلة متاحة إلا إذا كانت سرعة الرياح وارتفاع الموج ضمن الحدود الآمنة لفئة اليخت، ويُعاد التقييم تلقائياً قبل الرحلة.'),
      feature('map-location-dot', 'تتبع حي ومناطق محظورة', 'خريطة تعرض مواقع اليخوت مع مضلعات الشعاب المرجانية والمحميات، وتنبيه فوري عند الرسو في منطقة محظورة أو إرسال نداء استغاثة.'),
      feature('screwdriver-wrench', 'صيانة وامتثال', 'أوامر صيانة تنشأ تلقائياً بحسب ساعات تشغيل المحرك، ووثائق وتصاريح إبحار تمنع أي رحلة غير مستوفية للمتطلبات.')),
    el('div', { class: 'grid grid-2' },
      UI.panel('كيف تعمل المنصة', el('ol', { class: 'steps' },
        el('li', { text: 'يسجل المالك يخته ووثائقه وجهاز التتبع، ويعتمد مدير المنصة الوثائق.' }),
        el('li', { text: 'يبحث السائح عن رحلة، ويرى تقييم الطقس للفترة قبل الحجز.' }),
        el('li', { text: 'يوافق المالك على الحجز ويصدر تصريح الإبحار من مدير المنصة.' }),
        el('li', { text: 'تُتابع الرحلة على الخريطة الحية، وتُسجل ساعات المحرك لتوليد أوامر الصيانة.' }))),
      UI.panel('لمن صُممت المنصة', UI.table(['الفئة', 'ما تقدمه المنصة'], [
        ['السائح', 'حجز آمن، متابعة الرحلة، زر استغاثة'],
        ['مالك اليخت', 'إدارة الأسطول والحجوزات والصيانة والوثائق'],
        ['مدير المرسى', 'إدارة المرابط وطلبات الرسو والإشغال'],
        ['مزود الخدمة', 'استقبال أوامر العمل وتقديم العروض'],
        ['مدير المنصة', 'المناطق البحرية والاعتمادات والتنبيهات']
      ]))));
  if (me) { root.prepend(el('div', { class: 'notice' }, icon('circle-info'), el('span', {}, 'أنت مسجل الدخول. ', el('a', { href: App.HOME[me.role], text: 'انتقل إلى لوحتك' })))); }
});
