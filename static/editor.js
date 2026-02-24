import { Jot } from '/static/js/jot.js';
import { bindImageHandlers, uploadImage } from '/static/image-upload.js';

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
    bubbleMenu: true,
    imageBtn: true
  },
  onImage: function(file) {
    uploadImage(jot, file);
  }
});

editorEl.querySelector('.ProseMirror').focus();

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

bindImageHandlers(editorEl, jot);
