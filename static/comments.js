const form = document.querySelector('.comment-form');
if (form) {
  const slug = form.dataset.slug;
  const loggedIn = form.dataset.loggedIn === 'true';
  const fields = form.querySelector('.comment-fields');
  const textarea = form.querySelector('textarea');
  const submitBtn = form.querySelector('.comment-submit');
  const footer = form.querySelector('.comment-form-footer');
  const identity = form.querySelector('.comment-identity');
  const identityName = form.querySelector('.comment-identity-name');
  const notYouLink = form.querySelector('.comment-not-you');
  const passcodeSection = form.querySelector('.comment-passcode');
  const verifyMsg = form.querySelector('.comment-verify-msg');
  const errorMsg = form.querySelector('.comment-error');
  const passcodeInputs = passcodeSection.querySelectorAll('.passcode-inputs input');

  const nameInput = fields.querySelector('input[name="name"]');
  const emailInput = fields.querySelector('input[name="email"]');
  const savedName = localStorage.getItem('jottit_comment_name');
  const savedEmail = localStorage.getItem('jottit_comment_email');
  if (savedName) nameInput.value = savedName;
  if (savedEmail && emailInput) emailInput.value = savedEmail;

  const hasSavedIdentity = !!(savedName && (loggedIn || savedEmail));

  // "Not you?" link clears saved identity and shows fields
  notYouLink.addEventListener('click', (e) => {
    e.preventDefault();
    identity.hidden = true;
    fields.classList.add('comment-fields--visible');
    nameInput.focus();
  });

  // Progressive disclosure on textarea focus
  let fieldsRevealed = false;
  textarea.addEventListener('focus', () => {
    if (fieldsRevealed) return;
    fieldsRevealed = true;
    footer.classList.add('comment-form-footer--visible');
    submitBtn.classList.add('comment-submit--visible');
    updateSubmit();
    if (hasSavedIdentity) {
      identityName.textContent = savedName;
      identity.hidden = false;
    } else {
      fields.classList.add('comment-fields--visible');
      if (!nameInput.value.trim()) {
        nameInput.focus();
      } else if (emailInput && !emailInput.value.trim()) {
        emailInput.focus();
      }
    }
  });

  textarea.addEventListener('input', updateSubmit);

  function updateSubmit() {
    submitBtn.disabled = !textarea.value.trim();
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    submitBtn.disabled = true;
    errorMsg.hidden = true;

    const data = new FormData(form);
    const res = await fetch(`/-/comment/${slug}`, { method: 'POST', body: data });
    const json = await res.json();

    if (json.status === 'ok') {
      localStorage.setItem('jottit_comment_name', nameInput.value.trim());
      if (emailInput) localStorage.setItem('jottit_comment_email', emailInput.value.trim());
      window.location.reload();
    } else if (json.status === 'verify') {
      verifyMsg.textContent = `Enter the code sent to ${json.email}`;
      passcodeSection.hidden = false;
      submitBtn.classList.remove('comment-submit--visible');
      identity.hidden = true;
      textarea.disabled = true;
      fields.querySelectorAll('input').forEach(i => i.disabled = true);
      passcodeInputs[0].focus();
      passcodeSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } else {
      errorMsg.textContent = json.message;
      errorMsg.hidden = false;
      submitBtn.disabled = false;
    }
  });

  // Passcode input behavior
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
      localStorage.setItem('jottit_comment_name', nameInput.value.trim());
      if (emailInput) localStorage.setItem('jottit_comment_email', emailInput.value.trim());
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
