/* الصيانة: الخطط الدورية وأوامر العمل وعروض الأسعار */
App.start(async (root) => {
  const { el, icon } = UI;
  const plansBox = el('div');
  const ordersBox = el('div');
  let yachts = [];
  const serviceOpts = Object.entries(UI.TEXT.service);
  function progress(p) {
    const parts = [];
    if (p.hours_ratio !== null) {
      const pct = Math.round(p.hours_ratio * 100);
      const bar = el('span', { class: pct >= 100 ? 'over' : (pct >= 90 ? 'warn' : '') });
      bar.style.width = `${Math.min(pct, 100)}%`;
      parts.push(el('div', { class: 'small', text: `ساعات التشغيل: ${pct}% من ${UI.num(p.interval_engine_hours)} ساعة` }), el('div', { class: 'progress' }, bar));
    }
    if (p.days_left !== null) { parts.push(el('div', { class: `small${p.days_left <= 7 ? ' muted' : ''}` }, `الموعد: `, Dates.element(p.due_at, true), ` (متبقٍ ${Math.max(0, p.days_left)} يوم)`)); }
    return el('div', {}, parts);
  }
  async function load() {
    const [plans, orders, ys] = await Promise.all([Api.get('/api/owner/maintenance/plans'), Api.get('/api/owner/work-orders'), Api.get('/api/owner/yachts')]);
    yachts = ys;
    plansBox.replaceChildren(plans.length ? UI.table(['اليخت', 'المهمة', 'النوع', 'التقدم', ''], plans.map((p) => [
      p.yacht_name, p.task_name, UI.TEXT.service[p.service_type] || p.service_type, progress(p),
      el('div', { class: 'actions' }, UI.button('تعديل', () => { planForm(p); }, 'btn-sm btn-ghost', 'pen'),
        UI.button('حذف', async () => {
          if (!await UI.confirm('حذف الخطة', `حذف خطة ${p.task_name}؟`, 'حذف', 'btn-danger')) { return; }
          try {
            await Api.del(`/api/owner/maintenance/plans/${p.id}`);
            await load();
          } catch (e) {
            UI.error(e);
          }
        }, 'btn-sm btn-ghost', 'trash'))])) : UI.empty('لا توجد خطط صيانة.', 'calendar-check'));
    ordersBox.replaceChildren(orders.length ? UI.table(['الأمر', 'اليخت', 'الأولوية', 'الحالة', 'الاستحقاق', 'المزود / العروض', ''], orders.map((w) => [
      el('div', {}, w.title, w.auto_generated ? el('span', { class: 'badge badge-info', text: 'تلقائي' }) : null, el('div', { class: 'small muted', text: w.description || '' })),
      w.yacht_name, UI.badge('priority', w.priority), UI.badge('wo', w.status), Dates.element(w.due_at, true),
      w.provider_name ? el('div', {}, w.provider_name, el('div', { class: 'small muted', text: w.quote ? UI.money(w.quote) : '' })) : (w.quotes.length ? `${w.quotes.length} عرض` : '-'),
      orderActions(w)])) : UI.empty('لا توجد أوامر عمل.', 'screwdriver-wrench'));
  }
  function orderActions(w) {
    const box = el('div', { class: 'actions' });
    const open = w.quotes.filter((q) => q.status === 'submitted');
    if (['open', 'quoted'].includes(w.status) && open.length) { box.appendChild(UI.button('العروض', () => { quotes(w); }, 'btn-sm', 'file-invoice-dollar')); }
    if (['open', 'quoted', 'assigned'].includes(w.status)) {
      box.appendChild(UI.button('إلغاء', async () => {
        if (!await UI.confirm('إلغاء الأمر', `إلغاء أمر العمل ${w.title}؟`, 'إلغاء الأمر', 'btn-danger')) { return; }
        try {
          await Api.post(`/api/owner/work-orders/${w.id}/cancel`);
          await load();
        } catch (e) {
          UI.error(e);
        }
      }, 'btn-sm btn-ghost', 'xmark'));
    }
    if (w.status === 'completed' && w.completion_notes) { box.appendChild(el('span', { class: 'small muted', text: w.completion_notes })); }
    return box;
  }
  function quotes(w) {
    const close = UI.modal(`عروض ${w.title}`, UI.table(['المزود', 'المبلغ', 'المدة', 'الملاحظات', ''], w.quotes.filter((q) => q.status === 'submitted').map((q) => [
      q.provider_name, UI.money(q.amount), `${q.eta_days} يوم`, q.notes || '-',
      UI.button('قبول', async () => {
        try {
          await Api.post(`/api/owner/work-orders/${w.id}/accept-quote`, { quote_id: q.id });
          close();
          UI.ok('تم إسناد الأمر للمزود.');
          await load();
        } catch (e) {
          UI.error(e);
        }
      }, 'btn-sm btn-success')])), []);
  }
  function planForm(p) {
    const v = p || {};
    let close = null;
    const defs = [
      { name: 'yacht_id', label: 'اليخت', type: 'select', value: v.yacht_id, options: yachts.map((y) => [y.id, y.name]) },
      { name: 'service_type', label: 'نوع الخدمة', type: 'select', value: v.service_type, options: serviceOpts },
      { name: 'task_name', label: 'اسم المهمة', required: true, full: true, value: v.task_name },
      { name: 'interval_engine_hours', label: 'كل (ساعة تشغيل)', type: 'number', min: 1, max: 10000, value: v.interval_engine_hours },
      { name: 'interval_days', label: 'أو كل (يوم)', type: 'number', min: 1, max: 3650, value: v.interval_days }
    ];
    const f = UI.form(defs, async (d) => {
      if (p) {
        await Api.put(`/api/owner/maintenance/plans/${p.id}`, d);
      } else {
        await Api.post('/api/owner/maintenance/plans', d);
      }
      close();
      await load();
    });
    if (p) { f.elements.yacht_id.disabled = true; }
    close = UI.modal(p ? 'تعديل خطة' : 'خطة صيانة جديدة', f, []);
  }
  function orderForm() {
    let close = null;
    const due = Dates.toInput(new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 19), true);
    const f = UI.form([
      { name: 'yacht_id', label: 'اليخت', type: 'select', options: yachts.map((y) => [y.id, y.name]) },
      { name: 'service_type', label: 'نوع الخدمة', type: 'select', options: serviceOpts },
      { name: 'title', label: 'العنوان', required: true, full: true },
      { name: 'priority', label: 'الأولوية', type: 'select', value: 'normal', options: Object.entries(UI.LABELS.priority).map(([k, x]) => [k, x[0]]) },
      { name: 'due_at', label: 'تاريخ الاستحقاق', type: 'date', required: true, value: due },
      { name: 'description', label: 'الوصف', type: 'textarea', full: true, max: 1000 }
    ], async (d) => {
      d.due_at = Dates.fromInput(d.due_at);
      await Api.post('/api/owner/work-orders', d);
      close();
      UI.ok('تم إنشاء أمر العمل وإشعار مزودي الخدمة.');
      await load();
    }, 'إنشاء');
    close = UI.modal('أمر عمل جديد', f, []);
  }
  root.append(UI.pageHead('الصيانة', 'تُنشأ أوامر العمل تلقائياً عند بلوغ 90 بالمئة من فاصل الساعات أو قبل الموعد بـ 7 أيام',
    UI.button('خطة جديدة', () => { planForm(null); }, 'btn-secondary', 'calendar-plus'), UI.button('أمر عمل جديد', orderForm, '', 'plus')),
  UI.panel('أوامر العمل', ordersBox), UI.panel('خطط الصيانة الدورية', plansBox));
  await load();
});
