(function() {
  function digitsOnly(str) {
    return (str || '').replace(/\D/g, '');
  }

  function formatPhone(value) {
    var d = digitsOnly(value);
    if (d.length > 0 && (d[0] === '8' || d[0] === '7')) d = d.substring(1);
    if (d.length > 10) d = d.substring(0, 10);
    if (d.length === 0) return '';
    if (d.length <= 3) return '+7 (' + d;
    if (d.length <= 6) return '+7 (' + d.substring(0, 3) + ') ' + d.substring(3);
    return '+7 (' + d.substring(0, 3) + ') ' + d.substring(3, 6) + '-' + d.substring(6, 8) + '-' + d.substring(8, 10);
  }

  function validatePhone(value) {
    var d = digitsOnly(value);
    if (d.length > 0 && (d[0] === '8' || d[0] === '7')) d = d.substring(1);
    if (d.length === 0) return { valid: true, value: '' };
    if (d.length < 10) return { valid: false, value: '', message: 'Введите не менее 10 цифр номера телефона' };
    if (d.length > 10) d = d.substring(0, 10);
    return { valid: true, value: formatPhone(d) };
  }

  function onPhoneInput(e) {
    var el = e.target;
    var start = el.selectionStart;
    var oldLen = el.value.length;
    var formatted = formatPhone(el.value);
    el.value = formatted;
    var newLen = el.value.length;
    var newStart = Math.max(0, start + (newLen - oldLen));
    if (newStart > 0 && el.value[newStart - 1] === '-') newStart--;
    if (newStart > 0 && el.value[newStart - 1] === ')') newStart--;
    if (newStart > 0 && el.value[newStart - 1] === ' ') newStart--;
    el.setSelectionRange(newStart, newStart);
  }

  function initPhoneMask() {
    var inputs = document.querySelectorAll('.phone-input');
    for (var i = 0; i < inputs.length; i++) {
      var el = inputs[i];
      if (el.dataset.phoneMaskInited) continue;
      el.dataset.phoneMaskInited = '1';
      el.addEventListener('input', onPhoneInput);
      el.addEventListener('paste', function(e) {
        e.preventDefault();
        var text = (e.clipboardData || window.clipboardData).getData('text');
        var formatted = formatPhone(text);
        e.target.value = formatted;
      });
      if (el.value) el.value = formatPhone(el.value);
    }
  }

  window.phoneMaskFormat = formatPhone;
  window.phoneMaskValidate = validatePhone;
  window.phoneMaskInit = initPhoneMask;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPhoneMask);
  } else {
    initPhoneMask();
  }
})();
