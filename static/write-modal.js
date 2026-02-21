import { Jot } from '/static/js/jot.js';

var modal = document.getElementById('write-modal');
var form = document.getElementById('write-modal-form');
var editorEl = document.getElementById('write-modal-editor');
var hiddenInput = form.querySelector('input[name="body"]');
var titleInput = form.querySelector('input[name="title"]');
var jot = null;
var saveTimer = null;
var STORAGE_KEY = 'jottit-write-draft';

function saveDraftNow() {
  clearTimeout(saveTimer);
  var title = titleInput.value;
  var body = jot ? jot.getValue() : '';
  if (title.trim() || body.trim()) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ title: title, body: body }));
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
}

function saveDraft() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveDraftNow, 500);
}

function loadDraft() {
  try {
    var raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch (e) {}
  return null;
}

function clearDraft() {
  clearTimeout(saveTimer);
  localStorage.removeItem(STORAGE_KEY);
}

function updatePlaceholder() {
  var pm = editorEl.querySelector('.ProseMirror');
  if (!pm) return;
  var isEmpty = !jot.getValue().trim();
  pm.classList.toggle('ProseMirror-empty', isEmpty);
}

function initEditor() {
  if (jot) return;
  jot = new Jot(editorEl, {
    onChange: function(markdown) {
      hiddenInput.value = markdown;
      updatePlaceholder();
      saveDraft();
    },
    ui: {
      bubbleMenu: true
    }
  });
  var pm = editorEl.querySelector('.ProseMirror');
  pm.setAttribute('data-placeholder', 'Start writing...');
  pm.classList.add('ProseMirror-empty');
}

function resetForm() {
  titleInput.value = '';
  hiddenInput.value = '';
  if (jot) {
    jot.setValue('');
    var pm = editorEl.querySelector('.ProseMirror');
    if (pm) pm.classList.add('ProseMirror-empty');
  }
  var errorEl = form.querySelector('.write-modal-error');
  if (errorEl) errorEl.remove();
}

function isDirty() {
  return titleInput.value.trim() !== '' || (jot && jot.getValue().trim() !== '');
}

window.openWriteModal = function() {
  initEditor();
  var draft = loadDraft();
  if (draft) {
    titleInput.value = draft.title || '';
    if (draft.body) {
      jot.setValue(draft.body);
      hiddenInput.value = draft.body;
    }
    updatePlaceholder();
  }
  modal.hidden = false;
  document.body.style.overflow = 'hidden';
  titleInput.focus();
};

window.closeWriteModal = function() {
  modal.hidden = true;
  document.body.style.overflow = '';
};

window.cancelWriteModal = function() {
  if (isDirty() && !confirm('You have unsaved changes. Discard them?')) return;
  clearDraft();
  resetForm();
  modal.hidden = true;
  document.body.style.overflow = '';
};

window.expandWriteModal = function() {
  saveDraftNow();
  window.location.href = '/edit';
};

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape' && !modal.hidden) {
    closeWriteModal();
  }
});

titleInput.addEventListener('keydown', function(e) {
  if (e.key === 'Enter') {
    e.preventDefault();
    editorEl.querySelector('.ProseMirror').focus();
  }
});

titleInput.addEventListener('input', saveDraft);

var draftCheckbox = form.querySelector('input[name="is_draft"]');
var submitBtn = form.querySelector('button[type="submit"]');
draftCheckbox.addEventListener('change', function() {
  submitBtn.textContent = draftCheckbox.checked ? 'Save draft' : 'Publish';
});

form.addEventListener('submit', function(e) {
  e.preventDefault();
  hiddenInput.value = jot ? jot.getValue() : '';

  var data = new FormData(form);
  fetch('/edit', {
    method: 'POST',
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    body: data
  })
    .then(function(res) { return res.json().then(function(json) { return { ok: res.ok, json: json }; }); })
    .then(function(result) {
      if (result.ok && result.json.slug) {
        clearDraft();
        window.location.href = '/' + result.json.slug;
      } else {
        showError(result.json.error || 'Something went wrong.');
      }
    })
    .catch(function() {
      showError('Something went wrong.');
    });
});

function showError(msg) {
  var existing = form.querySelector('.write-modal-error');
  if (existing) existing.remove();
  var el = document.createElement('p');
  el.className = 'write-modal-error';
  el.textContent = msg;
  form.insertBefore(el, form.firstChild);
}

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
