(function() {
  function showConfirm(message, onConfirm) {
    $('#confirmModalMessage').text(message);
    $('#confirmModal').modal('show');
    $('#confirmModalOk').off('click').on('click', function() {
      $('#confirmModal').modal('hide');
      if (typeof onConfirm === 'function') {
        onConfirm();
      }
    });
  }
  window.showConfirm = showConfirm;
  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('[data-confirm]').forEach(function(el) {
      el.addEventListener('click', function(e) {
        e.preventDefault();
        var message = this.getAttribute('data-confirm') || 'Are you sure?';
        var formId = this.getAttribute('data-form-id');
        showConfirm(message, function() {
          if (formId) {
            var form = document.getElementById(formId);
            if (form) {
              form.submit();
            }
          }
        });
      });
    });
  });
})();
