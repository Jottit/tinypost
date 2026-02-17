var ta = document.querySelector('.editor-body');
var titleInput = document.querySelector('.editor-title');
var form = document.querySelector('form');

function autoExpand() {
  ta.style.height = 'auto';
  ta.style.height = ta.scrollHeight + 'px';
}

ta.addEventListener('input', autoExpand);
autoExpand();

titleInput.addEventListener('keydown', function(e) {
  if (e.key === 'Enter') { e.preventDefault(); ta.focus(); }
});

var origTitle = titleInput.value;
var origBody = ta.value;
var submitting = false;

form.addEventListener('submit', function() { submitting = true; });
window.addEventListener('beforeunload', function(e) {
  if (submitting) return;
  if (titleInput.value !== origTitle || ta.value !== origBody) { e.preventDefault(); }
});

var allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
var maxSize = 5 * 1024 * 1024;

function insertAtCursor(text) {
  var start = ta.selectionStart;
  ta.value = ta.value.slice(0, start) + text + ta.value.slice(ta.selectionEnd);
  ta.selectionStart = ta.selectionEnd = start + text.length;
  autoExpand();
}

function removePlaceholder(placeholder) {
  ta.value = ta.value.replace(placeholder, '');
  autoExpand();
}

function uploadImage(file) {
  if (allowedTypes.indexOf(file.type) === -1) {
    alert('Only jpg, png, gif, and webp images are allowed.');
    return;
  }
  if (file.size > maxSize) {
    alert('Image must be under 5MB.');
    return;
  }

  var placeholder = '![Uploading...]()\n';
  insertAtCursor(placeholder);

  var data = new FormData();
  data.append('file', file);

  fetch('/upload', { method: 'POST', body: data })
    .then(function(res) { return res.json(); })
    .then(function(json) {
      if (json.url) {
        ta.value = ta.value.replace(placeholder, '![image](' + json.url + ')\n');
        autoExpand();
      } else {
        removePlaceholder(placeholder);
        alert(json.error || 'Upload failed');
      }
    })
    .catch(function() {
      removePlaceholder(placeholder);
      alert('Upload failed');
    });
}

ta.addEventListener('dragover', function(e) {
  e.preventDefault();
  ta.classList.add('drag-over');
});
ta.addEventListener('dragleave', function() {
  ta.classList.remove('drag-over');
});
ta.addEventListener('drop', function(e) {
  e.preventDefault();
  ta.classList.remove('drag-over');
  var files = e.dataTransfer.files;
  for (var i = 0; i < files.length; i++) {
    if (files[i].type.startsWith('image/')) {
      uploadImage(files[i]);
    }
  }
});
ta.addEventListener('paste', function(e) {
  var items = e.clipboardData && e.clipboardData.items;
  if (!items) return;
  for (var i = 0; i < items.length; i++) {
    if (items[i].type.startsWith('image/')) {
      var file = items[i].getAsFile();
      if (file) uploadImage(file);
    }
  }
});
