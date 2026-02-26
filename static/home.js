(function() {
  var input = document.querySelector('.pill-input input');
  var form = input.closest('form');
  var hint = document.querySelector('.page-centered > p');
  var defaultText = hint.textContent;
  var defaultClass = hint.className;
  var timer;
  var available = true;
  var validPattern = /^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$/;

  function resize() {
    input.size = Math.min(20, Math.max(8, input.value.length || 8));
  }
  resize();

  if (window.matchMedia('(min-width: 768px)').matches) {
    input.focus();
  }

  form.addEventListener('submit', function(e) {
    if (!available) e.preventDefault();
  });

  input.addEventListener('input', function() {
    resize();
    clearTimeout(timer);
    available = true;
    var name = input.value.toLowerCase().trim();
    if (!validPattern.test(name)) {
      hint.textContent = defaultText;
      hint.className = defaultClass;
      return;
    }
    timer = setTimeout(function() {
      fetch('/check-subdomain?name=' + encodeURIComponent(name))
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (input.value.toLowerCase().trim() !== name) return;
          if (data.available) {
            hint.textContent = name + '.tinypost.blog is available';
            hint.className = 'success';
          } else {
            available = false;
            hint.textContent = name + '.tinypost.blog is not available';
            hint.className = 'error';
          }
        });
    }, 300);
  });
})();
