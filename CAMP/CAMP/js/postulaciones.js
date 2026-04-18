// ===================================================================
// POSTULACIONES.JS - VERSIÓN CORREGIDA Y COMPLETA
// ===================================================================

// Variables globales
let postulacionesData = [];
let currentPage = 1;
const itemsPerPage = 6;
let filteredData = [];
let userData = null;
let refreshInterval;

// ===================================================================
// FUNCIÓN PARA CARGAR DATOS DEL USUARIO
// ===================================================================
async function loadUserData() {
    try {
        const response = await fetch('/get_user_session');
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.user) {
                userData = data.user;
                console.log('✅ Usuario cargado:', userData);
            }
        }
    } catch (error) {
        console.error('❌ Error cargando datos del usuario:', error);
    }
}

// ===================================================================
// FUNCIÓN PRINCIPAL PARA CARGAR POSTULACIONES
// ===================================================================
async function loadPostulacionesFromServer() {
    try {
        console.log('🔄 Cargando postulaciones del servidor...');
        showLoadingState();
        
        const response = await fetch('/api/postulaciones', {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            }
        });
        
        console.log('📥 Respuesta recibida:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('📊 Datos recibidos:', data);
            
            if (data.success) {
                postulacionesData = data.postulaciones || [];
                console.log(`✅ ${postulacionesData.length} postulaciones cargadas`);
                
                // Log de estados para debug
                const estados = postulacionesData.map(p => p.estado);
                console.log('📌 Estados encontrados:', estados);
                
                showToast('success', '✅ Actualizado', `${postulacionesData.length} postulaciones cargadas`);
            } else {
                postulacionesData = [];
                console.warn('⚠️ No se encontraron postulaciones:', data.error);
                showToast('info', 'Sin resultados', data.error || 'No hay postulaciones disponibles');
            }
        } else if (response.status === 401) {
            console.error('❌ Sesión expirada');
            showToast('error', 'Sesión Expirada', 'Por favor inicia sesión nuevamente');
            setTimeout(() => {
                window.location.href = '/vista/login-trabajador.html';
            }, 2000);
            return;
        } else {
            throw new Error(`Error del servidor: ${response.status}`);
        }
    } catch (error) {
        console.error('❌ Error cargando postulaciones:', error);
        postulacionesData = [];
        showToast('error', 'Error de Conexión', 'No se pudieron cargar las postulaciones');
    }
    
    filteredData = [...postulacionesData];
    renderPostulaciones();
    updateTabCounts();
    hideLoadingState();
}

// ===================================================================
// FUNCIÓN PARA MOSTRAR ESTADO DE CARGA
// ===================================================================
function showLoadingState() {
    const container = document.getElementById('postulacionesList');
    if (container) {
        container.innerHTML = `
            <div class="loading-container">
                <div class="loading-spinner"></div>
                <p>⏳ Cargando postulaciones...</p>
            </div>
        `;
    }
}

function hideLoadingState() {
    // Se oculta automáticamente cuando se renderiza el contenido
}

// ===================================================================
// FUNCIÓN PARA RENDERIZAR POSTULACIONES
// ===================================================================
function renderPostulaciones() {
    console.log('🎨 Renderizando postulaciones:', filteredData.length);
    
    const container = document.getElementById('postulacionesList');
    if (!container) {
        console.error('❌ No se encontró el contenedor postulacionesList');
        return;
    }
    
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageData = filteredData.slice(startIndex, endIndex);

    if (pageData.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-paper-plane"></i>
                <h3>No se encontraron postulaciones</h3>
                <p>No hay postulaciones que coincidan con los filtros seleccionados.</p>
                ${postulacionesData.length === 0 ? '<p><small>Es posible que aún no hayas postulado a ningún trabajo.</small></p>' : ''}
            </div>
        `;
        updatePagination();
        return;
    }

    container.innerHTML = pageData.map(postulacion => createPostulacionCard(postulacion)).join('');
    updatePagination();
    addCardAnimations();
}

// ===================================================================
// FUNCIÓN PARA CREAR TARJETA DE POSTULACIÓN
// ===================================================================
function createPostulacionCard(postulacion) {
    const isRecent = checkIfRecent(postulacion.ultimaActualizacion || postulacion.fechaPostulacion);
    const isFavorito = postulacion.estado === 'Favorito';
    
    return `
        <div class="postulacion-card" data-id="${postulacion.id}" data-estado="${postulacion.estado}">
            ${postulacion.estado === 'Aceptada' && isRecent ? 
                '<div class="notificacion-badge">✨ NUEVO</div>' : ''}
            
            ${isFavorito ? 
                '<div class="notificacion-badge" style="background: linear-gradient(135deg, #E91E63, #C2185B);"><i class="fas fa-heart"></i> FAVORITO</div>' : ''}
            
            <div class="postulacion-header">
                <div>
                    <div class="postulacion-title">${postulacion.titulo}</div>
                    <div class="agricultor-info">
                        <i class="fas fa-seedling"></i>
                        ${postulacion.agricultor}
                    </div>
                </div>
                <div class="postulacion-status status-${postulacion.estado.toLowerCase()}">
                    ${getStatusIcon(postulacion.estado)}
                    ${postulacion.estado}
                </div>
            </div>

            <div class="postulacion-details">
                <div class="detail-item">
                    <i class="fas fa-calendar-plus"></i>
                    <span>Postulado: ${formatDate(postulacion.fechaPostulacion)}</span>
                </div>
                <div class="detail-item">
                    <i class="fas fa-dollar-sign"></i>
                    <span>${formatCurrency(postulacion.pago)}/día</span>
                </div>
                <div class="detail-item">
                    <i class="fas fa-map-marker-alt"></i>
                    <span>${postulacion.ubicacion}</span>
                </div>
                <div class="detail-item">
                    <i class="fas fa-clock"></i>
                    <span>${postulacion.duracion || 'Por definir'}</span>
                </div>
            </div>

            <div class="postulacion-timeline">
                ${generateTimeline(postulacion)}
            </div>

            <div class="postulacion-footer">
                <div class="postulacion-actions">
                    <button class="action-btn" onclick="showPostulacionDetails(${postulacion.id})">
                        <i class="fas fa-eye"></i> Ver Detalles
                    </button>
                    ${postulacion.estado === 'Pendiente' ? `
                        <button class="action-btn btn-danger" onclick="cancelarPostulacion(${postulacion.id})">
                            <i class="fas fa-times"></i> Cancelar
                        </button>
                    ` : ''}
                </div>
            </div>
        </div>
    `;
}

// ===================================================================
// FUNCIONES AUXILIARES
// ===================================================================
function getStatusIcon(estado) {
    const icons = {
        'Pendiente': '<i class="fas fa-hourglass-half"></i>',
        'Aceptada': '<i class="fas fa-check-circle"></i>',
        'Rechazada': '<i class="fas fa-times-circle"></i>',
        'Finalizada': '<i class="fas fa-flag-checkered"></i>',
        'Favorito': '<i class="fas fa-heart"></i>'
    };
    return icons[estado] || '<i class="fas fa-question-circle"></i>';
}

function generateTimeline(postulacion) {
    return `
        <div class="timeline-item">
            <i class="fas fa-paper-plane"></i>
            <span>Postulación enviada - ${formatDateTime(postulacion.fechaPostulacion)}</span>
        </div>
    `;
}

function checkIfRecent(dateString) {
    if (!dateString) return false;
    const date = new Date(dateString);
    const now = new Date();
    const diffHours = (now - date) / (1000 * 60 * 60);
    return diffHours < 24;
}

function formatDate(dateString) {
    if (!dateString) return 'Fecha no disponible';
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('es-ES', options);
}

function formatDateTime(dateString) {
    if (!dateString) return 'Fecha no disponible';
    const options = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    return new Date(dateString).toLocaleDateString('es-ES', options);
}

function formatCurrency(amount) {
    if (!amount) return '$0';
    return new Intl.NumberFormat('es-CO', { 
        style: 'currency', 
        currency: 'COP', 
        minimumFractionDigits: 0 
    }).format(amount);
}

// ===================================================================
// FUNCIÓN PARA FILTRAR POR ESTADO
// ===================================================================
function filterByStatus(status) {
    console.log('🔍 Filtrando por estado:', status);
    
    // Actualizar tabs activos
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    if (status === '') {
        filteredData = [...postulacionesData];
    } else {
        filteredData = postulacionesData.filter(p => p.estado === status);
    }

    console.log(`📊 Resultados: ${filteredData.length} postulaciones`);
    currentPage = 1;
    renderPostulaciones();
}

// Hacer la función global
window.filterByStatus = filterByStatus;

// ===================================================================
// FUNCIÓN PARA BÚSQUEDA
// ===================================================================
function setupSearch() {
    const searchInput = document.getElementById('searchPostulaciones');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            console.log('🔎 Buscando:', searchTerm);
            
            filteredData = postulacionesData.filter(postulacion => 
                postulacion.titulo.toLowerCase().includes(searchTerm) ||
                postulacion.agricultor.toLowerCase().includes(searchTerm) ||
                postulacion.ubicacion.toLowerCase().includes(searchTerm)
            );
            
            currentPage = 1;
            renderPostulaciones();
        });
    }
}

// ===================================================================
// FUNCIÓN PARA ACTUALIZAR CONTADORES DE TABS
// ===================================================================
function updateTabCounts() {
    const pendientes = postulacionesData.filter(p => p.estado === 'Pendiente').length;
    const aceptadas = postulacionesData.filter(p => p.estado === 'Aceptada').length;
    const rechazadas = postulacionesData.filter(p => p.estado === 'Rechazada').length;
    const finalizadas = postulacionesData.filter(p => p.estado === 'Finalizada').length;
    const favoritos = postulacionesData.filter(p => p.estado === 'Favorito').length;
    const total = postulacionesData.length;

    const tabs = document.querySelectorAll('.tab-btn');
    if (tabs.length >= 6) {
        tabs[0].innerHTML = `<i class="fas fa-list"></i> Todas (${total})`;
        tabs[1].innerHTML = `<i class="fas fa-hourglass-half"></i> Pendientes (${pendientes})`;
        tabs[2].innerHTML = `<i class="fas fa-check-circle"></i> Aceptadas (${aceptadas})`;
        tabs[3].innerHTML = `<i class="fas fa-times-circle"></i> Rechazadas (${rechazadas})`;
        tabs[4].innerHTML = `<i class="fas fa-flag-checkered"></i> Finalizadas (${finalizadas})`;
        tabs[5].innerHTML = `<i class="fas fa-heart"></i> Favoritos (${favoritos})`;
    }
}

// ===================================================================
// PAGINACIÓN
// ===================================================================
function updatePagination() {
    const totalPages = Math.ceil(filteredData.length / itemsPerPage);
    const currentPageEl = document.getElementById('currentPageNumber');
    const totalPagesEl = document.getElementById('totalPagesNumber');
    
    if (currentPageEl) currentPageEl.textContent = currentPage;
    if (totalPagesEl) totalPagesEl.textContent = totalPages || 1;
}

function previousPage() {
    if (currentPage > 1) {
        currentPage--;
        renderPostulaciones();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function nextPage() {
    const totalPages = Math.ceil(filteredData.length / itemsPerPage);
    if (currentPage < totalPages) {
        currentPage++;
        renderPostulaciones();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

window.previousPage = previousPage;
window.nextPage = nextPage;

// ===================================================================
// FUNCIÓN PARA REFRESCAR
// ===================================================================
function refreshPostulaciones() {
    console.log('🔄 Refrescando postulaciones...');
    loadPostulacionesFromServer();
}

window.refreshPostulaciones = refreshPostulaciones;

// ===================================================================
// SISTEMA DE NOTIFICACIONES (TOAST)
// ===================================================================
function showToast(type, title, message) {
    const container = document.getElementById('toastContainer');
    if (!container) {
        console.warn('⚠️ No se encontró toastContainer');
        return;
    }
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-header">
            <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-triangle' : 'fa-info-circle'} toast-icon"></i>
            <span class="toast-title">${title}</span>
        </div>
        <div class="toast-message">${message}</div>
    `;
    
    container.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 100);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            if (container.contains(toast)) {
                container.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// ===================================================================
// ANIMACIONES
// ===================================================================
function addCardAnimations() {
    const cards = document.querySelectorAll('.postulacion-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

// ===================================================================
// MODAL DE DETALLES
// ===================================================================
function showPostulacionDetails(postulacionId) {
    const postulacion = postulacionesData.find(p => p.id === postulacionId);
    if (!postulacion) {
        showToast('error', 'Error', 'No se encontró la postulación');
        return;
    }
    
    console.log('👁️ Mostrando detalles de:', postulacion);
    
    const modal = document.getElementById('detalleModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    modalTitle.innerHTML = `<i class="fas fa-file-alt"></i> ${postulacion.titulo}`;
    
    modalBody.innerHTML = `
        <div class="modal-detail-section">
            <div class="modal-status-badge status-${postulacion.estado.toLowerCase()}">
                ${getStatusIcon(postulacion.estado)}
                Estado: ${postulacion.estado}
            </div>
        </div>

        <div class="modal-detail-section">
            <h4><i class="fas fa-seedling"></i> Información del Agricultor</h4>
            <p><strong>Nombre:</strong> ${postulacion.agricultor}</p>
            <p><strong>Ubicación:</strong> ${postulacion.ubicacion}</p>
        </div>

        <div class="modal-detail-section">
            <h4><i class="fas fa-briefcase"></i> Detalles del Trabajo</h4>
            <p><strong>Duración:</strong> ${postulacion.duracion || 'Por definir'}</p>
            <p><strong>Pago:</strong> ${formatCurrency(postulacion.pago)} por día</p>
            <p><strong>Descripción:</strong> ${postulacion.descripcion || 'No disponible'}</p>
        </div>

        <div class="modal-detail-section">
            <h4><i class="fas fa-calendar"></i> Fechas Importantes</h4>
            <p><strong>Fecha de postulación:</strong> ${formatDateTime(postulacion.fechaPostulacion)}</p>
        </div>

        <div class="modal-actions">
            ${postulacion.estado === 'Pendiente' ? `
                <button class="btn btn-danger" onclick="cancelarPostulacion(${postulacion.id})">
                    <i class="fas fa-times"></i> Cancelar Postulación
                </button>
            ` : ''}
            <button class="btn btn-secondary" onclick="closeModal()">
                <i class="fas fa-times"></i> Cerrar
            </button>
        </div>
    `;
    
    modal.classList.add('show');
}

window.showPostulacionDetails = showPostulacionDetails;

function closeModal() {
    const modal = document.getElementById('detalleModal');
    if (modal) modal.classList.remove('show');
}

window.closeModal = closeModal;

// ===================================================================
// FUNCIÓN PARA CANCELAR POSTULACIÓN
// ===================================================================
async function cancelarPostulacion(postulacionId) {
    if (!confirm('¿Estás seguro de que deseas cancelar esta postulación?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/cancel_application/${postulacionId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('success', '✅ Cancelada', 'Postulación cancelada correctamente');
            closeModal();
            loadPostulacionesFromServer();
        } else {
            showToast('error', 'Error', data.message || 'No se pudo cancelar');
        }
    } catch (error) {
        console.error('Error cancelando:', error);
        showToast('error', 'Error', 'Error de conexión');
    }
}

window.cancelarPostulacion = cancelarPostulacion;

// ===================================================================
// FUNCIÓN PARA VOLVER
// ===================================================================
function goBack() {
    window.location.href = '/vista/index-trabajador.html';
}

window.goBack = goBack;

// ===================================================================
// INICIALIZACIÓN
// ===================================================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando página de postulaciones...');
    loadUserData();
    loadPostulacionesFromServer();
    setupSearch();
    
    // Auto-refresh cada 30 segundos
    refreshInterval = setInterval(() => {
        console.log('🔄 Auto-refresh de postulaciones');
        loadPostulacionesFromServer();
    }, 30000);
});

// Limpiar interval al salir
window.addEventListener('beforeunload', function() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});

console.log('✅ postulaciones.js cargado correctamente');