(function() {
  'use strict';
  var el = document.getElementById('system-status-indicator');
  if (!el) return;

  var url = el.getAttribute('data-status-url');
  if (!url) return;

  var labels = {ok: 'Operational', warn: 'Degraded', error: 'Critical'};

  function applyStatus(status, title) {
    el.className = 'ssi-' + status;
    el.id = 'system-status-indicator';
    el.querySelector('.ssi-label').textContent = labels[status] || 'Critical';
    el.title = title;
  }

  function update() {
    fetch(url, {credentials: 'same-origin', redirect: 'manual'}).then(function(r) {
      if (r.type === 'opaqueredirect' || !r.ok) {
        applyStatus('error', 'Could not fetch status (not authenticated)');
        return null;
      }
      return r.json();
    }).then(function(data) {
      if (!data) return;
      var s = data.overall || 'error';
      var parts = [];
      for (var name in data.services) {
        if (data.services[name] !== 'ok') parts.push(name + ': ' + data.services[name]);
      }
      applyStatus(s, parts.length ? parts.join(', ') : 'All systems operational');
    }).catch(function() {
      applyStatus('error', 'Could not fetch status');
    });
  }

  update();
  setInterval(update, 30000);
})();
