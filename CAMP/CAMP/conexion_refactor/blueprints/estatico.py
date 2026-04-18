# Blueprint: estatico
from flask import Blueprint, request, redirect, url_for, session, jsonify, render_template, send_from_directory, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, timedelta
from urllib.parse import quote, unquote
import hashlib, uuid, bcrypt, re, os, json, mysql.connector, logging, secrets, smtplib, traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
try:
    from flask_mail import Mail, Message
except ImportError:
    Mail = None
    Message = None
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from conexion import execute_query, get_db_connection

logger = logging.getLogger(__name__)

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost', database='camp', user='root', password='123456',
            charset='utf8mb4', collation='utf8mb4_unicode_ci'
        )
        return connection
    except mysql.connector.Error as e:
        logger.error(f"Error conectando a la base de datos: {e}")
        raise

create_connection = get_db_connection

estatico_bp = Blueprint('estatico', __name__)
from blueprints.helpers import require_login, require_role, hash_password, verify_password, no_cache

def _find_project_root():
    """Sube desde blueprints/ hasta encontrar la carpeta vista/"""
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):  # máximo 5 niveles hacia arriba
        if os.path.isdir(os.path.join(current, 'vista')):
            return current
        current = os.path.dirname(current)
    return None

PROJECT_ROOT = _find_project_root()

@estatico_bp.route('/vista/<path:filename>')
def serve_vista(filename):
    """Sirve archivos HTML desde la carpeta vista"""
    try:
        if not PROJECT_ROOT:
            return "Error: No se encontró la carpeta vista/", 500
        vista_path = os.path.join(PROJECT_ROOT, 'vista')
        file_path = os.path.join(vista_path, filename)
        if not os.path.exists(file_path):
            print(f"❌ Archivo no encontrado: {file_path}")
            return f"Archivo no encontrado: {filename}", 404
        print(f"✅ Sirviendo: {file_path}")
        return send_from_directory(vista_path, filename)
    except Exception as e:
        print(f"❌ Error sirviendo vista {filename}: {str(e)}")
        return f"Error: {filename}", 500


@estatico_bp.route('/script.js')
def serve_script():
    """Sirve el archivo script.js desde la carpeta vista"""
    try:
        base_dir = PROJECT_ROOT  # auto-detected root
        vista_path = os.path.join(PROJECT_ROOT, 'vista')
        vista_path = os.path.abspath(vista_path)
        
        file_path = os.path.join(vista_path, 'script.js')
        if not os.path.exists(file_path):
            print(f"❌ script.js no encontrado: {file_path}")
            return "script.js no encontrado", 404
            
        print(f"✅ Sirviendo script.js: {file_path}")
        response = send_from_directory(vista_path, 'script.js')
        response.headers['Content-Type'] = 'application/javascript'
        return response
    except Exception as e:
        print(f"❌ Error sirviendo script.js: {str(e)}")
        return f"Error sirviendo script.js: {str(e)}", 500


@estatico_bp.route('/css/<path:filename>')
def serve_css(filename):
    """Sirve archivos CSS desde assent/css"""
    try:
        base_dir = PROJECT_ROOT  # auto-detected root
        css_path = os.path.join(PROJECT_ROOT, 'assent', 'css')
        css_path = os.path.abspath(css_path)
        
        if not os.path.exists(os.path.join(css_path, filename)):
            print(f"❌ CSS no encontrado: {filename}")
            return f"CSS no encontrado: {filename}", 404
            
        response = send_from_directory(css_path, filename)
        response.headers['Content-Type'] = 'text/css'
        return response
    except Exception as e:
        print(f"❌ Error sirviendo CSS {filename}: {str(e)}")
        return f"Error sirviendo CSS: {filename}", 500


@estatico_bp.route('/js/<path:filename>')
def serve_js(filename):
    """Sirve archivos JavaScript desde js/"""
    try:
        base_dir = PROJECT_ROOT  # auto-detected root
        js_path = os.path.join(PROJECT_ROOT, 'js')
        js_path = os.path.abspath(js_path)
        
        if not os.path.exists(os.path.join(js_path, filename)):
            print(f"❌ JS no encontrado: {filename}")
            return f"JS no encontrado: {filename}", 404
            
        response = send_from_directory(js_path, filename)
        response.headers['Content-Type'] = 'application/javascript'
        return response
    except Exception as e:
        print(f"❌ Error sirviendo JS {filename}: {str(e)}")
        return f"Error sirviendo JS: {filename}", 500


@estatico_bp.route('/assent/css/<path:filename>')
def serve_assent_css(filename):
    """Sirve archivos CSS desde assent/css"""
    try:
        base_dir = PROJECT_ROOT  # auto-detected root
        assent_css_path = os.path.join(PROJECT_ROOT, 'assent', 'css')
        assent_css_path = os.path.abspath(assent_css_path)
        
        if not os.path.exists(os.path.join(assent_css_path, filename)):
            print(f"❌ Assent CSS no encontrado: {filename}")
            return f"Assent CSS no encontrado: {filename}", 404
            
        response = send_from_directory(assent_css_path, filename)
        response.headers['Content-Type'] = 'text/css'
        return response
    except Exception as e:
        print(f"❌ Error sirviendo Assent CSS {filename}: {str(e)}")
        return f"Error sirviendo Assent CSS: {filename}", 500


@estatico_bp.route('/img/<path:filename>')
def serve_img(filename):
    """Sirve archivos de imágenes"""
    try:
        base_dir = PROJECT_ROOT  # auto-detected root
        img_path = os.path.join(PROJECT_ROOT, 'img')
        img_path = os.path.abspath(img_path)
        
        if not os.path.exists(os.path.join(img_path, filename)):
            print(f"❌ Imagen no encontrada: {filename}")
            return f"Imagen no encontrada: {filename}", 404
            
        return send_from_directory(img_path, filename)
    except Exception as e:
        print(f"❌ Error sirviendo imagen {filename}: {str(e)}")
        return f"Error sirviendo imagen: {filename}", 500


@estatico_bp.route('/assent/img/<path:filename>')
def serve_assent_img(filename):
    """Sirve archivos de imágenes desde assent/img"""
    try:
        base_dir = PROJECT_ROOT  # auto-detected root
        assent_img_path = os.path.join(PROJECT_ROOT, 'assent', 'img')
        assent_img_path = os.path.abspath(assent_img_path)
        
        if not os.path.exists(os.path.join(assent_img_path, filename)):
            print(f"❌ Assent imagen no encontrada: {filename}")
            return f"Assent imagen no encontrada: {filename}", 404
            
        return send_from_directory(assent_img_path, filename)
    except Exception as e:
        print(f"❌ Error sirviendo Assent imagen {filename}: {str(e)}")
        return f"Error sirviendo Assent imagen: {filename}", 500


@estatico_bp.route('/assent/js/<path:filename>')
def serve_assent_js(filename):
    """Sirve archivos JavaScript desde assent/js"""
    try:
        base_dir = PROJECT_ROOT  # auto-detected root
        assent_js_path = os.path.join(PROJECT_ROOT, 'assent', 'js')
        assent_js_path = os.path.abspath(assent_js_path)
        
        if not os.path.exists(os.path.join(assent_js_path, filename)):
            print(f"❌ Assent JS no encontrado: {filename}")
            return f"Assent JS no encontrado: {filename}", 404
            
        response = send_from_directory(assent_js_path, filename)
        response.headers['Content-Type'] = 'application/javascript'
        return response
    except Exception as e:
        print(f"❌ Error sirviendo Assent JS {filename}: {str(e)}")
        return f"Error sirviendo Assent JS: {filename}", 500


# ================================================================
# RUTA DE ESTADISTICAS DEL TRABAJADOR
# ================================================================    

@estatico_bp.route('/estadisticas-trabajador')
def estadisticas_trabajador():
    """Sirve la página de estadísticas del trabajador"""
    try:
        vista_path = os.path.join(PROJECT_ROOT, 'vista')
        file_path = os.path.join(vista_path, 'estadisticas-trabajador.html')
        if os.path.exists(file_path):
            return send_from_directory(vista_path, 'estadisticas-trabajador.html')
        return f"Archivo no encontrado: estadisticas-trabajador.html", 404
    except Exception as e:
        return f"Error: {str(e)}", 500


@estatico_bp.route('/index-trabajador.html')
def serve_index_trabajador():
    """Sirve la página principal del trabajador"""
    try:
        vista_path = os.path.join(PROJECT_ROOT, 'vista')
        return send_from_directory(vista_path, 'index-trabajador.html')
    except Exception as e:
        return f'Error: {str(e)}', 500


# ================================================================
# RUTA PARA VERIFICAR ARCHIVOS (DEBUGGING MEJORADO)
# ================================================================

# ...existing code...
@estatico_bp.route('/check_files')
def check_files():
    """Verifica qué archivos existen en las carpetas"""
    try:
        base_dir = PROJECT_ROOT  # auto-detected root
        
        # Verificar carpetas
        folders_to_check = ['vista', 'css', 'js', 'img', 'assent/css', 'assent/js', 'assent/img']
        result = {
            'base_dir': base_dir,
            'folders': {},
            'dashboard_files': {}
        }
        
        for folder in folders_to_check:
            folder_path = os.path.join(PROJECT_ROOT, folder)
            folder_path = os.path.abspath(folder_path)
            
            if os.path.exists(folder_path):
                files = os.listdir(folder_path)
                result['folders'][folder] = {
                    'exists': True,
                    'path': folder_path,
                    'files': files
                }
            else:
                result['folders'][folder] = {
                    'exists': False,
                    'path': folder_path,
                    'files': []
                }
        
        # Verificar específicamente los archivos del dashboard de agricultor
        vista_path = os.path.join(PROJECT_ROOT, 'vista')
        dashboard_files = {
            'dashboard-agricultor.html': os.path.join(vista_path, 'dashboard-agricultor.html'),
            'styles.css': os.path.join(vista_path, 'styles.css'),
            'script.js': os.path.join(vista_path, 'script.js')
        }
        
        for file_name, file_path in dashboard_files.items():
            result['dashboard_files'][file_name] = {
                'exists': os.path.exists(file_path),
                'path': file_path
            }
        
        # Verificar archivos del dashboard de trabajador
        trabajador_files = {
            'index-trabajador.html': os.path.join(vista_path, 'index-trabajador.html'),
            'dashboard-trabajador.css': os.path.join(vista_path, 'index-trabajador.css'),
            'dashboard-trabajador.js': os.path.join(vista_path, 'index-trabajador.js')
        }

        result['trabajador_files'] = {}
        for file_name, file_path in trabajador_files.items():
            result['trabajador_files'][file_name] = {
                'exists': os.path.exists(file_path),
                'path': file_path
            }

        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'base_dir': PROJECT_ROOT
        })
        
# ================================================================
# FUNCIONES AUXILIARES
# ================================================================

def validate_email(email):
    """Valida formato de email"""
    pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return re.match(pattern, email) is not None

def validate_name(name):
    """Valida que el nombre solo contenga letras y espacios"""
    pattern = r'^[A-Za-zÀ-ÿ\s]+$'
    return re.match(pattern, name) is not None

@estatico_bp.route('/test', methods=['GET'])
def test():
    """Ruta de prueba para verificar que el servidor funciona"""
    try:
        base_dir = PROJECT_ROOT  # auto-detected root
        
        return jsonify({
            'message': 'Servidor Flask funcionando correctamente',
            'status': 'OK',
            'base_directory': base_dir,
            'session_active': 'user_id' in session,
            'session_user': session.get('user_name', 'No logueado'),
            'rutas_disponibles': [
                '/test',
                '/check_files',
                '/check_session',
                '/validate_session',
                '/get_user_session',
                '/get_user_data.py',
                '/registro.py',
                '/login.py',
                '/logout',
                '/logout.py',
                '/dashboard-agricultor',
                '/dashboard-trabajador', 
                '/dashboard-admin',
                '/vista/<archivo>',
                '/css/<archivo>',
                '/assent/css/<archivo>',
                '/img/<archivo>',
                '/assent/img/<archivo>',
                '/js/<archivo>',
                '/assent/js/<archivo>',
                '/styles.css',
                '/script.js'
            ],
            'dashboard_files': {
                'html': '/vista/dashboard-agricultor.html',
                'css': '/styles.css',
                'js': '/script.js'
            }
        })
    except Exception as e:
        return jsonify({
            'message': 'Error en el servidor',
            'status': 'ERROR',
            'error': str(e)
        }), 500

# ================================================================
# MANEJO DE ERRORES MEJORADO
# ================================================================

def not_found(error):
    """Maneja errores 404 con más información"""
    requested_url = request.url
    print(f"❌ Error 404: Página no encontrada - {requested_url}")
    
    # Si es una solicitud de archivo HTML, intentar sugerir alternativas
    if '.html' in requested_url:
        print(f"🔍 Intentando encontrar alternativas para: {requested_url}")
        
        # Obtener información de archivos disponibles
        try:
            base_dir = PROJECT_ROOT  # auto-detected root
            vista_path = os.path.join(PROJECT_ROOT, 'vista')
            
            if os.path.exists(vista_path):
                available_files = os.listdir(vista_path)
                html_files = [f for f in available_files if f.endswith('.html')]
                
                return jsonify({
                    'error': True,
                    'message': 'Página no encontrada',
                    'status': 404,
                    'requested_url': requested_url,
                    'suggestion': 'Verifica que el archivo exists en la carpeta vista/',
                    'available_html_files': html_files,
                    'vista_path': vista_path
                }), 404
        except:
            pass
    
    return jsonify({
        'error': True,
        'message': 'Página no encontrada',
        'status': 404,
        'requested_url': requested_url
    }), 404

def internal_error(error):
    """Maneja errores 500"""
    print(f"❌ Error interno del servidor: {error}")
    return jsonify({
        'error': True,
        'message': 'Error interno del servidor',
        'status': 500,
        'details': str(error)
    }), 500

# ================================================================
# MIDDLEWARE PARA LOGS DE SESIÓN
# ================================================================

def log_request_info():
    """Log información de cada request (solo para debugging)"""
    # Solo loguear requests importantes, no archivos estáticos
    if request.endpoint and not any(static in request.path for static in ['/css/', '/js/', '/img/', '/assent/']):
        print(f"🔍 Request: {request.method} {request.path} | Session: {'✅' if 'user_id' in session else '❌'} | User: {session.get('user_name', 'Anónimo')}")

# ================================================================
# FUNCIONES ADICIONALES DE UTILIDAD
# ================================================================

@estatico_bp.route('/api/user/profile', methods=['GET'])
@require_login
def get_user_profile():
    """Obtiene el perfil completo del usuario"""
    try:
        user_id = session['user_id']
        
        # Obtener datos completos del usuario desde la base de datos
        user = execute_query(
            """SELECT ID_Usuario, Nombre, Apellido, Correo, Telefono, Rol, 
                      Estado, Fecha_Registro 
               FROM Usuario WHERE ID_Usuario = %s""",
            (user_id,),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'error': True, 'message': 'Usuario no encontrado'}), 404
        
        return jsonify({
            'error': False,
            'user': {
                'id': user['ID_Usuario'],
                'nombre': user['Nombre'],
                'apellido': user['Apellido'],
                'correo': user['Correo'],
                'telefono': user.get('Telefono', ''),
                'rol': user['Rol'],
                'estado': user['Estado'],
                'fecha_registro': user['Fecha_Registro'].isoformat() if user['Fecha_Registro'] else None
            }
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo perfil: {str(e)}")
        return jsonify({'error': True, 'message': str(e)}), 500


@estatico_bp.route('/static/<path:filename>')
def serve_static_file(filename):
    """Servir archivos estáticos incluyendo uploads"""
    try:
        # Crear directorio static si no existe
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static')
        static_dir = os.path.abspath(static_dir)
        
        if not os.path.exists(static_dir):
            os.makedirs(static_dir, exist_ok=True)
        
        return send_from_directory(static_dir, filename)
    except Exception as e:
        print(f"Error sirviendo archivo estático: {str(e)}")
        return "Archivo no encontrado", 404


# ================================================================
# RUTA PARA OBTENER PERFIL COMPLETO DE OTRO USUARIO
# ================================================================

@estatico_bp.route('/api/get-user-profile/<int:user_id>')
def get_user_profile_complete(user_id):
    """Obtener perfil completo de un usuario (para visualización)"""
    try:
        # Verificar que el usuario solicitado existe y está activo
        user = execute_query(
            """SELECT ID_Usuario, Nombre, Apellido, Correo, Telefono, URL_Foto, 
                      Red_Social, Rol, Estado, Fecha_Registro
               FROM Usuario 
               WHERE ID_Usuario = %s AND Estado = 'Activo'""",
            (user_id,),
            fetch_one=True
        )
        
        if not user:
            return jsonify({
                'success': False, 
                'message': 'Usuario no encontrado o inactivo'
            }), 404
        
        # Información adicional según el rol
        additional_info = {}
        
        if user['Rol'] == 'Trabajador':
            # Obtener habilidades
            habilidades = execute_query(
                "SELECT Nombre, Clasificacion FROM Habilidad WHERE ID_Trabajador = %s",
                (user_id,)
            ) or []
            
            # Obtener experiencias
            experiencias = execute_query(
                """SELECT Fecha_Inicio, Fecha_Fin, Ubicacion, Observacion 
                   FROM Experiencia WHERE ID_Trabajador = %s 
                   ORDER BY Fecha_Inicio DESC""",
                (user_id,)
            ) or []
            
            additional_info = {
                'habilidades': habilidades,
                'experiencias': experiencias
            }
            
        elif user['Rol'] == 'Agricultor':
            # Obtener predios
            predios = execute_query(
                """SELECT Nombre_Finca, Ubicacion_Latitud, Ubicacion_Longitud, 
                          Descripcion FROM Predio WHERE ID_Usuario = %s""",
                (user_id,)
            ) or []
            
            # Obtener ofertas activas
            ofertas = execute_query(
                """SELECT Titulo, Descripcion, Pago_Ofrecido, Fecha_Publicacion 
                   FROM Oferta_Trabajo 
                   WHERE ID_Agricultor = %s AND Estado = 'Abierta' 
                   ORDER BY Fecha_Publicacion DESC LIMIT 5""",
                (user_id,)
            ) or []
            
            additional_info = {
                'predios': predios,
                'ofertas_activas': ofertas
            }
        
        # Calcular calificación promedio
        calificacion_info = execute_query(
            """SELECT AVG(CAST(Puntuacion AS UNSIGNED)) as promedio, 
                      COUNT(*) as total_calificaciones
               FROM Calificacion 
               WHERE ID_Usuario_Receptor = %s""",
            (user_id,),
            fetch_one=True
        )
        
        calificacion_promedio = 0
        total_calificaciones = 0
        
        if calificacion_info:
            calificacion_promedio = float(calificacion_info['promedio']) if calificacion_info['promedio'] else 0
            total_calificaciones = calificacion_info['total_calificaciones'] or 0
        
        return jsonify({
            'success': True,
            'user': {
                'id': user['ID_Usuario'],
                'nombre_completo': f"{user['Nombre']} {user['Apellido']}",
                'nombre': user['Nombre'],
                'apellido': user['Apellido'],
                'correo': user['Correo'],
                'telefono': user.get('Telefono', ''),
                'rol': user['Rol'],
                'foto_url': user.get('URL_Foto'),
                'red_social': user.get('Red_Social', ''),
                'fecha_registro': user['Fecha_Registro'].isoformat() if user['Fecha_Registro'] else None,
                'calificacion_promedio': calificacion_promedio,
                'total_calificaciones': total_calificaciones,
                **additional_info
            }
        })
        
    except Exception as e:
        print(f"Error obteniendo perfil de usuario: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ================================================================
# RUTA DE PRUEBA PARA CREAR SESIÓN (TEMPORAL - PARA TESTING)
# ================================================================

@estatico_bp.route('/test-session')
def test_session():
    """Crear sesión de prueba - ELIMINAR EN PRODUCCIÓN"""
    # Buscar el primer usuario activo en la base de datos
    user = execute_query(
        "SELECT * FROM Usuario WHERE Estado = 'Activo' LIMIT 1",
        fetch_one=True
    )
    
    if user:
        session['user_id'] = user['ID_Usuario']
        session['username'] = user['Correo']
        session['first_name'] = user['Nombre']
        session['last_name'] = user['Apellido']
        session['email'] = user['Correo']
        session['user_role'] = user['Rol']
        session['user_name'] = f"{user['Nombre']} {user['Apellido']}"
        session['telefono'] = user.get('Telefono', '')
        
        return f"""
        <h2>Sesión de prueba creada</h2>
        <p><strong>Usuario:</strong> {user['Nombre']} {user['Apellido']}</p>
        <p><strong>Email:</strong> {user['Correo']}</p>
        <p><strong>Rol:</strong> {user['Rol']}</p>
        <p><strong>ID:</strong> {user['ID_Usuario']}</p>
        <br>
        <a href="/vista/perfil-trabajador.html" style="background: #28a745; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;">
            Ir al Perfil
        </a>
        """
    else:
        return "No hay usuarios en la base de datos. Registra un usuario primero."


# ================================================================
# RUTAS PARA CONFIGURACIÓN DEL TRABAJADOR - SIN TABLA ADICIONAL
# ================================================================

@estatico_bp.route('/api/change-password', methods=['POST'])
@require_login
def change_password():
   """Cambiar contraseña del usuario"""
   try:
       data = request.get_json()
       current_password = data.get('currentPassword')
       new_password = data.get('newPassword')
       
       if not current_password or not new_password:
           return jsonify({'success': False, 'message': 'Faltan datos requeridos'}), 400
       
       # Obtener usuario actual
       user = execute_query(
           "SELECT Contrasena FROM Usuario WHERE ID_Usuario = %s",
           (session['user_id'],),
           fetch_one=True
       )
       
       if not user:
           return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
       
       # Verificar contraseña actual
       if not verify_password(current_password, user['Contrasena']):
           return jsonify({'success': False, 'message': 'Contraseña actual incorrecta'}), 400
       
       # Hashear nueva contraseña
       hashed_new_password = hash_password(new_password)
       
       # Actualizar en base de datos
       execute_query(
           "UPDATE Usuario SET Contrasena = %s WHERE ID_Usuario = %s",
           (hashed_new_password, session['user_id'])
       )
       
       print(f"Contraseña actualizada para usuario ID: {session['user_id']}")
       
       return jsonify({
           'success': True,
           'message': 'Contraseña actualizada correctamente'
       })
       
   except Exception as e:
       print(f"Error cambiando contraseña: {str(e)}")
       return jsonify({'success': False, 'message': str(e)}), 500


@estatico_bp.route('/api/update-notification-settings', methods=['POST'])
@require_login
def update_notification_settings():
   """Actualizar configuración de notificaciones usando tabla Usuario"""
   try:
       import json
       
       data = request.get_json()
       user_id = session['user_id']
       
       # Obtener configuraciones actuales
       current_user = execute_query(
           "SELECT Configuraciones FROM Usuario WHERE ID_Usuario = %s",
           (user_id,),
           fetch_one=True
       )
       
       # Parsear configuraciones existentes o crear nuevas
       if current_user and current_user.get('Configuraciones'):
           try:
               configuraciones = json.loads(current_user['Configuraciones'])
           except:
               configuraciones = {}
       else:
           configuraciones = {}
       
       # Actualizar configuración de notificaciones
       configuraciones['notificaciones'] = {
           'emailNotifications': data.get('emailNotifications', True),
           'emailUpdates': data.get('emailUpdates', True),
           'whatsappNotifications': data.get('whatsappNotifications', False),
           'whatsappUrgent': data.get('whatsappUrgent', False)
       }
       
       # Actualizar teléfono y configuraciones
       whatsapp_number = data.get('whatsappNumber', '').strip()
       
       execute_query(
           """UPDATE Usuario 
              SET Telefono = %s, Configuraciones = %s
              WHERE ID_Usuario = %s""",
           (whatsapp_number if whatsapp_number else None, 
            json.dumps(configuraciones), 
            user_id)
       )
       
       print(f"Configuración de notificaciones actualizada para usuario ID: {user_id}")
       
       return jsonify({
           'success': True,
           'message': 'Configuración de notificaciones guardada'
       })
       
   except Exception as e:
       print(f"Error actualizando notificaciones: {str(e)}")
       return jsonify({'success': False, 'message': str(e)}), 500


@estatico_bp.route('/api/update-preferences', methods=['POST'])
@require_login
def update_preferences():
   """Actualizar preferencias del usuario usando tabla Usuario"""
   try:
       import json
       
       data = request.get_json()
       user_id = session['user_id']
       
       # Obtener configuraciones actuales
       current_user = execute_query(
           "SELECT Configuraciones FROM Usuario WHERE ID_Usuario = %s",
           (user_id,),
           fetch_one=True
       )
       
       # Parsear configuraciones existentes o crear nuevas
       if current_user and current_user.get('Configuraciones'):
           try:
               configuraciones = json.loads(current_user['Configuraciones'])
           except:
               configuraciones = {}
       else:
           configuraciones = {}
       
       # Actualizar preferencias
       configuraciones['preferencias'] = {
           'language': data.get('language', 'es'),
           'theme': data.get('theme', 'light'),
           'timezone': data.get('timezone', 'America/Bogota')
       }
       
       # Guardar en base de datos
       execute_query(
           """UPDATE Usuario 
              SET Configuraciones = %s
              WHERE ID_Usuario = %s""",
           (json.dumps(configuraciones), user_id)
       )
       
       print(f"Preferencias actualizadas para usuario ID: {user_id}")
       
       return jsonify({
           'success': True,
           'message': 'Preferencias guardadas correctamente'
       })
       
   except Exception as e:
       print(f"Error actualizando preferencias: {str(e)}")
       return jsonify({'success': False, 'message': str(e)}), 500


@estatico_bp.route('/api/delete-account', methods=['DELETE'])
@require_login
def delete_account():
   """Eliminar cuenta del usuario"""
   try:
       data = request.get_json()
       password = data.get('password')
       user_id = session['user_id']
       
       if not password:
           return jsonify({'success': False, 'message': 'Contraseña requerida'}), 400
       
       # Verificar contraseña
       user = execute_query(
           "SELECT Contrasena FROM Usuario WHERE ID_Usuario = %s",
           (user_id,),
           fetch_one=True
       )
       
       if not user or not verify_password(password, user['Contrasena']):
           return jsonify({'success': False, 'message': 'Contraseña incorrecta'}), 400
       
       # Eliminar registros relacionados (en orden de dependencias)
       tables_to_clean = [
           ('Calificacion', ['ID_Usuario_Emisor', 'ID_Usuario_Receptor']),
           ('Mensaje', ['ID_Emisor', 'ID_Receptor']),
           ('Acuerdo_Laboral', ['ID_Trabajador']),
           ('Postulacion', ['ID_Trabajador']),
           ('Anexo', ['ID_Usuario']),
           ('Habilidad', ['ID_Trabajador']),
           ('Experiencia', ['ID_Trabajador']),
           ('Oferta_Trabajo', ['ID_Agricultor']),
           ('Predio', ['ID_Usuario'])
       ]
       
       for table_name, columns in tables_to_clean:
           try:
               if len(columns) == 1:
                   # Una sola columna de referencia
                   execute_query(f"DELETE FROM {table_name} WHERE {columns[0]} = %s", (user_id,))
               else:
                   # Múltiples columnas de referencia
                   conditions = ' OR '.join([f"{col} = %s" for col in columns])
                   params = [user_id] * len(columns)
                   execute_query(f"DELETE FROM {table_name} WHERE {conditions}", params)
                   
           except Exception as table_error:
               print(f"Error eliminando de {table_name}: {str(table_error)}")
               # Continuar con las otras tablas aunque falle una
               continue
       
       # Finalmente, eliminar el usuario
       execute_query("DELETE FROM Usuario WHERE ID_Usuario = %s", (user_id,))
       
       # Limpiar sesión
       session.clear()
       
       print(f"Cuenta eliminada completamente para usuario ID: {user_id}")
       
       return jsonify({
           'success': True,
           'message': 'Cuenta eliminada correctamente'
       })
       
   except Exception as e:
       print(f"Error eliminando cuenta: {str(e)}")
       return jsonify({'success': False, 'message': str(e)}), 500


@estatico_bp.route('/api/get-user-settings', methods=['GET'])
@require_login
def get_user_settings():
   """Obtener configuraciones del usuario desde tabla Usuario"""
   try:
       import json
       
       user_id = session['user_id']
       
       # Obtener configuraciones del usuario
       user = execute_query(
           "SELECT Configuraciones, Telefono FROM Usuario WHERE ID_Usuario = %s",
           (user_id,),
           fetch_one=True
       )
       
       if user and user.get('Configuraciones'):
           try:
               configuraciones = json.loads(user['Configuraciones'])
               
               return jsonify({
                   'success': True,
                   'settings': {
                       'notifications': configuraciones.get('notificaciones', {
                           'emailNotifications': True,
                           'emailUpdates': True,
                           'whatsappNotifications': False,
                           'whatsappUrgent': False
                       }),
                       'preferences': configuraciones.get('preferencias', {
                           'language': 'es',
                           'theme': 'light',
                           'timezone': 'America/Bogota'
                       }),
                       'whatsappNumber': user.get('Telefono', '')
                   }
               })
           except:
               # Si hay error parseando JSON, devolver configuración por defecto
               pass
       
       # Devolver configuración por defecto
       return jsonify({
           'success': True,
           'settings': {
               'notifications': {
                   'emailNotifications': True,
                   'emailUpdates': True,
                   'whatsappNotifications': False,
                   'whatsappUrgent': False
               },
               'preferences': {
                   'language': 'es',
                   'theme': 'light',
                   'timezone': 'America/Bogota'
               },
               'whatsappNumber': user.get('Telefono', '') if user else ''
           }
       })
           
   except Exception as e:
       print(f"Error obteniendo configuraciones: {str(e)}")
       return jsonify({'success': False, 'message': str(e)}), 500

# ================================================================
# SIMULACIÓN DE DATOS DE REDES SOCIALES
# ================================================================

# Usuarios simulados de Google (para demostración)
GOOGLE_USERS_DEMO = {
    "demo1": {
        "id": "google_123456",
        "email": "usuario.demo1@gmail.com",
        "given_name": "Juan",
        "family_name": "Pérez",
        "picture": "/static/uploads/profile_photos/default_google.jpg"
    },
    "demo2": {
        "id": "google_789012",
        "email": "maria.demo2@gmail.com",
        "given_name": "María",
        "family_name": "García",
        "picture": "/static/uploads/profile_photos/default_google2.jpg"
    }
}

# Usuarios simulados de Facebook (para demostración)
FACEBOOK_USERS_DEMO = {
    "demo1": {
        "id": "facebook_345678",
        "email": "usuario.demo1@outlook.com",
        "first_name": "Carlos",
        "last_name": "López",
        "picture": "/static/uploads/profile_photos/default_facebook.jpg"
    },
    "demo2": {
        "id": "facebook_901234",
        "email": "ana.demo2@hotmail.com",
        "first_name": "Ana",
        "last_name": "Martínez",
        "picture": "/static/uploads/profile_photos/default_facebook2.jpg"
    }
}

# ================================================================
# FUNCIONES AUXILIARES
# ================================================================

def generate_demo_password(email, provider):
    """Genera contraseña para usuarios demo"""
    combined = f"{email}_{provider}_{uuid.uuid4()}"
    return hashlib.sha256(combined.encode()).hexdigest()[:50]

def create_demo_user(user_data, provider, rol='Trabajador'):
    """Crea un usuario desde datos simulados"""
    try:
        # Hash de contraseña temporal
        from app import hash_password
        temp_password = hash_password(f"{user_data['email']}_social_{provider}")
        
        # Obtener nombres según el proveedor
        if provider == 'google':
            nombre = user_data.get('given_name', '')
            apellido = user_data.get('family_name', '')
        else:  # facebook
            nombre = user_data.get('first_name', '')
            apellido = user_data.get('last_name', '')
        
        # URL de foto por defecto
        foto_url = user_data.get('picture', f'/static/uploads/profile_photos/default_{provider}.jpg')
        
        # Insertar en base de datos
        user_id = execute_query(
            """INSERT INTO Usuario (Nombre, Apellido, Correo, Contrasena, URL_Foto, 
                                   Red_Social, Rol, Estado) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'Activo')""",
            (
                nombre,
                apellido,
                user_data['email'],
                temp_password,
                foto_url,
                f"{provider}:{user_data['id']}",
                rol
            )
        )
        
        print(f"Usuario demo creado desde {provider}: {user_data['email']}")
        return user_id
        
    except Exception as e:
        print(f"Error creando usuario demo: {str(e)}")
        return None


@estatico_bp.route('/vista/configuracion-trabajador.html')
def configuracion_trabajador_html():
    """Página de configuración del trabajador"""
    try:
        base_dir = PROJECT_ROOT  # auto-detected root
        vista_path = os.path.join(PROJECT_ROOT, 'vista')
        vista_path = os.path.abspath(vista_path)
        return send_from_directory(vista_path, 'configuracion-trabajador.html')
    except Exception as e:
        print(f"Error sirviendo configuracion-trabajador.html: {e}")
        return "Archivo no encontrado", 404


@estatico_bp.route('/vista/estadisticas-trabajador.html')
def estadisticas_trabajador_html():
    """Página de estadísticas del trabajador"""
    try:
        base_dir = PROJECT_ROOT  # auto-detected root
        vista_path = os.path.join(PROJECT_ROOT, 'vista')
        vista_path = os.path.abspath(vista_path)
        return send_from_directory(vista_path, 'estadisticas-trabajador.html')
    except Exception as e:
        print(f"Error sirviendo estadisticas-trabajador.html: {e}")
        return "Archivo no encontrado", 404


@estatico_bp.route('/vista/index-agricultor.html')
def index_agricultor_html():
    """Dashboard principal del agricultor"""
    try:
        base_dir = PROJECT_ROOT  # auto-detected root
        vista_path = os.path.join(PROJECT_ROOT, 'vista')
        vista_path = os.path.abspath(vista_path)
        return send_from_directory(vista_path, 'index-agricultor.html')
    except Exception as e:
        print(f"Error sirviendo index-agricultor.html: {e}")
        return "Archivo no encontrado", 404


@estatico_bp.route('/vista/index-trabajador.html')
def index_trabajador_html():
    """Dashboard principal del trabajador"""
    try:
        base_dir = PROJECT_ROOT  # auto-detected root
        vista_path = os.path.join(PROJECT_ROOT, 'vista')
        vista_path = os.path.abspath(vista_path)
        return send_from_directory(vista_path, 'index-trabajador.html')
    except Exception as e:
        print(f"Error sirviendo index-trabajador.html: {e}")
        return "Archivo no encontrado", 404


@estatico_bp.route('/vista/seleccion-rol.html')
def seleccion_rol_html():
    """Página de selección de rol"""
    try:
        base_dir = PROJECT_ROOT  # auto-detected root
        vista_path = os.path.join(PROJECT_ROOT, 'vista')
        vista_path = os.path.abspath(vista_path)
        return send_from_directory(vista_path, 'seleccion-rol.html')
    except Exception as e:
        print(f"Error sirviendo seleccion-rol.html: {e}")
        return "Archivo no encontrado", 404


@estatico_bp.route('/api/debug_postulaciones', methods=['GET'])
@require_login
def debug_postulaciones():
    """Debug para ver qué hay en la BD"""
    try:
        user_id = session['user_id']
        
        # Ver TODAS las postulaciones sin filtros
        todas = execute_query("""
            SELECT 
                p.ID_Postulacion,
                p.ID_Oferta,
                p.ID_Trabajador,
                p.Estado,
                p.Fecha_Postulacion,
                ot.Titulo
            FROM Postulacion p
            LEFT JOIN Oferta_Trabajo ot ON p.ID_Oferta = ot.ID_Oferta
            WHERE p.ID_Trabajador = %s
        """, (user_id,))
        
        # Ver favoritos específicamente
        favoritos = execute_query("""
            SELECT COUNT(*) as total
            FROM Postulacion 
            WHERE ID_Trabajador = %s AND Estado = 'Favorito'
        """, (user_id,), fetch_one=True)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'total_postulaciones': len(todas) if todas else 0,
            'total_favoritos': favoritos['total'] if favoritos else 0,
            'postulaciones': todas or [],
            'session_data': {
                'user_role': session.get('user_role'),
                'user_name': session.get('user_name')
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


@estatico_bp.route('/api/toggle-favorito', methods=['POST'])
@require_login
def toggle_favorito():
    """API para agregar/quitar favoritos desde el dashboard"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role')
        
        if user_role != 'Trabajador':
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
        
        data = request.get_json()
        oferta_id = data.get('job_id')  # Mantener compatibilidad con el frontend
        action = data.get('action')
        
        if not oferta_id or not action:
            return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
        
        # Verificar que la oferta existe
        oferta = execute_query("""
            SELECT 
                ot.ID_Oferta, 
                ot.Titulo, 
                ot.Estado,
                CONCAT(u.Nombre, ' ', u.Apellido) as Empleador
            FROM Oferta_Trabajo ot
            JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
            WHERE ot.ID_Oferta = %s
        """, (oferta_id,), fetch_one=True)
        
        if not oferta:
            return jsonify({'success': False, 'error': 'Oferta no encontrada'}), 404
        
        # Verificar si ya existe algún tipo de postulación
        postulacion_existente = execute_query("""
            SELECT ID_Postulacion, Estado FROM Postulacion 
            WHERE ID_Oferta = %s AND ID_Trabajador = %s
        """, (oferta_id, user_id), fetch_one=True)
        
        if action == 'add':
            if postulacion_existente:
                if postulacion_existente['Estado'] == 'Favorito':
                    # Ya es favorito
                    return jsonify({'success': False, 'error': 'Ya está en favoritos'}), 400
                else:
                    # Ya hay postulación activa, no se puede agregar como favorito
                    return jsonify({'success': False, 'error': 'Ya tienes una postulación activa para este trabajo'}), 400
            else:
                # Crear nueva entrada como favorito
                execute_query("""
                    INSERT INTO Postulacion (ID_Oferta, ID_Trabajador, Estado, Fecha_Postulacion)
                    VALUES (%s, %s, 'Favorito', CURRENT_TIMESTAMP)
                """, (oferta_id, user_id))
                
                message = f'"{oferta["Titulo"]}" agregado a favoritos'
        
        elif action == 'remove':
            if postulacion_existente and postulacion_existente['Estado'] == 'Favorito':
                # Eliminar favorito
                execute_query("""
                    DELETE FROM Postulacion 
                    WHERE ID_Postulacion = %s
                """, (postulacion_existente['ID_Postulacion'],))
                
                message = f'"{oferta["Titulo"]}" removido de favoritos'
            else:
                return jsonify({'success': False, 'error': 'No está en favoritos'}), 400
        
        else:
            return jsonify({'success': False, 'error': 'Acción no válida'}), 400
        
        return jsonify({
            'success': True,
            'message': message,
            'oferta_titulo': oferta['Titulo']
        })
        
    except Exception as e:
        print(f"Error manejando favorito: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# RUTAS ESPECÍFICAS PARA EL ADMINISTRADOR
# Agregar estas rutas a tu app.py existente
# ================================================================

# ================================================================
# RUTAS PARA ARCHIVOS DEL ADMINISTRADOR
# ================================================================

@estatico_bp.route('/vista/index-administrador.html')
def index_administrador_html():
    """Dashboard principal del administrador"""
    try:
        base_dir = PROJECT_ROOT  # auto-detected root
        vista_path = os.path.join(PROJECT_ROOT, 'vista')
        vista_path = os.path.abspath(vista_path)
        return send_from_directory(vista_path, 'index-administrador.html')
    except Exception as e:
        print(f"Error sirviendo index-administrador.html: {e}")
        return "Archivo no encontrado", 404


@estatico_bp.route('/assent/css/index-administrador.css')
def administrador_css():
    """CSS para el dashboard del administrador"""
    try:
        base_dir = PROJECT_ROOT  # auto-detected root
        css_path = os.path.join(PROJECT_ROOT, 'assent', 'css')
        css_path = os.path.abspath(css_path)
        response = send_from_directory(css_path, 'index-administrador.css')
        response.headers['Content-Type'] = 'text/css'
        return response
    except Exception as e:
        print(f"Error sirviendo index-administrador.css: {e}")
        return "CSS no encontrado", 404


@estatico_bp.route('/js/index-administrador.js')
def administrador_js():
    """JavaScript para el dashboard del administrador"""
    try:
        base_dir = PROJECT_ROOT  # auto-detected root
        js_path = os.path.join(PROJECT_ROOT, 'js')
        js_path = os.path.abspath(js_path)
        response = send_from_directory(js_path, 'index-administrador.js')
        response.headers['Content-Type'] = 'application/javascript'
        return response
    except Exception as e:
        print(f"Error sirviendo index-administrador.js: {e}")
        return "JS no encontrado", 404


# ================================================================
# ENDPOINT PARA VER POSTULACIONES DE UNA OFERTA (Para Agricultor)
# ================================================================
@estatico_bp.route('/api/get_offer_applications/<int:offer_id>', methods=['GET'])
@require_login
def get_offer_applications(offer_id):
    """Obtener todas las postulaciones de una oferta específica"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role')
        
        if user_role != 'Agricultor':
            return jsonify({'success': False, 'message': 'Solo agricultores pueden ver postulaciones'}), 403
        
        # Verificar que la oferta pertenece al agricultor
        oferta = execute_query("""
            SELECT ID_Agricultor, Titulo 
            FROM Oferta_Trabajo 
            WHERE ID_Oferta = %s
        """, (offer_id,), fetch_one=True)
        
        if not oferta or oferta['ID_Agricultor'] != user_id:
            return jsonify({'success': False, 'message': 'Oferta no encontrada o sin permisos'}), 404
        
        # Obtener postulaciones
        postulaciones = execute_query("""
            SELECT 
                p.ID_Postulacion,
                p.Fecha_Postulacion,
                p.Estado,
                u.ID_Usuario as trabajador_id,
                CONCAT(u.Nombre, ' ', u.Apellido) as nombre_completo,
                u.Telefono,
                u.Correo,
                u.URL_Foto,
                -- Estadísticas del trabajador
                (SELECT COUNT(*) FROM Acuerdo_Laboral al 
                 WHERE al.ID_Trabajador = u.ID_Usuario AND al.Estado = 'Finalizado') as trabajos_completados,
                (SELECT AVG(CAST(c.Puntuacion AS DECIMAL(3,2))) 
                 FROM Calificacion c 
                 WHERE c.ID_Usuario_Receptor = u.ID_Usuario) as calificacion_promedio
            FROM Postulacion p
            JOIN Usuario u ON p.ID_Trabajador = u.ID_Usuario
            WHERE p.ID_Oferta = %s
            ORDER BY p.Fecha_Postulacion DESC
        """, (offer_id,))
        
        postulaciones_list = []
        if postulaciones:
            for post in postulaciones:
                postulaciones_list.append({
                    'id_postulacion': post['ID_Postulacion'],
                    'trabajador_id': post['trabajador_id'],
                    'nombre_completo': post['nombre_completo'],
                    'telefono': post['Telefono'] or 'No disponible',
                    'email': post['Correo'],
                    'foto_url': post['URL_Foto'],
                    'fecha_postulacion': post['Fecha_Postulacion'].strftime('%Y-%m-%d %H:%M') if post['Fecha_Postulacion'] else None,
                    'estado': post['Estado'],
                    'trabajos_completados': post['trabajos_completados'] or 0,
                    'calificacion': float(post['calificacion_promedio']) if post['calificacion_promedio'] else 0.0
                })
        
        return jsonify({
            'success': True,
            'oferta_titulo': oferta['Titulo'],
            'postulaciones': postulaciones_list,
            'total': len(postulaciones_list)
        })
        
    except Exception as e:
        print(f"Error obteniendo postulaciones: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ================================================================
# ENDPOINT PARA ACEPTAR/RECHAZAR POSTULACIÓN
# ================================================================
@estatico_bp.route('/api/update_application_status/<int:postulacion_id>', methods=['PUT'])
def update_application_status(postulacion_id):
    """Actualizar estado de postulación y crear acuerdo laboral si se acepta"""
    print(f"🔵 FUNCIÓN LLAMADA - Postulación ID: {postulacion_id}")
    
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'}), 401
    
    data = request.get_json()
    nuevo_estado = data.get('estado')
    
    if nuevo_estado not in ['Aceptada', 'Rechazada']:
        return jsonify({'success': False, 'message': 'Estado inválido'}), 400
    
    try:
        # Usar tu conexión personalizada con context manager
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            
            # Obtener información de la postulación
            cursor.execute("""
                SELECT p.ID_Oferta, p.ID_Trabajador, ot.ID_Agricultor, ot.Pago_Ofrecido
                FROM Postulacion p
                INNER JOIN Oferta_Trabajo ot ON p.ID_Oferta = ot.ID_Oferta
                WHERE p.ID_Postulacion = %s
            """, (postulacion_id,))
            
            postulacion = cursor.fetchone()
            
            if not postulacion:
                return jsonify({'success': False, 'message': 'Postulación no encontrada'}), 404
            
            oferta_id = postulacion['ID_Oferta']
            trabajador_id = postulacion['ID_Trabajador']
            agricultor_id = postulacion['ID_Agricultor']
            pago_ofrecido = postulacion['Pago_Ofrecido']
            
            # Verificar autorización
            if agricultor_id != session['user_id']:
                return jsonify({'success': False, 'message': 'No autorizado'}), 403
            
            # Actualizar postulación
            cursor.execute("""
                UPDATE Postulacion 
                SET Estado = %s 
                WHERE ID_Postulacion = %s
            """, (nuevo_estado, postulacion_id))
            
            print(f"✅ Postulación {postulacion_id} actualizada a {nuevo_estado}")
            
            # Si se acepta, crear acuerdo laboral
            if nuevo_estado == 'Aceptada':
                # Verificar si ya existe
                cursor.execute("""
                    SELECT ID_Acuerdo 
                    FROM Acuerdo_Laboral 
                    WHERE ID_Oferta = %s AND ID_Trabajador = %s
                """, (oferta_id, trabajador_id))
                
                acuerdo_existe = cursor.fetchone()
                
                if not acuerdo_existe:
                    fecha_inicio = datetime.now().date()
                    
                    cursor.execute("""
                        INSERT INTO Acuerdo_Laboral 
                        (ID_Oferta, ID_Trabajador, Fecha_Inicio, Pago_Final, Estado)
                        VALUES (%s, %s, %s, %s, 'Activo')
                    """, (oferta_id, trabajador_id, fecha_inicio, pago_ofrecido))
                    
                    print(f"✅ Acuerdo laboral creado: Oferta {oferta_id} - Trabajador {trabajador_id}")
                    
                    # Actualizar oferta a "En Proceso"
                    cursor.execute("""
                        UPDATE Oferta_Trabajo 
                        SET Estado = 'En Proceso' 
                        WHERE ID_Oferta = %s
                    """, (oferta_id,))
                    
                    print(f"✅ Oferta {oferta_id} actualizada a 'En Proceso'")
                else:
                    print(f"⚠️ Ya existe acuerdo laboral")
            
            connection.commit()
            cursor.close()
        
        return jsonify({
            'success': True,
            'message': f'Postulación {nuevo_estado.lower()} exitosamente'
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@estatico_bp.route('/api/debug_session', methods=['GET'])
def debug_session():
    """Ver qué hay en la sesión - TEMPORAL PARA DEBUG"""
    return jsonify({
        'session_data': dict(session),
        'user_id': session.get('user_id'),
        'user_role': session.get('user_role'),
        'role': session.get('role'),
        'all_keys': list(session.keys())
    })


@estatico_bp.route('/api/debug_toggle_favorite', methods=['GET'])
@require_login
def debug_toggle_favorite():
    """Debug para favoritos"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role') or session.get('role')
        
        # Contar favoritos actuales
        favoritos = execute_query("""
            SELECT COUNT(*) as total
            FROM Postulacion 
            WHERE ID_Trabajador = %s AND Estado = 'Favorito'
        """, (user_id,), fetch_one=True)
        
        # Obtener algunos favoritos
        lista_favoritos = execute_query("""
            SELECT p.ID_Postulacion, p.ID_Oferta, ot.Titulo
            FROM Postulacion p
            JOIN Oferta_Trabajo ot ON p.ID_Oferta = ot.ID_Oferta
            WHERE p.ID_Trabajador = %s AND p.Estado = 'Favorito'
            LIMIT 5
        """, (user_id,))
        
        return jsonify({
            'success': True,
            'debug_info': {
                'user_id': user_id,
                'user_role': user_role,
                'session_data': dict(session),
                'total_favoritos': favoritos['total'] if favoritos else 0,
                'favoritos': lista_favoritos or []
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ================================================================
# ENDPOINT FAVORITOS - SOLUCIÓN DEFINITIVA
# ================================================================
@estatico_bp.route('/api/toggle_favorite', methods=['POST', 'OPTIONS'])
def api_toggle_favorite():
    """Toggle favorito - CORS habilitado"""
    
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
    
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No hay sesión activa'}), 401
        
        user_id = session['user_id']
        user_role = session.get('user_role') or session.get('role')
        
        print(f"DEBUG - User ID: {user_id}, Role: {user_role}")
        
        if user_role != 'Trabajador':
            return jsonify({'success': False, 'message': 'Solo trabajadores pueden usar favoritos'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
        
        job_id = data.get('job_id')
        action = data.get('action')
        
        print(f"DEBUG - Job ID: {job_id}, Action: {action}")
        
        if not job_id:
            return jsonify({'success': False, 'message': 'ID de trabajo requerido'}), 400
        
        if action == 'add':
            # Verificar si ya existe
            existe = execute_query("""
                SELECT ID_Postulacion FROM Postulacion 
                WHERE ID_Oferta = %s AND ID_Trabajador = %s
            """, (job_id, user_id), fetch_one=True)
            
            if existe:
                # Ya existe, actualizar a Favorito
                execute_query("""
                    UPDATE Postulacion 
                    SET Estado = 'Favorito', Fecha_Postulacion = NOW()
                    WHERE ID_Postulacion = %s
                """, (existe['ID_Postulacion'],))
                print(f"DEBUG - Actualizado a Favorito: {existe['ID_Postulacion']}")
            else:
                # No existe, crear nuevo
                execute_query("""
                    INSERT INTO Postulacion (ID_Oferta, ID_Trabajador, Estado, Fecha_Postulacion)
                    VALUES (%s, %s, 'Favorito', NOW())
                """, (job_id, user_id))
                print(f"DEBUG - Nuevo favorito creado")
            
            return jsonify({'success': True, 'message': 'Agregado a favoritos', 'is_favorite': True})
        
        elif action == 'remove':
            execute_query("""
                DELETE FROM Postulacion 
                WHERE ID_Oferta = %s AND ID_Trabajador = %s AND Estado = 'Favorito'
            """, (job_id, user_id))
            print(f"DEBUG - Favorito eliminado")
            
            return jsonify({'success': True, 'message': 'Removido de favoritos', 'is_favorite': False})
        
        return jsonify({'success': False, 'message': 'Acción no válida'}), 400
        
    except Exception as e:
        print(f"ERROR toggle_favorite: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@estatico_bp.route('/api/estadisticas_agricultor', methods=['GET'])
def api_estadisticas_agricultor():
    """Obtener estadísticas completas del agricultor"""
    print("🔍 Request: GET /api/estadisticas_agricultor")
    
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'}), 401
    
    user_id = session['user_id']
    periodo = request.args.get('periodo', 'all')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Calcular filtro de fecha
        where_fecha_ofertas = ""
        where_fecha_acuerdos = ""
        
        if periodo == 'month':
            where_fecha_ofertas = "AND ot.Fecha_Publicacion >= DATE_SUB(NOW(), INTERVAL 1 MONTH)"
            where_fecha_acuerdos = "AND al.Fecha_Inicio >= DATE_SUB(NOW(), INTERVAL 1 MONTH)"
        elif periodo == 'quarter':
            where_fecha_ofertas = "AND ot.Fecha_Publicacion >= DATE_SUB(NOW(), INTERVAL 3 MONTH)"
            where_fecha_acuerdos = "AND al.Fecha_Inicio >= DATE_SUB(NOW(), INTERVAL 3 MONTH)"
        elif periodo == 'year':
            where_fecha_ofertas = "AND ot.Fecha_Publicacion >= DATE_SUB(NOW(), INTERVAL 1 YEAR)"
            where_fecha_acuerdos = "AND al.Fecha_Inicio >= DATE_SUB(NOW(), INTERVAL 1 YEAR)"
        
        # 1. RESUMEN
        cursor.execute(f"SELECT COUNT(*) as total FROM Oferta_Trabajo ot WHERE ot.ID_Agricultor = %s {where_fecha_ofertas}", (user_id,))
        total_ofertas = cursor.fetchone()['total']
        
        cursor.execute(f"""
            SELECT COUNT(DISTINCT al.ID_Acuerdo) as total
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            WHERE ot.ID_Agricultor = %s {where_fecha_acuerdos}
        """, (user_id,))
        total_contrataciones = cursor.fetchone()['total']
        
        cursor.execute(f"""
            SELECT COALESCE(SUM(al.Pago_Final), 0) as total
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            WHERE ot.ID_Agricultor = %s
            AND al.Estado = 'Finalizado'
            AND al.Pago_Final IS NOT NULL
            {where_fecha_acuerdos}
        """, (user_id,))
        total_inversion = cursor.fetchone()['total']
        
        cursor.execute(f"""
            SELECT COALESCE(AVG(CAST(c.Puntuacion AS UNSIGNED)), 0) as promedio
            FROM Calificacion c
            INNER JOIN Acuerdo_Laboral al ON c.ID_Acuerdo = al.ID_Acuerdo
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            WHERE ot.ID_Agricultor = %s
            AND c.ID_Usuario_Emisor = %s
            {where_fecha_acuerdos}
        """, (user_id, user_id))
        calificacion_promedio = cursor.fetchone()['promedio']
        
        # 2. INVERSIÓN MENSUAL
        cursor.execute("""
            SELECT 
                DATE_FORMAT(al.Fecha_Inicio, '%b') as mes,
                COALESCE(SUM(al.Pago_Final), 0) as inversion
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            WHERE ot.ID_Agricultor = %s
            AND al.Estado = 'Finalizado'
            AND al.Fecha_Inicio >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY YEAR(al.Fecha_Inicio), MONTH(al.Fecha_Inicio), DATE_FORMAT(al.Fecha_Inicio, '%b')
            ORDER BY YEAR(al.Fecha_Inicio), MONTH(al.Fecha_Inicio)
        """, (user_id,))
        inversion_mensual = cursor.fetchall()
        
        # 3. OFERTAS POR ESTADO
        cursor.execute(f"""
            SELECT 
                Estado as estado,
                COUNT(*) as cantidad
            FROM Oferta_Trabajo
            WHERE ID_Agricultor = %s {where_fecha_ofertas}
            GROUP BY Estado
        """, (user_id,))
        ofertas_por_estado = cursor.fetchall()
        
        # 4. CONTRATACIONES MENSUALES
        cursor.execute("""
            SELECT 
                DATE_FORMAT(al.Fecha_Inicio, '%b') as mes,
                COUNT(*) as contrataciones
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            WHERE ot.ID_Agricultor = %s
            AND al.Fecha_Inicio >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY YEAR(al.Fecha_Inicio), MONTH(al.Fecha_Inicio), DATE_FORMAT(al.Fecha_Inicio, '%b')
            ORDER BY YEAR(al.Fecha_Inicio), MONTH(al.Fecha_Inicio)
        """, (user_id,))
        contrataciones_mensuales = cursor.fetchall()
        
        # 5. TRABAJADORES MÁS CONTRATADOS
        cursor.execute(f"""
            SELECT 
                CONCAT(u.Nombre, ' ', u.Apellido) as nombre,
                COUNT(*) as contrataciones
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            INNER JOIN Usuario u ON al.ID_Trabajador = u.ID_Usuario
            WHERE ot.ID_Agricultor = %s {where_fecha_acuerdos}
            GROUP BY al.ID_Trabajador, u.Nombre, u.Apellido
            ORDER BY contrataciones DESC
            LIMIT 5
        """, (user_id,))
        trabajadores_frecuentes = cursor.fetchall()
        
        # 6. OFERTAS RECIENTES
        cursor.execute(f"""
            SELECT 
                ot.Titulo as titulo,
                'Sin ubicación' as ubicacion,
                ot.Estado as estado,
                ot.Pago_Ofrecido as pago,
                (SELECT COUNT(*) FROM Postulacion p WHERE p.ID_Oferta = ot.ID_Oferta) as postulaciones
            FROM Oferta_Trabajo ot
            WHERE ot.ID_Agricultor = %s {where_fecha_ofertas}
            ORDER BY ot.Fecha_Publicacion DESC
            LIMIT 5
        """, (user_id,))
        ofertas_recientes = cursor.fetchall()
        
        # 7. TOP TRABAJADORES
        cursor.execute(f"""
            SELECT 
                CONCAT(u.Nombre, ' ', u.Apellido) as nombre,
                COUNT(DISTINCT al.ID_Acuerdo) as trabajos,
                COALESCE(AVG(CAST(c.Puntuacion AS UNSIGNED)), 0) as calificacion
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            INNER JOIN Usuario u ON al.ID_Trabajador = u.ID_Usuario
            LEFT JOIN Calificacion c ON al.ID_Acuerdo = c.ID_Acuerdo 
                AND c.ID_Usuario_Receptor = al.ID_Trabajador
            WHERE ot.ID_Agricultor = %s {where_fecha_acuerdos}
            GROUP BY al.ID_Trabajador, u.Nombre, u.Apellido
            HAVING trabajos > 0
            ORDER BY calificacion DESC, trabajos DESC
            LIMIT 5
        """, (user_id,))
        top_trabajadores = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Construir respuesta
        estadisticas = {
            'resumen': {
                'totalOfertas': int(total_ofertas or 0),
                'totalContrataciones': int(total_contrataciones or 0),
                'totalInversion': float(total_inversion or 0),
                'calificacionPromedio': round(float(calificacion_promedio or 0), 1)
            },
            'inversionMensual': inversion_mensual or [],
            'ofertasPorEstado': ofertas_por_estado or [],
            'contratacionesMensuales': contrataciones_mensuales or [],
            'trabajadoresFrecuentes': trabajadores_frecuentes or [],
            'ofertasRecientes': ofertas_recientes or [],
            'topTrabajadores': top_trabajadores or []
        }
        
        print(f"✅ Estadísticas agricultor: {estadisticas['resumen']}")
        
        return jsonify({'success': True, 'estadisticas': estadisticas})
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@estatico_bp.route('/api/estadisticas_trabajador', methods=['GET'])
def api_estadisticas_trabajador():
    """Obtener estadísticas completas del trabajador"""
    print("🔍 Request: GET /api/estadisticas_trabajador")
    
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'}), 401
    
    user_id = session['user_id']
    periodo = request.args.get('periodo', 'all')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Calcular filtro de fecha
        where_fecha = ""
        if periodo == 'month':
            where_fecha = "AND al.Fecha_Fin >= DATE_SUB(NOW(), INTERVAL 1 MONTH)"
        elif periodo == 'quarter':
            where_fecha = "AND al.Fecha_Fin >= DATE_SUB(NOW(), INTERVAL 3 MONTH)"
        elif periodo == 'year':
            where_fecha = "AND al.Fecha_Fin >= DATE_SUB(NOW(), INTERVAL 1 YEAR)"
        
        # 1. RESUMEN
        cursor.execute(f"""
            SELECT COUNT(DISTINCT ID_Acuerdo) as total
            FROM Acuerdo_Laboral
            WHERE ID_Trabajador = %s
            AND Estado = 'Finalizado'
            {where_fecha}
        """, (user_id,))
        total_trabajos = cursor.fetchone()['total']
        
        cursor.execute(f"""
            SELECT COALESCE(SUM(DATEDIFF(Fecha_Fin, Fecha_Inicio)), 0) as total_dias
            FROM Acuerdo_Laboral
            WHERE ID_Trabajador = %s
            AND Estado = 'Finalizado'
            AND Fecha_Fin IS NOT NULL
            {where_fecha}
        """, (user_id,))
        total_dias = cursor.fetchone()['total_dias']
        total_horas = int(total_dias * 8)
        
        cursor.execute(f"""
            SELECT COALESCE(SUM(Pago_Final), 0) as total
            FROM Acuerdo_Laboral
            WHERE ID_Trabajador = %s
            AND Estado = 'Finalizado'
            AND Pago_Final IS NOT NULL
            {where_fecha}
        """, (user_id,))
        total_ingresos = cursor.fetchone()['total']
        
        cursor.execute(f"""
            SELECT COALESCE(AVG(CAST(Puntuacion AS UNSIGNED)), 0) as promedio
            FROM Calificacion
            WHERE ID_Usuario_Receptor = %s
            {where_fecha.replace('al.Fecha_Fin', 'Fecha')}
        """, (user_id,))
        calificacion_promedio = cursor.fetchone()['promedio']
        
        # 2. INGRESOS MENSUALES
        cursor.execute("""
            SELECT 
                DATE_FORMAT(Fecha_Fin, '%b') as mes,
                COALESCE(SUM(Pago_Final), 0) as ingresos
            FROM Acuerdo_Laboral
            WHERE ID_Trabajador = %s
            AND Estado = 'Finalizado'
            AND Fecha_Fin >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY YEAR(Fecha_Fin), MONTH(Fecha_Fin), DATE_FORMAT(Fecha_Fin, '%b')
            ORDER BY YEAR(Fecha_Fin), MONTH(Fecha_Fin)
        """, (user_id,))
        ingresos_mensuales = cursor.fetchall()
        
        # 3. TRABAJOS POR TIPO
        cursor.execute(f"""
            SELECT 
                SUBSTRING_INDEX(ot.Titulo, ' ', 1) as tipo,
                COUNT(*) as cantidad
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            WHERE al.ID_Trabajador = %s
            AND al.Estado = 'Finalizado'
            {where_fecha}
            GROUP BY tipo
            ORDER BY cantidad DESC
            LIMIT 5
        """, (user_id,))
        trabajos_por_tipo = cursor.fetchall()
        
        # 4. HORAS MENSUALES
        cursor.execute("""
            SELECT 
                DATE_FORMAT(Fecha_Fin, '%b') as mes,
                COALESCE(SUM(DATEDIFF(Fecha_Fin, Fecha_Inicio) * 8), 0) as horas
            FROM Acuerdo_Laboral
            WHERE ID_Trabajador = %s
            AND Estado = 'Finalizado'
            AND Fecha_Fin >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY YEAR(Fecha_Fin), MONTH(Fecha_Fin), DATE_FORMAT(Fecha_Fin, '%b')
            ORDER BY YEAR(Fecha_Fin), MONTH(Fecha_Fin)
        """, (user_id,))
        horas_mensuales = cursor.fetchall()
        
        # 5. CALIFICACIONES POR MES
        cursor.execute("""
            SELECT 
                DATE_FORMAT(Fecha, '%b') as mes,
                COALESCE(AVG(CAST(Puntuacion AS UNSIGNED)), 0) as calificacion
            FROM Calificacion
            WHERE ID_Usuario_Receptor = %s
            AND Fecha >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY YEAR(Fecha), MONTH(Fecha), DATE_FORMAT(Fecha, '%b')
            ORDER BY YEAR(Fecha), MONTH(Fecha)
        """, (user_id,))
        calificaciones_por_mes = cursor.fetchall()
        
        # 6. TRABAJOS RECIENTES
        cursor.execute(f"""
            SELECT 
                ot.Titulo as titulo,
                CONCAT(u.Nombre, ' ', u.Apellido) as agricultor,
                al.Fecha_Fin as fechaFin,
                al.Pago_Final as pago,
                (SELECT Puntuacion FROM Calificacion c 
                 WHERE c.ID_Acuerdo = al.ID_Acuerdo 
                 AND c.ID_Usuario_Receptor = %s LIMIT 1) as calificacion
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            INNER JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
            WHERE al.ID_Trabajador = %s
            AND al.Estado = 'Finalizado'
            {where_fecha}
            ORDER BY al.Fecha_Fin DESC
            LIMIT 5
        """, (user_id, user_id))
        trabajos_recientes = cursor.fetchall()
        
        # 7. HABILIDADES
        cursor.execute("""
            SELECT 
                Nombre as nombre,
                Clasificacion as clasificacion
            FROM Habilidad
            WHERE ID_Trabajador = %s
        """, (user_id,))
        habilidades = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Construir respuesta
        estadisticas = {
            'resumen': {
                'totalTrabajos': int(total_trabajos or 0),
                'totalHoras': int(total_horas or 0),
                'totalIngresos': float(total_ingresos or 0),
                'calificacionPromedio': round(float(calificacion_promedio or 0), 1)
            },
            'ingresosMensuales': ingresos_mensuales or [],
            'trabajosPorTipo': trabajos_por_tipo or [],
            'horasMensuales': horas_mensuales or [],
            'calificacionesPorMes': calificaciones_por_mes or [],
            'trabajosRecientes': trabajos_recientes or [],
            'habilidades': habilidades or []
        }
        
        print(f"✅ Estadísticas trabajador: {estadisticas['resumen']}")
        
        return jsonify({'success': True, 'estadisticas': estadisticas})
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ================================================================
# ENDPOINT: ACTUALIZAR IDIOMA
# ================================================================
@estatico_bp.route('/api/update-language', methods=['POST'])
def update_language():
    """Actualiza el idioma preferido del usuario"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        data = request.get_json()
        language = data.get('language', 'es')
        user_id = session['user_id']
        
        # Validar idioma
        valid_languages = ['es', 'en', 'zh']
        if language not in valid_languages:
            language = 'es'
        
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="camp"
        )
        cursor = conexion.cursor(dictionary=True)
        
        # Actualizar idioma en la base de datos
        # Primero verificamos si existe la columna idioma en la tabla usuarios
        cursor.execute("SHOW COLUMNS FROM usuarios LIKE 'idioma'")
        column_exists = cursor.fetchone()
        
        if not column_exists:
            # Si no existe la columna, la creamos
            cursor.execute("ALTER TABLE usuarios ADD COLUMN idioma VARCHAR(5) DEFAULT 'es'")
            conexion.commit()
        
        # Actualizar el idioma del usuario
        query = "UPDATE usuarios SET idioma = %s WHERE id_usuario = %s"
        cursor.execute(query, (language, user_id))
        conexion.commit()
        
        # Guardar en sesión
        session['user_language'] = language
        
        cursor.close()
        conexion.close()
        
        print(f"✅ Idioma actualizado a '{language}' para usuario ID: {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Idioma actualizado correctamente',
            'language': language
        })
        
    except Exception as e:
        print(f"❌ Error actualizando idioma: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


# ================================================================
# ENDPOINT: OBTENER CONFIGURACIONES DEL USUARIO (ACTUALIZADO)
# ================================================================
@estatico_bp.route('/api/get-user-settings', methods=['GET'])
def get_user_settings_updated():
    """Obtiene todas las configuraciones del usuario incluyendo idioma y disponibilidad"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        user_id = session['user_id']
        
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="camp"
        )
        cursor = conexion.cursor(dictionary=True)
        
        # Obtener idioma del usuario
        cursor.execute("SELECT idioma FROM usuarios WHERE id_usuario = %s", (user_id,))
        user_data = cursor.fetchone()
        language = user_data.get('idioma', 'es') if user_data else 'es'
        
        # Obtener disponibilidad
        cursor.execute("""
            SELECT disponible, dias_disponibles, hora_inicio, hora_fin, 
                   fechas_no_disponibles
            FROM disponibilidad_trabajador
            WHERE id_usuario = %s
        """, (user_id,))
        availability = cursor.fetchone()
        
        # Obtener otras configuraciones (notificaciones, etc.)
        cursor.execute("""
            SELECT configuraciones 
            FROM usuarios 
            WHERE id_usuario = %s
        """, (user_id,))
        config_data = cursor.fetchone()
        
        cursor.close()
        conexion.close()
        
        # Preparar respuesta
        settings = {
            'language': language,
            'availability': None,
            'notifications': {
                'emailNotifications': True,
                'emailUpdates': True
            }
        }
        
        # Agregar disponibilidad si existe
        if availability:
            settings['availability'] = {
                'available': availability['disponible'],
                'days': json.loads(availability['dias_disponibles']) if availability['dias_disponibles'] else [],
                'startTime': str(availability['hora_inicio']) if availability['hora_inicio'] else '08:00',
                'endTime': str(availability['hora_fin']) if availability['hora_fin'] else '18:00',
                'unavailableDates': json.loads(availability['fechas_no_disponibles']) if availability['fechas_no_disponibles'] else []
            }
        
        # Agregar otras configuraciones si existen
        if config_data and config_data.get('configuraciones'):
            try:
                other_settings = json.loads(config_data['configuraciones'])
                if 'notifications' in other_settings:
                    settings['notifications'] = other_settings['notifications']
            except:
                pass
        
        return jsonify({
            'success': True,
            'settings': settings
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo configuraciones: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


# ENDPOINT 1: ACTUALIZAR IDIOMA (nombre único)
@estatico_bp.route('/api/actualizar-idioma-usuario', methods=['POST'])
def actualizar_idioma_usuario():
    """Actualiza el idioma del usuario en la base de datos"""
    try:
        # Verificar autenticación
        if 'user_id' not in session:
            return jsonify({
                'success': False, 
                'message': 'No autenticado'
            }), 401
        
        # Obtener datos
        data = request.get_json()
        language = data.get('language', 'es')
        user_id = session['user_id']
        
        # Validar idioma
        valid_languages = ['es', 'en', 'zh']
        if language not in valid_languages:
            language = 'es'
        
        # Conectar a la base de datos
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="camp"  # Nombre correcto de tu base de datos
        )
        cursor = conexion.cursor(dictionary=True)
        
        # Verificar si existe la columna Idioma
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'camp' 
            AND TABLE_NAME = 'Usuario' 
            AND COLUMN_NAME = 'Idioma'
        """)
        column_exists = cursor.fetchone()
        
        # Si no existe la columna, crearla
        if not column_exists:
            print("⚠️ Columna 'Idioma' no existe, creándola...")
            cursor.execute("""
                ALTER TABLE Usuario 
                ADD COLUMN Idioma VARCHAR(5) DEFAULT 'es' 
                AFTER Red_Social
            """)
            conexion.commit()
            print("✅ Columna 'Idioma' creada exitosamente")
        
        # Actualizar el idioma del usuario
        query = """
            UPDATE Usuario 
            SET Idioma = %s 
            WHERE ID_Usuario = %s
        """
        cursor.execute(query, (language, user_id))
        conexion.commit()
        
        # Verificar que se actualizó
        rows_affected = cursor.rowcount
        
        # Guardar en sesión
        session['user_language'] = language
        
        cursor.close()
        conexion.close()
        
        print(f"✅ Idioma actualizado exitosamente:")
        print(f"   - Usuario ID: {user_id}")
        print(f"   - Nuevo idioma: {language}")
        print(f"   - Filas afectadas: {rows_affected}")
        
        return jsonify({
            'success': True,
            'message': 'Idioma actualizado correctamente',
            'language': language,
            'user_id': user_id
        })
        
    except mysql.connector.Error as db_error:
        print(f"❌ Error de base de datos: {str(db_error)}")
        return jsonify({
            'success': False,
            'message': f'Error de base de datos: {str(db_error)}'
        }), 500
        
    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


# ENDPOINT 4: OBTENER CONFIGURACIONES (nombre único)
@estatico_bp.route('/api/obtener-configuraciones-usuario', methods=['GET'])
def obtener_configuraciones_usuario():
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        user_id = session['user_id']
        
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="camp"
        )
        cursor = conexion.cursor(dictionary=True)
        
        cursor.execute("SELECT Idioma FROM Usuario WHERE ID_Usuario = %s", (user_id,))
        user_data = cursor.fetchone()
        language = user_data.get('Idioma', 'es') if user_data else 'es'
        
        cursor.execute("""
            SELECT Disponible, Visibilidad, Dias_Disponibles, Hora_Inicio, Hora_Fin, 
                   Fechas_No_Disponibles
            FROM disponibilidad_trabajador
            WHERE ID_Usuario = %s
        """, (user_id,))
        availability = cursor.fetchone()
        
        cursor.close()
        conexion.close()
        
        settings = {
            'language': language,
            'availability': None,
            'notifications': {
                'emailNotifications': True,
                'emailUpdates': True
            }
        }
        
        if availability:
            settings['availability'] = {
                'available': availability['Disponible'],
                'visibility': availability['Visibilidad'],
                'days': json.loads(availability['Dias_Disponibles']) if availability['Dias_Disponibles'] else [],
                'startTime': str(availability['Hora_Inicio']) if availability['Hora_Inicio'] else '08:00',
                'endTime': str(availability['Hora_Fin']) if availability['Hora_Fin'] else '18:00',
                'unavailableDates': json.loads(availability['Fechas_No_Disponibles']) if availability['Fechas_No_Disponibles'] else []
            }
        
        return jsonify({'success': True, 'settings': settings})
        
    except Exception as e:
        print(f"❌ Error obteniendo configuraciones: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


# ================================================================
# ENDPOINT 1: Obtener ofertas cercanas con ubicación para TRABAJADORES
# ================================================================
@estatico_bp.route('/api/get_nearby_jobs', methods=['POST'])
@require_login
def get_nearby_jobs():
    """Obtener ofertas de trabajo cercanas según la ubicación del trabajador"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role')
        
        if user_role != 'Trabajador':
            return jsonify({'success': False, 'error': 'Solo trabajadores'}), 403
        
        data = request.get_json()
        user_lat = data.get('latitude')
        user_lon = data.get('longitude')
        radio_km = data.get('radius', 50)  # Radio por defecto: 50km
        
        if not user_lat or not user_lon:
            return jsonify({'success': False, 'error': 'Ubicación requerida'}), 400
        
        # Obtener ofertas activas con ubicación del predio
        ofertas = execute_query("""
            SELECT 
                ot.ID_Oferta,
                ot.Titulo,
                ot.Descripcion,
                ot.Pago_Ofrecido,
                ot.Fecha_Publicacion,
                ot.Estado,
                CONCAT(u.Nombre, ' ', u.Apellido) as Agricultor,
                u.ID_Usuario as ID_Agricultor,
                pr.Ubicacion_Latitud,
                pr.Ubicacion_Longitud,
                pr.Nombre_Finca
            FROM Oferta_Trabajo ot
            INNER JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
            LEFT JOIN Predio pr ON u.ID_Usuario = pr.ID_Usuario
            WHERE ot.Estado = 'Abierta'
              AND ot.ID_Agricultor != %s
              AND pr.Ubicacion_Latitud IS NOT NULL
              AND pr.Ubicacion_Longitud IS NOT NULL
            ORDER BY ot.Fecha_Publicacion DESC
        """, (user_id,))
        
        # Filtrar por distancia y agregar datos
        ofertas_cercanas = []
        for oferta in ofertas:
            if oferta['Ubicacion_Latitud'] and oferta['Ubicacion_Longitud']:
                distancia = calcular_distancia(
                    float(user_lat), float(user_lon),
                    float(oferta['Ubicacion_Latitud']), 
                    float(oferta['Ubicacion_Longitud'])
                )
                
                if distancia <= radio_km:
                    ofertas_cercanas.append({
                        'id': oferta['ID_Oferta'],
                        'titulo': oferta['Titulo'],
                        'descripcion': oferta['Descripcion'][:150] + '...' if len(oferta['Descripcion']) > 150 else oferta['Descripcion'],
                        'pago': float(oferta['Pago_Ofrecido']),
                        'agricultor': oferta['Agricultor'],
                        'id_agricultor': oferta['ID_Agricultor'],
                        'ubicacion': oferta['Nombre_Finca'],
                        'lat': float(oferta['Ubicacion_Latitud']),
                        'lng': float(oferta['Ubicacion_Longitud']),
                        'distancia': round(distancia, 2),
                        'fecha': oferta['Fecha_Publicacion'].isoformat() if oferta['Fecha_Publicacion'] else None
                    })
        
        # Ordenar por distancia
        ofertas_cercanas.sort(key=lambda x: x['distancia'])
        
        return jsonify({
            'success': True,
            'ofertas': ofertas_cercanas,
            'total': len(ofertas_cercanas),
            'user_location': {
                'lat': float(user_lat),
                'lng': float(user_lon)
            }
        })
        
    except Exception as e:
        print(f"Error obteniendo ofertas cercanas: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# ENDPOINT 2: Obtener trabajadores cercanos para AGRICULTORES
# ================================================================
@estatico_bp.route('/api/get_nearby_workers', methods=['POST'])
@require_login
def get_nearby_workers():
    """Obtener trabajadores disponibles cercanos según la ubicación del agricultor"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role')
        
        if user_role != 'Agricultor':
            return jsonify({'success': False, 'error': 'Solo agricultores'}), 403
        
        data = request.get_json()
        user_lat = data.get('latitude')
        user_lon = data.get('longitude')
        radio_km = data.get('radius', 50)
        
        if not user_lat or not user_lon:
            return jsonify({'success': False, 'error': 'Ubicación requerida'}), 400
        
        # Obtener trabajadores con su última ubicación registrada
        # (Nota: necesitas almacenar la ubicación del trabajador en alguna tabla)
        trabajadores = execute_query("""
            SELECT 
                u.ID_Usuario,
                u.Nombre,
                u.Apellido,
                u.Telefono,
                u.URL_Foto,
                COUNT(DISTINCT al.ID_Acuerdo) as trabajos_completados,
                AVG(CAST(c.Puntuacion AS DECIMAL)) as calificacion_promedio,
                GROUP_CONCAT(DISTINCT h.Nombre SEPARATOR ', ') as habilidades,
                -- Aquí necesitamos obtener la ubicación del trabajador
                -- Por ahora usaremos ubicaciones aleatorias cerca de Bogotá
                4.7110 + (RAND() * 0.2 - 0.1) as Latitud,
                -74.0721 + (RAND() * 0.2 - 0.1) as Longitud
            FROM Usuario u
            LEFT JOIN Acuerdo_Laboral al ON u.ID_Usuario = al.ID_Trabajador AND al.Estado = 'Finalizado'
            LEFT JOIN Calificacion c ON u.ID_Usuario = c.ID_Usuario_Receptor
            LEFT JOIN Habilidad h ON u.ID_Usuario = h.ID_Trabajador
            WHERE u.Rol = 'Trabajador'
              AND u.Estado = 'Activo'
              AND u.ID_Usuario != %s
            GROUP BY u.ID_Usuario, u.Nombre, u.Apellido, u.Telefono, u.URL_Foto
            LIMIT 50
        """, (user_id,))
        
        # Filtrar por distancia
        trabajadores_cercanos = []
        for trabajador in trabajadores:
            distancia = calcular_distancia(
                float(user_lat), float(user_lon),
                float(trabajador['Latitud']), 
                float(trabajador['Longitud'])
            )
            
            if distancia <= radio_km:
                trabajadores_cercanos.append({
                    'id': trabajador['ID_Usuario'],
                    'nombre': f"{trabajador['Nombre']} {trabajador['Apellido']}",
                    'telefono': trabajador.get('Telefono', ''),
                    'foto': trabajador.get('URL_Foto'),
                    'trabajos': trabajador['trabajos_completados'] or 0,
                    'calificacion': float(trabajador['calificacion_promedio']) if trabajador['calificacion_promedio'] else 0,
                    'habilidades': trabajador['habilidades'].split(', ') if trabajador['habilidades'] else [],
                    'lat': float(trabajador['Latitud']),
                    'lng': float(trabajador['Longitud']),
                    'distancia': round(distancia, 2)
                })
        
        # Ordenar por calificación y distancia
        trabajadores_cercanos.sort(key=lambda x: (-x['calificacion'], x['distancia']))
        
        return jsonify({
            'success': True,
            'trabajadores': trabajadores_cercanos,
            'total': len(trabajadores_cercanos),
            'user_location': {
                'lat': float(user_lat),
                'lng': float(user_lon)
            }
        })
        
    except Exception as e:
        print(f"Error obteniendo trabajadores cercanos: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@estatico_bp.route('/api/request-password-reset', methods=['POST'])
def request_password_reset():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'success': False, 'message': 'Email requerido'}), 400
        
        user = execute_query(
            "SELECT ID_Usuario, Nombre, Apellido, Correo, Estado FROM Usuario WHERE Correo = %s",
            (email,), fetch_one=True
        )
        
        if not user or user['Estado'] != 'Activo':
            return jsonify({
                'success': True,
                'message': 'Si el correo existe, recibirás un enlace'
            })
        
        reset_token = secrets.token_urlsafe(32)
        expiration_time = datetime.now() + timedelta(minutes=30)
        
        password_reset_tokens[reset_token] = {
            'user_id': user['ID_Usuario'],
            'email': email,
            'expires_at': expiration_time,
            'used': False
        }
        
        reset_link = f"http://localhost:5000/reset-password?token={reset_token}"
        user_name = f"{user['Nombre']} {user['Apellido']}"
        email_html = get_password_reset_email_template(user_name, reset_link)
        
        send_email(email, '🔐 Recuperación de Contraseña - CAMP', email_html)
        
        print(f"✅ Token: {reset_token}")
        
        return jsonify({
            'success': True,
            'message': 'Te hemos enviado un correo con instrucciones'
        })
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'success': False, 'message': 'Error interno'}), 500


# ===================================================================
# ENDPOINT PARA CANCELAR POSTULACIÓN
# ===================================================================
@estatico_bp.route('/api/cancel_application/<int:application_id>', methods=['DELETE'])
def cancel_application(application_id):
    """Cancelar una postulación del trabajador"""
    try:
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'message': 'Sesión no válida'
            }), 401
        
        user_id = session['user_id']
        user_role = session.get('user_role') or session.get('role')
        
        if user_role != 'Trabajador':
            return jsonify({
                'success': False,
                'message': 'Solo los trabajadores pueden cancelar postulaciones'
            }), 403
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Verificar que la postulación existe y pertenece al usuario
        check_query = """
        SELECT ID_Postulacion, Estado 
        FROM Postulacion 
        WHERE ID_Postulacion = %s AND ID_Trabajador = %s
        """
        cursor.execute(check_query, (application_id, user_id))
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            connection.close()
            return jsonify({
                'success': False,
                'message': 'Postulación no encontrada'
            }), 404
        
        # Verificar que la postulación esté en estado Pendiente
        if result[1] != 'Pendiente':
            cursor.close()
            connection.close()
            return jsonify({
                'success': False,
                'message': f'No se puede cancelar una postulación en estado {result[1]}'
            }), 400
        
        # Eliminar la postulación
        delete_query = "DELETE FROM Postulacion WHERE ID_Postulacion = %s"
        cursor.execute(delete_query, (application_id,))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print(f"✅ Postulación {application_id} cancelada por usuario {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Postulación cancelada exitosamente'
        }), 200
        
    except Exception as e:
        print(f"❌ Error cancelando postulación: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno del servidor: {str(e)}'
        }), 500

