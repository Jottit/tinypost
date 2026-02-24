var allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
var maxSize = 5 * 1024 * 1024;

export function uploadImage(jot, file) {
  if (!allowedTypes.includes(file.type)) {
    alert('Only jpg, png, gif, and webp images are allowed.');
    return;
  }
  if (file.size > maxSize) {
    alert('Image must be under 5MB.');
    return;
  }

  var data = new FormData();
  data.append('file', file);

  fetch('/-/upload', { method: 'POST', body: data })
    .then(function(res) { return res.json(); })
    .then(function(json) {
      if (json.url) {
        var current = jot.getValue();
        jot.setValue(current.replace(/\n*$/, '') + '\n\n![image](' + json.url + ')\n');
      } else {
        alert(json.error || 'Upload failed');
      }
    })
    .catch(function() {
      alert('Upload failed');
    });
}

export function bindImageHandlers(el, jot) {
  el.addEventListener('dragover', function(e) {
    e.preventDefault();
    el.classList.add('drag-over');
  });
  el.addEventListener('dragleave', function() {
    el.classList.remove('drag-over');
  });
  el.addEventListener('drop', function(e) {
    e.preventDefault();
    el.classList.remove('drag-over');
    Array.from(e.dataTransfer.files).forEach(function(file) {
      if (file.type.startsWith('image/')) {
        uploadImage(jot, file);
      }
    });
  });
  el.addEventListener('paste', function(e) {
    var items = e.clipboardData && e.clipboardData.items;
    if (!items) return;
    Array.from(items).forEach(function(item) {
      if (item.type.startsWith('image/')) {
        var file = item.getAsFile();
        if (file) uploadImage(jot, file);
      }
    });
  });
}
