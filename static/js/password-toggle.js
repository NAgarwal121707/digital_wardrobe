document.querySelectorAll('.password-wrap').forEach((wrap) => {
  const input = wrap.querySelector('input');
  const button = wrap.querySelector('.password-toggle');
  if (!input || !button) return;
  button.addEventListener('click', () => {
    const showing = input.type === 'text';
    input.type = showing ? 'password' : 'text';
    button.textContent = showing ? '👁' : '🙈';
    button.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
  });
});
