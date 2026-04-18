# Blueprint: ofertas
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

ofertas_bp = Blueprint('ofertas', __name__)
from blueprints.helpers import require_login, require_role, hash_password, verify_password, no_cache


@ofertas_bp.route('/api/crear_oferta', methods=['POST'])
def crear_oferta():
    """Crear una nueva oferta de trabajo"""
    try:
        # Verificar sesión
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'message': 'Sesión no válida'
            }), 401
        
        # Verificar que el usuario sea agricultor
        user_role = session.get('user_role') or session.get('role')
        if user_role != 'Agricultor':
            return jsonify({
                'success': False,
                'message': 'Solo los agricultores pueden crear ofertas'
            }), 403
        
        data = request.get_json()
        print(f"Datos recibidos: {data}")  # Para debug
        
        # Validación de datos básicos
        if not data.get('titulo') or len(data['titulo']) < 10:
            return jsonify({
                'success': False,
                'message': 'El título debe tener al menos 10 caracteres'
            }), 400
        
        if not data.get('descripcion') or len(data['descripcion']) < 20:
            return jsonify({
                'success': False,
                'message': 'La descripción debe tener al menos 20 caracteres'
            }), 400
        
        if not data.get('pago') or int(data['pago']) < 10000:
            return jsonify({
                'success': False,
                'message': 'El pago mínimo debe ser $10,000 COP'
            }), 400
        
        # Descripción con ubicación incluida
        descripcion_completa = data['descripcion']
        if data.get('ubicacion'):
            descripcion_completa += f"\n\nUbicación: {data['ubicacion']}"
        
        # Insertar en la base de datos usando execute_query
        user_id = execute_query(
            """INSERT INTO Oferta_Trabajo (ID_Agricultor, Titulo, Descripcion, Pago_Ofrecido, Estado) 
               VALUES (%s, %s, %s, %s, 'Abierta')""",
            (session['user_id'], data['titulo'], descripcion_completa, int(data['pago']))
        )
        
        print(f"Oferta creada con ID: {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Oferta creada exitosamente',
            'oferta_id': user_id
        }), 201
        
    except Exception as e:
        print(f"❌ Error en crear_oferta: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


# ================================================================
# DUPLICAR OFERTA - VERSIÓN CORREGIDA
# ================================================================

@ofertas_bp.route('/api/duplicar_oferta/<int:oferta_id>', methods=['POST'])
def duplicar_oferta(oferta_id):
    """Duplicar una oferta existente"""
    try:
        # Verificar sesión manualmente
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'message': 'Sesión no válida'
            }), 401
        
        user_id = session['user_id']
        user_role = session.get('user_role', session.get('role'))
        
        print(f"🔍 Duplicando oferta {oferta_id} - Usuario: {user_id}, Rol: {user_role}")
        
        if user_role != 'Agricultor':
            return jsonify({
                'success': False,
                'message': 'Solo los agricultores pueden duplicar ofertas'
            }), 403
        
        # Obtener la oferta original
        oferta = execute_query("""
            SELECT Titulo, Descripcion, Pago_Ofrecido, ID_Agricultor
            FROM Oferta_Trabajo
            WHERE ID_Oferta = %s
        """, (oferta_id,), fetch_one=True)
        
        if not oferta:
            return jsonify({
                'success': False,
                'message': 'Oferta no encontrada'
            }), 404
        
        if oferta['ID_Agricultor'] != user_id:
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para duplicar esta oferta'
            }), 403
        
        # Crear nueva oferta con el prefijo "Copia de"
        titulo_nuevo = f"Copia de {oferta['Titulo']}"
        
        # Insertar la copia
        nueva_oferta_id = execute_query("""
            INSERT INTO Oferta_Trabajo (ID_Agricultor, Titulo, Descripcion, Pago_Ofrecido, Estado, Fecha_Publicacion)
            VALUES (%s, %s, %s, %s, 'Abierta', NOW())
        """, (user_id, titulo_nuevo, oferta['Descripcion'], oferta['Pago_Ofrecido']))
        
        print(f"✅ Oferta {oferta_id} duplicada. Nueva ID: {nueva_oferta_id}")
        
        return jsonify({
            'success': True,
            'message': f'Oferta duplicada exitosamente',
            'nueva_oferta_id': nueva_oferta_id
        })
        
    except Exception as e:
        print(f"❌ Error duplicando oferta: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

print("✅ Endpoint de duplicar oferta cargado correctamente")


@ofertas_bp.route('/api/get_jobs', methods=['GET'])
def get_jobs():
    """Obtener todas las ofertas disponibles para trabajadores - MEJORADO"""
    try:
        # Obtener ID del usuario si está logueado (para filtrar)
        user_id = session.get('user_id')
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Si hay usuario logueado, excluir ofertas a las que ya se postuló
        if user_id:
            query = """
            SELECT 
                ot.ID_Oferta as id_oferta,
                ot.Titulo as titulo,
                ot.Descripcion as descripcion,
                ot.Pago_Ofrecido as pago_ofrecido,
                ot.Fecha_Publicacion as fecha_publicacion,
                ot.Estado as estado,
                CONCAT(u.Nombre, ' ', u.Apellido) as nombre_agricultor,
                COUNT(p.ID_Postulacion) as num_postulaciones
            FROM Oferta_Trabajo ot
            INNER JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
            LEFT JOIN Postulacion p ON ot.ID_Oferta = p.ID_Oferta
            WHERE ot.Estado = 'Abierta'
              AND ot.Fecha_Publicacion >= DATE_SUB(NOW(), INTERVAL 30 DAY)
              AND ot.ID_Oferta NOT IN (
                  SELECT ID_Oferta 
                  FROM Postulacion 
                  WHERE ID_Trabajador = %s
              )
            GROUP BY ot.ID_Oferta, ot.Titulo, ot.Descripcion, ot.Pago_Ofrecido, 
                     ot.Fecha_Publicacion, ot.Estado, u.Nombre, u.Apellido
            ORDER BY ot.Fecha_Publicacion DESC
            LIMIT 50
            """
            cursor.execute(query, (user_id,))
        else:
            # Si no hay usuario logueado, mostrar todas
            query = """
            SELECT 
                ot.ID_Oferta as id_oferta,
                ot.Titulo as titulo,
                ot.Descripcion as descripcion,
                ot.Pago_Ofrecido as pago_ofrecido,
                ot.Fecha_Publicacion as fecha_publicacion,
                ot.Estado as estado,
                CONCAT(u.Nombre, ' ', u.Apellido) as nombre_agricultor,
                COUNT(p.ID_Postulacion) as num_postulaciones
            FROM Oferta_Trabajo ot
            INNER JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
            LEFT JOIN Postulacion p ON ot.ID_Oferta = p.ID_Oferta
            WHERE ot.Estado = 'Abierta'
              AND ot.Fecha_Publicacion >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY ot.ID_Oferta, ot.Titulo, ot.Descripcion, ot.Pago_Ofrecido, 
                     ot.Fecha_Publicacion, ot.Estado, u.Nombre, u.Apellido
            ORDER BY ot.Fecha_Publicacion DESC
            LIMIT 50
            """
            cursor.execute(query)
        
        jobs = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        print(f"Ofertas encontradas: {len(jobs)}")
        
        return jsonify({
            'success': True,
            'jobs': jobs,
            'total': len(jobs)
        })
        
    except Exception as e:
        print(f"Error al obtener trabajos: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': f'Error interno del servidor: {str(e)}'
        }), 500


@ofertas_bp.route('/api/apply_job', methods=['POST'])
def apply_job():
    """Postularse a un trabajo - CORREGIDO"""
    try:
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'message': 'Sesión no válida'
            }), 401
        
        # IMPORTANTE: Usar ambos nombres posibles para el rol
        user_role = session.get('user_role') or session.get('role')
        
        print(f"🔍 DEBUG - User ID: {session['user_id']}")
        print(f"🔍 DEBUG - User Role: {user_role}")
        print(f"🔍 DEBUG - Session completa: {dict(session)}")
        
        if user_role != 'Trabajador':
            return jsonify({
                'success': False,
                'message': f'Solo los trabajadores pueden postularse. Tu rol actual: {user_role}'
            }), 403
        
        data = request.get_json()
        job_id = data.get('job_id')
        
        if not job_id:
            return jsonify({
                'success': False,
                'message': 'ID de trabajo requerido'
            }), 400
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Verificar que el trabajo existe y está abierto
        check_job_query = "SELECT Estado FROM Oferta_Trabajo WHERE ID_Oferta = %s"
        cursor.execute(check_job_query, (job_id,))
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            connection.close()
            return jsonify({
                'success': False,
                'message': 'Trabajo no encontrado'
            }), 404
        
        if result[0] != 'Abierta':
            cursor.close()
            connection.close()
            return jsonify({
                'success': False,
                'message': 'Este trabajo ya no está disponible'
            }), 400
        
        # Verificar si ya se postuló
        check_application_query = """
        SELECT ID_Postulacion FROM Postulacion 
        WHERE ID_Oferta = %s AND ID_Trabajador = %s
        """
        cursor.execute(check_application_query, (job_id, session['user_id']))
        existing_application = cursor.fetchone()
        
        if existing_application:
            cursor.close()
            connection.close()
            return jsonify({
                'success': False,
                'message': 'Ya te has postulado a este trabajo'
            }), 400
        
        # Crear postulación
        insert_query = """
        INSERT INTO Postulacion (ID_Oferta, ID_Trabajador, Fecha_Postulacion, Estado)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(insert_query, (job_id, session['user_id'], datetime.now(), 'Pendiente'))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print(f"✅ Postulación creada exitosamente para user {session['user_id']} en oferta {job_id}")
        
        return jsonify({
            'success': True,
            'message': 'Postulación enviada exitosamente'
        }), 201
        
    except Exception as e:
        print(f"❌ Error al postularse: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno del servidor: {str(e)}'
        }), 500


@ofertas_bp.route('/vista/postulaciones.html')
def postulaciones_html():
    """Página de postulaciones"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vista_path = os.path.join(base_dir, '..', '..', 'vista')
        vista_path = os.path.abspath(vista_path)
        return send_from_directory(vista_path, 'postulaciones.html')
    except Exception as e:
        print(f"Error sirviendo postulaciones.html: {e}")
        return "Archivo no encontrado", 404


@ofertas_bp.route('/assent/css/postulaciones.css')
def postulaciones_css():
    """CSS para página de postulaciones"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        css_path = os.path.join(base_dir, '..', '..', 'assent', 'css')
        css_path = os.path.abspath(css_path)
        response = send_from_directory(css_path, 'postulaciones.css')
        response.headers['Content-Type'] = 'text/css'
        return response
    except Exception as e:
        print(f"Error sirviendo postulaciones.css: {e}")
        return "CSS no encontrado", 404


@ofertas_bp.route('/js/postulaciones.js')
def postulaciones_js():
    """JavaScript para página de postulaciones"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        js_path = os.path.join(base_dir, '..', '..', 'js')
        js_path = os.path.abspath(js_path)
        response = send_from_directory(js_path, 'postulaciones.js')
        response.headers['Content-Type'] = 'application/javascript'
        return response
    except Exception as e:
        print(f"Error sirviendo postulaciones.js: {e}")
        return "JS no encontrado", 404


# ===================================================================
# ENDPOINT PARA OBTENER POSTULACIONES (MEJORADO CON DEBUG)
# ===================================================================
@ofertas_bp.route('/api/postulaciones', methods=['GET'])
def get_postulaciones():
    """API para obtener postulaciones del trabajador - MEJORADO"""
    try:
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'error': 'Sesión no válida'
            }), 401
        
        user_id = session['user_id']
        user_role = session.get('user_role') or session.get('role')
        
        print(f"📊 Obteniendo postulaciones para user_id: {user_id}, role: {user_role}")
        
        if user_role != 'Trabajador':
            return jsonify({
                'success': False,
                'error': 'Acceso denegado - Solo trabajadores'
            }), 403
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Consulta mejorada
        query = """
            SELECT 
                p.ID_Postulacion as id,
                ot.Titulo as titulo,
                CONCAT(u.Nombre, ' ', u.Apellido) as agricultor,
                u.ID_Usuario as agricultorId,
                p.Fecha_Postulacion as fechaPostulacion,
                p.Estado as estado,
                ot.Pago_Ofrecido as pago,
                COALESCE(pr.Nombre_Finca, 'Colombia') as ubicacion,
                ot.Descripcion as descripcion,
                ot.Fecha_Publicacion as fechaPublicacion,
                ot.ID_Oferta as oferta_id
            FROM Postulacion p
            INNER JOIN Oferta_Trabajo ot ON p.ID_Oferta = ot.ID_Oferta
            INNER JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
            LEFT JOIN Predio pr ON u.ID_Usuario = pr.ID_Usuario
            WHERE p.ID_Trabajador = %s
            ORDER BY p.Fecha_Postulacion DESC
        """
        
        cursor.execute(query, (user_id,))
        postulaciones = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        print(f"✅ {len(postulaciones)} postulaciones encontradas")
        
        # Procesar las postulaciones
        postulaciones_list = []
        for post in postulaciones:
            # Simular duración basada en descripción
            descripcion = post['descripcion'].lower() if post['descripcion'] else ''
            if 'cosecha' in descripcion:
                duracion = "3-5 días"
            elif 'siembra' in descripcion:
                duracion = "2-4 días"
            elif 'mantenimiento' in descripcion:
                duracion = "1-2 días"
            else:
                duracion = "1-3 días"
            
            postulacion_data = {
                'id': post['id'],
                'titulo': post['titulo'],
                'agricultor': post['agricultor'],
                'agricultorId': post['agricultorId'],
                'fechaPostulacion': post['fechaPostulacion'].isoformat(),
                'estado': post['estado'],
                'pago': float(post['pago']),
                'ubicacion': post['ubicacion'],
                'descripcion': post['descripcion'],
                'duracion': duracion,
                'ultimaActualizacion': post['fechaPostulacion'].isoformat(),
                'oferta_id': post['oferta_id']
            }
            
            postulaciones_list.append(postulacion_data)
        
        return jsonify({
            'success': True,
            'postulaciones': postulaciones_list,
            'total': len(postulaciones_list)
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo postulaciones: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error del servidor: {str(e)}'
        }), 500

print("✅ Endpoints de postulaciones corregidos y cargados")


# ================================================================
# RUTA PARA CANCELAR POSTULACIONES
# ================================================================

@ofertas_bp.route('/api/postulaciones/<int:postulacion_id>/cancelar', methods=['POST'])
@require_login
def cancelar_postulacion(postulacion_id):
    """API para cancelar una postulación específica"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role')
        
        if user_role != 'Trabajador':
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
        
        # Verificar que la postulación existe y pertenece al trabajador
        postulacion = execute_query("""
            SELECT p.ID_Postulacion, p.Estado, ot.Titulo
            FROM Postulacion p
            JOIN Oferta_Trabajo ot ON p.ID_Oferta = ot.ID_Oferta
            WHERE p.ID_Postulacion = %s AND p.ID_Trabajador = %s
        """, (postulacion_id, user_id), fetch_one=True)
        
        if not postulacion:
            return jsonify({
                'success': False, 
                'error': 'Postulación no encontrada o no tienes permisos para cancelarla'
            }), 404
        
        # Verificar que se puede cancelar (solo las pendientes)
        if postulacion['Estado'] != 'Pendiente':
            return jsonify({
                'success': False,
                'error': f'No se puede cancelar una postulación con estado: {postulacion["Estado"]}'
            }), 400
        
        # Eliminar la postulación de la base de datos
        execute_query("""
            DELETE FROM Postulacion 
            WHERE ID_Postulacion = %s AND ID_Trabajador = %s
        """, (postulacion_id, user_id))
        
        return jsonify({
            'success': True,
            'message': f'Postulación para "{postulacion["Titulo"]}" cancelada exitosamente'
        })
        
    except Exception as e:
        print(f"Error cancelando postulación: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# MEJORA EN LA API DE POSTULACIONES EXISTENTE
# ================================================================

@ofertas_bp.route('/api/postulaciones', methods=['GET'])
@require_login
def get_postulaciones_mejorada():
    """API para obtener postulaciones del trabajador (versión mejorada con favoritos)"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role')
        
        if user_role != 'Trabajador':
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
        
        # CAMBIO IMPORTANTE: Incluir TODOS los estados, incluyendo Favorito
        postulaciones = execute_query("""
            SELECT 
                p.ID_Postulacion,
                p.ID_Oferta,
                ot.Titulo,
                CONCAT(u.Nombre, ' ', u.Apellido) as Agricultor,
                u.ID_Usuario as Agricultor_ID,
                p.Fecha_Postulacion,
                p.Estado,
                ot.Pago_Ofrecido,
                COALESCE(pr.Nombre_Finca, CONCAT(u.Nombre, ' - ', SUBSTRING(u.Correo, 1, LOCATE('@', u.Correo) - 1))) as Ubicacion,
                ot.Descripcion,
                ot.Fecha_Publicacion,
                (SELECT COUNT(*) FROM Mensaje m 
                 WHERE (m.ID_Emisor = %s AND m.ID_Receptor = u.ID_Usuario) 
                    OR (m.ID_Emisor = u.ID_Usuario AND m.ID_Receptor = %s)) as Mensajes,
                CASE 
                    WHEN LOWER(ot.Descripcion) LIKE '%%cosecha%%' OR LOWER(ot.Descripcion) LIKE '%%recolección%%' THEN '3-5 días'
                    WHEN LOWER(ot.Descripcion) LIKE '%%siembra%%' THEN '2-4 días'
                    WHEN LOWER(ot.Descripcion) LIKE '%%mantenimiento%%' OR LOWER(ot.Descripcion) LIKE '%%poda%%' THEN '1-2 días'
                    WHEN LOWER(ot.Descripcion) LIKE '%%fumigación%%' THEN '1-3 días'
                    ELSE '1-3 días'
                END as Duracion_Estimada,
                CASE 
                    WHEN ot.Pago_Ofrecido >= 50000 THEN 'alta'
                    WHEN ot.Pago_Ofrecido >= 40000 THEN 'media'
                    ELSE 'baja'
                END as Prioridad
            FROM Postulacion p
            JOIN Oferta_Trabajo ot ON p.ID_Oferta = ot.ID_Oferta
            JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
            LEFT JOIN Predio pr ON u.ID_Usuario = pr.ID_Usuario
            WHERE p.ID_Trabajador = %s
            ORDER BY 
                CASE p.Estado
                    WHEN 'Pendiente' THEN 1
                    WHEN 'Aceptada' THEN 2
                    WHEN 'Favorito' THEN 3
                    WHEN 'Rechazada' THEN 4
                    ELSE 5
                END,
                p.Fecha_Postulacion DESC
        """, (user_id, user_id, user_id))
        
        postulaciones_list = []
        if postulaciones:
            for post in postulaciones:
                fecha_inicio = None
                if post['Fecha_Publicacion']:
                    fecha_inicio_dt = post['Fecha_Publicacion'] + timedelta(days=7)
                    fecha_inicio = fecha_inicio_dt.strftime('%Y-%m-%d')
                
                postulacion_data = {
                    'id': post['ID_Postulacion'],
                    'titulo': post['Titulo'],
                    'agricultor': post['Agricultor'],
                    'agricultorId': post['Agricultor_ID'],
                    'fechaPostulacion': post['Fecha_Postulacion'].isoformat() if post['Fecha_Postulacion'] else None,
                    'estado': post['Estado'],
                    'pago': float(post['Pago_Ofrecido']) if post['Pago_Ofrecido'] else 0,
                    'ubicacion': post['Ubicacion'],
                    'descripcion': post['Descripcion'] or 'Descripción no disponible',
                    'duracion': post['Duracion_Estimada'],
                    'fechaInicio': fecha_inicio,
                    'ultimaActualizacion': post['Fecha_Postulacion'].isoformat() if post['Fecha_Postulacion'] else None,
                    'mensajes': post['Mensajes'] or 0,
                    'prioridad': post['Prioridad'],
                    'oferta_id': post['ID_Oferta']
                }
                
                if post['Estado'] == 'Rechazada':
                    postulacion_data['motivoRechazo'] = 'El agricultor seleccionó otro candidato'
                
                postulaciones_list.append(postulacion_data)
        
        return jsonify({
            'success': True,
            'postulaciones': postulaciones_list,
            'total': len(postulaciones_list)
        })
        
    except Exception as e:
        print(f"Error obteniendo postulaciones: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# RUTA PARA CREAR NUEVA POSTULACIÓN
# ================================================================

@ofertas_bp.route('/api/postulaciones', methods=['POST'])
@require_login
def crear_postulacion():
    """API para crear una nueva postulación a un trabajo"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role')
        
        if user_role != 'Trabajador':
            return jsonify({'success': False, 'error': 'Solo los trabajadores pueden postularse'}), 403
        
        data = request.get_json()
        oferta_id = data.get('oferta_id')
        
        if not oferta_id:
            return jsonify({'success': False, 'error': 'ID de oferta requerido'}), 400
        
        # Verificar que la oferta existe y está abierta
        oferta = execute_query("""
            SELECT ID_Oferta, Titulo, Estado, ID_Agricultor 
            FROM Oferta_Trabajo 
            WHERE ID_Oferta = %s
        """, (oferta_id,), fetch_one=True)
        
        if not oferta:
            return jsonify({'success': False, 'error': 'Oferta de trabajo no encontrada'}), 404
        
        if oferta['Estado'] != 'Abierta':
            return jsonify({'success': False, 'error': 'Esta oferta ya no está disponible'}), 400
        
        # Verificar que el trabajador no se postule a su propia oferta (en caso de que sea agricultor también)
        if oferta['ID_Agricultor'] == user_id:
            return jsonify({'success': False, 'error': 'No puedes postularte a tu propia oferta'}), 400
        
        # Verificar que no existe ya una postulación
        postulacion_existente = execute_query("""
            SELECT ID_Postulacion FROM Postulacion 
            WHERE ID_Oferta = %s AND ID_Trabajador = %s
        """, (oferta_id, user_id), fetch_one=True)
        
        if postulacion_existente:
            return jsonify({'success': False, 'error': 'Ya te has postulado a esta oferta'}), 400
        
        # Crear la postulación
        execute_query("""
            INSERT INTO Postulacion (ID_Oferta, ID_Trabajador, Estado, Fecha_Postulacion)
            VALUES (%s, %s, 'Pendiente', CURRENT_TIMESTAMP)
        """, (oferta_id, user_id))
        
        return jsonify({
            'success': True,
            'message': f'Te has postulado exitosamente para "{oferta["Titulo"]}"'
        })
        
    except Exception as e:
        print(f"Error creando postulación: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

print("✅ Rutas para cancelar postulaciones y API mejorada agregadas correctamente")


# ================================================================
# RUTAS PARA POSTULACIONES Y FAVORITOS DESDE EL DASHBOARD
# ================================================================

@ofertas_bp.route('/api/trabajos-disponibles', methods=['GET'])
@require_login
def get_trabajos_disponibles():
    """API para obtener trabajos disponibles en el dashboard"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role')
        
        if user_role != 'Trabajador':
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
        
        # Obtener trabajos disponibles que no sean del propio usuario y que estén abiertos
        trabajos = execute_query("""
            SELECT 
                ot.ID_Oferta,
                ot.Titulo,
                ot.Descripcion,
                ot.Pago_Ofrecido,
                ot.Estado as Estado_Oferta,
                ot.Fecha_Publicacion,
                CONCAT(u.Nombre, ' ', u.Apellido) as Empleador,
                COALESCE(pr.Nombre_Finca, CONCAT(u.Nombre, ' - Finca')) as Ubicacion,
                u.ID_Usuario as Empleador_ID,
                -- Verificar si el trabajador ya se postuló
                (SELECT COUNT(*) FROM Postulacion p 
                 WHERE p.ID_Oferta = ot.ID_Oferta AND p.ID_Trabajador = %s) as Ya_Postulado,
                -- Verificar si está en favoritos
                (SELECT COUNT(*) FROM Postulacion p 
                 WHERE p.ID_Oferta = ot.ID_Oferta AND p.ID_Trabajador = %s AND p.Estado = 'Favorito') as Es_Favorito
            FROM Oferta_Trabajo ot
            JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
            LEFT JOIN Predio pr ON u.ID_Usuario = pr.ID_Usuario
            WHERE ot.ID_Agricultor != %s 
              AND ot.Estado = 'Abierta'
              AND ot.Fecha_Publicacion >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            ORDER BY ot.Fecha_Publicacion DESC
            LIMIT 20
        """, (user_id, user_id, user_id))
        
        trabajos_list = []
        if trabajos:
            for trabajo in trabajos:
                # Determinar el tipo basado en la descripción
                descripcion_lower = trabajo['Descripcion'].lower()
                if 'cosecha' in descripcion_lower or 'recolección' in descripcion_lower:
                    tipo = 'cosecha'
                elif 'siembra' in descripcion_lower:
                    tipo = 'siembra'
                elif 'mantenimiento' in descripcion_lower or 'poda' in descripcion_lower:
                    tipo = 'mantenimiento'
                elif 'recolección' in descripcion_lower:
                    tipo = 'recoleccion'
                else:
                    tipo = 'otros'
                
                # Calcular duración estimada
                if 'cosecha' in descripcion_lower or 'café' in descripcion_lower:
                    duracion = '3-5 días'
                elif 'siembra' in descripcion_lower:
                    duracion = '2-4 días'
                elif 'mantenimiento' in descripcion_lower:
                    duracion = '1-2 días'
                else:
                    duracion = '1-3 días'
                
                trabajo_data = {
                    'id': trabajo['ID_Oferta'],
                    'titulo': trabajo['Titulo'],
                    'descripcion': trabajo['Descripcion'],
                    'pago': float(trabajo['Pago_Ofrecido']) if trabajo['Pago_Ofrecido'] else 0,
                    'empleador': trabajo['Empleador'],
                    'empleador_id': trabajo['Empleador_ID'],
                    'ubicacion': trabajo['Ubicacion'],
                    'fecha_publicacion': trabajo['Fecha_Publicacion'].isoformat() if trabajo['Fecha_Publicacion'] else None,
                    'tipo': tipo,
                    'duracion': duracion,
                    'ya_postulado': bool(trabajo['Ya_Postulado']),
                    'es_favorito': bool(trabajo['Es_Favorito'])
                }
                trabajos_list.append(trabajo_data)
        
        return jsonify({
            'success': True,
            'trabajos': trabajos_list,
            'total': len(trabajos_list)
        })
        
    except Exception as e:
        print(f"Error obteniendo trabajos disponibles: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ofertas_bp.route('/api/postular-trabajo', methods=['POST'])
@require_login
def postular_trabajo():
    """API para postularse a un trabajo desde el dashboard"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role')
        
        if user_role != 'Trabajador':
            return jsonify({'success': False, 'error': 'Solo los trabajadores pueden postularse'}), 403
        
        data = request.get_json()
        oferta_id = data.get('oferta_id')
        
        if not oferta_id:
            return jsonify({'success': False, 'error': 'ID de oferta requerido'}), 400
        
        # Verificar que la oferta existe y está disponible
        oferta = execute_query("""
            SELECT 
                ot.ID_Oferta, 
                ot.Titulo, 
                ot.Estado, 
                ot.ID_Agricultor,
                CONCAT(u.Nombre, ' ', u.Apellido) as Empleador
            FROM Oferta_Trabajo ot
            JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
            WHERE ot.ID_Oferta = %s
        """, (oferta_id,), fetch_one=True)
        
        if not oferta:
            return jsonify({'success': False, 'error': 'Oferta de trabajo no encontrada'}), 404
        
        if oferta['Estado'] != 'Abierta':
            return jsonify({'success': False, 'error': 'Esta oferta ya no está disponible'}), 400
        
        # Verificar que no se postule a su propia oferta
        if oferta['ID_Agricultor'] == user_id:
            return jsonify({'success': False, 'error': 'No puedes postularte a tu propia oferta'}), 400
        
        # Verificar si ya existe una postulación (no favorito)
        postulacion_existente = execute_query("""
            SELECT ID_Postulacion FROM Postulacion 
            WHERE ID_Oferta = %s AND ID_Trabajador = %s AND Estado != 'Favorito'
        """, (oferta_id, user_id), fetch_one=True)
        
        if postulacion_existente:
            return jsonify({'success': False, 'error': 'Ya te has postulado a esta oferta'}), 400
        
        # Verificar si existe como favorito, en ese caso actualizar el estado
        favorito_existente = execute_query("""
            SELECT ID_Postulacion FROM Postulacion 
            WHERE ID_Oferta = %s AND ID_Trabajador = %s AND Estado = 'Favorito'
        """, (oferta_id, user_id), fetch_one=True)
        
        if favorito_existente:
            # Actualizar de favorito a postulación pendiente
            execute_query("""
                UPDATE Postulacion 
                SET Estado = 'Pendiente', Fecha_Postulacion = CURRENT_TIMESTAMP
                WHERE ID_Postulacion = %s
            """, (favorito_existente['ID_Postulacion'],))
        else:
            # Crear nueva postulación
            execute_query("""
                INSERT INTO Postulacion (ID_Oferta, ID_Trabajador, Estado, Fecha_Postulacion)
                VALUES (%s, %s, 'Pendiente', CURRENT_TIMESTAMP)
            """, (oferta_id, user_id))
        
        return jsonify({
            'success': True,
            'message': f'Te has postulado exitosamente para "{oferta["Titulo"]}" con {oferta["Empleador"]}',
            'oferta_titulo': oferta['Titulo'],
            'empleador': oferta['Empleador']
        })
        
    except Exception as e:
        print(f"Error creando postulación: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ofertas_bp.route('/api/dashboard-stats', methods=['GET'])
@require_login
def get_dashboard_stats():
    """API para obtener estadísticas del dashboard"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role')
        
        if user_role != 'Trabajador':
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
        
        # Contar trabajos cercanos (ofertas disponibles)
        trabajos_cercanos = execute_query("""
            SELECT COUNT(*) as total
            FROM Oferta_Trabajo ot
            WHERE ot.ID_Agricultor != %s 
              AND ot.Estado = 'Abierta'
              AND ot.Fecha_Publicacion >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """, (user_id,), fetch_one=True)
        
        # Contar postulaciones pendientes
        postulaciones_pendientes = execute_query("""
            SELECT COUNT(*) as total
            FROM Postulacion p
            WHERE p.ID_Trabajador = %s 
              AND p.Estado = 'Pendiente'
        """, (user_id,), fetch_one=True)
        
        # Contar trabajos en progreso (acuerdos activos)
        trabajos_progreso = execute_query("""
            SELECT COUNT(*) as total
            FROM Acuerdo_Laboral al
            WHERE al.ID_Trabajador = %s 
              AND al.Estado = 'Activo'
        """, (user_id,), fetch_one=True)
        
        # Contar favoritos
        favoritos = execute_query("""
            SELECT COUNT(*) as total
            FROM Postulacion p
            WHERE p.ID_Trabajador = %s 
              AND p.Estado = 'Favorito'
        """, (user_id,), fetch_one=True)
        
        return jsonify({
            'success': True,
            'stats': {
                'trabajos_cercanos': trabajos_cercanos['total'] if trabajos_cercanos else 0,
                'postulaciones': postulaciones_pendientes['total'] if postulaciones_pendientes else 0,
                'en_progreso': trabajos_progreso['total'] if trabajos_progreso else 0,
                'favoritos': favoritos['total'] if favoritos else 0
            }
        })
        
    except Exception as e:
        print(f"Error obteniendo estadísticas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

print("✅ Rutas para postulaciones y favoritos desde dashboard agregadas correctamente")


@ofertas_bp.route('/api/get_farmer_jobs', methods=['GET'])
@require_login
def get_farmer_jobs():
    """Obtener ofertas publicadas por el agricultor - CON DEBUG"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role', session.get('role'))
        
        # DEBUGGING
        print(f"🔍 DEBUG - User ID: {user_id}")
        print(f"🔍 DEBUG - User Role: {user_role}")
        print(f"🔍 DEBUG - Session data: {dict(session)}")
        
        if user_role != 'Agricultor':
            print(f"❌ DEBUG - Usuario no es agricultor: {user_role}")
            return jsonify({
                'success': False,
                'message': f'Solo los agricultores pueden ver sus ofertas. Tu rol: {user_role}'
            }), 403
        
        # Primero, verificar cuántas ofertas hay en total para este usuario
        total_ofertas = execute_query("""
            SELECT COUNT(*) as total
            FROM Oferta_Trabajo 
            WHERE ID_Agricultor = %s
        """, (user_id,), fetch_one=True)
        
        print(f"🔍 DEBUG - Total ofertas en BD para user {user_id}: {total_ofertas['total'] if total_ofertas else 0}")
        
        # Consulta con debugging
        ofertas = execute_query("""
            SELECT 
                ot.ID_Oferta as id_oferta,
                ot.Titulo as titulo,
                ot.Descripcion as descripcion,
                ot.Pago_Ofrecido as pago_ofrecido,
                ot.Fecha_Publicacion as fecha_publicacion,
                ot.Estado as estado,
                COUNT(p.ID_Postulacion) as num_postulaciones
            FROM Oferta_Trabajo ot
            LEFT JOIN Postulacion p ON ot.ID_Oferta = p.ID_Oferta 
            WHERE ot.ID_Agricultor = %s
            GROUP BY ot.ID_Oferta, ot.Titulo, ot.Descripcion, ot.Pago_Ofrecido, ot.Fecha_Publicacion, ot.Estado
            ORDER BY ot.Fecha_Publicacion DESC
        """, (user_id,))
        
        print(f"🔍 DEBUG - Ofertas encontradas: {len(ofertas) if ofertas else 0}")
        if ofertas:
            for i, oferta in enumerate(ofertas):
                print(f"🔍 DEBUG - Oferta {i+1}: {oferta['titulo']} - Estado: {oferta['estado']}")
        
        # Procesar ofertas
        ofertas_procesadas = []
        if ofertas:
            for oferta in ofertas:
                ubicacion = None
                if oferta['descripcion']:
                    desc_text = str(oferta['descripcion'])
                    if 'Ubicación:' in desc_text:
                        try:
                            ubicacion_parte = desc_text.split('Ubicación:')[-1].strip()
                            ubicacion = ubicacion_parte.split('\n')[0].strip()
                        except:
                            ubicacion = None
                
                ofertas_procesadas.append({
                    'id_oferta': oferta['id_oferta'],
                    'titulo': oferta['titulo'],
                    'descripcion': oferta['descripcion'],
                    'pago_ofrecido': float(oferta['pago_ofrecido']) if oferta['pago_ofrecido'] else 0,
                    'fecha_publicacion': oferta['fecha_publicacion'].strftime('%Y-%m-%d') if oferta['fecha_publicacion'] else None,
                    'estado': oferta['estado'],
                    'num_postulaciones': oferta['num_postulaciones'] or 0,
                    'ubicacion': ubicacion
                })
        
        print(f"🔍 DEBUG - Ofertas procesadas: {len(ofertas_procesadas)}")
        
        # Estadísticas
        estadisticas = execute_query("""
            SELECT 
                COUNT(CASE WHEN ot.Estado = 'Abierta' THEN 1 END) as ofertas_activas,
                COUNT(DISTINCT p.ID_Trabajador) as trabajadores_postulados
            FROM Oferta_Trabajo ot
            LEFT JOIN Postulacion p ON ot.ID_Oferta = p.ID_Oferta
            WHERE ot.ID_Agricultor = %s
        """, (user_id,), fetch_one=True)
        
        response_data = {
            'success': True,
            'ofertas': ofertas_procesadas,
            'estadisticas': {
                'ofertas_activas': estadisticas['ofertas_activas'] if estadisticas else 0,
                'trabajadores_contratados': estadisticas['trabajadores_postulados'] if estadisticas else 0
            }
        }
        
        print(f"🔍 DEBUG - Response final: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Error al obtener ofertas del agricultor: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


# ================================================================
# APIs PARA EDITAR Y ELIMINAR OFERTAS (AGRICULTORES)
# ================================================================

@ofertas_bp.route('/api/edit_job/<int:job_id>', methods=['PUT'])
@require_login
def edit_job(job_id):
    """Editar una oferta de trabajo existente"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role', session.get('role'))
        
        print(f"🔄 Editando oferta {job_id} - Usuario: {user_id}, Rol: {user_role}")
        
        if user_role != 'Agricultor':
            return jsonify({
                'success': False,
                'message': 'Solo los agricultores pueden editar ofertas'
            }), 403
        
        # Verificar que la oferta existe y pertenece al agricultor
        oferta_actual = execute_query("""
            SELECT ID_Oferta, ID_Agricultor, Titulo, Estado 
            FROM Oferta_Trabajo 
            WHERE ID_Oferta = %s
        """, (job_id,), fetch_one=True)
        
        if not oferta_actual:
            return jsonify({
                'success': False,
                'message': 'Oferta no encontrada'
            }), 404
        
        if oferta_actual['ID_Agricultor'] != user_id:
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para editar esta oferta'
            }), 403
        
        # Obtener datos del request
        data = request.get_json()
        
        titulo = data.get('titulo', '').strip()
        descripcion = data.get('descripcion', '').strip()
        pago = data.get('pago')
        ubicacion = data.get('ubicacion', '').strip()
        
        # Validaciones
        if not titulo or len(titulo) < 10:
            return jsonify({
                'success': False,
                'message': 'El título debe tener al menos 10 caracteres'
            }), 400
        
        if not descripcion or len(descripcion) < 20:
            return jsonify({
                'success': False,
                'message': 'La descripción debe tener al menos 20 caracteres'
            }), 400
        
        if not pago or int(pago) < 10000:
            return jsonify({
                'success': False,
                'message': 'El pago mínimo debe ser $10,000 COP'
            }), 400
        
        # Preparar descripción completa con ubicación
        descripcion_completa = descripcion
        if ubicacion:
            # Actualizar o agregar ubicación
            if 'Ubicación:' in descripcion_completa:
                # Reemplazar ubicación existente
                partes = descripcion_completa.split('\n\nUbicación:')
                descripcion_completa = partes[0] + f"\n\nUbicación: {ubicacion}"
            else:
                # Agregar nueva ubicación
                descripcion_completa += f"\n\nUbicación: {ubicacion}"
        
        # Actualizar en la base de datos
        execute_query("""
            UPDATE Oferta_Trabajo 
            SET Titulo = %s, Descripcion = %s, Pago_Ofrecido = %s
            WHERE ID_Oferta = %s
        """, (titulo, descripcion_completa, int(pago), job_id))
        
        print(f"✅ Oferta {job_id} actualizada exitosamente")
        
        return jsonify({
            'success': True,
            'message': f'Oferta "{titulo}" actualizada correctamente',
            'oferta': {
                'id': job_id,
                'titulo': titulo,
                'descripcion': descripcion_completa,
                'pago': int(pago),
                'ubicacion': ubicacion
            }
        })
        
    except Exception as e:
        print(f"❌ Error editando oferta: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


@ofertas_bp.route('/api/delete_job/<int:job_id>', methods=['DELETE'])
@require_login
def delete_job(job_id):
    """Eliminar una oferta de trabajo"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role', session.get('role'))
        
        print(f"🗑️ Eliminando oferta {job_id} - Usuario: {user_id}, Rol: {user_role}")
        
        if user_role != 'Agricultor':
            return jsonify({
                'success': False,
                'message': 'Solo los agricultores pueden eliminar ofertas'
            }), 403
        
        # Verificar que la oferta existe y pertenece al agricultor
        oferta = execute_query("""
            SELECT ID_Oferta, ID_Agricultor, Titulo, Estado 
            FROM Oferta_Trabajo 
            WHERE ID_Oferta = %s
        """, (job_id,), fetch_one=True)
        
        if not oferta:
            return jsonify({
                'success': False,
                'message': 'Oferta no encontrada'
            }), 404
        
        if oferta['ID_Agricultor'] != user_id:
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para eliminar esta oferta'
            }), 403
        
        # Verificar si hay acuerdos laborales activos
        acuerdos_activos = execute_query("""
            SELECT COUNT(*) as total 
            FROM Acuerdo_Laboral 
            WHERE ID_Oferta = %s AND Estado = 'Activo'
        """, (job_id,), fetch_one=True)
        
        if acuerdos_activos and acuerdos_activos['total'] > 0:
            return jsonify({
                'success': False,
                'message': f'No se puede eliminar una oferta con {acuerdos_activos["total"]} contrato(s) activo(s)'
            }), 400
        
        # Eliminar primero las postulaciones
        execute_query("DELETE FROM Postulacion WHERE ID_Oferta = %s", (job_id,))
        print(f"✅ Postulaciones eliminadas para oferta {job_id}")
        
        # Eliminar acuerdos laborales finalizados/cancelados
        execute_query("DELETE FROM Acuerdo_Laboral WHERE ID_Oferta = %s", (job_id,))
        print(f"✅ Acuerdos laborales eliminados para oferta {job_id}")
        
        # Finalmente, eliminar la oferta
        execute_query("DELETE FROM Oferta_Trabajo WHERE ID_Oferta = %s", (job_id,))
        print(f"✅ Oferta {job_id} eliminada exitosamente")
        
        return jsonify({
            'success': True,
            'message': f'Oferta "{oferta["Titulo"]}" eliminada correctamente'
        })
        
    except Exception as e:
        print(f"❌ Error eliminando oferta: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


# ================================================================
# VERIFICACIÓN Y CIERRE AUTOMÁTICO DE OFERTAS
# ================================================================

@ofertas_bp.route('/api/cerrar_oferta_manual/<int:job_id>', methods=['PUT'])
@require_login
def cerrar_oferta_manual(job_id):
    """Cerrar manualmente una oferta de trabajo"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role', session.get('role'))
        
        if user_role != 'Agricultor':
            return jsonify({
                'success': False,
                'message': 'Solo los agricultores pueden cerrar ofertas'
            }), 403
        
        # Verificar que la oferta existe y pertenece al agricultor
        oferta = execute_query("""
            SELECT ID_Oferta, ID_Agricultor, Titulo, Estado 
            FROM Oferta_Trabajo 
            WHERE ID_Oferta = %s
        """, (job_id,), fetch_one=True)
        
        if not oferta:
            return jsonify({
                'success': False,
                'message': 'Oferta no encontrada'
            }), 404
        
        if oferta['ID_Agricultor'] != user_id:
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para cerrar esta oferta'
            }), 403
        
        if oferta['Estado'] == 'Cerrada':
            return jsonify({
                'success': False,
                'message': 'La oferta ya está cerrada'
            }), 400
        
        # Cerrar la oferta
        execute_query("""
            UPDATE Oferta_Trabajo 
            SET Estado = 'Cerrada' 
            WHERE ID_Oferta = %s
        """, (job_id,))
        
        # Rechazar automáticamente las postulaciones pendientes
        execute_query("""
            UPDATE Postulacion 
            SET Estado = 'Rechazada' 
            WHERE ID_Oferta = %s AND Estado = 'Pendiente'
        """, (job_id,))
        
        # Finalizar acuerdos laborales activos
        execute_query("""
            UPDATE Acuerdo_Laboral 
            SET Estado = 'Finalizado', Fecha_Fin = CURDATE()
            WHERE ID_Oferta = %s AND Estado = 'Activo'
        """, (job_id,))
        
        print(f"✅ Oferta {job_id} cerrada manualmente")
        
        return jsonify({
            'success': True,
            'message': f'Oferta "{oferta["Titulo"]}" cerrada correctamente'
        })
        
    except Exception as e:
        print(f"❌ Error cerrando oferta: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@ofertas_bp.route('/api/reabrir_oferta_cerrada/<int:job_id>', methods=['PUT'])
@require_login
def reabrir_oferta_cerrada(job_id):
    """Reabrir una oferta que fue cerrada"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role', session.get('role'))
        
        if user_role != 'Agricultor':
            return jsonify({
                'success': False,
                'message': 'Solo los agricultores pueden reabrir ofertas'
            }), 403
        
        # Verificar que la oferta existe y pertenece al agricultor
        oferta = execute_query("""
            SELECT ID_Oferta, ID_Agricultor, Titulo, Estado 
            FROM Oferta_Trabajo 
            WHERE ID_Oferta = %s
        """, (job_id,), fetch_one=True)
        
        if not oferta:
            return jsonify({
                'success': False,
                'message': 'Oferta no encontrada'
            }), 404
        
        if oferta['ID_Agricultor'] != user_id:
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para reabrir esta oferta'
            }), 403
        
        if oferta['Estado'] != 'Cerrada':
            return jsonify({
                'success': False,
                'message': 'Solo se pueden reabrir ofertas cerradas'
            }), 400
        
        # Reabrir la oferta
        execute_query("""
            UPDATE Oferta_Trabajo 
            SET Estado = 'Abierta' 
            WHERE ID_Oferta = %s
        """, (job_id,))
        
        print(f"✅ Oferta {job_id} reabierta exitosamente")
        
        return jsonify({
            'success': True,
            'message': f'Oferta "{oferta["Titulo"]}" reabierta correctamente'
        })
        
    except Exception as e:
        print(f"❌ Error reabriendo oferta: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ================================================================
# ESTADÍSTICAS DE CIERRE (PARA MOSTRAR EN CONFIRMACIÓN)
# ================================================================

@ofertas_bp.route('/api/estadisticas_cierre/<int:job_id>', methods=['GET'])
@require_login
def estadisticas_cierre(job_id):
    """Obtener estadísticas antes de cerrar una oferta"""
    try:
        user_id = session['user_id']
        
        # Verificar propiedad
        oferta = execute_query("""
            SELECT ID_Agricultor 
            FROM Oferta_Trabajo 
            WHERE ID_Oferta = %s
        """, (job_id,), fetch_one=True)
        
        if not oferta or oferta['ID_Agricultor'] != user_id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
        # Obtener estadísticas de postulaciones
        stats = execute_query("""
            SELECT 
                COUNT(CASE WHEN Estado = 'Pendiente' THEN 1 END) as pendientes,
                COUNT(CASE WHEN Estado = 'Aceptada' THEN 1 END) as aceptadas,
                COUNT(CASE WHEN Estado = 'Rechazada' THEN 1 END) as rechazadas,
                COUNT(*) as total
            FROM Postulacion
            WHERE ID_Oferta = %s
        """, (job_id,), fetch_one=True)
        
        return jsonify({
            'success': True,
            'stats': {
                'pendientes': stats['pendientes'] or 0,
                'aceptadas': stats['aceptadas'] or 0,
                'rechazadas': stats['rechazadas'] or 0,
                'total': stats['total'] or 0
            }
        })
        
    except Exception as e:
        print(f"Error obteniendo estadísticas: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


print("✅ APIs de edición y eliminación de ofertas cargadas correctamente")
print("📋 Nuevas rutas disponibles:")
print("   • PUT    /api/edit_job/<job_id>")
print("   • DELETE /api/delete_job/<job_id>")
print("   • PUT    /api/cerrar_oferta_manual/<job_id>")
print("   • PUT    /api/reabrir_oferta_cerrada/<job_id>")
print("   • GET    /api/estadisticas_cierre/<job_id>")


# ================================================================
# ENDPOINTS PARA CIERRE DE OFERTAS - CON NOMBRES ÚNICOS
# ================================================================

# ================================================================
# 1. CERRAR OFERTA MANUALMENTE (NUEVO NOMBRE)
# ================================================================

@ofertas_bp.route('/api/cerrar_oferta_manual_v2/<int:job_id>', methods=['PUT'])
def cerrar_oferta_manual_v2(job_id):
    """Cerrar una oferta manualmente y guardar Fecha_Fin"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        user_id = session['user_id']
        user_role = session.get('user_role', session.get('role'))
        
        print(f"🔒 Cerrando oferta {job_id} por usuario {user_id}")
        
        if user_role != 'Agricultor':
            return jsonify({'success': False, 'message': 'Solo agricultores pueden cerrar ofertas'}), 403
        
        oferta = execute_query("""
            SELECT ID_Oferta, Titulo, Estado, ID_Agricultor
            FROM Oferta_Trabajo
            WHERE ID_Oferta = %s
        """, (job_id,), fetch_one=True)
        
        if not oferta:
            return jsonify({'success': False, 'message': 'Oferta no encontrada'}), 404
        
        if oferta['ID_Agricultor'] != user_id:
            return jsonify({'success': False, 'message': 'Sin permisos'}), 403
        
        if oferta['Estado'] == 'Cerrada':
            return jsonify({'success': False, 'message': 'Ya está cerrada'}), 400
        
        # Cerrar oferta
        execute_query("UPDATE Oferta_Trabajo SET Estado = 'Cerrada' WHERE ID_Oferta = %s", (job_id,))
        
        # Rechazar pendientes
        execute_query("UPDATE Postulacion SET Estado = 'Rechazada' WHERE ID_Oferta = %s AND Estado = 'Pendiente'", (job_id,))
        
        # GUARDAR FECHA_FIN
        execute_query("""
            UPDATE Acuerdo_Laboral 
            SET Estado = 'Finalizado', Fecha_Fin = CURDATE()
            WHERE ID_Oferta = %s AND Estado = 'Activo' AND Fecha_Fin IS NULL
        """, (job_id,))
        
        print(f"✅ Oferta {job_id} cerrada con Fecha_Fin guardada")
        
        return jsonify({'success': True, 'message': f'Oferta "{oferta["Titulo"]}" cerrada exitosamente'})
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ================================================================
# 2. REABRIR OFERTA (NUEVO NOMBRE)
# ================================================================

@ofertas_bp.route('/api/reabrir_oferta_v2/<int:job_id>', methods=['PUT'])
def reabrir_oferta_v2(job_id):
    """Reabrir una oferta cerrada"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        user_id = session['user_id']
        user_role = session.get('user_role', session.get('role'))
        
        if user_role != 'Agricultor':
            return jsonify({'success': False, 'message': 'Solo agricultores'}), 403
        
        oferta = execute_query("""
            SELECT ID_Oferta, Titulo, Estado, ID_Agricultor
            FROM Oferta_Trabajo WHERE ID_Oferta = %s
        """, (job_id,), fetch_one=True)
        
        if not oferta or oferta['ID_Agricultor'] != user_id:
            return jsonify({'success': False, 'message': 'Oferta no encontrada o sin permisos'}), 404
        
        if oferta['Estado'] != 'Cerrada':
            return jsonify({'success': False, 'message': 'La oferta no está cerrada'}), 400
        
        execute_query("UPDATE Oferta_Trabajo SET Estado = 'Abierta' WHERE ID_Oferta = %s", (job_id,))
        
        print(f"✅ Oferta {job_id} reabierta")
        return jsonify({'success': True, 'message': f'Oferta "{oferta["Titulo"]}" reabierta'})
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ================================================================
# 3. ACEPTAR POSTULACIÓN V3 (NUEVO NOMBRE)
# ================================================================

@ofertas_bp.route('/api/aceptar_postulacion_v3/<int:application_id>', methods=['PUT'])
def aceptar_postulacion_v3(application_id):
    """Aceptar postulación con opción de cerrar oferta"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        user_id = session['user_id']
        user_role = session.get('user_role', session.get('role'))
        
        if user_role != 'Agricultor':
            return jsonify({'success': False, 'message': 'Solo agricultores'}), 403
        
        data = request.get_json()
        cerrar_oferta = data.get('cerrar_oferta', False)
        
        postulacion = execute_query("""
            SELECT p.ID_Postulacion, p.ID_Oferta, p.ID_Trabajador, p.Estado,
                   ot.ID_Agricultor, ot.Titulo, ot.Pago_Ofrecido,
                   CONCAT(u.Nombre, ' ', u.Apellido) as nombre_trabajador
            FROM Postulacion p
            INNER JOIN Oferta_Trabajo ot ON p.ID_Oferta = ot.ID_Oferta
            INNER JOIN Usuario u ON p.ID_Trabajador = u.ID_Usuario
            WHERE p.ID_Postulacion = %s
        """, (application_id,), fetch_one=True)
        
        if not postulacion or postulacion['ID_Agricultor'] != user_id:
            return jsonify({'success': False, 'message': 'Postulación no encontrada'}), 404
        
        if postulacion['Estado'] != 'Pendiente':
            return jsonify({'success': False, 'message': 'Ya fue procesada'}), 400
        
        # Aceptar
        execute_query("UPDATE Postulacion SET Estado = 'Aceptada' WHERE ID_Postulacion = %s", (application_id,))
        
        # Crear acuerdo si no existe
        acuerdo_existe = execute_query("""
            SELECT ID_Acuerdo FROM Acuerdo_Laboral
            WHERE ID_Oferta = %s AND ID_Trabajador = %s
        """, (postulacion['ID_Oferta'], postulacion['ID_Trabajador']), fetch_one=True)
        
        if not acuerdo_existe:
            execute_query("""
                INSERT INTO Acuerdo_Laboral 
                (ID_Oferta, ID_Trabajador, Fecha_Inicio, Pago_Final, Estado)
                VALUES (%s, %s, CURDATE(), %s, 'Activo')
            """, (postulacion['ID_Oferta'], postulacion['ID_Trabajador'], postulacion['Pago_Ofrecido']))
        
        mensaje = f'Postulación de {postulacion["nombre_trabajador"]} aceptada'
        
        # Si debe cerrar oferta
        if cerrar_oferta:
            execute_query("UPDATE Oferta_Trabajo SET Estado = 'Cerrada' WHERE ID_Oferta = %s", (postulacion['ID_Oferta'],))
            execute_query("""
                UPDATE Postulacion SET Estado = 'Rechazada'
                WHERE ID_Oferta = %s AND Estado = 'Pendiente' AND ID_Postulacion != %s
            """, (postulacion['ID_Oferta'], application_id))
            execute_query("""
                UPDATE Acuerdo_Laboral 
                SET Estado = 'Finalizado', Fecha_Fin = CURDATE()
                WHERE ID_Oferta = %s AND Estado = 'Activo' AND Fecha_Fin IS NULL
            """, (postulacion['ID_Oferta'],))
            mensaje += ' y oferta cerrada'
        
        return jsonify({'success': True, 'message': mensaje, 'oferta_cerrada': cerrar_oferta})
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ================================================================
# 4. RECHAZAR POSTULACIÓN V3 (NUEVO NOMBRE)
# ================================================================

@ofertas_bp.route('/api/rechazar_postulacion_v3/<int:application_id>', methods=['PUT'])
def rechazar_postulacion_v3(application_id):
    """Rechazar postulación"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        user_id = session['user_id']
        user_role = session.get('user_role', session.get('role'))
        
        if user_role != 'Agricultor':
            return jsonify({'success': False, 'message': 'Solo agricultores'}), 403
        
        postulacion = execute_query("""
            SELECT p.ID_Postulacion, p.Estado, ot.ID_Agricultor,
                   CONCAT(u.Nombre, ' ', u.Apellido) as nombre_trabajador
            FROM Postulacion p
            INNER JOIN Oferta_Trabajo ot ON p.ID_Oferta = ot.ID_Oferta
            INNER JOIN Usuario u ON p.ID_Trabajador = u.ID_Usuario
            WHERE p.ID_Postulacion = %s
        """, (application_id,), fetch_one=True)
        
        if not postulacion or postulacion['ID_Agricultor'] != user_id:
            return jsonify({'success': False, 'message': 'No encontrada'}), 404
        
        if postulacion['Estado'] != 'Pendiente':
            return jsonify({'success': False, 'message': 'Ya fue procesada'}), 400
        
        execute_query("UPDATE Postulacion SET Estado = 'Rechazada' WHERE ID_Postulacion = %s", (application_id,))
        
        return jsonify({'success': True, 'message': f'Postulación de {postulacion["nombre_trabajador"]} rechazada'})
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ================================================================
# 5. ESTADÍSTICAS V2 (NUEVO NOMBRE)
# ================================================================

@ofertas_bp.route('/api/estadisticas_cierre_v2/<int:job_id>', methods=['GET'])
def estadisticas_cierre_v2(job_id):
    """Obtener estadísticas de oferta"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        stats = execute_query("""
            SELECT 
                COUNT(CASE WHEN p.Estado = 'Pendiente' THEN 1 END) as pendientes,
                COUNT(CASE WHEN p.Estado = 'Aceptada' THEN 1 END) as aceptadas,
                COUNT(CASE WHEN p.Estado = 'Rechazada' THEN 1 END) as rechazadas,
                COUNT(*) as total
            FROM Postulacion p
            WHERE p.ID_Oferta = %s
        """, (job_id,), fetch_one=True)
        
        return jsonify({
            'success': True,
            'stats': {
                'pendientes': stats['pendientes'] or 0,
                'aceptadas': stats['aceptadas'] or 0,
                'rechazadas': stats['rechazadas'] or 0,
                'total': stats['total'] or 0
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

