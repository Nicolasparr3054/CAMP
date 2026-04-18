# Blueprint: notificaciones
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

notif_bp = Blueprint('notificaciones', __name__)
from blueprints.helpers import require_login, require_role, hash_password, verify_password, no_cache

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

notif_bp = Blueprint('notificaciones', __name__)
from blueprints.helpers import require_login, require_role, hash_password, verify_password, no_cache


# ================================================================
# NOTIFICACIONES PROACTIVAS (RF18 - Parte de notificar usuarios)
# ================================================================

@notif_bp.route('/api/notificar-usuarios-habilidades', methods=['POST'])
@require_login
def notificar_usuarios_habilidades():
    """Notificar a usuarios con habilidades específicas sobre una nueva oferta"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role')
        
        if user_role != 'Agricultor':
            return jsonify({
                'success': False,
                'message': 'Solo agricultores pueden enviar notificaciones'
            }), 403
        
        data = request.get_json()
        oferta_id = data.get('oferta_id')
        
        if not oferta_id:
            return jsonify({
                'success': False,
                'message': 'ID de oferta requerido'
            }), 400
        
        # Obtener información de la oferta
        oferta = execute_query("""
            SELECT 
                ot.ID_Oferta,
                ot.Titulo,
                ot.Descripcion,
                ot.Pago_Ofrecido,
                ot.ID_Agricultor
            FROM Oferta_Trabajo ot
            WHERE ot.ID_Oferta = %s AND ot.ID_Agricultor = %s
        """, (oferta_id, user_id), fetch_one=True)
        
        if not oferta:
            return jsonify({
                'success': False,
                'message': 'Oferta no encontrada o sin permisos'
            }), 404
        
        # Analizar la descripción para extraer habilidades requeridas
        descripcion_lower = oferta['Descripcion'].lower()
        
        # Buscar trabajadores con habilidades relevantes
        trabajadores_query = """
            SELECT DISTINCT
                u.ID_Usuario,
                u.Nombre,
                u.Apellido,
                u.Correo,
                GROUP_CONCAT(h.Nombre SEPARATOR ', ') as habilidades_coincidentes
            FROM Usuario u
            JOIN Habilidad h ON u.ID_Usuario = h.ID_Trabajador
            WHERE u.Rol = 'Trabajador' 
              AND u.Estado = 'Activo'
              AND (
                  %s LIKE CONCAT('%%', h.Nombre, '%%') OR
                  %s LIKE CONCAT('%%', h.Clasificacion, '%%')
              )
              AND u.ID_Usuario NOT IN (
                  SELECT ID_Trabajador 
                  FROM Postulacion 
                  WHERE ID_Oferta = %s
              )
            GROUP BY u.ID_Usuario
            LIMIT 50
        """
        
        trabajadores_notificar = execute_query(
            trabajadores_query,
            (descripcion_lower, descripcion_lower, oferta_id)
        )
        
        # Crear notificaciones (guardar en tabla Mensaje)
        notificaciones_creadas = 0
        if trabajadores_notificar:
            for trabajador in trabajadores_notificar:
                mensaje_contenido = f"""
Nueva oportunidad de trabajo que coincide con tu perfil:

📋 {oferta['Titulo']}
💰 Pago: ${oferta['Pago_Ofrecido']:,.0f}
✨ Habilidades coincidentes: {trabajador['habilidades_coincidentes']}

¡No pierdas esta oportunidad! Postúlate ahora.
                """.strip()
                
                execute_query("""
                    INSERT INTO Mensaje 
                    (ID_Emisor, ID_Receptor, Contenido, Estado, Fecha_Envio)
                    VALUES (%s, %s, %s, 'Enviado', NOW())
                """, (user_id, trabajador['ID_Usuario'], mensaje_contenido))
                
                notificaciones_creadas += 1
        
        return jsonify({
            'success': True,
            'message': f'Notificaciones enviadas a {notificaciones_creadas} trabajadores',
            'total_notificados': notificaciones_creadas
        })
        
    except Exception as e:
        print(f"Error enviando notificaciones: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


print("✅ APIs de Búsqueda y Recomendaciones cargadas:")
print("   🔍 RF18: Búsqueda avanzada de trabajadores")
print("   💡 RF24: Sistema de recomendaciones personalizadas")
print("   📧 Notificaciones proactivas por habilidades")


# ================================================================
# ENDPOINTS DE NOTIFICACIONES DINÁMICAS
# Agregar al final de tu app.py (después de tus otros endpoints)
# ================================================================

@notif_bp.route('/api/notificaciones', methods=['GET'])
def obtener_notificaciones():
    """Genera notificaciones dinámicamente desde las tablas existentes"""
    try:
        # Verificar sesión
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        user_id = session.get('user_id')
        user_role = session.get('user_role', '')
        notificaciones_leidas = session.get('notificaciones_leidas', [])
        
        print(f"🔔 Generando notificaciones para user_id={user_id}, role={user_role}")
        
        # Obtener conexión
        conexion = get_db_connection()
        if not conexion:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
        
        cursor = conexion.cursor(dictionary=True)
        notificaciones = []
        
        # ============================================================
        # NOTIFICACIONES PARA TRABAJADOR
        # ============================================================
        if user_role == 'Trabajador':
            
            # 1. Postulaciones respondidas (últimos 7 días)
            query_postulaciones = """
                SELECT 
                    p.id_postulacion, p.estado, p.fecha_postulacion,
                    o.titulo as oferta_titulo, o.id_oferta,
                    CONCAT(u.first_name, ' ', u.last_name) as nombre_agricultor
                FROM postulaciones p
                JOIN ofertas_trabajo o ON o.id_oferta = p.id_oferta
                JOIN usuarios u ON u.id_usuario = o.id_agricultor
                WHERE p.id_trabajador = %s
                AND p.estado IN ('Aceptada', 'Rechazada')
                AND p.fecha_postulacion >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                ORDER BY p.fecha_postulacion DESC
                LIMIT 10
            """
            
            cursor.execute(query_postulaciones, (user_id,))
            postulaciones = cursor.fetchall()
            
            for post in postulaciones:
                notif_id = f"post_{post['estado'].lower()}_{post['id_postulacion']}"
                
                if post['estado'] == 'Aceptada':
                    notificaciones.append({
                        'id': notif_id,
                        'tipo': 'postulacion_aceptada',
                        'titulo': '¡Felicitaciones! 🎉',
                        'mensaje': f"{post['nombre_agricultor']} aceptó tu postulación para '{post['oferta_titulo']}'",
                        'fecha': str(post['fecha_postulacion']),
                        'leida': notif_id in notificaciones_leidas,
                        'url_accion': '/vista/postulaciones.html'
                    })
                else:
                    notificaciones.append({
                        'id': notif_id,
                        'tipo': 'postulacion_rechazada',
                        'titulo': 'Postulación no aceptada',
                        'mensaje': f"Tu postulación para '{post['oferta_titulo']}' no fue aceptada",
                        'fecha': str(post['fecha_postulacion']),
                        'leida': notif_id in notificaciones_leidas,
                        'url_accion': '/vista/index-trabajador.html'
                    })
            
            # 2. Nuevas ofertas (últimas 24 horas)
            query_ofertas = """
                SELECT id_oferta, titulo, pago_ofrecido, fecha_publicacion, ubicacion
                FROM ofertas_trabajo
                WHERE estado = 'Abierta'
                AND fecha_publicacion >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                ORDER BY fecha_publicacion DESC
                LIMIT 5
            """
            
            cursor.execute(query_ofertas)
            ofertas = cursor.fetchall()
            
            for oferta in ofertas:
                notif_id = f"nueva_oferta_{oferta['id_oferta']}"
                pago = float(oferta['pago_ofrecido']) if oferta['pago_ofrecido'] else 0
                notificaciones.append({
                    'id': notif_id,
                    'tipo': 'nueva_oferta',
                    'titulo': 'Nueva oferta disponible 💼',
                    'mensaje': f"{oferta['titulo']} - ${pago:,.0f}/día en {oferta['ubicacion']}",
                    'fecha': str(oferta['fecha_publicacion']),
                    'leida': notif_id in notificaciones_leidas,
                    'url_accion': '/vista/index-trabajador.html'
                })
            
            # 3. Recordatorios de trabajos aceptados
            query_recordatorios = """
                SELECT 
                    p.id_postulacion, o.titulo, p.fecha_postulacion,
                    CONCAT(u.first_name, ' ', u.last_name) as nombre_agricultor
                FROM postulaciones p
                JOIN ofertas_trabajo o ON o.id_oferta = p.id_oferta
                JOIN usuarios u ON u.id_usuario = o.id_agricultor
                WHERE p.id_trabajador = %s
                AND p.estado = 'Aceptada'
                AND o.estado = 'Abierta'
                ORDER BY p.fecha_postulacion DESC
                LIMIT 3
            """
            
            cursor.execute(query_recordatorios, (user_id,))
            trabajos = cursor.fetchall()
            
            for trabajo in trabajos:
                notif_id = f"recordatorio_{trabajo['id_postulacion']}"
                notificaciones.append({
                    'id': notif_id,
                    'tipo': 'recordatorio',
                    'titulo': 'Recordatorio de trabajo 📅',
                    'mensaje': f"Trabajo confirmado: '{trabajo['titulo']}' con {trabajo['nombre_agricultor']}",
                    'fecha': str(trabajo['fecha_postulacion']),
                    'leida': notif_id in notificaciones_leidas,
                    'url_accion': '/vista/postulaciones.html'
                })
        
        # ============================================================
        # NOTIFICACIONES PARA AGRICULTOR
        # ============================================================
        elif user_role == 'Agricultor':
            
            # 1. Nuevas postulaciones pendientes (últimos 3 días)
            query_nuevas_post = """
                SELECT 
                    p.id_postulacion, p.fecha_postulacion,
                    o.titulo as oferta_titulo, o.id_oferta,
                    CONCAT(u.first_name, ' ', u.last_name) as nombre_trabajador,
                    COALESCE((SELECT AVG(c.calificacion) 
                     FROM calificaciones c 
                     WHERE c.id_calificado = p.id_trabajador), 0) as calificacion
                FROM postulaciones p
                JOIN ofertas_trabajo o ON o.id_oferta = p.id_oferta
                JOIN usuarios u ON u.id_usuario = p.id_trabajador
                WHERE o.id_agricultor = %s
                AND p.estado = 'Pendiente'
                AND p.fecha_postulacion >= DATE_SUB(NOW(), INTERVAL 3 DAY)
                ORDER BY p.fecha_postulacion DESC
                LIMIT 15
            """
            
            cursor.execute(query_nuevas_post, (user_id,))
            nuevas_post = cursor.fetchall()
            
            for post in nuevas_post:
                notif_id = f"nueva_postulacion_{post['id_postulacion']}"
                calificacion = float(post['calificacion']) if post['calificacion'] else 0
                estrellas = '⭐' * int(round(calificacion))
                
                notificaciones.append({
                    'id': notif_id,
                    'tipo': 'nueva_postulacion',
                    'titulo': 'Nueva postulación 👤',
                    'mensaje': f"{post['nombre_trabajador']} {estrellas} se postuló a '{post['oferta_titulo']}'",
                    'fecha': str(post['fecha_postulacion']),
                    'leida': notif_id in notificaciones_leidas,
                    'url_accion': f'/vista/index-agricultor.html#oferta-{post["id_oferta"]}'
                })
            
            # 2. Ofertas antiguas (más de 25 días)
            query_ofertas_antiguas = """
                SELECT 
                    id_oferta, titulo, fecha_publicacion,
                    DATEDIFF(NOW(), fecha_publicacion) as dias_publicada,
                    (SELECT COUNT(*) FROM postulaciones 
                     WHERE id_oferta = ofertas_trabajo.id_oferta 
                     AND estado = 'Pendiente') as pendientes
                FROM ofertas_trabajo
                WHERE id_agricultor = %s
                AND estado = 'Abierta'
                AND DATEDIFF(NOW(), fecha_publicacion) >= 25
                ORDER BY fecha_publicacion DESC
                LIMIT 5
            """
            
            cursor.execute(query_ofertas_antiguas, (user_id,))
            ofertas_antiguas = cursor.fetchall()
            
            for oferta in ofertas_antiguas:
                notif_id = f"oferta_venciendo_{oferta['id_oferta']}"
                notificaciones.append({
                    'id': notif_id,
                    'tipo': 'recordatorio',
                    'titulo': 'Oferta antigua ⏰',
                    'mensaje': f"'{oferta['titulo']}' lleva {oferta['dias_publicada']} días publicada ({oferta['pendientes']} pendientes)",
                    'fecha': str(oferta['fecha_publicacion']),
                    'leida': notif_id in notificaciones_leidas,
                    'url_accion': '/vista/index-agricultor.html'
                })
            
            # 3. Trabajos activos
            query_trabajos_activos = """
                SELECT 
                    a.id_acuerdo, a.fecha_inicio, o.titulo,
                    CONCAT(u.first_name, ' ', u.last_name) as nombre_trabajador,
                    DATEDIFF(NOW(), a.fecha_inicio) as dias_activo
                FROM acuerdos_laborales a
                JOIN ofertas_trabajo o ON o.id_oferta = a.id_oferta
                JOIN usuarios u ON u.id_usuario = a.id_trabajador
                WHERE a.id_agricultor = %s
                AND a.estado = 'Activo'
                ORDER BY a.fecha_inicio DESC
                LIMIT 5
            """
            
            cursor.execute(query_trabajos_activos, (user_id,))
            trabajos_activos = cursor.fetchall()
            
            for trabajo in trabajos_activos:
                notif_id = f"trabajo_activo_{trabajo['id_acuerdo']}"
                notificaciones.append({
                    'id': notif_id,
                    'tipo': 'mensaje',
                    'titulo': 'Trabajo en progreso 🔄',
                    'mensaje': f"{trabajo['nombre_trabajador']} trabajando en '{trabajo['titulo']}' (día {trabajo['dias_activo']})",
                    'fecha': str(trabajo['fecha_inicio']),
                    'leida': notif_id in notificaciones_leidas,
                    'url_accion': '/vista/historial-contrataciones.html'
                })
        
        # Cerrar cursor y conexión
        cursor.close()
        conexion.close()
        
        # Ordenar por fecha (más recientes primero)
        notificaciones.sort(key=lambda x: x['fecha'], reverse=True)
        notificaciones = notificaciones[:30]
        
        # Contar no leídas
        no_leidas = len([n for n in notificaciones if not n['leida']])
        
        print(f"✅ {len(notificaciones)} notificaciones generadas ({no_leidas} no leídas)")
        
        return jsonify({
            'success': True,
            'notificaciones': notificaciones,
            'total': len(notificaciones),
            'no_leidas': no_leidas
        })
        
    except Exception as e:
        print(f"❌ Error generando notificaciones: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@notif_bp.route('/api/notificaciones/<notif_id>/marcar-leida', methods=['PUT'])
def marcar_notificacion_leida(notif_id):
    """Marca una notificación como leída"""
    try:
        if 'notificaciones_leidas' not in session:
            session['notificaciones_leidas'] = []
        
        if notif_id not in session['notificaciones_leidas']:
            session['notificaciones_leidas'].append(notif_id)
            session.modified = True
            print(f"✅ Notificación {notif_id} marcada como leída")
        
        return jsonify({'success': True, 'message': 'Notificación marcada como leída'})
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@notif_bp.route('/api/notificaciones/marcar-todas-leidas', methods=['PUT'])
def marcar_todas_leidas():
    """Marca todas las notificaciones como leídas"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        user_id = session.get('user_id')
        user_role = session.get('user_role', '')
        
        # Obtener conexión
        conexion = get_db_connection()
        if not conexion:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
        
        cursor = conexion.cursor(dictionary=True)
        notif_ids = []
        
        # Generar IDs según el rol
        if user_role == 'Trabajador':
            # Postulaciones
            cursor.execute("""
                SELECT id_postulacion, estado 
                FROM postulaciones 
                WHERE id_trabajador = %s 
                AND estado IN ('Aceptada', 'Rechazada')
                AND fecha_postulacion >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """, (user_id,))
            
            for p in cursor.fetchall():
                notif_ids.append(f"post_{p['estado'].lower()}_{p['id_postulacion']}")
            
            # Ofertas
            cursor.execute("""
                SELECT id_oferta 
                FROM ofertas_trabajo 
                WHERE estado = 'Abierta' 
                AND fecha_publicacion >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            
            for o in cursor.fetchall():
                notif_ids.append(f"nueva_oferta_{o['id_oferta']}")
            
            # Recordatorios
            cursor.execute("""
                SELECT p.id_postulacion
                FROM postulaciones p
                JOIN ofertas_trabajo o ON o.id_oferta = p.id_oferta
                WHERE p.id_trabajador = %s
                AND p.estado = 'Aceptada'
                AND o.estado = 'Abierta'
            """, (user_id,))
            
            for r in cursor.fetchall():
                notif_ids.append(f"recordatorio_{r['id_postulacion']}")
        
        elif user_role == 'Agricultor':
            # Postulaciones
            cursor.execute("""
                SELECT p.id_postulacion
                FROM postulaciones p
                JOIN ofertas_trabajo o ON o.id_oferta = p.id_oferta
                WHERE o.id_agricultor = %s
                AND p.estado = 'Pendiente'
                AND p.fecha_postulacion >= DATE_SUB(NOW(), INTERVAL 3 DAY)
            """, (user_id,))
            
            for p in cursor.fetchall():
                notif_ids.append(f"nueva_postulacion_{p['id_postulacion']}")
            
            # Ofertas antiguas
            cursor.execute("""
                SELECT id_oferta 
                FROM ofertas_trabajo 
                WHERE id_agricultor = %s 
                AND estado = 'Abierta' 
                AND DATEDIFF(NOW(), fecha_publicacion) >= 25
            """, (user_id,))
            
            for o in cursor.fetchall():
                notif_ids.append(f"oferta_venciendo_{o['id_oferta']}")
            
            # Trabajos activos
            cursor.execute("""
                SELECT id_acuerdo 
                FROM acuerdos_laborales 
                WHERE id_agricultor = %s 
                AND estado = 'Activo'
            """, (user_id,))
            
            for t in cursor.fetchall():
                notif_ids.append(f"trabajo_activo_{t['id_acuerdo']}")
        
        cursor.close()
        conexion.close()
        
        # Guardar en sesión
        session['notificaciones_leidas'] = notif_ids
        session.modified = True
        
        print(f"✅ {len(notif_ids)} notificaciones marcadas como leídas")
        
        return jsonify({
            'success': True, 
            'message': f'{len(notif_ids)} notificaciones marcadas como leídas'
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ================================================================
# SISTEMA DE NOTIFICACIONES - ENDPOINTS
# ================================================================

@notif_bp.route('/api/get_notifications', methods=['GET'])
def get_notifications():
    """Genera notificaciones dinámicas basadas en actividad reciente"""
    
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    user_id = session['user_id']
    user_rol = session.get('user_role')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        notificaciones = []
        
        # ====== NOTIFICACIONES PARA TRABAJADORES ======
        if user_rol == 'Trabajador':
            
            # 1. Postulaciones aceptadas (últimos 7 días)
            query_aceptadas = """
                SELECT 
                    p.ID_Postulacion,
                    p.Fecha_Postulacion,
                    o.Titulo as titulo_trabajo,
                    CONCAT(u.Nombre, ' ', u.Apellido) as nombre_agricultor
                FROM Postulacion p
                JOIN Oferta_Trabajo o ON p.ID_Oferta = o.ID_Oferta
                JOIN Usuario u ON o.ID_Agricultor = u.ID_Usuario
                WHERE p.ID_Trabajador = %s
                AND p.Estado = 'Aceptada'
                AND p.Fecha_Postulacion >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                ORDER BY p.Fecha_Postulacion DESC
                LIMIT 5
            """
            cursor.execute(query_aceptadas, (user_id,))
            aceptadas = cursor.fetchall()
            
            for item in aceptadas:
                notificaciones.append({
                    'id': f"postulacion_{item['ID_Postulacion']}",
                    'tipo': 'aceptada',
                    'titulo': '✅ Postulación Aceptada',
                    'mensaje': f"Tu postulación para '{item['titulo_trabajo']}' fue aceptada por {item['nombre_agricultor']}",
                    'fecha': item['Fecha_Postulacion'].isoformat() if item['Fecha_Postulacion'] else None,
                    'icono': 'fa-check-circle',
                    'color': '#28a745',
                    'leida': False
                })
            
            # 2. Postulaciones rechazadas (últimos 7 días)
            query_rechazadas = """
                SELECT 
                    p.ID_Postulacion,
                    p.Fecha_Postulacion,
                    o.Titulo as titulo_trabajo
                FROM Postulacion p
                JOIN Oferta_Trabajo o ON p.ID_Oferta = o.ID_Oferta
                WHERE p.ID_Trabajador = %s
                AND p.Estado = 'Rechazada'
                AND p.Fecha_Postulacion >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                ORDER BY p.Fecha_Postulacion DESC
                LIMIT 3
            """
            cursor.execute(query_rechazadas, (user_id,))
            rechazadas = cursor.fetchall()
            
            for item in rechazadas:
                notificaciones.append({
                    'id': f"rechazo_{item['ID_Postulacion']}",
                    'tipo': 'rechazada',
                    'titulo': '❌ Postulación Rechazada',
                    'mensaje': f"Tu postulación para '{item['titulo_trabajo']}' no fue aceptada",
                    'fecha': item['Fecha_Postulacion'].isoformat() if item['Fecha_Postulacion'] else None,
                    'icono': 'fa-times-circle',
                    'color': '#dc3545',
                    'leida': False
                })
            
            # 3. Nuevas ofertas recomendadas (últimas 3)
            query_nuevas_ofertas = """
                SELECT 
                    o.ID_Oferta,
                    o.Titulo,
                    o.Pago_Ofrecido,
                    o.Fecha_Publicacion,
                    CONCAT(u.Nombre, ' ', u.Apellido) as nombre_agricultor
                FROM Oferta_Trabajo o
                JOIN Usuario u ON o.ID_Agricultor = u.ID_Usuario
                WHERE o.Estado = 'Abierta'
                AND o.Fecha_Publicacion >= DATE_SUB(NOW(), INTERVAL 3 DAY)
                AND NOT EXISTS (
                    SELECT 1 FROM Postulacion p 
                    WHERE p.ID_Oferta = o.ID_Oferta 
                    AND p.ID_Trabajador = %s
                )
                ORDER BY o.Fecha_Publicacion DESC
                LIMIT 3
            """
            cursor.execute(query_nuevas_ofertas, (user_id,))
            nuevas_ofertas = cursor.fetchall()
            
            for oferta in nuevas_ofertas:
                notificaciones.append({
                    'id': f"nueva_oferta_{oferta['ID_Oferta']}",
                    'tipo': 'nueva_oferta',
                    'titulo': '💼 Nuevo Trabajo Disponible',
                    'mensaje': f"Nueva oferta: '{oferta['Titulo']}' - ${oferta['Pago_Ofrecido']:,.0f}/día",
                    'fecha': oferta['Fecha_Publicacion'].isoformat() if oferta['Fecha_Publicacion'] else None,
                    'icono': 'fa-briefcase',
                    'color': '#007bff',
                    'leida': False,
                    'link': f"/vista/index-trabajador.html?highlight={oferta['ID_Oferta']}"
                })
            
            # 4. Recordatorio de calificaciones pendientes
            query_calificaciones_pendientes = """
                SELECT COUNT(*) as pendientes
                FROM Acuerdo_Laboral al
                WHERE al.ID_Trabajador = %s
                AND al.Estado = 'Finalizado'
                AND NOT EXISTS (
                    SELECT 1 FROM Calificacion c 
                    WHERE c.ID_Acuerdo = al.ID_Acuerdo 
                    AND c.ID_Usuario_Emisor = %s
                )
            """
            cursor.execute(query_calificaciones_pendientes, (user_id, user_id))
            pendientes = cursor.fetchone()
            
            if pendientes and pendientes['pendientes'] > 0:
                notificaciones.append({
                    'id': 'calificaciones_pendientes',
                    'tipo': 'recordatorio',
                    'titulo': '⭐ Calificaciones Pendientes',
                    'mensaje': f"Tienes {pendientes['pendientes']} {'empleador' if pendientes['pendientes'] == 1 else 'empleadores'} por calificar",
                    'fecha': datetime.now().isoformat(),
                    'icono': 'fa-star',
                    'color': '#ffc107',
                    'leida': False,
                    'link': '/vista/perfil-trabajador.html?tab=ratings'
                })
        
        # ====== NOTIFICACIONES PARA AGRICULTORES ======
        elif user_rol == 'Agricultor':
            
            # 1. Nuevas postulaciones (últimos 7 días)
            query_nuevas_postulaciones = """
                SELECT 
                    p.ID_Postulacion,
                    p.Fecha_Postulacion,
                    o.Titulo as titulo_trabajo,
                    CONCAT(u.Nombre, ' ', u.Apellido) as nombre_trabajador
                FROM Postulacion p
                JOIN Oferta_Trabajo o ON p.ID_Oferta = o.ID_Oferta
                JOIN Usuario u ON p.ID_Trabajador = u.ID_Usuario
                WHERE o.ID_Agricultor = %s
                AND p.Estado = 'Pendiente'
                AND p.Fecha_Postulacion >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                ORDER BY p.Fecha_Postulacion DESC
                LIMIT 5
            """
            cursor.execute(query_nuevas_postulaciones, (user_id,))
            nuevas_postulaciones = cursor.fetchall()
            
            for item in nuevas_postulaciones:
                notificaciones.append({
                    'id': f"nueva_postulacion_{item['ID_Postulacion']}",
                    'tipo': 'nueva_postulacion',
                    'titulo': '👤 Nueva Postulación',
                    'mensaje': f"{item['nombre_trabajador']} se postuló a '{item['titulo_trabajo']}'",
                    'fecha': item['Fecha_Postulacion'].isoformat() if item['Fecha_Postulacion'] else None,
                    'icono': 'fa-user-plus',
                    'color': '#17a2b8',
                    'leida': False,
                    'link': f"/vista/postulaciones-agricultor.html?oferta={item['ID_Postulacion']}"
                })
            
            # 2. Ofertas próximas a cerrar
            query_ofertas_cerrar = """
                SELECT 
                    o.ID_Oferta,
                    o.Titulo,
                    o.Fecha_Publicacion,
                    DATEDIFF(DATE_ADD(o.Fecha_Publicacion, INTERVAL 30 DAY), NOW()) as dias_restantes
                FROM Oferta_Trabajo o
                WHERE o.ID_Agricultor = %s
                AND o.Estado = 'Abierta'
                AND DATEDIFF(DATE_ADD(o.Fecha_Publicacion, INTERVAL 30 DAY), NOW()) <= 3
                AND DATEDIFF(DATE_ADD(o.Fecha_Publicacion, INTERVAL 30 DAY), NOW()) > 0
                ORDER BY dias_restantes ASC
                LIMIT 3
            """
            cursor.execute(query_ofertas_cerrar, (user_id,))
            ofertas_cerrar = cursor.fetchall()
            
            for oferta in ofertas_cerrar:
                notificaciones.append({
                    'id': f"oferta_cerrar_{oferta['ID_Oferta']}",
                    'tipo': 'recordatorio',
                    'titulo': '⏰ Oferta por Vencer',
                    'mensaje': f"'{oferta['Titulo']}' vence en {oferta['dias_restantes']} {'día' if oferta['dias_restantes'] == 1 else 'días'}",
                    'fecha': datetime.now().isoformat(),
                    'icono': 'fa-clock',
                    'color': '#fd7e14',
                    'leida': False
                })
        
        cursor.close()
        conn.close()
        
        # Ordenar por fecha (más recientes primero)
        notificaciones.sort(key=lambda x: x.get('fecha', ''), reverse=True)
        
        # Limitar a 10 notificaciones
        notificaciones = notificaciones[:10]
        
        return jsonify({
            'success': True,
            'notificaciones': notificaciones,
            'total': len(notificaciones),
            'no_leidas': len([n for n in notificaciones if not n.get('leida', True)])
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo notificaciones: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@notif_bp.route('/api/mark_notification_read', methods=['POST'])
def mark_notification_read():
    """Marca una notificación como leída (opcional, para futuro)"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    data = request.get_json()
    notification_id = data.get('notification_id')
    
    # Por ahora solo retornamos éxito
    # En el futuro podrías guardar las notificaciones leídas en una tabla
    
    return jsonify({
        'success': True,
        'message': 'Notificación marcada como leída'
    })


print("✅ Endpoints de calificaciones y notificaciones cargados correctamente")


# ================================================================.
# INICIO DEL SERVIDOR   
# ================================================================
if __name__ == '__main__':
    print("=" * 70)
    print("🌱 INICIANDO SERVIDOR CAMP - VERSIÓN DASHBOARD SEPARADO")
    print("=" * 70)
    
    # Verificar estructura de archivos al inicio
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"📁 Directorio base: {base_dir}")
        
        # Verificar carpetas importantes
        folders_to_check = ['../vista', '../assent/css', '../js', '../img']
        
        for folder in folders_to_check:
            folder_path = os.path.join(base_dir, folder)
            folder_path = os.path.abspath(folder_path)
            
            if os.path.exists(folder_path):
                files_count = len(os.listdir(folder_path))
                print(f"✅ {folder}: {folder_path} ({files_count} archivos)")
            else:
                print(f"❌ {folder}: {folder_path} (NO EXISTE)")
        
        # Verificar específicamente los archivos del dashboard
        print("\n📊 Verificando archivos del dashboard:")
        dashboard_files = {
            'HTML': '../vista/dashboard-agricultor.html',
            'CSS': '../vista/styles.css',
            'JS': '../vista/script.js'
        }
        
        for file_type, file_path in dashboard_files.items():
            full_path = os.path.join(base_dir, file_path)
            full_path = os.path.abspath(full_path)
            
            if os.path.exists(full_path):
                print(f"✅ {file_type}: {full_path}")
            else:
                print(f"❌ {file_type}: {full_path} (NO EXISTE)")
        
    except Exception as e:
        print(f"⚠️ Error verificando estructura: {e}")
    
    print("\n" + "=" * 70)
    print("📍 URLs principales:")
    print("🧪 http://localhost:5000/test")
    print("🔍 http://localhost:5000/check_files")
    print("🔐 http://localhost:5000/check_session")
    print("✅ http://localhost:5000/validate_session")
    print("👤 http://localhost:5000/get_user_session")
    print("🏠 http://localhost:5000/")
    print("👷 http://localhost:5000/vista/login-trabajador.html")
    print("🌾 http://localhost:5000/vista/login-trabajador.html")
    print("📝 http://localhost:5000/vista/registro-trabajador.html")
    print("📝 http://localhost:5000/vista/registro-agricultor.html")
    print("\n🎯 NUEVO DASHBOARD SEPARADO:")
    print("🌱 http://localhost:5000/vista/dashboard-agricultor.html")
    print("📄 http://localhost:5000/styles.css")
    print("⚙️ http://localhost:5000/script.js")
    print("👷 http://localhost:5000/vista/index-trabajador.html")
    print("📄 http://localhost:5000/index-trabajador.css")
    print("⚙️ http://localhost:5000/index-trabajador.js")
    print("=" * 70)
    print("🔧 Funcionalidades del dashboard:")
    print("• Archivos HTML, CSS y JS separados")
    print("• Menú de usuario completo con dropdown")
    print("• Modal de confirmación para logout")
    print("• Integración completa con backend Python")
    print("• Validación de sesiones en tiempo real")
    print("• Responsive design")
    print("=" * 70)
    print("💡 Para probar:")
    print("1. Registra un usuario como 'Agricultor'")
    print("2. Inicia sesión")
    print("3. Accede al dashboard del agricultor")
    print("4. Prueba el menú de usuario (clic en avatar)")
    print("5. Prueba el logout con confirmación")
    print("=" * 70)
    
