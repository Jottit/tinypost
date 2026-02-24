import { Jot } from '/static/js/jot.js';
import { bindImageHandlers, uploadImage } from '/static/image-upload.js';

var editorEl = document.getElementById('editor');
var hiddenInput = document.querySelector('input[name="body"]');
var titleInput = document.querySelector('.editor-title');
var form = document.querySelector('form');
var STORAGE_KEY = 'jottit-write-draft';
var isNewPost = !titleInput.value && !hiddenInput.value;
var saveTimer = null;

if (isNewPost) {
  try {
    var draft = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (draft) {
      if (draft.title) titleInput.value = draft.title;
      if (draft.body) hiddenInput.value = draft.body;
    }
  } catch (e) {}
}

var jot = new Jot(editorEl, {
  initialValue: hiddenInput.value,
  onChange: function(markdown) {
    hiddenInput.value = markdown;
    if (isNewPost) saveDraft();
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

if (isNewPost) {
  titleInput.addEventListener('input', saveDraft);
}

function saveDraft() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(function() {
    var title = titleInput.value;
    var body = jot.getValue();
    if (title.trim() || body.trim()) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ title: title, body: body }));
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
  var title = titleInput.value;
  var body = jot.getValue();
  if (title.trim() || body.trim()) {
    e.preventDefault();
    if (confirm('You have unsaved changes. Discard them?')) {
      clearDraft();
      window.location.href = cancelLink.href;
    }
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
