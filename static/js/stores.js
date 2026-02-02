window.storesEditingId = null;
function storesShowModal(id) { var el = document.getElementById(id); if (el) el.style.display = 'flex'; }
function storesHideModal(id) { var el = document.getElementById(id); if (el) el.style.display = 'none'; }
function storesOpenAdd() {
  window.storesEditingId = null;
  document.getElementById('modal-store-title').textContent = 'Добавить магазин';
  document.getElementById('store-name').value = '';
  document.getElementById('store-address').value = '';
  document.getElementById('store-phone').value = '';
  document.getElementById('store-error').textContent = '';
  document.getElementById('store-error').style.display = 'none';
  document.getElementById('btn-store-delete').style.display = 'none';
  storesShowModal('modal-store');
}
function storesOpenEdit(id) {
  window.storesEditingId = id;
  document.getElementById('modal-store-title').textContent = 'Редактировать магазин';
  document.getElementById('btn-store-delete').style.display = 'inline-block';
  document.getElementById('store-error').textContent = '';
  document.getElementById('store-error').style.display = 'none';
  fetch('/api/stores/' + id, { credentials: 'same-origin' })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.error) { document.getElementById('store-error').textContent = data.error; document.getElementById('store-error').style.display = 'block'; return; }
      document.getElementById('store-name').value = data.name || '';
      document.getElementById('store-address').value = data.address || '';
      document.getElementById('store-phone').value = (window.phoneMaskFormat && window.phoneMaskFormat(data.phone || '')) || (data.phone || '');
      if (window.phoneMaskInit) window.phoneMaskInit();
      storesShowModal('modal-store');
    })
    .catch(function() { document.getElementById('store-error').textContent = 'Ошибка загрузки'; document.getElementById('store-error').style.display = 'block'; });
}
function storesOpenStock(linkEl) {
  var id = parseInt(linkEl.getAttribute('data-id'), 10);
  var type = linkEl.getAttribute('data-type') || 'store';
  var titleName = linkEl.getAttribute('data-title') || '';
  document.getElementById('modal-stock-title').textContent = (type === 'store' ? 'Остатки в магазине «' : 'Остатки на складе «') + titleName + '»';
  var tbody = document.getElementById('modal-stock-tbody');
  tbody.innerHTML = '<tr><td colspan="2">Загрузка…</td></tr>';
  storesShowModal('modal-stock');
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
function storesCloseStock() { storesHideModal('modal-stock'); }
function storesCloseForm() { storesHideModal('modal-store'); }
function storesSave() {
  var name = document.getElementById('store-name').value.trim();
  var errEl = document.getElementById('store-error');
  if (!name) { errEl.textContent = 'Укажите название'; errEl.style.display = 'block'; return; }
  var phoneRaw = document.getElementById('store-phone').value.trim();
  if (phoneRaw && window.phoneMaskValidate) {
    var phoneResult = window.phoneMaskValidate(phoneRaw);
    if (!phoneResult.valid) { errEl.textContent = phoneResult.message || 'Некорректный номер телефона'; errEl.style.display = 'block'; return; }
    phoneRaw = phoneResult.value;
  }
  var url = '/api/stores'; var method = 'POST';
  var body = { name: name, address: document.getElementById('store-address').value.trim(), phone: phoneRaw };
  if (window.storesEditingId) { url = '/api/stores/' + window.storesEditingId; method = 'PUT'; }
  fetch(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), credentials: 'same-origin' })
    .then(function(r) { return r.json(); })
    .then(function(data) { if (data.error) { errEl.textContent = data.error; errEl.style.display = 'block'; } else { storesHideModal('modal-store'); location.reload(); } })
    .catch(function() { errEl.textContent = 'Ошибка сохранения'; errEl.style.display = 'block'; });
}
function storesDelete() {
  if (!window.storesEditingId) return;
  if (!confirm('Удалить этот магазин? Запись будет деактивирована.')) return;
  var errEl = document.getElementById('store-error');
  fetch('/api/stores/' + window.storesEditingId, { method: 'DELETE', credentials: 'same-origin' })
    .then(function(r) { return r.json(); })
    .then(function(data) { if (data.error && errEl) { errEl.textContent = data.error; errEl.style.display = 'block'; } else { storesHideModal('modal-store'); location.reload(); } })
    .catch(function() { if (errEl) { errEl.textContent = 'Ошибка удаления'; errEl.style.display = 'block'; } });
}
