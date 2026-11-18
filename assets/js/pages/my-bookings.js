/* حجوزات السائح: الإلغاء، إعادة الجدولة عند تعليق الطقس، ومتابعة الرحلة */
App.start(async (root) => {
  const { el, icon } = UI;
  const list = el('div');
  async function load() {
    const [dash, rows] = await Promise.all([Api.get('/api/dashboard/tourist'), Api.get('/api/bookings/mine')]);
    const weatherById = {};
    dash.upcoming.forEach((b) => { weatherById[b.id] = b.weather; });
    if (!rows.length) {
      list.replaceChildren(UI.empty('لا توجد حجوزات بعد.', 'ship'), el('div', { class: 'actions' }, el('a', { class: 'btn', href: '/yachts', text: 'ابحث عن يخت' })));
      return;
    }
    const live = rows.find((b) => b.status === 'in_progress');
    const holds = rows.filter((b) => b.status === 'weather_hold');
    list.replaceChildren(
      live ? el('div', { class: 'notice notice-success' }, icon('location-crosshairs'), el('span', {}, `رحلتك ${live.reference} جارية الآن. `, el('a', { href: `/trip-live?id=${live.id}`, text: 'افتح الخريطة الحية وزر الاستغاثة' }))) : null,
      holds.length ? el('div', { class: 'notice notice-warning' }, icon('triangle-exclamation'), `لديك ${holds.length} حجز معلق بسبب توقع طقس غير آمن. أعد الجدولة إلى فترة آمنة أو ألغِ باسترداد كامل.`) : null,
      el('div', { class: 'grid grid-3' }, UI.stat('الحجوزات القادمة', dash.upcoming.length, 'calendar'), UI.stat('الرحلات المكتملة', dash.completed_count, 'flag-checkered'), UI.stat('المعلقة بسبب الطقس', holds.length, 'wind')),
      el('br'),
      UI.table(['المرجع', 'اليخت', 'البداية', 'النهاية', 'المبلغ', 'الحالة', 'الطقس الآن', 'الإجراءات'], rows.map((b) => [
        el('span', { class: 'ltr', text: b.reference }),
        el('span', {}, b.yacht_name, el('div', { class: 'small muted', text: b.marina_name })),
        Dates.element(b.start_at), Dates.element(b.end_at), UI.money(b.total),
        el('div', {}, UI.badge('booking', b.status), b.permit && b.status === 'confirmed' ? el('div', {}, UI.badge('permit', b.permit)) : null),
        weatherById[b.id] ? UI.badge('weather', weatherById[b.id]) : '-',
        actions(b)
      ])));
  }
  function actions(b) {
    const box = el('div', { class: 'actions' });
    if (b.status === 'in_progress') { box.appendChild(el('a', { class: 'btn btn-sm', href: `/trip-live?id=${b.id}` }, icon('map'), 'تتبع')); }
    if (b.status === 'weather_hold') { box.appendChild(UI.button('إعادة جدولة', () => { reschedule(b).catch(UI.error); }, 'btn-sm', 'calendar-days')); }
    if (['pending', 'confirmed', 'weather_hold'].includes(b.status)) { box.appendChild(UI.button('إلغاء', () => { cancel(b).catch(UI.error); }, 'btn-sm btn-ghost', 'xmark')); }
    if (b.status === 'completed') { box.appendChild(el('a', { class: 'btn btn-sm btn-ghost', href: `/trip-live?id=${b.id}`, text: 'مسار الرحلة' })); }
    return box;
  }
  async function cancel(b) {
    const hours = Dates.hoursBetween(Dates.nowIso(), b.start_at);
    const policy = b.status === 'weather_hold' ? 'استرداد كامل لأن التعليق بسبب الطقس.' : (hours >= 48 ? 'استرداد كامل (قبل 48 ساعة أو أكثر).' : (hours >= 24 ? 'استرداد 50 بالمئة (بين 24 و48 ساعة).' : 'لا يوجد استرداد (أقل من 24 ساعة).'));
    if (!await UI.confirm('إلغاء الحجز', `هل تريد إلغاء الحجز ${b.reference}؟ ${policy}`, 'تأكيد الإلغاء', 'btn-danger')) { return; }
    const r = await Api.post(`/api/bookings/${b.id}/cancel`);
    UI.ok(`تم الإلغاء. المبلغ المسترد: ${UI.money(r.refund)}`);
    await load();
  }
  async function reschedule(b) {
    const slots = await Api.get(`/api/bookings/${b.id}/slots`);
    const body = el('div');
    if (!slots.length) {
      body.appendChild(UI.empty('لا توجد فترات آمنة متاحة خلال الأيام السبعة القادمة. يمكنك الإلغاء باسترداد كامل.', 'wind'));
      UI.modal('إعادة الجدولة', body, []);
      return;
    }
    body.appendChild(el('p', { text: 'أقرب الفترات الآمنة بنفس مدة رحلتك:' }));
    const close = UI.modal('إعادة الجدولة', body, []);
    slots.forEach((s) => {
      body.appendChild(el('div', { class: 'notice notice-success' }, icon('sun'), el('div', { class: 'actions' }, Dates.element(s.start_at), ' إلى ', Dates.element(s.end_at),
        UI.button('اختيار', async () => {
          try {
            await Api.post(`/api/bookings/${b.id}/reschedule`, s);
            close();
            UI.ok('تمت إعادة جدولة الحجز.');
            await load();
          } catch (e) {
            UI.error(e);
          }
        }, 'btn-sm btn-success'))));
    });
  }
  root.append(UI.pageHead('حجوزاتي', 'تابع حالة حجوزاتك وتقييم الطقس لكل رحلة', el('a', { class: 'btn', href: '/yachts' }, icon('plus'), 'حجز جديد')), list);
  await load();
});
