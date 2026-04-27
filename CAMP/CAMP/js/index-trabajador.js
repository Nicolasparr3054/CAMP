// ===================================================================
// VARIABLES GLOBALES
// ===================================================================
let appliedJobs = [];
let favoriteJobs = [];
let userData = null;
let currentUser = null;
let map = null;
let favoritosCache = new Set();
let selectedJobId = null;
let ofertasDisponibles = [];
let favoritos = [];

// Variables para geolocalización
let userMarker = null;
let jobMarkers = [];
let currentUserLocation = null;

// ===================================================================
// VERIFICACIÓN DE SESIÓN Y PREVENCIÓN DE CACHÉ
// ===================================================================
async function verificarSesionActiva() {
    try {
        const response = await fetch('/check_session', {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        });
        
        if (!response.ok || response.status === 401) {
            console.log('Sesión no válida, redirigiendo al login');
            window.location.replace('/vista/login-trabajador.html?message=Sesión expirada&type=error');
            return false;
        }
        
        const data = await response.json();
        
        if (!data.authenticated) {
            console.log('No autenticado, redirigiendo al login');
            window.location.replace('/vista/login-trabajador.html?message=Por favor inicia sesión&type=info');
            return false;
        }
        
        return true;
        
    } catch (error) {
        console.error('Error verificando sesión:', error);
        window.location.replace('/vista/login-trabajador.html?message=Error de conexión&type=error');
        return false;
    }
}

window.addEventListener('pageshow', function(event) {
    if (event.persisted) {
        console.log('Página cargada desde caché, verificando sesión...');
        verificarSesionActiva();
    }
});

if (window.performance && window.performance.navigation.type === 2) {
    window.location.reload(true);
}

setInterval(verificarSesionActiva, 5 * 60 * 1000); 

// ===================================================================
// FUNCIONES DE CARGA DE DATOS DE USUARIO
// ===================================================================
async function loadUserData() {
    try {
        console.log('Cargando datos del usuario...');
        
        const response = await fetch('/get_user_session');
        
        if (!response.ok) {
            if (response.status === 401) {
                console.log('No hay sesión activa, redirigiendo al login');
                window.location.href = '/vista/login-trabajador.html';
                return;
            }
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Datos recibidos:', data);
        
        if (data.success && data.user) {
            userData = data.user;
            currentUser = data.user;
            updateUIWithUserData(userData);
            loadUserProfilePhoto();
        } else {
            throw new Error(data.error || 'No se pudieron cargar los datos del usuario');
        }
        
    } catch (error) {
        console.error('Error cargando datos del usuario:', error);
        showErrorMessage('Error al cargar los datos del usuario. Intenta recargar la página.');
        setTimeout(() => showDefaultUserData(), 2000);
    }
}

function updateUIWithUserData(user) {
    console.log('Actualizando UI con datos del usuario:', user);
    
    const profileNameEl = document.getElementById('profileName');
    const fullName = `${user.first_name || ''} ${user.last_name || ''}`.trim();
    const displayName = fullName || user.username || 'Usuario';
    
    if (profileNameEl) {
        profileNameEl.textContent = displayName;
        profileNameEl.classList.remove('skeleton', 'skeleton-text');
        profileNameEl.style.opacity = '0';
        setTimeout(() => {
            profileNameEl.style.transition = 'opacity 0.5s ease';
            profileNameEl.style.opacity = '1';
        }, 100);
    }
    
    const profileAvatarEl = document.getElementById('profileAvatar');
    if (profileAvatarEl) {
        const initials = getInitials(user.first_name, user.last_name);
        profileAvatarEl.innerHTML = `<span style="font-size: 24px; font-weight: bold;">${initials}</span>`;
        profileAvatarEl.classList.remove('skeleton', 'skeleton-circle');
        profileAvatarEl.style.opacity = '0';
        setTimeout(() => {
            profileAvatarEl.style.transition = 'opacity 0.5s ease';
            profileAvatarEl.style.opacity = '1';
        }, 100);
    }
    
    updateDropdownData(user, displayName, getInitials(user.first_name, user.last_name));
}

function updateDropdownData(user, displayName, initials) {
    const dropdownName = document.getElementById('dropdownName');
    if (dropdownName) {
        dropdownName.textContent = displayName;
    }
    
    const dropdownAvatar = document.getElementById('dropdownAvatar');
    if (dropdownAvatar) {
        dropdownAvatar.innerHTML = `<span style="font-size: 24px; font-weight: bold;">${initials}</span>`;
    }
}

function getInitials(firstName, lastName) {
    let initials = '';
    
    if (firstName && firstName.trim()) {
        initials += firstName.trim().charAt(0).toUpperCase();
    }
    
    if (lastName && lastName.trim()) {
        initials += lastName.trim().charAt(0).toUpperCase();
    }
    
    return initials || 'U';
}

function showDefaultUserData() {
    const profileNameEl = document.getElementById('profileName');
    const profileAvatarEl = document.getElementById('profileAvatar');
    const dropdownName = document.getElementById('dropdownName');
    const dropdownAvatar = document.getElementById('dropdownAvatar');
    
    if (profileNameEl) {
        profileNameEl.textContent = 'Usuario';
        profileNameEl.classList.remove('skeleton', 'skeleton-text');
    }
    
    if (profileAvatarEl) {
        profileAvatarEl.innerHTML = '<i class="fas fa-user"></i>';
        profileAvatarEl.classList.remove('skeleton', 'skeleton-circle');
    }
    
    if (dropdownName) dropdownName.textContent = 'Usuario';
    if (dropdownAvatar) dropdownAvatar.innerHTML = '<i class="fas fa-user"></i>';
}

function showErrorMessage(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(errorDiv, container.firstChild);
        setTimeout(() => errorDiv.remove(), 5000);
    }
}

function loadUserProfilePhoto() {
    console.log('Cargando foto de perfil...');
    fetch('/get_user_session')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.user) {
                const photoUrl = data.user.url_foto;
                console.log('URL de foto recibida:', photoUrl);
                
                const profilePhotoElements = document.querySelectorAll('.profile-photo, #profilePhoto, .user-avatar, .profile-image, #profileAvatar, #dropdownAvatar, #profileMenuBtn');
                
                profilePhotoElements.forEach(element => {
                    if (photoUrl && photoUrl !== '' && photoUrl !== null) {
                        element.style.backgroundImage = `url('${photoUrl}')`;
                        element.style.backgroundSize = 'cover';
                        element.style.backgroundPosition = 'center';
                        element.style.borderRadius = '50%';
                        element.innerHTML = '';
                        console.log('Foto aplicada a elemento:', element.id || element.className);
                    } else {
                        element.innerHTML = '<i class="fas fa-user"></i>';
                        element.style.backgroundImage = 'none';
                    }
                });
            }
        })
        .catch(error => {
            console.error('Error cargando foto de perfil:', error);
        });
}

// ===================================================================
// FUNCIONES DE FAVORITOS
// ===================================================================
async function cargarFavoritos() {
    try {
        console.log('Cargando favoritos...');
        const response = await fetch('/api/get_favorites', {
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success) {
            favoritosCache.clear();
            data.favoritos.forEach(fav => {
                favoritosCache.add(fav.id_oferta);
            });
            
            console.log(`Favoritos cargados: ${favoritosCache.size} trabajos`);
            actualizarIconosFavoritos();
        }
    } catch (error) {
        console.error('Error cargando favoritos:', error);
    }
}

function actualizarIconosFavoritos() {
    document.querySelectorAll('.favorite-btn').forEach(btn => {
        const jobId = parseInt(btn.getAttribute('data-job-id'));
        const icon = btn.querySelector('i');
        
        if (favoritosCache.has(jobId)) {
            icon.classList.remove('far');
            icon.classList.add('fas');
            icon.style.color = '#e74c3c';
            btn.classList.add('active');
        } else {
            icon.classList.remove('fas');
            icon.classList.add('far');
            icon.style.color = '';
            btn.classList.remove('active');
        }
    });
}

async function toggleFavorite(button, jobId) {
    console.log('toggleFavorite llamado con:', jobId);
    
    if (!jobId || isNaN(jobId)) {
        console.error('ID inválido recibido:', jobId);
        return;
    }
    
    const icon = button.querySelector('i');
    const isFavorite = favoritosCache.has(jobId);
    const action = isFavorite ? 'remove' : 'add';
    
    button.classList.add('animating');
    setTimeout(() => button.classList.remove('animating'), 400);
    
    try {
        console.log('Enviando petición:', { job_id: jobId, action: action });
        
        const response = await fetch('/api/toggle_favorite', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
                job_id: jobId,
                action: action
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Respuesta del servidor:', data);
        
        if (data.success) {
            if (data.is_favorite) {
                icon.classList.remove('far');
                icon.classList.add('fas');
                icon.style.color = '#e74c3c';
                button.classList.add('active');
                favoritosCache.add(jobId);
                console.log('✅ Agregado a favoritos');
            } else {
                icon.classList.remove('fas');
                icon.classList.add('far');
                icon.style.color = '';
                button.classList.remove('active');
                favoritosCache.delete(jobId);
                console.log('✅ Removido de favoritos');
            }
        } else {
            console.warn('⚠️ Operación no exitosa:', data.message);
        }
        
    } catch (error) {
        console.error('❌ Error completo:', error);
        
        if (action === 'add') {
            icon.classList.remove('fas');
            icon.classList.add('far');
            icon.style.color = '';
            button.classList.remove('active');
        } else {
            icon.classList.remove('far');
            icon.classList.add('fas');
            icon.style.color = '#e74c3c';
            button.classList.add('active');
        }
    }
}

// ===================================================================
// FUNCIONES DE TRABAJOS
// ===================================================================
function loadAvailableJobs() {
    console.log('🔄 Cargando trabajos disponibles...');
    
    fetch('/api/get_jobs', {
        method: 'GET',
        credentials: 'include',
        headers: {
            'Cache-Control': 'no-cache'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            ofertasDisponibles = data.jobs;
            console.log(`✅ ${data.jobs.length} ofertas cargadas`);
            displayJobs(data.jobs);
            updateJobsCount(data.jobs.length);
        } else {
            console.warn('⚠️ No hay ofertas disponibles');
            showNoJobsMessage();
        }
    })
    .catch(error => {
        console.error('❌ Error al cargar trabajos:', error);
        showNoJobsMessage();
    });
}

function displayJobs(jobs) {
    const jobsList = document.getElementById('jobsList');
    const noJobsMessage = document.getElementById('noJobsMessage');
    
    if (jobs.length === 0) {
        showNoJobsMessage();
        return;
    }
    
    if (jobsList) {
        jobsList.innerHTML = '';
    }
    if (noJobsMessage) {
        noJobsMessage.style.display = 'none';
    }
    
    jobs.forEach(job => {
        const jobCard = createJobCard(job);
        if (jobsList) {
            jobsList.appendChild(jobCard);
        }
    });
    
    setTimeout(() => cargarFavoritos(), 500);
}

function createJobCard(job) {
    console.log('Creando tarjeta para job:', job.id_oferta);
    
    const div = document.createElement('div');
    div.className = 'job-card';
    div.setAttribute('data-job-id', job.id_oferta);
    
    const isFavorite = favoritosCache.has(job.id_oferta);
    const heartClass = isFavorite ? 'fas' : 'far';
    const heartColor = isFavorite ? 'style="color: #e74c3c;"' : '';
    const activeClass = isFavorite ? 'active' : '';
    
    const tituloEscapado = (job.titulo || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
    
    div.innerHTML = `
        <div class="job-header">
            <div class="job-title">${job.titulo}</div>
            <div class="job-salary">$${Number(job.pago_ofrecido).toLocaleString()}/día</div>
        </div>
        <div class="job-details">
            ${job.descripcion}
        </div>
        <div class="job-location">
            <i class="fas fa-user"></i>
            ${job.nombre_agricultor} • Publicado: ${formatDate(job.fecha_publicacion)}
        </div>
        <div class="job-footer">
            <div class="job-tags">
                <span class="job-tag">${job.estado}</span>
            </div>
            <div class="job-actions">
                <button class="favorite-btn ${activeClass}" data-job-id="${job.id_oferta}" type="button">
                    <i class="${heartClass} fa-heart" ${heartColor}></i>
                </button>
                <button class="apply-btn" data-job-id="${job.id_oferta}" type="button">
                    <i class="fas fa-paper-plane"></i> Postularme
                </button>
            </div>
        </div>
    `;
    
    setTimeout(() => {
        const favoriteBtn = div.querySelector('.favorite-btn');
        const applyBtn = div.querySelector('.apply-btn');
        
        if (favoriteBtn) {
            favoriteBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const jobId = parseInt(this.getAttribute('data-job-id'));
                console.log('Click en favorito, ID:', jobId);
                
                if (!jobId || isNaN(jobId)) {
                    console.error('ID de trabajo inválido:', jobId);
                    showMessage('Error: ID de trabajo no válido', 'error');
                    return;
                }
                
                toggleFavorite(this, jobId);
            });
        }
        
        if (applyBtn) {
            applyBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const jobId = parseInt(this.getAttribute('data-job-id'));
                console.log('🎯 Click en Postularme - Job ID:', jobId);
                showApplyModal(jobId, job.titulo);
            });
        }
    }, 100);
    
    return div;
}

function showApplyModal(jobId, jobTitle) {
    console.log('📝 showApplyModal llamado con:', { jobId, jobTitle });
    selectedJobId = jobId;
    
    const jobDetails = document.getElementById('jobDetailsForApplication');
    if (jobDetails) {
        jobDetails.innerHTML = `<strong>Trabajo:</strong> ${jobTitle}`;
    }
    
    const modal = document.getElementById('applyJobModal');
    const overlay = document.getElementById('overlay');
    
    if (modal) {
        modal.style.display = 'flex';
        console.log('✅ Modal mostrado');
    } else {
        console.error('❌ No se encontró el modal applyJobModal');
    }
    
    if (overlay) {
        overlay.style.display = 'block';
    }
}

function closeApplyModal() {
    console.log('Cerrando modal de postulación');
    const modal = document.getElementById('applyJobModal');
    const overlay = document.getElementById('overlay');
    
    if (modal) modal.style.display = 'none';
    if (overlay) overlay.style.display = 'none';
    
    selectedJobId = null;
    
    const btnConfirm = document.getElementById('confirmApplyBtn');
    if (btnConfirm) {
        btnConfirm.innerHTML = '<i class="fas fa-paper-plane"></i> Confirmar Postulación';
        btnConfirm.disabled = false;
        btnConfirm.style.background = '';
    }
}

function confirmApplication() {
    console.log('🚀 confirmApplication llamado con selectedJobId:', selectedJobId);
    
    if (!selectedJobId) {
        console.error('❌ No hay selectedJobId');
        showToast('error', 'Error', 'No se ha seleccionado un trabajo');
        return;
    }
    
    const btnConfirm = document.getElementById('confirmApplyBtn');
    const originalText = btnConfirm.innerHTML;
    
    btnConfirm.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando...';
    btnConfirm.disabled = true;
    
    console.log('📤 Enviando petición a /api/apply_job con job_id:', selectedJobId);
    
    fetch('/api/apply_job', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
            job_id: selectedJobId
        })
    })
    .then(response => {
        console.log('📥 Respuesta recibida:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('📊 Datos de respuesta:', data);
        
        if (data.success) {
            btnConfirm.innerHTML = '<i class="fas fa-check"></i> ¡Enviado!';
            btnConfirm.style.background = 'linear-gradient(135deg, #22c55e, #16a34a)';
            
            showToast('success', '✅ Postulación enviada', 'Tu postulación ha sido enviada exitosamente');
            
            setTimeout(() => {
                closeApplyModal();
                loadAvailableJobs();
                loadStats();
                
                if (typeof loadPostulacionesFromServer === 'function') {
                    console.log('🔄 Recargando postulaciones...');
                    loadPostulacionesFromServer();
                }
            }, 1500);
            
        } else {
            throw new Error(data.message || 'Error desconocido');
        }
    })
    .catch(error => {
        console.error('❌ Error en confirmApplication:', error);
        showToast('error', 'Error', error.message || 'Error de conexión. Intenta de nuevo.');
        
        btnConfirm.innerHTML = originalText;
        btnConfirm.disabled = false;
        btnConfirm.style.background = '';
    });
}

function loadMyJobs() {
    fetch('/api/get_my_jobs')
    .then(response => response.json())
    .then(data => {
        if (data.success && data.jobs.length > 0) {
            displayMyJobs(data.jobs);
        } else {
            const noMyJobsMessage = document.getElementById('noMyJobsMessage');
            if (noMyJobsMessage) {
                noMyJobsMessage.style.display = 'block';
            }
        }
    })
    .catch(error => {
        console.error('Error al cargar mis trabajos:', error);
    });
}

function displayMyJobs(jobs) {
    const myJobsList = document.getElementById('myJobsList');
    const noMyJobsMessage = document.getElementById('noMyJobsMessage');
    
    if (!myJobsList) return;
    
    myJobsList.innerHTML = '';
    if (noMyJobsMessage) noMyJobsMessage.style.display = 'none';
    
    jobs.forEach(job => {
        const jobCard = createMyJobCard(job);
        myJobsList.appendChild(jobCard);
    });
}

function createMyJobCard(job) {
    const div = document.createElement('div');
    div.className = 'job-card my-job-card';
    
    let statusClass = '';
    let statusText = '';
    
    switch(job.estado) {
        case 'Pendiente':
            statusClass = 'status-pending';
            statusText = 'Pendiente';
            break;
        case 'Aceptada':
            statusClass = 'status-confirmed';
            statusText = 'Confirmado';
            break;
        case 'Rechazada':
            statusClass = 'status-rejected';
            statusText = 'Rechazado';
            break;
        case 'Favorito':
            statusClass = 'status-favorite';
            statusText = 'Favorito';
            break;
    }
    
    let descripcionCorta = job.descripcion;
    if (descripcionCorta && descripcionCorta.length > 150) {
        descripcionCorta = descripcionCorta.substring(0, 150) + '...';
    }
    
    div.innerHTML = `
        <div class="job-header">
            <div class="job-title">${job.titulo}</div>
            <div class="job-status ${statusClass}">${statusText}</div>
        </div>
        <div class="job-details">
            ${descripcionCorta}
        </div>
        <div class="job-location">
            <i class="fas fa-user"></i>
            ${job.nombre_agricultor} • Postulado: ${formatDate(job.fecha_postulacion)}
        </div>
    `;
    
    return div;
}

function loadStats() {
    fetch('/api/get_worker_stats', {
        credentials: 'include',
        headers: {
            'Cache-Control': 'no-cache'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const applicationsCount = document.getElementById('applicationsCount');
            const activeJobsCount = document.getElementById('activeJobsCount');
            const totalJobs = document.getElementById('totalJobs');
            const totalHours = document.getElementById('totalHours');
            
            if (applicationsCount) applicationsCount.textContent = data.applications || 0;
            if (activeJobsCount) activeJobsCount.textContent = data.active_jobs || 0;
            if (totalJobs) totalJobs.textContent = data.total_jobs || 0;
            if (totalHours) totalHours.textContent = (data.total_hours || 0) + 'h';
            
            console.log('✅ Estadísticas actualizadas:', data);
        }
    })
    .catch(error => {
        console.error('❌ Error al cargar estadísticas:', error);
    });
}

function showNoJobsMessage() {
    const jobsList = document.getElementById('jobsList');
    const noJobsMessage = document.getElementById('noJobsMessage');
    
    if (jobsList) jobsList.innerHTML = '';
    if (noJobsMessage) noJobsMessage.style.display = 'block';
}

function updateJobsCount(count) {
    const jobsNearCount = document.getElementById('jobsNearCount');
    if (jobsNearCount) jobsNearCount.textContent = count;
}

function formatDate(dateString) {
    if (!dateString) return 'Fecha no disponible';
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES');
}

// ===================================================================
// FUNCIONES DE FILTRADO Y BÚSQUEDA
// ===================================================================
function filterJobs(searchTerm) {
    const jobCards = document.querySelectorAll('#jobsList .job-card');
    const searchLower = searchTerm.toLowerCase();
    
    jobCards.forEach(card => {
        const title = card.querySelector('.job-title')?.textContent.toLowerCase() || '';
        const details = card.querySelector('.job-details')?.textContent.toLowerCase() || '';
        
        if (title.includes(searchLower) || details.includes(searchLower)) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}

function filterByType(button, type) {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    button.classList.add('active');
    
    if (type === 'todos') {
        loadAvailableJobs();
    } else {
        const jobCards = document.querySelectorAll('#jobsList .job-card');
        jobCards.forEach(card => {
            const title = card.querySelector('.job-title')?.textContent.toLowerCase() || '';
            const description = card.querySelector('.job-details')?.textContent.toLowerCase() || '';
            
            if (title.includes(type) || description.includes(type)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    }
}

function searchJobs() {
    const modal = document.getElementById('searchModal');
    const overlay = document.getElementById('overlay');
    
    if (modal) modal.style.display = 'flex';
    if (overlay) overlay.style.display = 'block';
}

function closeSearchModal() {
    const modal = document.getElementById('searchModal');
    const overlay = document.getElementById('overlay');
    
    if (modal) modal.style.display = 'none';
    if (overlay) overlay.style.display = 'none';
}

function clearSearchFilters() {
    const locationInput = document.getElementById('searchLocation');
    const cropTypeInput = document.getElementById('searchCropType');
    const minPayInput = document.getElementById('searchMinPay');
    const maxPayInput = document.getElementById('searchMaxPay');
    const availabilityInput = document.getElementById('searchAvailability');
    
    if (locationInput) locationInput.value = '';
    if (cropTypeInput) cropTypeInput.value = '';
    if (minPayInput) minPayInput.value = '';
    if (maxPayInput) maxPayInput.value = '';
    if (availabilityInput) availabilityInput.value = '';
}

function applySearchFilters() {
    const locationInput = document.getElementById('searchLocation');
    const cropTypeInput = document.getElementById('searchCropType');
    const minPayInput = document.getElementById('searchMinPay');
    const maxPayInput = document.getElementById('searchMaxPay');
    const availabilityInput = document.getElementById('searchAvailability');
    
    const filters = {
        location: locationInput ? locationInput.value : '',
        cropType: cropTypeInput ? cropTypeInput.value : '',
        minPay: minPayInput ? minPayInput.value : '',
        maxPay: maxPayInput ? maxPayInput.value : '',
        availability: availabilityInput ? availabilityInput.value : ''
    };
    
    console.log('Filtros aplicados:', filters);
    
    const jobCards = document.querySelectorAll('#jobsList .job-card');
    let visibleCount = 0;
    
    jobCards.forEach(card => {
        let shouldShow = true;
        
        const title = card.querySelector('.job-title')?.textContent.toLowerCase() || '';
        const description = card.querySelector('.job-details')?.textContent.toLowerCase() || '';
        const salaryText = card.querySelector('.job-salary')?.textContent || '';
        const salary = parseInt(salaryText.replace(/[^0-9]/g, ''));
        
        if (filters.location && !description.toLowerCase().includes(filters.location.toLowerCase())) {
            shouldShow = false;
        }
        
        if (filters.cropType && !title.includes(filters.cropType) && !description.includes(filters.cropType)) {
            shouldShow = false;
        }
        
        if (filters.minPay && salary < parseInt(filters.minPay)) {
            shouldShow = false;
        }
        
        if (filters.maxPay && salary > parseInt(filters.maxPay)) {
            shouldShow = false;
        }
        
        if (shouldShow) {
            card.style.display = 'block';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });
    
    if (visibleCount === 0) {
        showNoJobsMessage();
    } else {
        const noJobsMessage = document.getElementById('noJobsMessage');
        if (noJobsMessage) noJobsMessage.style.display = 'none';
    }
    
    updateJobsCount(visibleCount);
    closeSearchModal();
    
    showMessage(`Se encontraron ${visibleCount} trabajos con los filtros aplicados`, 'info');
}

// ===================================================================
// FUNCIONES DE MENÚ
// ===================================================================
function toggleProfileMenu() {
    console.log('Click en menú detectado');
    
    const dropdown = document.getElementById('dynamicProfileDropdown');
    
    if (!dropdown) {
        console.error('No se encontró dynamicProfileDropdown');
        return;
    }
    
    const isVisible = dropdown.style.display === 'block';
    
    if (isVisible) {
        dropdown.style.display = 'none';
        dropdown.style.opacity = '0';
        dropdown.style.transform = 'translateY(-10px)';
        dropdown.style.pointerEvents = 'none';
    } else {
        dropdown.style.display = 'block';
        dropdown.style.opacity = '1';
        dropdown.style.transform = 'translateY(0)';
        dropdown.style.pointerEvents = 'all';
        dropdown.style.transition = 'all 0.3s ease';
    }
}

document.addEventListener('click', function(event) {
    const profileMenu = document.querySelector('.profile-menu');
    const dropdown = document.getElementById('dynamicProfileDropdown');
    
    if (!profileMenu || !dropdown) return;
    
    if (!profileMenu.contains(event.target) && 
        !dropdown.contains(event.target) && 
        dropdown.style.display === 'block') {
        dropdown.style.display = 'none';
        dropdown.style.opacity = '0';
        dropdown.style.transform = 'translateY(-10px)';
        dropdown.style.pointerEvents = 'none';
    }
});

async function logout() {
    try {
        console.log('Cerrando sesión...');
        
        const response = await fetch('/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            },
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('Sesión cerrada correctamente');
            
            sessionStorage.clear();
            localStorage.removeItem('user_data');
            
            window.location.replace('/vista/login-trabajador.html?message=Sesión cerrada correctamente&type=success');
        } else {
            throw new Error(data.error || 'Error cerrando sesión');
        }
        
    } catch (error) {
        console.error('Error cerrando sesión:', error);
        window.location.replace('/vista/login-trabajador.html');
    }
}

function showProfile() {
    const dropdown = document.getElementById('dynamicProfileDropdown');
    if (dropdown) {
        dropdown.style.display = 'none';
        dropdown.style.opacity = '0';
        dropdown.style.transform = 'translateY(-10px)';
        dropdown.style.pointerEvents = 'none';
    }
    
    if (userData) {
        window.location.href = `perfil-trabajador.html?userId=${userData.user_id}&self=true`;
    } else {
        window.location.href = '/vista/perfil-trabajador.html';
    }
}

function showStats() {
    const dropdown = document.getElementById('dynamicProfileDropdown');
    if (dropdown) {
        dropdown.style.display = 'none';
        dropdown.style.opacity = '0';
        dropdown.style.transform = 'translateY(-10px)';
        dropdown.style.pointerEvents = 'none';
    }
    
    window.location.href = '/vista/estadisticas-trabajador.html';
}

function showSettings() {
    const dropdown = document.getElementById('dynamicProfileDropdown');
    if (dropdown) {
        dropdown.style.display = 'none';
        dropdown.style.opacity = '0';
        dropdown.style.transform = 'translateY(-10px)';
        dropdown.style.pointerEvents = 'none';
    }
    
    window.location.href = '/vista/configuracion-trabajador.html';
}

function showHistorialEmpleos() {
    window.location.href = '/vista/historial-empleos.html';
}

function showPostulaciones() {
    window.location.href = '/vista/postulaciones.html';
}

function showFavoritos() {
    const dropdown = document.getElementById('dynamicProfileDropdown');
    if (dropdown) {
        dropdown.style.display = 'none';
        dropdown.style.opacity = '0';
        dropdown.style.transform = 'translateY(-10px)';
        dropdown.style.pointerEvents = 'none';
    }
    window.location.href = '/vista/favoritos.html';
}

function showHelpSupport() {
    window.location.href = '/vista/soporte-trabajador.html';
    toggleProfileMenu();
}

// ===================================================================
// FUNCIONES DE NOTIFICACIONES
// ===================================================================
function showToast(tipo, titulo, mensaje) {
    const toastAnterior = document.querySelector('.toast');
    if (toastAnterior) {
        toastAnterior.remove();
    }
    
    const toast = document.createElement('div');
    toast.className = `toast ${tipo}`;
    
    const iconos = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-triangle',
        info: 'fa-info-circle',
        warning: 'fa-exclamation-circle'
    };
    
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="fas ${iconos[tipo]}"></i>
        </div>
        <div class="toast-content">
            <div class="toast-title">${titulo}</div>
            <div class="toast-message">${mensaje}</div>
        </div>
    `;
    
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: white;
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        padding: 20px 24px;
        display: flex;
        align-items: center;
        gap: 12px;
        z-index: 10001;
        transform: translateX(400px);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        border-left: 5px solid ${tipo === 'success' ? '#22c55e' : tipo === 'error' ? '#ef4444' : '#4a7c59'};
        max-width: 400px;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => toast.style.transform = 'translateX(0)', 100);
    
    setTimeout(() => {
        toast.style.transform = 'translateX(400px)';
        setTimeout(() => {
            if (document.body.contains(toast)) {
                document.body.removeChild(toast);
            }
        }, 400);
    }, 4000);
}

function showMessage(message, type = 'info') {
    const colors = {
        success: '#22c55e',
        error: '#ef4444',
        info: '#3b82f6',
        warning: '#f59e0b'
    };
    
    const msgDiv = document.createElement('div');
    msgDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${colors[type]};
        color: white;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 100000;
        font-weight: 600;
        animation: slideIn 0.3s ease;
    `;
    msgDiv.textContent = message;
    
    document.body.appendChild(msgDiv);
    
    setTimeout(() => {
        msgDiv.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => msgDiv.remove(), 300);
    }, 3000);
}

function showNotifications() {
    // Abrir un pequeño panel flotante junto a la campana
    const existente = document.getElementById('notifDropdown');
    if (existente) { existente.remove(); return; }

    const bell = document.querySelector('.notification-icon');
    const rect  = bell ? bell.getBoundingClientRect() : { bottom: 80, right: 40 };

    const panel = document.createElement('div');
    panel.id = 'notifDropdown';
    panel.style.cssText = `
        position: fixed;
        top:  ${rect.bottom + 10}px;
        right: ${window.innerWidth - rect.right}px;
        width: 320px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--r-xl);
        box-shadow: var(--s4);
        z-index: 10002;
        overflow: hidden;
        animation: modalIn .25s var(--bounce);
    `;

    // Rellena con las notificaciones ya cargadas o con el contenido del sidebar
    const srcHtml = document.getElementById('notificationsList')?.innerHTML || '';
    panel.innerHTML = `
        <div style="
            background: linear-gradient(135deg, var(--g800), var(--g500));
            padding: 14px 18px;
            display: flex; align-items: center; justify-content: space-between;
        ">
            <span style="color:#fff; font-family:var(--ff-display); font-size:.92rem; font-weight:600;">
                <i class="fas fa-bell" style="margin-right:8px;"></i>Notificaciones
            </span>
            <button onclick="document.getElementById('notifDropdown')?.remove()"
                style="background:rgba(255,255,255,.15); border:none; color:#fff;
                       width:26px; height:26px; border-radius:6px; cursor:pointer;
                       font-size:11px; display:flex; align-items:center; justify-content:center;">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div style="max-height:340px; overflow-y:auto; padding:8px;">
            ${srcHtml || `<p style="text-align:center;padding:24px;color:var(--n400);font-size:.80rem;">Sin notificaciones nuevas</p>`}
        </div>
    `;

    document.body.appendChild(panel);

    // Cierra al hacer clic fuera
    setTimeout(() => {
        document.addEventListener('click', function handler(e) {
            if (!panel.contains(e.target) && !bell?.contains(e.target)) {
                panel.remove();
                document.removeEventListener('click', handler);
            }
        });
    }, 50);
}

function handleNotification(element) {
    element.style.opacity = '0.7';
    element.style.transform = 'translateX(10px)';
    
    setTimeout(() => {
        element.style.opacity = '1';
        element.style.transform = 'translateX(0)';
        
        const title = element.querySelector('.notification-title')?.textContent || '';
        if (title.includes('Nuevo trabajo')) {
            showMessage('Nuevo trabajo encontrado cerca de ti', 'success');
        } else {
            showMessage('Recordatorio guardado', 'info');
        }
    }, 200);
}

// ===================================================================
// FUNCIONES DEL MAPA CON GEOLOCALIZACIÓN
// ===================================================================
function initMap() {
    console.log('🗺️ Inicializando mapa...');
    
    const mapElement = document.getElementById("map");
    if (!mapElement) {
        console.error('❌ Elemento del mapa no encontrado');
        return;
    }
    
    try {
        const defaultLocation = [4.7110, -74.0721];
        
        map = L.map('map').setView(defaultLocation, 12);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 18,
        }).addTo(map);
        
        cargarUbicacionGuardadaTrabajador();
        
        console.log('✅ Mapa inicializado correctamente');
        
    } catch (error) {
        console.error('❌ Error inicializando el mapa:', error);
        handleMapError();
    }
}

async function cargarUbicacionGuardadaTrabajador() {
    try {
        console.log('📍 Cargando ubicación guardada...');
        
        const response = await fetch('/api/get_user_location', {
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success && data.location && !data.is_default) {
            const { lat, lng } = data.location;
            
            console.log(`✅ Ubicación guardada: ${lat}, ${lng}`);
            
            currentUserLocation = { lat, lng };
            
            if (map) {
                map.setView([lat, lng], 13);
                agregarMarcadorUsuario(lat, lng);
            }
            
            cargarOfertasCercanas(lat, lng);
            
        } else {
            console.log('📍 Solicitando ubicación actual...');
            obtenerUbicacionSilenciosa();
        }
        
    } catch (error) {
        console.error('❌ Error:', error);
        obtenerUbicacionSilenciosa();
    }
}

function obtenerUbicacionSilenciosa() {
    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const userLat = position.coords.latitude;
                const userLon = position.coords.longitude;
                
                console.log(`✅ Ubicación obtenida: ${userLat}, ${userLon}`);
                
                currentUserLocation = { lat: userLat, lng: userLon };
                
                if (map) {
                    map.setView([userLat, userLon], 13);
                    agregarMarcadorUsuario(userLat, userLon);
                }
                
                cargarOfertasCercanas(userLat, userLon);
                guardarUbicacionTrabajador(userLat, userLon);
            },
            (error) => {
                console.warn('⚠️ No se pudo obtener ubicación:', error.message);
                usarUbicacionPorDefecto();
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 60000
            }
        );
    } else {
        usarUbicacionPorDefecto();
    }
}

function usarUbicacionPorDefecto() {
    console.log('📍 Usando ubicación por defecto');
    
    const defaultLat = 4.7110;
    const defaultLng = -74.0721;
    
    currentUserLocation = { lat: defaultLat, lng: defaultLng };
    
    if (map) {
        map.setView([defaultLat, defaultLng], 12);
        agregarMarcadorUsuario(defaultLat, defaultLng);
    }
    
    cargarOfertasCercanas(defaultLat, defaultLng, 100);
}

function agregarMarcadorUsuario(lat, lng) {
    try {
        console.log('🧭 agregarMarcadorUsuario llamado con:', lat, lng);

        if (!map) {
            console.warn('⚠️ map no está inicializado todavía. Se pospone agregar marcador.');
            return;
        }

        try {
            if (userMarker && map.hasLayer(userMarker)) {
                map.removeLayer(userMarker);
            }
        } catch (err) {
            console.warn('Error removiendo userMarker previo:', err);
        }

        const userIcon = L.divIcon({
            className: 'user-location-marker',
            html: `<div style="
                width: 34px; 
                height: 34px; 
                background: #dc2626; 
                border: 4px solid white; 
                border-radius: 50%; 
                box-shadow: 0 6px 12px rgba(0,0,0,0.25);
                display:flex; align-items:center; justify-content:center;
            ">
                <i class="fas fa-user" style="color: white; font-size: 14px;"></i>
            </div>`,
            iconSize: [34, 34],
            iconAnchor: [17, 17]
        });

        userMarker = L.marker([lat, lng], {
            icon: userIcon,
            zIndexOffset: 2000,
            riseOnHover: true
        }).addTo(map);

        userMarker.bindPopup(`
            <div style="text-align:center; padding:6px;">
                <strong style="color:#dc2626">📍 Tú</strong><br>
                <small>${lat.toFixed(6)}, ${lng.toFixed(6)}</small>
            </div>
        `);

        try { 
            if (userMarker.bringToFront) userMarker.bringToFront();
        } catch(e) { /* no crítico */ }

        console.log('✅ Marcador de usuario añadido al mapa');
    } catch (error) {
        console.error('❌ Error en agregarMarcadorUsuario:', error);
    }
}

async function cargarOfertasCercanas(lat, lng, radius = 50) {
    console.log(`🔍 Buscando ofertas en radio de ${radius}km...`);
    
    try {
        const response = await fetch('/api/get_nearby_jobs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                latitude: lat,
                longitude: lng,
                radius: radius
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log(`✅ ${data.total} ofertas encontradas`);
            
            limpiarMarcadoresTrabajos();
            
            data.ofertas.forEach(oferta => {
                agregarMarcadorOferta(oferta);
            });
            
            const jobsNearCount = document.getElementById('jobsNearCount');
            if (jobsNearCount) {
                jobsNearCount.textContent = data.total;
            }
            
            if (data.total === 0) {
                showMessage('No hay ofertas de trabajo cerca de ti', 'info');
            }
            
        } else {
            console.error('❌ Error en respuesta:', data.error);
            showMessage('Error al cargar ofertas cercanas', 'error');
        }
        
    } catch (error) {
        console.error('❌ Error cargando ofertas:', error);
        showMessage('Error de conexión al cargar ofertas', 'error');
    }
}

function agregarMarcadorOferta(oferta) {
    const jobIcon = L.divIcon({
        className: 'job-marker',
        html: `<div style="
            background: #4a7c59; 
            width: 35px; 
            height: 35px; 
            border-radius: 50%; 
            border: 3px solid white; 
            box-shadow: 0 3px 6px rgba(0,0,0,0.3); 
            display: flex; 
            align-items: center; 
            justify-content: center;
            cursor: pointer;
            transition: transform 0.2s;
        " onmouseover="this.style.transform='scale(1.2)'" onmouseout="this.style.transform='scale(1)'">
            <i class="fas fa-briefcase" style="color: white; font-size: 16px;"></i>
        </div>`,
        iconSize: [35, 35],
        iconAnchor: [17, 17]
    });
    
    const marker = L.marker([oferta.lat, oferta.lng], { icon: jobIcon }).addTo(map);
    
    const popupContent = `
        <div style="min-width: 250px; padding: 12px; font-family: 'Segoe UI', sans-serif;">
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <i class="fas fa-briefcase" style="color: #4a7c59; font-size: 20px; margin-right: 10px;"></i>
                <h4 style="margin: 0; color: #1e3a2e; font-size: 16px; font-weight: 600;">
                    ${oferta.titulo}
                </h4>
            </div>
            
            <div style="margin: 8px 0; padding: 8px; background: #f0f9ff; border-left: 3px solid #4a7c59; border-radius: 4px;">
                <div style="display: flex; align-items: center; margin-bottom: 6px;">
                    <i class="fas fa-dollar-sign" style="color: #16a34a; margin-right: 8px; width: 16px;"></i>
                    <strong style="color: #16a34a; font-size: 15px;">
                        ${oferta.pago.toLocaleString()} COP/día
                    </strong>
                </div>
                
                <div style="display: flex; align-items: center; margin-bottom: 6px;">
                    <i class="fas fa-user" style="color: #4a7c59; margin-right: 8px; width: 16px;"></i>
                    <span style="font-size: 13px; color: #374151;">${oferta.agricultor}</span>
                </div>
                
                <div style="display: flex; align-items: center; margin-bottom: 6px;">
                    <i class="fas fa-map-marker-alt" style="color: #dc2626; margin-right: 8px; width: 16px;"></i>
                    <span style="font-size: 13px; color: #374151;">
                        ${oferta.ubicacion} • <strong>${oferta.distancia} km</strong>
                    </span>
                </div>
            </div>
            
            <p style="margin: 10px 0; font-size: 13px; color: #4b5563; line-height: 1.4;">
                ${oferta.descripcion}
            </p>
            
            <button 
                onclick="postularseDesdeMapaTrabajador(${oferta.id}, '${oferta.titulo.replace(/'/g, "\\'")}')"
                style="
                    width: 100%;
                    background: linear-gradient(135deg, #4a7c59, #1e3a2e);
                    color: white;
                    border: none;
                    padding: 10px 16px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 600;
                    margin-top: 10px;
                    transition: all 0.3s;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                "
                onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 8px rgba(0,0,0,0.3)';"
                onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.2)';"
            >
                <i class="fas fa-paper-plane"></i> Postularme Ahora
            </button>
        </div>
    `;
    
    marker.bindPopup(popupContent, {
        maxWidth: 300,
        className: 'custom-popup'
    });
    
    jobMarkers.push(marker);
}

function limpiarMarcadoresTrabajos() {
    jobMarkers.forEach(marker => {
        map.removeLayer(marker);
    });
    jobMarkers = [];
}

window.postularseDesdeMapaTrabajador = function(jobId, jobTitle) {
    console.log(`📝 Postulándose a: ${jobTitle} (ID: ${jobId})`);
    
    map.closePopup();
    
    if (confirm(`¿Deseas postularte a "${jobTitle}"?`)) {
        fetch('/api/apply_job', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ job_id: jobId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('success', '¡Éxito!', 'Tu postulación fue enviada correctamente');
                
                if (currentUserLocation) {
                    cargarOfertasCercanas(currentUserLocation.lat, currentUserLocation.lng);
                }
            } else {
                showToast('error', 'Error', data.message || 'No se pudo enviar la postulación');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('error', 'Error', 'Error de conexión');
        });
    }
};

function agregarBotonRecargarUbicacion() {
    const control = L.control({ position: 'topright' });
    
    control.onAdd = function() {
        const div = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
        div.innerHTML = `
            <a href="#" title="Actualizar ubicación" style="
                background: white;
                width: 34px;
                height: 34px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
                color: #4a7c59;
                text-decoration: none;
            ">
                <i class="fas fa-crosshairs"></i>
            </a>
        `;
        
        div.onclick = function(e) {
            e.preventDefault();
            obtenerUbicacionSilenciosa();
        };
        
        return div;
    };
    
    control.addTo(map);
}

async function guardarUbicacionTrabajador(lat, lng) {
    try {
        await fetch('/api/save_user_location', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                latitude: lat,
                longitude: lng
            })
        });
        console.log('✅ Ubicación guardada');
    } catch (error) {
        console.error('❌ Error guardando ubicación:', error);
    }
}

function handleMapError() {
    console.error('Error cargando el mapa');
    const mapElement = document.getElementById("map");
    if (mapElement) {
        mapElement.innerHTML = `
            <div style="
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100%;
                background: linear-gradient(135deg, rgba(144, 238, 144, 0.2), rgba(74, 124, 89, 0.1));
                border-radius: 15px;
                color: #1e3a2e;
                text-align: center;
                padding: 20px;
            ">
                <div>
                    <div style="font-size: 48px; margin-bottom: 15px; color: #4a7c59;">
                        <i class="fas fa-map-marked-alt"></i>
                    </div>
                    <strong style="font-size: 16px; color: #1e3a2e;">Mapa no disponible</strong><br>
                    <small style="color: #4a7c59; font-size: 14px; display: block; margin-top: 5px;">
                        8 trabajos en 10km de radio
                    </small>
                </div>
            </div>
        `;
    }
}

// ===================================================================
// SISTEMA DE CALIFICACIONES Y NOTIFICACIONES
// ===================================================================
async function loadUserRating() {
    try {
        const response = await fetch(`/api/get_user_rating/${userData.user_id}`, {
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success) {
            const ratingContainer = document.querySelector('.rating');
            if (ratingContainer) {
                const starsHTML = generateStarsHTML(data.promedio);
                ratingContainer.innerHTML = `
                    ${starsHTML}
                    <span class="rating-value">${data.promedio.toFixed(1)}</span>
                    <span class="rating-count">(${data.total_calificaciones})</span>
                `;
            }
        }
    } catch (error) {
        console.error('Error cargando calificación:', error);
    }
}

function generateStarsHTML(rating) {
    let starsHTML = '';
    const fullStars = Math.floor(rating);
    const hasHalfStar = (rating % 1) >= 0.5;
    
    for (let i = 0; i < fullStars; i++) {
        starsHTML += '<i class="fas fa-star"></i>';
    }
    
    if (hasHalfStar) {
        starsHTML += '<i class="fas fa-star-half-alt"></i>';
    }
    
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
    for (let i = 0; i < emptyStars; i++) {
        starsHTML += '<i class="far fa-star"></i>';
    }
    
    return starsHTML;
}

async function loadNotifications() {
    try {
        const response = await fetch('/api/get_notifications', {
            credentials: 'include'
        });
        
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
    const badge = document.querySelector('.notification-badge');
    if (badge) {
        if (count > 0) {
            badge.textContent = count > 9 ? '9+' : count;
            badge.style.display = 'block';
        } else {
            badge.style.display = 'none';
        }
    }
}

function displayNotifications(notificaciones) {
    const container = document.getElementById('notificationsList');
    if (!container) return;
    
    if (notificaciones.length === 0) {
        container.innerHTML = `
            <div class="notification-item" style="text-align: center; padding: 30px 15px; color: #6c757d;">
                <i class="fas fa-bell-slash" style="font-size: 32px; margin-bottom: 10px; display: block;"></i>
                <p>No tienes notificaciones</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    
    notificaciones.slice(0, 5).forEach(notif => {
        const fechaFormateada = formatearTiempoTranscurrido(notif.fecha);
        
        html += `
            <div class="notification-item ${notif.leida ? '' : 'unread'}" 
                 onclick="handleNotificationClick('${notif.id}', '${notif.link || ''}')">
                <div class="notification-icon" style="background: ${notif.color}20;">
                    <i class="fas ${notif.icono}" style="color: ${notif.color};"></i>
                </div>
                <div class="notification-content">
                    <div class="notification-title">${notif.titulo}</div>
                    <div class="notification-message">${notif.mensaje}</div>
                    <div class="notification-time">${fechaFormateada}</div>
                </div>
            </div>
        `;
    });
    
    if (notificaciones.length > 5) {
        html += `
            <div class="notification-item" style="text-align: center; padding: 12px; border-top: 2px solid #e9ecef;">
                <a href="/vista/notificaciones.html" style="color: #4a7c59; font-weight: 600; text-decoration: none;">
                    Ver todas las notificaciones (${notificaciones.length})
                </a>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

function handleNotificationClick(notifId, link) {
    fetch('/api/mark_notification_read', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({ notification_id: notifId })
    });
    
    if (link && link !== '' && link !== 'undefined') {
        window.location.href = link;
    }
}

function formatearTiempoTranscurrido(fechaISO) {
    if (!fechaISO) return 'Hace un momento';
    
    const fecha = new Date(fechaISO);
    const ahora = new Date();
    const diff = Math.floor((ahora - fecha) / 1000);
    
    if (diff < 60) return 'Hace un momento';
    if (diff < 3600) return `Hace ${Math.floor(diff / 60)} minutos`;
    if (diff < 86400) return `Hace ${Math.floor(diff / 3600)} horas`;
    if (diff < 604800) return `Hace ${Math.floor(diff / 86400)} días`;
    
    return fecha.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
}

// ===================================================================
// FUNCIONES GLOBALES PARA WINDOW
// ===================================================================
window.initMap = initMap;
window.handleMapError = handleMapError;
window.toggleFavorite = toggleFavorite;
window.showApplyModal = showApplyModal;
window.closeApplyModal = closeApplyModal;
window.confirmApplication = confirmApplication;
window.searchJobs = searchJobs;
window.closeSearchModal = closeSearchModal;
window.clearSearchFilters = clearSearchFilters;
window.applySearchFilters = applySearchFilters;
window.filterJobs = filterJobs;
window.filterByType = filterByType;
window.toggleProfileMenu = toggleProfileMenu;
window.logout = logout;
window.showProfile = showProfile;
window.showStats = showStats;
window.showSettings = showSettings;
window.showHistorialEmpleos = showHistorialEmpleos;
window.showPostulaciones = showPostulaciones;
window.showFavoritos = showFavoritos;
window.showNotifications = showNotifications;
window.handleNotification = handleNotification;
window.showHelpSupport = showHelpSupport;

// ===================================================================
// INICIALIZACIÓN
// ===================================================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('🌱 Inicializando dashboard de trabajador...');
    
    verificarSesionActiva();
    loadUserData();
    loadAvailableJobs();
    loadMyJobs();
    loadStats();
    
    setTimeout(() => cargarFavoritos(), 1000);
    
    setTimeout(() => {
        initMap();
        if (map) {
            agregarBotonRecargarUbicacion();
        }
    }, 500);
    
    setTimeout(() => {
        const jobCards = document.querySelectorAll('.job-card');
        jobCards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(30px)';
            
            setTimeout(() => {
                card.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 150);
        });
    }, 2000);

    const quickStats = document.querySelectorAll('.quick-stat');
    quickStats.forEach((stat) => {
        const number = stat.querySelector('.quick-stat-number');
        if (number) {
            const finalNumber = parseInt(number.textContent);
            
            let currentNumber = 0;
            const increment = finalNumber / 30;
            const counter = setInterval(() => {
                currentNumber += increment;
                if (currentNumber >= finalNumber) {
                    number.textContent = finalNumber;
                    clearInterval(counter);
                } else {
                    number.textContent = Math.floor(currentNumber);
                }
            }, 50);
        }
    });

    setInterval(async () => {
        try {
            const response = await fetch('/check_session');
            const data = await response.json();
            
            if (!data.authenticated) {
                console.log('Sesión expirada, redirigiendo al login');
                window.location.href = '/vista/login-trabajador.html';
            }
        } catch (error) {
            console.error('Error verificando sesión:', error);
        }
    }, 5 * 60 * 1000);
    
    setTimeout(() => {
        if (userData && userData.user_id) {
            loadUserRating();
            loadNotifications();
            setInterval(loadNotifications, 120000);
        }
    }, 2000);
});

document.addEventListener('keydown', function(e) {
    if (e.ctrlKey || e.metaKey) {
        switch(e.key) {
            case 'f':
                e.preventDefault();
                const searchBar = document.querySelector('.search-bar');
                if (searchBar) searchBar.focus();
                break;
            case 'n':
                e.preventDefault();
                showNotifications();
                break;
            case 'm':
                e.preventDefault();
                const mapElement = document.getElementById('map');
                if (mapElement) mapElement.scrollIntoView({ behavior: 'smooth' });
                break;
            case 'h':
                e.preventDefault();
                showHistorialEmpleos();
                break;
            case 'p':
                e.preventDefault();
                showPostulaciones();
                break;
        }
    }
});

const styleNotif = document.createElement('style');
styleNotif.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to   { transform: translateX(0);    opacity: 1; }
    }
    
    @keyframes slideOutRight {
        from { transform: translateX(0);    opacity: 1; }
        to   { transform: translateX(100%); opacity: 0; }
    }
    
    .notification-item {
        padding: 15px;
        border-bottom: 1px solid #e9ecef;
        display: flex;
        gap: 12px;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .notification-item:hover { background: #f8f9fa; }
    
    .notification-item.unread { background: #e7f5ff; }
    
    .notification-icon {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    
    .notification-content { flex: 1; }
    
    .notification-title {
        font-weight: 700;
        color: #1e3a2e;
        margin-bottom: 4px;
        font-size: 14px;
    }
    
    .notification-message {
        color: #495057;
        font-size: 13px;
        line-height: 1.4;
        margin-bottom: 4px;
    }
    
    .notification-time {
        color: #6c757d;
        font-size: 11px;
    }
    
    .rating {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 5px;
        margin: 15px 0;
    }
    
    .rating i { color: #ffc107; font-size: 16px; }
    
    .rating-value { font-weight: 700; color: #1e3a2e; margin-left: 5px; }
    
    .rating-count { color: #6c757d; font-size: 12px; }
`;

document.head.appendChild(styleNotif);

// ===================================================================
// PAGINACIÓN Y NAVEGACIÓN A RECOMENDACIONES
// (anteriormente inline en index-trabajador.html)
// ===================================================================

/* ── Redirigir a la página de recomendaciones ── */
function showRecomendaciones() {
    window.location.href = '/vista/recomendaciones.html';
}

/** Número de página actual (empieza en 1) */
let currentPageNum = 1;

/** Cuántas tarjetas mostrar por página */
const jobsPerPage = 3;

/** Copia de todos los trabajos cargados (para paginar sin refetch) */
let allJobsData = [];

/**
 * Avanza o retrocede una página y actualiza la vista.
 * @param {'prev'|'next'} direction
 */
function changePage(direction) {
    const totalPages = Math.ceil(allJobsData.length / jobsPerPage);

    if (direction === 'prev' && currentPageNum > 1) {
        currentPageNum--;
    } else if (direction === 'next' && currentPageNum < totalPages) {
        currentPageNum++;
    }

    displayJobsPage();
}

/**
 * Renderiza las tarjetas correspondientes a la página actual.
 */
function displayJobsPage() {
    const startIndex = (currentPageNum - 1) * jobsPerPage;
    const endIndex   = startIndex + jobsPerPage;
    const jobsToShow = allJobsData.slice(startIndex, endIndex);

    const jobsList = document.getElementById('jobsList');
    if (jobsList) {
        jobsList.innerHTML = '';
        jobsToShow.forEach(job => {
            jobsList.appendChild(createJobCard(job));
        });
    }

    setTimeout(() => cargarFavoritos(), 500);
    updatePaginationUI();
}

/**
 * Actualiza los controles de paginación.
 * Oculta el componente si solo hay una página.
 */
function updatePaginationUI() {
    const totalPages    = Math.ceil(allJobsData.length / jobsPerPage);
    const container     = document.getElementById('paginationContainer');
    const currentPageEl = document.getElementById('currentPage');
    const totalPagesEl  = document.getElementById('totalPages');
    const prevBtn       = document.getElementById('prevPageBtn');
    const nextBtn       = document.getElementById('nextPageBtn');

    if (totalPages <= 1) {
        if (container) container.style.display = 'none';
        return;
    }

    if (container)     container.style.display  = 'flex';
    if (currentPageEl) currentPageEl.textContent = currentPageNum;
    if (totalPagesEl)  totalPagesEl.textContent  = totalPages;

    if (prevBtn) {
        prevBtn.disabled      = currentPageNum === 1;
        prevBtn.style.opacity = currentPageNum === 1 ? '0.5' : '1';
    }

    if (nextBtn) {
        nextBtn.disabled      = currentPageNum === totalPages;
        nextBtn.style.opacity = currentPageNum === totalPages ? '0.5' : '1';
    }
}

/**
 * Sobreescribe displayJobs() para aplicar paginación.
 * @param {Array} jobs
 */
window.displayJobs = function(jobs) {
    allJobsData    = jobs;
    currentPageNum = 1;

    const noJobsMessage  = document.getElementById('noJobsMessage');
    const paginationCont = document.getElementById('paginationContainer');

    if (jobs.length === 0) {
        if (typeof showNoJobsMessage === 'function') showNoJobsMessage();
        if (paginationCont) paginationCont.style.display = 'none';
        return;
    }

    if (noJobsMessage) noJobsMessage.style.display = 'none';
    displayJobsPage();
};

console.log('✅ JavaScript del trabajador cargado correctamente');