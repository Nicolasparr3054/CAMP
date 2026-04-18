// estadisticas-trabajador.js - VERSIÓN CORREGIDA

let estadisticasData = {};
let charts = {};

// Inicializar
document.addEventListener('DOMContentLoaded', function() {
    console.log('🌱 Iniciando Estadísticas Trabajador...');
    cargarEstadisticas();
    configurarFiltros();
});

function volverAlIndex() {
    window.location.href = '/vista/index-trabajador.html';
}

// Cargar estadísticas desde el servidor
async function cargarEstadisticas(periodo = 'all') {
    try {
        mostrarLoading();
        
        console.log('📊 Cargando estadísticas del servidor...');
        const response = await fetch(`/api/estadisticas_trabajador?periodo=${periodo}`, {
            credentials: 'include'
        });
        
        console.log('📡 Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        console.log('📦 Datos recibidos:', data);
        
        if (data.success) {
            estadisticasData = data.estadisticas;
            console.log('✅ Estadísticas cargadas correctamente:', estadisticasData);
            actualizarUI();
        } else {
            throw new Error(data.message || 'Error al cargar datos');
        }
    } catch (error) {
        console.error('❌ Error cargando estadísticas:', error);
        // Mostrar mensaje de error al usuario
        mostrarMensajeError('No se pudieron cargar las estadísticas. Por favor, intenta de nuevo.');
    }
}

// Actualizar toda la UI
function actualizarUI() {
    console.log('🎨 Actualizando interfaz...');
    actualizarResumen();
    crearGraficas();
    actualizarTrabajosRecientes();
    actualizarHabilidades();
}

// Actualizar resumen
function actualizarResumen() {
    const { resumen } = estadisticasData;
    
    if (!resumen) {
        console.error('❌ No hay datos de resumen');
        return;
    }
    
    console.log('📊 Resumen:', resumen);
    
    document.getElementById('totalTrabajos').textContent = resumen.totalTrabajos || 0;
    document.getElementById('totalHoras').textContent = (resumen.totalHoras || 0) + 'h';
    document.getElementById('totalIngresos').textContent = formatCurrency(resumen.totalIngresos || 0);
    document.getElementById('calificacionPromedio').textContent = (resumen.calificacionPromedio || 0).toFixed(1) + '/5';
}

// Crear todas las gráficas
function crearGraficas() {
    crearGraficaIngresosMensuales();
    crearGraficaTrabajosPorTipo();
    crearGraficaHorasMensuales();
    crearGraficaEvolucionCalificaciones();
}

// Gráfica de ingresos mensuales
function crearGraficaIngresosMensuales() {
    const ctx = document.getElementById('ingresosMensuales');
    if (!ctx) return;
    
    const data = estadisticasData.ingresosMensuales || [];
    console.log('📈 Ingresos mensuales:', data);
    
    if (charts.ingresosMensuales) charts.ingresosMensuales.destroy();
    
    // Si no hay datos, mostrar gráfica vacía
    if (data.length === 0) {
        data.push({ mes: 'Sin datos', ingresos: 0 });
    }
    
    charts.ingresosMensuales = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(item => item.mes),
            datasets: [{
                label: 'Ingresos ($)',
                data: data.map(item => item.ingresos),
                backgroundColor: 'rgba(144, 238, 144, 0.2)',
                borderColor: 'rgba(74, 124, 89, 1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: 'rgba(30, 58, 46, 1)',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: value => '$' + (value / 1000).toFixed(0) + 'k'
                    }
                }
            }
        }
    });
}

// Gráfica de trabajos por tipo
function crearGraficaTrabajosPorTipo() {
    const ctx = document.getElementById('trabajosPorTipo');
    if (!ctx) return;
    
    const data = estadisticasData.trabajosPorTipo || [];
    console.log('📊 Trabajos por tipo:', data);
    
    if (charts.trabajosPorTipo) charts.trabajosPorTipo.destroy();
    
    // Si no hay datos
    if (data.length === 0) {
        data.push({ tipo: 'Sin datos', cantidad: 0 });
    }
    
    charts.trabajosPorTipo = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(item => item.tipo),
            datasets: [{
                data: data.map(item => item.cantidad),
                backgroundColor: [
                    'rgba(144, 238, 144, 0.8)',
                    'rgba(102, 187, 106, 0.8)',
                    'rgba(74, 124, 89, 0.8)',
                    'rgba(56, 142, 60, 0.8)',
                    'rgba(30, 58, 46, 0.8)'
                ],
                borderColor: '#fff',
                borderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: { size: 13, weight: '600' }
                    }
                }
            }
        }
    });
}

// Gráfica de horas mensuales
function crearGraficaHorasMensuales() {
    const ctx = document.getElementById('horasMensuales');
    if (!ctx) return;
    
    const data = estadisticasData.horasMensuales || [];
    console.log('⏰ Horas mensuales:', data);
    
    if (charts.horasMensuales) charts.horasMensuales.destroy();
    
    if (data.length === 0) {
        data.push({ mes: 'Sin datos', horas: 0 });
    }
    
    charts.horasMensuales = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.mes),
            datasets: [{
                label: 'Horas',
                data: data.map(item => item.horas),
                backgroundColor: 'rgba(74, 124, 89, 0.8)',
                borderColor: 'rgba(30, 58, 46, 1)',
                borderWidth: 2,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: value => value + 'h'
                    }
                }
            }
        }
    });
}

// Gráfica de evolución de calificaciones
function crearGraficaEvolucionCalificaciones() {
    const ctx = document.getElementById('evolucionCalificaciones');
    if (!ctx) return;
    
    const data = estadisticasData.calificacionesPorMes || [];
    console.log('⭐ Calificaciones:', data);
    
    if (charts.evolucionCalificaciones) charts.evolucionCalificaciones.destroy();
    
    if (data.length === 0) {
        data.push({ mes: 'Sin datos', calificacion: 0 });
    }
    
    charts.evolucionCalificaciones = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(item => item.mes),
            datasets: [{
                label: 'Calificación',
                data: data.map(item => item.calificacion),
                backgroundColor: 'rgba(255, 193, 7, 0.2)',
                borderColor: 'rgba(255, 152, 0, 1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: 'rgba(255, 152, 0, 1)',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    min: 0,
                    max: 5,
                    ticks: {
                        callback: value => value.toFixed(1) + '/5'
                    }
                }
            }
        }
    });
}

// Actualizar trabajos recientes
function actualizarTrabajosRecientes() {
    const container = document.getElementById('trabajosRecientes');
    if (!container) return;
    
    const trabajos = estadisticasData.trabajosRecientes || [];
    console.log('📋 Trabajos recientes:', trabajos);
    
    if (trabajos.length === 0) {
        container.innerHTML = '<div class="empty-state"><i class="fas fa-inbox"></i><p>No hay trabajos finalizados aún</p></div>';
        return;
    }
    
    container.innerHTML = trabajos.map(trabajo => `
        <div class="trabajo-item">
            <div class="trabajo-titulo">${trabajo.titulo}</div>
            <div class="trabajo-info">
                <span>👨‍🌾 ${trabajo.agricultor}</span>
                <span>💰 ${formatCurrency(trabajo.pago)}</span>
                <span>⭐ ${trabajo.calificacion || 'Sin calificar'}/5</span>
            </div>
        </div>
    `).join('');
}

// Actualizar habilidades
function actualizarHabilidades() {
    const container = document.getElementById('habilidadesList');
    if (!container) return;
    
    const habilidades = estadisticasData.habilidades || [];
    console.log('🛠️ Habilidades:', habilidades);
    
    if (habilidades.length === 0) {
        container.innerHTML = '<div class="empty-state"><i class="fas fa-tools"></i><p>No hay habilidades registradas</p></div>';
        return;
    }
    
    container.innerHTML = habilidades.map(habilidad => `
        <span class="habilidad-tag" title="${habilidad.clasificacion}">${habilidad.nombre}</span>
    `).join('');
}

// Configurar filtros
function configurarFiltros() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            filterButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            
            const periodo = this.getAttribute('data-period');
            cargarEstadisticas(periodo);
        });
    });
}

// Utilidades
function formatCurrency(amount) {
    return new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        minimumFractionDigits: 0
    }).format(amount);
}

function mostrarLoading() {
    const containers = ['trabajosRecientes', 'habilidadesList'];
    containers.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Cargando...</div>';
    });
}

function mostrarMensajeError(mensaje) {
    alert(mensaje); // Puedes mejorar esto con un modal bonito
}

console.log('✅ Estadísticas Trabajador cargado correctamente');