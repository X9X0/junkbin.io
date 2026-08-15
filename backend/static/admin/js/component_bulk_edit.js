(function() {
  'use strict';
  // Show only the value input matching the selected field, and only submit that one.
  var fieldSelect = document.getElementById('id_field');
  if (!fieldSelect) return;
  var valueInputs = document.querySelectorAll('.value-input');

  function syncValueInput() {
    var selected = fieldSelect.value;
    valueInputs.forEach(function(input) {
      var active = input.dataset.for === selected;
      input.style.display = active ? '' : 'none';
      input.disabled = !active;
    });
  }

  fieldSelect.addEventListener('change', syncValueInput);
  syncValueInput();
})();
