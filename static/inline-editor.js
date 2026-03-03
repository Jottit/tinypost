import { Jot } from '/static/js/jot.js';
import { bindImageHandlers } from '/static/image-upload.js';

var area = document.querySelector('.write-area');
var form = document.getElementById('inline-editor-form');
var editorEl = document.getElementById('inline-editor-body');
var hiddenInput = form.querySelector('input[name="body"]');
var titleInput = form.querySelector('input[name="title"]');
var STORAGE_KEY = 'tinypost-write-draft';
var jot = null;

function initEditor() {
  if (jot) return;
  jot = new Jot(editorEl, {
    onChange: function(markdown) {
      hiddenInput.value = markdown;
      updatePlaceholder();
    },
    ui: { bubbleMenu: true }
  });

  var pm = editorEl.querySelector('.ProseMirror');
  pm.setAttribute('data-placeholder', 'Start writing...');
  pm.classList.add('ProseMirror-empty');
  bindImageHandlers(editorEl, jot);
}

function updatePlaceholder() {
  var el = editorEl.querySelector('.ProseMirror');
  if (!el) return;
  el.classList.toggle('ProseMirror-empty', !jot.getValue().trim());
}

// If already open (empty blog), init immediately
if (area.classList.contains('write-area--open')) {
  initEditor();
  editorEl.querySelector('.ProseMirror').focus();
}

window.openWriteModal = function() {
  if (area.classList.contains('write-area--open')) {
    area.classList.remove('write-area--open');
    return;
  }

  initEditor();
  var draft = null;
  try {
    var raw = localStorage.getItem(STORAGE_KEY);
    if (raw) draft = JSON.parse(raw);
  } catch (e) {}
  if (draft) {
    titleInput.value = draft.title || '';
    if (draft.body) {
      jot.setValue(draft.body);
      hiddenInput.value = draft.body;
    }
    updatePlaceholder();
  }

  area.classList.add('write-area--open');
  editorEl.querySelector('.ProseMirror').focus();
};

window.expandInlineEditor = function() {
  var title = titleInput.value;
  var body = jot ? jot.getValue() : '';
  if (title.trim() || body.trim()) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ title: title, body: body }));
  }
  window.location.href = '/-/edit';
};

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

form.addEventListener('submit', function(e) {
  e.preventDefault();
  hiddenInput.value = jot ? jot.getValue() : '';

  var data = new FormData(form);
  fetch('/-/edit', {
    method: 'POST',
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    body: data
  })
    .then(function(res) {
      return res.json().then(function(json) {
        if (res.ok && json.slug) {
          localStorage.removeItem(STORAGE_KEY);
          window.location.href = '/';
        } else {
          showError(json.error || 'Something went wrong.');
        }
      });
    })
    .catch(function() {
      showError('Something went wrong.');
    });
});

function showError(msg) {
  var existing = form.querySelector('.inline-editor-error');
  if (existing) existing.remove();
  var el = document.createElement('p');
  el.className = 'inline-editor-error';
  el.textContent = msg;
  form.insertBefore(el, form.firstChild);
}
