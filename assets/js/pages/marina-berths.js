/* إدارة المرابط وقرارات طلبات الرسو */
App.start(async (root) => {
  const { el, icon } = UI;
  const marinas = await Api.get('/api/marina/mine');
  if (!marinas.length) {
    root.appendChild(UI.empty('لا توجد مراسٍ مسندة إليك.', 'anchor'));
    return;
  }
  const select = UI.field({ name: 'marina', label: 'المرسى', type: 'select', options: marinas.map((m) => [m.id, m.name]) });
  const grid = el('div');
  const requests = el('div');
  const mid = () => +select.querySelector('select').value;
  async function load() {
    const [berths, res] = await Promise.all([Api.get(`/api/marinas/${mid()}/berths`), Api.get('/api/marina/reservations')]);
    grid.replaceChildren(el('div', { class: 'berth-grid' }, berths.map((b) => {
      const state = b.status !== 'available' ? b.status : (b.occupied_by ? 'occupied' : 'available');
      return el('div', { class: `berth ${state}`, role: 'button', tabindex: 0, onclick: () => { berthForm(b); } },
        el('strong', { text: b.code }), el('div', { class: 'ltr', text: `${b.max_length_m} x ${b.max_beam_m} x ${b.max_draft_m}` }),
        el('div', { text: b.occupied_by ? b.occupied_by.yacht_name : UI.LABELS.berth[b.status][0] }), el('div', { class: 'muted', text: UI.money(b.daily_rate) }));
    })), el('div', { class: 'legend' }, ['available:متاح', 'occupied:مشغول', 'maintenance:صيانة', 'closed:مغلق'].map((s) => {
      const [k, t] = s.split(':');
      return el('span', {}, el('b', { class: `berth ${k}` }), t);
    })));
    const mine = res.filter((r) => r.marina_id === mid());
    requests.replaceChildren(mine.length ? UI.table(['اليخت', 'المالك', 'المربط', 'من', 'إلى', 'التكلفة', 'الحالة', ''], mine.map((r) => [
      el('span', {}, r.yacht_name, el('div', { class: 'small muted', text: `${r.length_m} م` })), r.owner_name, r.code,
      Dates.element(r.start_at, true), Dates.element(r.end_at, true), UI.money(r.total),
      el('div', {}, UI.badge('berth', r.status), r.notes ? el('div', { class: 'small muted', text: r.notes }) : null),
      r.status === 'requested' ? el('div', { class: 'actions' },
        UI.button('اعتماد', () => { decide(r.id, 'approve'); }, 'btn-sm btn-success', 'check'),
        UI.button('رفض', () => { decide(r.id, 'reject'); }, 'btn-sm btn-ghost', 'xmark')) : ''])) : UI.empty('لا توجد طلبات.', 'inbox'));
  }
  async function decide(id, decision) {
    try {
      await Api.post(`/api/marina/reservations/${id}/decision`, { decision });
      UI.ok(decision === 'approve' ? 'تم اعتماد الطلب.' : 'تم رفض الطلب.');
      await load();
    } catch (e) {
      UI.error(e);
    }
  }
  function berthForm(b) {
    const v = b || { has_power: true, has_water: true, status: 'available' };
    let close = null;
    const defs = [
      { name: 'code', label: 'رمز المربط', required: true, value: v.code },
      { name: 'status', label: 'الحالة', type: 'select', value: v.status, options: [['available', 'متاح'], ['maintenance', 'صيانة'], ['closed', 'مغلق']] },
      { name: 'max_length_m', label: 'أقصى طول (م)', type: 'number', step: '0.1', min: 4, max: 150, required: true, value: v.max_length_m },
      { name: 'max_beam_m', label: 'أقصى عرض (م)', type: 'number', step: '0.1', min: 1.5, max: 40, required: true, value: v.max_beam_m },
      { name: 'max_draft_m', label: 'أقصى غاطس (م)', type: 'number', step: '0.1', min: 0.5, max: 12, required: true, value: v.max_draft_m },
      { name: 'daily_rate', label: 'السعر اليومي (ر.س)', type: 'number', min: 10, max: 100000, required: true, value: v.daily_rate },
      { name: 'has_power', label: 'كهرباء', type: 'checkbox', value: v.has_power },
      { name: 'has_water', label: 'ماء', type: 'checkbox', value: v.has_water }
    ];
    const f = UI.form(defs, async (d) => {
      d.marina_id = mid();
      if (b) {
        await Api.put(`/api/marina/berths/${b.id}`, d);
      } else {
        await Api.post('/api/marina/berths', d);
      }
      close();
      UI.ok('تم الحفظ.');
      await load();
    });
    if (b) { f.elements.code.disabled = true; }
    close = UI.modal(b ? `المربط ${b.code}` : 'إضافة مربط', f, []);
  }
  select.querySelector('select').addEventListener('change', () => { load().catch(UI.error); });
  root.append(UI.pageHead('المرابط والطلبات', 'اضغط على أي مربط لتعديل أبعاده وحالته', UI.button('إضافة مربط', () => { berthForm(null); }, '', 'plus')),
    UI.panel(null, el('div', { class: 'filters' }, select)), UI.panel('خريطة المرابط', grid), UI.panel('طلبات الرسو', requests));
  await load();
});
