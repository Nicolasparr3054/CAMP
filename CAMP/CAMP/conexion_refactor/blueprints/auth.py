# Blueprint: auth
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

def no_cache(view):
    @wraps(view)
    def no_cache_view(*args, **kwargs):
        from flask import make_response
        response = make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
    return no_cache_view

auth_bp = Blueprint('auth', __name__)
from blueprints.helpers import require_login, require_role, hash_password, verify_password, no_cache


# NUEVAS RUTAS PARA DASHBOARD DE TRABAJADOR
@auth_bp.route('/dashboard-trabajador.css')
def serve_dashboard_trabajador_css():
    """Sirve el archivo dashboard-trabajador.css"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vista_path = os.path.join(base_dir, '..', '..', 'vista')
        vista_path = os.path.abspath(vista_path)
        
        response = send_from_directory(vista_path, 'index-trabajador.css')
        response.headers['Content-Type'] = 'text/css'
        return response
    except Exception as e:
        return f"Error sirviendo CSS: {str(e)}", 500


@auth_bp.route('/dashboard-trabajador.js')
def serve_dashboard_trabajador_js():
    """Sirve el archivo dashboard-trabajador.js"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vista_path = os.path.join(base_dir, '..', '..', 'vista')
        vista_path = os.path.abspath(vista_path)
        
        response = send_from_directory(vista_path, 'index-trabajador.js')
        response.headers['Content-Type'] = 'application/javascript'
        return response
    except Exception as e:
        return f"Error sirviendo JS: {str(e)}", 500


# RUTA ESPECIAL PARA EL DASHBOARD DE AGRICULTOR
@auth_bp.route('/vista/dashboard-agricultor.html')
def serve_dashboard_agricultor():
    """Sirve el dashboard del agricultor con archivos separados"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vista_path = os.path.join(base_dir, '..', '..', 'vista')
        vista_path = os.path.abspath(vista_path)
        
        # Verificar que existen los archivos necesarios
        html_file = os.path.join(vista_path, 'dashboard-agricultor.html')
        css_file = os.path.join(vista_path, 'styles.css')
        js_file = os.path.join(vista_path, 'script.js')
        
        if not os.path.exists(html_file):
            print(f"❌ dashboard-agricultor.html no encontrado: {html_file}")
            return "Dashboard de agricultor no encontrado", 404
            
        print(f"✅ Sirviendo dashboard del agricultor")
        print(f"   HTML: {'✅' if os.path.exists(html_file) else '❌'}")
        print(f"   CSS:  {'✅' if os.path.exists(css_file) else '❌'}")
        print(f"   JS:   {'✅' if os.path.exists(js_file) else '❌'}")
        
        return send_from_directory(vista_path, 'dashboard-agricultor.html')
        
    except Exception as e:
        print(f"❌ Error sirviendo dashboard del agricultor: {str(e)}")
        return f"Error sirviendo dashboard: {str(e)}", 500


# ================================================================
# RUTA DE REGISTRO MEJORADA
# ================================================================

@auth_bp.route('/registro.py', methods=['POST'])
def registro():
    """Procesa el registro de usuarios (Trabajador o Agricultor)"""
    
    try:
        # Obtener y limpiar datos del formulario
        nombre = request.form.get('nombre', '').strip()
        apellido = request.form.get('apellido', '').strip()
        correo = request.form.get('correo', '').strip()
        telefono = request.form.get('telefono', '').strip() if request.form.get('telefono') else None
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        rol = request.form.get('rol', '').strip()
        
        # Debug: Imprimir información del registro
        print(f"=== NUEVO REGISTRO ===")
        print(f"Nombre: {nombre}")
        print(f"Apellido: {apellido}")
        print(f"Correo: {correo}")
        print(f"Rol recibido: '{rol}'")
        print(f"Tipo de rol: {type(rol)}")
        
        # Validación de campos obligatorios
        errores = []
        
        if not nombre:
            errores.append('El nombre es obligatorio')
        elif not validate_name(nombre):
            errores.append('El nombre solo puede contener letras y espacios')
        
        if not apellido:
            errores.append('El apellido es obligatorio')
        elif not validate_name(apellido):
            errores.append('El apellido solo puede contener letras y espacios')
        
        if not correo:
            errores.append('El correo es obligatorio')
        elif not validate_email(correo):
            errores.append('El formato del correo electrónico no es válido')
        
        if not password:
            errores.append('La contraseña es obligatoria')
        elif len(password) < 8:
            errores.append('La contraseña debe tener mínimo 8 caracteres')
        
        if not confirm_password:
            errores.append('Debe confirmar la contraseña')
        elif password != confirm_password:
            errores.append('Las contraseñas no coinciden')
        
        if not rol:
            errores.append('No se pudo determinar el tipo de usuario')
        elif rol not in ['Trabajador', 'Agricultor']:
            errores.append('Tipo de usuario no válido')
        
        # Validar términos y condiciones
        if not request.form.get('terminos'):
            errores.append('Debe aceptar los términos y condiciones')
        
        # Si hay errores, mostrarlos
        if errores:
            print(f"Errores encontrados: {errores}")
            raise Exception('<br>'.join(errores))
        
        # Verificar si el email ya existe
        existing_user = execute_query(
            "SELECT ID_Usuario FROM Usuario WHERE Correo = %s",
            (correo,),
            fetch_one=True
        )
        
        if existing_user:
            # Determinar el enlace de login según el rol
            login_link = '/vista/login-trabajador.html' if rol == 'Agricultor' else '/vista/login-trabajador.html'
            raise Exception(f'El correo electrónico ya está registrado. <a href="{login_link}">¿Ya tienes cuenta? Inicia sesión aquí</a>')
        
        # Encriptar contraseña
        hashed_password = hash_password(password)
        
        # Insertar usuario en la base de datos
        user_id = execute_query(
            "INSERT INTO Usuario (Nombre, Apellido, Correo, Contrasena, Telefono, Rol) VALUES (%s, %s, %s, %s, %s, %s)",
            (nombre, apellido, correo, hashed_password, telefono, rol)
        )
        
        print(f"Usuario registrado exitosamente con ID: {user_id}")
        
        # VERIFICAR QUE EL ARCHIVO DE LOGIN EXISTE ANTES DE REDIRIGIR
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        if rol == 'Trabajador':
            login_file = 'login-trabajador.html'
            tipo_usuario = 'trabajador'
            print("🔄 Preparando redirección a login de TRABAJADOR")
        elif rol == 'Agricultor':
            login_file = 'login-trabajador.html'
            tipo_usuario = 'agricultor'
            print("🔄 Preparando redirección a login de AGRICULTOR")
        else:
            print(f"❌ Rol no reconocido: '{rol}'")
            login_file = 'login-trabajador.html'
            tipo_usuario = 'trabajador'
        
        # Verificar que el archivo existe
        login_file_path = os.path.join(base_dir, '..', '..', 'vista', login_file)
        login_file_path = os.path.abspath(login_file_path)
        
        if not os.path.exists(login_file_path):
            print(f"❌ ARCHIVO DE LOGIN NO EXISTE: {login_file_path}")
            # Si no existe el archivo específico, usar el genérico
            login_file = 'login-trabajador.html'
            tipo_usuario = 'trabajador'
        else:
            print(f"✅ Archivo de login encontrado: {login_file_path}")
        
        redirect_url = f'/vista/{login_file}'
        
        mensaje_exito = f"¡Registro exitoso {nombre}! Tu cuenta como {tipo_usuario} fue creada. Ahora puedes iniciar sesión con tu correo y contraseña."
        
        print(f"✅ Mensaje: {mensaje_exito}")
        print(f"🎯 Redirigiendo a: {redirect_url}")
        
        # Redireccionar con mensaje de éxito
        return redirect(f"{redirect_url}?message={quote(mensaje_exito)}&type=success")
        
    except Exception as e:
        print(f"❌ Error en registro: {str(e)}")
        
        # Determinar la URL de retorno según el rol
        return_url = '/vista/registro-trabajador.html'  # Por defecto
        
        if rol:
            if rol == 'Agricultor':
                # Verificar que existe el archivo de registro de agricultor
                base_dir = os.path.dirname(os.path.abspath(__file__))
                reg_file_path = os.path.join(base_dir, '..', '..', 'vista', 'registro-agricultor.html')
                if os.path.exists(reg_file_path):
                    return_url = '/vista/registro-agricultor.html'
                else:
                    print(f"❌ Archivo de registro de agricultor no existe: {reg_file_path}")
                    return_url = '/vista/registro-trabajador.html'
            else:
                return_url = '/vista/registro-trabajador.html'
        else:
            # Si no hay rol, usar el referer para determinar dónde regresar
            referer = request.headers.get('Referer', '')
            if 'registro-agricultor.html' in referer:
                return_url = '/vista/registro-agricultor.html'
        
        print(f"🔙 Redirigiendo con error a: {return_url}")
        
        # Redireccionar de vuelta al formulario con el mensaje de error
        error_message = quote(str(e))
        return redirect(f"{return_url}?message={error_message}&type=error")


# ================================================================
# RUTA DE LOGIN MEJORADA
# ================================================================

@auth_bp.route('/login.py', methods=['POST'])
def login():
    """Procesa el login de usuarios"""
    
    try:
        # Recoger datos del formulario
        email = request.form.get('email', '').strip()
        password = request.form.get('contrasena', '')
        
        print(f"🔐 Intento de login para: {email}")
        
        # Validaciones básicas
        if not email or not password:
            raise Exception('Por favor completa todos los campos.')
        
        # Buscar usuario en la base de datos
        user = execute_query(
            """SELECT u.ID_Usuario, u.Nombre, u.Apellido, u.Correo, u.Contrasena, u.Rol, u.Estado, u.Telefono
               FROM Usuario u 
               WHERE u.Correo = %s OR u.Telefono = %s""",
            (email, email),
            fetch_one=True
        )
        
        if not user:
            raise Exception('Credenciales incorrectas.')
        
        # Verificar contraseña
        if not verify_password(password, user['Contrasena']):
            raise Exception('Credenciales incorrectas.')
        
        # Verificar que el usuario esté activo
        if user['Estado'] != 'Activo':
            raise Exception('Tu cuenta está inactiva. Contacta al administrador.')
        
        # Crear sesión con todos los datos necesarios
        session['user_id'] = user['ID_Usuario']
        session['username'] = user['Correo']  # Usamos el email como username
        session['first_name'] = user['Nombre']
        session['last_name'] = user['Apellido']
        session['email'] = user['Correo']
        session['user_role'] = user['Rol']
        session['user_name'] = f"{user['Nombre']} {user['Apellido']}"
        session['telefono'] = user.get('Telefono', '')
        
        print(f"✅ Login exitoso para: {user['Nombre']} {user['Apellido']} - Rol: {user['Rol']}")
        print(f"📊 Datos de sesión guardados: ID={user['ID_Usuario']}, Role={user['Rol']}")
        
        # Redireccionar según el rol - ACTUALIZADO PARA USAR LOS NUEVOS DASHBOARDS
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        if user['Rol'] == 'Agricultor':
            # Para agricultor, usar el nuevo dashboard separado
            dashboard_file = 'index-agricultor.html'
            redirect_url = '/vista/index-agricultor.html'
            
            dashboard_path = os.path.join(base_dir, '..', '..', 'vista', dashboard_file)
            if not os.path.exists(dashboard_path):
                print(f"❌ Dashboard de agricultor no existe: {dashboard_path}")
                redirect_url = '/vista/index-agricultor.html'
            
        elif user['Rol'] == 'Trabajador':
            redirect_url = '/vista/index-trabajador.html'
            
        elif user['Rol'] == 'Administrador':
            redirect_url = '/vista/index-administrador.html'
            
        else:
            raise Exception('Rol de usuario no válido.')
        
        print(f"🎯 Redirigiendo a: {redirect_url}")
        return redirect(redirect_url)
        
    except Exception as e:
        print(f"❌ Error en login: {str(e)}")
        
        # Redireccionar con error - determinar la página de login correcta
        referer = request.headers.get('Referer', '')
        if 'login-trabajador.html' in referer:
            login_page = '/vista/login-trabajador.html'
        else:
            login_page = '/vista/login-trabajador.html'
        
        error_message = quote(str(e))
        return redirect(f"{login_page}?message={error_message}&type=error")


@auth_bp.route('/get_user_data.py', methods=['GET'])
def get_user_data():
    """API para obtener datos del usuario logueado (mantener compatibilidad)"""
    
    # Verificar que el usuario esté logueado
    if 'user_id' not in session:
        return jsonify({
            'error': True,
            'message': 'Usuario no autenticado'
        }), 401
    
    # Devolver datos del usuario
    return jsonify({
        'error': False,
        'data': {
            'user_id': session['user_id'],
            'user_name': session['user_name'],
            'user_email': session['email'],
            'user_role': session['user_role'],
            'first_name': session['first_name'],
            'last_name': session['last_name'],
            'username': session['username'],
            'telefono': session.get('telefono', '')
        }
    })


# ================================================================
# RUTAS DE DASHBOARD ACTUALIZADAS
# ================================================================

@auth_bp.route('/dashboard-agricultor')
def dashboard_agricultor():
    """Ruta para el dashboard del agricultor"""
    if 'user_id' not in session:
        print("❌ Usuario no autenticado, redirigiendo a login")
        return redirect('/vista/login-trabajador.html')
    
    # Verificar que el usuario sea agricultor
    if session.get('user_role') != 'Agricultor':
        print(f"❌ Usuario no es agricultor: {session.get('user_role')}")
        return redirect('/vista/index-trabajador.html')
    
    print(f"✅ Acceso autorizado al dashboard de agricultor: {session.get('user_name')}")
    return redirect('/vista/dashboard-agricultor.html')


@auth_bp.route('/dashboard-trabajador')
def dashboard_trabajador():
    """Ruta para el dashboard del trabajador"""
    if 'user_id' not in session:
        print("❌ Usuario no autenticado, redirigiendo a login")
        return redirect('/vista/login-trabajador.html')
    
    # Verificar que el usuario sea trabajador
    if session.get('user_role') != 'Trabajador':
        print(f"❌ Usuario no es trabajador: {session.get('user_role')}")
        return redirect('/vista/index-agricultor.html')
    
    print(f"✅ Acceso autorizado al dashboard de trabajador: {session.get('user_name')}")
    return redirect('/vista/index-trabajador.html')


@auth_bp.route('/dashboard-admin')
def dashboard_admin():
    """Ruta para el dashboard del administrador"""
    if 'user_id' not in session:
        print("❌ Usuario no autenticado, redirigiendo a login")
        return redirect('/vista/login-trabajador.html')
    
    # Verificar que el usuario sea administrador
    if session.get('user_role') != 'Administrador':
        print(f"❌ Usuario no es administrador: {session.get('user_role')}")
        return redirect('/vista/index-trabajador.html')
    
    print(f"✅ Acceso autorizado al dashboard de administrador: {session.get('user_name')}")
    return redirect('/vista/index-administrador.html')


# ================================================================
# RUTA DE LOGOUT MEJORADA
# ================================================================

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Cierra la sesión del usuario (nueva ruta)"""
    try:
        user_name = session.get('user_name', 'Desconocido')
        print(f"👋 Cerrando sesión para usuario: {user_name}")
        
        # Limpiar toda la sesión
        session.clear()
        
        return jsonify({
            'success': True, 
            'message': 'Sesión cerrada correctamente'
        })
        
    except Exception as e:
        print(f"❌ Error cerrando sesión: {str(e)}")
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500


@auth_bp.route('/logout.py', methods=['POST', 'GET'])
def logout_legacy():
    """Cierra la sesión del usuario (ruta legacy para compatibilidad)"""
    
    print(f"👋 Cerrando sesión para usuario: {session.get('user_name', 'Desconocido')}")
    
    # Limpiar sesión
    session.clear()
    
    # Devolver respuesta JSON
    return jsonify({
        'success': True,
        'message': 'Sesión cerrada correctamente'
    })


# ================================================================
# VERIFICACIÓN DE SESIÓN
# ================================================================

@auth_bp.route('/check_session', methods=['GET'])
def check_session():
    """Verifica si hay una sesión activa"""
    try:
        if 'user_id' in session:
            return jsonify({
                'authenticated': True,
                'user_id': session['user_id'],
                'user_role': session.get('user_role'),
                'user_name': session.get('user_name')
            })
        else:
            return jsonify({
                'authenticated': False
            })
    except Exception as e:
        return jsonify({
            'authenticated': False,
            'error': str(e)
        }), 500


@auth_bp.route('/validate_session', methods=['GET'])
def validate_session():
    """Valida que la sesión sea válida y el usuario exista"""
    try:
        if 'user_id' not in session:
            return jsonify({
                'valid': False,
                'message': 'No hay sesión activa'
            }), 401
        
        # Verificar que el usuario aún existe en la base de datos
        user = execute_query(
            "SELECT ID_Usuario, Nombre, Apellido, Rol, Estado FROM Usuario WHERE ID_Usuario = %s",
            (session['user_id'],),
            fetch_one=True
        )
        
        if not user:
            # Usuario no existe, limpiar sesión
            session.clear()
            return jsonify({
                'valid': False,
                'message': 'Usuario no encontrado'
            }), 401
        
        if user['Estado'] != 'Activo':
            # Usuario inactivo, limpiar sesión
            session.clear()
            return jsonify({
                'valid': False,
                'message': 'Usuario inactivo'
            }), 401
        
        return jsonify({
            'valid': True,
            'user': {
                'id': user['ID_Usuario'],
                'nombre': user['Nombre'],
                'apellido': user['Apellido'],
                'rol': user['Rol']
            }
        })
        
    except Exception as e:
        print(f"❌ Error validando sesión: {str(e)}")
        return jsonify({
            'valid': False,
            'error': str(e)
        }), 500


# ================================================================
# RUTAS ADICIONALES PARA REDIRECCIONES
# ================================================================

@auth_bp.route('/')
def index():
    """Ruta principal - redirige al login de trabajador"""
    return redirect('/vista/inicio-sesion.html')


@auth_bp.route('/registro-trabajador')
def registro_trabajador():
    """Redirige al registro de trabajador"""
    return redirect('/vista/registro-trabajador.html')


@auth_bp.route('/registro-agricultor')
def registro_agricultor():
    """Redirige al registro de agricultor"""
    return redirect('/vista/registro-agricultor.html')


@auth_bp.route('/login-trabajador')
def login_trabajador():
    """Redirige al login de trabajador"""
    return redirect('/vista/login-trabajador.html')


@auth_bp.route('/login-agricultor')
def login_agricultor():
    """Redirige al login de agricultor"""
    return redirect('/vista/login-trabajador.html')


# ================================================================
# RUTAS PARA SIMULACIÓN DE GOOGLE
# ================================================================

@auth_bp.route('/auth/google/demo')
def google_demo():
    """Página de selección de usuario demo de Google"""
    try:
        rol = request.args.get('rol', 'Trabajador')
        session['oauth_rol'] = rol
        
        # Generar página HTML simple para seleccionar usuario demo
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Demo Google - CAMP</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0;
                }}
                .demo-container {{
                    background: white;
                    padding: 40px;
                    border-radius: 15px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    max-width: 500px;
                    width: 90%;
                    text-align: center;
                }}
                .demo-header {{
                    margin-bottom: 30px;
                }}
                .demo-header h2 {{
                    color: #333;
                    margin-bottom: 10px;
                }}
                .demo-header p {{
                    color: #666;
                    margin-bottom: 5px;
                }}
                .role-badge {{
                    background: #4CAF50;
                    color: white;
                    padding: 5px 15px;
                    border-radius: 20px;
                    font-size: 14px;
                    font-weight: 600;
                }}
                .user-list {{
                    margin: 30px 0;
                }}
                .demo-user {{
                    display: flex;
                    align-items: center;
                    padding: 15px;
                    margin: 10px 0;
                    background: #f8f9fa;
                    border-radius: 10px;
                    border: 2px solid transparent;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }}
                .demo-user:hover {{
                    border-color: #4285f4;
                    background: #e3f2fd;
                }}
                .user-avatar {{
                    width: 50px;
                    height: 50px;
                    background: #4285f4;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                    font-size: 18px;
                    margin-right: 15px;
                }}
                .user-info {{
                    flex: 1;
                    text-align: left;
                }}
                .user-name {{
                    font-weight: 600;
                    color: #333;
                    margin-bottom: 3px;
                }}
                .user-email {{
                    color: #666;
                    font-size: 14px;
                }}
                .cancel-btn {{
                    background: #6c757d;
                    color: white;
                    border: none;
                    padding: 12px 25px;
                    border-radius: 8px;
                    cursor: pointer;
                    text-decoration: none;
                    display: inline-block;
                    margin-top: 20px;
                    transition: background 0.3s ease;
                }}
                .cancel-btn:hover {{
                    background: #5a6268;
                }}
                .google-logo {{
                    color: #4285f4;
                    font-size: 24px;
                    margin-right: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="demo-container">
                <div class="demo-header">
                    <h2><i class="fab fa-google google-logo"></i>Simulación Google OAuth</h2>
                    <p>Registro como: <span class="role-badge">{rol}</span></p>
                    <p>Selecciona un usuario demo para continuar</p>
                </div>
                
                <div class="user-list">
        """
        
        # Agregar usuarios demo
        for demo_id, user_data in GOOGLE_USERS_DEMO.items():
            initials = f"{user_data['given_name'][0]}{user_data['family_name'][0]}"
            html_content += f"""
                    <div class="demo-user" onclick="selectGoogleUser('{demo_id}')">
                        <div class="user-avatar">{initials}</div>
                        <div class="user-info">
                            <div class="user-name">{user_data['given_name']} {user_data['family_name']}</div>
                            <div class="user-email">{user_data['email']}</div>
                        </div>
                    </div>
            """
        
        html_content += """
                </div>
                
                <a href="javascript:history.back()" class="cancel-btn">Cancelar</a>
            </div>
            
            <script>
                function selectGoogleUser(demoId) {
                    window.location.href = `/auth/google/demo/callback?demo_user=${demoId}`;
                }
            </script>
        </body>
        </html>
        """
        
        return html_content
        
    except Exception as e:
        print(f"Error en Google demo: {str(e)}")
        return redirect('/vista/registro-trabajador.html?message=Error en simulación de Google&type=error')


@auth_bp.route('/auth/google/demo/callback')
def google_demo_callback():
    """Procesar selección de usuario demo de Google"""
    try:
        demo_user_id = request.args.get('demo_user')
        rol = session.get('oauth_rol', 'Trabajador')
        
        if not demo_user_id or demo_user_id not in GOOGLE_USERS_DEMO:
            return redirect('/vista/registro-trabajador.html?message=Usuario demo no válido&type=error')
        
        user_data = GOOGLE_USERS_DEMO[demo_user_id]
        
        # Verificar si el usuario ya existe
        existing_user = execute_query(
            "SELECT * FROM Usuario WHERE Correo = %s",
            (user_data['email'],),
            fetch_one=True
        )
        
        if existing_user:
            user_id = existing_user['ID_Usuario']
            print(f"Usuario demo existente: {existing_user['Nombre']}")
        else:
            user_id = create_demo_user(user_data, 'google', rol)
            if not user_id:
                return redirect('/vista/registro-trabajador.html?message=Error creando usuario demo&type=error')
        
        # Obtener datos actualizados del usuario
        user = execute_query(
            "SELECT * FROM Usuario WHERE ID_Usuario = %s",
            (user_id,),
            fetch_one=True
        )
        
        # Crear sesión
        session['user_id'] = user['ID_Usuario']
        session['username'] = user['Correo']
        session['first_name'] = user['Nombre']
        session['last_name'] = user['Apellido']
        session['email'] = user['Correo']
        session['user_role'] = user['Rol']
        session['user_name'] = f"{user['Nombre']} {user['Apellido']}"
        session['telefono'] = user.get('Telefono', '')
        
        session.pop('oauth_rol', None)
        
        # Redireccionar según el rol
        if user['Rol'] == 'Agricultor':
            redirect_url = '/vista/index-agricultor.html'
        else:
            redirect_url = '/vista/index-trabajador.html'
        
        return redirect(redirect_url)
        
    except Exception as e:
        print(f"Error en Google demo callback: {str(e)}")
        return redirect('/vista/registro-trabajador.html?message=Error procesando usuario demo&type=error')


# ================================================================
# RUTAS PARA SIMULACIÓN DE FACEBOOK
# ================================================================

@auth_bp.route('/auth/facebook/demo')
def facebook_demo():
    """Página de selección de usuario demo de Facebook"""
    try:
        rol = request.args.get('rol', 'Trabajador')
        session['oauth_rol'] = rol
        
        # Similar al de Google pero con estilo de Facebook
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Demo Facebook - CAMP</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #4267B2 0%, #365899 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0;
                }}
                .demo-container {{
                    background: white;
                    padding: 40px;
                    border-radius: 15px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    max-width: 500px;
                    width: 90%;
                    text-align: center;
                }}
                .demo-header {{
                    margin-bottom: 30px;
                }}
                .demo-header h2 {{
                    color: #333;
                    margin-bottom: 10px;
                }}
                .demo-header p {{
                    color: #666;
                    margin-bottom: 5px;
                }}
                .role-badge {{
                    background: #4CAF50;
                    color: white;
                    padding: 5px 15px;
                    border-radius: 20px;
                    font-size: 14px;
                    font-weight: 600;
                }}
                .user-list {{
                    margin: 30px 0;
                }}
                .demo-user {{
                    display: flex;
                    align-items: center;
                    padding: 15px;
                    margin: 10px 0;
                    background: #f8f9fa;
                    border-radius: 10px;
                    border: 2px solid transparent;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }}
                .demo-user:hover {{
                    border-color: #4267B2;
                    background: #e3f2fd;
                }}
                .user-avatar {{
                    width: 50px;
                    height: 50px;
                    background: #4267B2;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                    font-size: 18px;
                    margin-right: 15px;
                }}
                .user-info {{
                    flex: 1;
                    text-align: left;
                }}
                .user-name {{
                    font-weight: 600;
                    color: #333;
                    margin-bottom: 3px;
                }}
                .user-email {{
                    color: #666;
                    font-size: 14px;
                }}
                .cancel-btn {{
                    background: #6c757d;
                    color: white;
                    border: none;
                    padding: 12px 25px;
                    border-radius: 8px;
                    cursor: pointer;
                    text-decoration: none;
                    display: inline-block;
                    margin-top: 20px;
                    transition: background 0.3s ease;
                }}
                .cancel-btn:hover {{
                    background: #5a6268;
                }}
                .facebook-logo {{
                    color: #4267B2;
                    font-size: 24px;
                    margin-right: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="demo-container">
                <div class="demo-header">
                    <h2><i class="fab fa-facebook facebook-logo"></i>Simulación Facebook OAuth</h2>
                    <p>Registro como: <span class="role-badge">{rol}</span></p>
                    <p>Selecciona un usuario demo para continuar</p>
                </div>
                
                <div class="user-list">
        """
        
        # Agregar usuarios demo
        for demo_id, user_data in FACEBOOK_USERS_DEMO.items():
            initials = f"{user_data['first_name'][0]}{user_data['last_name'][0]}"
            html_content += f"""
                    <div class="demo-user" onclick="selectFacebookUser('{demo_id}')">
                        <div class="user-avatar">{initials}</div>
                        <div class="user-info">
                            <div class="user-name">{user_data['first_name']} {user_data['last_name']}</div>
                            <div class="user-email">{user_data['email']}</div>
                        </div>
                    </div>
            """
        
        html_content += """
                </div>
                
                <a href="javascript:history.back()" class="cancel-btn">Cancelar</a>
            </div>
            
            <script>
                function selectFacebookUser(demoId) {
                    window.location.href = `/auth/facebook/demo/callback?demo_user=${demoId}`;
                }
            </script>
        </body>
        </html>
        """
        
        return html_content
        
    except Exception as e:
        print(f"Error en Facebook demo: {str(e)}")
        return redirect('/vista/registro-trabajador.html?message=Error en simulación de Facebook&type=error')


@auth_bp.route('/auth/facebook/demo/callback')
def facebook_demo_callback():
    """Procesar selección de usuario demo de Facebook"""
    try:
        demo_user_id = request.args.get('demo_user')
        rol = session.get('oauth_rol', 'Trabajador')
        
        if not demo_user_id or demo_user_id not in FACEBOOK_USERS_DEMO:
            return redirect('/vista/registro-trabajador.html?message=Usuario demo no válido&type=error')
        
        user_data = FACEBOOK_USERS_DEMO[demo_user_id]
        
        # Verificar si el usuario ya existe
        existing_user = execute_query(
            "SELECT * FROM Usuario WHERE Correo = %s",
            (user_data['email'],),
            fetch_one=True
        )
        
        if existing_user:
            user_id = existing_user['ID_Usuario']
            print(f"Usuario demo existente: {existing_user['Nombre']}")
        else:
            user_id = create_demo_user(user_data, 'facebook', rol)
            if not user_id:
                return redirect('/vista/registro-trabajador.html?message=Error creando usuario demo&type=error')
        
        # Obtener datos actualizados del usuario
        user = execute_query(
            "SELECT * FROM Usuario WHERE ID_Usuario = %s",
            (user_id,),
            fetch_one=True
        )
        
        # Crear sesión
        session['user_id'] = user['ID_Usuario']
        session['username'] = user['Correo']
        session['first_name'] = user['Nombre']
        session['last_name'] = user['Apellido']
        session['email'] = user['Correo']
        session['user_role'] = user['Rol']
        session['user_name'] = f"{user['Nombre']} {user['Apellido']}"
        session['telefono'] = user.get('Telefono', '')
        
        session.pop('oauth_rol', None)
        
        # Redireccionar según el rol
        if user['Rol'] == 'Agricultor':
            redirect_url = '/vista/index-agricultor.html'
        else:
            redirect_url = '/vista/index-trabajador.html'
        
        return redirect(redirect_url)
        
    except Exception as e:
        print(f"Error en Facebook demo callback: {str(e)}")
        return redirect('/vista/registro-trabajador.html?message=Error procesando usuario demo&type=error')

# ================================================================
# SIMULACIÓN DE AUTENTICACIÓN REAL
# ================================================================

def extract_info_from_email(email, provider):
    """Extrae información básica del email para crear el usuario"""
    try:
        # Extraer nombre del email (parte antes del @)
        username = email.split('@')[0]
        
        # Limpiar números y caracteres especiales
        clean_name = re.sub(r'[0-9._-]', ' ', username).strip()
        
        # Dividir en nombre y apellido
        name_parts = clean_name.split()
        
        if len(name_parts) >= 2:
            nombre = name_parts[0].capitalize()
            apellido = ' '.join(name_parts[1:]).title()
        elif len(name_parts) == 1:
            nombre = name_parts[0].capitalize()
            apellido = "Usuario"
        else:
            nombre = "Usuario"
            apellido = provider.capitalize()
        
        return {
            'nombre': nombre,
            'apellido': apellido,
            'email': email,
            'username': username,
            'provider': provider
        }
        
    except Exception as e:
        print(f"Error extrayendo info del email: {str(e)}")
        return None

def create_social_user_real(email, provider, rol='Trabajador'):
    """Crea un usuario real desde email de red social"""
    try:
        # Extraer información del email
        user_info = extract_info_from_email(email, provider)
        if not user_info:
            return None
        
        # Generar contraseña temporal hasheada
        from app import hash_password
        temp_password = hash_password(f"{email}_social_{provider}_{uuid.uuid4()}")
        
        # URL de foto por defecto según el proveedor
        if provider == 'google':
            foto_url = "/static/uploads/profile_photos/default_google_user.jpg"
        else:
            foto_url = "/static/uploads/profile_photos/default_facebook_user.jpg"
        
        # Insertar en base de datos
        user_id = execute_query(
            """INSERT INTO Usuario (Nombre, Apellido, Correo, Contrasena, URL_Foto, 
                                   Red_Social, Rol, Estado) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'Activo')""",
            (
                user_info['nombre'],
                user_info['apellido'], 
                email,
                temp_password,
                foto_url,
                f"{provider}:{user_info['username']}",
                rol
            )
        )
        
        print(f"Usuario real creado desde {provider}: {email}")
        return user_id
        
    except Exception as e:
        print(f"Error creando usuario social real: {str(e)}")
        return None


# ================================================================
# FORMULARIO PARA INGRESO CON GOOGLE
# ================================================================

@auth_bp.route('/auth/google/login')
def google_auth_form():
    """Formulario para ingresar email de Google - VERSIÓN CORREGIDA"""
    try:
        # Obtener rol si viene desde registro, si no, es login
        rol = request.args.get('rol', None)
        
        if rol:
            # Es registro con rol específico
            session['oauth_rol'] = rol
            action_text = f"Registro como {rol}"
            process_url = "/auth/google/process"
            info_text = "Se creará tu cuenta automáticamente"
        else:
            # Es login sin rol específico
            action_text = "Iniciar Sesión"
            process_url = "/auth/google/login-process"
            info_text = "Si no tienes cuenta, te ayudaremos a crearla"
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Google - CAMP</title>
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #4285f4 0%, #34a853 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0;
                    padding: 20px;
                }}
                .auth-container {{
                    background: white;
                    padding: 40px;
                    border-radius: 20px;
                    box-shadow: 0 15px 35px rgba(0,0,0,0.1);
                    max-width: 450px;
                    width: 100%;
                    text-align: center;
                }}
                .google-logo {{
                    font-size: 48px;
                    background: linear-gradient(45deg, #4285f4, #34a853, #fbbc05, #ea4335);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin-bottom: 20px;
                }}
                .auth-header h2 {{
                    color: #202124;
                    font-size: 24px;
                    margin-bottom: 10px;
                }}
                .auth-header p {{
                    color: #5f6368;
                    font-size: 16px;
                    margin-bottom: 30px;
                }}
                .form-group {{
                    margin-bottom: 20px;
                    text-align: left;
                }}
                .form-group label {{
                    display: block;
                    color: #3c4043;
                    font-size: 14px;
                    font-weight: 500;
                    margin-bottom: 8px;
                }}
                .form-group input {{
                    width: 100%;
                    padding: 16px;
                    border: 1px solid #dadce0;
                    border-radius: 8px;
                    font-size: 16px;
                    box-sizing: border-box;
                    transition: border-color 0.3s ease;
                }}
                .form-group input:focus {{
                    outline: none;
                    border-color: #1a73e8;
                    box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2);
                }}
                .btn-continue {{
                    width: 100%;
                    background: #1a73e8;
                    color: white;
                    border: none;
                    padding: 16px;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: 500;
                    cursor: pointer;
                    margin-bottom: 16px;
                    transition: background 0.3s ease;
                }}
                .btn-continue:hover {{
                    background: #1557b0;
                }}
                .btn-continue:disabled {{
                    background: #dadce0;
                    cursor: not-allowed;
                }}
                .btn-cancel {{
                    width: 100%;
                    background: transparent;
                    color: #1a73e8;
                    border: 1px solid #dadce0;
                    padding: 16px;
                    border-radius: 8px;
                    text-decoration: none;
                    display: inline-block;
                    transition: background 0.3s ease;
                }}
                .btn-cancel:hover {{
                    background: #f8f9fa;
                }}
                .info-note {{
                    background: #e3f2fd;
                    border: 1px solid #1976d2;
                    border-radius: 8px;
                    padding: 12px;
                    margin: 20px 0;
                    font-size: 13px;
                    color: #0d47a1;
                }}
                .help-text {{
                    font-size: 12px;
                    color: #5f6368;
                    margin-top: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="auth-container">
                <div class="auth-header">
                    <div class="google-logo">
                        <i class="fab fa-google"></i>
                    </div>
                    <h2>Continuar con Google</h2>
                    <p>{action_text}</p>
                </div>

                <form id="googleForm" action="{process_url}" method="POST">
                    {"<input type='hidden' name='rol' value='" + str(rol) + "'>" if rol else ""}
                    
                    <div class="form-group">
                        <label for="google_email">Tu correo de Gmail</label>
                        <input 
                            type="email" 
                            id="google_email" 
                            name="google_email" 
                            placeholder="ejemplo@gmail.com"
                            required>
                        <div class="help-text">Ingresa tu dirección de Gmail real</div>
                    </div>

                    <div class="info-note">
                        <i class="fas fa-info-circle"></i> 
                        {info_text}
                    </div>

                    <button type="submit" class="btn-continue" id="continueBtn">
                        <i class="fas fa-arrow-right"></i> Continuar
                    </button>
                </form>

                <a href="javascript:history.back()" class="btn-cancel">
                    <i class="fas fa-arrow-left"></i> Volver
                </a>
            </div>

            <script>
                // Validación en tiempo real
                document.getElementById('google_email').addEventListener('input', function() {{
                    const email = this.value;
                    const btn = document.getElementById('continueBtn');
                    
                    if (email.includes('@gmail.com') || email.includes('@googlemail.com')) {{
                        this.style.borderColor = '#34a853';
                        btn.disabled = false;
                    }} else if (email.includes('@')) {{
                        this.style.borderColor = '#ea4335';
                        btn.disabled = true;
                    }} else {{
                        this.style.borderColor = '#dadce0';
                        btn.disabled = email.length === 0;
                    }}
                }});

                // Validación del formulario
                document.getElementById('googleForm').addEventListener('submit', function(e) {{
                    const email = document.getElementById('google_email').value;
                    
                    if (!email.includes('@gmail.com') && !email.includes('@googlemail.com')) {{
                        e.preventDefault();
                        alert('Por favor ingresa un correo válido de Gmail (@gmail.com)');
                        return false;
                    }}
                }});
            </script>
        </body>
        </html>
        """
        
        return html_content
        
    except Exception as e:
        print(f"Error en formulario de Google: {str(e)}")
        return redirect('/vista/login-trabajador.html?message=Error cargando Google&type=error')


@auth_bp.route('/auth/facebook/login')
def facebook_auth_form():
    """Formulario para ingresar email de Facebook - VERSIÓN CORREGIDA"""
    try:
        # Obtener rol si viene desde registro, si no, es login
        rol = request.args.get('rol', None)
        
        if rol:
            # Es registro con rol específico
            session['oauth_rol'] = rol
            action_text = f"Registro como {rol}"
            process_url = "/auth/facebook/process"
            info_text = "Se creará tu cuenta automáticamente"
        else:
            # Es login sin rol específico
            action_text = "Iniciar Sesión"
            process_url = "/auth/facebook/login-process"
            info_text = "Si no tienes cuenta, te ayudaremos a crearla"
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Facebook - CAMP</title>
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #4267B2 0%, #365899 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0;
                    padding: 20px;
                }}
                .auth-container {{
                    background: white;
                    padding: 40px;
                    border-radius: 20px;
                    box-shadow: 0 15px 35px rgba(0,0,0,0.1);
                    max-width: 450px;
                    width: 100%;
                    text-align: center;
                }}
                .facebook-logo {{
                    font-size: 48px;
                    color: #4267B2;
                    margin-bottom: 20px;
                }}
                .auth-header h2 {{
                    color: #1c1e21;
                    font-size: 24px;
                    margin-bottom: 10px;
                }}
                .auth-header p {{
                    color: #606770;
                    font-size: 16px;
                    margin-bottom: 30px;
                }}
                .form-group {{
                    margin-bottom: 20px;
                    text-align: left;
                }}
                .form-group label {{
                    display: block;
                    color: #1c1e21;
                    font-size: 14px;
                    font-weight: 500;
                    margin-bottom: 8px;
                }}
                .form-group input {{
                    width: 100%;
                    padding: 16px;
                    border: 1px solid #dddfe2;
                    border-radius: 8px;
                    font-size: 16px;
                    box-sizing: border-box;
                    transition: border-color 0.3s ease;
                }}
                .form-group input:focus {{
                    outline: none;
                    border-color: #4267B2;
                    box-shadow: 0 0 0 2px rgba(66, 103, 178, 0.2);
                }}
                .btn-continue {{
                    width: 100%;
                    background: #4267B2;
                    color: white;
                    border: none;
                    padding: 16px;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    margin-bottom: 16px;
                    transition: background 0.3s ease;
                }}
                .btn-continue:hover {{
                    background: #365899;
                }}
                .btn-continue:disabled {{
                    background: #e4e6ea;
                    cursor: not-allowed;
                }}
                .btn-cancel {{
                    width: 100%;
                    background: transparent;
                    color: #4267B2;
                    border: 1px solid #dddfe2;
                    padding: 16px;
                    border-radius: 8px;
                    text-decoration: none;
                    display: inline-block;
                    transition: background 0.3s ease;
                }}
                .btn-cancel:hover {{
                    background: #f5f6f7;
                }}
                .info-note {{
                    background: #e7f3ff;
                    border: 1px solid #4267B2;
                    border-radius: 8px;
                    padding: 12px;
                    margin: 20px 0;
                    font-size: 13px;
                    color: #4267B2;
                }}
                .help-text {{
                    font-size: 12px;
                    color: #606770;
                    margin-top: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="auth-container">
                <div class="auth-header">
                    <div class="facebook-logo">
                        <i class="fab fa-facebook"></i>
                    </div>
                    <h2>Continuar con Facebook</h2>
                    <p>{action_text}</p>
                </div>

                <form id="facebookForm" action="{process_url}" method="POST">
                    {"<input type='hidden' name='rol' value='" + str(rol) + "'>" if rol else ""}
                    
                    <div class="form-group">
                        <label for="facebook_email">Tu correo asociado a Facebook</label>
                        <input 
                            type="email" 
                            id="facebook_email" 
                            name="facebook_email" 
                            placeholder="ejemplo@hotmail.com o @outlook.com"
                            required>
                        <div class="help-text">Hotmail, Outlook, Live o MSN</div>
                    </div>

                    <div class="info-note">
                        <i class="fas fa-info-circle"></i> 
                        {info_text}
                    </div>

                    <button type="submit" class="btn-continue" id="continueBtn">
                        <i class="fas fa-arrow-right"></i> Continuar
                    </button>
                </form>

                <a href="javascript:history.back()" class="btn-cancel">
                    <i class="fas fa-arrow-left"></i> Volver
                </a>
            </div>

            <script>
                // Validación en tiempo real
                document.getElementById('facebook_email').addEventListener('input', function() {{
                    const email = this.value;
                    const btn = document.getElementById('continueBtn');
                    const validDomains = ['@hotmail.com', '@outlook.com', '@live.com', '@msn.com'];
                    
                    if (validDomains.some(domain => email.includes(domain))) {{
                        this.style.borderColor = '#42b883';
                        btn.disabled = false;
                    }} else if (email.includes('@')) {{
                        this.style.borderColor = '#e74c3c';
                        btn.disabled = true;
                    }} else {{
                        this.style.borderColor = '#dddfe2';
                        btn.disabled = email.length === 0;
                    }}
                }});

                // Validación del formulario
                document.getElementById('facebookForm').addEventListener('submit', function(e) {{
                    const email = document.getElementById('facebook_email').value;
                    const validDomains = ['@hotmail.com', '@outlook.com', '@live.com', '@msn.com'];
                    
                    if (!validDomains.some(domain => email.includes(domain))) {{
                        e.preventDefault();
                        alert('Por favor ingresa un correo válido asociado a Facebook (Hotmail, Outlook, Live, MSN)');
                        return false;
                    }}
                }});
            </script>
        </body>
        </html>
        """
        
        return html_content
        
    except Exception as e:
        print(f"Error en formulario de Facebook: {str(e)}")
        return redirect('/vista/login-trabajador.html?message=Error cargando Facebook&type=error')

# ================================================================
# RUTAS DE PROCESAMIENTO (MANTENER LAS EXISTENTES)
# ================================================================

print("✅ Rutas de Google y Facebook corregidas y cargadas")


# ================================================================
# RUTAS PARA ELIMINACIÓN DE CUENTA CON REDES SOCIALES
# ================================================================

@auth_bp.route('/auth/google/delete-account', methods=['POST'])
@require_login
def delete_account_with_google():
    """Eliminar cuenta verificando que fue creada con Google"""
    try:
        user_id = session['user_id']
        
        # Verificar que el usuario actual existe y tiene Google asociado
        user = execute_query(
            "SELECT * FROM Usuario WHERE ID_Usuario = %s",
            (user_id,),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
        # Verificar que la cuenta fue creada con Google
        red_social = user.get('Red_Social', '')
        if not red_social or not red_social.startswith('google:'):
            return jsonify({
                'success': False, 
                'message': 'Esta cuenta no fue creada con Google'
            }), 400
        
        print(f"Eliminando cuenta con Google para usuario: {user['Nombre']} {user['Apellido']}")
        
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
                    execute_query(f"DELETE FROM {table_name} WHERE {columns[0]} = %s", (user_id,))
                else:
                    conditions = ' OR '.join([f"{col} = %s" for col in columns])
                    params = [user_id] * len(columns)
                    execute_query(f"DELETE FROM {table_name} WHERE {conditions}", params)
                    
            except Exception as table_error:
                print(f"Error eliminando de {table_name}: {str(table_error)}")
                continue
        
        # Eliminar el usuario
        execute_query("DELETE FROM Usuario WHERE ID_Usuario = %s", (user_id,))
        
        # Limpiar sesión
        session.clear()
        
        print(f"Cuenta eliminada exitosamente con Google para usuario ID: {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Cuenta eliminada correctamente con Google'
        })
        
    except Exception as e:
        print(f"Error eliminando cuenta con Google: {str(e)}")
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500


@auth_bp.route('/auth/facebook/delete-account', methods=['POST'])
@require_login
def delete_account_with_facebook():
    """Eliminar cuenta verificando que fue creada con Facebook"""
    try:
        user_id = session['user_id']
        
        # Verificar que el usuario actual existe y tiene Facebook asociado
        user = execute_query(
            "SELECT * FROM Usuario WHERE ID_Usuario = %s",
            (user_id,),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
        # Verificar que la cuenta fue creada con Facebook
        red_social = user.get('Red_Social', '')
        if not red_social or not red_social.startswith('facebook:'):
            return jsonify({
                'success': False, 
                'message': 'Esta cuenta no fue creada con Facebook'
            }), 400
        
        print(f"Eliminando cuenta con Facebook para usuario: {user['Nombre']} {user['Apellido']}")
        
        # Eliminar registros relacionados (mismo proceso que Google)
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
                    execute_query(f"DELETE FROM {table_name} WHERE {columns[0]} = %s", (user_id,))
                else:
                    conditions = ' OR '.join([f"{col} = %s" for col in columns])
                    params = [user_id] * len(columns)
                    execute_query(f"DELETE FROM {table_name} WHERE {conditions}", params)
                    
            except Exception as table_error:
                print(f"Error eliminando de {table_name}: {str(table_error)}")
                continue
        
        # Eliminar el usuario
        execute_query("DELETE FROM Usuario WHERE ID_Usuario = %s", (user_id,))
        
        # Limpiar sesión
        session.clear()
        
        print(f"Cuenta eliminada exitosamente con Facebook para usuario ID: {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Cuenta eliminada correctamente con Facebook'
        })
        
    except Exception as e:
        print(f"Error eliminando cuenta con Facebook: {str(e)}")
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500

print("✅ Rutas de eliminación social cargadas correctamente")


# ================================================================
# RUTAS DE PROCESAMIENTO FALTANTES - AGREGAR A APP.PY
# Estas son las rutas que procesan el login sin rol específico
# ================================================================

@auth_bp.route('/auth/google/login-process', methods=['POST'])
def google_login_process():
    """Procesar login con Google (desde página de login - sin rol específico)"""
    try:
        google_email = request.form.get('google_email', '').strip().lower()
        
        print(f"Procesando login con Google para: {google_email}")
        
        # Validar email de Google
        if not google_email or not (google_email.endswith('@gmail.com') or google_email.endswith('@googlemail.com')):
            return redirect('/vista/login-trabajador.html?message=Por favor ingresa un correo válido de Gmail&type=error')
        
        # Buscar si el usuario ya existe
        existing_user = execute_query(
            "SELECT * FROM Usuario WHERE Correo = %s",
            (google_email,),
            fetch_one=True
        )
        
        if not existing_user:
            # Usuario no existe, redirigir a selección de rol para registro
            return redirect(f'/vista/seleccion-rol.html?email={quote(google_email)}&provider=google&message=Cuenta no encontrada. Selecciona tu rol para registrarte&type=info')
        
        # Usuario existe, crear sesión
        user = existing_user
        session['user_id'] = user['ID_Usuario']
        session['username'] = user['Correo']
        session['first_name'] = user['Nombre']
        session['last_name'] = user['Apellido']
        session['email'] = user['Correo']
        session['user_role'] = user['Rol']
        session['user_name'] = f"{user['Nombre']} {user['Apellido']}"
        session['telefono'] = user.get('Telefono', '')
        
        print(f"Login exitoso con Google: {user['Nombre']} - Rol: {user['Rol']}")
        
        # Redireccionar según el rol
        if user['Rol'] == 'Agricultor':
            return redirect('/vista/index-agricultor.html')
        else:
            return redirect('/vista/index-trabajador.html')
        
    except Exception as e:
        print(f"Error en login Google: {str(e)}")
        return redirect('/vista/login-trabajador.html?message=Error procesando Google&type=error')


@auth_bp.route('/auth/facebook/login-process', methods=['POST'])
def facebook_login_process():
    """Procesar login con Facebook (desde página de login - sin rol específico)"""
    try:
        facebook_email = request.form.get('facebook_email', '').strip().lower()
        
        print(f"Procesando login con Facebook para: {facebook_email}")
        
        # Validar email de Facebook
        valid_domains = ['@hotmail.com', '@outlook.com', '@live.com', '@msn.com']
        if not facebook_email or not any(facebook_email.endswith(domain) for domain in valid_domains):
            return redirect('/vista/login-trabajador.html?message=Por favor ingresa un correo válido asociado a Facebook&type=error')
        
        # Buscar si el usuario ya existe
        existing_user = execute_query(
            "SELECT * FROM Usuario WHERE Correo = %s",
            (facebook_email,),
            fetch_one=True
        )
        
        if not existing_user:
            # Usuario no existe, redirigir a selección de rol para registro
            return redirect(f'/vista/seleccion-rol.html?email={quote(facebook_email)}&provider=facebook&message=Cuenta no encontrada. Selecciona tu rol para registrarte&type=info')
        
        # Usuario existe, crear sesión
        user = existing_user
        session['user_id'] = user['ID_Usuario']
        session['username'] = user['Correo']
        session['first_name'] = user['Nombre']
        session['last_name'] = user['Apellido']
        session['email'] = user['Correo']
        session['user_role'] = user['Rol']
        session['user_name'] = f"{user['Nombre']} {user['Apellido']}"
        session['telefono'] = user.get('Telefono', '')
        
        print(f"Login exitoso con Facebook: {user['Nombre']} - Rol: {user['Rol']}")
        
        # Redireccionar según el rol
        if user['Rol'] == 'Agricultor':
            return redirect('/vista/index-agricultor.html')
        else:
            return redirect('/vista/index-trabajador.html')
        
    except Exception as e:
        print(f"Error en login Facebook: {str(e)}")
        return redirect('/vista/login-trabajador.html?message=Error procesando Facebook&type=error')


@auth_bp.route('/auth/google/process', methods=['POST'])
def google_register_process():
    """Procesar registro con Google (desde páginas de registro - con rol específico)"""
    try:
        google_email = request.form.get('google_email', '').strip().lower()
        rol = request.form.get('rol', 'Trabajador')
        
        print(f"Procesando registro con Google para: {google_email} como {rol}")
        
        # Validar email de Google
        if not google_email or not (google_email.endswith('@gmail.com') or google_email.endswith('@googlemail.com')):
            redirect_url = '/vista/registro-agricultor.html' if rol == 'Agricultor' else '/vista/registro-trabajador.html'
            return redirect(f'{redirect_url}?message=Por favor ingresa un correo válido de Gmail&type=error')
        
        # Verificar si el usuario ya existe
        existing_user = execute_query(
            "SELECT * FROM Usuario WHERE Correo = %s",
            (google_email,),
            fetch_one=True
        )
        
        if existing_user:
            # Usuario existe, iniciar sesión
            user = existing_user
            print(f"Usuario existente encontrado: {existing_user['Nombre']}")
        else:
            # Crear nuevo usuario
            user_id = create_social_user_real(google_email, 'google', rol)
            if not user_id:
                redirect_url = '/vista/registro-agricultor.html' if rol == 'Agricultor' else '/vista/registro-trabajador.html'
                return redirect(f'{redirect_url}?message=Error creando usuario con Google&type=error')
            
            user = execute_query(
                "SELECT * FROM Usuario WHERE ID_Usuario = %s",
                (user_id,),
                fetch_one=True
            )
        
        # Crear sesión
        session['user_id'] = user['ID_Usuario']
        session['username'] = user['Correo']
        session['first_name'] = user['Nombre']
        session['last_name'] = user['Apellido']
        session['email'] = user['Correo']
        session['user_role'] = user['Rol']
        session['user_name'] = f"{user['Nombre']} {user['Apellido']}"
        session['telefono'] = user.get('Telefono', '')
        
        session.pop('oauth_rol', None)
        
        print(f"Registro/Login exitoso con Google: {user['Nombre']} - Rol: {user['Rol']}")
        
        # Redireccionar según el rol
        if user['Rol'] == 'Agricultor':
            return redirect('/vista/index-agricultor.html')
        else:
            return redirect('/vista/index-trabajador.html')
        
    except Exception as e:
        print(f"Error procesando registro Google: {str(e)}")
        return redirect('/vista/registro-trabajador.html?message=Error con Google&type=error')


@auth_bp.route('/auth/facebook/process', methods=['POST'])
def facebook_register_process():
    """Procesar registro con Facebook (desde páginas de registro - con rol específico)"""
    try:
        facebook_email = request.form.get('facebook_email', '').strip().lower()
        rol = request.form.get('rol', 'Trabajador')
        
        print(f"Procesando registro con Facebook para: {facebook_email} como {rol}")
        
        # Validar email de Facebook
        valid_domains = ['@hotmail.com', '@outlook.com', '@live.com', '@msn.com']
        if not facebook_email or not any(facebook_email.endswith(domain) for domain in valid_domains):
            redirect_url = '/vista/registro-agricultor.html' if rol == 'Agricultor' else '/vista/registro-trabajador.html'
            return redirect(f'{redirect_url}?message=Por favor ingresa un correo válido asociado a Facebook&type=error')
        
        # Verificar si el usuario ya existe
        existing_user = execute_query(
            "SELECT * FROM Usuario WHERE Correo = %s",
            (facebook_email,),
            fetch_one=True
        )
        
        if existing_user:
            # Usuario existe, iniciar sesión
            user = existing_user
            print(f"Usuario existente encontrado: {existing_user['Nombre']}")
        else:
            # Crear nuevo usuario
            user_id = create_social_user_real(facebook_email, 'facebook', rol)
            if not user_id:
                redirect_url = '/vista/registro-agricultor.html' if rol == 'Agricultor' else '/vista/registro-trabajador.html'
                return redirect(f'{redirect_url}?message=Error creando usuario con Facebook&type=error')
            
            user = execute_query(
                "SELECT * FROM Usuario WHERE ID_Usuario = %s",
                (user_id,),
                fetch_one=True
            )
        
        # Crear sesión
        session['user_id'] = user['ID_Usuario']
        session['username'] = user['Correo']
        session['first_name'] = user['Nombre']
        session['last_name'] = user['Apellido']
        session['email'] = user['Correo']
        session['user_role'] = user['Rol']
        session['user_name'] = f"{user['Nombre']} {user['Apellido']}"
        session['telefono'] = user.get('Telefono', '')
        
        session.pop('oauth_rol', None)
        
        print(f"Registro/Login exitoso con Facebook: {user['Nombre']} - Rol: {user['Rol']}")
        
        # Redireccionar según el rol
        if user['Rol'] == 'Agricultor':
            return redirect('/vista/index-agricultor.html')
        else:
            return redirect('/vista/index-trabajador.html')
        
    except Exception as e:
        print(f"Error procesando registro Facebook: {str(e)}")
        return redirect('/vista/registro-trabajador.html?message=Error con Facebook&type=error')

# También necesitas la función auxiliar si no la tienes:
def create_social_user_real(email, provider, rol='Trabajador'):
    """Crea un usuario real desde email de red social"""
    try:
        # Extraer información del email
        user_info = extract_info_from_email(email, provider)
        if not user_info:
            return None
        
        # Generar contraseña temporal hasheada
        temp_password = hash_password(f"{email}_social_{provider}_{uuid.uuid4()}")
        
        # URL de foto por defecto según el proveedor
        if provider == 'google':
            foto_url = "/static/uploads/profile_photos/default_google_user.jpg"
        else:
            foto_url = "/static/uploads/profile_photos/default_facebook_user.jpg"
        
        # Insertar en base de datos
        user_id = execute_query(
            """INSERT INTO Usuario (Nombre, Apellido, Correo, Contrasena, URL_Foto, 
                                   Red_Social, Rol, Estado) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'Activo')""",
            (
                user_info['nombre'],
                user_info['apellido'], 
                email,
                temp_password,
                foto_url,
                f"{provider}:{user_info['username']}",
                rol
            )
        )
        
        print(f"Usuario real creado desde {provider}: {email} - Rol: {rol}")
        return user_id
        
    except Exception as e:
        print(f"Error creando usuario social real: {str(e)}")
        return None

def extract_info_from_email(email, provider):
    """Extrae información básica del email para crear el usuario"""
    try:
        import re
        # Extraer nombre del email (parte antes del @)
        username = email.split('@')[0]
        
        # Limpiar números y caracteres especiales
        clean_name = re.sub(r'[0-9._-]', ' ', username).strip()
        
        # Dividir en nombre y apellido
        name_parts = clean_name.split()
        
        if len(name_parts) >= 2:
            nombre = name_parts[0].capitalize()
            apellido = ' '.join(name_parts[1:]).title()
        elif len(name_parts) == 1:
            nombre = name_parts[0].capitalize()
            apellido = "Usuario"
        else:
            nombre = "Usuario"
            apellido = provider.capitalize()
        
        return {
            'nombre': nombre,
            'apellido': apellido,
            'email': email,
            'username': username,
            'provider': provider
        }
        
    except Exception as e:
        print(f"Error extrayendo info del email: {str(e)}")
        return None

print("✅ Rutas de procesamiento social agregadas correctamente")


@auth_bp.route('/vista/login-trabajador.html')
def login_trabajador_html():
    """Página de login"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vista_path = os.path.join(base_dir, '..', '..', 'vista')
        vista_path = os.path.abspath(vista_path)
        return send_from_directory(vista_path, 'login-trabajador.html')
    except Exception as e:
        print(f"Error sirviendo login-trabajador.html: {e}")
        return "Archivo no encontrado", 404


@auth_bp.route('/vista/registro-trabajador.html')
def registro_trabajador_html():
    """Página de registro del trabajador"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vista_path = os.path.join(base_dir, '..', '..', 'vista')
        vista_path = os.path.abspath(vista_path)
        return send_from_directory(vista_path, 'registro-trabajador.html')
    except Exception as e:
        print(f"Error sirviendo registro-trabajador.html: {e}")
        return "Archivo no encontrado", 404


# ================================================================
# MODIFICAR LA FUNCIÓN DE LOGIN EXISTENTE
# Reemplaza tu función login() existente con esta versión actualizada
# ================================================================

@auth_bp.route('/login.py', methods=['POST'])
def login_actualizado():
    """Procesa el login de usuarios - VERSIÓN ACTUALIZADA CON ADMINISTRADOR"""
    
    try:
        # Recoger datos del formulario
        email = request.form.get('email', '').strip()
        password = request.form.get('contrasena', '')
        
        print(f"🔐 Intento de login para: {email}")
        
        # Validaciones básicas
        if not email or not password:
            raise Exception('Por favor completa todos los campos.')
        
        # Buscar usuario en la base de datos
        user = execute_query(
            """SELECT u.ID_Usuario, u.Nombre, u.Apellido, u.Correo, u.Contrasena, u.Rol, u.Estado, u.Telefono
               FROM Usuario u 
               WHERE u.Correo = %s OR u.Telefono = %s""",
            (email, email),
            fetch_one=True
        )
        
        if not user:
            raise Exception('Credenciales incorrectas.')
        
        # Verificar contraseña
        if not verify_password(password, user['Contrasena']):
            raise Exception('Credenciales incorrectas.')
        
        # Verificar que el usuario esté activo
        if user['Estado'] != 'Activo':
            raise Exception('Tu cuenta está inactiva. Contacta al administrador.')
        
        # Crear sesión con todos los datos necesarios
        session['user_id'] = user['ID_Usuario']
        session['username'] = user['Correo']
        session['first_name'] = user['Nombre']
        session['last_name'] = user['Apellido']
        session['email'] = user['Correo']
        session['user_role'] = user['Rol']
        session['role'] = user['Rol']
        session['user_name'] = f"{user['Nombre']} {user['Apellido']}"
        session['telefono'] = user.get('Telefono', '')
        
        print(f"✅ Login exitoso para: {user['Nombre']} {user['Apellido']} - Rol: {user['Rol']}")
        print(f"📊 Datos de sesión guardados: ID={user['ID_Usuario']}, Role={user['Rol']}")
        
        # Redireccionar según el rol - ACTUALIZADO PARA INCLUIR ADMINISTRADOR
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        if user['Rol'] == 'Agricultor':
            redirect_url = '/vista/index-agricultor.html'
            dashboard_path = os.path.join(base_dir, '..', '..', 'vista', 'index-agricultor.html')
            
        elif user['Rol'] == 'Trabajador':
            redirect_url = '/vista/index-trabajador.html'
            dashboard_path = os.path.join(base_dir, '..', '..', 'vista', 'index-trabajador.html')
            
        elif user['Rol'] == 'Administrador':
            redirect_url = '/vista/index-administrador.html'
            dashboard_path = os.path.join(base_dir, '..', '..', 'vista', 'index-administrador.html')
            print("🔄 Preparando redirección a dashboard de ADMINISTRADOR")
            
        else:
            raise Exception('Rol de usuario no válido.')
        
        # Verificar que el archivo existe
        if not os.path.exists(dashboard_path):
            print(f"❌ DASHBOARD NO EXISTE: {dashboard_path}")
            # Fallback a un dashboard genérico
            redirect_url = '/vista/index-trabajador.html'
        else:
            print(f"✅ Dashboard encontrado: {dashboard_path}")
        
        print(f"🎯 Redirigiendo a: {redirect_url}")
        return redirect(redirect_url)
        
    except Exception as e:
        print(f"❌ Error en login: {str(e)}")
        
        # Redireccionar con error
        referer = request.headers.get('Referer', '')
        if 'login-trabajador.html' in referer:
            login_page = '/vista/login-trabajador.html'
        else:
            login_page = '/vista/login-trabajador.html'
        
        error_message = quote(str(e))
        return redirect(f"{login_page}?message={error_message}&type=error")


# ================================================================
# ACTUALIZAR LA FUNCIÓN dashboard_admin EXISTENTE
# ================================================================

@auth_bp.route('/dashboard-admin')
def dashboard_admin_actualizado():
    """Ruta para el dashboard del administrador - VERSIÓN ACTUALIZADA"""
    if 'user_id' not in session:
        print("❌ Usuario no autenticado, redirigiendo a login")
        return redirect('/vista/login-trabajador.html')
    
    # Verificar que el usuario sea administrador
    if session.get('user_role') != 'Administrador':
        print(f"❌ Usuario no es administrador: {session.get('user_role')}")
        # Redireccionar según su rol actual
        if session.get('user_role') == 'Agricultor':
            return redirect('/vista/index-agricultor.html')
        else:
            return redirect('/vista/index-trabajador.html')
    
    print(f"✅ Acceso autorizado al dashboard de administrador: {session.get('user_name')}")
    return redirect('/vista/index-administrador.html')


# ============================================================
# ENDPOINT 1: GET USER SESSION (ÚNICO Y CORRECTO)
# ============================================================

@auth_bp.route('/get_user_session')
def get_user_session():
    """Obtener datos completos de sesión con configuraciones JSON"""
    try:
        if 'user_id' not in session:
            print("⚠️ No hay sesión activa")
            return jsonify({
                'success': False,
                'error': 'No hay sesión activa'
            }), 401
        
        user_id = session.get('user_id')
        print(f"📥 Obteniendo sesión para usuario ID: {user_id}")
        
        # Obtener datos del usuario
        user_data = execute_query(
            """SELECT 
                ID_Usuario, 
                Nombre, 
                Apellido, 
                Correo, 
                Telefono, 
                URL_Foto, 
                Red_Social, 
                Rol, 
                Estado, 
                Fecha_Registro,
                Configuraciones
            FROM Usuario 
            WHERE ID_Usuario = %s""",
            (user_id,),
            fetch_one=True
        )
        
        if not user_data:
            print(f"❌ Usuario {user_id} no encontrado")
            return jsonify({
                'success': False,
                'error': 'Usuario no encontrado'
            }), 404
        
        # Parsear configuraciones JSON
        import json
        configuraciones = {}
        
        if user_data.get('Configuraciones'):
            try:
                configuraciones = json.loads(user_data['Configuraciones'])
                print(f"✅ Configuraciones JSON leídas: {configuraciones}")
            except json.JSONDecodeError as e:
                print(f"⚠️ Error decodificando JSON: {e}")
                configuraciones = {}
        else:
            print("ℹ️ No hay configuraciones guardadas")
        
        # Obtener estadísticas
        stats = execute_query("""
            SELECT 
                COUNT(DISTINCT al.ID_Acuerdo) as trabajos_completados,
                AVG(CAST(c.Puntuacion AS DECIMAL)) as calificacion_promedio
            FROM Usuario u
            LEFT JOIN Acuerdo_Laboral al ON u.ID_Usuario = al.ID_Trabajador AND al.Estado = 'Finalizado'
            LEFT JOIN Calificacion c ON u.ID_Usuario = c.ID_Usuario_Receptor
            WHERE u.ID_Usuario = %s
        """, (user_id,), fetch_one=True)
        
        # Actualizar sesión con datos frescos
        session['first_name'] = user_data['Nombre']
        session['last_name'] = user_data['Apellido']
        session['email'] = user_data['Correo']
        session['user_name'] = f"{user_data['Nombre']} {user_data['Apellido']}"
        session['telefono'] = user_data.get('Telefono', '')
        
        # Construir respuesta
        response_data = {
            'success': True,
            'user': {
                'user_id': user_data['ID_Usuario'],
                'id': user_data['ID_Usuario'],
                'full_name': f"{user_data['Nombre']} {user_data['Apellido']}",
                'user_name': f"{user_data['Nombre']} {user_data['Apellido']}",
                'nombre': user_data['Nombre'],
                'apellido': user_data['Apellido'],
                'first_name': user_data['Nombre'],
                'last_name': user_data['Apellido'],
                'email': user_data['Correo'],
                'telefono': user_data.get('Telefono', ''),
                'url_foto': user_data.get('URL_Foto'),
                'red_social': user_data.get('Red_Social', ''),
                'rol': user_data['Rol'],
                'role': user_data['Rol'],
                'estado': user_data['Estado'],
                'fecha_registro': user_data['Fecha_Registro'].isoformat() if user_data.get('Fecha_Registro') else None,
                'username': user_data['Correo'],
                
                # CAMPOS PROFESIONALES desde JSON
                'area_trabajo': configuraciones.get('area_trabajo'),
                'especializacion': configuraciones.get('especializacion'),
                'anos_experiencia': configuraciones.get('anos_experiencia', 0),
                'nivel_educativo': configuraciones.get('nivel_educativo'),
                'ubicacion': configuraciones.get('ubicacion'),
                
                # ESTADÍSTICAS
                'trabajos_completados': stats['trabajos_completados'] if stats else 0,
                'calificacion_promedio': float(stats['calificacion_promedio']) if stats and stats['calificacion_promedio'] else 0.0
            }
        }
        
        print(f"✅ Sesión obtenida correctamente para {user_data['Nombre']} {user_data['Apellido']}")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Error en get_user_session: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error interno: {str(e)}'
        }), 500


# ================================================================
# ENDPOINT: OBTENER SESIÓN DE USUARIO (ACTUALIZADO CON IDIOMA)
# ================================================================

@auth_bp.route('/get_user_session', methods=['GET'])
def get_user_session_with_language():
    """Obtiene la información del usuario incluyendo el idioma"""
    try:
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'message': 'No hay sesión activa'
            }), 401
        
        user_id = session['user_id']
        
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="camp"
        )
        cursor = conexion.cursor(dictionary=True)
        
        # Obtener información del usuario incluyendo idioma
        query = """
            SELECT 
                ID_Usuario,
                Nombre,
                Apellido,
                Correo,
                Telefono,
                URL_Foto,
                Red_Social,
                Rol,
                Estado,
                Idioma,
                Fecha_Registro
            FROM Usuario
            WHERE ID_Usuario = %s
        """
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
        
        cursor.close()
        conexion.close()
        
        if user:
            # Formatear datos del usuario
            user_data = {
                'id': user['ID_Usuario'],
                'first_name': user['Nombre'],
                'last_name': user['Apellido'],
                'full_name': f"{user['Nombre']} {user['Apellido']}",
                'email': user['Correo'],
                'telefono': user['Telefono'],
                'url_foto': user['URL_Foto'],
                'red_social': user['Red_Social'],
                'role': user['Rol'],
                'estado': user['Estado'],
                'language': user.get('Idioma', 'es') or 'es',  # Default a 'es' si es NULL
                'fecha_registro': user['Fecha_Registro'].isoformat() if user['Fecha_Registro'] else None
            }
            
            return jsonify({
                'success': True,
                'user': user_data
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404
            
    except Exception as e:
        print(f"❌ Error obteniendo sesión: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


# ================================================================
# SCRIPT PARA VERIFICAR/CREAR LA COLUMNA IDIOMA
# ================================================================

def verificar_columna_idioma():
    """Verifica y crea la columna Idioma si no existe"""
    try:
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="camp"
        )
        cursor = conexion.cursor(dictionary=True)
        
        # Verificar si existe la columna
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'camp' 
            AND TABLE_NAME = 'Usuario' 
            AND COLUMN_NAME = 'Idioma'
        """)
        exists = cursor.fetchone()
        
        if not exists:
            print("⚠️ Columna 'Idioma' no existe. Creándola...")
            cursor.execute("""
                ALTER TABLE Usuario 
                ADD COLUMN Idioma VARCHAR(5) DEFAULT 'es' 
                AFTER Red_Social
            """)
            conexion.commit()
            print("✅ Columna 'Idioma' creada exitosamente")
        else:
            print("✅ Columna 'Idioma' ya existe")
        
        cursor.close()
        conexion.close()
        
    except Exception as e:
        print(f"❌ Error verificando columna: {str(e)}")

# Ejecutar verificación al iniciar la aplicación

print("✅ Endpoints de idioma cargados correctamente:")
print("   - POST /api/actualizar-idioma-usuario")
print("   - GET  /get_user_session (actualizado con idioma)")


# ================================================================
# AGREGAR ESTOS ENDPOINTS AL FINAL DE TU app.py (ANTES DEL if __name__)
# ================================================================

from math import radians, cos, sin, asin, sqrt

def calcular_distancia(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia en kilómetros entre dos puntos usando la fórmula de Haversine
    """
    # Convertir grados a radianes
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    
    # Fórmula de Haversine
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radio de la Tierra en kilómetros
    
    return c * r


@auth_bp.route('/reset-password', methods=['GET'])
def reset_password_page():
    token = request.args.get('token')
    
    if not token or token not in password_reset_tokens:
        return redirect('/vista/login-trabajador.html?message=Token inválido&type=error')
    
    token_data = password_reset_tokens[token]
    
    if datetime.now() > token_data['expires_at'] or token_data['used']:
        return redirect('/vista/login-trabajador.html?message=Token expirado&type=error')
    
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Restablecer Contraseña</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:linear-gradient(135deg,#1e3a2e 0%,#2d5a27 35%,#4a7c59 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}
.container{{background:white;padding:50px;border-radius:20px;box-shadow:0 15px 50px rgba(0,0,0,0.2);max-width:500px;width:100%}}
.header{{text-align:center;margin-bottom:40px}}
.header i{{font-size:4rem;color:#4a7c59;margin-bottom:20px}}
.header h1{{color:#1e3a2e;font-size:2rem;margin-bottom:10px}}
.form-group{{margin-bottom:25px}}
.form-group label{{display:block;color:#1e3a2e;font-weight:600;margin-bottom:10px}}
.input-container{{position:relative}}
.input-container input{{width:100%;padding:15px 15px 15px 45px;border:2px solid #e2e8f0;border-radius:10px;font-size:1rem}}
.input-container input:focus{{outline:none;border-color:#4a7c59;box-shadow:0 0 0 4px rgba(74,124,89,0.1)}}
.input-icon{{position:absolute;left:15px;top:50%;transform:translateY(-50%);color:#64748b}}
.toggle-password{{position:absolute;right:15px;top:50%;transform:translateY(-50%);color:#64748b;cursor:pointer}}
.btn-submit{{width:100%;padding:16px;background:linear-gradient(135deg,#4a7c59 0%,#2d5a27 100%);color:white;border:none;border-radius:10px;font-size:1.1rem;font-weight:600;cursor:pointer;margin-top:30px}}
.btn-submit:hover{{transform:translateY(-2px);box-shadow:0 8px 20px rgba(74,124,89,0.3)}}
.btn-submit:disabled{{background:#94a3b8;cursor:not-allowed}}
.alert{{padding:15px;border-radius:10px;margin-bottom:20px;display:none}}
.alert-error{{background:#fee;color:#c00}}
.alert-success{{background:#efe;color:#060}}
.requirements{{background:#f8f9fa;border:1px solid #e2e8f0;border-radius:10px;padding:15px;margin-top:20px}}
.requirement{{display:flex;align-items:center;gap:10px;color:#64748b;font-size:0.85rem;margin-bottom:5px}}
.requirement.valid{{color:#22c55e}}
</style></head><body>
<div class="container">
<div class="header"><i class="fas fa-key"></i><h1>Restablecer Contraseña</h1><p>Ingresa tu nueva contraseña</p></div>
<div id="alert" class="alert"></div>
<form id="resetForm">
<input type="hidden" id="token" value="{token}">
<div class="form-group"><label>Nueva Contraseña</label>
<div class="input-container">
<i class="fas fa-lock input-icon"></i>
<input type="password" id="new_password" required>
<i class="fas fa-eye toggle-password" onclick="togglePwd('new_password')"></i>
</div></div>
<div class="form-group"><label>Confirmar Contraseña</label>
<div class="input-container">
<i class="fas fa-lock input-icon"></i>
<input type="password" id="confirm_password" required>
<i class="fas fa-eye toggle-password" onclick="togglePwd('confirm_password')"></i>
</div></div>
<div class="requirements"><h4>Requisitos:</h4>
<div class="requirement" id="req-length"><i class="fas fa-circle"></i><span>Mínimo 8 caracteres</span></div>
<div class="requirement" id="req-upper"><i class="fas fa-circle"></i><span>Una mayúscula</span></div>
<div class="requirement" id="req-lower"><i class="fas fa-circle"></i><span>Una minúscula</span></div>
<div class="requirement" id="req-number"><i class="fas fa-circle"></i><span>Un número</span></div>
</div>
<button type="submit" class="btn-submit" id="submitBtn">Restablecer Contraseña</button>
</form></div>
<script>
function togglePwd(id){{const input=document.getElementById(id);const icon=input.nextElementSibling;if(input.type==='password'){{input.type='text';icon.classList.remove('fa-eye');icon.classList.add('fa-eye-slash')}}else{{input.type='password';icon.classList.remove('fa-eye-slash');icon.classList.add('fa-eye')}}}}
function showAlert(msg,type){{const alert=document.getElementById('alert');alert.textContent=msg;alert.className=`alert alert-${{type}}`;alert.style.display='block'}}
function validatePassword(pwd){{const reqs={{length:pwd.length>=8,upper:/[A-Z]/.test(pwd),lower:/[a-z]/.test(pwd),number:/[0-9]/.test(pwd)}};document.getElementById('req-length').classList.toggle('valid',reqs.length);document.getElementById('req-upper').classList.toggle('valid',reqs.upper);document.getElementById('req-lower').classList.toggle('valid',reqs.lower);document.getElementById('req-number').classList.toggle('valid',reqs.number);return Object.values(reqs).every(v=>v)}}
document.getElementById('new_password').addEventListener('input',function(){{validatePassword(this.value)}});
document.getElementById('resetForm').addEventListener('submit',async function(e){{e.preventDefault();const newPwd=document.getElementById('new_password').value;const confirmPwd=document.getElementById('confirm_password').value;const btn=document.getElementById('submitBtn');if(!validatePassword(newPwd)){{showAlert('La contraseña no cumple los requisitos','error');return}}if(newPwd!==confirmPwd){{showAlert('Las contraseñas no coinciden','error');return}}btn.disabled=true;btn.innerHTML='Procesando...';try{{const response=await fetch('/api/reset-password',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{token:document.getElementById('token').value,new_password:newPwd}})}});const data=await response.json();if(data.success){{showAlert('¡Contraseña actualizada! Redirigiendo...','success');setTimeout(()=>{{window.location.href='/vista/login-trabajador.html?message=Contraseña actualizada correctamente&type=success'}},2000)}}else{{showAlert(data.message,'error');btn.disabled=false;btn.innerHTML='Restablecer Contraseña'}}}}catch(error){{showAlert('Error de conexión','error');btn.disabled=false;btn.innerHTML='Restablecer Contraseña'}}}});
</script></body></html>"""


@auth_bp.route('/api/reset-password', methods=['POST'])
def process_password_reset():
    try:
        data = request.get_json()
        token = data.get('token')
        new_password = data.get('new_password')
        
        if not token or not new_password or len(new_password) < 8:
            return jsonify({'success': False, 'message': 'Datos inválidos'}), 400
        
        token_data = password_reset_tokens.get(token)
        
        if not token_data or datetime.now() > token_data['expires_at'] or token_data['used']:
            return jsonify({'success': False, 'message': 'Token inválido'}), 400
        
        hashed_password = hash_password(new_password)
        execute_query("UPDATE Usuario SET Contrasena = %s WHERE ID_Usuario = %s",
                     (hashed_password, token_data['user_id']))
        
        token_data['used'] = True
        print(f"✅ Contraseña actualizada para usuario {token_data['user_id']}")
        
        return jsonify({'success': True, 'message': 'Contraseña actualizada'})
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'success': False, 'message': 'Error interno'}), 500

print("✅ Sistema de recuperación cargado")

# ================================================================

# Inicializar Flask-Mail

print("✅ Flask-Mail configurado correctamente")

