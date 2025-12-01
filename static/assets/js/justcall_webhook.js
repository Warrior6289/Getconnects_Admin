(function() {
  document.addEventListener('DOMContentLoaded', function() {
    function showAlert(id, message, ok) {
      var el = document.getElementById(id);
      if (el) {
        el.textContent = message;
        el.className = 'mt-2 alert ' + (ok ? 'alert-success' : 'alert-danger');
        el.style.display = 'block';
      }
    }

    var csrfInput = document.querySelector('input[name="csrf_token"]');
    var csrfToken = csrfInput ? csrfInput.value : '';

    var btn = document.getElementById('retest-webhook');
    if (btn) {
      btn.addEventListener('click', function() {
        var token = btn.getAttribute('data-token');
        fetch('/webhooks/justcall/' + token + '/latest', {
          headers: { 'X-CSRFToken': csrfToken }
        })
          .then(function(resp) {
            if (!resp.ok) throw new Error();
            return resp.json();
          })
          .then(function(data) {
            var pre = document.getElementById('payload');
            if (pre) {
              pre.textContent = JSON.stringify(data, null, 2);
            }
            showAlert('payload-status', 'Latest payload loaded', true);
          })
          .catch(function() {
            var pre = document.getElementById('payload');
            if (pre) {
              pre.textContent = 'Error fetching payload';
            }
            showAlert('payload-status', 'Error fetching payload', false);
          });
      });
    }

    var mappingForm = document.getElementById('mapping-form');
    if (mappingForm) {
      var token = mappingForm.getAttribute('data-token');

      function extractPaths(obj, prefix) {
        var paths = [];
        prefix = prefix || '';
        if (Array.isArray(obj)) {
          obj.forEach(function(val, idx) {
            var newPrefix = prefix ? prefix + '[' + idx + ']' : '[' + idx + ']';
            paths = paths.concat(extractPaths(val, newPrefix));
          });
        } else if (obj && typeof obj === 'object') {
          Object.keys(obj).forEach(function(key) {
            var newPrefix = prefix ? prefix + '.' + key : key;
            paths = paths.concat(extractPaths(obj[key], newPrefix));
          });
        } else if (prefix) {
          paths.push(prefix);
        }
        return paths;
      }

      function updateSelectOptions() {
        var selected = [];
        mappingForm.querySelectorAll('select[data-field]').forEach(function(sel) {
          if (sel.value) selected.push(sel.value);
        });
        mappingForm.querySelectorAll('select[data-field]').forEach(function(sel) {
          Array.from(sel.options).forEach(function(opt) {
            if (!opt.value) return;
            opt.disabled = selected.includes(opt.value) && sel.value !== opt.value;
          });
        });
      }

      var savedMapping = {};
      fetch('/webhooks/justcall/' + token + '/mapping', {
        headers: { 'X-CSRFToken': csrfToken }
      })
        .then(function(resp) {
          if (!resp.ok) throw new Error();
          return resp.json();
        })
        .then(function(mapping) {
          savedMapping = mapping || {};
          return fetch('/webhooks/justcall/' + token + '/latest', {
            headers: { 'X-CSRFToken': csrfToken }
          });
        })
        .then(function(resp) {
          if (!resp.ok) throw new Error();
          return resp.json();
        })
        .then(function(payload) {
          if (Array.isArray(payload)) {
            payload = payload[0] || {};
          }
          var paths = extractPaths(payload);
          mappingForm.querySelectorAll('select[data-field]').forEach(function(sel) {
            while (sel.options.length > 1) sel.remove(1);
            paths.forEach(function(p) {
              var opt = document.createElement('option');
              opt.value = p;
              opt.textContent = p;
              sel.appendChild(opt);
            });
            var field = sel.getAttribute('data-field');
            if (savedMapping[field]) sel.value = savedMapping[field];
          });
          updateSelectOptions();
        })
        .catch(function() {
          showAlert('mapping-status', 'Error loading mapping', false);
        });

      mappingForm.querySelectorAll('select[data-field]').forEach(function(sel) {
        sel.addEventListener('change', updateSelectOptions);
      });

      mappingForm.addEventListener('submit', function(e) {
        e.preventDefault();
        var data = {};
        mappingForm.querySelectorAll('select[data-field]').forEach(function(sel) {
          var val = sel.value.trim();
          if (val) data[sel.getAttribute('data-field')] = val;
        });
        fetch('/webhooks/justcall/' + token + '/mapping', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: JSON.stringify(data)
        })
          .then(function(resp) {
            showAlert(
              'mapping-status',
              resp.ok ? 'Mapping saved' : 'Error saving mapping',
              resp.ok
            );
          })
          .catch(function() {
            showAlert('mapping-status', 'Error saving mapping', false);
          });
      });
    }
  });
})();
