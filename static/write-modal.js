import { Jot } from '/static/js/jot.js';
import { bindImageHandlers, uploadImage } from '/static/image-upload.js';

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
      bubbleMenu: true,
      imageBtn: true
    },
    onImage: function(file) {
      uploadImage(jot, file);
    }
  });
  var pm = editorEl.querySelector('.ProseMirror');
  pm.setAttribute('data-placeholder', 'Start writing...');
  pm.classList.add('ProseMirror-empty');
  bindImageHandlers(editorEl, jot);
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
  editorEl.querySelector('.ProseMirror').focus();
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
  window.location.href = '/-/edit';
};

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape' && !modal.hidden) {
    closeWriteModal();
  }
});

titleInput.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' || e.key === 'ArrowDown') {
    e.preventDefault();
    editorEl.querySelector('.ProseMirror').focus();
  }
});

editorEl.addEventListener('keydown', function(e) {
  if (e.key === 'ArrowUp' && jot && jot.isAtStart()) {
    e.preventDefault();
    titleInput.focus();
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
  fetch('/-/edit', {
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
