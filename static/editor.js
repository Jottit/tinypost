import { Jot } from '/static/js/jot.js';
import { bindImageHandlers, uploadImage } from '/static/image-upload.js';

var editorEl = document.getElementById('editor');
var hiddenInput = document.querySelector('input[name="body"]');
var titleInput = document.querySelector('.editor-title');
var form = document.querySelector('form');
var saveTimer = null;

var formAction = form.getAttribute('action');
var slug = formAction.replace('/-/edit', '').replace(/^\//, '');
var STORAGE_KEY = slug ? 'jottit-draft-' + slug : 'jottit-write-draft';
var CURSOR_KEY = slug ? 'jottit-cursor-' + slug : 'jottit-cursor-new';

var draftRestored = false;
try {
  var draft = JSON.parse(localStorage.getItem(STORAGE_KEY));
  if (draft) {
    if (draft.title) titleInput.value = draft.title;
    if (draft.body) hiddenInput.value = draft.body;
    draftRestored = true;
  }
} catch (e) {}

var savedCursor = parseInt(localStorage.getItem(CURSOR_KEY), 10) || 0;

var origTitle = titleInput.value;
var origBody = hiddenInput.value;

var jot = new Jot(editorEl, {
  initialValue: hiddenInput.value,
  onChange: function(markdown) {
    hiddenInput.value = markdown;
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

editorEl.querySelector('.ProseMirror').focus();

if (savedCursor) {
  jot.setCursor(savedCursor);
}

if (draftRestored) {
  showToast('Unsaved changes restored');
}

function showToast(message) {
  var toast = document.createElement('div');
  toast.className = 'editor-toast';
  toast.textContent = message;
  document.body.appendChild(toast);
  requestAnimationFrame(function() {
    toast.classList.add('editor-toast-visible');
  });
  setTimeout(function() {
    toast.classList.remove('editor-toast-visible');
    toast.addEventListener('transitionend', function() { toast.remove(); });
  }, 3000);
}

titleInput.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' || e.key === 'ArrowDown') {
    e.preventDefault();
    editorEl.querySelector('.ProseMirror').focus();
  }
});

editorEl.addEventListener('keydown', function(e) {
  if (e.key === 'ArrowUp' && jot.isAtStart()) {
    e.preventDefault();
    titleInput.focus();
  }
});

titleInput.addEventListener('input', saveDraft);

function isDirty() {
  return titleInput.value !== origTitle || jot.getValue() !== origBody;
}

function saveDraft() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(function() {
    localStorage.setItem(CURSOR_KEY, jot.getCursor());
    if (isDirty()) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        title: titleInput.value,
        body: jot.getValue()
      }));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, 500);
}

function clearDraft() {
  clearTimeout(saveTimer);
  localStorage.removeItem(STORAGE_KEY);
}

var cancelLink = form.querySelector('a.btn');
cancelLink.addEventListener('click', function(e) {
  if (!isDirty()) return;
  e.preventDefault();
  if (confirm('You have unsaved changes. Discard them?')) {
    clearDraft();
    window.location.href = cancelLink.href;
  }
});

var draftCheckbox = form.querySelector('input[name="is_draft"]');
var submitBtn = form.querySelector('button[type="submit"]');
if (draftCheckbox.checked) submitBtn.textContent = 'Save draft';
draftCheckbox.addEventListener('change', function() {
  submitBtn.textContent = draftCheckbox.checked ? 'Save draft' : 'Publish';
});

form.addEventListener('submit', function() {
  hiddenInput.value = jot.getValue();
  clearDraft();
});

bindImageHandlers(editorEl, jot);
