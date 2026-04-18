/**
 * ════════════════════════════════════════════════
 *  CAMP — Script principal · app.js
 *
 *  MÓDULOS:
 *  1. Cursor personalizado (dot + ring con lerp)
 *  2. Header (.scrolled al hacer scroll)
 *  3. Canvas de partículas (hero)
 *  4. Animaciones de entrada (IntersectionObserver)
 *  5. Contadores animados
 *  6. Tabs de beneficios
 *  7. Botón volver arriba
 *  8. Nav activa por scroll
 *  9. Inicialización
 * ════════════════════════════════════════════════
 */

'use strict';


/* ─── Referencias al DOM ─── */
const dom = {
  header:   document.getElementById('header'),
  navLinks: document.querySelectorAll('.nav-lnk'),
  canvas:   document.getElementById('particles'),
  anims:    document.querySelectorAll('[data-anim]'),
  counters: document.querySelectorAll('[data-count]'),
  tabBtns:  document.querySelectorAll('.tab-btn'),
  tabPanes: document.querySelectorAll('.tab-panel'),
  backTop:  document.getElementById('backTop'),
  sections: document.querySelectorAll('section[id]'),
  curDot:   document.getElementById('curDot'),
  curRing:  document.getElementById('curRing'),
};


/* ════════════════════════════════════════
   1. CURSOR PERSONALIZADO
   Punto sigue cursor exactamente.
   Anillo usa lerp (interpolación lineal) para retraso suave.
════════════════════════════════════════ */
const Cursor = {
  mx: 0, my: 0,   /* Posición real del mouse */
  rx: 0, ry: 0,   /* Posición actual del anillo */
  LERP: 0.11,

  onMove(e) {
    this.mx = e.clientX;
    this.my = e.clientY;
    dom.curDot.style.left = e.clientX + 'px';
    dom.curDot.style.top  = e.clientY + 'px';
  },

  loop() {
    this.rx += (this.mx - this.rx) * this.LERP;
    this.ry += (this.my - this.ry) * this.LERP;
    dom.curRing.style.left = this.rx + 'px';
    dom.curRing.style.top  = this.ry + 'px';
    requestAnimationFrame(() => this.loop());
  },

  init() {
    if (!dom.curDot || !dom.curRing) return;
    document.addEventListener('mousemove', e => this.onMove(e));

    /* Expandir cursor en elementos interactivos */
    document.querySelectorAll('a, button, .ben-card, .test-card, .step, .value-list li').forEach(el => {
      el.addEventListener('mouseenter', () => document.body.classList.add('c-hover'));
      el.addEventListener('mouseleave', () => document.body.classList.remove('c-hover'));
    });

    this.rx = window.innerWidth  / 2;
    this.ry = window.innerHeight / 2;
    this.loop();
  },
};


/* ════════════════════════════════════════
   2. HEADER
   Añade .scrolled al pasar el umbral de scroll.
════════════════════════════════════════ */
const Header = {
  THRESHOLD: 64,
  update() { dom.header.classList.toggle('scrolled', window.scrollY > this.THRESHOLD); },
  init() {
    if (!dom.header) return;
    window.addEventListener('scroll', () => this.update(), { passive: true });
    this.update();
  },
};


/* ════════════════════════════════════════
   3. CANVAS DE PARTÍCULAS
   Partículas verdes claras flotando en el hero.
   Reaccionan al cursor con repulsión suave.
   Conexiones entre partículas cercanas.
════════════════════════════════════════ */
const Particles = {
  canvas: null, ctx: null, items: [],
  mouse: { x: null, y: null, r: 85 },

  make() {
    const cols = ['rgba(58,173,90,OP)', 'rgba(144,238,144,OP)', 'rgba(90,158,111,OP)'];
    return {
      x: Math.random() * this.canvas.width,
      y: Math.random() * this.canvas.height,
      r: Math.random() * 1.6 + 0.5,
      vx: (Math.random() - 0.5) * 0.28,
      vy: -(Math.random() * 0.22 + 0.07),
      op: Math.random() * 0.35 + 0.05,
      tOp: Math.random() * 0.35 + 0.05,
      ops: Math.random() * 0.004 + 0.002,
      col: cols[Math.floor(Math.random() * cols.length)],
    };
  },

  resize() {
    this.canvas.width  = this.canvas.offsetWidth;
    this.canvas.height = this.canvas.offsetHeight;
  },

  populate() {
    const n = Math.min(75, Math.floor((this.canvas.width * this.canvas.height) / 16000));
    this.items = Array.from({ length: n }, () => this.make());
  },

  update(p) {
    p.x += p.vx;
    p.y += p.vy;

    if (this.mouse.x !== null) {
      const dx = p.x - this.mouse.x;
      const dy = p.y - this.mouse.y;
      const d  = Math.sqrt(dx * dx + dy * dy);
      if (d < this.mouse.r) {
        const f = (this.mouse.r - d) / this.mouse.r;
        p.x += Math.cos(Math.atan2(dy, dx)) * f * 2;
        p.y += Math.sin(Math.atan2(dy, dx)) * f * 2;
      }
    }

    /* Parpadeo */
    if (Math.abs(p.op - p.tOp) < p.ops) p.tOp = Math.random() * 0.35 + 0.05;
    else p.op += p.op < p.tOp ? p.ops : -p.ops;

    /* Reaparición */
    if (p.y < -6) { p.y = this.canvas.height + 6; p.x = Math.random() * this.canvas.width; }
    if (p.x < -6) p.x = this.canvas.width + 6;
    if (p.x > this.canvas.width  + 6) p.x = -6;
    if (p.y > this.canvas.height + 6) p.y = -6;
  },

  draw(p) {
    this.ctx.beginPath();
    this.ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    this.ctx.fillStyle = p.col.replace('OP', p.op.toFixed(2));
    this.ctx.shadowBlur  = 5;
    this.ctx.shadowColor = 'rgba(58,173,90,0.18)';
    this.ctx.fill();
    this.ctx.shadowBlur  = 0;
  },

  connect(a, b, d) {
    if (d > 88) return;
    const op = (1 - d / 88) * 0.08;
    this.ctx.beginPath();
    this.ctx.moveTo(a.x, a.y);
    this.ctx.lineTo(b.x, b.y);
    this.ctx.strokeStyle = `rgba(58,173,90,${op.toFixed(2)})`;
    this.ctx.lineWidth = 0.5;
    this.ctx.stroke();
  },

  animate() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    for (let i = 0; i < this.items.length; i++) {
      for (let j = i + 1; j < this.items.length; j++) {
        const dx = this.items[i].x - this.items[j].x;
        const dy = this.items[i].y - this.items[j].y;
        const dSq = dx * dx + dy * dy;
        if (dSq < 7744) this.connect(this.items[i], this.items[j], Math.sqrt(dSq));
      }
    }
    this.items.forEach(p => { this.update(p); this.draw(p); });
    requestAnimationFrame(() => this.animate());
  },

  init() {
    if (!dom.canvas) return;
    this.canvas = dom.canvas;
    this.ctx    = this.canvas.getContext('2d');
    this.resize();
    this.populate();
    window.addEventListener('resize', () => { this.resize(); this.populate(); });
    const hero = this.canvas.closest('.hero');
    if (hero) {
      hero.addEventListener('mousemove', e => {
        const r = this.canvas.getBoundingClientRect();
        this.mouse.x = e.clientX - r.left;
        this.mouse.y = e.clientY - r.top;
      });
      hero.addEventListener('mouseleave', () => { this.mouse.x = null; this.mouse.y = null; });
    }
    this.animate();
  },
};


/* ════════════════════════════════════════
   4. ANIMACIONES DE ENTRADA
   IntersectionObserver añade .visible.
   CSS define el estado inicial y la transición.
════════════════════════════════════════ */
const Animations = {
  init() {
    if (!dom.anims.length) return;
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); }
      });
    }, { threshold: 0.10, rootMargin: '0px 0px -50px 0px' });
    dom.anims.forEach(el => obs.observe(el));
  },
};


/* ════════════════════════════════════════
   5. CONTADORES ANIMADOS
   Ease-out cúbico + formato local colombiano.
════════════════════════════════════════ */
const Counters = {
  ease: t => 1 - Math.pow(1 - t, 3),

  run(el, target, ms = 1800) {
    const t0 = performance.now();
    const go = now => {
      const p = Math.min((now - t0) / ms, 1);
      el.textContent = Math.round(this.ease(p) * target).toLocaleString('es-CO');
      if (p < 1) requestAnimationFrame(go);
      else el.textContent = target.toLocaleString('es-CO');
    };
    requestAnimationFrame(go);
  },

  init() {
    if (!dom.counters.length) return;
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          const val = parseInt(e.target.dataset.count, 10);
          if (!isNaN(val)) this.run(e.target, val);
          obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.5 });
    dom.counters.forEach(el => obs.observe(el));
  },
};


/* ════════════════════════════════════════
   6. TABS DE BENEFICIOS
   Activa el panel al hacer clic en el tab.
════════════════════════════════════════ */
const Tabs = {
  activate(btn) {
    const id = btn.dataset.tab;
    dom.tabBtns.forEach(b => {
      const on = b === btn;
      b.classList.toggle('tab-on', on);
      b.setAttribute('aria-selected', String(on));
    });
    dom.tabPanes.forEach(p => {
      const on = p.id === id;
      p.classList.toggle('panel-on', on);
      on ? p.removeAttribute('hidden') : p.setAttribute('hidden', '');
    });
  },
  init() {
    if (!dom.tabBtns.length) return;
    dom.tabBtns.forEach(btn => btn.addEventListener('click', () => this.activate(btn)));
  },
};


/* ════════════════════════════════════════
   7. BOTÓN VOLVER ARRIBA
════════════════════════════════════════ */
const BackTop = {
  init() {
    if (!dom.backTop) return;
    window.addEventListener('scroll', () => {
      dom.backTop.classList.toggle('visible', window.scrollY > 400);
    }, { passive: true });
    dom.backTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  },
};


/* ════════════════════════════════════════
   8. NAV ACTIVA POR SCROLL
════════════════════════════════════════ */
const ActiveNav = {
  update() {
    const y = window.scrollY + 90;
    let cur = '';
    dom.sections.forEach(s => { if (y >= s.offsetTop) cur = s.id; });
    dom.navLinks.forEach(a => a.classList.toggle('active', a.getAttribute('href') === `#${cur}`));
  },
  init() {
    if (!dom.sections.length) return;
    window.addEventListener('scroll', () => this.update(), { passive: true });
    this.update();
  },
};


/* ════════════════════════════════════════
   9. INICIALIZACIÓN
════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {

  Cursor.init();
  Header.init();
  Particles.init();
  Animations.init();
  Counters.init();
  Tabs.init();
  BackTop.init();
  ActiveNav.init();

  /* Scroll suave compensado por altura del header */
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const target = document.querySelector(a.getAttribute('href'));
      if (!target) return;
      e.preventDefault();
      const offset = dom.header ? dom.header.offsetHeight : 72;
      window.scrollTo({ top: target.getBoundingClientRect().top + window.scrollY - offset, behavior: 'smooth' });
    });
  });

});