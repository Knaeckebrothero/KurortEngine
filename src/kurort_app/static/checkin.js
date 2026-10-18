/* AVS crib sheet; delegated handler also covers htmx-replaced guest cards. */
document.addEventListener('click', async (event) => {
  const button = event.target.closest('[data-copy]');
  if (!button) return;
  const value = button.dataset.copy;
  try {
    await navigator.clipboard.writeText(value);
    const original = button.textContent;
    button.textContent = 'Kopiert';
    setTimeout(() => { button.textContent = original; }, 2000);
  } catch {
    const text = document.createElement('textarea');
    text.value = value;
    text.setAttribute('aria-label', 'Zum Kopieren auswählen');
    button.after(text);
    text.focus();
    text.select();
    text.addEventListener('blur', () => text.remove(), {once: true});
  }
});
