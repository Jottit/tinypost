import { Jot } from '/static/js/jot.js';
import { bindImageHandlers } from '/static/image-upload.js';

var wrapper = document.querySelector('.inline-editor');
var writeBtn = document.querySelector('.write-pill');
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

// If editor is already visible (empty blog), init immediately and hide write pill
if (!wrapper.hidden) {
  initEditor();
  if (writeBtn) writeBtn.classList.add('write-pill--hidden');
}

function hideWriteBtn() {
  if (!writeBtn) return;
  writeBtn.style.display = 'none';
}

function showWriteBtn() {
  if (!writeBtn) return;
  writeBtn.style.display = '';
  // Force reflow so transition plays
  writeBtn.offsetHeight;
  writeBtn.classList.remove('write-pill--hidden');
}

// Override openWriteModal so "+ Write" toggles the inline editor
window.openWriteModal = function() {
  if (!wrapper.hidden) {
    wrapper.classList.remove('inline-editor--slide-in');
    wrapper.classList.add('inline-editor--slide-out');
    wrapper.addEventListener('animationend', function() {
      wrapper.hidden = true;
      wrapper.classList.remove('inline-editor--slide-out');
      showWriteBtn();
    }, { once: true });
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
  hideWriteBtn();
  wrapper.hidden = false;
  wrapper.classList.add('inline-editor--slide-in');
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
