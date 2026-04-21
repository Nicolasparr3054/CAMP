'use strict';

/* ================================================================
   CAMP — login-trabajador.js
   ================================================================ */

const $ = (id) => document.getElementById(id);

/* ────────────────────────────────────────────────
   1. TOGGLE CONTRASEÑA
   ──────────────────────────────────────────────── */
function togglePassword() {
  const input     = $('password');
  const eyeOpen   = $('eye-open');
  const eyeClosed = $('eye-closed');
  if (!input) return;
  const show = input.type === 'password';
  input.type              = show ? 'text'  : 'password';
  eyeOpen.style.display   = show ? 'none'  : 'block';
  eyeClosed.style.display = show ? 'block' : 'none';
}

/* ────────────────────────────────────────────────
   2. VALIDACIÓN
   ──────────────────────────────────────────────── */
function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

function setError(inputId, errId, msg) {
  const input  = $(inputId);
  const errEl  = $(errId);
  if (!input || !errEl) return;
  const field = input.closest('.field');
  if (msg) { field?.classList.add('error');    errEl.textContent = msg; }
  else      { field?.classList.remove('error'); errEl.textContent = ''; }
}

function validateEmail() {
  const val = $('email')?.value.trim() ?? '';
  if (!val)               { setError('email','err-email','El correo es requerido.');   return false; }
  if (!isValidEmail(val)) { setError('email','err-email','Ingresa un correo válido.'); return false; }
  setError('email','err-email',''); return true;
}

function validatePassword() {
  const val = $('password')?.value ?? '';
  if (!val)          { setError('password','err-password','La contraseña es requerida.'); return false; }
  if (val.length < 6){ setError('password','err-password','Mínimo 6 caracteres.');        return false; }
  setError('password','err-password',''); return true;
}

/* ────────────────────────────────────────────────
   3. FORMULARIO DE LOGIN
   ──────────────────────────────────────────────── */
function initLoginForm() {
  const form = $('loginForm');
  if (!form) return;

  $('email')?.addEventListener('blur', validateEmail);
  $('password')?.addEventListener('blur', validatePassword);

  form.addEventListener('submit', function (e) {
    const ok = validateEmail() & validatePassword();
    if (!ok) { e.preventDefault(); return; }
    const btn = $('btnLogin');
    if (btn) {
      btn.disabled = true;
      const txt = btn.querySelector('.btn-text');
      if (txt) txt.textContent = 'Ingresando…';
    }
  });
}

/* ────────────────────────────────────────────────
   4. REDES SOCIALES
   ──────────────────────────────────────────────── */
function continueWithGoogle() {
  showNotif('info','Redirigiendo a Google','Serás llevado al inicio de sesión con tu cuenta de Google.');
  setTimeout(() => { window.location.href = '/auth/google/login'; }, 900);
}
function continueWithFacebook() {
  showNotif('info','Redirigiendo a Facebook','Serás llevado al inicio de sesión con tu cuenta de Facebook.');
  setTimeout(() => { window.location.href = '/auth/facebook/login'; }, 900);
}

/* ────────────────────────────────────────────────
   5. MODAL — RECUPERAR CONTRASEÑA
   ──────────────────────────────────────────────── */
function openForgotModal() {
  const modal = $('forgotModal');
  if (!modal) return;
  modal.classList.add('open');
  const inp = $('forgotEmail');
  if (inp) { inp.value = ''; setTimeout(() => inp.focus(), 120); }
  const errEl = $('err-forgot');
  if (errEl) errEl.textContent = '';
  inp?.closest('.field')?.classList.remove('error');
}

function closeForgotModal() {
  $('forgotModal')?.classList.remove('open');
}

function initForgotForm() {
  const form = $('forgotPasswordForm');
  if (!form) return;

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    const emailInput = $('forgotEmail');
    const email      = emailInput?.value.trim() ?? '';
    const errEl      = $('err-forgot');

    if (!email) {
      if (errEl) errEl.textContent = 'Por favor ingresa tu correo electrónico.';
      emailInput?.closest('.field')?.classList.add('error');
      emailInput?.focus(); return;
    }
    if (!isValidEmail(email)) {
      if (errEl) errEl.textContent = 'Ingresa un correo electrónico válido.';
      emailInput?.closest('.field')?.classList.add('error');
      emailInput?.focus(); return;
    }

    const btn  = $('btnForgot');
    const orig = btn?.querySelector('.btn-text')?.textContent ?? 'Enviar enlace de recuperación';
    if (btn) { btn.disabled = true; const t = btn.querySelector('.btn-text'); if (t) t.textContent = 'Enviando…'; }

    try {
      const res  = await fetch('/api/request-password-reset', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();

      if (data.success) {
        closeForgotModal();
        showNotif('success','¡Correo enviado!',
          `Enviamos un enlace a <strong>${email}</strong>.<br>
           Revisa también tu carpeta de spam.<br>
           El enlace expirará en <strong>30 minutos</strong>.`
        );
        form.reset();
      } else {
        showNotif('error','Error', data.message || 'No pudimos procesar tu solicitud. Intenta nuevamente.');
      }
    } catch {
      showNotif('error','Sin conexión','Verifica tu conexión a internet e intenta de nuevo.');
    } finally {
      if (btn) { btn.disabled = false; const t = btn.querySelector('.btn-text'); if (t) t.textContent = orig; }
    }
  });
}

/* ────────────────────────────────────────────────
   6. NOTIFICACIONES
   ──────────────────────────────────────────────── */
const NOTIF = {
  success: { ico:`<svg viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`, bg:'rgba(74,122,52,.09)', border:'rgba(74,122,52,.22)', color:'#4A7A34' },
  error:   { ico:`<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`, bg:'rgba(192,57,43,.08)', border:'rgba(192,57,43,.22)', color:'#C0392B' },
  info:    { ico:`<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`, bg:'rgba(36,60,80,.08)', border:'rgba(36,60,80,.22)', color:'#243C50' },
};

function showNotif(type = 'info', title = '', message = '') {
  const modal   = $('notifModal');
  const icoWrap = $('notifIco');
  const titleEl = $('notifTitle');
  const msgEl   = $('notifMsg');
  if (!modal) return;

  const cfg = NOTIF[type] ?? NOTIF.info;
  icoWrap.innerHTML = cfg.ico;
  Object.assign(icoWrap.style, { background: cfg.bg, border: `1px solid ${cfg.border}`, color: cfg.color });
  const svg = icoWrap.querySelector('svg');
  if (svg) Object.assign(svg.style, { width:'28px', height:'28px', stroke:'currentColor', fill:'none', strokeWidth:'1.5', strokeLinecap:'round', strokeLinejoin:'round' });

  titleEl.textContent = title;
  msgEl.innerHTML     = message;
  modal.classList.add('open');
}

function closeNotif() { $('notifModal')?.classList.remove('open'); }

/* ────────────────────────────────────────────────
   7. COMPORTAMIENTOS DE MODALES
   ──────────────────────────────────────────────── */
function initModalBehaviors() {
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    closeForgotModal(); closeNotif();
  });
  [$('forgotModal'), $('notifModal')].forEach(o => {
    o?.addEventListener('click', (e) => { if (e.target === o) o.classList.remove('open'); });
  });
}

/* ────────────────────────────────────────────────
   8. MENSAJES DESDE URL
   ──────────────────────────────────────────────── */
function checkUrlMessages() {
  const p = new URLSearchParams(window.location.search);
  const msg = p.get('message'); if (!msg) return;
  const type  = p.get('type')  ?? 'info';
  const title = p.get('title') ?? (type === 'error' ? 'Error' : 'Información');
  showNotif(type, title, decodeURIComponent(msg));
  window.history.replaceState({}, document.title, window.location.pathname);
}

/* ── INIT ── */
document.addEventListener('DOMContentLoaded', () => {
  initLoginForm();
  initForgotForm();
  initModalBehaviors();
  checkUrlMessages();
});