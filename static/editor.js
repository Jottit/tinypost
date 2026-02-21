import { Jot } from '/static/js/jot.js';

var editorEl = document.getElementById('editor');
var hiddenInput = document.querySelector('input[name="body"]');
var titleInput = document.querySelector('.editor-title');
var form = document.querySelector('form');

try {
  var draft = JSON.parse(localStorage.getItem('jottit-write-draft'));
  if (draft) {
    if (draft.title && !titleInput.value) titleInput.value = draft.title;
    if (draft.body && !hiddenInput.value) hiddenInput.value = draft.body;
    localStorage.removeItem('jottit-write-draft');
  }
} catch (e) {}

var jot = new Jot(editorEl, {
  initialValue: hiddenInput.value,
  onChange: function(markdown) {
    hiddenInput.value = markdown;
  },
  ui: {
    bubbleMenu: true
  }
});

if (editorEl.hasAttribute('autofocus')) {
  editorEl.querySelector('.ProseMirror').focus();
}

titleInput.addEventListener('keydown', function(e) {
  if (e.key === 'Enter') {
    e.preventDefault();
    editorEl.querySelector('.ProseMirror').focus();
  }
});

var draftCheckbox = form.querySelector('input[name="is_draft"]');
var submitBtn = form.querySelector('button[type="submit"]');
if (draftCheckbox.checked) submitBtn.textContent = 'Save draft';
draftCheckbox.addEventListener('change', function() {
  submitBtn.textContent = draftCheckbox.checked ? 'Save draft' : 'Publish';
});

var origTitle = titleInput.value;
var origBody = hiddenInput.value;
var submitting = false;

form.addEventListener('submit', function() {
  hiddenInput.value = jot.getValue();
  submitting = true;
});

window.addEventListener('beforeunload', function(e) {
  if (submitting) return;
  if (titleInput.value !== origTitle || jot.getValue() !== origBody) {
    e.preventDefault();
  }
});

var allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
var maxSize = 5 * 1024 * 1024;

function uploadImage(file) {
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

  fetch('/upload', { method: 'POST', body: data })
    .then(function(res) { return res.json(); })
    .then(function(json) {
      if (json.url) {
        var current = jot.getValue();
        jot.setValue(current + '\n![image](' + json.url + ')\n');
      } else {
        alert(json.error || 'Upload failed');
      }
    })
    .catch(function() {
      alert('Upload failed');
    });
}

editorEl.addEventListener('dragover', function(e) {
  e.preventDefault();
  editorEl.classList.add('drag-over');
});
editorEl.addEventListener('dragleave', function() {
  editorEl.classList.remove('drag-over');
});
editorEl.addEventListener('drop', function(e) {
  e.preventDefault();
  editorEl.classList.remove('drag-over');
  var files = e.dataTransfer.files;
  for (var i = 0; i < files.length; i++) {
    if (files[i].type.startsWith('image/')) {
      uploadImage(files[i]);
    }
  }
});
editorEl.addEventListener('paste', function(e) {
  var items = e.clipboardData && e.clipboardData.items;
  if (!items) return;
  for (var i = 0; i < items.length; i++) {
    if (items[i].type.startsWith('image/')) {
      var file = items[i].getAsFile();
      if (file) uploadImage(file);
    }
  }
});
