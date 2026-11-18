/* البحث عن اليخوت مع مؤشر الطقس للفترة المختارة */
App.start(async (root, me) => {
  const { el, icon } = UI;
  const marinas = await Api.get('/api/marinas');
  const q = new URLSearchParams(location.search);
  const tomorrow = Dates.toInput(new Date(Date.now() + 26 * 3600000).toISOString().slice(0, 19), true);
  const filters = el('form', { class: 'filters' },
    UI.field({ name: 'marina_id', label: 'المرسى', type: 'select', value: q.get('marina_id') || '', options: [['', 'كل المراسي']].concat(marinas.map((m) => [m.id, m.name])) }),
    UI.field({ name: 'date', label: 'التاريخ', type: 'date', value: q.get('date') || tomorrow }),
    UI.field({ name: 'time', label: 'وقت الانطلاق', type: 'time', value: q.get('time') || '09:00' }),
    UI.field({ name: 'hours', label: 'المدة (ساعات)', type: 'number', min: 2, max: 12, value: q.get('hours') || 4 }),
    UI.field({ name: 'guests', label: 'الضيوف', type: 'number', min: 1, max: 200, value: q.get('guests') || 2 }),
    UI.field({ name: 'type', label: 'النوع', type: 'select', value: q.get('type') || '', options: [['', 'الكل'], ['motor', 'يخت بمحرك'], ['sailing', 'شراعي'], ['catamaran', 'مزدوج البدن']] }),
    UI.field({ name: 'max_price', label: 'أقصى سعر للساعة', type: 'number', min: 0, max: 100000, value: q.get('max_price') || '' }),
    el('div', { class: 'field' }, el('button', { class: 'btn', type: 'submit' }, icon('magnifying-glass'), 'بحث')));
  const results = el('div');
  async function load() {
    const d = UI.read(filters);
    const start = Dates.fromInput(`${d.date}T${d.time || '09:00'}`);
    const params = new URLSearchParams();
    ['marina_id', 'guests', 'type', 'max_price', 'hours'].forEach((k) => { if (d[k]) { params.set(k, d[k]); } });
    if (start) { params.set('start', start); }
    history.replaceState(null, '', '/yachts?' + new URLSearchParams(d).toString());
    results.replaceChildren(UI.loading());
    const list = await Api.get('/api/yachts?' + params.toString());
    if (!list.length) {
      results.replaceChildren(UI.empty('لا توجد يخوت مطابقة لمعايير البحث.', 'ship'));
      return;
    }
    const source = list.find((y) => y.weather_source);
    const grid = el('div', { class: 'grid grid-3' }, list.map((y) => {
      const link = `/yacht-details?id=${y.id}&start=${encodeURIComponent(start || '')}&hours=${d.hours || 4}&guests=${d.guests || 2}`;
      const photo = el('div', { class: 'yacht-photo' }, y.photos.length ? el('img', { src: y.photos[0], alt: y.name, loading: 'lazy' }) : icon('sailboat'));
      const status = y.weather ? el('div', { class: 'actions' }, UI.badge('weather', y.weather), y.available ? el('span', { class: 'badge badge-success', text: 'متاح للحجز' }) : el('span', { class: 'badge badge-danger', text: 'غير متاح' })) : null;
      return el('article', { class: 'yacht-card' }, photo, el('div', { class: 'yacht-body' },
        el('h3', { text: y.name }),
        el('ul', { class: 'specs' },
          el('li', {}, icon('location-dot'), `${y.marina_name} - ${y.marina_city}`),
          el('li', {}, icon('ruler-horizontal'), `${y.length_m} م`),
          el('li', {}, icon('users'), `${y.capacity} ضيوف`),
          el('li', {}, icon('anchor'), y.type_label)),
        status,
        y.reasons && y.reasons.length ? el('p', { class: 'small muted', text: y.reasons[0] }) : null,
        el('div', { class: 'yacht-foot' }, el('span', { class: 'price', text: `${UI.money(y.hourly_rate)} / ساعة` }), el('a', { class: 'btn btn-sm', href: link, text: 'التفاصيل والحجز' }))));
    }));
    results.replaceChildren(
      source ? el('div', { class: `notice${source.weather_source === 'simulated' ? ' notice-warning' : ''}` }, icon('cloud-sun'), `مصدر بيانات الطقس: ${UI.TEXT.source[source.weather_source]}`) : null,
      grid);
  }
  filters.addEventListener('submit', (e) => {
    e.preventDefault();
    load().catch(UI.error);
  });
  root.append(UI.pageHead('اليخوت المتاحة', 'اختر الفترة لترى حالة الطقس البحري وإتاحة كل يخت'), UI.panel(null, filters), results);
  await load();
});
