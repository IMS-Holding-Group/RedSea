/* مراجعة الوثائق واعتماد تصاريح الإبحار */
App.start(async (root) => {
  const { el, icon } = UI;
  const docStatus = UI.field({ name: 's', label: 'حالة الوثيقة', type: 'select', options: [['pending_review', 'بانتظار المراجعة'], ['approved', 'معتمدة'], ['rejected', 'مرفوضة'], ['expired', 'منتهية'], ['all', 'الكل']] });
  const permitStatus = UI.field({ name: 'p', label: 'حالة التصريح', type: 'select', options: [['requested', 'قيد الاعتماد'], ['approved', 'معتمد'], ['rejected', 'مرفوض'], ['all', 'الكل']] });
  const docs = el('div');
  const permits = el('div');
  async function decide(url, decision) {
    let note = '';
    if (decision === 'reject') {
      const f = el('form', { class: 'form-grid' }, UI.field({ name: 'notes', label: 'سبب الرفض', type: 'textarea', full: true, max: 300 }));
      const ok = await new Promise((resolve) => {
        let answered = false;
        UI.modal('رفض', f, [{ text: 'رفض', class: 'btn-danger', onClick: (c) => { answered = true; note = UI.read(f).notes; c(); } }], () => { resolve(answered); });
      });
      if (!ok) { return; }
    }
    try {
      await Api.post(url, { decision, notes: note });
      UI.ok('تم حفظ القرار.');
      await load();
    } catch (e) {
      UI.error(e);
    }
  }
  const decisionButtons = (url) => el('div', { class: 'actions' }, UI.button('اعتماد', () => { decide(url, 'approve'); }, 'btn-sm btn-success', 'check'), UI.button('رفض', () => { decide(url, 'reject'); }, 'btn-sm btn-ghost', 'xmark'));
  async function load() {
    const [d, p] = await Promise.all([Api.get(`/api/admin/documents?status=${docStatus.querySelector('select').value}`), Api.get(`/api/admin/permits?status=${permitStatus.querySelector('select').value}`)]);
    docs.replaceChildren(d.length ? UI.table(['اليخت', 'المالك', 'الوثيقة', 'الرقم', 'الانتهاء', 'الملف', 'الحالة', ''], d.map((x) => [
      x.yacht_name, x.owner_name, UI.TEXT.doc[x.doc_type], el('span', { class: 'ltr', text: x.doc_number }), Dates.element(x.expires_at, true),
      x.has_file ? el('a', { href: `/media/documents/${x.id}`, target: '_blank', rel: 'noopener' }, icon('file'), ' عرض') : '-',
      UI.badge('doc', x.status), x.status === 'pending_review' ? decisionButtons(`/api/admin/documents/${x.id}/decision`) : ''])) : UI.empty('لا توجد وثائق.', 'file'));
    permits.replaceChildren(p.length ? UI.table(['الرحلة', 'اليخت', 'الفترة', 'الضيوف', 'منطقة الإبحار', 'الحالة', ''], p.map((x) => [
      el('span', { class: 'ltr', text: x.reference }), x.yacht_name, el('div', {}, Dates.element(x.start_at), el('div', {}, Dates.element(x.end_at))), x.guests, x.zone_name || '-',
      UI.badge('permit', x.status), x.status === 'requested' ? decisionButtons(`/api/admin/permits/${x.id}/decision`) : ''])) : UI.empty('لا توجد تصاريح.', 'stamp'));
  }
  [docStatus, permitStatus].forEach((s) => { s.querySelector('select').addEventListener('change', () => { load().catch(UI.error); }); });
  root.append(UI.pageHead('الامتثال والتصاريح', 'لا يمكن حجز يخت دون وثائق معتمدة، ولا تبدأ رحلة دون تصريح إبحار'),
    UI.panel('تصاريح الإبحار', el('div', { class: 'filters' }, permitStatus), el('br'), permits),
    UI.panel('الوثائق', el('div', { class: 'filters' }, docStatus), el('br'), docs));
  await load();
});
