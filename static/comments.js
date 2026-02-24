const form = document.querySelector('.comment-form');
if (form) {
  const slug = form.dataset.slug;
  const loggedIn = form.dataset.loggedIn === 'true';
  const fields = form.querySelector('.comment-fields');
  const textarea = form.querySelector('textarea');
  const submitBtn = form.querySelector('button[type="submit"]');
  const passcodeSection = form.querySelector('.comment-passcode');
  const verifyMsg = form.querySelector('.comment-verify-msg');
  const errorMsg = form.querySelector('.comment-error');
  const passcodeInputs = passcodeSection.querySelectorAll('.passcode-inputs input');

  // Progressive disclosure: show name/email fields on focus
  if (!loggedIn) {
    textarea.addEventListener('focus', () => {
      fields.classList.add('comment-fields--visible');
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    submitBtn.disabled = true;
    errorMsg.hidden = true;

    const data = new FormData(form);
    const res = await fetch(`/-/comment/${slug}`, { method: 'POST', body: data });
    const json = await res.json();

    if (json.status === 'ok') {
      window.location.reload();
    } else if (json.status === 'verify') {
      // Show passcode UI
      verifyMsg.textContent = `Enter the code sent to ${json.email}`;
      passcodeSection.hidden = false;
      submitBtn.hidden = true;
      textarea.disabled = true;
      fields.querySelectorAll('input').forEach(i => i.disabled = true);
      passcodeInputs[0].focus();
    } else {
      errorMsg.textContent = json.message;
      errorMsg.hidden = false;
      submitBtn.disabled = false;
    }
  });

  // Passcode input behavior (reuse pattern from passcode.js)
  function tryVerify() {
    const code = Array.from(passcodeInputs).map(el => el.value).join('');
    if (code.length === 6) {
      verifyPasscode(code);
    }
  }

  async function verifyPasscode(code) {
    passcodeInputs.forEach(i => i.disabled = true);
    errorMsg.hidden = true;

    const data = new FormData();
    data.append('passcode', code);
    const res = await fetch(`/-/comment/${slug}/verify`, { method: 'POST', body: data });
    const json = await res.json();

    if (json.status === 'ok') {
      window.location.reload();
    } else {
      errorMsg.textContent = json.message;
      errorMsg.hidden = false;
      passcodeInputs.forEach(i => { i.disabled = false; i.value = ''; });
      passcodeInputs[0].focus();
    }
  }

  passcodeInputs.forEach((input, i) => {
    input.addEventListener('input', () => {
      input.value = input.value.replace(/\D/g, '');
      if (input.value && i < passcodeInputs.length - 1) passcodeInputs[i + 1].focus();
      tryVerify();
    });
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace' && !input.value && i > 0) passcodeInputs[i - 1].focus();
    });
    input.addEventListener('paste', (e) => {
      const paste = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '');
      if (!paste) return;
      e.preventDefault();
      for (let j = 0; j < passcodeInputs.length && j < paste.length; j++) {
        passcodeInputs[j].value = paste[j];
      }
      passcodeInputs[Math.min(paste.length, passcodeInputs.length) - 1].focus();
      tryVerify();
    });
  });
}
