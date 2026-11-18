/* الامتثال البحري: الوثائق الإلزامية ونسبة الامتثال لكل يخت */
App.start(async (root) => {
  const { el, icon } = UI;
  const box = el('div');
  let yachts = [];
  async function load() {
    yachts = await Api.get('/api/owner/documents');
    box.replaceChildren(...yachts.map((y) => {
      const panel = UI.panel(null,
        el('div', { class: 'panel-head' }, el('h2', { text: y.name }), el('span', { class: `badge badge-${y.score === 100 ? 'success' : (y.score >= 67 ? 'warning' : 'danger')}`, text: `نسبة الامتثال ${y.score}%` })),
        y.missing.length ? el('div', { class: 'notice notice-danger' }, icon('ban'), `لا يمكن حجز هذا اليخت حتى تُعتمد: ${y.missing.join('، ')}.`) : null,
        y.documents.length ? UI.table(['الوثيقة', 'الرقم', 'الإصدار', 'الانتهاء', 'الحالة', 'الملف'], y.documents.map((d) => [
          UI.TEXT.doc[d.doc_type], el('span', { class: 'ltr', text: d.doc_number }), Dates.element(d.issued_at, true), Dates.element(d.expires_at, true),
          el('div', {}, UI.badge('doc', d.status), d.review_notes ? el('div', { class: 'small muted', text: d.review_notes }) : null),
          d.has_file ? el('a', { href: `/media/documents/${d.id}`, target: '_blank', rel: 'noopener' }, icon('file'), ' عرض') : '-'])) : UI.empty('لا توجد وثائق.', 'file'));
      return panel;
    }));
  }
  function upload() {
    const today = Dates.toInput(Dates.nowIso(), true);
    const nextYear = Dates.toInput(new Date(Date.now() + 365 * 86400000).toISOString().slice(0, 19), true);
    const defs = [
      { name: 'yacht_id', label: 'اليخت', type: 'select', options: yachts.map((y) => [y.id, y.name]) },
      { name: 'doc_type', label: 'نوع الوثيقة', type: 'select', options: Object.entries(UI.TEXT.doc) },
      { name: 'doc_number', label: 'رقم الوثيقة', required: true },
      { name: 'issued_at', label: 'تاريخ الإصدار', type: 'date', required: true, value: today },
      { name: 'expires_at', label: 'تاريخ الانتهاء', type: 'date', required: true, value: nextYear },
      { name: 'file', label: 'الملف (PDF أو صورة حتى 5 ميجابايت)', type: 'file', accept: 'application/pdf,image/jpeg,image/png', required: true }
    ];
    let close = null;
    const f = UI.form(defs, async (d, form) => {
      const fd = new FormData();
      fd.append('yacht_id', d.yacht_id);
      fd.append('doc_type', d.doc_type);
      fd.append('doc_number', d.doc_number);
      fd.append('issued_at', Dates.fromInput(d.issued_at));
      fd.append('expires_at', Dates.fromInput(d.expires_at));
      fd.append('file', form.elements.file.files[0]);
      await Api.upload('/api/owner/documents', fd);
      close();
      UI.ok('تم رفع الوثيقة وإرسالها للمراجعة.');
      await load();
    }, 'رفع الوثيقة');
    close = UI.modal('رفع وثيقة', f, []);
  }
  root.append(UI.pageHead('الامتثال والوثائق', 'شهادة التسجيل والتأمين وفحص السلامة إلزامية وسارية طوال فترة أي رحلة', UI.button('رفع وثيقة', upload, '', 'upload')), box);
  await load();
});
