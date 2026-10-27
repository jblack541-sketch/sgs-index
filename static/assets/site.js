// Mobile nav
document.querySelectorAll('.nav-toggle').forEach(b => b.addEventListener('click', () => {
  const n = document.getElementById('nav'); const open = n.classList.toggle('open');
  b.setAttribute('aria-expanded', open);
}));
// Newsletter signup. Invalid email or missing consent stays on the page.
// A valid form posts normally to the provider (Kit).
document.querySelectorAll('form.signup').forEach(f => f.addEventListener('submit', ev => {
  const msg = f.querySelector('.form-msg'); const email = f.querySelector('input[type=email]');
  msg.className = 'form-msg small';
  if (!email.checkValidity()) { ev.preventDefault(); msg.textContent = 'Please enter a valid email address.'; msg.classList.add('err'); return; }
  if (!f.querySelector('input[name=consent]').checked) { ev.preventDefault(); msg.textContent = 'Please tick the consent box to sign up.'; msg.classList.add('err'); return; }
}));
