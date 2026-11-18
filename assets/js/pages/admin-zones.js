/* إدارة المناطق البحرية: رسم المضلعات بالنقر على الخريطة */
App.start(async (root) => {
  const { el, icon } = UI;
  const mapBox = el('div');
  const list = el('div');
  let zones = [];
  let editing = null;
  let drawing = false;
  const hint = el('div', { class: 'notice' }, icon('circle-info'), 'اضغط "رسم منطقة جديدة" ثم انقر على الخريطة لإضافة رؤوس المضلع (3 نقاط على الأقل)، ثم احفظ.');
  const f = el('form', { class: 'form-grid', novalidate: true },
    UI.field({ name: 'name', label: 'اسم المنطقة', required: true, full: true }),
    UI.field({ name: 'zone_type', label: 'النوع', type: 'select', options: Object.entries(UI.TEXT.zone) }),
    UI.field({ name: 'is_active', label: 'نشطة', type: 'checkbox', value: true }),
    UI.field({ name: 'description', label: 'الوصف', type: 'textarea', full: true, max: 300 }),
    el('div', { class: 'actions full' },
      el('button', { class: 'btn', type: 'submit' }, icon('floppy-disk'), 'حفظ المنطقة'),
      UI.button('تراجع عن آخر نقطة', () => {
        const d = map.get('draft').slice(0, -1);
        map.set('draft', d);
      }, 'btn-ghost', 'rotate-left'),
      UI.button('إلغاء', reset, 'btn-ghost', 'xmark')));
  const editor = UI.panel('محرر المنطقة', hint, f);
  editor.classList.add('hidden');
  const map = RYMap.create(mapBox, { center: [21.73, 39.03], zoom: 11, onClick: (ll) => {
    if (!drawing) { return; }
    map.set('draft', map.get('draft').concat([[+ll[0].toFixed(6), +ll[1].toFixed(6)]]));
  } });
  function reset() {
    editing = null;
    drawing = false;
    map.set('draft', []);
    f.reset();
    editor.classList.add('hidden');
  }
  function start(z) {
    editing = z;
    drawing = true;
    editor.classList.remove('hidden');
    f.elements.name.value = z ? z.name : '';
    f.elements.zone_type.value = z ? z.zone_type : 'no_anchor';
    f.elements.description.value = z ? z.description || '' : '';
    f.elements.is_active.checked = z ? !!z.is_active : true;
    map.set('draft', z ? z.polygon.map((p) => p.slice()) : []);
    if (z) {
      mapBox.scrollIntoView({ block: 'start' });
      map.fit(z.polygon);
    }
  }
  f.addEventListener('submit', async (e) => {
    e.preventDefault();
    const d = UI.read(f);
    d.polygon = map.get('draft');
    if (d.polygon.length < 3) {
      UI.error('ارسم 3 نقاط على الأقل.');
      return;
    }
    try {
      if (editing) {
        await Api.put(`/api/admin/zones/${editing.id}`, d);
      } else {
        await Api.post('/api/admin/zones', d);
      }
      UI.ok('تم حفظ المنطقة، وتطبق فوراً على فحص مواقع اليخوت.');
      reset();
      await load();
    } catch (err) {
      UI.error(err);
    }
  });
  async function load() {
    zones = await Api.get('/api/admin/zones');
    map.set('zones', zones.filter((z) => z.is_active));
    list.replaceChildren(UI.table(['المنطقة', 'النوع', 'عدد النقاط', 'الحالة', ''], zones.map((z) => [
      el('div', {}, z.name, el('div', { class: 'small muted', text: z.description || '' })), UI.TEXT.zone[z.zone_type], z.polygon.length,
      z.is_active ? el('span', { class: 'badge badge-success', text: 'نشطة' }) : el('span', { class: 'badge badge-muted', text: 'معطلة' }),
      el('div', { class: 'actions' }, UI.button('عرض', () => { map.fit(z.polygon); }, 'btn-sm btn-ghost', 'eye'),
        UI.button('تعديل', () => { start(z); }, 'btn-sm btn-ghost', 'pen'),
        UI.button('حذف', async () => {
          if (!await UI.confirm('حذف المنطقة', `حذف ${z.name}؟ إن كانت مرتبطة بحجوزات فستُعطل بدلاً من حذفها.`, 'حذف', 'btn-danger')) { return; }
          try {
            await Api.del(`/api/admin/zones/${z.id}`);
            await load();
          } catch (err) {
            UI.error(err);
          }
        }, 'btn-sm btn-ghost', 'trash'))])));
  }
  root.append(UI.pageHead('المناطق البحرية', 'مناطق حظر الرسو والمحميات والمناطق المقيدة ومناطق الإبحار المصرح بها', UI.button('رسم منطقة جديدة', () => { start(null); }, '', 'draw-polygon')),
    UI.panel(null, mapBox), editor, list);
  await load();
});
