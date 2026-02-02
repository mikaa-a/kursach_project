window.whEditingId = null;
window.whStockId = null;
window.whStockType = null;
window.whStockTitle = '';
function whShowModal(id) { var el = document.getElementById(id); if (el) el.style.display = 'flex'; }
function whHideModal(id) { var el = document.getElementById(id); if (el) el.style.display = 'none'; }
function whOpenAdd() {
  window.whEditingId = null;
  document.getElementById('modal-wh-title').textContent = 'Добавить склад';
  document.getElementById('wh-name').value = '';
  document.getElementById('wh-address').value = '';
  document.getElementById('wh-phone').value = '';
  document.getElementById('wh-area').value = '0';
  document.getElementById('wh-error').textContent = '';
  document.getElementById('wh-error').style.display = 'none';
  document.getElementById('btn-wh-delete').style.display = 'none';
  whShowModal('modal-wh');
}
function whOpenEdit(id) {
  window.whEditingId = id;
  document.getElementById('modal-wh-title').textContent = 'Редактировать склад';
  document.getElementById('btn-wh-delete').style.display = 'inline-block';
  document.getElementById('wh-error').textContent = '';
  document.getElementById('wh-error').style.display = 'none';
  fetch('/api/warehouses/' + id, { credentials: 'same-origin' })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.error) { document.getElementById('wh-error').textContent = data.error; document.getElementById('wh-error').style.display = 'block'; return; }
      document.getElementById('wh-name').value = data.name || '';
      document.getElementById('wh-address').value = data.address || '';
      document.getElementById('wh-phone').value = (window.phoneMaskFormat && window.phoneMaskFormat(data.phone || '')) || (data.phone || '');
      document.getElementById('wh-area').value = data.area != null ? data.area : '0';
      if (window.phoneMaskInit) window.phoneMaskInit();
      whShowModal('modal-wh');
    })
    .catch(function() { document.getElementById('wh-error').textContent = 'Ошибка загрузки'; document.getElementById('wh-error').style.display = 'block'; });
}
function whOpenStock(linkEl) {
  var id = parseInt(linkEl.getAttribute('data-id'), 10);
  var type = linkEl.getAttribute('data-type') || 'warehouse';
  var titleName = linkEl.getAttribute('data-title') || '';
  window.whStockId = id;
  window.whStockType = type;
  window.whStockTitle = titleName;
  document.getElementById('modal-stock-title').textContent = (type === 'store' ? 'Остатки в магазине «' : 'Остатки на складе «') + titleName + '»';
  var tbody = document.getElementById('modal-stock-tbody');
  tbody.innerHTML = '<tr><td colspan="2">Загрузка…</td></tr>';
  whShowModal('modal-stock');
  var url = type === 'store' ? '/api/stores/' + id + '/stock' : '/api/warehouses/' + id + '/stock';
  fetch(url, { credentials: 'same-origin' })
    .then(function(r) { return r.json().then(function(d) { return d; }).catch(function() { return null; }); })
    .then(function(data) {
      if (!data || data.error) { tbody.innerHTML = '<tr><td colspan="2">' + (data && data.error ? data.error : 'Ошибка загрузки') + '</td></tr>'; return; }
      if (!Array.isArray(data) || !data.length) { tbody.innerHTML = '<tr><td colspan="2">Нет данных</td></tr>'; return; }
      tbody.innerHTML = '';
      data.forEach(function(row) {
        var tr = document.createElement('tr');
        tr.innerHTML = '<td>' + (row.product_name || row.name || '') + '</td><td>' + (row.quantity != null ? row.quantity : '') + '</td>';
        tbody.appendChild(tr);
      });
    })
    .catch(function() { tbody.innerHTML = '<tr><td colspan="2">Ошибка загрузки</td></tr>'; });
}
function whCloseStock() { whHideModal('modal-stock'); }
function whCloseForm() { whHideModal('modal-wh'); }
function whSave() {
  var name = document.getElementById('wh-name').value.trim();
  var errEl = document.getElementById('wh-error');
  if (!name) { errEl.textContent = 'Укажите название'; errEl.style.display = 'block'; return; }
  var phoneRaw = document.getElementById('wh-phone').value.trim();
  if (phoneRaw && window.phoneMaskValidate) {
    var phoneResult = window.phoneMaskValidate(phoneRaw);
    if (!phoneResult.valid) { errEl.textContent = phoneResult.message || 'Некорректный номер телефона'; errEl.style.display = 'block'; return; }
    phoneRaw = phoneResult.value;
  }
  var url = '/api/warehouses'; var method = 'POST';
  var body = { name: name, address: document.getElementById('wh-address').value.trim(), phone: phoneRaw, area: parseFloat(document.getElementById('wh-area').value) || 0 };
  if (window.whEditingId) { url = '/api/warehouses/' + window.whEditingId; method = 'PUT'; }
  fetch(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), credentials: 'same-origin' })
    .then(function(r) { return r.json(); })
    .then(function(data) { if (data.error) { errEl.textContent = data.error; errEl.style.display = 'block'; } else { whHideModal('modal-wh'); location.reload(); } })
    .catch(function() { errEl.textContent = 'Ошибка сохранения'; errEl.style.display = 'block'; });
}
function whDelete() {
  if (!window.whEditingId) return;
  if (!confirm('Удалить этот склад? Запись будет деактивирована.')) return;
  var errEl = document.getElementById('wh-error');
  fetch('/api/warehouses/' + window.whEditingId, { method: 'DELETE', credentials: 'same-origin' })
    .then(function(r) { return r.json(); })
    .then(function(data) { if (data.error && errEl) { errEl.textContent = data.error; errEl.style.display = 'block'; } else { whHideModal('modal-wh'); location.reload(); } })
    .catch(function() { if (errEl) { errEl.textContent = 'Ошибка удаления'; errEl.style.display = 'block'; } });
}
function whReceiptOpen() {
  if (!window.whStockId || !window.whStockType) return;
  document.getElementById('modal-receipt-title').textContent = window.whStockType === 'warehouse' ? ('Поступление на склад «' + window.whStockTitle + '»') : ('Поступление в магазин «' + window.whStockTitle + '»');
  var sel = document.getElementById('receipt-product');
  sel.innerHTML = '<option value="">— выберите товар —</option>';
  document.getElementById('receipt-quantity').value = '1';
  document.getElementById('receipt-error').textContent = '';
  document.getElementById('receipt-error').style.display = 'none';
  fetch('/api/products', { credentials: 'same-origin' }).then(function(r) { return r.ok ? r.json() : []; }).then(function(products) {
    if (Array.isArray(products)) products.forEach(function(p) { var o = document.createElement('option'); o.value = p.id; o.textContent = p.name; sel.appendChild(o); });
  }).catch(function() {});
  whHideModal('modal-stock');
  whShowModal('modal-receipt');
}
function whReceiptCancel() { whHideModal('modal-receipt'); whShowModal('modal-stock'); }
function whReceiptSubmit() {
  var productId = document.getElementById('receipt-product').value;
  var qty = parseInt(document.getElementById('receipt-quantity').value, 10);
  var errEl = document.getElementById('receipt-error');
  if (!productId || !qty || qty < 1) { errEl.textContent = 'Выберите товар и укажите количество'; errEl.style.display = 'block'; return; }
  var body = { product_id: parseInt(productId, 10), quantity: qty };
  if (window.whStockType === 'warehouse') body.warehouse_id = window.whStockId; else body.store_id = window.whStockId;
  errEl.style.display = 'none';
  fetch('/api/receipt', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), credentials: 'same-origin' })
    .then(function(r) { return r.json().then(function(d) { return d || {}; }).catch(function() { return {}; }); })
    .then(function(data) {
      if (data.error) { errEl.textContent = data.error; errEl.style.display = 'block'; return; }
      whHideModal('modal-receipt');
      var url = window.whStockType === 'store' ? '/api/stores/' + window.whStockId + '/stock' : '/api/warehouses/' + window.whStockId + '/stock';
      var tbody = document.getElementById('modal-stock-tbody');
      fetch(url, { credentials: 'same-origin' }).then(function(r) { return r.json(); }).then(function(list) {
        if (Array.isArray(list) && list.length) { tbody.innerHTML = ''; list.forEach(function(row) { var tr = document.createElement('tr'); tr.innerHTML = '<td>' + (row.product_name || row.name || '') + '</td><td>' + (row.quantity != null ? row.quantity : '') + '</td>'; tbody.appendChild(tr); }); }
        else if (Array.isArray(list)) tbody.innerHTML = '<tr><td colspan="2">Нет данных</td></tr>';
      });
      whShowModal('modal-stock');
    })
    .catch(function() { errEl.textContent = 'Ошибка сохранения'; errEl.style.display = 'block'; });
}
