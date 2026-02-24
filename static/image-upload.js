var allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
var maxSize = 5 * 1024 * 1024;

export function uploadImage(jot, file) {
  if (allowedTypes.indexOf(file.type) === -1) {
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
    var files = e.dataTransfer.files;
    for (var i = 0; i < files.length; i++) {
      if (files[i].type.startsWith('image/')) {
        uploadImage(jot, files[i]);
      }
    }
  });
  el.addEventListener('paste', function(e) {
    var items = e.clipboardData && e.clipboardData.items;
    if (!items) return;
    for (var i = 0; i < items.length; i++) {
      if (items[i].type.startsWith('image/')) {
        var file = items[i].getAsFile();
        if (file) uploadImage(jot, file);
      }
    }
  });
}
