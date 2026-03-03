(function() {
  var timers = {};
  var dirty = {};
  var DELAY = 800;

  function save(form) {
    delete dirty[form.action];
    clearTimeout(timers[form.action]);
    delete timers[form.action];
    fetch(form.action, {
      method: 'POST',
      body: new FormData(form),
      headers: {'X-Auto-Save': '1'}
    });
  }

  function debouncedSave(form) {
    dirty[form.action] = form;
    clearTimeout(timers[form.action]);
    timers[form.action] = setTimeout(function() { save(form); }, DELAY);
  }

  function flushAll() {
    for (var action in dirty) {
      var form = dirty[action];
      clearTimeout(timers[action]);
      fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: {'X-Auto-Save': '1'},
        keepalive: true
      });
    }
    dirty = {};
    timers = {};
  }

  document.querySelectorAll('.auto-save').forEach(function(form) {
    form.addEventListener('input', function(e) {
      if (e.target.matches('input:not([type="checkbox"]), textarea')) {
        debouncedSave(form);
      }
    });

    form.addEventListener('change', function(e) {
      if (e.target.matches('select, input[type="checkbox"]')) {
        save(form);
      }
    });
  });

  // Expose for pages that need to trigger a save manually (e.g. social links remove)
  window.autoSaveNow = function(form) { save(form); };

  document.addEventListener('click', function(e) {
    if (e.target.closest('a[href]')) flushAll();
  });

  window.addEventListener('beforeunload', flushAll);
})();
