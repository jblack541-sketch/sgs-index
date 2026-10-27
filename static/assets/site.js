// Mobile nav
document.querySelectorAll('.nav-toggle').forEach(b => b.addEventListener('click', () => {
  const n = document.getElementById('nav'); const open = n.classList.toggle('open');
  b.setAttribute('aria-expanded', open);
}));
// Newsletter signup. While the form action is still the "#..." placeholder,
// nothing is sent anywhere and the visitor is told so.
document.querySelectorAll('form.signup').forEach(f => f.addEventListener('submit', ev => {
  const msg = f.querySelector('.form-msg'); const email = f.querySelector('input[type=email]');
  msg.className = 'form-msg small';
  if (!email.checkValidity()) { ev.preventDefault(); msg.textContent = 'Please enter a valid email address.'; msg.classList.add('err'); return; }
  if (!f.querySelector('input[name=consent]').checked) { ev.preventDefault(); msg.textContent = 'Please tick the consent box to sign up.'; msg.classList.add('err'); return; }
  if (f.dataset.placeholder === 'true') {
    ev.preventDefault();
    msg.textContent = "Thanks! Signups aren't live yet, so your email was not sent or stored. Please check back soon.";
    msg.classList.add('ok');
  }
}));
