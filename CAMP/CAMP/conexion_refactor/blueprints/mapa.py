# Blueprint: mapa
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

mapa_bp = Blueprint('mapa', __name__)
from blueprints.helpers import require_login, require_role, hash_password, verify_password, no_cache


# ================================================================
# ENDPOINT 3: Guardar ubicación del usuario
# ================================================================
@mapa_bp.route('/api/save_user_location', methods=['POST'])
@require_login
def save_user_location():
    """Guardar la ubicación actual del usuario"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not latitude or not longitude:
            return jsonify({'success': False, 'error': 'Ubicación requerida'}), 400
        
        # Guardar en tabla Predio si es agricultor
        user_role = session.get('user_role')
        
        if user_role == 'Agricultor':
            # Verificar si tiene predio
            predio = execute_query("""
                SELECT ID_Predio FROM Predio WHERE ID_Usuario = %s LIMIT 1
            """, (user_id,), fetch_one=True)
            
            if predio:
                # Actualizar predio existente
                execute_query("""
                    UPDATE Predio 
                    SET Ubicacion_Latitud = %s, Ubicacion_Longitud = %s
                    WHERE ID_Predio = %s
                """, (latitude, longitude, predio['ID_Predio']))
            else:
                # Crear nuevo predio
                execute_query("""
                    INSERT INTO Predio (ID_Usuario, Nombre_Finca, Ubicacion_Latitud, Ubicacion_Longitud, Descripcion)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, 'Mi Finca', latitude, longitude, 'Ubicación registrada automáticamente'))
        
        # Para trabajadores, podrías crear una tabla separada para ubicaciones
        # O usar la tabla Configuraciones en formato JSON
        
        return jsonify({
            'success': True,
            'message': 'Ubicación guardada correctamente'
        })
        
    except Exception as e:
        print(f"Error guardando ubicación: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# ENDPOINT 4: Obtener ubicación del predio del agricultor
# ================================================================
@mapa_bp.route('/api/get_user_location', methods=['GET'])
@require_login
def get_user_location():
    """Obtener la ubicación guardada del usuario"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role')
        
        if user_role == 'Agricultor':
            # Obtener del predio
            predio = execute_query("""
                SELECT Ubicacion_Latitud, Ubicacion_Longitud, Nombre_Finca
                FROM Predio 
                WHERE ID_Usuario = %s 
                LIMIT 1
            """, (user_id,), fetch_one=True)
            
            if predio and predio['Ubicacion_Latitud'] and predio['Ubicacion_Longitud']:
                return jsonify({
                    'success': True,
                    'location': {
                        'lat': float(predio['Ubicacion_Latitud']),
                        'lng': float(predio['Ubicacion_Longitud']),
                        'nombre': predio['Nombre_Finca']
                    }
                })
        
        # Si no hay ubicación guardada, devolver ubicación por defecto (Bogotá)
        return jsonify({
            'success': True,
            'location': {
                'lat': 4.7110,
                'lng': -74.0721,
                'nombre': 'Ubicación no configurada'
            },
            'is_default': True
        })
        
    except Exception as e:
        print(f"Error obteniendo ubicación: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


print("✅ Endpoints de geolocalización cargados correctamente")
print("📋 APIs disponibles:")
print("   • POST /api/get_nearby_jobs        - Ofertas cercanas (trabajador)")
print("   • POST /api/get_nearby_workers     - Trabajadores cercanos (agricultor)")
print("   • POST /api/save_user_location     - Guardar ubicación")
print("   • GET  /api/get_user_location      - Obtener ubicación guardada")


# Configuración
GMAIL_USER = 'camp2025@gmail.com'
GMAIL_APP_PASSWORD = 'wfme fcns ubgw viju'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
password_reset_tokens = {}

def send_email(to_email, subject, html_content):
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f'CAMP <{GMAIL_USER}>'
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ Email enviado a {to_email}")
        return True
    except Exception as e:
        print(f"❌ Error enviando email: {str(e)}")
        return False

def get_password_reset_email_template(user_name, reset_link):
    return f"""
    <html><body style="font-family: Arial, sans-serif; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
        <div style="background: linear-gradient(135deg, #4a7c59 0%, #2d5a27 100%); padding: 40px; text-align: center;">
            <h1 style="margin: 0; color: white; font-size: 28px;">🌱 CAMP</h1>
            <p style="margin: 10px 0 0; color: #90EE90; font-size: 16px;">Recuperación de Contraseña</p>
        </div>
        <div style="padding: 40px;">
            <h2 style="color: #1e3a2e; font-size: 24px;">Hola {user_name},</h2>
            <p style="color: #64748b; font-size: 16px; line-height: 1.6;">
                Recibimos una solicitud para restablecer tu contraseña en CAMP.
            </p>
            <div style="text-align: center; padding: 20px 0;">
                <a href="{reset_link}" style="display: inline-block; background: linear-gradient(135deg, #4a7c59 0%, #2d5a27 100%); color: white; text-decoration: none; padding: 16px 40px; border-radius: 10px; font-size: 16px; font-weight: 600;">
                    Restablecer Contraseña
                </a>
            </div>
            <p style="color: #64748b; font-size: 14px;">O copia este enlace: {reset_link}</p>
            <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 10px; padding: 15px; margin: 20px 0;">
                <p style="margin: 0; color: #856404; font-size: 14px;">⚠️ Este enlace expirará en 30 minutos</p>
            </div>
        </div>
    </div>
    </body></html>
    """

