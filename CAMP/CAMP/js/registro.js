'use strict';

const $ = id => document.getElementById(id);
let rolSeleccionado = null;

/* ─── Selección de rol ─── */
function selectRole(rol) {
  rolSeleccionado = rol;
  document.querySelectorAll('.role-card').forEach(b => {
    b.classList.remove('selected');
    b.setAttribute('aria-pressed', 'false');
  });
  const btn = rol === 'Trabajador' ? $('btnTrabajador') : $('btnAgricultor');
  if (btn) {
    btn.classList.add('selected');
    btn.setAttribute('aria-pressed', 'true');
  }
  const h = $('hiddenRol');
  if (h) h.value = rol;
  clearErr('field-rol', 'err-rol');
}

/* ─── Toggle contraseña ─── */
function togglePwd(inputId, openId, closedId) {
  const input = $(inputId);
  if (!input) return;
  const show = input.type === 'password';
  input.type = show ? 'text' : 'password';
  $(openId).style.display   = show ? 'none' : '';
  $(closedId).style.display = show ? '' : 'none';
}

/* ─── Errores de campo ─── */
function setErr(fieldId, errId, msg) {
  const field = $(fieldId);
  const err   = $(errId);
  if (!err) return;
  if (msg) {
    field?.classList.add('error');
    err.textContent = msg;
  } else {
    field?.classList.remove('error');
    err.textContent = '';
  }
}
function clearErr(fieldId, errId) { setErr(fieldId, errId, ''); }

/* ─── Regex ─── */
const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const nameRe  = /^[A-Za-zÀ-ÿ\s]+$/;

/* ─── Validaciones individuales ─── */
function validateRol() {
  if (!rolSeleccionado) {
    setErr('field-rol', 'err-rol', 'Selecciona tu rol para continuar.');
    document.querySelectorAll('.role-card').forEach(p => {
      p.style.animation = 'none';
      p.offsetHeight;
      p.style.animation = 'shake .35s ease';
    });
    return false;
  }
  clearErr('field-rol', 'err-rol');
  return true;
}

function validateNombre() {
  const v = $('nombre')?.value.trim() ?? '';
  if (!v) { setErr('field-nombre', 'err-nombre', 'El nombre es requerido.'); return false; }
  if (!nameRe.test(v)) { setErr('field-nombre', 'err-nombre', 'Solo letras y espacios.'); return false; }
  clearErr('field-nombre', 'err-nombre');
  return true;
}

function validateApellido() {
  const v = $('apellido')?.value.trim() ?? '';
  if (!v) { setErr('field-apellido', 'err-apellido', 'El apellido es requerido.'); return false; }
  if (!nameRe.test(v)) { setErr('field-apellido', 'err-apellido', 'Solo letras y espacios.'); return false; }
  clearErr('field-apellido', 'err-apellido');
  return true;
}

function validateCorreo() {
  const v = $('correo')?.value.trim() ?? '';
  if (!v) { setErr('field-correo', 'err-correo', 'El correo es requerido.'); return false; }
  if (!emailRe.test(v)) { setErr('field-correo', 'err-correo', 'Ingresa un correo válido.'); return false; }
  clearErr('field-correo', 'err-correo');
  return true;
}

function validatePassword() {
  const v = $('password')?.value ?? '';
  if (!v) { setErr('field-password', 'err-password', 'La contraseña es requerida.'); return false; }
  if (v.length < 8) { setErr('field-password', 'err-password', 'Mínimo 8 caracteres.'); return false; }
  clearErr('field-password', 'err-password');
  return true;
}

function validateConfirm() {
  const pwd  = $('password')?.value ?? '';
  const conf = $('confirm_password')?.value ?? '';
  if (!conf) { setErr('field-confirm', 'err-confirm', 'Confirma tu contraseña.'); return false; }
  if (pwd !== conf) { setErr('field-confirm', 'err-confirm', 'Las contraseñas no coinciden.'); return false; }
  clearErr('field-confirm', 'err-confirm');
  return true;
}

function validateTerminos() {
  const checked = $('terminos')?.checked;
  const err = $('err-terminos');
  if (!checked) {
    if (err) err.textContent = 'Debes aceptar los términos.';
    return false;
  }
  if (err) err.textContent = '';
  return true;
}

/* ─── Submit del formulario ─── */
const form = $('registerForm');
if (form) {
  $('nombre')?.addEventListener('blur', validateNombre);
  $('apellido')?.addEventListener('blur', validateApellido);
  $('correo')?.addEventListener('blur', validateCorreo);
  $('password')?.addEventListener('blur', validatePassword);
  $('confirm_password')?.addEventListener('blur', validateConfirm);

  form.addEventListener('submit', e => {
    const ok = [
      validateRol(),
      validateNombre(),
      validateApellido(),
      validateCorreo(),
      validatePassword(),
      validateConfirm(),
      validateTerminos()
    ].every(Boolean);

    if (!ok) {
      e.preventDefault();
      form.querySelector('.error')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    const btn = $('btnRegister');
    if (btn) {
      btn.disabled = true;
      const t = btn.querySelector('.btn-text');
      if (t) t.textContent = 'Creando cuenta…';
    }
  });
}

/* ─── Modal de notificaciones ─── */
const NOTIF = {
  success: {
    ico: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    bg: 'rgba(74,122,52,.1)', border: 'rgba(74,122,52,.25)', color: '#4A7A34'
  },
  error: {
    ico: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
    bg: 'rgba(192,57,43,.09)', border: 'rgba(192,57,43,.25)', color: '#C0392B'
  },
  info: {
    ico: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    bg: 'rgba(36,60,80,.08)', border: 'rgba(36,60,80,.22)', color: '#243C50'
  },
};

function showNotif(type = 'info', title = '', message = '') {
  const m   = $('notifModal');
  const ico = $('notifIco');
  const t   = $('notifTitle');
  const msg = $('notifMsg');
  if (!m) return;
  const c = NOTIF[type] ?? NOTIF.info;
  ico.innerHTML = c.ico;
  Object.assign(ico.style, { background: c.bg, border: `1px solid ${c.border}`, color: c.color });
  const s = ico.querySelector('svg');
  if (s) Object.assign(s.style, { width: '26px', height: '26px', stroke: 'currentColor', fill: 'none' });
  t.textContent = title;
  msg.innerHTML = message;
  m.classList.add('open');
}

function closeNotif() {
  $('notifModal')?.classList.remove('open');
}

/* ─── Botones sociales (requieren rol) ─── */
const needRole = () => {
  showNotif('info', 'Selecciona tu rol', 'Primero elige si eres <strong>Trabajador</strong> o <strong>Agricultor</strong>.');
  document.querySelectorAll('.role-card').forEach(p => {
    p.style.animation = 'none';
    p.offsetHeight;
    p.style.animation = 'shake .35s ease';
  });
};

$('btnGoogle')?.addEventListener('click', () => {
  if (!rolSeleccionado) { needRole(); return; }
  window.location.href = `/auth/google/login?rol=${rolSeleccionado}`;
});

$('btnFacebook')?.addEventListener('click', () => {
  if (!rolSeleccionado) { needRole(); return; }
  window.location.href = `/auth/facebook/login?rol=${rolSeleccionado}`;
});

/* ─── Mensajes desde URL ─── */
const p = new URLSearchParams(window.location.search);
const urlMsg = p.get('message');
if (urlMsg) {
  showNotif(
    p.get('type') ?? 'info',
    p.get('title') ?? (p.get('type') === 'error' ? 'Error' : 'Información'),
    decodeURIComponent(urlMsg)
  );
  window.history.replaceState({}, '', window.location.pathname);
}

/* ─── Teclado y overlay del modal ─── */
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeNotif(); });
$('notifModal')?.addEventListener('click', e => { if (e.target === $('notifModal')) closeNotif(); });