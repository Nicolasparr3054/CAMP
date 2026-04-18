// ================================================================
// CONFIGURACIÓN AGRICULTOR - CON SISTEMA DE TRADUCCIONES INTEGRADO
// ================================================================

let currentUser = null;
let selectedLanguage = 'es';

// ================================================================
// TRADUCCIONES MULTI-IDIOMA (igual que trabajador)
// ================================================================
const translations = {
    es: {
        page_title: 'Configuración - CAMP',
        user_role: 'Agricultor',
        breadcrumb_home: 'Dashboard',
        breadcrumb_config: 'Configuración',
        main_title: 'Configuración de Cuenta',
        language_title: 'Cambiar Idioma',
        language_desc: 'Selecciona tu idioma preferido para la plataforma',
        save_language: 'Guardar Idioma',
        password_title: 'Cambiar Contraseña',
        password_desc: 'Actualiza tu contraseña para mantener tu cuenta segura',
        current_password: 'Contraseña Actual',
        new_password: 'Nueva Contraseña',
        confirm_password: 'Confirmar Nueva Contraseña',
        change_password: 'Cambiar Contraseña',
        delete_account_title: 'Eliminar Cuenta',
        delete_warning: 'Esta acción no se puede deshacer. Se eliminarán todos tus datos permanentemente.',
        delete_confirm_title: '¿Estás seguro?',
        delete_lose_text: 'Al eliminar tu cuenta se perderán:',
        delete_item1: 'Tu perfil y datos de finca',
        delete_item2: 'Todas las ofertas publicadas',
        delete_item3: 'Historial de contrataciones',
        delete_item4: 'Mensajes y comunicaciones',
        delete_with_password: 'Eliminar con contraseña',
        delete_account_modal: 'Eliminar Cuenta',
        delete_enter_password: 'Para confirmar la eliminación, escribe tu contraseña:',
        delete_understand: 'Entiendo que esta acción no se puede deshacer',
        cancel: 'Cancelar',
        delete_permanently: 'Eliminar Cuenta Permanentemente',
        success_language: 'Idioma cambiado exitosamente',
        success_password: 'Contraseña actualizada correctamente',
        error_password_match: 'Las contraseñas no coinciden',
        error_password_length: 'La contraseña debe tener al menos 8 caracteres',
        error_fill_fields: 'Por favor, completa todos los campos'
    },
    en: {
        page_title: 'Settings - CAMP',
        user_role: 'Farmer',
        breadcrumb_home: 'Dashboard',
        breadcrumb_config: 'Settings',
        main_title: 'Account Settings',
        language_title: 'Change Language',
        language_desc: 'Select your preferred language for the platform',
        save_language: 'Save Language',
        password_title: 'Change Password',
        password_desc: 'Update your password to keep your account secure',
        current_password: 'Current Password',
        new_password: 'New Password',
        confirm_password: 'Confirm New Password',
        change_password: 'Change Password',
        delete_account_title: 'Delete Account',
        delete_warning: 'This action cannot be undone. All your data will be permanently deleted.',
        delete_confirm_title: 'Are you sure?',
        delete_lose_text: 'Deleting your account will lose:',
        delete_item1: 'Your profile and farm data',
        delete_item2: 'All published offers',
        delete_item3: 'Hiring history',
        delete_item4: 'Messages and communications',
        delete_with_password: 'Delete with password',
        delete_account_modal: 'Delete Account',
        delete_enter_password: 'To confirm deletion, enter your password:',
        delete_understand: 'I understand this action cannot be undone',
        cancel: 'Cancel',
        delete_permanently: 'Delete Account Permanently',
        success_language: 'Language changed successfully',
        success_password: 'Password updated successfully',
        error_password_match: 'Passwords do not match',
        error_password_length: 'Password must be at least 8 characters',
        error_fill_fields: 'Please fill in all fields'
    },
    zh: {
        page_title: '设置 - CAMP',
        user_role: '农民',
        breadcrumb_home: '仪表板',
        breadcrumb_config: '设置',
        main_title: '账户设置',
        language_title: '更改语言',
        language_desc: '选择您喜欢的平台语言',
        save_language: '保存语言',
        password_title: '更改密码',
        password_desc: '更新您的密码以保护您的账户',
        current_password: '当前密码',
        new_password: '新密码',
        confirm_password: '确认新密码',
        change_password: '更改密码',
        delete_account_title: '删除账户',
        delete_warning: '此操作无法撤消。您的所有数据将被永久删除。',
        delete_confirm_title: '您确定吗？',
        delete_lose_text: '删除您的账户将丢失：',
        delete_item1: '您的个人资料和农场数据',
        delete_item2: '所有发布的优惠',
        delete_item3: '雇用历史',
        delete_item4: '消息和通信',
        delete_with_password: '使用密码删除',
        delete_account_modal: '删除账户',
        delete_enter_password: '要确认删除，请输入您的密码：',
        delete_understand: '我理解此操作无法撤消',
        cancel: '取消',
        delete_permanently: '永久删除账户',
        success_language: '语言已成功更改',
        success_password: '密码已成功更新',
        error_password_match: '密码不匹配',
        error_password_length: '密码必须至少8个字符',
        error_fill_fields: '请填写所有字段'
    }
};

// ================================================================
// INICIALIZACIÓN
// ================================================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('📋 Configuración agricultor cargada');
    
    loadUserData();
    setupEventListeners();
    initializeLanguageSelector();
    loadUserLanguage();
});

// ================================================================
// SISTEMA DE TRADUCCIÓN
// ================================================================
function loadUserLanguage() {
    const savedLang = localStorage.getItem('userLanguage') || 'es';
    selectedLanguage = savedLang;
    applyTranslations(savedLang);
    updateLanguageSelection(savedLang);
}

function applyTranslations(lang) {
    const trans = translations[lang] || translations['es'];
    
    // Actualizar todos los elementos con data-i18n
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (trans[key]) {
            if (element.tagName === 'INPUT' && element.type !== 'submit') {
                element.placeholder = trans[key];
            } else {
                element.textContent = trans[key];
            }
        }
    });
    
    // Actualizar placeholders específicos
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        const key = element.getAttribute('data-i18n-placeholder');
        if (trans[key]) {
            element.placeholder = trans[key];
        }
    });
    
    // Actualizar el título de la página
    document.title = trans['page_title'];
    
    // Actualizar el atributo lang del HTML
    document.documentElement.lang = lang;
}

function updateLanguageSelection(lang) {
    document.querySelectorAll('.language-card').forEach(card => {
        card.classList.remove('active');
        if (card.getAttribute('data-lang') === lang) {
            card.classList.add('active');
        }
    });
}

// ================================================================
// CARGAR DATOS DEL USUARIO
// ================================================================
async function loadUserData() {
    try {
        const response = await fetch('/get_user_session', {
            method: 'GET',
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                currentUser = data.user;
                updateUIWithUserData(data.user);
            } else {
                window.location.href = '/vista/login-trabajador.html';
            }
        } else {
            window.location.href = '/vista/login-trabajador.html';
        }
    } catch (error) {
        console.error('Error:', error);
        loadLocalUserData();
    }
}

function loadLocalUserData() {
    try {
        const userData = localStorage.getItem('agroMatchUser');
        if (userData) {
            currentUser = JSON.parse(userData);
            updateUIWithUserData(currentUser);
        } else {
            window.location.href = '/vista/login-trabajador.html';
        }
    } catch (error) {
        console.error('Error cargando datos locales:', error);
        window.location.href = '/vista/login-trabajador.html';
    }
}

function updateUIWithUserData(user) {
    const userNameElement = document.getElementById('userName');
    if (userNameElement) {
        const fullName = user.full_name || `${user.first_name || ''} ${user.last_name || ''}`.trim();
        userNameElement.textContent = fullName || user.username || user.email || 'Usuario';
    }
}

// ================================================================
// INICIALIZAR SELECTOR DE IDIOMA
// ================================================================
function initializeLanguageSelector() {
    document.querySelectorAll('.language-card').forEach(card => {
        card.addEventListener('click', function() {
            const lang = this.getAttribute('data-lang');
            selectedLanguage = lang;
            updateLanguageSelection(lang);
        });
    });
}

// ================================================================
// EVENT LISTENERS
// ================================================================
function setupEventListeners() {
    const languageForm = document.getElementById('languageForm');
    if (languageForm) {
        languageForm.addEventListener('submit', handleLanguageChange);
    }
    
    const passwordForm = document.getElementById('changePasswordForm');
    if (passwordForm) {
        passwordForm.addEventListener('submit', handlePasswordChange);
    }
    
    // Validación de contraseñas
    const confirmPasswordField = document.getElementById('confirmPassword');
    if (confirmPasswordField) {
        confirmPasswordField.addEventListener('input', validatePasswordMatch);
    }
}

// ================================================================
// MANEJAR CAMBIO DE IDIOMA
// ================================================================
async function handleLanguageChange(e) {
    e.preventDefault();
    
    try {
        // Guardar en localStorage inmediatamente
        localStorage.setItem('userLanguage', selectedLanguage);
        
        // Intentar guardar en el servidor
        const response = await fetch('/api/actualizar-idioma-usuario', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
                language: selectedLanguage
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                showNotification(translations[selectedLanguage].success_language, 'success');
                applyTranslations(selectedLanguage);
            }
        } else {
            // Si falla el servidor, aún aplicamos el cambio localmente
            showNotification(translations[selectedLanguage].success_language, 'success');
            applyTranslations(selectedLanguage);
        }
    } catch (error) {
        console.error('Error:', error);
        // Aplicar el cambio localmente aunque falle el servidor
        showNotification(translations[selectedLanguage].success_language, 'success');
        applyTranslations(selectedLanguage);
    }
}

// ================================================================
// MANEJAR CAMBIO DE CONTRASEÑA
// ================================================================
async function handlePasswordChange(e) {
    e.preventDefault();
    
    const currentPassword = document.getElementById('currentPassword')?.value;
    const newPassword = document.getElementById('newPassword')?.value;
    const confirmPassword = document.getElementById('confirmPassword')?.value;
    
    if (!currentPassword || !newPassword || !confirmPassword) {
        showNotification(translations[selectedLanguage].error_fill_fields, 'error');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        showNotification(translations[selectedLanguage].error_password_match, 'error');
        return;
    }
    
    if (newPassword.length < 8) {
        showNotification(translations[selectedLanguage].error_password_length, 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
                currentPassword: currentPassword,
                newPassword: newPassword
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showNotification(translations[selectedLanguage].success_password, 'success');
            const form = document.getElementById('changePasswordForm');
            if (form) form.reset();
        } else {
            showNotification(data.message || 'Error al cambiar la contraseña', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error de conexión', 'error');
    }
}

// ================================================================
// FUNCIONES DE UTILIDAD
// ================================================================
function togglePassword(fieldId) {
    const field = document.getElementById(fieldId);
    if (!field) return;
    
    const button = field.nextElementSibling;
    if (!button) return;
    
    const icon = button.querySelector('i');
    if (!icon) return;
    
    if (field.type === 'password') {
        field.type = 'text';
        icon.classList.replace('fa-eye', 'fa-eye-slash');
    } else {
        field.type = 'password';
        icon.classList.replace('fa-eye-slash', 'fa-eye');
    }
}

function validatePasswordMatch() {
    const newPassword = document.getElementById('newPassword');
    const confirmPassword = document.getElementById('confirmPassword');
    
    if (!newPassword || !confirmPassword) return;
    
    if (confirmPassword.value && newPassword.value !== confirmPassword.value) {
        confirmPassword.style.borderColor = '#f44336';
        confirmPassword.style.boxShadow = '0 0 0 3px rgba(244, 67, 54, 0.1)';
    } else {
        confirmPassword.style.borderColor = '#4CAF50';
        confirmPassword.style.boxShadow = '0 0 0 3px rgba(76, 175, 80, 0.1)';
    }
}

// ================================================================
// ELIMINACIÓN DE CUENTA
// ================================================================
function showDeleteConfirmation() {
    const modal = document.getElementById('deleteAccountModal');
    if (modal) modal.style.display = 'flex';
}

function hideDeleteModal() {
    const modal = document.getElementById('deleteAccountModal');
    if (modal) modal.style.display = 'none';
    
    const deletePassword = document.getElementById('deletePassword');
    const confirmDelete = document.getElementById('confirmDelete');
    
    if (deletePassword) deletePassword.value = '';
    if (confirmDelete) confirmDelete.checked = false;
}

async function deleteAccount() {
    const passwordField = document.getElementById('deletePassword');
    const confirmedField = document.getElementById('confirmDelete');
    
    const password = passwordField ? passwordField.value : '';
    const confirmed = confirmedField ? confirmedField.checked : false;
    
    if (!password) {
        showNotification('Por favor, ingresa tu contraseña', 'error');
        return;
    }
    
    if (!confirmed) {
        showNotification('Debes confirmar la eliminación', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/delete-account', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
                password: password
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showNotification('Cuenta eliminada correctamente', 'success');
            
            localStorage.clear();
            sessionStorage.clear();
            
            setTimeout(() => {
                window.location.href = '/vista/login-trabajador.html';
            }, 3000);
            
        } else {
            showNotification(data.message || 'Error al eliminar la cuenta', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error de conexión', 'error');
    }
    
    hideDeleteModal();
}

// ================================================================
// SISTEMA DE NOTIFICACIONES
// ================================================================
function showNotification(message, type = 'info', duration = 4000) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    
    const icon = getNotificationIcon(type);
    
    notification.innerHTML = `
        <div class="notification-content">
            <i class="${icon}"></i>
            <span>${message}</span>
        </div>
        <button class="notification-close" onclick="closeNotification(this.parentElement)">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    if (!document.getElementById('notification-styles')) {
        const styles = document.createElement('style');
        styles.id = 'notification-styles';
        styles.textContent = `
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                background: white;
                border: 2px solid #ddd;
                border-radius: 12px;
                padding: 1.25rem;
                box-shadow: 0 8px 25px rgba(0,0,0,0.15);
                z-index: 10000;
                max-width: 400px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                animation: slideInRight 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .notification-success {
                border-left: 5px solid #4CAF50;
                background: linear-gradient(135deg, #ffffff, #f1f8f4);
            }
            
            .notification-error {
                border-left: 5px solid #f44336;
                background: linear-gradient(135deg, #ffffff, #fef5f4);
            }
            
            .notification-info {
                border-left: 5px solid #2196F3;
                background: linear-gradient(135deg, #ffffff, #f1f7fc);
            }
            
            .notification-content {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                flex: 1;
            }
            
            .notification-success .notification-content i {
                color: #4CAF50;
                font-size: 1.5rem;
            }
            
            .notification-error .notification-content i {
                color: #f44336;
                font-size: 1.5rem;
            }
            
            .notification-info .notification-content i {
                color: #2196F3;
                font-size: 1.5rem;
            }
            
            .notification-close {
                background: none;
                border: none;
                color: #666;
                cursor: pointer;
                padding: 0.5rem;
                border-radius: 8px;
                transition: all 0.3s;
            }
            
            .notification-close:hover {
                background: #f0f0f0;
                color: #333;
            }
            
            @keyframes slideInRight {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            
            @keyframes slideOutRight {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(styles);
    }
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        closeNotification(notification);
    }, duration);
    
    return notification;
}

function getNotificationIcon(type) {
    switch (type) {
        case 'success':
            return 'fas fa-check-circle';
        case 'error':
            return 'fas fa-exclamation-circle';
        case 'info':
        default:
            return 'fas fa-info-circle';
    }
}

function closeNotification(element) {
    if (element && element.parentNode) {
        element.style.animation = 'slideOutRight 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
        setTimeout(() => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
        }, 400);
    }
}

// ================================================================
// CERRAR MODALES CON ESC Y CLICK FUERA
// ================================================================
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        hideDeleteModal();
    }
});

document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-overlay')) {
        hideDeleteModal();
    }
});

// ================================================================
// FUNCIONES GLOBALES
// ================================================================
window.togglePassword = togglePassword;
window.showDeleteConfirmation = showDeleteConfirmation;
window.hideDeleteModal = hideDeleteModal;
window.deleteAccount = deleteAccount;
window.closeNotification = closeNotification;

console.log('✅ Configuración agricultor cargado correctamente');