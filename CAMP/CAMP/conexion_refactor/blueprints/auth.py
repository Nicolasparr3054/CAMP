# Blueprint: auth
from flask import Blueprint, request, redirect, url_for, session, jsonify, render_template, send_from_directory, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, timedelta
from urllib.parse import quote, unquote
from math import radians, cos, sin, asin, sqrt
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

# ================================================================
# VARIABLES GLOBALES
# ================================================================

# Tokens de recuperación de contraseña (en memoria)
password_reset_tokens = {}

# Usuarios demo de Google
GOOGLE_USERS_DEMO = {
    'google_demo_1': {
        'given_name': 'Carlos',
        'family_name': 'Ramírez',
        'email': 'carlos.ramirez@gmail.com',
        'sub': 'google_demo_001'
    },
    'google_demo_2': {
        'given_name': 'María',
        'family_name': 'López',
        'email': 'maria.lopez@gmail.com',
        'sub': 'google_demo_002'
    },
    'google_demo_3': {
        'given_name': 'Juan',
        'family_name': 'García',
        'email': 'juan.garcia@gmail.com',
        'sub': 'google_demo_003'
    }
}

# Usuarios demo de Facebook
FACEBOOK_USERS_DEMO = {
    'facebook_demo_1': {
        'first_name': 'Andrés',
        'last_name': 'Torres',
        'email': 'andres.torres@hotmail.com',
        'id': 'fb_demo_001'
    },
    'facebook_demo_2': {
        'first_name': 'Luisa',
        'last_name': 'Herrera',
        'email': 'luisa.herrera@outlook.com',
        'id': 'fb_demo_002'
    },
    'facebook_demo_3': {
        'first_name': 'Pedro',
        'last_name': 'Martínez',
        'email': 'pedro.martinez@hotmail.com',
        'id': 'fb_demo_003'
    }
}


# ================================================================
# HELPERS LOCALES
# ================================================================

def get_db_connection_local():
    try:
        connection = mysql.connector.connect(
            host='localhost', database='camp', user='root', password='123456',
            charset='utf8mb4', collation='utf8mb4_unicode_ci'
        )
        return connection
    except mysql.connector.Error as e:
        logger.error(f"Error conectando a la base de datos: {e}")
        raise

def no_cache(view):
    @wraps(view)
    def no_cache_view(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
    return no_cache_view

def validate_email(email):
    return bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email))

def validate_name(name):
    return bool(re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', name))

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return check_password_hash(hashed, password)

def calcular_distancia(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return c * 6371


# ================================================================
# BLUEPRINT
# ================================================================

auth_bp = Blueprint('auth', __name__)
from blueprints.helpers import require_login, require_role, hash_password, verify_password, no_cache


# ================================================================
# FUNCIONES AUXILIARES PARA REDES SOCIALES
# ================================================================

def extract_info_from_email(email, provider):
    """Extrae información básica del email para crear el usuario"""
    try:
        username = email.split('@')[0]
        clean_name = re.sub(r'[0-9._-]', ' ', username).strip()
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
        user_info = extract_info_from_email(email, provider)
        if not user_info:
            return None

        temp_password = hash_password(f"{email}_social_{provider}_{uuid.uuid4()}")

        if provider == 'google':
            foto_url = "/static/uploads/profile_photos/default_google_user.jpg"
        else:
            foto_url = "/static/uploads/profile_photos/default_facebook_user.jpg"

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


def create_demo_user(user_data, provider, rol='Trabajador'):
    """Crea un usuario demo para pruebas de OAuth"""
    try:
        if provider == 'google':
            nombre = user_data.get('given_name', 'Demo')
            apellido = user_data.get('family_name', 'Usuario')
        else:
            nombre = user_data.get('first_name', 'Demo')
            apellido = user_data.get('last_name', 'Usuario')

        email = user_data.get('email', '')
        temp_password = hash_password(f"demo_{provider}_{uuid.uuid4()}")
        foto_url = f"/static/uploads/profile_photos/default_{provider}_user.jpg"

        user_id = execute_query(
            """INSERT INTO Usuario (Nombre, Apellido, Correo, Contrasena, URL_Foto,
                                   Red_Social, Rol, Estado)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'Activo')""",
            (nombre, apellido, email, temp_password, foto_url,
             f"{provider}:demo", rol)
        )
        return user_id
    except Exception as e:
        print(f"Error creando usuario demo: {str(e)}")
        return None


def send_reset_email(to_email, nombre, reset_url):
    """Envía el correo de recuperación de contraseña"""
    try:
        MAIL_USER = os.environ.get('MAIL_USERNAME', '')
        MAIL_PASS = os.environ.get('MAIL_PASSWORD', '')
        MAIL_HOST = 'smtp.gmail.com'
        MAIL_PORT = 587

        if not MAIL_USER or not MAIL_PASS:
            print("⚠️ MAIL_USERNAME o MAIL_PASSWORD no configurados en .env")
            return False

        msg = MIMEMultipart('alternative')
        msg['Subject'] = '🔑 Restablece tu contraseña — CAMP'
        msg['From'] = f'CAMP <{MAIL_USER}>'
        msg['To'] = to_email

        html_body = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
          <meta charset="UTF-8">
          <style>
            body {{ font-family: 'Segoe UI', sans-serif; background: #f2ede3; margin: 0; padding: 0; }}
            .wrapper {{ max-width: 560px; margin: 40px auto; background: #faf7f0; border-radius: 16px; overflow: hidden; box-shadow: 0 8px 32px rgba(0,0,0,.10); }}
            .header {{ background: #1e3d16; padding: 36px 40px; text-align: center; }}
            .header h1 {{ color: #fff; font-size: 1.5rem; margin: 16px 0 0; font-weight: 600; }}
            .body {{ padding: 40px; }}
            .body p {{ color: #4a3118; font-size: .95rem; line-height: 1.8; margin-bottom: 16px; }}
            .btn {{ display: inline-block; padding: 16px 36px; background: #1e3d16; color: #fff !important; text-decoration: none; border-radius: 10px; font-weight: 600; font-size: 1rem; margin: 20px 0; }}
            .note {{ font-size: .8rem; color: #8b5e2d; background: #f2e0c4; border-radius: 8px; padding: 12px 16px; }}
            .footer {{ background: #e8e1d4; padding: 20px 40px; text-align: center; font-size: .75rem; color: #8b5e2d; }}
            .url-fallback {{ word-break: break-all; font-size: .75rem; color: #4a7a34; }}
          </style>
        </head>
        <body>
          <div class="wrapper">
            <div class="header">
              <h1>🌱 CAMP</h1>
              <p style="color:#b8d89f;margin:8px 0 0;font-size:.9rem;">Plataforma agrícola · Colombia</p>
            </div>
            <div class="body">
              <p>Hola <strong>{nombre}</strong>,</p>
              <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta en CAMP. Haz clic en el botón para continuar:</p>
              <div style="text-align:center">
                <a href="{reset_url}" class="btn">Restablecer contraseña</a>
              </div>
              <div class="note">
                ⏱ Este enlace expirará en <strong>30 minutos</strong>. Si no solicitaste este cambio, ignora este correo — tu cuenta sigue segura.
              </div>
              <p style="margin-top:24px;font-size:.82rem;">Si el botón no funciona, copia y pega este enlace en tu navegador:</p>
              <p class="url-fallback">{reset_url}</p>
            </div>
            <div class="footer">
              © 2026 CAMP · Conexión Agrícola y Mercado de Personal · Colombia<br>
              Este correo fue enviado automáticamente, no respondas a este mensaje.
            </div>
          </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(MAIL_HOST, MAIL_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(MAIL_USER, MAIL_PASS)
            server.sendmail(MAIL_USER, to_email, msg.as_string())

        return True
    except Exception as e:
        print(f"❌ Error enviando correo: {str(e)}")
        return False


# ================================================================
# RUTAS DE ARCHIVOS ESTÁTICOS
# ================================================================

@auth_bp.route('/dashboard-trabajador.css')
def serve_dashboard_trabajador_css():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vista_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'vista'))
        response = send_from_directory(vista_path, 'index-trabajador.css')
        response.headers['Content-Type'] = 'text/css'
        return response
    except Exception as e:
        return f"Error sirviendo CSS: {str(e)}", 500


@auth_bp.route('/dashboard-trabajador.js')
def serve_dashboard_trabajador_js():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vista_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'vista'))
        response = send_from_directory(vista_path, 'index-trabajador.js')
        response.headers['Content-Type'] = 'application/javascript'
        return response
    except Exception as e:
        return f"Error sirviendo JS: {str(e)}", 500


@auth_bp.route('/vista/dashboard-agricultor.html')
def serve_dashboard_agricultor():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vista_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'vista'))
        return send_from_directory(vista_path, 'dashboard-agricultor.html')
    except Exception as e:
        print(f"❌ Error sirviendo dashboard del agricultor: {str(e)}")
        return f"Error sirviendo dashboard: {str(e)}", 500


@auth_bp.route('/vista/login-trabajador.html')
def login_trabajador_html():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vista_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'vista'))
        return send_from_directory(vista_path, 'login-trabajador.html')
    except Exception as e:
        print(f"Error sirviendo login-trabajador.html: {e}")
        return "Archivo no encontrado", 404


@auth_bp.route('/vista/registro-trabajador.html')
def registro_trabajador_html():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vista_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'vista'))
        return send_from_directory(vista_path, 'registro-trabajador.html')
    except Exception as e:
        print(f"Error sirviendo registro-trabajador.html: {e}")
        return "Archivo no encontrado", 404


# ================================================================
# REGISTRO
# ================================================================

@auth_bp.route('/registro.py', methods=['POST'])
def registro():
    """Procesa el registro de usuarios (Trabajador o Agricultor)"""
    rol = ''
    try:
        nombre = request.form.get('nombre', '').strip()
        apellido = request.form.get('apellido', '').strip()
        correo = request.form.get('correo', '').strip()
        telefono = request.form.get('telefono', '').strip() or None
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        rol = request.form.get('rol', '').strip()

        print(f"=== NUEVO REGISTRO === Nombre: {nombre} | Rol: '{rol}'")

        errores = []
        if not nombre or not validate_name(nombre):
            errores.append('El nombre es obligatorio y solo puede contener letras')
        if not apellido or not validate_name(apellido):
            errores.append('El apellido es obligatorio y solo puede contener letras')
        if not correo or not validate_email(correo):
            errores.append('El correo electrónico no es válido')
        if not password or len(password) < 8:
            errores.append('La contraseña debe tener mínimo 8 caracteres')
        if password != confirm_password:
            errores.append('Las contraseñas no coinciden')
        if rol not in ['Trabajador', 'Agricultor']:
            errores.append('Tipo de usuario no válido')
        if not request.form.get('terminos'):
            errores.append('Debe aceptar los términos y condiciones')

        if errores:
            raise Exception('<br>'.join(errores))

        existing_user = execute_query(
            "SELECT ID_Usuario FROM Usuario WHERE Correo = %s",
            (correo,), fetch_one=True
        )
        if existing_user:
            raise Exception(f'El correo ya está registrado. <a href="/vista/login-trabajador.html">Inicia sesión aquí</a>')

        hashed_password = hash_password(password)
        execute_query(
            "INSERT INTO Usuario (Nombre, Apellido, Correo, Contrasena, Telefono, Rol) VALUES (%s, %s, %s, %s, %s, %s)",
            (nombre, apellido, correo, hashed_password, telefono, rol)
        )

        print(f"✅ Usuario registrado: {correo} como {rol}")
        mensaje = f"¡Registro exitoso {nombre}! Ahora puedes iniciar sesión."
        return redirect(f"/vista/login-trabajador.html?message={quote(mensaje)}&type=success")

    except Exception as e:
        print(f"❌ Error en registro: {str(e)}")
        return_url = '/vista/registro-agricultor.html' if rol == 'Agricultor' else '/vista/registro-trabajador.html'
        return redirect(f"{return_url}?message={quote(str(e))}&type=error")


# ================================================================
# LOGIN
# ================================================================

@auth_bp.route('/login.py', methods=['POST'])
def login():
    """Procesa el login de usuarios"""
    try:
        email = request.form.get('email', '').strip()
        password = request.form.get('contrasena', '')

        print(f"🔐 Intento de login para: {email}")

        if not email or not password:
            raise Exception('Por favor completa todos los campos.')

        user = execute_query(
            """SELECT ID_Usuario, Nombre, Apellido, Correo, Contrasena, Rol, Estado, Telefono
               FROM Usuario WHERE Correo = %s OR Telefono = %s""",
            (email, email), fetch_one=True
        )

        if not user or not verify_password(password, user['Contrasena']):
            raise Exception('Credenciales incorrectas.')

        if user['Estado'] != 'Activo':
            raise Exception('Tu cuenta está inactiva. Contacta al administrador.')

        session['user_id'] = user['ID_Usuario']
        session['username'] = user['Correo']
        session['first_name'] = user['Nombre']
        session['last_name'] = user['Apellido']
        session['email'] = user['Correo']
        session['user_role'] = user['Rol']
        session['role'] = user['Rol']
        session['user_name'] = f"{user['Nombre']} {user['Apellido']}"
        session['telefono'] = user.get('Telefono', '')

        print(f"✅ Login exitoso: {user['Nombre']} - Rol: {user['Rol']}")

        if user['Rol'] == 'Agricultor':
            redirect_url = '/vista/index-agricultor.html'
        elif user['Rol'] == 'Trabajador':
            redirect_url = '/vista/index-trabajador.html'
        elif user['Rol'] == 'Administrador':
            redirect_url = '/vista/index-administrador.html'
        else:
            raise Exception('Rol de usuario no válido.')

        return redirect(redirect_url)

    except Exception as e:
        print(f"❌ Error en login: {str(e)}")
        return redirect(f"/vista/login-trabajador.html?message={quote(str(e))}&type=error")


# ================================================================
# RECUPERACIÓN DE CONTRASEÑA
# ================================================================

@auth_bp.route('/api/request-password-reset', methods=['POST'])
def request_password_reset():
    """
    Genera token de recuperación y envía correo.
    Llamado desde login-trabajador.js cuando el usuario
    usa el modal '¿Olvidaste tu contraseña?'
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Datos inválidos'}), 400

        email = data.get('email', '').strip().lower()

        if not email:
            return jsonify({'success': False, 'message': 'El correo es requerido'}), 400

        if not validate_email(email):
            return jsonify({'success': False, 'message': 'Correo electrónico inválido'}), 400

        user = execute_query(
            "SELECT ID_Usuario, Nombre, Apellido, Correo, Estado FROM Usuario WHERE Correo = %s",
            (email,), fetch_one=True
        )

        # Por seguridad respondemos igual aunque el correo no exista
        if not user:
            print(f"⚠️ Solicitud de reset para correo no registrado: {email}")
            return jsonify({
                'success': True,
                'message': 'Si el correo existe, recibirás el enlace en breve.'
            })

        if user['Estado'] != 'Activo':
            return jsonify({
                'success': False,
                'message': 'Tu cuenta está inactiva. Contacta al administrador.'
            }), 403

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(minutes=30)

        password_reset_tokens[token] = {
            'user_id':    user['ID_Usuario'],
            'email':      email,
            'expires_at': expires_at,
            'used':       False
        }

        print(f"✅ Token generado para {email}: {token[:10]}...")

        reset_url = f"http://localhost:5000/reset-password?token={token}"

        email_sent = send_reset_email(
            to_email=email,
            nombre=user['Nombre'],
            reset_url=reset_url
        )

        if email_sent:
            print(f"✅ Correo de recuperación enviado a: {email}")
            return jsonify({
                'success': True,
                'message': 'Enlace enviado. Revisa tu bandeja de entrada.'
            })
        else:
            print(f"⚠️ Correo no enviado. URL de reset: {reset_url}")
            return jsonify({
                'success': True,
                'message': 'Enlace generado. Si no recibes el correo, revisa la consola del servidor.',
                # Quitar en producción:
                'dev_url': reset_url
            })

    except Exception as e:
        print(f"❌ Error en request_password_reset: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error interno del servidor.'}), 500


@auth_bp.route('/reset-password', methods=['GET'])
def reset_password_page():
    """Página para ingresar la nueva contraseña"""
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
.btn-submit:disabled{{background:#94a3b8;cursor:not-allowed;transform:none}}
.alert{{padding:15px;border-radius:10px;margin-bottom:20px;display:none}}
.alert-error{{background:#fee;color:#c00}}
.alert-success{{background:#efe;color:#060}}
.requirements{{background:#f8f9fa;border:1px solid #e2e8f0;border-radius:10px;padding:15px;margin-top:20px}}
.requirements h4{{color:#1e3a2e;margin-bottom:10px}}
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
document.getElementById('resetForm').addEventListener('submit',async function(e){{e.preventDefault();const newPwd=document.getElementById('new_password').value;const confirmPwd=document.getElementById('confirm_password').value;const btn=document.getElementById('submitBtn');if(!validatePassword(newPwd)){{showAlert('La contraseña no cumple los requisitos','error');return}}if(newPwd!==confirmPwd){{showAlert('Las contraseñas no coinciden','error');return}}btn.disabled=true;btn.innerHTML='<i class="fas fa-spinner fa-spin"></i> Procesando...';try{{const response=await fetch('/api/reset-password',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{token:document.getElementById('token').value,new_password:newPwd}})}});const data=await response.json();if(data.success){{showAlert('¡Contraseña actualizada! Redirigiendo...','success');setTimeout(()=>{{window.location.href='/vista/login-trabajador.html?message=Contraseña actualizada correctamente&type=success'}},2000)}}else{{showAlert(data.message,'error');btn.disabled=false;btn.innerHTML='Restablecer Contraseña'}}}}catch(error){{showAlert('Error de conexión. Intenta nuevamente.','error');btn.disabled=false;btn.innerHTML='Restablecer Contraseña'}}}});
</script></body></html>"""


@auth_bp.route('/api/reset-password', methods=['POST'])
def process_password_reset():
    """Procesa el cambio de contraseña con el token"""
    try:
        data = request.get_json()
        token = data.get('token')
        new_password = data.get('new_password')

        if not token or not new_password or len(new_password) < 8:
            return jsonify({'success': False, 'message': 'Datos inválidos'}), 400

        token_data = password_reset_tokens.get(token)

        if not token_data or datetime.now() > token_data['expires_at'] or token_data['used']:
            return jsonify({'success': False, 'message': 'Token inválido o expirado'}), 400

        hashed_password = hash_password(new_password)
        execute_query(
            "UPDATE Usuario SET Contrasena = %s WHERE ID_Usuario = %s",
            (hashed_password, token_data['user_id'])
        )
        token_data['used'] = True
        print(f"✅ Contraseña actualizada para usuario {token_data['user_id']}")

        return jsonify({'success': True, 'message': 'Contraseña actualizada correctamente'})

    except Exception as e:
        print(f"❌ Error en process_password_reset: {str(e)}")
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500


# ================================================================
# DATOS DE USUARIO Y SESIÓN
# ================================================================

@auth_bp.route('/get_user_data.py', methods=['GET'])
def get_user_data():
    """API para obtener datos del usuario logueado"""
    if 'user_id' not in session:
        return jsonify({'error': True, 'message': 'Usuario no autenticado'}), 401

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


@auth_bp.route('/get_user_session', methods=['GET'])
def get_user_session():
    """Obtener datos completos de sesión con configuraciones JSON e idioma"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'No hay sesión activa'}), 401

        user_id = session.get('user_id')
        print(f"📥 Obteniendo sesión para usuario ID: {user_id}")

        user_data = execute_query(
            """SELECT ID_Usuario, Nombre, Apellido, Correo, Telefono, URL_Foto,
                      Red_Social, Rol, Estado, Fecha_Registro, Configuraciones,
                      Idioma
               FROM Usuario WHERE ID_Usuario = %s""",
            (user_id,), fetch_one=True
        )

        if not user_data:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

        configuraciones = {}
        if user_data.get('Configuraciones'):
            try:
                configuraciones = json.loads(user_data['Configuraciones'])
            except json.JSONDecodeError:
                configuraciones = {}

        stats = execute_query("""
            SELECT
                COUNT(DISTINCT al.ID_Acuerdo) as trabajos_completados,
                AVG(CAST(c.Puntuacion AS DECIMAL)) as calificacion_promedio
            FROM Usuario u
            LEFT JOIN Acuerdo_Laboral al ON u.ID_Usuario = al.ID_Trabajador AND al.Estado = 'Finalizado'
            LEFT JOIN Calificacion c ON u.ID_Usuario = c.ID_Usuario_Receptor
            WHERE u.ID_Usuario = %s
        """, (user_id,), fetch_one=True)

        session['first_name'] = user_data['Nombre']
        session['last_name'] = user_data['Apellido']
        session['email'] = user_data['Correo']
        session['user_name'] = f"{user_data['Nombre']} {user_data['Apellido']}"
        session['telefono'] = user_data.get('Telefono', '')

        return jsonify({
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
                'language': user_data.get('Idioma', 'es') or 'es',
                'fecha_registro': user_data['Fecha_Registro'].isoformat() if user_data.get('Fecha_Registro') else None,
                'username': user_data['Correo'],
                # Campos profesionales desde JSON
                'area_trabajo': configuraciones.get('area_trabajo'),
                'especializacion': configuraciones.get('especializacion'),
                'anos_experiencia': configuraciones.get('anos_experiencia', 0),
                'nivel_educativo': configuraciones.get('nivel_educativo'),
                'ubicacion': configuraciones.get('ubicacion'),
                # Estadísticas
                'trabajos_completados': stats['trabajos_completados'] if stats else 0,
                'calificacion_promedio': float(stats['calificacion_promedio']) if stats and stats['calificacion_promedio'] else 0.0
            }
        })

    except Exception as e:
        print(f"❌ Error en get_user_session: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500


# ================================================================
# VERIFICACIÓN Y VALIDACIÓN DE SESIÓN
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
        return jsonify({'authenticated': False})
    except Exception as e:
        return jsonify({'authenticated': False, 'error': str(e)}), 500


@auth_bp.route('/validate_session', methods=['GET'])
def validate_session():
    """Valida que la sesión sea válida y el usuario exista en BD"""
    try:
        if 'user_id' not in session:
            return jsonify({'valid': False, 'message': 'No hay sesión activa'}), 401

        user = execute_query(
            "SELECT ID_Usuario, Nombre, Apellido, Rol, Estado FROM Usuario WHERE ID_Usuario = %s",
            (session['user_id'],), fetch_one=True
        )

        if not user:
            session.clear()
            return jsonify({'valid': False, 'message': 'Usuario no encontrado'}), 401

        if user['Estado'] != 'Activo':
            session.clear()
            return jsonify({'valid': False, 'message': 'Usuario inactivo'}), 401

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
        return jsonify({'valid': False, 'error': str(e)}), 500


# ================================================================
# DASHBOARDS Y REDIRECCIONES
# ================================================================

@auth_bp.route('/')
def index():
    return redirect('/vista/inicio-sesion.html')

@auth_bp.route('/registro-trabajador')
def registro_trabajador():
    return redirect('/vista/registro-trabajador.html')

@auth_bp.route('/registro-agricultor')
def registro_agricultor():
    return redirect('/vista/registro-agricultor.html')

@auth_bp.route('/login-trabajador')
def login_trabajador():
    return redirect('/vista/login-trabajador.html')

@auth_bp.route('/login-agricultor')
def login_agricultor():
    return redirect('/vista/login-trabajador.html')

@auth_bp.route('/dashboard-agricultor')
def dashboard_agricultor():
    if 'user_id' not in session:
        return redirect('/vista/login-trabajador.html')
    if session.get('user_role') != 'Agricultor':
        return redirect('/vista/index-trabajador.html')
    return redirect('/vista/index-agricultor.html')

@auth_bp.route('/dashboard-trabajador')
def dashboard_trabajador():
    if 'user_id' not in session:
        return redirect('/vista/login-trabajador.html')
    if session.get('user_role') != 'Trabajador':
        return redirect('/vista/index-agricultor.html')
    return redirect('/vista/index-trabajador.html')

@auth_bp.route('/dashboard-admin')
def dashboard_admin():
    if 'user_id' not in session:
        return redirect('/vista/login-trabajador.html')
    rol = session.get('user_role')
    if rol != 'Administrador':
        return redirect('/vista/index-agricultor.html' if rol == 'Agricultor' else '/vista/index-trabajador.html')
    return redirect('/vista/index-administrador.html')


# ================================================================
# LOGOUT
# ================================================================

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Cierra la sesión del usuario"""
    try:
        user_name = session.get('user_name', 'Desconocido')
        print(f"👋 Cerrando sesión para: {user_name}")
        session.clear()
        return jsonify({'success': True, 'message': 'Sesión cerrada correctamente'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@auth_bp.route('/logout.py', methods=['POST', 'GET'])
def logout_legacy():
    """Cierra la sesión (ruta legacy)"""
    print(f"👋 Cerrando sesión para: {session.get('user_name', 'Desconocido')}")
    session.clear()
    return jsonify({'success': True, 'message': 'Sesión cerrada correctamente'})


# ================================================================
# AUTENTICACIÓN CON GOOGLE
# ================================================================

@auth_bp.route('/auth/google/login')
def google_auth_form():
    """Formulario para ingresar email de Google"""
    try:
        rol = request.args.get('rol', None)
        if rol:
            session['oauth_rol'] = rol
            action_text = f"Registro como {rol}"
            process_url = "/auth/google/process"
            info_text = "Se creará tu cuenta automáticamente"
        else:
            action_text = "Iniciar Sesión"
            process_url = "/auth/google/login-process"
            info_text = "Si no tienes cuenta, te ayudaremos a crearla"

        hidden_rol = f"<input type='hidden' name='rol' value='{rol}'>" if rol else ""

        return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Google - CAMP</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
<style>
body{{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#4285f4,#34a853);min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0;padding:20px}}
.container{{background:white;padding:40px;border-radius:20px;box-shadow:0 15px 35px rgba(0,0,0,.1);max-width:450px;width:100%;text-align:center}}
.logo{{font-size:48px;margin-bottom:20px;background:linear-gradient(45deg,#4285f4,#34a853,#fbbc05,#ea4335);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
h2{{color:#202124;font-size:24px;margin-bottom:10px}}p{{color:#5f6368;margin-bottom:30px}}
.form-group{{margin-bottom:20px;text-align:left}}
.form-group label{{display:block;color:#3c4043;font-size:14px;font-weight:500;margin-bottom:8px}}
.form-group input{{width:100%;padding:16px;border:1px solid #dadce0;border-radius:8px;font-size:16px;box-sizing:border-box}}
.form-group input:focus{{outline:none;border-color:#1a73e8;box-shadow:0 0 0 2px rgba(26,115,232,.2)}}
.btn-primary{{width:100%;background:#1a73e8;color:white;border:none;padding:16px;border-radius:8px;font-size:16px;font-weight:500;cursor:pointer;margin-bottom:16px}}
.btn-primary:hover{{background:#1557b0}}
.btn-secondary{{width:100%;background:transparent;color:#1a73e8;border:1px solid #dadce0;padding:16px;border-radius:8px;text-decoration:none;display:inline-block}}
.info{{background:#e3f2fd;border:1px solid #1976d2;border-radius:8px;padding:12px;margin:20px 0;font-size:13px;color:#0d47a1}}
</style></head>
<body><div class="container">
<div class="logo"><i class="fab fa-google"></i></div>
<h2>Continuar con Google</h2><p>{action_text}</p>
<form action="{process_url}" method="POST">
{hidden_rol}
<div class="form-group"><label>Tu correo de Gmail</label>
<input type="email" name="google_email" placeholder="ejemplo@gmail.com" required></div>
<div class="info"><i class="fas fa-info-circle"></i> {info_text}</div>
<button type="submit" class="btn-primary"><i class="fas fa-arrow-right"></i> Continuar</button>
</form>
<a href="javascript:history.back()" class="btn-secondary"><i class="fas fa-arrow-left"></i> Volver</a>
</div></body></html>"""
    except Exception as e:
        return redirect('/vista/login-trabajador.html?message=Error cargando Google&type=error')


@auth_bp.route('/auth/google/process', methods=['POST'])
def google_register_process():
    """Procesar registro con Google (con rol específico)"""
    try:
        google_email = request.form.get('google_email', '').strip().lower()
        rol = request.form.get('rol', 'Trabajador')

        if not google_email or not (google_email.endswith('@gmail.com') or google_email.endswith('@googlemail.com')):
            redirect_url = '/vista/registro-agricultor.html' if rol == 'Agricultor' else '/vista/registro-trabajador.html'
            return redirect(f'{redirect_url}?message=Por favor ingresa un correo válido de Gmail&type=error')

        existing_user = execute_query("SELECT * FROM Usuario WHERE Correo = %s", (google_email,), fetch_one=True)

        if existing_user:
            user = existing_user
        else:
            user_id = create_social_user_real(google_email, 'google', rol)
            if not user_id:
                return redirect('/vista/registro-trabajador.html?message=Error creando usuario con Google&type=error')
            user = execute_query("SELECT * FROM Usuario WHERE ID_Usuario = %s", (user_id,), fetch_one=True)

        session['user_id'] = user['ID_Usuario']
        session['username'] = user['Correo']
        session['first_name'] = user['Nombre']
        session['last_name'] = user['Apellido']
        session['email'] = user['Correo']
        session['user_role'] = user['Rol']
        session['role'] = user['Rol']
        session['user_name'] = f"{user['Nombre']} {user['Apellido']}"
        session['telefono'] = user.get('Telefono', '')
        session.pop('oauth_rol', None)

        return redirect('/vista/index-agricultor.html' if user['Rol'] == 'Agricultor' else '/vista/index-trabajador.html')
    except Exception as e:
        print(f"Error procesando registro Google: {str(e)}")
        return redirect('/vista/registro-trabajador.html?message=Error con Google&type=error')


@auth_bp.route('/auth/google/login-process', methods=['POST'])
def google_login_process():
    """Procesar login con Google (sin rol específico)"""
    try:
        google_email = request.form.get('google_email', '').strip().lower()

        if not google_email or not (google_email.endswith('@gmail.com') or google_email.endswith('@googlemail.com')):
            return redirect('/vista/login-trabajador.html?message=Por favor ingresa un correo válido de Gmail&type=error')

        existing_user = execute_query("SELECT * FROM Usuario WHERE Correo = %s", (google_email,), fetch_one=True)

        if not existing_user:
            return redirect(f'/vista/seleccion-rol.html?email={quote(google_email)}&provider=google&message=Cuenta no encontrada. Selecciona tu rol para registrarte&type=info')

        user = existing_user
        session['user_id'] = user['ID_Usuario']
        session['username'] = user['Correo']
        session['first_name'] = user['Nombre']
        session['last_name'] = user['Apellido']
        session['email'] = user['Correo']
        session['user_role'] = user['Rol']
        session['role'] = user['Rol']
        session['user_name'] = f"{user['Nombre']} {user['Apellido']}"
        session['telefono'] = user.get('Telefono', '')

        return redirect('/vista/index-agricultor.html' if user['Rol'] == 'Agricultor' else '/vista/index-trabajador.html')
    except Exception as e:
        print(f"Error en login Google: {str(e)}")
        return redirect('/vista/login-trabajador.html?message=Error procesando Google&type=error')


@auth_bp.route('/auth/google/demo')
def google_demo():
    """Página de selección de usuario demo de Google"""
    try:
        rol = request.args.get('rol', 'Trabajador')
        session['oauth_rol'] = rol

        users_html = ""
        for demo_id, user_data in GOOGLE_USERS_DEMO.items():
            initials = f"{user_data['given_name'][0]}{user_data['family_name'][0]}"
            users_html += f"""
            <div class="demo-user" onclick="window.location.href='/auth/google/demo/callback?demo_user={demo_id}'">
                <div class="avatar">{initials}</div>
                <div class="info">
                    <div class="name">{user_data['given_name']} {user_data['family_name']}</div>
                    <div class="email">{user_data['email']}</div>
                </div>
            </div>"""

        return f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>Demo Google - CAMP</title>
<style>body{{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#4285f4,#34a853);min-height:100vh;display:flex;align-items:center;justify-content:center}}
.container{{background:white;padding:40px;border-radius:16px;max-width:480px;width:90%;text-align:center}}
h2{{color:#202124}}.badge{{background:#4CAF50;color:white;padding:4px 12px;border-radius:20px;font-size:13px}}
.demo-user{{display:flex;align-items:center;padding:14px;margin:8px 0;background:#f8f9fa;border-radius:10px;border:2px solid transparent;cursor:pointer}}
.demo-user:hover{{border-color:#4285f4;background:#e3f2fd}}
.avatar{{width:48px;height:48px;background:#4285f4;border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:18px;margin-right:14px;flex-shrink:0}}
.name{{font-weight:600;color:#333}}.email{{color:#666;font-size:13px}}
.cancel{{display:inline-block;margin-top:20px;padding:12px 24px;background:#6c757d;color:white;border-radius:8px;text-decoration:none}}</style></head>
<body><div class="container">
<h2>🔵 Google Demo</h2>
<p>Registro como: <span class="badge">{rol}</span></p>
<p>Selecciona un usuario demo:</p>
{users_html}
<a href="javascript:history.back()" class="cancel">Cancelar</a>
</div></body></html>"""
    except Exception as e:
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
        existing_user = execute_query("SELECT * FROM Usuario WHERE Correo = %s", (user_data['email'],), fetch_one=True)

        if existing_user:
            user_id = existing_user['ID_Usuario']
        else:
            user_id = create_demo_user(user_data, 'google', rol)
            if not user_id:
                return redirect('/vista/registro-trabajador.html?message=Error creando usuario demo&type=error')

        user = execute_query("SELECT * FROM Usuario WHERE ID_Usuario = %s", (user_id,), fetch_one=True)

        session['user_id'] = user['ID_Usuario']
        session['username'] = user['Correo']
        session['first_name'] = user['Nombre']
        session['last_name'] = user['Apellido']
        session['email'] = user['Correo']
        session['user_role'] = user['Rol']
        session['user_name'] = f"{user['Nombre']} {user['Apellido']}"
        session['telefono'] = user.get('Telefono', '')
        session.pop('oauth_rol', None)

        return redirect('/vista/index-agricultor.html' if user['Rol'] == 'Agricultor' else '/vista/index-trabajador.html')
    except Exception as e:
        return redirect('/vista/registro-trabajador.html?message=Error procesando usuario demo&type=error')


@auth_bp.route('/auth/google/delete-account', methods=['POST'])
@require_login
def delete_account_with_google():
    """Eliminar cuenta verificando que fue creada con Google"""
    try:
        user_id = session['user_id']
        user = execute_query("SELECT * FROM Usuario WHERE ID_Usuario = %s", (user_id,), fetch_one=True)

        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404

        red_social = user.get('Red_Social', '')
        if not red_social or not red_social.startswith('google:'):
            return jsonify({'success': False, 'message': 'Esta cuenta no fue creada con Google'}), 400

        _delete_user_data(user_id)
        execute_query("DELETE FROM Usuario WHERE ID_Usuario = %s", (user_id,))
        session.clear()

        return jsonify({'success': True, 'message': 'Cuenta eliminada correctamente con Google'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500


# ================================================================
# AUTENTICACIÓN CON FACEBOOK
# ================================================================

@auth_bp.route('/auth/facebook/login')
def facebook_auth_form():
    """Formulario para ingresar email de Facebook"""
    try:
        rol = request.args.get('rol', None)
        if rol:
            session['oauth_rol'] = rol
            action_text = f"Registro como {rol}"
            process_url = "/auth/facebook/process"
            info_text = "Se creará tu cuenta automáticamente"
        else:
            action_text = "Iniciar Sesión"
            process_url = "/auth/facebook/login-process"
            info_text = "Si no tienes cuenta, te ayudaremos a crearla"

        hidden_rol = f"<input type='hidden' name='rol' value='{rol}'>" if rol else ""

        return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Facebook - CAMP</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
<style>
body{{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#4267B2,#365899);min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0;padding:20px}}
.container{{background:white;padding:40px;border-radius:20px;box-shadow:0 15px 35px rgba(0,0,0,.1);max-width:450px;width:100%;text-align:center}}
.logo{{font-size:48px;color:#4267B2;margin-bottom:20px}}
h2{{color:#1c1e21;font-size:24px;margin-bottom:10px}}p{{color:#606770;margin-bottom:30px}}
.form-group{{margin-bottom:20px;text-align:left}}
.form-group label{{display:block;color:#1c1e21;font-size:14px;font-weight:500;margin-bottom:8px}}
.form-group input{{width:100%;padding:16px;border:1px solid #dddfe2;border-radius:8px;font-size:16px;box-sizing:border-box}}
.form-group input:focus{{outline:none;border-color:#4267B2;box-shadow:0 0 0 2px rgba(66,103,178,.2)}}
.btn-primary{{width:100%;background:#4267B2;color:white;border:none;padding:16px;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer;margin-bottom:16px}}
.btn-primary:hover{{background:#365899}}
.btn-secondary{{width:100%;background:transparent;color:#4267B2;border:1px solid #dddfe2;padding:16px;border-radius:8px;text-decoration:none;display:inline-block}}
.info{{background:#e7f3ff;border:1px solid #4267B2;border-radius:8px;padding:12px;margin:20px 0;font-size:13px;color:#4267B2}}
</style></head>
<body><div class="container">
<div class="logo"><i class="fab fa-facebook"></i></div>
<h2>Continuar con Facebook</h2><p>{action_text}</p>
<form action="{process_url}" method="POST">
{hidden_rol}
<div class="form-group"><label>Tu correo asociado a Facebook</label>
<input type="email" name="facebook_email" placeholder="ejemplo@hotmail.com" required>
<small style="color:#606770">Hotmail, Outlook, Live o MSN</small></div>
<div class="info"><i class="fas fa-info-circle"></i> {info_text}</div>
<button type="submit" class="btn-primary"><i class="fas fa-arrow-right"></i> Continuar</button>
</form>
<a href="javascript:history.back()" class="btn-secondary"><i class="fas fa-arrow-left"></i> Volver</a>
</div></body></html>"""
    except Exception as e:
        return redirect('/vista/login-trabajador.html?message=Error cargando Facebook&type=error')


@auth_bp.route('/auth/facebook/process', methods=['POST'])
def facebook_register_process():
    """Procesar registro con Facebook (con rol específico)"""
    try:
        facebook_email = request.form.get('facebook_email', '').strip().lower()
        rol = request.form.get('rol', 'Trabajador')
        valid_domains = ['@hotmail.com', '@outlook.com', '@live.com', '@msn.com']

        if not facebook_email or not any(facebook_email.endswith(d) for d in valid_domains):
            redirect_url = '/vista/registro-agricultor.html' if rol == 'Agricultor' else '/vista/registro-trabajador.html'
            return redirect(f'{redirect_url}?message=Por favor ingresa un correo válido asociado a Facebook&type=error')

        existing_user = execute_query("SELECT * FROM Usuario WHERE Correo = %s", (facebook_email,), fetch_one=True)

        if existing_user:
            user = existing_user
        else:
            user_id = create_social_user_real(facebook_email, 'facebook', rol)
            if not user_id:
                return redirect('/vista/registro-trabajador.html?message=Error creando usuario con Facebook&type=error')
            user = execute_query("SELECT * FROM Usuario WHERE ID_Usuario = %s", (user_id,), fetch_one=True)

        session['user_id'] = user['ID_Usuario']
        session['username'] = user['Correo']
        session['first_name'] = user['Nombre']
        session['last_name'] = user['Apellido']
        session['email'] = user['Correo']
        session['user_role'] = user['Rol']
        session['role'] = user['Rol']
        session['user_name'] = f"{user['Nombre']} {user['Apellido']}"
        session['telefono'] = user.get('Telefono', '')
        session.pop('oauth_rol', None)

        return redirect('/vista/index-agricultor.html' if user['Rol'] == 'Agricultor' else '/vista/index-trabajador.html')
    except Exception as e:
        return redirect('/vista/registro-trabajador.html?message=Error con Facebook&type=error')


@auth_bp.route('/auth/facebook/login-process', methods=['POST'])
def facebook_login_process():
    """Procesar login con Facebook (sin rol específico)"""
    try:
        facebook_email = request.form.get('facebook_email', '').strip().lower()
        valid_domains = ['@hotmail.com', '@outlook.com', '@live.com', '@msn.com']

        if not facebook_email or not any(facebook_email.endswith(d) for d in valid_domains):
            return redirect('/vista/login-trabajador.html?message=Por favor ingresa un correo válido asociado a Facebook&type=error')

        existing_user = execute_query("SELECT * FROM Usuario WHERE Correo = %s", (facebook_email,), fetch_one=True)

        if not existing_user:
            return redirect(f'/vista/seleccion-rol.html?email={quote(facebook_email)}&provider=facebook&message=Cuenta no encontrada. Selecciona tu rol para registrarte&type=info')

        user = existing_user
        session['user_id'] = user['ID_Usuario']
        session['username'] = user['Correo']
        session['first_name'] = user['Nombre']
        session['last_name'] = user['Apellido']
        session['email'] = user['Correo']
        session['user_role'] = user['Rol']
        session['role'] = user['Rol']
        session['user_name'] = f"{user['Nombre']} {user['Apellido']}"
        session['telefono'] = user.get('Telefono', '')

        return redirect('/vista/index-agricultor.html' if user['Rol'] == 'Agricultor' else '/vista/index-trabajador.html')
    except Exception as e:
        return redirect('/vista/login-trabajador.html?message=Error procesando Facebook&type=error')


@auth_bp.route('/auth/facebook/demo')
def facebook_demo():
    """Página de selección de usuario demo de Facebook"""
    try:
        rol = request.args.get('rol', 'Trabajador')
        session['oauth_rol'] = rol

        users_html = ""
        for demo_id, user_data in FACEBOOK_USERS_DEMO.items():
            initials = f"{user_data['first_name'][0]}{user_data['last_name'][0]}"
            users_html += f"""
            <div class="demo-user" onclick="window.location.href='/auth/facebook/demo/callback?demo_user={demo_id}'">
                <div class="avatar">{initials}</div>
                <div class="info">
                    <div class="name">{user_data['first_name']} {user_data['last_name']}</div>
                    <div class="email">{user_data['email']}</div>
                </div>
            </div>"""

        return f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>Demo Facebook - CAMP</title>
<style>body{{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#4267B2,#365899);min-height:100vh;display:flex;align-items:center;justify-content:center}}
.container{{background:white;padding:40px;border-radius:16px;max-width:480px;width:90%;text-align:center}}
h2{{color:#1c1e21}}.badge{{background:#4CAF50;color:white;padding:4px 12px;border-radius:20px;font-size:13px}}
.demo-user{{display:flex;align-items:center;padding:14px;margin:8px 0;background:#f8f9fa;border-radius:10px;border:2px solid transparent;cursor:pointer}}
.demo-user:hover{{border-color:#4267B2;background:#e7f3ff}}
.avatar{{width:48px;height:48px;background:#4267B2;border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:18px;margin-right:14px;flex-shrink:0}}
.name{{font-weight:600;color:#333}}.email{{color:#666;font-size:13px}}
.cancel{{display:inline-block;margin-top:20px;padding:12px 24px;background:#6c757d;color:white;border-radius:8px;text-decoration:none}}</style></head>
<body><div class="container">
<h2>🔵 Facebook Demo</h2>
<p>Registro como: <span class="badge">{rol}</span></p>
<p>Selecciona un usuario demo:</p>
{users_html}
<a href="javascript:history.back()" class="cancel">Cancelar</a>
</div></body></html>"""
    except Exception as e:
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
        existing_user = execute_query("SELECT * FROM Usuario WHERE Correo = %s", (user_data['email'],), fetch_one=True)

        if existing_user:
            user_id = existing_user['ID_Usuario']
        else:
            user_id = create_demo_user(user_data, 'facebook', rol)
            if not user_id:
                return redirect('/vista/registro-trabajador.html?message=Error creando usuario demo&type=error')

        user = execute_query("SELECT * FROM Usuario WHERE ID_Usuario = %s", (user_id,), fetch_one=True)

        session['user_id'] = user['ID_Usuario']
        session['username'] = user['Correo']
        session['first_name'] = user['Nombre']
        session['last_name'] = user['Apellido']
        session['email'] = user['Correo']
        session['user_role'] = user['Rol']
        session['user_name'] = f"{user['Nombre']} {user['Apellido']}"
        session['telefono'] = user.get('Telefono', '')
        session.pop('oauth_rol', None)

        return redirect('/vista/index-agricultor.html' if user['Rol'] == 'Agricultor' else '/vista/index-trabajador.html')
    except Exception as e:
        return redirect('/vista/registro-trabajador.html?message=Error procesando usuario demo&type=error')


@auth_bp.route('/auth/facebook/delete-account', methods=['POST'])
@require_login
def delete_account_with_facebook():
    """Eliminar cuenta verificando que fue creada con Facebook"""
    try:
        user_id = session['user_id']
        user = execute_query("SELECT * FROM Usuario WHERE ID_Usuario = %s", (user_id,), fetch_one=True)

        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404

        red_social = user.get('Red_Social', '')
        if not red_social or not red_social.startswith('facebook:'):
            return jsonify({'success': False, 'message': 'Esta cuenta no fue creada con Facebook'}), 400

        _delete_user_data(user_id)
        execute_query("DELETE FROM Usuario WHERE ID_Usuario = %s", (user_id,))
        session.clear()

        return jsonify({'success': True, 'message': 'Cuenta eliminada correctamente con Facebook'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500


# ================================================================
# FUNCIÓN AUXILIAR PARA ELIMINAR DATOS DE USUARIO
# ================================================================

def _delete_user_data(user_id):
    """Elimina todos los registros relacionados al usuario en orden de dependencias"""
    tables = [
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
    for table_name, columns in tables:
        try:
            if len(columns) == 1:
                execute_query(f"DELETE FROM {table_name} WHERE {columns[0]} = %s", (user_id,))
            else:
                conditions = ' OR '.join([f"{col} = %s" for col in columns])
                execute_query(f"DELETE FROM {table_name} WHERE {conditions}", [user_id] * len(columns))
        except Exception as e:
            print(f"Error eliminando de {table_name}: {str(e)}")


print("✅ auth.py cargado correctamente")
print("   - /api/request-password-reset  (¿Olvidaste tu contraseña?)")
print("   - /reset-password              (Página de nueva contraseña)")
print("   - /api/reset-password          (Procesar cambio de contraseña)")
print("   - /login.py                    (Login)")
print("   - /registro.py                 (Registro)")
print("   - /get_user_session            (Sesión + idioma)")
print("   - Google OAuth (login/registro/demo)")
print("   - Facebook OAuth (login/registro/demo)")