/* إدارة يخوت المالك: البيانات، الصور، جهاز التتبع، وطلب المرابط */
App.start(async (root) => {
  const { el, icon } = UI;
  const marinas = await Api.get('/api/marinas');
  const list = el('div');
  const reservations = el('div');
  let yachts = [];
  async function load() {
    const [ys, rs] = await Promise.all([Api.get('/api/owner/yachts'), Api.get('/api/owner/berth-reservations')]);
    yachts = ys;
    list.replaceChildren(ys.length ? UI.table(['اليخت', 'الأبعاد (م)', 'السعة', 'المرسى', 'السعر/ساعة', 'ساعات المحرك', 'الامتثال', 'الحالة', 'الإجراءات'], ys.map((y) => [
      el('span', {}, y.name, el('div', { class: 'small muted ltr', text: y.registration_no })),
      el('span', { class: 'ltr', text: `${y.length_m} x ${y.beam_m} x ${y.draft_m}` }), y.capacity, y.marina_name, UI.money(y.hourly_rate),
      UI.num(y.engine_hours), `${y.compliance}%`, UI.badge('yacht', y.status),
      el('div', { class: 'actions' },
        UI.button('تعديل', () => { edit(y); }, 'btn-sm btn-ghost', 'pen'),
        UI.button('الصور', () => { photos(y); }, 'btn-sm btn-ghost', 'image'),
        UI.button('جهاز التتبع', () => { device(y); }, 'btn-sm btn-ghost', 'satellite-dish'),
        UI.button('طلب مربط', () => { berth(y); }, 'btn-sm btn-secondary', 'anchor'))])) : UI.empty('لم تضف أي يخت بعد.', 'sailboat'));
    reservations.replaceChildren(rs.length ? UI.table(['اليخت', 'المرسى', 'المربط', 'من', 'إلى', 'التكلفة', 'الحالة'], rs.map((r) => [r.yacht_name, r.marina_name, r.code, Dates.element(r.start_at, true), Dates.element(r.end_at, true), UI.money(r.total_halalas / 100), UI.badge('berth', r.status)])) : UI.empty('لا توجد طلبات مرابط.', 'anchor'));
  }
  function edit(y) {
    const v = y || {};
    const defs = [
      { name: 'name', label: 'اسم اليخت', required: true, value: v.name },
      { name: 'registration_no', label: 'رقم التسجيل', required: true, value: v.registration_no },
      { name: 'type', label: 'النوع', type: 'select', value: v.type, options: [['motor', 'يخت بمحرك'], ['sailing', 'شراعي'], ['catamaran', 'مزدوج البدن']] },
      { name: 'home_marina_id', label: 'المرسى الأساسي', type: 'select', value: v.marina_id, options: marinas.map((m) => [m.id, m.name]) },
      { name: 'length_m', label: 'الطول (م)', type: 'number', step: '0.1', min: 4, max: 120, required: true, value: v.length_m, hint: 'أقل من 12 صغير، حتى 24 متوسط، وأكبر من ذلك كبير' },
      { name: 'beam_m', label: 'العرض (م)', type: 'number', step: '0.1', min: 1.5, max: 30, required: true, value: v.beam_m },
      { name: 'draft_m', label: 'الغاطس (م)', type: 'number', step: '0.1', min: 0.3, max: 8, required: true, value: v.draft_m },
      { name: 'capacity', label: 'السعة', type: 'number', min: 1, max: 200, required: true, value: v.capacity },
      { name: 'cabins', label: 'عدد الكبائن', type: 'number', min: 0, max: 30, required: true, value: v.cabins === undefined ? 0 : v.cabins },
      { name: 'hourly_rate', label: 'السعر بالساعة (ر.س)', type: 'number', min: 50, max: 100000, required: true, value: v.hourly_rate },
      { name: 'status', label: 'الحالة', type: 'select', value: v.status === 'maintenance' ? 'active' : v.status, options: [['active', 'نشط'], ['draft', 'مسودة'], ['suspended', 'موقوف']] },
      { name: 'description', label: 'الوصف', type: 'textarea', full: true, max: 1000, value: v.description }
    ];
    let close = null;
    const f = UI.form(defs, async (d) => {
      if (y) {
        await Api.put(`/api/owner/yachts/${y.id}`, d);
      } else {
        await Api.post('/api/owner/yachts', d);
      }
      close();
      UI.ok(y ? 'تم حفظ التعديلات.' : 'تمت إضافة اليخت مع خطط الصيانة الافتراضية.');
      await load();
    });
    close = UI.modal(y ? `تعديل ${y.name}` : 'إضافة يخت', f, []);
  }
  function photos(y) {
    const thumbs = el('div', { class: 'thumbs' });
    const draw = (ids) => {
      thumbs.replaceChildren(...(ids.length ? ids.map((pid) => el('figure', {}, el('img', { src: `/media/yachts/${pid}`, alt: '' }),
        el('button', { class: 'btn btn-danger btn-sm btn-icon', type: 'button', 'aria-label': 'حذف', onclick: async () => {
          try {
            await Api.del(`/api/owner/yachts/${y.id}/photos/${pid}`);
            y.photo_ids = y.photo_ids.filter((p) => p !== pid);
            draw(y.photo_ids);
          } catch (e) {
            UI.error(e);
          }
        } }, icon('trash')))) : [el('p', { class: 'muted', text: 'لا توجد صور.' })]));
    };
    draw(y.photo_ids);
    const input = el('input', { type: 'file', accept: 'image/jpeg,image/png,image/webp' });
    const body = el('div', {}, thumbs, el('br'), el('div', { class: 'field' }, el('label', { text: 'إضافة صورة (JPG أو PNG أو WEBP حتى 3 ميجابايت، 5 صور كحد أقصى)' }), input));
    UI.modal(`صور ${y.name}`, body, [{ text: 'رفع الصورة', onClick: async () => {
      if (!input.files.length) {
        UI.error('اختر صورة أولاً.');
        return;
      }
      const fd = new FormData();
      fd.append('photo', input.files[0]);
      try {
        const r = await Api.upload(`/api/owner/yachts/${y.id}/photos`, fd);
        y.photo_ids.push(r.id);
        input.value = '';
        draw(y.photo_ids);
        UI.ok('تم رفع الصورة.');
      } catch (e) {
        UI.error(e);
      }
    } }], () => { load().catch(UI.error); });
  }
  function device(y) {
    const body = el('div', {},
      el('p', {}, 'رمز الجهاز: ', el('strong', { class: 'ltr', text: y.device ? y.device.device_code : 'غير مسجل' })),
      el('p', {}, 'آخر اتصال: ', y.device && y.device.last_seen_at ? Dates.element(y.device.last_seen_at) : '-'),
      el('div', { class: 'notice notice-warning' }, icon('key'), 'إنشاء مفتاح جديد يلغي المفتاح الحالي فوراً. المفتاح الجديد يظهر مرة واحدة فقط، انسخه إلى إعدادات الجهاز.'));
    UI.modal(`جهاز تتبع ${y.name}`, body, [{ text: 'إنشاء مفتاح جديد', onClick: async () => {
      try {
        const r = await Api.post(`/api/owner/yachts/${y.id}/device`);
        body.appendChild(el('div', { class: 'key-box ltr', text: r.api_key }));
        UI.ok('تم إنشاء المفتاح.');
      } catch (e) {
        UI.error(e);
      }
    } }]);
  }
  function berth(y) {
    const tomorrow = Dates.toInput(new Date(Date.now() + 86400000).toISOString().slice(0, 19), true);
    const after = Dates.toInput(new Date(Date.now() + 4 * 86400000).toISOString().slice(0, 19), true);
    const f = el('form', { class: 'form-grid', novalidate: true },
      UI.field({ name: 'marina_id', label: 'المرسى', type: 'select', options: [['', 'كل المراسي']].concat(marinas.map((m) => [m.id, m.name])) }),
      UI.field({ name: 'notes', label: 'ملاحظات', maxlength: 300 }),
      UI.field({ name: 'start', label: 'من تاريخ', type: 'date', value: tomorrow, required: true }),
      UI.field({ name: 'end', label: 'إلى تاريخ', type: 'date', value: after, required: true }),
      el('div', { class: 'actions full' }, el('button', { class: 'btn btn-secondary', type: 'submit' }, icon('magnifying-glass'), 'ابحث عن مربط مناسب')));
    const out = el('div');
    const close = UI.modal(`طلب مربط لـ ${y.name}`, el('div', {}, el('p', { class: 'small muted', text: `أبعاد اليخت: طول ${y.length_m} م، عرض ${y.beam_m} م، غاطس ${y.draft_m} م. تُطبق هوامش أمان 0.5 م للطول و0.3 م للعرض والغاطس.` }), f, out), []);
    f.addEventListener('submit', async (e) => {
      e.preventDefault();
      const d = UI.read(f);
      const start = Dates.fromInput(d.start);
      const end = Dates.fromInput(d.end);
      if (!start || !end || end <= start) {
        UI.error('تحقق من التواريخ.');
        return;
      }
      try {
        const res = await Api.get(`/api/berths/match?yacht_id=${y.id}&start=${start}&end=${end}${d.marina_id ? '&marina_id=' + d.marina_id : ''}`);
        out.replaceChildren(res.length ? UI.table(['المرسى', 'المربط', 'الأبعاد', 'الفائض', 'التكلفة', ''], res.slice(0, 8).map((b, i) => [
          b.marina_name, el('span', {}, b.code, i === 0 ? el('span', { class: 'badge badge-success', text: 'الأنسب' }) : null),
          el('span', { class: 'ltr', text: `${b.max_length_m} x ${b.max_beam_m} x ${b.max_draft_m}` }), `${b.waste_m} م`, UI.money(b.total),
          UI.button('طلب', async () => {
            try {
              await Api.post('/api/berth-reservations', { yacht_id: y.id, berth_id: b.id, start_at: start, end_at: end, notes: d.notes });
              close();
              UI.ok('تم إرسال طلب المربط إلى مدير المرسى.');
              await load();
            } catch (err) {
              UI.error(err);
            }
          }, 'btn-sm')])) : UI.empty('لا يوجد مربط متاح يناسب أبعاد اليخت في هذه الفترة.', 'anchor'));
      } catch (err) {
        UI.error(err);
      }
    });
  }
  root.append(UI.pageHead('يخوتي', 'أضف يخوتك وأدر صورها وأجهزة تتبعها ومرابطها', UI.button('إضافة يخت', () => { edit(null); }, '', 'plus')),
    list, el('br'), UI.panel('طلبات المرابط', reservations));
  await load();
});
