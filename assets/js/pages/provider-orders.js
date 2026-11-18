/* أوامر العمل لمزود الخدمة: تقديم العروض والتنفيذ */
App.start(async (root) => {
  const { el, icon } = UI;
  const availBox = el('div');
  const mineBox = el('div');
  async function load() {
    const d = await Api.get('/api/provider/work-orders');
    availBox.replaceChildren(d.available.length ? UI.table(['الأمر', 'اليخت', 'المرسى', 'النوع', 'الأولوية', 'الاستحقاق', 'عرضي', ''], d.available.map((w) => [
      el('div', {}, w.title, el('div', { class: 'small muted', text: w.description || '' })), `${w.yacht_name} (${w.length_m} م)`, w.marina_name,
      UI.TEXT.service[w.service_type], UI.badge('priority', w.priority), Dates.element(w.due_at, true),
      w.my_quote ? UI.money(w.my_quote.amount) : '-',
      UI.button(w.my_quote ? 'تعديل العرض' : 'تقديم عرض', () => { quote(w); }, 'btn-sm', 'file-invoice-dollar')])) : UI.empty('لا توجد أوامر متاحة حالياً.', 'inbox'));
    mineBox.replaceChildren(d.assigned.length ? UI.table(['الأمر', 'اليخت', 'المبلغ', 'الاستحقاق', 'الحالة', ''], d.assigned.map((w) => [
      w.title, w.yacht_name, UI.money(w.quote), Dates.element(w.due_at, true), UI.badge('wo', w.status),
      w.status === 'assigned' ? UI.button('بدء التنفيذ', () => { start(w); }, 'btn-sm', 'play') : (w.status === 'in_progress' ? UI.button('إنهاء', () => { complete(w); }, 'btn-sm btn-success', 'check') : el('span', { class: 'small muted', text: w.completion_notes || '' }))])) : UI.empty('لا توجد أوامر مسندة إليك.', 'clipboard'));
  }
  function quote(w) {
    let close = null;
    const v = w.my_quote || {};
    const f = UI.form([
      { name: 'amount', label: 'المبلغ (ر.س)', type: 'number', min: 10, max: 1000000, required: true, value: v.amount },
      { name: 'eta_days', label: 'مدة التنفيذ (أيام)', type: 'number', min: 1, max: 90, required: true, value: v.eta_days },
      { name: 'notes', label: 'ملاحظات', type: 'textarea', full: true, max: 300, value: v.notes }
    ], async (d) => {
      await Api.post(`/api/provider/work-orders/${w.id}/quote`, d);
      close();
      UI.ok('تم إرسال العرض للمالك.');
      await load();
    }, 'إرسال العرض');
    close = UI.modal(`عرض سعر: ${w.title}`, f, []);
  }
  async function start(w) {
    try {
      await Api.post(`/api/provider/work-orders/${w.id}/start`);
      await load();
    } catch (e) {
      UI.error(e);
    }
  }
  function complete(w) {
    let close = null;
    const f = UI.form([{ name: 'completion_notes', label: 'ملاحظات الإنجاز', type: 'textarea', required: true, full: true, max: 1000 }], async (d) => {
      await Api.post(`/api/provider/work-orders/${w.id}/complete`, d);
      close();
      UI.ok('تم إنهاء أمر العمل.');
      await load();
    }, 'إنهاء');
    close = UI.modal(`إنهاء: ${w.title}`, f, []);
  }
  root.append(UI.pageHead('أوامر العمل', 'قدم عروضك على الأوامر المطابقة لخدماتك، ونفذ الأوامر المسندة إليك'), UI.panel('أوامر متاحة', availBox), UI.panel('أوامري', mineBox));
  await load();
});
