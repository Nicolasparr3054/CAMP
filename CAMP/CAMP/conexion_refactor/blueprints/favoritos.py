# Blueprint: favoritos
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

favoritos_bp = Blueprint('favoritos', __name__)
from blueprints.helpers import require_login, require_role, hash_password, verify_password, no_cache


# ================================================================
# RUTAS PARA ARCHIVOS HTML DE LA CARPETA VISTA
# ================================================================

@favoritos_bp.route('/vista/favoritos.html')
def favoritos_html():
    """Página de favoritos"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vista_path = os.path.join(base_dir, '..', '..', 'vista')
        vista_path = os.path.abspath(vista_path)
        return send_from_directory(vista_path, 'favoritos.html')
    except Exception as e:
        print(f"Error sirviendo favoritos.html: {e}")
        return "Archivo no encontrado", 404


# ================================================================
# RUTAS PARA ARCHIVOS CSS DE ASSENT/CSS
# ================================================================

@favoritos_bp.route('/assent/css/favoritos.css')
def favoritos_css():
    """CSS para página de favoritos"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        css_path = os.path.join(base_dir, '..', '..', 'assent', 'css')
        css_path = os.path.abspath(css_path)
        response = send_from_directory(css_path, 'favoritos.css')
        response.headers['Content-Type'] = 'text/css'
        return response
    except Exception as e:
        print(f"Error sirviendo favoritos.css: {e}")
        return "CSS no encontrado", 404


# ================================================================
# RUTAS PARA ARCHIVOS JAVASCRIPT DE JS/
# ================================================================

@favoritos_bp.route('/js/favoritos.js')
def favoritos_js():
    """JavaScript para página de favoritos"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        js_path = os.path.join(base_dir, '..', '..', 'js')
        js_path = os.path.abspath(js_path)
        response = send_from_directory(js_path, 'favoritos.js')
        response.headers['Content-Type'] = 'application/javascript'
        return response
    except Exception as e:
        print(f"Error sirviendo favoritos.js: {e}")
        return "JS no encontrado", 404


# ================================================================
# APIS PARA FAVORITOS, HISTORIAL Y POSTULACIONES
# ================================================================

@favoritos_bp.route('/api/favoritos', methods=['GET', 'POST'])
@require_login
def handle_favoritos():
    """API para manejar trabajos favoritos usando tabla Postulacion"""
    user_id = session['user_id']
    
    if request.method == 'GET':
        try:
            favoritos = execute_query("""
                SELECT p.ID_Oferta, ot.Titulo, p.Fecha_Postulacion,
                       ot.Descripcion, ot.Pago_Ofrecido, ot.Estado,
                       CONCAT(u.Nombre, ' ', u.Apellido) as Agricultor,
                       pr.Nombre_Finca as Ubicacion
                FROM Postulacion p
                JOIN Oferta_Trabajo ot ON p.ID_Oferta = ot.ID_Oferta
                JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
                LEFT JOIN Predio pr ON u.ID_Usuario = pr.ID_Usuario
                WHERE p.ID_Trabajador = %s AND p.Estado = 'Favorito'
                ORDER BY p.Fecha_Postulacion DESC
            """, (user_id,))
            
            favoritos_list = []
            if favoritos:
                for fav in favoritos:
                    favoritos_list.append({
                        'job_id': fav['ID_Oferta'],
                        'titulo': fav['Titulo'],
                        'descripcion': fav['Descripcion'],
                        'pago': float(fav['Pago_Ofrecido']),
                        'agricultor': fav['Agricultor'],
                        'ubicacion': fav['Ubicacion'] if fav['Ubicacion'] else 'No especificada',
                        'estado': fav['Estado'],
                        'fecha_agregado': fav['Fecha_Postulacion'].isoformat() if fav['Fecha_Postulacion'] else None
                    })
            
            return jsonify({
                'success': True,
                'favoritos': favoritos_list
            })
            
        except Exception as e:
            print(f"Error obteniendo favoritos: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            job_id = data.get('job_id')
            action = data.get('action')
            
            if not job_id or not action:
                return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
            
            if action == 'add':
                # Verificar si ya existe postulación para esta oferta
                existing = execute_query("""
                    SELECT ID_Postulacion, Estado FROM Postulacion 
                    WHERE ID_Trabajador = %s AND ID_Oferta = %s
                """, (user_id, job_id), fetch_one=True)
                
                if existing:
                    # Actualizar estado a Favorito
                    execute_query("""
                        UPDATE Postulacion 
                        SET Estado = 'Favorito', Fecha_Postulacion = CURRENT_TIMESTAMP
                        WHERE ID_Postulacion = %s
                    """, (existing['ID_Postulacion'],))
                else:
                    # Crear nueva entrada como favorito
                    execute_query("""
                        INSERT INTO Postulacion (ID_Oferta, ID_Trabajador, Estado, Fecha_Postulacion)
                        VALUES (%s, %s, 'Favorito', CURRENT_TIMESTAMP)
                    """, (job_id, user_id))
                
                message = "Trabajo agregado a favoritos"
                    
            elif action == 'remove':
                # Eliminar favorito
                execute_query("""
                    DELETE FROM Postulacion 
                    WHERE ID_Trabajador = %s AND ID_Oferta = %s AND Estado = 'Favorito'
                """, (user_id, job_id))
                
                message = "Trabajo removido de favoritos"
            
            return jsonify({
                'success': True,
                'message': message
            })
            
        except Exception as e:
            print(f"Error manejando favoritos: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# ENDPOINT PARA OBTENER FAVORITOS
# ================================================================
@favoritos_bp.route('/api/get_favorites', methods=['GET'])
@require_login
def get_favorites():
    """Obtener trabajos favoritos del trabajador"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role') or session.get('role')
        
        if user_role != 'Trabajador':
            return jsonify({'success': False, 'message': 'Solo trabajadores tienen favoritos'}), 403
        
        favoritos = execute_query("""
            SELECT 
                p.ID_Postulacion,
                p.Fecha_Postulacion,
                ot.ID_Oferta as id_oferta,
                ot.Titulo as titulo,
                ot.Descripcion as descripcion,
                ot.Pago_Ofrecido as pago_ofrecido,
                ot.Fecha_Publicacion as fecha_publicacion,
                ot.Estado as estado,
                CONCAT(u.Nombre, ' ', u.Apellido) as nombre_agricultor
            FROM Postulacion p
            JOIN Oferta_Trabajo ot ON p.ID_Oferta = ot.ID_Oferta
            JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
            WHERE p.ID_Trabajador = %s AND p.Estado = 'Favorito'
            ORDER BY p.Fecha_Postulacion DESC
        """, (user_id,))
        
        return jsonify({
            'success': True,
            'favoritos': favoritos or [],
            'total': len(favoritos) if favoritos else 0
        })
        
    except Exception as e:
        print(f"Error obteniendo favoritos: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ================================================================
# ENDPOINT PARA VERIFICAR SI UNA OFERTA ES FAVORITA
# ================================================================
@favoritos_bp.route('/api/check_favorite/<int:job_id>', methods=['GET'])
@require_login
def check_favorite(job_id):
    """Verificar si una oferta está en favoritos"""
    try:
        user_id = session['user_id']
        
        existe = execute_query("""
            SELECT ID_Postulacion 
            FROM Postulacion 
            WHERE ID_Oferta = %s AND ID_Trabajador = %s AND Estado = 'Favorito'
        """, (job_id, user_id), fetch_one=True)
        
        return jsonify({
            'success': True,
            'is_favorite': existe is not None
        })
        
    except Exception as e:
        print(f"Error verificando favorito: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

