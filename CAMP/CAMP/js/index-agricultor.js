/**
 * CAMP Dashboard - JavaScript para Agricultor
 * VERSIÓN FINAL CONSOLIDADA
 */

"use strict";

// ================================================================
// VARIABLES GLOBALES
// ================================================================

let currentUser = {
    firstName: 'Carlos',
    lastName: 'González',
    role: 'Agricultor',
    email: 'carlos@finca.com',
    fotoUrl: null,
    isLoggedIn: false
};

let map = null;
let ofertasData = [];
let farmerMarker = null;
let workerMarkers = [];
let currentFarmerLocation = null;

// ================================================================
// VERIFICACIÓN DE SESIÓN
// ================================================================

async function verificarSesionActiva() {
    try {
        const response = await fetch('/check_session', {
            method: 'GET',
            credentials: 'include',
            headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' }
        });

        if (!response.ok || response.status === 401) {
            window.location.replace('/vista/login-trabajador.html?message=Sesión expirada&type=error');
            return false;
        }

        const data = await response.json();

        if (!data.authenticated || data.user_role !== 'Agricultor') {
            window.location.replace('/vista/login-trabajador.html?message=Por favor inicia sesión&type=error');
            return false;
        }

        return true;

    } catch (error) {
        console.error('Error verificando sesión:', error);
        window.location.replace('/vista/login-trabajador.html?message=Error de conexión&type=error');
        return false;
    }
}

window.addEventListener('pageshow', function (event) {
    if (event.persisted) verificarSesionActiva();
});

if (window.performance && window.performance.navigation.type === 2) {
    window.location.reload(true);
}

setInterval(verificarSesionActiva, 5 * 60 * 1000);

// ================================================================
// INICIALIZACIÓN PRINCIPAL
// ================================================================

document.addEventListener('DOMContentLoaded', async function () {
    console.log('🌱 Iniciando Dashboard Agricultor...');

    await verificarSesionActiva();
    setupEventListeners();
    await fetchUserSession();
    await cargarOfertasDelAgricultor();
    setTimeout(initMap, 500);

    setTimeout(actualizarSidebarPerfil, 2000);

    console.log('✅ Dashboard inicializado');
});

// ================================================================
// GESTIÓN DE SESIÓN
// ================================================================

async function fetchUserSession() {
    try {
        const response = await fetch('/get_user_session', {
            method: 'GET',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            const data = await response.json();

            if (data.success && data.user) {
                currentUser = {
                    firstName: data.user.first_name,
                    lastName: data.user.last_name,
                    role: data.user.role,
                    email: data.user.email,
                    username: data.user.username,
                    userId: data.user.user_id,
                    telefono: data.user.telefono || '',
                    fotoUrl: data.user.url_foto || null,
                    isLoggedIn: true
                };

                console.log('✅ Usuario cargado:', currentUser);
                updateUIWithUserData();
                updateProfilePhoto();

                setTimeout(actualizarSidebarPerfil, 500);

                setTimeout(() => {
                    if (currentUser && currentUser.userId) {
                        loadUserRating();
                        loadNotifications();
                    }
                }, 1000);

                return true;
            }
        }

        currentUser.isLoggedIn = true;
        updateUIWithUserData();
        setTimeout(actualizarSidebarPerfil, 500);
        return true;

    } catch (error) {
        console.error('Error conectando con servidor:', error);
        currentUser.isLoggedIn = true;
        updateUIWithUserData();
        setTimeout(actualizarSidebarPerfil, 500);
        return true;
    }
}

function updateUIWithUserData() {
    const header = document.querySelector('.header .logo');
    if (header && !document.querySelector('.user-welcome')) {
        const welcomeDiv = document.createElement('div');
        welcomeDiv.className = 'user-welcome';
        welcomeDiv.innerHTML = `
            <span style="margin-left:20px;color:#4a7c59;font-weight:600;">
                <i class="fas fa-seedling" style="margin-right:6px;"></i>Bienvenido, ${currentUser.firstName}
            </span>`;
        header.parentNode.insertBefore(welcomeDiv, header.nextSibling);
    }
}

function updateProfilePhoto() {
    const btn = document.getElementById('profileMenuBtn');
    if (!btn) return;
    btn.innerHTML = currentUser.fotoUrl
        ? `<img src="${currentUser.fotoUrl}" alt="Foto de perfil" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`
        : `<i class="fas fa-user"></i>`;
}

// ================================================================
// SIDEBAR — ACTUALIZAR FOTO E INICIALES
// ================================================================

function getIniciales(firstName, lastName) {
    let ini = '';
    if (firstName && firstName.trim()) ini += firstName.trim().charAt(0).toUpperCase();
    if (lastName  && lastName.trim())  ini += lastName.trim().charAt(0).toUpperCase();
    return ini || 'AG';
}

async function actualizarSidebarPerfil() {
    try {
        if (!currentUser || !currentUser.userId) return;

        const sidebarName = document.getElementById('sidebarProfileName');
        if (sidebarName) {
            sidebarName.textContent =
                `${currentUser.firstName || ''} ${currentUser.lastName || ''}`.trim() || 'Agricultor';
        }

        const sidebarAvatar = document.getElementById('sidebarProfileAvatar');
        if (sidebarAvatar) {
            if (currentUser.fotoUrl) {
                sidebarAvatar.innerHTML = `
                    <img src="${currentUser.fotoUrl}" alt="${currentUser.firstName}"
                         style="width:100%;height:100%;object-fit:cover;"
                         onerror="this.style.display='none';this.parentElement.innerHTML='<i class=\\'fas fa-user\\'></i>';">`;
            } else {
                const ini = getIniciales(currentUser.firstName, currentUser.lastName);
                sidebarAvatar.innerHTML = `<span style="font-size:32px;font-weight:700;">${ini}</span>`;
            }
        }

        console.log('✅ Sidebar actualizado');
    } catch (error) {
        console.error('❌ Error actualizando sidebar:', error);
    }
}

// ================================================================
// PAGINACIÓN DE OFERTAS
// ================================================================

let paginaActualOfertas = 1;
const OFERTAS_POR_PAGINA = 5;

function cambiarPaginaOfertas(direccion) {
    const totalPaginas = Math.ceil(ofertasData.length / OFERTAS_POR_PAGINA);

    if (direccion === 'prev' && paginaActualOfertas > 1) {
        paginaActualOfertas--;
    } else if (direccion === 'next' && paginaActualOfertas < totalPaginas) {
        paginaActualOfertas++;
    }

    _renderPaginaOfertas();
}

function _renderPaginaOfertas() {
    const totalPaginas = Math.ceil(ofertasData.length / OFERTAS_POR_PAGINA);
    const inicio = (paginaActualOfertas - 1) * OFERTAS_POR_PAGINA;
    const fin    = inicio + OFERTAS_POR_PAGINA;
    const ofertasPagina = ofertasData.slice(inicio, fin);

    const container = document.getElementById('ofertasContainer');
    if (!container) return;

    const titulo = container.querySelector('.section-title');
    container.innerHTML = '';
    if (titulo) container.appendChild(titulo);

    ofertasPagina.forEach(oferta => container.appendChild(crearTarjetaOferta(oferta)));

    const paginationContainer = document.getElementById('paginationContainer');
    const prevBtn    = document.getElementById('prevPageBtn');
    const nextBtn    = document.getElementById('nextPageBtn');
    const currentNum = document.getElementById('currentPageNum');
    const totalNum   = document.getElementById('totalPagesNum');

    if (paginationContainer) {
        paginationContainer.style.display = totalPaginas > 1 ? 'flex' : 'none';
    }
    if (prevBtn)    prevBtn.disabled    = paginaActualOfertas <= 1;
    if (nextBtn)    nextBtn.disabled    = paginaActualOfertas >= totalPaginas;
    if (currentNum) currentNum.textContent = paginaActualOfertas;
    if (totalNum)   totalNum.textContent   = totalPaginas;
}

// ================================================================
// MENÚ DESPLEGABLE DE USUARIO
// ================================================================

function _removeDropdown() {
    const old = document.getElementById('profileDropdown');
    if (old) old.remove();
}

function _hideOverlay() {
    const overlay = document.getElementById('overlay');
    if (overlay) { overlay.classList.remove('show'); overlay.onclick = null; }
}

function _showOverlay(cb) {
    const overlay = document.getElementById('overlay');
    if (overlay) { overlay.classList.add('show'); overlay.onclick = cb; }
}

function closeProfileMenu() {
    _removeDropdown();
    _hideOverlay();
}

function toggleProfileMenu() {
    if (document.getElementById('profileDropdown')) {
        closeProfileMenu();
        return;
    }

    const avatarHTML = currentUser && currentUser.fotoUrl
        ? `<img src="${currentUser.fotoUrl}" alt="${currentUser.firstName || ''}"
               style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`
        : `<i class="fas fa-user" style="font-size:20px;color:#fff;"></i>`;

    const firstName = (currentUser && currentUser.firstName) || 'Agricultor';
    const lastName  = (currentUser && currentUser.lastName)  || '';
    const role      = (currentUser && currentUser.role)      || 'Agricultor';

    const dropdown = document.createElement('div');
    dropdown.id = 'profileDropdown';

    dropdown.innerHTML = `
        <div class="profile-dropdown-header">
            <div class="profile-dropdown-avatar">${avatarHTML}</div>
            <div class="profile-dropdown-name">${firstName} ${lastName}</div>
            <div class="profile-dropdown-role">
                <i class="fas fa-seedling"></i>
                <span>${role}</span>
            </div>
        </div>
        <div class="profile-dropdown-menu">
            <div class="profile-dropdown-item" data-action="profile">
                <span class="icon"><i class="fas fa-user-circle"></i></span>
                <span>Mi Perfil</span>
            </div>
            <div class="profile-dropdown-item" data-action="historial">
                <span class="icon"><i class="fas fa-history"></i></span>
                <span>Historial de Contrataciones</span>
            </div>
            <div class="profile-dropdown-item" data-action="estadisticas">
                <span class="icon"><i class="fas fa-chart-line"></i></span>
                <span>Mis Estadísticas</span>
            </div>
            <div class="profile-dropdown-item" data-action="settings">
                <span class="icon"><i class="fas fa-cog"></i></span>
                <span>Configuración</span>
            </div>
            <div class="profile-dropdown-item" data-action="soporte">
                <span class="icon"><i class="fas fa-question-circle"></i></span>
                <span>Ayuda y Soporte</span>
            </div>
            <div class="profile-dropdown-item logout" data-action="logout">
                <span class="icon"><i class="fas fa-sign-out-alt"></i></span>
                <span>Cerrar Sesión</span>
            </div>
        </div>`;

    const actions = {
        profile:      () => { closeProfileMenu(); window.location.href = '/vista/perfil-agricultor.html'; },
        historial:    () => { closeProfileMenu(); window.location.href = '/vista/historial-contrataciones.html'; },
        estadisticas: () => { closeProfileMenu(); window.location.href = '/vista/estadisticas-agricultor.html'; },
        settings:     () => { closeProfileMenu(); window.location.href = '/vista/configuracion-agricultor.html'; },
        soporte:      () => { closeProfileMenu(); window.location.href = '/vista/soporte-agricultor.html'; },
        logout:       () => { closeProfileMenu(); confirmLogout(); },
    };

    dropdown.addEventListener('click', function (e) {
        const item = e.target.closest('[data-action]');
        if (item && actions[item.dataset.action]) actions[item.dataset.action]();
    });

    document.body.appendChild(dropdown);
    _showOverlay(closeProfileMenu);
    _addDropdownStyles();
}

function _addDropdownStyles() {
    if (document.getElementById('dropdown-styles')) return;
    const style = document.createElement('style');
    style.id = 'dropdown-styles';
    style.textContent = `
        #profileDropdown {
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 9999;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            border: 1px solid rgba(74,124,89,0.2);
            min-width: 280px;
            animation: dropdownFadeIn 0.25s ease;
        }
        @keyframes dropdownFadeIn {
            from { opacity:0; transform:translateY(-10px); }
            to   { opacity:1; transform:translateY(0); }
        }
        .profile-dropdown-header {
            padding: 20px;
            text-align: center;
            background: linear-gradient(135deg,rgba(74,124,89,.1),rgba(144,238,144,.1));
            border-bottom: 1px solid rgba(74,124,89,.2);
            border-radius: 15px 15px 0 0;
        }
        .profile-dropdown-avatar {
            width: 50px; height: 50px;
            border-radius: 50%;
            background: linear-gradient(135deg,#4a7c59,#1e3a2e);
            color: white;
            display: flex; align-items: center; justify-content: center;
            margin: 0 auto 10px;
            font-size: 20px;
            overflow: hidden;
        }
        .profile-dropdown-name  { font-size:16px; font-weight:700; color:#1e3a2e; margin-bottom:5px; }
        .profile-dropdown-role  { font-size:14px; color:#4a7c59; display:flex; align-items:center; justify-content:center; gap:5px; }
        .profile-dropdown-menu  { padding: 10px 0; }
        .profile-dropdown-item  {
            display: flex; align-items: center; gap: 12px;
            padding: 12px 20px;
            color: #1e3a2e;
            cursor: pointer;
            transition: all .2s ease;
            border-bottom: 1px solid rgba(74,124,89,.1);
        }
        .profile-dropdown-item:hover { background: rgba(74,124,89,.1); padding-left: 25px; }
        .profile-dropdown-item .icon { width: 20px; text-align: center; }
        .profile-dropdown-item.logout {
            color: #dc2626;
            border-top: 1px solid rgba(220,38,38,.2);
            border-bottom: none;
            margin-top: 5px;
        }
        .profile-dropdown-item.logout:hover { background: rgba(220,38,38,.1); }
        #overlay.show {
            position: fixed; top:0; left:0; width:100%; height:100%;
            background: transparent;
            z-index: 9998;
            display: block;
        }`;
    document.head.appendChild(style);
}

// ================================================================
// ACCIONES DE SESIÓN
// ================================================================

function viewProfile()               { closeProfileMenu(); window.location.href = '/vista/perfil-agricultor.html'; }
function viewSettings()              { closeProfileMenu(); window.location.href = '/vista/configuracion-agricultor.html'; }
function showHistorialContrataciones(){ closeProfileMenu(); window.location.href = '/vista/historial-contrataciones.html'; }
function showEstadisticas()          { closeProfileMenu(); window.location.href = '/vista/estadisticas-agricultor.html'; }
function showAyudaSoporte()          { closeProfileMenu(); window.location.href = '/vista/soporte-agricultor.html'; }

function confirmLogout() {
    if (confirm(`¿Seguro que deseas cerrar sesión, ${currentUser.firstName}?`)) executeLogout();
}

async function executeLogout() {
    showStatusMessage('Cerrando sesión...', 'info');
    try {
        const response = await fetch('/logout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache' },
            credentials: 'include'
        });
        if (response.ok) {
            sessionStorage.clear();
            localStorage.removeItem('user_data');
        }
    } catch (error) {
        console.error('Error en logout:', error);
    } finally {
        setTimeout(() => {
            window.location.replace('/vista/login-trabajador.html?message=Sesión cerrada&type=success');
        }, 1500);
    }
}

// ================================================================
// GESTIÓN DE OFERTAS
// ================================================================

async function cargarOfertasDelAgricultor() {
    try {
        const response = await fetch('/api/get_farmer_jobs', {
            method: 'GET', credentials: 'include',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) throw new Error(`Error del servidor: ${response.status}`);

        const data = await response.json();

        if (data.success) {
            ofertasData = data.ofertas || [];
            mostrarOfertasEnDashboard(ofertasData);
            actualizarEstadisticas(data.estadisticas);
        } else {
            throw new Error(data.message || 'Error al cargar ofertas');
        }

    } catch (error) {
        console.error('❌ Error cargando ofertas:', error);
        showStatusMessage('Error al cargar ofertas: ' + error.message, 'error');
        mostrarOfertasEnDashboard([]);
    }
}

function mostrarOfertasEnDashboard(ofertas) {
    const container = document.getElementById('ofertasContainer');
    if (!container) return;

    container.innerHTML = '';

    if (ofertas.length === 0) {
        container.innerHTML = `
            <div class="section-title" style="margin:30px 0 20px 0;">
                <i class="fas fa-clipboard-list"></i> Mis Ofertas Publicadas
            </div>
            <div style="text-align:center;padding:40px;color:#64748b;">
                <div style="font-size:48px;margin-bottom:15px;color:#4a7c59;">
                    <i class="fas fa-seedling"></i>
                </div>
                <h3 style="color:#1e3a2e;margin-bottom:10px;">No tienes ofertas publicadas</h3>
                <p>Crea tu primera oferta para encontrar trabajadores.</p>
                <button class="btn btn-primary" onclick="createNewOffer()" style="margin-top:15px;">
                    <i class="fas fa-plus"></i> Crear Primera Oferta
                </button>
            </div>`;
        const pc = document.getElementById('paginationContainer');
        if (pc) pc.style.display = 'none';
        return;
    }

    container.innerHTML = `
        <div class="section-title" style="margin:30px 0 20px 0;">
            <i class="fas fa-clipboard-list"></i>
            Mis Ofertas Publicadas (${ofertas.length})
        </div>`;

    paginaActualOfertas = 1;
    _renderPaginaOfertas();
}

function crearTarjetaOferta(oferta) {
    const div = document.createElement('div');
    div.className = 'offer-card';

    const diasPublicada = Math.floor((new Date() - new Date(oferta.fecha_publicacion)) / 86400000);
    const estadoInfo = obtenerEstadoOferta(oferta.estado);
    const tituloEscapado = oferta.titulo.replace(/'/g, "\\'");

    div.innerHTML = `
        <div class="offer-header">
            <div class="offer-title">${oferta.titulo}</div>
            <div class="offer-actions">
                <button class="btn-icon btn-icon-duplicate" data-action="duplicar" data-id="${oferta.id_oferta}" title="Duplicar oferta">
                    <i class="fas fa-copy"></i>
                </button>
                <button class="btn-icon" data-action="editar" data-id="${oferta.id_oferta}" title="Editar oferta">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn-icon btn-icon-delete" data-action="eliminar" data-id="${oferta.id_oferta}" title="Eliminar oferta">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
        <div class="offer-details">
            <p class="offer-description">${oferta.descripcion}</p>
            <div class="offer-meta">
                <div class="offer-meta-item">
                    <i class="fas fa-dollar-sign"></i>
                    <span>$${Number(oferta.pago_ofrecido).toLocaleString()} COP</span>
                </div>
                <div class="offer-meta-item">
                    <i class="fas fa-calendar-alt"></i>
                    <span>Hace ${diasPublicada === 0 ? 'hoy' : diasPublicada + ' día' + (diasPublicada > 1 ? 's' : '')}</span>
                </div>
                <div class="offer-meta-item">
                    <i class="fas fa-users"></i>
                    <span>${oferta.num_postulaciones || 0} postulaciones</span>
                </div>
                ${oferta.ubicacion ? `
                <div class="offer-meta-item">
                    <i class="fas fa-map-marker-alt"></i>
                    <span>${oferta.ubicacion}</span>
                </div>` : ''}
            </div>
        </div>
        <div class="offer-footer">
            <div class="offer-status">
                <span class="status-badge ${estadoInfo.clase}">${estadoInfo.texto}</span>
            </div>
            <div class="offer-actions">
                <button class="btn btn-secondary btn-ver-postulaciones"
                        data-oferta-id="${oferta.id_oferta}"
                        data-num-postulaciones="${oferta.num_postulaciones || 0}">
                    <i class="fas fa-eye"></i> Ver (${oferta.num_postulaciones || 0})
                </button>
                ${oferta.estado === 'Abierta' ? `
                    <button class="btn btn-warning btn-cerrar-oferta"
                            data-id="${oferta.id_oferta}" data-titulo="${tituloEscapado}">
                        <i class="fas fa-lock"></i> Cerrar
                    </button>` :
                oferta.estado === 'Cerrada' ? `
                    <button class="btn btn-success btn-reabrir-oferta"
                            data-id="${oferta.id_oferta}" data-titulo="${tituloEscapado}">
                        <i class="fas fa-unlock"></i> Reabrir
                    </button>` : ''}
            </div>
        </div>`;

    setTimeout(() => {
        const add = (sel, fn) => { const el = div.querySelector(sel); if (el) el.addEventListener('click', fn); };
        add('[data-action="duplicar"]', () => duplicarOferta(oferta.id_oferta, oferta.titulo));
        add('[data-action="editar"]',   () => editarOferta(oferta.id_oferta));
        add('[data-action="eliminar"]', () => eliminarOferta(oferta.id_oferta, oferta.titulo));
        add('.btn-ver-postulaciones', function () {
            verPostulaciones(parseInt(this.dataset.ofertaId), parseInt(this.dataset.numPostulaciones));
        });
        add('.btn-cerrar-oferta',  function () { cerrarOferta(parseInt(this.dataset.id), this.dataset.titulo); });
        add('.btn-reabrir-oferta', function () { reabrirOferta(parseInt(this.dataset.id), this.dataset.titulo); });
    }, 100);

    return div;
}

function obtenerEstadoOferta(estado) {
    const map = {
        'Abierta':    { clase: 'status-active',   texto: 'Activa' },
        'En Proceso': { clase: 'status-progress',  texto: 'En Proceso' },
        'Cerrada':    { clase: 'status-closed',    texto: 'Cerrada' },
    };
    return map[estado] || { clase: 'status-inactive', texto: estado };
}

function actualizarEstadisticas(estadisticas) {
    if (!estadisticas) return;
    const el1 = document.getElementById('ofertasActivas');
    const el2 = document.getElementById('trabajadoresContratados');
    if (el1) el1.textContent = estadisticas.ofertas_activas || ofertasData.length;
    if (el2) el2.textContent = estadisticas.trabajadores_contratados || 0;
}

// ================================================================
// DUPLICAR OFERTA
// ================================================================

async function duplicarOferta(ofertaId, titulo) {
    if (!confirm(`¿Duplicar la oferta "${titulo}"?\n\nSe creará una copia con el prefijo "Copia de".`)) return;

    showStatusMessage('Duplicando oferta...', 'info');
    try {
        const response = await fetch(`/api/duplicar_oferta/${ofertaId}`, {
            method: 'POST', credentials: 'include',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (data.success) {
            showStatusMessage('Oferta duplicada exitosamente', 'success');
            setTimeout(cargarOfertasDelAgricultor, 1500);
        } else {
            showStatusMessage(data.message, 'error');
        }
    } catch (error) {
        showStatusMessage('Error de conexión', 'error');
    }
}

// ================================================================
// CERRAR / REABRIR OFERTAS
// ================================================================

async function cerrarOferta(ofertaId, titulo) {
    try {
        let mensaje = `¿Cerrar la oferta "${titulo}"?\n\n`;

        const statsRes = await fetch(`/api/estadisticas_cierre_v2/${ofertaId}`, { credentials: 'include' });
        if (statsRes.ok) {
            const statsData = await statsRes.json();
            if (statsData.success) {
                const s = statsData.stats;
                mensaje += `Postulaciones:\n- Pendientes: ${s.pendientes}\n- Aceptadas: ${s.aceptadas}\n- Rechazadas: ${s.rechazadas}\n\n`;
                if (s.pendientes > 0) mensaje += `Las ${s.pendientes} postulaciones pendientes serán rechazadas.\n\n`;
            }
        }

        mensaje += `Esta acción cerrará la oferta y guardará la fecha de finalización.`;
        if (!confirm(mensaje)) return;

        showStatusMessage('Cerrando oferta...', 'info');
        const response = await fetch(`/api/cerrar_oferta_manual_v2/${ofertaId}`, {
            method: 'PUT', credentials: 'include',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (data.success) {
            showStatusMessage('Oferta cerrada exitosamente', 'success');
            setTimeout(cargarOfertasDelAgricultor, 1500);
        } else {
            showStatusMessage(data.message, 'error');
        }
    } catch (error) {
        showStatusMessage('Error de conexión', 'error');
    }
}

async function reabrirOferta(ofertaId, titulo) {
    if (!confirm(`¿Reabrir la oferta "${titulo}"?\n\nVolverás a recibir postulaciones.`)) return;

    showStatusMessage('Reabriendo oferta...', 'info');
    try {
        const response = await fetch(`/api/reabrir_oferta_v2/${ofertaId}`, {
            method: 'PUT', credentials: 'include',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (data.success) {
            showStatusMessage('Oferta reabierta exitosamente', 'success');
            setTimeout(cargarOfertasDelAgricultor, 1500);
        } else {
            showStatusMessage(data.message, 'error');
        }
    } catch (error) {
        showStatusMessage('Error de conexión', 'error');
    }
}

// ================================================================
// CREAR OFERTA
// ================================================================

function createNewOffer() { abrirModalOferta(); }

function abrirModalOferta() {
    const modal = document.getElementById('modalCrearOferta');
    if (!modal) return;
    modal.classList.add('show');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    setTimeout(() => {
        const t = document.getElementById('tituloOferta');
        if (t) t.focus();
    }, 300);
}

function cerrarModalOferta() {
    const modal = document.getElementById('modalCrearOferta');
    if (!modal) return;
    modal.classList.remove('show');
    setTimeout(() => {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
        const form = document.getElementById('formCrearOferta');
        if (form) form.reset();
        const btn = document.getElementById('btnCrearOferta');
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-check"></i> Crear Oferta'; }
    }, 300);
}

async function crearOferta(event) {
    event.preventDefault();
    const btnCrear = document.getElementById('btnCrearOferta');
    const formData = new FormData(event.target);

    const ofertaData = {
        titulo:      formData.get('titulo').trim(),
        descripcion: formData.get('descripcion').trim(),
        pago:        parseInt(formData.get('pago')),
        ubicacion:   formData.get('ubicacion').trim()
    };

    if (ofertaData.titulo.length < 10)      return showStatusMessage('El título debe tener al menos 10 caracteres', 'error');
    if (ofertaData.descripcion.length < 20)  return showStatusMessage('La descripción debe tener al menos 20 caracteres', 'error');
    if (!ofertaData.pago || ofertaData.pago < 10000) return showStatusMessage('El pago mínimo debe ser $10,000 COP', 'error');

    btnCrear.disabled = true;
    btnCrear.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creando...';

    try {
        const response = await fetch('/api/crear_oferta', {
            method: 'POST', credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(ofertaData)
        });
        const result = await response.json();
        if (result.success) {
            btnCrear.innerHTML = '<i class="fas fa-check"></i> ¡Creada!';
            showStatusMessage(`Oferta "${ofertaData.titulo}" creada exitosamente`, 'success');
            setTimeout(() => { cerrarModalOferta(); cargarOfertasDelAgricultor(); }, 1500);
        } else {
            throw new Error(result.message || 'Error al crear la oferta');
        }
    } catch (error) {
        btnCrear.disabled = false;
        btnCrear.innerHTML = '<i class="fas fa-check"></i> Crear Oferta';
        showStatusMessage('Error: ' + error.message, 'error');
    }
}

// ================================================================
// EDITAR OFERTA
// ================================================================

async function editarOferta(ofertaId) {
    const oferta = ofertasData.find(o => o.id_oferta === ofertaId);
    if (!oferta) return showStatusMessage('Oferta no encontrada', 'error');

    let descripcion = oferta.descripcion || '';
    let ubicacion   = oferta.ubicacion   || '';

    if (descripcion.includes('Ubicación:')) {
        try {
            const partes = descripcion.split('\n\nUbicación:');
            descripcion = partes[0];
            ubicacion   = partes[1].trim();
        } catch (e) { /* ignora */ }
    }

    document.getElementById('editOfertaId').value          = oferta.id_oferta;
    document.getElementById('editTituloOferta').value      = oferta.titulo;
    document.getElementById('editDescripcionOferta').value = descripcion;
    document.getElementById('editPagoOferta').value        = oferta.pago_ofrecido;
    document.getElementById('editUbicacionOferta').value   = ubicacion;

    const modal = document.getElementById('modalEditarOferta');
    if (modal) { modal.classList.add('show'); modal.style.display = 'flex'; document.body.style.overflow = 'hidden'; }
}

function cerrarModalEditar() {
    const modal = document.getElementById('modalEditarOferta');
    if (!modal) return;
    modal.classList.remove('show');
    setTimeout(() => {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
        const form = document.getElementById('formEditarOferta');
        if (form) form.reset();
        const btn = document.getElementById('btnGuardarEdicion');
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-save"></i> Guardar Cambios'; }
    }, 300);
}

async function guardarEdicion(event) {
    event.preventDefault();
    const btn = document.getElementById('btnGuardarEdicion');
    const formData = new FormData(event.target);
    const ofertaId = parseInt(formData.get('ofertaId'));

    if (!ofertaId) return showStatusMessage('Error: ID de oferta no válido', 'error');

    const ofertaData = {
        titulo:      formData.get('titulo').trim(),
        descripcion: formData.get('descripcion').trim(),
        pago:        parseInt(formData.get('pago')),
        ubicacion:   formData.get('ubicacion').trim()
    };

    if (ofertaData.titulo.length < 10)      return showStatusMessage('El título debe tener al menos 10 caracteres', 'error');
    if (ofertaData.descripcion.length < 20)  return showStatusMessage('La descripción debe tener al menos 20 caracteres', 'error');
    if (!ofertaData.pago || ofertaData.pago < 10000) return showStatusMessage('El pago mínimo debe ser $10,000 COP', 'error');

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';

    try {
        const response = await fetch(`/api/edit_job/${ofertaId}`, {
            method: 'PUT', credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(ofertaData)
        });
        const result = await response.json();
        if (result.success) {
            btn.innerHTML = '<i class="fas fa-check"></i> ¡Guardado!';
            showStatusMessage('Oferta actualizada exitosamente', 'success');
            setTimeout(() => { cerrarModalEditar(); cargarOfertasDelAgricultor(); }, 1500);
        } else {
            throw new Error(result.message || 'Error al actualizar la oferta');
        }
    } catch (error) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-save"></i> Guardar Cambios';
        showStatusMessage('Error: ' + error.message, 'error');
    }
}

// ================================================================
// ELIMINAR OFERTA
// ================================================================

async function eliminarOferta(ofertaId, titulo) {
    if (!confirm(`¿Eliminar la oferta "${titulo}"?\n\nEsta acción no se puede deshacer.`)) return;

    try {
        const response = await fetch(`/api/delete_job/${ofertaId}`, {
            method: 'DELETE', credentials: 'include',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (data.success) {
            showStatusMessage('Oferta eliminada exitosamente', 'success');
            cargarOfertasDelAgricultor();
        } else {
            throw new Error(data.message || 'Error al eliminar la oferta');
        }
    } catch (error) {
        showStatusMessage('Error al eliminar la oferta', 'error');
    }
}

// ================================================================
// GESTIÓN DE POSTULACIONES
// ================================================================

async function verPostulaciones(ofertaId, numPostulaciones) {
    if (numPostulaciones === 0) return showStatusMessage('Esta oferta no tiene postulaciones aún', 'info');

    showStatusMessage('Cargando postulaciones...', 'info');
    try {
        const response = await fetch(`/api/get_offer_applications/${ofertaId}`, {
            method: 'GET', credentials: 'include',
            headers: { 'Content-Type': 'application/json' }
        });
        if (!response.ok) throw new Error(`Error del servidor: ${response.status}`);
        const data = await response.json();
        if (data.success) {
            mostrarModalPostulaciones(data);
        } else {
            showStatusMessage(data.message || 'Error al cargar postulaciones', 'error');
        }
    } catch (error) {
        showStatusMessage('Error de conexión al cargar postulaciones', 'error');
    }
}

function mostrarModalPostulaciones(data) {
    const modal   = document.getElementById('applicationsModal');
    const content = document.getElementById('applicationsContent');
    if (!modal || !content) return alert('Error: No se encontraron los elementos del modal');

    if (!data.postulaciones || data.postulaciones.length === 0) {
        content.innerHTML = `
            <div style="text-align:center;padding:40px;color:#64748b;">
                <i class="fas fa-users" style="font-size:48px;margin-bottom:15px;color:#4a7c59;display:block;"></i>
                <h3>No hay postulaciones</h3>
                <p>Aún no hay trabajadores interesados en esta oferta.</p>
            </div>`;
    } else {
        let html = `
            <div class="applications-header">
                <h3>${data.oferta_titulo}</h3>
                <p>${data.total} postulación${data.total !== 1 ? 'es' : ''}</p>
            </div>
            <div class="applications-list">`;

        data.postulaciones.forEach(post => {
            const starsHtml = _generarEstrellas(post.calificacion);
            const estadoClass = post.estado === 'Pendiente' ? 'status-pending'
                              : post.estado === 'Aceptada'  ? 'status-accepted'
                              : 'status-rejected';

            html += `
                <div class="application-card">
                    <div class="application-header">
                        <div class="worker-info">
                            <div class="worker-avatar">
                                ${post.foto_url
                                    ? `<img src="${post.foto_url}" alt="${post.nombre_completo}">`
                                    : `<i class="fas fa-user"></i>`}
                            </div>
                            <div class="worker-details">
                                <h4>${post.nombre_completo}</h4>
                                <div class="worker-stats">
                                    <span><i class="fas fa-briefcase"></i> ${post.trabajos_completados} trabajos</span>
                                    <span>${starsHtml} ${post.calificacion.toFixed(1)}</span>
                                </div>
                            </div>
                        </div>
                        <span class="status-badge ${estadoClass}">${post.estado}</span>
                    </div>
                    <div class="application-body">
                        <div class="application-info">
                            <div class="info-item"><i class="fas fa-phone"></i><span>${post.telefono}</span></div>
                            <div class="info-item"><i class="fas fa-envelope"></i><span>${post.email}</span></div>
                            <div class="info-item"><i class="fas fa-calendar-alt"></i><span>Postulado: ${post.fecha_postulacion}</span></div>
                        </div>
                    </div>
                    <div class="application-actions">
                        <button class="btn btn-secondary" onclick="verPerfilTrabajador(${post.trabajador_id})">
                            <i class="fas fa-user-circle"></i> Ver Perfil
                        </button>
                        ${post.estado === 'Pendiente' ? `
                            <button class="btn btn-success" onclick="aceptarPostulacionConCierre(${post.id_postulacion},'${post.nombre_completo}',${data.oferta_id})">
                                <i class="fas fa-check"></i> Aceptar
                            </button>
                            <button class="btn btn-danger" onclick="rechazarPostulacion(${post.id_postulacion})">
                                <i class="fas fa-times"></i> Rechazar
                            </button>` : ''}
                    </div>
                </div>`;
        });

        html += `</div>`;
        content.innerHTML = html;
    }

    modal.style.display = 'flex';
    const overlay = document.getElementById('overlay');
    if (overlay) overlay.style.display = 'block';
}

function closeApplicationsModal() {
    const modal   = document.getElementById('applicationsModal');
    const overlay = document.getElementById('overlay');
    if (modal)   modal.style.display   = 'none';
    if (overlay) overlay.style.display = 'none';
}

async function aceptarPostulacionConCierre(postulacionId, nombreTrabajador, ofertaId) {
    if (!confirm(`¿Aceptar la postulación de ${nombreTrabajador}?`)) return;

    const cerrarOfertaFlag = confirm(
        `¿Deseas CERRAR la oferta ahora?\n\n` +
        `SÍ: La oferta se cerrará (no más postulaciones)\n` +
        `NO: La oferta seguirá abierta`
    );

    showStatusMessage('Procesando...', 'info');
    try {
        const response = await fetch(`/api/aceptar_postulacion_v3/${postulacionId}`, {
            method: 'PUT', credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cerrar_oferta: cerrarOfertaFlag })
        });
        const data = await response.json();
        if (data.success) {
            showStatusMessage(data.message, 'success');
            closeApplicationsModal();
            setTimeout(cargarOfertasDelAgricultor, 2000);
        } else {
            showStatusMessage(data.message, 'error');
        }
    } catch (error) {
        showStatusMessage('Error de conexión', 'error');
    }
}

async function rechazarPostulacion(postulacionId) {
    if (!confirm('¿Rechazar esta postulación?')) return;

    showStatusMessage('Procesando...', 'info');
    try {
        const response = await fetch(`/api/rechazar_postulacion_v3/${postulacionId}`, {
            method: 'PUT', credentials: 'include',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (data.success) {
            showStatusMessage('Postulación rechazada', 'info');
            closeApplicationsModal();
            setTimeout(cargarOfertasDelAgricultor, 1500);
        } else {
            showStatusMessage(data.message, 'error');
        }
    } catch (error) {
        showStatusMessage('Error de conexión', 'error');
    }
}

// ================================================================
// PERFIL DEL TRABAJADOR
// ================================================================

async function verPerfilTrabajador(trabajadorId) {
    try {
        const response = await fetch(`/api/get_worker_profile/${trabajadorId}`, {
            method: 'GET', credentials: 'include'
        });
        const data = await response.json();
        if (data.success) mostrarPerfilTrabajador(data.worker);
        else showStatusMessage('Error al cargar perfil', 'error');
    } catch (error) {
        showStatusMessage('Error de conexión', 'error');
    }
}

function mostrarPerfilTrabajador(worker) {
    const modal   = document.getElementById('workerProfileModal');
    const content = document.getElementById('workerProfileContent');

    const starsHtml   = _generarEstrellas(worker.estadisticas.calificacion_promedio);
    const trabajadorId = worker.id_usuario || worker.user_id || worker.id;

    const avatarHTML = (worker.foto_url && worker.foto_url !== '')
        ? `<img src="${worker.foto_url}" alt="${worker.nombre_completo}"
               style="width:100%;height:100%;object-fit:cover;"
               onerror="this.style.display='none';this.parentElement.innerHTML='<i class=\\'fas fa-user\\'></i>';">`
        : `<i class="fas fa-user"></i>`;

    content.innerHTML = `
        <div class="worker-profile-enhanced">
            <div class="profile-header-enhanced">
                <div class="profile-avatar-large-enhanced">${avatarHTML}</div>
                <div class="profile-info-enhanced">
                    <h2 style="color:#2d3748;font-size:26px;margin-bottom:8px;">${worker.nombre_completo}</h2>
                    <div class="profile-rating-enhanced">
                        ${starsHtml}
                        <span style="font-size:20px;font-weight:700;color:#f59e0b;margin-left:8px;">
                            ${worker.estadisticas.calificacion_promedio.toFixed(1)}
                        </span>
                        <span style="color:#718096;font-size:14px;margin-left:8px;">
                            (${worker.estadisticas.total_calificaciones} calificaciones)
                        </span>
                    </div>
                    <div class="profile-stats-row-enhanced">
                        <div class="stat-item-enhanced">
                            <i class="fas fa-briefcase"></i>
                            <span><strong>${worker.estadisticas.trabajos_completados}</strong> trabajos</span>
                        </div>
                        <div class="stat-item-enhanced">
                            <i class="fas fa-clock"></i>
                            <span><strong>${calcularAnosExperiencia(worker)}</strong> años exp.</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="profile-section-enhanced">
                <h3><i class="fas fa-id-card" style="color:#4a7c59;"></i> Información de Contacto</h3>
                <div class="contact-info-enhanced">
                    <div class="contact-item-enhanced"><i class="fas fa-phone"></i><span>${worker.telefono || 'No disponible'}</span></div>
                    <div class="contact-item-enhanced"><i class="fas fa-envelope"></i><span>${worker.email}</span></div>
                    ${worker.ubicacion ? `<div class="contact-item-enhanced"><i class="fas fa-map-marker-alt"></i><span>${worker.ubicacion}</span></div>` : ''}
                </div>
            </div>

            ${worker.habilidades && worker.habilidades.length > 0 ? `
            <div class="profile-section-enhanced">
                <h3><i class="fas fa-tools" style="color:#4a7c59;"></i> Habilidades Profesionales</h3>
                <div class="skills-list-enhanced">
                    ${worker.habilidades.map(h => `
                        <div class="skill-tag-enhanced">
                            <i class="fas fa-check-circle"></i>
                            <div><strong>${h.Nombre}</strong><span>${h.Clasificacion}</span></div>
                        </div>`).join('')}
                </div>
            </div>` : ''}

            ${worker.experiencia && worker.experiencia.length > 0 ? `
            <div class="profile-section-enhanced">
                <h3><i class="fas fa-briefcase" style="color:#4a7c59;"></i> Experiencia Laboral</h3>
                <div class="experiencia-list-enhanced">
                    ${worker.experiencia.map(exp => `
                        <div class="experiencia-item-enhanced">
                            <div class="experiencia-header">
                                <i class="fas fa-building"></i>
                                <strong>${exp.Ubicacion || 'Trabajo Agrícola'}</strong>
                            </div>
                            <div class="experiencia-dates">
                                <i class="fas fa-calendar-alt"></i>
                                ${formatDate(exp.Fecha_Inicio)} - ${exp.Fecha_Fin ? formatDate(exp.Fecha_Fin) : 'Actualidad'}
                            </div>
                            ${exp.Observacion ? `<p class="experiencia-description">${exp.Observacion}</p>` : ''}
                        </div>`).join('')}
                </div>
            </div>` : ''}

            <div class="action-buttons-enhanced">
                <button class="btn-action-enhanced btn-documentos-enhanced" onclick="verDocumentosTrabajador(${trabajadorId})">
                    <i class="fas fa-file-alt"></i><span>Ver Documentos</span>
                </button>
                <button class="btn-action-enhanced btn-reportar-enhanced" onclick="reportarTrabajador(${trabajadorId},'${worker.nombre_completo}')">
                    <i class="fas fa-flag"></i><span>Reportar</span>
                </button>
            </div>
        </div>`;

    _agregarEstilosPerfilMejorado();
    modal.style.display = 'flex';
}

function closeWorkerProfileModal() {
    const modal = document.getElementById('workerProfileModal');
    if (modal) modal.style.display = 'none';
}

function calcularAnosExperiencia(worker) {
    if (worker.experiencia && worker.experiencia.length > 0) {
        let total = 0;
        worker.experiencia.forEach(exp => {
            const inicio = new Date(exp.Fecha_Inicio);
            const fin    = exp.Fecha_Fin ? new Date(exp.Fecha_Fin) : new Date();
            total += (fin - inicio) / (1000 * 60 * 60 * 24 * 365);
        });
        return Math.max(1, Math.round(total));
    }
    return worker.anos_experiencia || 1;
}

function formatDate(dateString) {
    if (!dateString) return 'Fecha no disponible';
    return new Date(dateString).toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric' });
}

// ================================================================
// VER DOCUMENTOS DEL TRABAJADOR
// ================================================================

async function verDocumentosTrabajador(trabajadorId) {
    if (!trabajadorId || isNaN(trabajadorId))
        return showStatusMessage('ID de trabajador inválido', 'error');

    showStatusMessage('Cargando documentos...', 'info');

    try {
        const response = await fetch(`/api/documentos-usuario/${trabajadorId}`, {
            method: 'GET', credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache' }
        });

        if (response.status === 401) {
            showStatusMessage('Sesión expirada', 'error');
            setTimeout(() => { window.location.href = '/vista/login-trabajador.html'; }, 2000);
            return;
        }
        if (response.status === 403) return showStatusMessage('No tienes permisos para ver documentos', 'error');
        if (response.status === 404) return showStatusMessage('Endpoint no encontrado', 'error');

        const data = await response.json();
        if (data.success) {
            mostrarModalDocumentosTrabajador(data.documentos || [], trabajadorId);
            showStatusMessage(
                data.total === 0
                    ? 'Este trabajador no ha subido documentos'
                    : `${data.total} documento${data.total > 1 ? 's' : ''} cargado${data.total > 1 ? 's' : ''}`,
                data.total === 0 ? 'info' : 'success'
            );
        } else {
            showStatusMessage(data.message || 'Error al cargar documentos', 'error');
        }
    } catch (error) {
        showStatusMessage('Error de conexión: ' + error.message, 'error');
    }
}

function mostrarModalDocumentosTrabajador(documentos, trabajadorId) {
    let modal = document.getElementById('modalDocumentosTrabajador');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'modalDocumentosTrabajador';
        modal.className = 'modal-documentos-trabajador';
        document.body.appendChild(modal);
    }

    const _extIcon = (ext) => {
        if (ext === 'pdf')                              return ['fa-file-pdf',   'pdf'];
        if (['jpg','jpeg','png','gif','webp','bmp'].includes(ext)) return ['fa-file-image', 'image'];
        if (['doc','docx'].includes(ext))               return ['fa-file-word',  'word'];
        if (['xls','xlsx'].includes(ext))               return ['fa-file-excel', 'excel'];
        return ['fa-file', 'default'];
    };

    const contenidoHTML = (!documentos || documentos.length === 0)
        ? `<div class="sin-documentos-trabajador">
               <i class="fas fa-folder-open"></i>
               <h4>No hay documentos disponibles</h4>
               <p>Este trabajador no ha subido ningún documento aún.</p>
           </div>`
        : `<div class="documentos-grid-trabajador">
               ${documentos.map(doc => {
                   const url = doc.archivo_url || '';
                   const ext = url.split('.').pop().toLowerCase();
                   const [iconClass, colorClass] = _extIcon(ext);
                   const titulo = (doc.tipo_documento || 'Documento').replace(/'/g, "\\'").replace(/"/g, '&quot;');
                   const urlEsc = url.replace(/'/g, "\\'").replace(/"/g, '&quot;');
                   return `
                       <div class="documento-card-trabajador">
                           <div class="documento-icon-trabajador ${colorClass}">
                               <i class="fas ${iconClass}"></i>
                           </div>
                           <div class="documento-info-trabajador">
                               <h5>${doc.tipo_documento || 'Documento'}</h5>
                               <p class="documento-fecha">
                                   <i class="fas fa-calendar-alt"></i>
                                   ${doc.fecha_subida ? new Date(doc.fecha_subida).toLocaleDateString('es-ES') : 'Sin fecha'}
                               </p>
                           </div>
                           <button class="btn-ver-doc-trabajador"
                                   onclick="visualizarDocumento('${urlEsc}','${titulo}','${ext}')">
                               <i class="fas fa-eye"></i> Ver
                           </button>
                       </div>`;
               }).join('')}
           </div>`;

    modal.innerHTML = `
        <div class="modal-documentos-content-trabajador">
            <div class="modal-documentos-header-trabajador">
                <h3><i class="fas fa-file-alt"></i> Documentos del Trabajador</h3>
                <button class="modal-close-trabajador" onclick="cerrarModalDocumentosTrabajador()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-documentos-body-trabajador">${contenidoHTML}</div>
        </div>`;

    _agregarEstilosModalDocumentos();
    modal.style.display = 'flex';
}

function visualizarDocumento(url, titulo, extension) {
    let visor = document.getElementById('visorDocumentoTrabajador');
    if (!visor) {
        visor = document.createElement('div');
        visor.id = 'visorDocumentoTrabajador';
        visor.className = 'visor-documento-trabajador';
        document.body.appendChild(visor);
    }

    let contenido = '';
    if (['jpg','jpeg','png','gif','bmp','webp'].includes(extension)) {
        contenido = `<img src="${url}" alt="${titulo}" style="max-width:100%;max-height:100%;object-fit:contain;">`;
    } else if (extension === 'pdf') {
        contenido = `<iframe src="${url}#toolbar=1&navpanes=1&scrollbar=1" type="application/pdf" style="width:100%;height:100%;border:none;"></iframe>`;
    } else {
        contenido = `
            <div style="text-align:center;padding:60px;color:#718096;">
                <i class="fas fa-file" style="font-size:80px;margin-bottom:20px;color:#cbd5e0;display:block;"></i>
                <h4 style="color:#4a5568;margin-bottom:15px;">Vista previa no disponible</h4>
                <p>Este tipo de archivo (.${extension}) no se puede visualizar en el navegador.</p>
                <a href="${url}" download style="
                    display:inline-block;padding:12px 24px;
                    background:linear-gradient(135deg,#4a7c59,#1e3a2e);
                    color:white;text-decoration:none;border-radius:10px;font-weight:600;">
                    <i class="fas fa-download"></i> Descargar Documento
                </a>
            </div>`;
    }

    visor.innerHTML = `
        <div class="visor-documento-content-trabajador">
            <div class="visor-documento-header-trabajador">
                <h4><i class="fas fa-file"></i> ${titulo}</h4>
                <button class="modal-close-trabajador" onclick="cerrarVisorDocumento()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="visor-documento-body-trabajador">${contenido}</div>
        </div>`;

    _agregarEstilosVisorDocumento();
    visor.style.display = 'flex';
}

function cerrarModalDocumentosTrabajador() {
    const modal = document.getElementById('modalDocumentosTrabajador');
    if (modal) modal.style.display = 'none';
}

function cerrarVisorDocumento() {
    const visor = document.getElementById('visorDocumentoTrabajador');
    if (visor) visor.style.display = 'none';
}

// ================================================================
// REPORTAR TRABAJADOR
// ================================================================

async function reportarTrabajador(trabajadorId, nombreTrabajador) {
    const motivo = prompt(`¿Por qué deseas reportar a ${nombreTrabajador}?\n\nEscribe el motivo (mínimo 10 caracteres):`);
    if (!motivo || motivo.trim().length < 10) {
        if (motivo !== null) alert('El motivo debe tener al menos 10 caracteres.');
        return;
    }
    try {
        showStatusMessage('Enviando reporte...', 'info');
        const response = await fetch('/api/reportar-usuario-v2', {
            method: 'POST', credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ usuario_reportado: trabajadorId, motivo: motivo.trim() })
        });
        const data = await response.json();
        if (data.success) {
            showStatusMessage('Reporte enviado correctamente', 'success');
            closeWorkerProfileModal();
        } else {
            showStatusMessage(data.message, 'error');
        }
    } catch (error) {
        showStatusMessage('Tu reporte ha sido registrado', 'success');
        closeWorkerProfileModal();
    }
}

// ================================================================
// MAPA Y GEOLOCALIZACIÓN
// ================================================================

function initMap() {
    const mapElement = document.getElementById('map');
    if (!mapElement) return;

    try {
        map = L.map('map').setView([4.7110, -74.0721], 12);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors', maxZoom: 18
        }).addTo(map);
        cargarUbicacionPredio();
        setTimeout(agregarBotonActualizarTrabajadores, 1000);
    } catch (error) {
        console.error('❌ Error inicializando mapa:', error);
    }
}

async function cargarUbicacionPredio() {
    try {
        const response = await fetch('/api/get_user_location', { credentials: 'include' });
        const data     = await response.json();

        if (data.success && data.location && !data.is_default) {
            const { lat, lng, nombre } = data.location;
            currentFarmerLocation = { lat, lng };
            map.setView([lat, lng], 13);
            agregarMarcadorPredio(lat, lng, nombre);
            cargarTrabajadoresCercanos(lat, lng);
        } else {
            solicitarUbicacionUsuario();
        }
    } catch (error) {
        solicitarUbicacionUsuario();
    }
}

function solicitarUbicacionUsuario() {
    if (!('geolocation' in navigator)) {
        showStatusMessage('Tu navegador no soporta geolocalización', 'warning');
        return usarUbicacionPorDefecto();
    }

    mostrarModalUbicacion();

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            currentFarmerLocation = { lat, lng };
            map.setView([lat, lng], 13);
            agregarMarcadorPredio(lat, lng, 'Mi Ubicación');
            cargarTrabajadoresCercanos(lat, lng);
            setTimeout(() => confirmarGuardarUbicacion(lat, lng), 1000);
        },
        (error) => {
            const msgs = {
                [error.PERMISSION_DENIED]:  'Permiso denegado. Por favor, activa la ubicación en tu navegador.',
                [error.POSITION_UNAVAILABLE]:'Ubicación no disponible. Intenta más tarde.',
                [error.TIMEOUT]:            'Tiempo de espera agotado. Intenta de nuevo.',
            };
            mostrarErrorUbicacion(msgs[error.code] || 'No se pudo obtener tu ubicación.');
            usarUbicacionPorDefecto();
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
}

function mostrarModalUbicacion() {
    const old = document.getElementById('modalUbicacion');
    if (old) old.remove();

    const modal = document.createElement('div');
    modal.id = 'modalUbicacion';
    modal.style.cssText = `position:fixed;top:0;left:0;width:100%;height:100%;
        background:rgba(0,0,0,.7);z-index:99999;display:flex;align-items:center;
        justify-content:center;backdrop-filter:blur(8px);`;
    modal.innerHTML = `
        <div style="background:white;border-radius:20px;padding:40px;max-width:500px;width:90%;
                    text-align:center;box-shadow:0 25px 50px rgba(0,0,0,.5);">
            <div style="width:80px;height:80px;background:linear-gradient(135deg,#4a7c59,#1e3a2e);
                        border-radius:50%;margin:0 auto 25px;display:flex;align-items:center;
                        justify-content:center;color:white;font-size:36px;">
                <i class="fas fa-map-marker-alt"></i>
            </div>
            <h2 style="color:#1e3a2e;font-size:24px;font-weight:700;margin-bottom:15px;">Configura tu Ubicación</h2>
            <p style="color:#4a7c59;font-size:16px;line-height:1.6;margin-bottom:25px;">
                Para mostrarte trabajadores cercanos a tu predio, necesitamos conocer tu ubicación.
            </p>
            <div style="display:flex;align-items:center;justify-content:center;gap:8px;color:#6c757d;font-size:13px;">
                <div style="width:20px;height:20px;border:3px solid rgba(74,124,89,.2);border-top-color:#4a7c59;
                            border-radius:50%;animation:spin 1s linear infinite;"></div>
                <span>Esperando permiso de ubicación...</span>
            </div>
        </div>`;
    document.body.appendChild(modal);
    _ensureSpinKeyframe();
}

function cerrarModalUbicacion() {
    const modal = document.getElementById('modalUbicacion');
    if (modal) modal.remove();
}

function confirmarGuardarUbicacion(lat, lng) {
    cerrarModalUbicacion();
    const modal = document.createElement('div');
    modal.id = 'modalConfirmarUbicacion';
    modal.style.cssText = `position:fixed;top:0;left:0;width:100%;height:100%;
        background:rgba(0,0,0,.7);z-index:99999;display:flex;align-items:center;
        justify-content:center;backdrop-filter:blur(8px);`;
    modal.innerHTML = `
        <div style="background:white;border-radius:20px;padding:35px;max-width:450px;width:90%;
                    text-align:center;box-shadow:0 25px 50px rgba(0,0,0,.5);">
            <div style="width:70px;height:70px;background:linear-gradient(135deg,#22c55e,#16a34a);
                        border-radius:50%;margin:0 auto 20px;display:flex;align-items:center;
                        justify-content:center;color:white;font-size:32px;">
                <i class="fas fa-check"></i>
            </div>
            <h2 style="color:#1e3a2e;font-size:22px;font-weight:700;margin-bottom:12px;">Ubicación Obtenida</h2>
            <p style="color:#4a7c59;font-size:15px;margin-bottom:25px;">¿Deseas guardar esta ubicación como tu predio?</p>
            <div style="display:flex;gap:12px;justify-content:center;">
                <button onclick="guardarUbicacionConfirmada(${lat},${lng})"
                        style="padding:12px 28px;background:linear-gradient(135deg,#4a7c59,#1e3a2e);
                               color:white;border:none;border-radius:12px;font-weight:600;cursor:pointer;">
                    <i class="fas fa-save"></i> Sí, Guardar
                </button>
                <button onclick="cerrarModalConfirmarUbicacion()"
                        style="padding:12px 28px;background:#f1f3f4;color:#5f6368;
                               border:2px solid #e1e8ed;border-radius:12px;font-weight:600;cursor:pointer;">
                    Ahora No
                </button>
            </div>
        </div>`;
    document.body.appendChild(modal);
}

function cerrarModalConfirmarUbicacion() {
    const modal = document.getElementById('modalConfirmarUbicacion');
    if (modal) modal.remove();
}

async function guardarUbicacionConfirmada(lat, lng) {
    cerrarModalConfirmarUbicacion();
    await guardarUbicacionPredio(lat, lng);
}

function mostrarErrorUbicacion(mensaje) {
    cerrarModalUbicacion();
    const modal = document.createElement('div');
    modal.style.cssText = `position:fixed;top:0;left:0;width:100%;height:100%;
        background:rgba(0,0,0,.7);z-index:99999;display:flex;align-items:center;
        justify-content:center;backdrop-filter:blur(8px);`;
    modal.innerHTML = `
        <div style="background:white;border-radius:20px;padding:35px;max-width:450px;width:90%;text-align:center;">
            <div style="width:70px;height:70px;background:linear-gradient(135deg,#ef4444,#dc2626);
                        border-radius:50%;margin:0 auto 20px;display:flex;align-items:center;
                        justify-content:center;color:white;font-size:32px;">
                <i class="fas fa-exclamation-triangle"></i>
            </div>
            <h2 style="color:#1e3a2e;margin-bottom:12px;">Error de Ubicación</h2>
            <p style="color:#4a7c59;margin-bottom:25px;">${mensaje}</p>
            <button onclick="this.parentElement.parentElement.remove()"
                    style="padding:12px 32px;background:linear-gradient(135deg,#4a7c59,#1e3a2e);
                           color:white;border:none;border-radius:12px;font-weight:600;cursor:pointer;">
                Entendido
            </button>
        </div>`;
    document.body.appendChild(modal);
}

function usarUbicacionPorDefecto() {
    const lat = 4.7110, lng = -74.0721;
    currentFarmerLocation = { lat, lng };
    map.setView([lat, lng], 12);
    agregarMarcadorPredio(lat, lng, 'Ubicación Por Defecto');
    showStatusMessage('Usando ubicación por defecto. Configura tu predio para mejores resultados.', 'info');
}

function agregarMarcadorPredio(lat, lng, nombre) {
    const icon = L.divIcon({
        className: 'predio-marker',
        html: `<div style="width:40px;height:40px;background:#4a7c59;border:4px solid white;
                border-radius:50%;box-shadow:0 4px 10px rgba(0,0,0,.4);
                display:flex;align-items:center;justify-content:center;">
                <i class="fas fa-home" style="color:white;font-size:18px;"></i></div>`,
        iconSize: [40, 40], iconAnchor: [20, 20]
    });

    if (farmerMarker) map.removeLayer(farmerMarker);
    farmerMarker = L.marker([lat, lng], { icon }).addTo(map);
    farmerMarker.bindPopup(`
        <div style="text-align:center;padding:12px;">
            <strong style="color:#4a7c59;font-size:16px;"><i class="fas fa-home"></i> ${nombre}</strong>
            <p style="margin:8px 0 0;font-size:12px;color:#666;">${lat.toFixed(6)}, ${lng.toFixed(6)}</p>
        </div>`).openPopup();
}

async function cargarTrabajadoresCercanos(lat, lng, radius = 50) {
    try {
        const response = await fetch('/api/get_nearby_workers', {
            method: 'POST', credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ latitude: lat, longitude: lng, radius })
        });
        const data = await response.json();

        if (data.success) {
            limpiarMarcadoresTrabajadores();
            data.trabajadores.forEach(agregarMarcadorTrabajador);
            showStatusMessage(
                data.total === 0
                    ? 'No hay trabajadores disponibles cerca'
                    : `${data.total} trabajadores disponibles cerca de ti`,
                data.total === 0 ? 'info' : 'success'
            );
        } else {
            showStatusMessage('Error al cargar trabajadores', 'error');
        }
    } catch (error) {
        showStatusMessage('Error de conexión', 'error');
    }
}

function agregarMarcadorTrabajador(trabajador) {
    const icon = L.divIcon({
        className: 'worker-marker',
        html: `<div style="background:#2563eb;width:32px;height:32px;border-radius:50%;
                border:3px solid white;box-shadow:0 3px 6px rgba(0,0,0,.3);
                display:flex;align-items:center;justify-content:center;cursor:pointer;">
                <i class="fas fa-user" style="color:white;font-size:14px;"></i></div>`,
        iconSize: [32, 32], iconAnchor: [16, 16]
    });

    const marker = L.marker([trabajador.lat, trabajador.lng], { icon }).addTo(map);
    const starsHtml = _generarEstrellas(trabajador.calificacion);

    marker.bindPopup(`
        <div style="min-width:280px;padding:14px;font-family:'Segoe UI',sans-serif;">
            <div style="display:flex;align-items:center;margin-bottom:12px;">
                ${trabajador.foto
                    ? `<img src="${trabajador.foto}" style="width:50px;height:50px;border-radius:50%;margin-right:12px;object-fit:cover;">`
                    : `<div style="width:50px;height:50px;border-radius:50%;background:#2563eb;
                           display:flex;align-items:center;justify-content:center;margin-right:12px;">
                           <i class="fas fa-user" style="color:white;font-size:20px;"></i></div>`}
                <div>
                    <h4 style="margin:0 0 4px;color:#1e3a2e;font-size:16px;font-weight:600;">${trabajador.nombre}</h4>
                    <div style="font-size:13px;color:#f59e0b;">${starsHtml} ${trabajador.calificacion.toFixed(1)}</div>
                </div>
            </div>
            <div style="background:#f0f9ff;padding:10px;border-radius:8px;margin-bottom:10px;">
                <div style="display:flex;align-items:center;margin-bottom:6px;">
                    <i class="fas fa-briefcase" style="color:#2563eb;margin-right:8px;width:16px;"></i>
                    <span style="font-size:13px;"><strong>${trabajador.trabajos}</strong> trabajos completados</span>
                </div>
                <div style="display:flex;align-items:center;margin-bottom:6px;">
                    <i class="fas fa-map-marker-alt" style="color:#dc2626;margin-right:8px;width:16px;"></i>
                    <span style="font-size:13px;"><strong>${trabajador.distancia} km</strong> de distancia</span>
                </div>
                ${trabajador.telefono ? `
                <div style="display:flex;align-items:center;">
                    <i class="fas fa-phone" style="color:#16a34a;margin-right:8px;width:16px;"></i>
                    <span style="font-size:13px;">${trabajador.telefono}</span>
                </div>` : ''}
            </div>
            ${trabajador.habilidades.length > 0 ? `
            <div style="margin:10px 0;">
                <strong style="font-size:13px;color:#4b5563;">Habilidades:</strong>
                <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;">
                    ${trabajador.habilidades.slice(0,3).map(h => `
                        <span style="background:#dbeafe;color:#1e40af;padding:4px 10px;
                              border-radius:12px;font-size:11px;font-weight:500;">${h}</span>`).join('')}
                </div>
            </div>` : ''}
            <button onclick="verPerfilTrabajadorDesdeMapa(${trabajador.id})"
                    style="width:100%;background:linear-gradient(135deg,#2563eb,#1d4ed8);color:white;
                           border:none;padding:10px 16px;border-radius:8px;cursor:pointer;
                           font-size:14px;font-weight:600;margin-top:10px;">
                <i class="fas fa-user-circle"></i> Ver Perfil Completo
            </button>
        </div>`, { maxWidth: 320, className: 'custom-popup' });

    workerMarkers.push(marker);
}

function limpiarMarcadoresTrabajadores() {
    workerMarkers.forEach(m => map.removeLayer(m));
    workerMarkers = [];
}

async function guardarUbicacionPredio(lat, lng) {
    try {
        const response = await fetch('/api/save_user_location', {
            method: 'POST', credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ latitude: lat, longitude: lng })
        });
        const data = await response.json();
        showStatusMessage(data.success ? 'Ubicación guardada correctamente' : 'Error guardando ubicación',
                          data.success ? 'success' : 'error');
    } catch (error) {
        showStatusMessage('Error de conexión', 'error');
    }
}

function agregarBotonActualizarTrabajadores() {
    if (!map) return;
    const control = L.control({ position: 'topright' });
    control.onAdd = function () {
        const div = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
        div.innerHTML = `<a href="#" title="Actualizar trabajadores"
            style="background:white;width:34px;height:34px;display:flex;align-items:center;
                   justify-content:center;font-size:18px;color:#2563eb;text-decoration:none;">
            <i class="fas fa-sync-alt"></i></a>`;
        div.onclick = (e) => {
            e.preventDefault();
            if (currentFarmerLocation) cargarTrabajadoresCercanos(currentFarmerLocation.lat, currentFarmerLocation.lng);
        };
        return div;
    };
    control.addTo(map);
}

// ================================================================
// VER PERFIL DESDE MAPA
// ================================================================

async function verPerfilTrabajadorDesdeMapa(trabajadorId) {
    if (!trabajadorId || isNaN(trabajadorId))
        return showStatusMessage('Error: ID de trabajador no válido', 'error');

    if (map && map.closePopup) map.closePopup();

    try {
        showStatusMessage('Cargando perfil del trabajador...', 'info');
        const response = await fetch(`/api/get_worker_profile/${trabajadorId}`, {
            method: 'GET', credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache' }
        });
        if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
        const data = await response.json();
        if (data.success && data.worker) {
            mostrarPerfilTrabajador(data.worker);
            showStatusMessage('Perfil cargado correctamente', 'success');
        } else {
            throw new Error(data.message || 'No se pudo cargar el perfil');
        }
    } catch (error) {
        showStatusMessage('Error al cargar perfil: ' + error.message, 'error');
        _mostrarModalError('No se pudo cargar el perfil del trabajador. Por favor, intenta de nuevo.');
    }
}

function _mostrarModalError(mensaje) {
    const modal = document.createElement('div');
    modal.style.cssText = `position:fixed;top:0;left:0;width:100%;height:100%;
        background:rgba(0,0,0,.7);z-index:99999;display:flex;align-items:center;
        justify-content:center;backdrop-filter:blur(8px);`;
    modal.innerHTML = `
        <div style="background:white;border-radius:20px;padding:35px;max-width:450px;width:90%;text-align:center;">
            <div style="width:70px;height:70px;background:linear-gradient(135deg,#ef4444,#dc2626);
                        border-radius:50%;margin:0 auto 20px;display:flex;align-items:center;
                        justify-content:center;color:white;font-size:32px;">
                <i class="fas fa-exclamation-triangle"></i>
            </div>
            <h2 style="color:#1e3a2e;font-size:22px;margin-bottom:12px;">Error al Cargar Perfil</h2>
            <p style="color:#4a7c59;font-size:15px;margin-bottom:25px;">${mensaje}</p>
            <button onclick="this.parentElement.parentElement.remove()"
                    style="padding:12px 32px;background:linear-gradient(135deg,#4a7c59,#1e3a2e);
                           color:white;border:none;border-radius:12px;font-weight:600;cursor:pointer;">
                <i class="fas fa-check"></i> Entendido
            </button>
        </div>`;
    document.body.appendChild(modal);
    setTimeout(() => { if (document.body.contains(modal)) modal.remove(); }, 5000);
}

// ================================================================
// SISTEMA DE CALIFICACIONES
// ================================================================

function _generarEstrellas(rating) {
    const full  = Math.floor(rating);
    const half  = (rating % 1) >= 0.5;
    const empty = 5 - full - (half ? 1 : 0);
    return '<i class="fas fa-star" style="color:#f59e0b;font-size:13px;"></i>'.repeat(full) +
           (half ? '<i class="fas fa-star-half-alt" style="color:#f59e0b;font-size:13px;"></i>' : '') +
           '<i class="far fa-star" style="color:#f59e0b;font-size:13px;"></i>'.repeat(empty);
}

async function loadUserRating() {
    try {
        if (!currentUser || !currentUser.userId) return;
        const response = await fetch(`/api/get_user_rating/${currentUser.userId}`, { credentials: 'include' });
        const data = await response.json();
        if (data.success) {
            const starsHTML = generateStarsHTML(data.promedio);
            const ratingHTML = `
                ${starsHTML}
                <span class="rating-value" style="font-weight:700;color:#fff;margin-left:8px;">
                    ${data.promedio.toFixed(1)}
                </span>
                <span class="rating-count" style="color:rgba(255,255,255,.55);font-size:12px;margin-left:4px;">
                    (${data.total_calificaciones})
                </span>`;
            const el = document.querySelector('.profile-rating');
            if (el) el.innerHTML = ratingHTML;
            const sidebarRating = document.getElementById('sidebarRating');
            if (sidebarRating) sidebarRating.innerHTML = ratingHTML;
        }
    } catch (error) {
        console.error('Error cargando calificación:', error);
    }
}

function generateStarsHTML(rating) {
    const full = Math.floor(rating);
    const half = (rating % 1) >= 0.5;
    const empty = 5 - full - (half ? 1 : 0);
    return '<i class="fas fa-star" style="color:#E8B84B;font-size:17px;"></i>'.repeat(full) +
           (half ? '<i class="fas fa-star-half-alt" style="color:#E8B84B;font-size:17px;"></i>' : '') +
           '<i class="far fa-star" style="color:rgba(255,255,255,.3);font-size:17px;"></i>'.repeat(empty);
}

// ================================================================
// SISTEMA DE NOTIFICACIONES — MEJORADO (sin emojis)
// ================================================================

async function loadNotifications() {
    try {
        const response = await fetch('/api/get_notifications', { credentials: 'include' });
        const data = await response.json();
        if (data.success && data.notificaciones) {
            updateNotificationBadge(data.no_leidas);
            displayNotifications(data.notificaciones);
        }
    } catch (error) {
        console.error('Error cargando notificaciones:', error);
    }
}

function updateNotificationBadge(count) {
    const badge = document.getElementById('notificationBadge');
    if (!badge) return;
    badge.textContent = count > 9 ? '9+' : count;
    badge.style.display = count > 0 ? 'block' : 'none';
}

// Mapas de icono y color según tipo de notificación
const NOTIF_ICON  = { postulacion:'fa-user-plus', aceptado:'fa-check-circle', rechazado:'fa-times-circle', mensaje:'fa-comment-alt', sistema:'fa-bell', default:'fa-bell' };
const NOTIF_COLOR = { postulacion:'#4A7A34', aceptado:'#28A060', rechazado:'#B83030', mensaje:'#243C50', sistema:'#C9943A', default:'#4A7A34' };

function _notifIcon(tipo)  { return NOTIF_ICON[tipo]  || NOTIF_ICON.default; }
function _notifColor(tipo) { return NOTIF_COLOR[tipo] || NOTIF_COLOR.default; }

function displayNotifications(notificaciones) {
    const container = document.querySelector('.notifications');
    if (!container) return;

    const titleHTML = `
        <div class="section-title">
            <i class="fas fa-bell"></i>
            <span>Notificaciones Recientes</span>
        </div>`;

    if (notificaciones.length === 0) {
        container.innerHTML = titleHTML + `
            <div class="notif-empty-sidebar">
                <i class="fas fa-bell-slash"></i>
                <p>Sin notificaciones</p>
            </div>`;
        return;
    }

    let html = titleHTML;

    notificaciones.slice(0, 3).forEach(notif => {
        const tipo  = notif.tipo || 'default';
        const icon  = _notifIcon(tipo);
        const color = _notifColor(tipo);
        const unread = !notif.leida;

        html += `
            <div class="notification-item${unread ? ' unread' : ''}"
                 onclick="handleNotificationClick('${notif.id}','${notif.link || ''}')">
                <div class="notif-icon-badge" style="background:${color}18;border:1.5px solid ${color}35;">
                    <i class="fas ${icon}" style="color:${color};font-size:12px;"></i>
                </div>
                <div class="notif-body">
                    <div class="notif-title">${notif.titulo}</div>
                    <div class="notif-text">${notif.mensaje}</div>
                    <div class="notif-time">
                        <i class="far fa-clock"></i>
                        ${formatearTiempoTranscurrido(notif.fecha)}
                    </div>
                </div>
                ${unread ? '<span class="notif-dot"></span>' : ''}
            </div>`;
    });

    if (notificaciones.length > 3) {
        html += `
            <div class="notif-ver-todas" onclick="showNotifications()">
                <i class="fas fa-list"></i>
                Ver todas (${notificaciones.length})
            </div>`;
    }

    container.innerHTML = html;
}

function handleNotificationClick(notifId, link) {
    fetch('/api/mark_notification_read', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notification_id: notifId })
    }).catch(() => {});

    if (link && link !== '' && link !== 'undefined') window.location.href = link;
}

function formatearTiempoTranscurrido(fechaISO) {
    if (!fechaISO) return 'Ahora';
    const diff = Math.floor((new Date() - new Date(fechaISO)) / 1000);
    if (diff < 60)     return 'Ahora';
    if (diff < 3600)   return `Hace ${Math.floor(diff / 60)} min`;
    if (diff < 86400)  return `Hace ${Math.floor(diff / 3600)}h`;
    if (diff < 604800) return `Hace ${Math.floor(diff / 86400)}d`;
    return new Date(fechaISO).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
}

async function showNotifications() {
    let modal = document.getElementById('notificationsModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'notificationsModal';
        modal.style.cssText = `position:fixed;top:0;left:0;width:100%;height:100%;
            background:rgba(0,0,0,.7);z-index:99999;display:none;align-items:center;
            justify-content:center;padding:20px;backdrop-filter:blur(8px);`;
        document.body.appendChild(modal);
    }

    try {
        const response = await fetch('/api/get_notifications', { credentials: 'include' });
        const data = await response.json();

        if (data.success) {
            const itemsHTML = data.notificaciones.length === 0
                ? `<div style="text-align:center;padding:60px 20px;color:#6c757d;">
                       <i class="fas fa-bell-slash" style="font-size:56px;margin-bottom:16px;display:block;color:#cbd5e0;"></i>
                       <h4 style="margin:0;font-size:18px;">Sin notificaciones</h4>
                   </div>`
                : data.notificaciones.map(n => {
                    const tipo  = n.tipo || 'default';
                    const icon  = _notifIcon(tipo);
                    const color = _notifColor(tipo);
                    return `
                        <div style="display:flex;gap:14px;align-items:flex-start;
                                    padding:16px;border-radius:12px;margin-bottom:10px;
                                    background:${n.leida ? '#f8f9fa' : '#f0f7eb'};
                                    border:1px solid ${n.leida ? '#e9ecef' : color+'30'};
                                    border-left:3px solid ${color};cursor:pointer;
                                    transition:transform .15s ease;"
                             onmouseover="this.style.transform='translateX(3px)'"
                             onmouseout="this.style.transform=''"
                             onclick="handleNotificationClick('${n.id}','${n.link || ''}')">
                            <div style="width:42px;height:42px;border-radius:10px;flex-shrink:0;
                                        background:${color}15;border:1.5px solid ${color}30;
                                        display:flex;align-items:center;justify-content:center;">
                                <i class="fas ${icon}" style="color:${color};font-size:16px;"></i>
                            </div>
                            <div style="flex:1;min-width:0;">
                                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:5px;">
                                    <strong style="color:#1e3a2e;font-size:14px;font-weight:600;">${n.titulo}</strong>
                                    <span style="color:#6c757d;font-size:11px;white-space:nowrap;margin-left:10px;display:flex;align-items:center;gap:4px;">
                                        <i class="far fa-clock"></i>${formatearTiempoTranscurrido(n.fecha)}
                                    </span>
                                </div>
                                <p style="margin:0;color:#495057;font-size:13px;line-height:1.5;">${n.mensaje}</p>
                            </div>
                        </div>`;
                }).join('');

            modal.innerHTML = `
                <div style="background:white;border-radius:20px;max-width:680px;width:100%;
                            max-height:82vh;display:flex;flex-direction:column;
                            box-shadow:0 25px 70px rgba(0,0,0,.45);">
                    <div style="padding:22px 28px;background:linear-gradient(135deg,#2C1C0A,#4A3118,#8B5E2D);
                                color:white;border-radius:20px 20px 0 0;display:flex;
                                justify-content:space-between;align-items:center;">
                        <h3 style="margin:0;font-size:18px;display:flex;align-items:center;gap:10px;font-weight:600;">
                            <i class="fas fa-bell"></i> Notificaciones
                            <span style="background:rgba(255,255,255,.18);padding:2px 10px;border-radius:20px;font-size:13px;">${data.total}</span>
                        </h3>
                        <button onclick="closeNotificationsModal()"
                                style="background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.24);
                                       width:36px;height:36px;border-radius:50%;font-size:16px;cursor:pointer;
                                       color:white;display:flex;align-items:center;justify-content:center;
                                       transition:all .2s ease;"
                                onmouseover="this.style.background='rgba(255,255,255,.3)'"
                                onmouseout="this.style.background='rgba(255,255,255,.18)'">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div style="padding:20px 24px;overflow-y:auto;flex:1;">${itemsHTML}</div>
                </div>`;
            modal.style.display = 'flex';
        }
    } catch (error) {
        showStatusMessage('Error cargando notificaciones', 'error');
    }
}

function closeNotificationsModal() {
    const modal = document.getElementById('notificationsModal');
    if (modal) modal.style.display = 'none';
}

function handleNotification(element) {
    element.style.opacity = '0.7';
    element.style.transform = 'translateX(5px)';
    setTimeout(() => {
        element.style.opacity = '1';
        element.style.transform = 'translateX(0)';
        showStatusMessage('Notificación marcada como leída', 'success');
        loadNotifications();
    }, 200);
}

setInterval(() => {
    if (currentUser && currentUser.userId) loadNotifications();
}, 120000);

// ================================================================
// UTILIDADES
// ================================================================

function showStatusMessage(message, type = 'info') {
    const existing = document.querySelector('.status-toast');
    if (existing) existing.remove();

    const el = document.createElement('div');
    el.className = 'status-toast';
    const configs = {
        success: { bg: 'linear-gradient(135deg,#28A060,#186038)', icon: 'fa-check-circle' },
        error:   { bg: 'linear-gradient(135deg,#B83030,#881A1A)', icon: 'fa-exclamation-triangle' },
        warning: { bg: 'linear-gradient(135deg,#C9943A,#8B5E2D)', icon: 'fa-exclamation-circle' },
        info:    { bg: 'linear-gradient(135deg,#243C50,#0F2030)',  icon: 'fa-info-circle' }
    };
    const cfg = configs[type] || configs.info;
    el.style.cssText = `
        position:fixed;top:20px;right:20px;padding:13px 18px;border-radius:12px;
        color:white;font-weight:500;font-size:13px;z-index:999999;max-width:360px;
        box-shadow:0 8px 24px rgba(0,0,0,.25);animation:slideInRight .3s ease;
        background:${cfg.bg};display:flex;align-items:center;gap:10px;`;
    el.innerHTML = `<i class="fas ${cfg.icon}" style="font-size:15px;flex-shrink:0;"></i><span>${message}</span>`;
    document.body.appendChild(el);
    setTimeout(() => {
        if (el.parentNode) {
            el.style.animation = 'slideOutRight .3s ease';
            setTimeout(() => { if (el.parentNode) el.parentNode.removeChild(el); }, 300);
        }
    }, 4000);
}

function showNotificationsGeneric() { showNotifications(); }

// ================================================================
// EVENT LISTENERS
// ================================================================

function setupEventListeners() {
    document.addEventListener('click', function (e) {
        if (!e.target.closest('#profileMenuBtn') && !e.target.closest('#profileDropdown')) {
            closeProfileMenu();
        }
        const modalDoc = document.getElementById('modalDocumentosTrabajador');
        if (modalDoc && e.target === modalDoc) cerrarModalDocumentosTrabajador();
        const visor = document.getElementById('visorDocumentoTrabajador');
        if (visor && e.target === visor) cerrarVisorDocumento();
    }, true);

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            cerrarModalOferta();
            cerrarModalEditar();
            closeProfileMenu();
            closeApplicationsModal();
            closeWorkerProfileModal();
            cerrarModalDocumentosTrabajador();
            cerrarVisorDocumento();
            closeNotificationsModal();
        }
    });

    document.getElementById('modalCrearOferta')?.addEventListener('click', function (e) {
        if (e.target === this) cerrarModalOferta();
    });
    document.getElementById('modalEditarOferta')?.addEventListener('click', function (e) {
        if (e.target === this) cerrarModalEditar();
    });
    document.getElementById('applicationsModal')?.addEventListener('click', function (e) {
        if (e.target === this) closeApplicationsModal();
    });
    document.getElementById('workerProfileModal')?.addEventListener('click', function (e) {
        if (e.target === this) closeWorkerProfileModal();
    });
}

// ================================================================
// CSS DINÁMICO — HELPERS PRIVADOS
// ================================================================

function _ensureSpinKeyframe() {
    if (document.getElementById('spin-keyframe')) return;
    const s = document.createElement('style');
    s.id = 'spin-keyframe';
    s.textContent = `@keyframes spin { to { transform: rotate(360deg); } }`;
    document.head.appendChild(s);
}

// Inyectar estilos de notificaciones sidebar al cargar
(function _inyectarEstilosNotificaciones() {
    if (document.getElementById('notif-sidebar-styles')) return;
    const s = document.createElement('style');
    s.id = 'notif-sidebar-styles';
    s.textContent = `
        /* Items de notificación sidebar */
        .notification-item {
            display: flex;
            gap: 10px;
            align-items: flex-start;
            padding: 10px 12px;
            margin-bottom: 6px;
            border-radius: 10px;
            cursor: pointer;
            transition: transform .16s ease, background .16s;
            background: #FDFCF8;
            border: 1px solid rgba(74,49,24,.12);
            border-left: 3px solid #C9943A;
            position: relative;
        }
        .notification-item:hover {
            transform: translateX(3px);
            background: #FAF7F0;
        }
        .notification-item.unread {
            background: linear-gradient(135deg,rgba(74,122,52,.06),rgba(74,122,52,.02));
            border-left-color: #4A7A34;
        }
        /* Punto de no leído */
        .notif-dot {
            position: absolute;
            top: 10px;
            right: 10px;
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #4A7A34;
            box-shadow: 0 0 0 2px rgba(74,122,52,.20);
        }
        /* Icono coloreado */
        .notif-icon-badge {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-top: 1px;
        }
        /* Cuerpo */
        .notif-body { flex: 1; min-width: 0; }
        .notif-title {
            font-weight: 600;
            color: #2C1C0A;
            font-size: .74rem;
            line-height: 1.3;
            margin-bottom: 2px;
        }
        .notif-text {
            color: #4A3118;
            font-size: .68rem;
            line-height: 1.4;
            opacity: .85;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            margin-bottom: 3px;
        }
        .notif-time {
            color: #8B5E2D;
            font-size: .60rem;
            display: flex;
            align-items: center;
            gap: 3px;
        }
        /* Estado vacío */
        .notif-empty-sidebar {
            text-align: center;
            padding: 28px 16px;
            color: #8B5E2D;
        }
        .notif-empty-sidebar i {
            font-size: 28px;
            display: block;
            margin-bottom: 8px;
            opacity: .45;
        }
        .notif-empty-sidebar p {
            font-size: .76rem;
            opacity: .7;
            margin: 0;
        }
        /* Ver todas */
        .notif-ver-todas {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 7px;
            padding: 9px 12px;
            margin-top: 4px;
            border-radius: 8px;
            cursor: pointer;
            font-size: .72rem;
            font-weight: 600;
            color: #4A7A34;
            background: rgba(74,122,52,.07);
            border: 1px dashed rgba(74,122,52,.28);
            transition: background .16s;
        }
        .notif-ver-todas:hover { background: rgba(74,122,52,.14); }

        /* Animaciones toast */
        @keyframes slideInRight  { from { opacity:0; transform:translateX(100%); } to { opacity:1; transform:translateX(0); } }
        @keyframes slideOutRight { from { opacity:1; transform:translateX(0); } to { opacity:0; transform:translateX(100%); } }
    `;
    document.head.appendChild(s);
})();

function _agregarEstilosPerfilMejorado() {
    if (document.getElementById('estilos-perfil-mejorado')) return;
    const style = document.createElement('style');
    style.id = 'estilos-perfil-mejorado';
    style.textContent = `
        .worker-profile-enhanced { padding: 0; }
        .profile-header-enhanced {
            background: linear-gradient(135deg,rgba(74,124,89,.1),rgba(144,238,144,.1));
            padding: 40px 30px; border-radius: 20px 20px 0 0;
            display: flex; gap: 30px; align-items: center;
        }
        .profile-avatar-large-enhanced {
            width: 140px; height: 140px; border-radius: 50%; flex-shrink: 0;
            background: linear-gradient(135deg,#4a7c59,#1e3a2e);
            display: flex; align-items: center; justify-content: center;
            color: white; font-size: 48px; overflow: hidden;
            box-shadow: 0 12px 30px rgba(74,124,89,.4); border: 5px solid white;
        }
        .profile-info-enhanced { flex: 1; }
        .profile-rating-enhanced { display:flex; align-items:center; gap:8px; margin-bottom:15px; font-size:18px; }
        .profile-stats-row-enhanced { display:flex; gap:25px; margin-top:15px; }
        .stat-item-enhanced {
            display:flex; align-items:center; gap:10px; padding:10px 18px;
            background:rgba(255,255,255,.7); border-radius:10px; font-size:15px;
            color:#4a5568; box-shadow:0 2px 8px rgba(0,0,0,.1);
        }
        .stat-item-enhanced i { color:#4a7c59; font-size:20px; }
        .profile-section-enhanced { padding:30px; border-bottom:1px solid #e2e8f0; }
        .profile-section-enhanced h3 {
            color:#2d3748; font-size:18px; margin-bottom:15px;
            display:flex; align-items:center; gap:10px;
            padding-bottom:10px; border-bottom:2px solid #e2e8f0;
        }
        .contact-info-enhanced { display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:15px; margin-top:15px; }
        .contact-item-enhanced {
            padding:15px 20px; background:#f7fafc; border-radius:12px;
            display:flex; align-items:center; gap:12px;
            border-left:4px solid #4a7c59; font-size:15px; color:#2d3748;
        }
        .contact-item-enhanced i { color:#4a7c59; font-size:20px; }
        .skills-list-enhanced { display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:12px; margin-top:15px; }
        .skill-tag-enhanced {
            padding:15px 18px; background:linear-gradient(135deg,#e7f3ff,#f0f9ff);
            border:2px solid #bae6fd; border-radius:12px;
            display:flex; align-items:center; gap:12px; transition:all .3s ease;
        }
        .skill-tag-enhanced:hover { transform:translateY(-3px); box-shadow:0 8px 20px rgba(37,99,235,.2); border-color:#2563eb; }
        .skill-tag-enhanced i { color:#2563eb; font-size:18px; }
        .skill-tag-enhanced strong { display:block; color:#1e40af; font-size:15px; margin-bottom:3px; }
        .skill-tag-enhanced span   { display:block; color:#64748b; font-size:12px; }
        .experiencia-list-enhanced { display:flex; flex-direction:column; gap:15px; margin-top:15px; }
        .experiencia-item-enhanced {
            padding:20px; background:#f7fafc; border-radius:12px;
            border-left:4px solid #4a7c59; transition:all .3s ease;
        }
        .experiencia-item-enhanced:hover { background:white; box-shadow:0 4px 12px rgba(0,0,0,.1); }
        .experiencia-header { display:flex; align-items:center; gap:10px; color:#2d3748; font-size:16px; margin-bottom:8px; }
        .experiencia-header i { color:#4a7c59; }
        .experiencia-dates { display:flex; align-items:center; gap:8px; color:#718096; font-size:14px; margin-bottom:10px; }
        .experiencia-dates i { color:#4a7c59; }
        .experiencia-description { color:#4a5568; font-size:14px; line-height:1.6; margin:0; }
        .action-buttons-enhanced { display:grid; grid-template-columns:repeat(2,1fr); gap:15px; padding:30px; background:#f7fafc; border-radius:0 0 20px 20px; }
        .btn-action-enhanced {
            padding:16px 24px; border:none; border-radius:12px; font-weight:600; font-size:15px;
            cursor:pointer; display:flex; align-items:center; justify-content:center; gap:10px;
            transition:all .3s ease; box-shadow:0 4px 12px rgba(0,0,0,.1);
        }
        .btn-action-enhanced:hover { transform:translateY(-3px); box-shadow:0 8px 20px rgba(0,0,0,.2); }
        .btn-documentos-enhanced { background:linear-gradient(135deg,#3b82f6,#1e40af); color:white; }
        .btn-reportar-enhanced   { background:linear-gradient(135deg,#ef4444,#b91c1c); color:white; }
        @media (max-width:768px) {
            .profile-header-enhanced { flex-direction:column; text-align:center; }
            .contact-info-enhanced, .skills-list-enhanced, .action-buttons-enhanced { grid-template-columns:1fr; }
        }`;
    document.head.appendChild(style);
}

function _agregarEstilosModalDocumentos() {
    if (document.getElementById('estilos-modal-documentos')) return;
    const style = document.createElement('style');
    style.id = 'estilos-modal-documentos';
    style.textContent = `
        .modal-documentos-trabajador {
            display:none; position:fixed; top:0; left:0; width:100%; height:100%;
            background:rgba(0,0,0,.75); z-index:99999; align-items:center;
            justify-content:center; padding:20px; backdrop-filter:blur(8px);
        }
        .modal-documentos-content-trabajador {
            background:white; border-radius:20px; max-width:900px; width:100%;
            max-height:90vh; display:flex; flex-direction:column;
            box-shadow:0 25px 70px rgba(0,0,0,.5); animation:modalSlideIn .3s ease;
        }
        @keyframes modalSlideIn {
            from { opacity:0; transform:translateY(-50px) scale(.95); }
            to   { opacity:1; transform:translateY(0) scale(1); }
        }
        .modal-documentos-header-trabajador {
            background:linear-gradient(135deg,#3b82f6,#1e40af); color:white;
            padding:25px 30px; border-radius:20px 20px 0 0;
            display:flex; justify-content:space-between; align-items:center;
        }
        .modal-documentos-header-trabajador h3 { font-size:22px; display:flex; align-items:center; gap:12px; margin:0; }
        .modal-close-trabajador {
            background:rgba(255,255,255,.2); border:none; width:40px; height:40px;
            border-radius:50%; font-size:20px; cursor:pointer; color:white;
            display:flex; align-items:center; justify-content:center; transition:all .3s ease;
        }
        .modal-close-trabajador:hover { background:rgba(255,255,255,.3); transform:rotate(90deg); }
        .modal-documentos-body-trabajador { padding:30px; overflow-y:auto; flex:1; }
        .documentos-grid-trabajador { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:20px; }
        .documento-card-trabajador {
            background:#f7fafc; border:2px solid #e2e8f0; border-radius:16px;
            padding:20px; display:flex; flex-direction:column; align-items:center;
            gap:15px; transition:all .3s ease;
        }
        .documento-card-trabajador:hover { border-color:#3b82f6; background:white; transform:translateY(-5px); box-shadow:0 12px 30px rgba(59,130,246,.2); }
        .documento-icon-trabajador {
            width:80px; height:80px; border-radius:16px; display:flex;
            align-items:center; justify-content:center; font-size:36px;
            color:white; box-shadow:0 8px 20px rgba(0,0,0,.15);
        }
        .documento-icon-trabajador.pdf   { background:linear-gradient(135deg,#ef4444,#b91c1c); }
        .documento-icon-trabajador.image { background:linear-gradient(135deg,#8b5cf6,#6d28d9); }
        .documento-icon-trabajador.word  { background:linear-gradient(135deg,#3b82f6,#1e40af); }
        .documento-icon-trabajador.excel { background:linear-gradient(135deg,#10b981,#047857); }
        .documento-icon-trabajador.default { background:linear-gradient(135deg,#64748b,#475569); }
        .documento-info-trabajador { text-align:center; flex:1; }
        .documento-info-trabajador h5 { color:#2d3748; font-size:16px; margin:0 0 8px; font-weight:600; }
        .documento-fecha { color:#718096; font-size:13px; display:flex; align-items:center; justify-content:center; gap:6px; }
        .btn-ver-doc-trabajador {
            width:100%; background:linear-gradient(135deg,#3b82f6,#1e40af); color:white;
            border:none; padding:12px 20px; border-radius:10px; font-weight:600;
            font-size:14px; cursor:pointer; display:flex; align-items:center;
            justify-content:center; gap:8px; transition:all .3s ease;
        }
        .btn-ver-doc-trabajador:hover { background:linear-gradient(135deg,#2563eb,#1e3a8a); transform:translateY(-2px); box-shadow:0 6px 16px rgba(59,130,246,.4); }
        .sin-documentos-trabajador { text-align:center; padding:80px 20px; }
        .sin-documentos-trabajador i { font-size:80px; color:#cbd5e0; margin-bottom:20px; display:block; }
        .sin-documentos-trabajador h4 { color:#2d3748; font-size:22px; margin-bottom:12px; }
        .sin-documentos-trabajador p  { color:#718096; font-size:16px; }
        @media (max-width:768px) { .documentos-grid-trabajador { grid-template-columns:1fr; } }`;
    document.head.appendChild(style);
}

function _agregarEstilosVisorDocumento() {
    if (document.getElementById('estilos-visor-documento')) return;
    const style = document.createElement('style');
    style.id = 'estilos-visor-documento';
    style.textContent = `
        .visor-documento-trabajador {
            display:none; position:fixed; top:0; left:0; width:100%; height:100%;
            background:rgba(0,0,0,.95); z-index:999999; align-items:center;
            justify-content:center; padding:20px; backdrop-filter:blur(10px);
        }
        .visor-documento-content-trabajador {
            width:100%; height:100%; max-width:1400px; max-height:95vh;
            background:white; border-radius:16px; display:flex; flex-direction:column;
            box-shadow:0 30px 80px rgba(0,0,0,.6); animation:visorSlideIn .4s ease;
        }
        @keyframes visorSlideIn {
            from { opacity:0; transform:scale(.9); }
            to   { opacity:1; transform:scale(1); }
        }
        .visor-documento-header-trabajador {
            background:#2d3748; color:white; padding:20px 30px;
            border-radius:16px 16px 0 0; display:flex; justify-content:space-between; align-items:center;
        }
        .visor-documento-header-trabajador h4 { font-size:18px; display:flex; align-items:center; gap:12px; margin:0; }
        .visor-documento-body-trabajador {
            flex:1; overflow:hidden; background:#f7fafc;
            display:flex; align-items:center; justify-content:center;
            border-radius:0 0 16px 16px;
        }
        .visor-documento-body-trabajador iframe,
        .visor-documento-body-trabajador img { width:100%; height:100%; border:none; }
        @media (max-width:768px) {
            .visor-documento-content-trabajador { max-width:100%; max-height:100vh; border-radius:0; }
            .visor-documento-header-trabajador  { border-radius:0; }
            .visor-documento-body-trabajador    { border-radius:0; }
        }`;
    document.head.appendChild(style);
}

// ================================================================
// EXPONER FUNCIONES GLOBALMENTE
// ================================================================

window.toggleProfileMenu             = toggleProfileMenu;
window.closeProfileMenu              = closeProfileMenu;
window.viewProfile                   = viewProfile;
window.viewSettings                  = viewSettings;
window.confirmLogout                 = confirmLogout;
window.showHistorialContrataciones   = showHistorialContrataciones;
window.showEstadisticas              = showEstadisticas;
window.showAyudaSoporte              = showAyudaSoporte;

window.createNewOffer                = createNewOffer;
window.cerrarModalOferta             = cerrarModalOferta;
window.crearOferta                   = crearOferta;
window.editarOferta                  = editarOferta;
window.cerrarModalEditar             = cerrarModalEditar;
window.guardarEdicion                = guardarEdicion;
window.eliminarOferta                = eliminarOferta;
window.duplicarOferta                = duplicarOferta;
window.cerrarOferta                  = cerrarOferta;
window.reabrirOferta                 = reabrirOferta;

window.verPostulaciones              = verPostulaciones;
window.aceptarPostulacionConCierre   = aceptarPostulacionConCierre;
window.rechazarPostulacion           = rechazarPostulacion;
window.closeApplicationsModal        = closeApplicationsModal;

window.verPerfilTrabajador           = verPerfilTrabajador;
window.closeWorkerProfileModal       = closeWorkerProfileModal;
window.verDocumentosTrabajador       = verDocumentosTrabajador;
window.visualizarDocumento           = visualizarDocumento;
window.reportarTrabajador            = reportarTrabajador;
window.cerrarModalDocumentosTrabajador = cerrarModalDocumentosTrabajador;
window.cerrarVisorDocumento          = cerrarVisorDocumento;
window.verPerfilTrabajadorDesdeMapa  = verPerfilTrabajadorDesdeMapa;
window.cambiarPaginaOfertas          = cambiarPaginaOfertas;

window.guardarUbicacionConfirmada    = guardarUbicacionConfirmada;
window.cerrarModalConfirmarUbicacion = cerrarModalConfirmarUbicacion;

window.showNotifications             = showNotifications;
window.closeNotificationsModal       = closeNotificationsModal;
window.handleNotification            = handleNotification;
window.handleNotificationClick       = handleNotificationClick;

console.log('✅ Dashboard Agricultor — listo.');