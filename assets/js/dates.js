/* التواريخ: التخزين UTC، والعرض بتوقيت السعودية بالصيغة 2026/1/3م 5:50ص */
const Dates = (() => {
  const KSA_MS = 3 * 3600 * 1000;
  const pad2 = (n) => { return String(n).padStart(2, '0'); };
  function toKsa(iso) {
    if (!iso) { return null; }
    const d = new Date(String(iso).replace('Z', '').slice(0, 19) + 'Z');
    if (Number.isNaN(d.getTime())) { return null; }
    return new Date(d.getTime() + KSA_MS);
  }
  function parts(iso) {
    const k = toKsa(iso);
    if (!k) { return null; }
    const h = k.getUTCHours();
    const h12 = h % 12 || 12;
    const suffix = h < 12 ? 'ص' : 'م';
    return {
      date: `${k.getUTCFullYear()}/${k.getUTCMonth() + 1}/${k.getUTCDate()}م`,
      time: `${h12}:${pad2(k.getUTCMinutes())}${suffix}`
    };
  }
  function text(iso) {
    const p = parts(iso);
    return p ? `${p.date} ${p.time}` : '-';
  }
  function dateText(iso) {
    const p = parts(iso);
    return p ? p.date : '-';
  }
  function timeText(iso) {
    const p = parts(iso);
    return p ? p.time : '-';
  }
  function element(iso, dateOnly) {
    const wrap = document.createElement('span');
    const p = parts(iso);
    if (!p) {
      wrap.textContent = '-';
      return wrap;
    }
    /* كل جزء معزول باتجاه RTL حتى لا ينفصل حرف (م) أو (ص) عن الرقم داخل الجداول العربية */
    wrap.className = 'dt';
    wrap.dir = 'rtl';
    const d = document.createElement('span');
    d.dir = 'rtl';
    d.textContent = p.date;
    wrap.appendChild(d);
    if (!dateOnly) {
      const t = document.createElement('span');
      t.dir = 'rtl';
      t.textContent = p.time;
      wrap.appendChild(document.createTextNode(' '));
      wrap.appendChild(t);
    }
    return wrap;
  }
  function fromInput(value) {
    if (!value) { return null; }
    const m = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/.exec(value);
    if (!m) { return null; }
    const utc = Date.UTC(+m[1], +m[2] - 1, +m[3], +(m[4] || 0), +(m[5] || 0)) - KSA_MS;
    return new Date(utc).toISOString().slice(0, 19);
  }
  function toInput(iso, dateOnly) {
    const k = toKsa(iso);
    if (!k) { return ''; }
    const s = k.toISOString();
    return dateOnly ? s.slice(0, 10) : s.slice(0, 16);
  }
  function nowIso() { return new Date().toISOString().slice(0, 19); }
  function addHours(iso, h) { return new Date(new Date(iso + 'Z').getTime() + h * 3600000).toISOString().slice(0, 19); }
  function hoursBetween(a, b) { return (new Date(b + 'Z') - new Date(a + 'Z')) / 3600000; }
  return { text, dateText, timeText, element, fromInput, toInput, nowIso, addHours, hoursBetween };
})();
