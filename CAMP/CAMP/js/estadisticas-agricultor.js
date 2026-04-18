// estadisticas-agricultor.js - VERSIÓN QUE SÍ FUNCIONA

let estadisticasData = {};
let charts = {};

// Inicializar
document.addEventListener('DOMContentLoaded', function() {
    console.log('🌱 Iniciando Estadísticas Agricultor...');
    cargarEstadisticas();
    configurarFiltros();
});

function volverAlIndex() {
    window.location.href = '/vista/index-agricultor.html';
}

// Cargar estadísticas desde el servidor
async function cargarEstadisticas(periodo = 'all') {
    try {
        mostrarLoading();
        
        console.log('📊 Cargando estadísticas del servidor...');
        const response = await fetch(`/api/estadisticas_agricultor?periodo=${periodo}`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        console.log('📡 Response status:', response.status);
        
        const data = await response.json();
        console.log('📦 Datos recibidos:', data);
        
        if (data.success && data.estadisticas) {
            estadisticasData = data.estadisticas;
            console.log('✅ Estadísticas cargadas:', estadisticasData);
            actualizarUI();
        } else {
            console.error('❌ Error en respuesta:', data);
            cargarDatosVacios();
        }
    } catch (error) {
        console.error('❌ Error completo:', error);
        cargarDatosVacios();
    }
}

function cargarDatosVacios() {
    console.warn('⚠️ Cargando interfaz con datos vacíos');
    estadisticasData = {
        resumen: {
            totalOfertas: 0,
            totalContrataciones: 0,
            totalInversion: 0,
            calificacionPromedio: 0
        },
        inversionMensual: [],
        ofertasPorEstado: [],
        contratacionesMensuales: [],
        trabajadoresFrecuentes: [],
        ofertasRecientes: [],
        topTrabajadores: []
    };
    actualizarUI();
}

// Actualizar toda la UI
function actualizarUI() {
    console.log('🎨 Actualizando interfaz...');
    actualizarResumen();
    crearGraficas();
    actualizarOfertasRecientes();
    actualizarTopTrabajadores();
}

// Actualizar resumen
function actualizarResumen() {
    try {
        const resumen = estadisticasData?.resumen || {
            totalOfertas: 0,
            totalContrataciones: 0,
            totalInversion: 0,
            calificacionPromedio: 0
        };
        
        console.log('📊 Resumen:', resumen);
        
        const totalOfertasEl = document.getElementById('totalOfertas');
        const totalContratacionesEl = document.getElementById('totalContrataciones');
        const totalInversionEl = document.getElementById('totalInversion');
        const calificacionPromedioEl = document.getElementById('calificacionPromedio');
        
        if (totalOfertasEl) totalOfertasEl.textContent = resumen.totalOfertas || 0;
        if (totalContratacionesEl) totalContratacionesEl.textContent = resumen.totalContrataciones || 0;
        if (totalInversionEl) totalInversionEl.textContent = formatCurrency(resumen.totalInversion || 0);
        if (calificacionPromedioEl) calificacionPromedioEl.textContent = ((resumen.calificacionPromedio || 0).toFixed(1)) + '/5';
    } catch (error) {
        console.error('❌ Error actualizando resumen:', error);
    }
}

// Crear todas las gráficas
function crearGraficas() {
    try {
        crearGraficaInversionMensual();
        crearGraficaOfertasPorEstado();
        crearGraficaContratacionesMensuales();
        crearGraficaTrabajadoresFrecuentes();
    } catch (error) {
        console.error('❌ Error creando gráficas:', error);
    }
}

// Gráfica de inversión mensual
function crearGraficaInversionMensual() {
    const canvas = document.getElementById('inversionMensual');
    if (!canvas) {
        console.warn('⚠️ Canvas inversionMensual no encontrado');
        return;
    }
    
    try {
        const ctx = canvas.getContext('2d');
        const data = estadisticasData.inversionMensual || [];
        
        if (charts.inversionMensual) {
            charts.inversionMensual.destroy();
        }
        
        const labels = data.length > 0 ? data.map(item => item.mes) : ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'];
        const valores = data.length > 0 ? data.map(item => item.inversion) : [0, 0, 0, 0, 0, 0];
        
        charts.inversionMensual = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Inversión ($)',
                    data: valores,
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
    } catch (error) {
        console.error('❌ Error en gráfica inversión:', error);
    }
}

// Gráfica de ofertas por estado
function crearGraficaOfertasPorEstado() {
    const canvas = document.getElementById('ofertasPorEstado');
    if (!canvas) {
        console.warn('⚠️ Canvas ofertasPorEstado no encontrado');
        return;
    }
    
    try {
        const ctx = canvas.getContext('2d');
        const data = estadisticasData.ofertasPorEstado || [];
        
        if (charts.ofertasPorEstado) {
            charts.ofertasPorEstado.destroy();
        }
        
        const labels = data.length > 0 ? data.map(item => item.estado) : ['Sin datos'];
        const valores = data.length > 0 ? data.map(item => item.cantidad) : [1];
        
        const colors = {
            'Abierta': 'rgba(76, 175, 80, 0.8)',
            'En Proceso': 'rgba(255, 193, 7, 0.8)',
            'Cerrada': 'rgba(244, 67, 54, 0.8)',
            'Finalizada': 'rgba(33, 150, 243, 0.8)'
        };
        
        const backgroundColors = data.length > 0 
            ? data.map(item => colors[item.estado] || 'rgba(158, 158, 158, 0.8)')
            : ['rgba(200, 200, 200, 0.5)'];
        
        charts.ofertasPorEstado = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: valores,
                    backgroundColor: backgroundColors,
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
    } catch (error) {
        console.error('❌ Error en gráfica ofertas:', error);
    }
}

// Gráfica de contrataciones mensuales
function crearGraficaContratacionesMensuales() {
    const canvas = document.getElementById('contratacionesMensuales');
    if (!canvas) {
        console.warn('⚠️ Canvas contratacionesMensuales no encontrado');
        return;
    }
    
    try {
        const ctx = canvas.getContext('2d');
        const data = estadisticasData.contratacionesMensuales || [];
        
        if (charts.contratacionesMensuales) {
            charts.contratacionesMensuales.destroy();
        }
        
        const labels = data.length > 0 ? data.map(item => item.mes) : ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'];
        const valores = data.length > 0 ? data.map(item => item.contrataciones) : [0, 0, 0, 0, 0, 0];
        
        charts.contratacionesMensuales = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Contrataciones',
                    data: valores,
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
                            stepSize: 1
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('❌ Error en gráfica contrataciones:', error);
    }
}

// Gráfica de trabajadores más frecuentes
function crearGraficaTrabajadoresFrecuentes() {
    const canvas = document.getElementById('trabajadoresFrecuentes');
    if (!canvas) {
        console.warn('⚠️ Canvas trabajadoresFrecuentes no encontrado');
        return;
    }
    
    try {
        const ctx = canvas.getContext('2d');
        const data = estadisticasData.trabajadoresFrecuentes || [];
        
        if (charts.trabajadoresFrecuentes) {
            charts.trabajadoresFrecuentes.destroy();
        }
        
        const labels = data.length > 0 ? data.map(item => item.nombre) : ['Sin datos'];
        const valores = data.length > 0 ? data.map(item => item.contrataciones) : [0];
        
        charts.trabajadoresFrecuentes = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Contrataciones',
                    data: valores,
                    backgroundColor: 'rgba(102, 187, 106, 0.8)',
                    borderColor: 'rgba(46, 125, 50, 1)',
                    borderWidth: 2,
                    borderRadius: 8
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('❌ Error en gráfica trabajadores:', error);
    }
}

// Actualizar ofertas recientes
function actualizarOfertasRecientes() {
    const container = document.getElementById('ofertasRecientes');
    if (!container) return;
    
    try {
        const ofertas = estadisticasData.ofertasRecientes || [];
        
        if (ofertas.length === 0) {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-inbox"></i><p>No hay ofertas publicadas</p></div>';
            return;
        }
        
        container.innerHTML = ofertas.map(oferta => {
            const estadoClass = (oferta.estado || '').toLowerCase().replace(' ', '-');
            return `
                <div class="oferta-item">
                    <div class="oferta-titulo">${oferta.titulo || 'Sin título'}</div>
                    <div class="oferta-info">
                        <span>📍 ${oferta.ubicacion || 'Sin ubicación'}</span>
                        <span class="estado-badge estado-${estadoClass}">${oferta.estado || 'Sin estado'}</span>
                        <span>👥 ${oferta.postulaciones || 0} postulación${(oferta.postulaciones !== 1) ? 'es' : ''}</span>
                        <span>💰 ${formatCurrency(oferta.pago || 0)}</span>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('❌ Error actualizando ofertas:', error);
    }
}

// Actualizar top trabajadores
function actualizarTopTrabajadores() {
    const container = document.getElementById('topTrabajadores');
    if (!container) return;
    
    try {
        const trabajadores = estadisticasData.topTrabajadores || [];
        
        if (trabajadores.length === 0) {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-users"></i><p>No hay trabajadores contratados</p></div>';
            return;
        }
        
        container.innerHTML = trabajadores.map((trabajador, index) => `
            <div class="trabajador-item">
                <div class="trabajador-info">
                    <h4>${index + 1}. ${trabajador.nombre || 'Sin nombre'}</h4>
                    <div class="trabajador-stats">
                        <span>💼 ${trabajador.trabajos || 0} trabajo${(trabajador.trabajos !== 1) ? 's' : ''}</span>
                        <span>⭐ ${(trabajador.calificacion || 0).toFixed(1)}/5</span>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('❌ Error actualizando trabajadores:', error);
    }
}

// Configurar filtros
function configurarFiltros() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            filterButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            
            const periodo = this.getAttribute('data-period');
            console.log('🔄 Filtrando por período:', periodo);
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
    }).format(amount || 0);
}

function mostrarLoading() {
    const containers = ['ofertasRecientes', 'topTrabajadores'];
    containers.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Cargando...</div>';
        }
    });
}

console.log('✅ Estadísticas Agricultor cargado');