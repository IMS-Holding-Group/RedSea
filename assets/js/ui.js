/* أدوات الواجهة المشتركة: بناء العناصر بأمان، الشارات، النوافذ، النماذج */
/* الدوال الأصلية append و prepend و replaceChildren تكتب null نصاً عند تمرير قيمة فارغة،
   فتُغلف هنا لتتجاهل القيم الفارغة، مما يسمح بالعرض الشرطي مثل (شرط ? عنصر : null) */
['append', 'prepend', 'replaceChildren'].forEach((name) => {
  const original = Element.prototype[name];
  Element.prototype[name] = function (...nodes) {
    return original.apply(this, nodes.filter((n) => n !== null && n !== undefined && n !== false));
  };
});

const UI = (() => {
  function escapeHtml(value) {
    return String(value === null || value === undefined ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  /* el: ينشئ عنصراً، والنصوص تمر دائماً عبر textContent لمنع XSS */
  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => {
      if (v === null || v === undefined || v === false) { return; }
      if (k === 'class') {
        node.className = v;
      } else if (k === 'text') {
        node.textContent = v;
      } else if (k.startsWith('on') && typeof v === 'function') {
        node.addEventListener(k.slice(2), v);
      } else if (k === 'dataset') {
        Object.assign(node.dataset, v);
      } else {
        node.setAttribute(k, v === true ? '' : v);
      }
    });
    children.flat().forEach((c) => {
      if (c === null || c === undefined || c === false) { return; }
      node.appendChild(c instanceof Node ? c : document.createTextNode(String(c)));
    });
    return node;
  }
  const icon = (name, extra) => el('i', { class: `fa-solid fa-${name}${extra ? ' ' + extra : ''}`, 'aria-hidden': 'true' });
  const clear = (node) => { node.replaceChildren(); return node; };
  const nf = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 });
  const num = (v) => nf.format(Number(v || 0));
  const money = (v) => `${num(v)} ر.س`;

  const LABELS = {
    booking: { pending: ['بانتظار الموافقة', 'info'], confirmed: ['مؤكد', 'success'], weather_hold: ['معلق بسبب الطقس', 'warning'], in_progress: ['رحلة جارية', 'info'], completed: ['مكتمل', 'muted'], cancelled: ['ملغى', 'danger'], rejected: ['مرفوض', 'danger'] },
    weather: { safe: ['طقس آمن', 'success', 'sun'], caution: ['طقس يستدعي الحذر', 'warning', 'wind'], unsafe: ['طقس غير آمن', 'danger', 'triangle-exclamation'], unknown: ['الطقس غير متوقع بعد', 'muted', 'circle-question'] },
    yacht: { active: ['نشط', 'success'], maintenance: ['في الصيانة', 'warning'], suspended: ['موقوف', 'danger'], draft: ['مسودة', 'muted'] },
    wo: { open: ['مفتوح', 'info'], quoted: ['وصلت عروض', 'info'], assigned: ['مسند', 'warning'], in_progress: ['قيد التنفيذ', 'warning'], completed: ['مكتمل', 'success'], cancelled: ['ملغى', 'muted'] },
    priority: { low: ['منخفضة', 'muted'], normal: ['عادية', 'info'], high: ['عالية', 'warning'], urgent: ['عاجلة', 'danger'] },
    doc: { pending_review: ['بانتظار المراجعة', 'info'], approved: ['معتمدة', 'success'], rejected: ['مرفوضة', 'danger'], expired: ['منتهية', 'danger'] },
    permit: { requested: ['التصريح قيد الاعتماد', 'info'], approved: ['التصريح معتمد', 'success'], rejected: ['التصريح مرفوض', 'danger'], not_required: ['لا يتطلب تصريحاً', 'muted'] },
    berth: { requested: ['بانتظار القرار', 'info'], approved: ['معتمد', 'success'], rejected: ['مرفوض', 'danger'], cancelled: ['ملغى', 'muted'], completed: ['مكتمل', 'muted'], available: ['متاح', 'success'], maintenance: ['صيانة', 'warning'], closed: ['مغلق', 'muted'] },
    severity: { info: ['معلومة', 'info'], warning: ['تحذير', 'warning'], critical: ['حرج', 'danger'] },
    alertStatus: { open: ['مفتوح', 'danger'], acknowledged: ['تم الاطلاع', 'warning'], resolved: ['تم الحل', 'success'] },
    role: { admin: ['مدير المنصة', 'danger'], marina_manager: ['مدير مرسى', 'info'], owner: ['مالك يخت', 'success'], tourist: ['سائح', 'muted'], provider: ['مزود خدمة', 'warning'] }
  };
  const TEXT = {
    purpose: { leisure: 'ترفيه', business: 'أعمال', fishing: 'صيد', diving: 'غوص' },
    service: { maintenance: 'صيانة', cleaning: 'تنظيف', fueling: 'تزويد وقود', electrical: 'كهرباء', diving_inspection: 'فحص تحت الماء' },
    doc: { registration: 'شهادة التسجيل', insurance: 'وثيقة التأمين', safety_inspection: 'فحص السلامة', navigation_license: 'رخصة الملاحة', crew_certificate: 'شهادة الطاقم' },
    zone: { no_anchor: 'حظر رسو', protected: 'منطقة محمية', restricted: 'منطقة مقيدة', cruising_area: 'منطقة إبحار مصرح بها' },
    alert: { no_anchor_violation: 'رسو في منطقة محظورة', protected_zone_entry: 'دخول منطقة محمية', restricted_zone_entry: 'دخول منطقة مقيدة', outside_cruising_area: 'خروج عن منطقة الإبحار', signal_lost: 'فقدان الإشارة', sos: 'نداء استغاثة', weather_warning: 'تحذير طقس' },
    size: { small: 'صغير', medium: 'متوسط', large: 'كبير' },
    source: { live: 'بيانات حية', cached: 'آخر بيانات محفوظة', simulated: 'بيانات تقديرية (دون اتصال)' }
  };
  function badge(group, key) {
    const def = (LABELS[group] || {})[key] || [key || '-', 'muted'];
    const b = el('span', { class: `badge badge-${def[1]}` });
    if (def[2]) { b.appendChild(icon(def[2])); }
    b.appendChild(document.createTextNode(def[0]));
    return b;
  }

  function toast(message, type) {
    let area = document.querySelector('.toast-area');
    if (!area) {
      area = el('div', { class: 'toast-area', role: 'status', 'aria-live': 'polite' });
      document.body.appendChild(area);
    }
    const t = el('div', { class: `toast${type ? ' toast-' + type : ''}`, text: message });
    area.appendChild(t);
    setTimeout(() => { t.remove(); }, 4500);
  }
  const ok = (m) => { toast(m, 'success'); };
  const error = (e) => { toast(e && e.message ? e.message : String(e), 'error'); };

  function modal(title, body, buttons, onClose) {
    const backdrop = el('div', { class: 'modal-backdrop' });
    let closed = false;
    const close = () => {
      if (closed) { return; }
      closed = true;
      backdrop.remove();
      if (onClose) { onClose(); }
    };
    const foot = el('div', { class: 'modal-foot' });
    (buttons || []).forEach((b) => {
      foot.appendChild(el('button', { class: `btn ${b.class || ''}`, type: 'button', text: b.text, onclick: () => { b.onClick(close); } }));
    });
    foot.appendChild(el('button', { class: 'btn btn-ghost', type: 'button', text: 'إغلاق', onclick: close }));
    const box = el('div', { class: 'modal', role: 'dialog', 'aria-modal': 'true' },
      el('div', { class: 'modal-head' }, el('h2', { text: title }),
        el('button', { class: 'btn btn-ghost btn-icon', type: 'button', 'aria-label': 'إغلاق', onclick: close }, icon('xmark'))),
      body, foot);
    backdrop.appendChild(box);
    backdrop.addEventListener('click', (e) => { if (e.target === backdrop) { close(); } });
    document.body.appendChild(backdrop);
    return close;
  }
  function confirm(title, message, confirmText, cls) {
    return new Promise((resolve) => {
      let answer = false;
      modal(title, el('p', { text: message }), [{ text: confirmText || 'تأكيد', class: cls || '', onClick: (c) => { answer = true; c(); } }], () => { resolve(answer); });
    });
  }

  /* النماذج */
  function field(def) {
    const id = `f-${def.name}-${Math.random().toString(36).slice(2, 7)}`;
    let input;
    if (def.type === 'select') {
      input = el('select', { id, name: def.name, required: def.required });
      (def.options || []).forEach(([v, t]) => {
        const o = el('option', { value: v, text: t });
        if (String(v) === String(def.value)) { o.selected = true; }
        input.appendChild(o);
      });
    } else if (def.type === 'textarea') {
      input = el('textarea', { id, name: def.name, required: def.required, maxlength: def.max });
      input.value = def.value || '';
    } else if (def.type === 'checkbox') {
      input = el('input', { id, name: def.name, type: 'checkbox' });
      input.checked = !!def.value;
      return el('label', { class: `check${def.full ? ' full' : ''}`, for: id }, input, def.label);
    } else {
      input = el('input', { id, name: def.name, type: def.type || 'text', required: def.required, min: def.min, max: def.max, step: def.step, maxlength: def.maxlength, accept: def.accept, placeholder: def.placeholder, autocomplete: def.autocomplete });
      if (def.value !== undefined && def.value !== null && def.type !== 'file') { input.value = def.value; }
    }
    return el('div', { class: `field${def.full ? ' full' : ''}` },
      el('label', { for: id, text: def.label + (def.required ? ' *' : '') }), input,
      def.hint ? el('span', { class: 'hint', text: def.hint }) : null,
      el('span', { class: 'error', 'data-error-for': def.name }));
  }
  function form(defs, onSubmit, submitText) {
    const f = el('form', { class: 'form-grid', novalidate: true });
    defs.forEach((d) => { f.appendChild(field(d)); });
    const btn = el('button', { class: 'btn', type: 'submit', text: submitText || 'حفظ' });
    f.appendChild(el('div', { class: 'actions full' }, btn));
    f.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearErrors(f);
      if (!validate(f, defs)) { return; }
      btn.disabled = true;
      try {
        await onSubmit(read(f), f);
      } catch (err) {
        error(err);
      } finally {
        btn.disabled = false;
      }
    });
    return f;
  }
  function read(f) {
    const data = {};
    Array.from(f.elements).forEach((i) => {
      if (!i.name) { return; }
      if (i.type === 'checkbox') {
        data[i.name] = i.checked;
      } else if (i.type !== 'file') {
        data[i.name] = i.value.trim();
      }
    });
    return data;
  }
  function setError(f, name, message) {
    const slot = f.querySelector(`[data-error-for="${name}"]`);
    if (slot) { slot.textContent = message; }
  }
  function clearErrors(f) { f.querySelectorAll('.error').forEach((s) => { s.textContent = ''; }); }
  function validate(f, defs) {
    let valid = true;
    defs.forEach((d) => {
      const input = f.elements[d.name];
      if (!input || d.type === 'checkbox') { return; }
      const v = d.type === 'file' ? (input.files.length ? 'x' : '') : input.value.trim();
      if (d.required && !v) {
        setError(f, d.name, 'هذا الحقل مطلوب.');
        valid = false;
      } else if (v && d.type === 'number') {
        const n = Number(v);
        if (Number.isNaN(n) || (d.min !== undefined && n < d.min) || (d.max !== undefined && n > d.max)) {
          setError(f, d.name, `أدخل رقماً بين ${d.min} و${d.max}.`);
          valid = false;
        }
      } else if (v && d.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v)) {
        setError(f, d.name, 'صيغة البريد الإلكتروني غير صحيحة.');
        valid = false;
      } else if (v && d.name === 'phone' && !/^05\d{8}$/.test(v)) {
        setError(f, d.name, 'رقم الجوال يبدأ بـ 05 ويتكون من 10 أرقام.');
        valid = false;
      }
    });
    return valid;
  }

  /* الجداول والحالات */
  function table(headers, rows) {
    const thead = el('thead', {}, el('tr', {}, headers.map((h) => el('th', { text: h }))));
    const tbody = el('tbody', {}, rows.map((r) => el('tr', {}, r.map((c) => el('td', {}, c)))));
    return el('div', { class: 'table-wrap' }, el('table', {}, thead, tbody));
  }
  const empty = (message, ic) => el('div', { class: 'empty' }, icon(ic || 'water'), message);
  const loading = () => el('div', { class: 'loading' }, icon('spinner', 'fa-spin'), ' جار التحميل...');
  const stat = (label, value, ic) => el('div', { class: 'stat' }, ic ? icon(ic) : null, el('span', { class: 'value', text: value }), el('span', { class: 'label', text: label }));
  const panel = (title, ...children) => el('section', { class: 'panel' }, title ? el('div', { class: 'panel-head' }, el('h2', { text: title })) : null, ...children);
  const pageHead = (title, sub, ...actions) => el('div', { class: 'page-head' }, el('div', {}, el('h1', { text: title }), sub ? el('p', { text: sub }) : null), actions.length ? el('div', { class: 'actions' }, actions) : null);
  const button = (text, onClick, cls, ic) => el('button', { class: `btn ${cls || ''}`, type: 'button', onclick: onClick }, ic ? icon(ic) : null, text);
  const qs = (name) => new URLSearchParams(location.search).get(name);

  return { escapeHtml, el, icon, clear, num, money, badge, LABELS, TEXT, toast, ok, error, modal, confirm, field, form, read, setError, table, empty, loading, stat, panel, pageHead, button, qs };
})();
