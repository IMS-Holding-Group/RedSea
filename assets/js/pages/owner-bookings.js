/* حجوزات يخوت المالك: الموافقة والرفض وبدء الرحلة وإنهاؤها */
App.start(async (root) => {
  const { el, icon } = UI;
  const filter = UI.field({ name: 'status', label: 'تصفية بالحالة', type: 'select', options: [['', 'الكل']].concat(Object.entries(UI.LABELS.booking).map(([k, v]) => [k, v[0]])) });
  const list = el('div');
  let rows = [];
  async function load() {
    rows = await Api.get('/api/owner/bookings');
    render();
  }
  function render() {
    const s = filter.querySelector('select').value;
    const shown = rows.filter((b) => !s || b.status === s);
    list.replaceChildren(shown.length ? UI.table(['المرجع', 'اليخت', 'السائح', 'الفترة', 'الضيوف', 'الغرض', 'المبلغ', 'الحالة', 'الإجراءات'], shown.map((b) => [
      el('span', { class: 'ltr', text: b.reference }), b.yacht_name, b.tourist_name,
      el('div', {}, Dates.element(b.start_at), el('div', {}, Dates.element(b.end_at))),
      b.guests, UI.TEXT.purpose[b.purpose] || '-', UI.money(b.total),
      el('div', {}, UI.badge('booking', b.status), b.permit && ['confirmed', 'in_progress'].includes(b.status) ? el('div', {}, UI.badge('permit', b.permit)) : null,
        b.weather_status_at_booking ? el('div', {}, UI.badge('weather', b.weather_status_at_booking)) : null),
      actions(b)])) : UI.empty('لا توجد حجوزات.', 'calendar'));
  }
  const act = async (url, data, msg) => {
    try {
      const r = await Api.post(url, data);
      UI.ok(msg);
      await load();
      return r;
    } catch (e) {
      UI.error(e);
      return null;
    }
  };
  function actions(b) {
    const box = el('div', { class: 'actions' });
    if (b.status === 'pending') {
      box.append(UI.button('موافقة', () => { act(`/api/owner/bookings/${b.id}/decision`, { decision: 'approve' }, 'تم تأكيد الحجز وطلب تصريح الإبحار.'); }, 'btn-sm btn-success', 'check'),
        UI.button('رفض', async () => { if (await UI.confirm('رفض الحجز', 'سيتم رفض الحجز واسترداد المبلغ للسائح كاملاً.', 'رفض', 'btn-danger')) { act(`/api/owner/bookings/${b.id}/decision`, { decision: 'reject' }, 'تم رفض الحجز.'); } }, 'btn-sm btn-ghost', 'xmark'));
    }
    if (b.status === 'confirmed') { box.appendChild(UI.button('بدء الرحلة', () => { act(`/api/owner/bookings/${b.id}/start`, {}, 'بدأت الرحلة.'); }, 'btn-sm', 'play')); }
    if (b.status === 'in_progress') {
      box.append(el('a', { class: 'btn btn-sm btn-secondary', href: `/trip-live?id=${b.id}` }, icon('map'), 'تتبع'),
        UI.button('إنهاء الرحلة', () => { complete(b); }, 'btn-sm btn-success', 'flag-checkered'));
    }
    return box;
  }
  function complete(b) {
    const planned = Math.ceil(Dates.hoursBetween(b.start_at, b.end_at));
    const f = el('form', { class: 'form-grid', novalidate: true }, UI.field({ name: 'engine_hours', label: 'ساعات تشغيل المحرك الفعلية', type: 'number', min: 0, max: 48, value: planned, required: true, full: true, hint: 'تُضاف إلى عداد اليخت وتُستخدم لتوليد أوامر الصيانة تلقائياً.' }));
    UI.modal('إنهاء الرحلة', f, [{ text: 'إنهاء', class: 'btn-success', onClick: async (close) => {
      const r = await act(`/api/owner/bookings/${b.id}/complete`, { engine_hours: +UI.read(f).engine_hours }, 'اكتملت الرحلة.');
      if (r) {
        close();
        if (r.work_orders_created) { UI.toast(`تم إنشاء ${r.work_orders_created} أمر صيانة تلقائي.`); }
      }
    } }]);
  }
  filter.querySelector('select').addEventListener('change', render);
  root.append(UI.pageHead('حجوزات يخوتي', 'وافق على الطلبات وأدر الرحلات من البداية إلى النهاية'), UI.panel(null, el('div', { class: 'filters' }, filter)), list);
  await load();
});
