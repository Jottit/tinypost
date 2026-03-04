const inputs = document.querySelectorAll('.passcode-inputs input');
const hidden = document.getElementById('passcode-value');
const form = document.querySelector('.passcode-form');

function collectCode() {
  return Array.from(inputs).map(el => el.value).join('');
}

function trySubmit() {
  const code = collectCode();
  if (code.length === 6) {
    hidden.value = code;
    form.submit();
  }
}

form.addEventListener('submit', () => {
  hidden.value = collectCode();
});

inputs.forEach((input, i) => {
  input.addEventListener('input', () => {
    input.value = input.value.replace(/\D/g, '');
    if (input.value && i < inputs.length - 1) inputs[i + 1].focus();
    trySubmit();
  });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Backspace' && !input.value && i > 0) inputs[i - 1].focus();
  });
  input.addEventListener('paste', (e) => {
    const paste = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '');
    if (!paste) return;
    e.preventDefault();
    for (let j = 0; j < inputs.length && j < paste.length; j++) {
      inputs[j].value = paste[j];
    }
    inputs[Math.min(paste.length, inputs.length) - 1].focus();
    trySubmit();
  });
});
