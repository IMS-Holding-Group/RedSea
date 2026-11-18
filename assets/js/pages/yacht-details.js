/* تفاصيل اليخت، توقع الطقس، والحجز مع الدفع المحاكى */
App.start(async (root, me) => {
  const { el, icon } = UI;
  const id = UI.qs('id');
  if (!/^\d+$/.test(id || '')) { throw new Error('اليخت غير محدد.'); }
  const y = await Api.get(`/api/yachts/${id}`);
  const fc = await Api.get(`/api/weather/forecast?lat=${y.marina_lat}&lng=${y.marina_lng}`);
  const limits = { small: [15, 20, 1.0], medium: [20, 27, 1.5], large: [25, 33, 2.5] }[y.size_class];
  const cls = (h) => {
    const r = Math.max(h.wind / limits[0], h.gust / limits[1], h.wave / limits[2]);
    return r < 0.8 ? 'safe' : (r <= 1 ? 'caution' : 'unsafe');
  };
  const photos = y.photos.map((src) => el('div', { class: 'yacht-photo' }, el('img', { src, alt: y.name })));
  const gallery = el('div', { class: `gallery${photos.length ? '' : ' gallery-empty'}` }, photos[0] || el('div', { class: 'yacht-photo' }, icon('sailboat')), photos[1] || el('div', { class: 'yacht-photo' }, icon('water')));
  const upcoming = fc.hours.filter((h) => h.time >= Dates.nowIso().slice(0, 13)).slice(0, 48);
  const strip = el('div', { class: 'weather-strip' }, upcoming.filter((h, i) => i % 3 === 0).map((h) => el('div', { class: `wx ${cls(h)}` },
    el('strong', {}, Dates.element(h.time, true)), el('div', { text: Dates.timeText(h.time) }),
    el('div', {}, icon('wind'), ` ${UI.num(h.wind)} عقدة`), el('div', {}, icon('water'), ` ${UI.num(h.wave)} م`))));
  const windChart = el('div', { class: 'chart' });
  const weatherPanel = UI.panel('توقع الطقس البحري عند المرسى (48 ساعة)',
    el('div', { class: `notice${fc.source === 'simulated' ? ' notice-warning' : ''}` }, icon('circle-info'),
      `مصدر البيانات: ${UI.TEXT.source[fc.source]}. حدود الأمان لفئة هذا اليخت (${UI.TEXT.size[y.size_class]}): رياح حتى ${limits[0]} عقدة، هبات حتى ${limits[1]} عقدة، موج حتى ${limits[2]} م.`),
    strip, el('h3', { text: 'سرعة الرياح المتوقعة (عقدة)' }), windChart);

  const q = new URLSearchParams(location.search);
  const startIso = q.get('start') || Dates.addHours(Dates.nowIso().slice(0, 13) + ':00:00', 26);
  const zones = [['', 'بدون تحديد']].concat(y.cruising_zones.map((z) => [z.id, z.name]));
  const bookForm = el('form', { class: 'form-grid', novalidate: true },
    UI.field({ name: 'date', label: 'التاريخ', type: 'date', required: true, value: Dates.toInput(startIso, true) }),
    UI.field({ name: 'time', label: 'وقت الانطلاق', type: 'time', required: true, value: Dates.toInput(startIso).slice(11, 16) }),
    UI.field({ name: 'hours', label: 'المدة (ساعات)', type: 'number', min: 2, max: 12, required: true, value: q.get('hours') || 4 }),
    UI.field({ name: 'guests', label: 'عدد الضيوف', type: 'number', min: 1, max: y.capacity, required: true, value: Math.min(+(q.get('guests') || 2), y.capacity) }),
    UI.field({ name: 'purpose', label: 'غرض الرحلة', type: 'select', options: Object.entries(UI.TEXT.purpose) }),
    UI.field({ name: 'route_zone_id', label: 'منطقة الإبحار', type: 'select', options: zones }),
    el('div', { class: 'actions full' }, el('button', { class: 'btn btn-secondary', type: 'submit' }, icon('cloud-sun'), 'تحقق من الطقس والإتاحة')));
  const result = el('div');
  function period() {
    const d = UI.read(bookForm);
    const start = Dates.fromInput(`${d.date}T${d.time}`);
    return { d, start, end: start ? Dates.addHours(start, +d.hours) : null };
  }
  async function check() {
    const { d, start, end } = period();
    if (!start || !(+d.hours >= 2 && +d.hours <= 12)) { throw new Error('تحقق من التاريخ والوقت والمدة.'); }
    result.replaceChildren(UI.loading());
    const r = await Api.get(`/api/weather/assess?yacht_id=${y.id}&start=${start}&end=${end}`);
    const w = r.weather;
    const box = el('div', { class: 'panel' },
      el('div', { class: 'panel-head' }, el('h3', {}, 'الفترة: ', Dates.element(start), ' إلى ', Dates.element(end)), UI.badge('weather', w.status)));
    if (w.max_ratio !== null) { box.appendChild(el('p', { class: 'small muted', text: `أعلى نسبة استهلاك لحدود الأمان خلال الرحلة: ${Math.round(w.max_ratio * 100)} بالمئة` })); }
    if (w.status === 'unknown') { box.appendChild(el('div', { class: 'notice' }, icon('circle-info'), 'الفترة أبعد من نطاق التوقع المتاح. يمكن الحجز وسيُعاد تقييم الطقس تلقائياً قبل الرحلة بـ 48 ساعة.')); }
    if (r.reasons.length) {
      box.appendChild(el('div', { class: 'notice notice-danger' }, icon('ban'), el('div', {}, r.reasons.map((t) => el('div', { text: t })))));
      result.replaceChildren(box);
      return;
    }
    box.appendChild(el('p', { class: 'price', text: `الإجمالي: ${UI.money(r.total)} (${r.hours} ساعات)` }));
    let ack = null;
    if (w.status === 'caution') {
      box.appendChild(el('div', { class: 'notice notice-warning' }, icon('wind'), 'الطقس المتوقع قريب من حدود الأمان لهذا اليخت. قد تكون الرحلة أقل راحة، ويحق للربان تعديل المسار.'));
      ack = UI.field({ name: 'ack', label: 'اطلعت على تحذير الطقس وأرغب في المتابعة', type: 'checkbox' });
      box.appendChild(ack);
    }
    if (!me) {
      box.appendChild(el('a', { class: 'btn', href: `/login?next=${encodeURIComponent(location.pathname + location.search)}`, text: 'سجل الدخول لإتمام الحجز' }));
    } else if (me.role !== 'tourist') {
      box.appendChild(el('p', { class: 'muted', text: 'الحجز متاح لحسابات السياح فقط.' }));
    } else {
      box.appendChild(UI.button('متابعة إلى الدفع', () => { pay(d, start, end, r.total, ack ? ack.querySelector('input').checked : false); }, '', 'credit-card'));
    }
    result.replaceChildren(box);
  }
  function pay(d, start, end, total, ackCaution) {
    const f = el('form', { class: 'form-grid', novalidate: true },
      el('div', { class: 'notice full' }, icon('shield-halved'), 'هذا دفع محاكى لأغراض العرض. لا يتم طلب أو تخزين أي بيانات بطاقة.'),
      UI.field({ name: 'payer_name', label: 'اسم حامل البطاقة', required: true, full: true, value: me.full_name }),
      el('p', { class: 'price full', text: `المبلغ: ${UI.money(total)}` }));
    UI.modal('الدفع وتأكيد الطلب', f, [{ text: 'ادفع وأرسل الطلب', onClick: async (close) => {
      try {
        const res = await Api.post('/api/bookings', { yacht_id: y.id, start_at: start, end_at: end, guests: +d.guests, purpose: d.purpose, route_zone_id: d.route_zone_id || null, payer_name: UI.read(f).payer_name, ack_caution: ackCaution });
        close();
        UI.ok(`تم إرسال طلب الحجز ${res.reference} إلى المالك.`);
        setTimeout(() => { location.href = '/my-bookings'; }, 1200);
      } catch (e) {
        UI.error(e);
      }
    } }]);
  }
  bookForm.addEventListener('submit', (e) => {
    e.preventDefault();
    check().catch(UI.error);
  });
  root.append(
    UI.pageHead(y.name, `${y.marina_name} - ${y.marina_city}`),
    gallery,
    el('div', { class: 'grid grid-2' },
      UI.panel('المواصفات', el('ul', { class: 'specs' },
        el('li', {}, icon('anchor'), y.type_label),
        el('li', {}, icon('ruler-horizontal'), `الطول ${y.length_m} م`),
        el('li', {}, icon('arrows-left-right'), `العرض ${y.beam_m} م`),
        el('li', {}, icon('arrow-down'), `الغاطس ${y.draft_m} م`),
        el('li', {}, icon('users'), `السعة ${y.capacity}`),
        el('li', {}, icon('bed'), `الكبائن ${y.cabins}`),
        el('li', {}, icon('layer-group'), `الفئة ${UI.TEXT.size[y.size_class]}`)),
        el('p', { text: y.description || '' }),
        el('p', { class: 'price', text: `${UI.money(y.hourly_rate)} / ساعة` }),
        y.status !== 'active' ? UI.badge('yacht', y.status) : null),
      UI.panel('احجز رحلتك', bookForm, result)),
    weatherPanel);
  Charts.line(windChart, upcoming.map((h) => ({ label: Dates.timeText(h.time), value: h.wind })), '', '#13315C');
  if (q.get('start')) { check().catch(UI.error); }
});
