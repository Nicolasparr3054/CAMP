# Blueprint: contratos
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

contratos_bp = Blueprint('contratos', __name__)
from blueprints.helpers import require_login, require_role, hash_password, verify_password, no_cache


# 2. Endpoint para obtener empleadores disponibles para calificar
@contratos_bp.route('/api/user-employers', methods=['GET'])
@require_login
def get_user_employers():
    try:
        user_id = session['user_id']
        
        # Obtener agricultores con los que ha trabajado
        empleadores = execute_query("""
            SELECT DISTINCT u.ID_Usuario, u.Nombre, u.Apellido, u.Correo
            FROM Usuario u
            INNER JOIN Oferta_Trabajo ot ON u.ID_Usuario = ot.ID_Agricultor
            INNER JOIN Acuerdo_Laboral al ON ot.ID_Oferta = al.ID_Oferta
            WHERE al.ID_Trabajador = %s 
            AND al.Estado = 'Finalizado'
            AND u.Rol = 'Agricultor'
            ORDER BY u.Nombre, u.Apellido
        """, (user_id,))
        
        employers_list = []
        if empleadores:
            for emp in empleadores:
                employers_list.append({
                    'id': emp['ID_Usuario'],
                    'nombre': f"{emp['Nombre']} {emp['Apellido']}",
                    'empresa': emp['Nombre'],
                    'email': emp['Correo']
                })
        
        return jsonify({
            'success': True,
            'employers': employers_list
        })
        
    except Exception as e:
        print(f"Error al obtener empleadores: {e}")
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500


# 3. Endpoint para enviar calificación
@contratos_bp.route('/api/submit-rating', methods=['POST'])
@require_login
def submit_rating():
    try:
        data = request.get_json()
        user_id = session['user_id']
        employer_id = data.get('employerId')
        rating = data.get('rating')
        comment = data.get('comment')
        
        # Validar datos
        if not employer_id or not rating or not comment:
            return jsonify({'success': False, 'message': 'Todos los campos son requeridos'})
        
        if not (1 <= int(rating) <= 5):
            return jsonify({'success': False, 'message': 'La calificación debe ser entre 1 y 5'})
        
        # Buscar acuerdo laboral finalizado
        acuerdo = execute_query("""
            SELECT al.ID_Acuerdo
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            WHERE al.ID_Trabajador = %s 
            AND ot.ID_Agricultor = %s
            AND al.Estado = 'Finalizado'
            ORDER BY al.ID_Acuerdo DESC
            LIMIT 1
        """, (user_id, employer_id), fetch_one=True)
        
        if not acuerdo:
            return jsonify({'success': False, 'message': 'No se encontró un trabajo finalizado con este empleador'})
        
        # Verificar que no haya calificado ya
        existing = execute_query("""
            SELECT ID_Calificacion FROM Calificacion 
            WHERE ID_Usuario_Emisor = %s AND ID_Usuario_Receptor = %s AND ID_Acuerdo = %s
        """, (user_id, employer_id, acuerdo['ID_Acuerdo']), fetch_one=True)
        
        if existing:
            return jsonify({'success': False, 'message': 'Ya has calificado a este empleador'})
        
        # Insertar calificación
        execute_query("""
            INSERT INTO Calificacion 
            (ID_Acuerdo, ID_Usuario_Emisor, ID_Usuario_Receptor, Puntuacion, Comentario)
            VALUES (%s, %s, %s, %s, %s)
        """, (acuerdo['ID_Acuerdo'], user_id, employer_id, str(rating), comment))
        
        return jsonify({'success': True, 'message': 'Calificación enviada correctamente'})
        
    except Exception as e:
        print(f"Error al enviar calificación: {e}")
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500


# 4. Endpoint para obtener calificaciones enviadas
@contratos_bp.route('/api/user-ratings', methods=['GET'])
@require_login
def get_user_ratings():
    try:
        user_id = session['user_id']
        
        calificaciones = execute_query("""
            SELECT c.Puntuacion, c.Comentario, c.Fecha,
                   u.Nombre, u.Apellido
            FROM Calificacion c
            INNER JOIN Usuario u ON c.ID_Usuario_Receptor = u.ID_Usuario
            WHERE c.ID_Usuario_Emisor = %s
            ORDER BY c.Fecha DESC
        """, (user_id,))
        
        ratings_list = []
        if calificaciones:
            for rating in calificaciones:
                ratings_list.append({
                    'calificacion': int(rating['Puntuacion']),
                    'comentario': rating['Comentario'],
                    'fecha': rating['Fecha'].strftime('%Y-%m-%d %H:%M:%S') if rating['Fecha'] else None,
                    'empleador_nombre': f"{rating['Nombre']} {rating['Apellido']}",
                    'empresa': rating['Nombre']
                })
        
        return jsonify({
            'success': True,
            'ratings': ratings_list
        })
        
    except Exception as e:
        print(f"Error al obtener calificaciones: {e}")
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500


@contratos_bp.route('/vista/historial-empleos.html')
def historial_empleos_html():
    """Página de historial de empleos"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vista_path = os.path.join(base_dir, '..', '..', 'vista')
        vista_path = os.path.abspath(vista_path)
        return send_from_directory(vista_path, 'historial-empleos.html')
    except Exception as e:
        print(f"Error sirviendo historial-empleos.html: {e}")
        return "Archivo no encontrado", 404


@contratos_bp.route('/assent/css/historial-empleos.css')
def historial_empleos_css():
    """CSS para página de historial de empleos"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        css_path = os.path.join(base_dir, '..', '..', 'assent', 'css')
        css_path = os.path.abspath(css_path)
        response = send_from_directory(css_path, 'historial-empleos.css')
        response.headers['Content-Type'] = 'text/css'
        return response
    except Exception as e:
        print(f"Error sirviendo historial-empleos.css: {e}")
        return "CSS no encontrado", 404


@contratos_bp.route('/js/historial-empleos.js')
def historial_empleos_js():
    """JavaScript para página de historial de empleos"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        js_path = os.path.join(base_dir, '..', '..', 'js')
        js_path = os.path.abspath(js_path)
        response = send_from_directory(js_path, 'historial-empleos.js')
        response.headers['Content-Type'] = 'application/javascript'
        return response
    except Exception as e:
        print(f"Error sirviendo historial-empleos.js: {e}")
        return "JS no encontrado", 404


@contratos_bp.route('/api/historial-empleos', methods=['GET'])
@require_login
def get_historial_empleos():
    """API para obtener historial de empleos del trabajador"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role')
        
        if user_role != 'Trabajador':
            return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
        
        # Consulta para obtener historial de empleos
        empleos = execute_query("""
            SELECT 
                al.ID_Acuerdo,
                ot.Titulo,
                CONCAT(u.Nombre, ' ', u.Apellido) as Empleador,
                u.ID_Usuario as Empleador_ID,
                al.Fecha_Inicio,
                al.Fecha_Fin,
                al.Pago_Final,
                al.Estado,
                ot.Descripcion,
                c.Puntuacion,
                c.Comentario,
                ot.Pago_Ofrecido,
                p.Nombre_Finca as Ubicacion
            FROM Acuerdo_Laboral al
            JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
            LEFT JOIN Predio p ON u.ID_Usuario = p.ID_Usuario
            LEFT JOIN Calificacion c ON al.ID_Acuerdo = c.ID_Acuerdo AND c.ID_Usuario_Receptor = %s
            WHERE al.ID_Trabajador = %s
            ORDER BY al.Fecha_Inicio DESC
        """, (user_id, user_id))
        
        empleos_list = []
        if empleos:
            for empleo in empleos:
                # Calcular duración
                if empleo['Fecha_Fin']:
                    duracion_dias = (empleo['Fecha_Fin'] - empleo['Fecha_Inicio']).days + 1
                    duracion = f"{duracion_dias} días"
                else:
                    duracion = "En curso"
                
                # Determinar tipo de trabajo
                descripcion = empleo['Descripcion'].lower()
                if 'cosecha' in descripcion or 'recolección' in descripcion:
                    tipo = 'Cosecha'
                elif 'siembra' in descripcion:
                    tipo = 'Siembra'
                elif 'mantenimiento' in descripcion or 'poda' in descripcion:
                    tipo = 'Mantenimiento'
                else:
                    tipo = 'Otro'
                
                empleo_data = {
                    'id': empleo['ID_Acuerdo'],
                    'titulo': empleo['Titulo'],
                    'empleador': empleo['Empleador'],
                    'empleadorId': empleo['Empleador_ID'],
                    'fechaInicio': empleo['Fecha_Inicio'].strftime('%Y-%m-%d') if empleo['Fecha_Inicio'] else None,
                    'fechaFin': empleo['Fecha_Fin'].strftime('%Y-%m-%d') if empleo['Fecha_Fin'] else None,
                    'duracion': duracion,
                    'estado': empleo['Estado'],
                    'pago': float(empleo['Pago_Final']) if empleo['Pago_Final'] else float(empleo['Pago_Ofrecido']),
                    'ubicacion': empleo['Ubicacion'] if empleo['Ubicacion'] else 'Colombia',
                    'calificacion': empleo['Puntuacion'],
                    'comentario': empleo['Comentario'],
                    'descripcion': empleo['Descripcion'],
                    'tipo': tipo
                }
                empleos_list.append(empleo_data)
        
        return jsonify({
            'success': True,
            'empleos': empleos_list
        })
        
    except Exception as e:
        print(f"Error obteniendo historial: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# RUTAS PARA HISTORIAL DE EMPLEOS (TRABAJADOR)
# ============================================================

@contratos_bp.route('/api/historial_empleos_trabajador', methods=['GET'])
def historial_empleos_trabajador():
    """Obtener historial de empleos de un trabajador"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'}), 401
    
    trabajador_id = session['user_id']
    
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT 
                    al.ID_Acuerdo as id,
                    ot.Titulo as titulo,
                    ot.Descripcion as descripcion,
                    CONCAT(u.Nombre, ' ', u.Apellido) as empleador,
                    al.Fecha_Inicio as fecha_inicio,
                    al.Fecha_Fin as fecha_fin,
                    al.Pago_Final as pago,
                    al.Estado as estado,
                    'Colombia' as ubicacion,
                    CASE 
                        WHEN LOWER(ot.Titulo) LIKE '%cosecha%' THEN 'Cosecha'
                        WHEN LOWER(ot.Titulo) LIKE '%siembra%' THEN 'Siembra'
                        WHEN LOWER(ot.Titulo) LIKE '%mantenimiento%' THEN 'Mantenimiento'
                        WHEN LOWER(ot.Titulo) LIKE '%recolección%' OR LOWER(ot.Titulo) LIKE '%recoleccion%' THEN 'Recolección'
                        ELSE 'Otro'
                    END as tipo,
                    c.Puntuacion as calificacion,
                    c.Comentario as comentario
                FROM 
                    Acuerdo_Laboral al
                INNER JOIN 
                    Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
                INNER JOIN 
                    Usuario u ON ot.ID_Agricultor = u.ID_Usuario
                LEFT JOIN 
                    Calificacion c ON al.ID_Acuerdo = c.ID_Acuerdo 
                    AND c.ID_Usuario_Receptor = al.ID_Trabajador
                WHERE 
                    al.ID_Trabajador = %s
                ORDER BY 
                    al.Fecha_Inicio DESC
            """
            
            cursor.execute(query, (trabajador_id,))
            resultados = cursor.fetchall()
            
            empleos = []
            for row in resultados:
                if row['fecha_fin']:
                    duracion_dias = (row['fecha_fin'] - row['fecha_inicio']).days
                    duracion = f"{duracion_dias} día{'s' if duracion_dias > 1 else ''}"
                else:
                    duracion = "En curso"
                
                empleo = {
                    'id': row['id'],
                    'titulo': row['titulo'],
                    'descripcion': row['descripcion'] if row['descripcion'] else 'Sin descripción',
                    'empleador': row['empleador'],
                    'fecha_inicio': row['fecha_inicio'].strftime('%Y-%m-%d') if row['fecha_inicio'] else None,
                    'fecha_fin': row['fecha_fin'].strftime('%Y-%m-%d') if row['fecha_fin'] else None,
                    'pago': float(row['pago']) if row['pago'] else 0,
                    'estado': row['estado'],
                    'ubicacion': row['ubicacion'],
                    'tipo': row['tipo'],
                    'duracion': duracion,
                    'calificacion': int(row['calificacion']) if row['calificacion'] else None,
                    'comentario': row['comentario'] if row['comentario'] else None
                }
                empleos.append(empleo)
            
            cursor.close()
        
        return jsonify({
            'success': True,
            'empleos': empleos,
            'total': len(empleos)
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# RUTAS PARA HISTORIAL DE CONTRATACIONES (AGRICULTOR)
# ============================================================

@contratos_bp.route('/api/historial_contrataciones_agricultor', methods=['GET'])
def historial_contrataciones_agricultor():
    """Historial de contrataciones para agricultores con datos de calificación"""
    try:
        agricultor_id = session.get('user_id')
        if not agricultor_id:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        user_role = session.get('user_role', session.get('role'))
        if user_role != 'Agricultor':
            return jsonify({'success': False, 'message': 'Solo agricultores'}), 403
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                a.ID_Acuerdo as id,
                a.ID_Acuerdo as id_acuerdo,
                a.ID_Trabajador as id_trabajador,
                CONCAT(t.Nombre, ' ', t.Apellido) as nombre_trabajador,
                t.Correo as email_trabajador,
                t.Telefono as telefono_trabajador,
                t.URL_Foto as foto_trabajador,
                o.Titulo as titulo_oferta,
                o.ID_Oferta as id_oferta,
                a.Fecha_Inicio as fecha_inicio,
                a.Fecha_Fin as fecha_fin,
                a.Pago_Final as pago_final,
                a.Estado as estado,
                DATEDIFF(COALESCE(a.Fecha_Fin, NOW()), a.Fecha_Inicio) as duracion_dias,
                c.Puntuacion as calificacion_dada,
                c.Comentario as comentario_calificacion,
                -- Calificación promedio del trabajador (para referencia)
                (SELECT AVG(CAST(c2.Puntuacion AS UNSIGNED)) 
                 FROM Calificacion c2 
                 WHERE c2.ID_Usuario_Receptor = t.ID_Usuario) as calificacion_trabajador,
                -- Total de trabajos completados por el trabajador
                (SELECT COUNT(*) 
                 FROM Acuerdo_Laboral al2 
                 WHERE al2.ID_Trabajador = t.ID_Usuario 
                 AND al2.Estado = 'Finalizado') as trabajos_completados
            FROM Acuerdo_Laboral a
            INNER JOIN Oferta_Trabajo o ON a.ID_Oferta = o.ID_Oferta
            INNER JOIN Usuario t ON a.ID_Trabajador = t.ID_Usuario
            LEFT JOIN Calificacion c ON a.ID_Acuerdo = c.ID_Acuerdo 
                AND c.ID_Usuario_Emisor = %s
            WHERE o.ID_Agricultor = %s
            ORDER BY a.Fecha_Inicio DESC
        """
        
        cursor.execute(query, (agricultor_id, agricultor_id))
        contrataciones = cursor.fetchall()
        
        # Formatear datos
        contrataciones_formateadas = []
        for cont in contrataciones:
            # Calcular duración legible
            dias = cont['duracion_dias'] or 0
            if dias == 0:
                duracion = "Menos de 1 día"
            elif dias == 1:
                duracion = "1 día"
            else:
                duracion = f"{dias} días"
            
            # Estado legible
            estado_map = {
                'Activo': 'En curso',
                'Finalizado': 'Completado',
                'Cancelado': 'Cancelado'
            }
            estado = estado_map.get(cont['estado'], cont['estado'])
            
            cont_data = {
                'id': cont['id'],
                'id_acuerdo': cont['id_acuerdo'],
                'id_trabajador': cont['id_trabajador'],
                'nombre_trabajador': cont['nombre_trabajador'],
                'email_trabajador': cont['email_trabajador'],
                'telefono_trabajador': cont['telefono_trabajador'] or 'No disponible',
                'foto_trabajador': cont['foto_trabajador'],
                'titulo_oferta': cont['titulo_oferta'],
                'id_oferta': cont['id_oferta'],
                'fecha_inicio': cont['fecha_inicio'].strftime('%Y-%m-%d') if cont['fecha_inicio'] else None,
                'fecha_fin': cont['fecha_fin'].strftime('%Y-%m-%d') if cont['fecha_fin'] else None,
                'duracion': duracion,
                'pago_final': float(cont['pago_final']) if cont['pago_final'] else 0,
                'estado': estado,
                'calificacion_dada': int(cont['calificacion_dada']) if cont['calificacion_dada'] else None,
                'comentario_calificacion': cont['comentario_calificacion'],
                # Datos adicionales del trabajador
                'calificacion_trabajador': round(float(cont['calificacion_trabajador']), 1) if cont['calificacion_trabajador'] else 0.0,
                'trabajos_completados': cont['trabajos_completados'] or 0
            }
            contrataciones_formateadas.append(cont_data)
        
        cursor.close()
        conn.close()
        
        print(f"✅ Historial contrataciones: {len(contrataciones_formateadas)} para agricultor {agricultor_id}")
        
        return jsonify({
            'success': True,
            'contrataciones': contrataciones_formateadas,
            'total': len(contrataciones_formateadas)
        })
        
    except Exception as e:
        print(f"❌ Error en historial_contrataciones_agricultor: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


print("✅ Endpoint de historial de contrataciones actualizado con datos de calificación")


# ============================================================
# RUTA AUXILIAR: OBTENER ESTADÍSTICAS DEL TRABAJADOR
# ============================================================

@contratos_bp.route('/api/historial_stats_trabajador', methods=['GET'])
def historial_stats_trabajador():
    """Obtener estadísticas detalladas del trabajador para historial"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'}), 401
    
    trabajador_id = session['user_id']
    
    try:
        cursor = mysql.connection.cursor()
        
        # Trabajos completados
        cursor.execute("""
            SELECT COUNT(*) 
            FROM Acuerdo_Laboral 
            WHERE ID_Trabajador = %s AND Estado = 'Finalizado'
        """, (trabajador_id,))
        trabajos_completados = cursor.fetchone()[0]
        
        # Horas trabajadas (estimado)
        cursor.execute("""
            SELECT COALESCE(SUM(DATEDIFF(Fecha_Fin, Fecha_Inicio) * 8), 0)
            FROM Acuerdo_Laboral
            WHERE ID_Trabajador = %s AND Estado = 'Finalizado'
        """, (trabajador_id,))
        horas_trabajadas = cursor.fetchone()[0]
        
        # Calificación promedio
        cursor.execute("""
            SELECT COALESCE(AVG(CAST(Puntuacion AS DECIMAL)), 0)
            FROM Calificacion
            WHERE ID_Usuario_Receptor = %s
        """, (trabajador_id,))
        calificacion_promedio = float(cursor.fetchone()[0])
        
        # Ingresos totales
        cursor.execute("""
            SELECT COALESCE(SUM(Pago_Final), 0)
            FROM Acuerdo_Laboral
            WHERE ID_Trabajador = %s AND Estado = 'Finalizado'
        """, (trabajador_id,))
        ingresos_totales = float(cursor.fetchone()[0])
        
        cursor.close()
        
        return jsonify({
            'success': True,
            'estadisticas': {
                'trabajos_completados': trabajos_completados,
                'horas_trabajadas': horas_trabajadas,
                'calificacion_promedio': round(calificacion_promedio, 1),
                'ingresos_totales': ingresos_totales
            }
        })
        
    except Exception as e:
        print(f"Error en historial_stats_trabajador: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ============================================================
# RUTA AUXILIAR: OBTENER ESTADÍSTICAS DEL AGRICULTOR
# ============================================================

@contratos_bp.route('/api/historial_stats_agricultor', methods=['GET'])
def historial_stats_agricultor():
    """Obtener estadísticas detalladas del agricultor para historial"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'}), 401
    
    agricultor_id = session['user_id']
    
    try:
        cursor = mysql.connection.cursor()
        
        # Total de contrataciones
        cursor.execute("""
            SELECT COUNT(DISTINCT al.ID_Acuerdo)
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            WHERE ot.ID_Agricultor = %s
        """, (agricultor_id,))
        total_contrataciones = cursor.fetchone()[0]
        
        # Contrataciones activas
        cursor.execute("""
            SELECT COUNT(DISTINCT al.ID_Acuerdo)
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            WHERE ot.ID_Agricultor = %s AND al.Estado = 'Activo'
        """, (agricultor_id,))
        contrataciones_activas = cursor.fetchone()[0]
        
        # Calificación promedio dada
        cursor.execute("""
            SELECT COALESCE(AVG(CAST(c.Puntuacion AS DECIMAL)), 0)
            FROM Calificacion c
            WHERE c.ID_Usuario_Emisor = %s
        """, (agricultor_id,))
        calificacion_promedio = float(cursor.fetchone()[0])
        
        # Total invertido
        cursor.execute("""
            SELECT COALESCE(SUM(al.Pago_Final), 0)
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            WHERE ot.ID_Agricultor = %s
        """, (agricultor_id,))
        total_invertido = float(cursor.fetchone()[0])
        
        cursor.close()
        
        return jsonify({
            'success': True,
            'estadisticas': {
                'total_contrataciones': total_contrataciones,
                'contrataciones_activas': contrataciones_activas,
                'calificacion_promedio': round(calificacion_promedio, 1),
                'total_invertido': total_invertido
            }
        })
        
    except Exception as e:
        print(f"Error en historial_stats_agricultor: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ================================================================
# RUTA PARA FINALIZAR ACUERDO LABORAL
# ================================================================

@contratos_bp.route('/api/finalizar_acuerdo/<int:acuerdo_id>', methods=['PUT'])
def finalizar_acuerdo(acuerdo_id):
    """Finalizar un acuerdo laboral y cerrar oferta si ya no hay acuerdos activos"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'}), 401
    
    try:
        cursor = mysql.connection.cursor()
        
        # Obtener información del acuerdo
        cursor.execute("""
            SELECT al.ID_Oferta, ot.ID_Agricultor, al.Estado
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            WHERE al.ID_Acuerdo = %s
        """, (acuerdo_id,))
        
        acuerdo = cursor.fetchone()
        
        if not acuerdo:
            cursor.close()
            return jsonify({'success': False, 'message': 'Acuerdo no encontrado'}), 404
        
        oferta_id = acuerdo[0]
        agricultor_id = acuerdo[1]
        estado_actual = acuerdo[2]
        
        # Verificar que el agricultor es el dueño
        if agricultor_id != session['user_id']:
            cursor.close()
            return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
        # Verificar que no esté ya finalizado
        if estado_actual == 'Finalizado':
            cursor.close()
            return jsonify({'success': False, 'message': 'El acuerdo ya está finalizado'}), 400
        
        # Finalizar acuerdo
        fecha_fin = datetime.now().date()
        cursor.execute("""
            UPDATE Acuerdo_Laboral 
            SET Estado = 'Finalizado', Fecha_Fin = %s
            WHERE ID_Acuerdo = %s
        """, (fecha_fin, acuerdo_id))
        
        print(f"✅ Acuerdo {acuerdo_id} finalizado")
        
        # Verificar si hay más acuerdos activos para esta oferta
        cursor.execute("""
            SELECT COUNT(*) 
            FROM Acuerdo_Laboral 
            WHERE ID_Oferta = %s AND Estado = 'Activo'
        """, (oferta_id,))
        
        acuerdos_activos = cursor.fetchone()[0]
        
        # Si no hay más acuerdos activos, cerrar la oferta
        if acuerdos_activos == 0:
            cursor.execute("""
                UPDATE Oferta_Trabajo 
                SET Estado = 'Cerrada' 
                WHERE ID_Oferta = %s
            """, (oferta_id,))
            print(f"✅ Oferta {oferta_id} cerrada automáticamente (no hay más acuerdos activos)")
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({
            'success': True, 
            'message': 'Acuerdo finalizado exitosamente',
            'oferta_cerrada': acuerdos_activos == 0
        })
        
    except Exception as e:
        print(f"❌ Error en finalizar_acuerdo: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ================================================================
# RUTA PARA CANCELAR ACUERDO LABORAL
# ================================================================

@contratos_bp.route('/api/cancelar_acuerdo/<int:acuerdo_id>', methods=['PUT'])
def cancelar_acuerdo(acuerdo_id):
    """Cancelar un acuerdo laboral"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'}), 401
    
    data = request.get_json()
    motivo = data.get('motivo', '')
    
    try:
        cursor = mysql.connection.cursor()
        
        # Obtener información del acuerdo
        cursor.execute("""
            SELECT al.ID_Oferta, ot.ID_Agricultor, al.ID_Trabajador, al.Estado
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            WHERE al.ID_Acuerdo = %s
        """, (acuerdo_id,))
        
        acuerdo = cursor.fetchone()
        
        if not acuerdo:
            cursor.close()
            return jsonify({'success': False, 'message': 'Acuerdo no encontrado'}), 404
        
        oferta_id = acuerdo[0]
        agricultor_id = acuerdo[1]
        trabajador_id = acuerdo[2]
        estado_actual = acuerdo[3]
        
        # Verificar autorización (agricultor o trabajador)
        if session['user_id'] not in [agricultor_id, trabajador_id]:
            cursor.close()
            return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
        # Verificar que esté activo
        if estado_actual != 'Activo':
            cursor.close()
            return jsonify({'success': False, 'message': 'Solo se pueden cancelar acuerdos activos'}), 400
        
        # Cancelar acuerdo
        cursor.execute("""
            UPDATE Acuerdo_Laboral 
            SET Estado = 'Cancelado', Fecha_Fin = %s
            WHERE ID_Acuerdo = %s
        """, (datetime.now().date(), acuerdo_id))
        
        print(f"⚠️ Acuerdo {acuerdo_id} cancelado. Motivo: {motivo}")
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({
            'success': True, 
            'message': 'Acuerdo cancelado exitosamente'
        })
        
    except Exception as e:
        print(f"❌ Error en cancelar_acuerdo: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ================================================================
# RUTA PARA OBTENER DETALLES DE UN ACUERDO LABORAL
# ================================================================

@contratos_bp.route('/api/get_acuerdo/<int:acuerdo_id>', methods=['GET'])
def get_acuerdo(acuerdo_id):
    """Obtener detalles de un acuerdo laboral específico"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'}), 401
    
    try:
        cursor = mysql.connection.cursor()
        
        cursor.execute("""
            SELECT 
                al.ID_Acuerdo,
                al.Fecha_Inicio,
                al.Fecha_Fin,
                al.Pago_Final,
                al.Estado,
                ot.Titulo as titulo_oferta,
                ot.Descripcion as descripcion_oferta,
                CONCAT(ut.Nombre, ' ', ut.Apellido) as nombre_trabajador,
                ut.Telefono as telefono_trabajador,
                ut.Correo as email_trabajador,
                CONCAT(ua.Nombre, ' ', ua.Apellido) as nombre_agricultor,
                ua.Telefono as telefono_agricultor,
                c.Puntuacion as calificacion,
                c.Comentario as comentario_calificacion
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            INNER JOIN Usuario ut ON al.ID_Trabajador = ut.ID_Usuario
            INNER JOIN Usuario ua ON ot.ID_Agricultor = ua.ID_Usuario
            LEFT JOIN Calificacion c ON al.ID_Acuerdo = c.ID_Acuerdo
            WHERE al.ID_Acuerdo = %s
        """, (acuerdo_id,))
        
        acuerdo = cursor.fetchone()
        cursor.close()
        
        if not acuerdo:
            return jsonify({'success': False, 'message': 'Acuerdo no encontrado'}), 404
        
        # Calcular duración
        if acuerdo[2]:  # Tiene fecha_fin
            duracion_dias = (acuerdo[2] - acuerdo[1]).days
            duracion = f"{duracion_dias} día{'s' if duracion_dias > 1 else ''}"
        else:
            duracion = "En curso"
        
        resultado = {
            'id': acuerdo[0],
            'fecha_inicio': acuerdo[1].strftime('%Y-%m-%d') if acuerdo[1] else None,
            'fecha_fin': acuerdo[2].strftime('%Y-%m-%d') if acuerdo[2] else None,
            'duracion': duracion,
            'pago_final': float(acuerdo[3]) if acuerdo[3] else 0,
            'estado': acuerdo[4],
            'titulo_oferta': acuerdo[5],
            'descripcion_oferta': acuerdo[6],
            'nombre_trabajador': acuerdo[7],
            'telefono_trabajador': acuerdo[8],
            'email_trabajador': acuerdo[9],
            'nombre_agricultor': acuerdo[10],
            'telefono_agricultor': acuerdo[11],
            'calificacion': int(acuerdo[12]) if acuerdo[12] else None,
            'comentario_calificacion': acuerdo[13] if acuerdo[13] else None
        }
        
        return jsonify({
            'success': True,
            'acuerdo': resultado
        })
        
    except Exception as e:
        print(f"❌ Error en get_acuerdo: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ================================================================
# RUTA PARA ACTUALIZAR PAGO DE UN ACUERDO
# ================================================================

@contratos_bp.route('/api/actualizar_pago_acuerdo/<int:acuerdo_id>', methods=['PUT'])
def actualizar_pago_acuerdo(acuerdo_id):
    """Actualizar el pago final de un acuerdo laboral"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'}), 401
    
    data = request.get_json()
    nuevo_pago = data.get('pago_final')
    
    if not nuevo_pago or float(nuevo_pago) <= 0:
        return jsonify({'success': False, 'message': 'Pago inválido'}), 400
    
    try:
        cursor = mysql.connection.cursor()
        
        # Verificar que el agricultor es el dueño
        cursor.execute("""
            SELECT ot.ID_Agricultor 
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            WHERE al.ID_Acuerdo = %s
        """, (acuerdo_id,))
        
        result = cursor.fetchone()
        
        if not result or result[0] != session['user_id']:
            cursor.close()
            return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
        # Actualizar pago
        cursor.execute("""
            UPDATE Acuerdo_Laboral 
            SET Pago_Final = %s
            WHERE ID_Acuerdo = %s
        """, (nuevo_pago, acuerdo_id))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({
            'success': True,
            'message': 'Pago actualizado exitosamente'
        })
        
    except Exception as e:
        print(f"❌ Error en actualizar_pago_acuerdo: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ================================================================
# ENDPOINTS PARA HISTORIAL DE EMPLEOS (TRABAJADOR)
# Agregar estos endpoints a tu app.py
# ================================================================

@contratos_bp.route('/api/historial_empleos_trabajador', methods=['GET'])
@require_login
def get_historial_empleos_trabajador():
    """Obtener historial completo de empleos del trabajador"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role')
        
        if user_role != 'Trabajador':
            return jsonify({
                'success': False,
                'message': 'Solo los trabajadores pueden ver este historial'
            }), 403
        
        # Consulta para obtener historial de empleos
        empleos = execute_query("""
            SELECT 
                al.ID_Acuerdo as id,
                ot.Titulo as titulo,
                ot.Descripcion as descripcion,
                CONCAT(u.Nombre, ' ', u.Apellido) as empleador,
                u.Correo as email_empleador,
                u.Telefono as telefono_empleador,
                u.ID_Usuario as empleador_id,
                al.Fecha_Inicio as fecha_inicio,
                al.Fecha_Fin as fecha_fin,
                al.Pago_Final as pago,
                al.Estado as estado,
                COALESCE(pr.Nombre_Finca, 'No especificada') as ubicacion,
                c.Puntuacion as calificacion,
                c.Comentario as comentario,
                DATEDIFF(COALESCE(al.Fecha_Fin, CURDATE()), al.Fecha_Inicio) as dias_trabajados
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            INNER JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
            LEFT JOIN Predio pr ON u.ID_Usuario = pr.ID_Usuario
            LEFT JOIN Calificacion c ON al.ID_Acuerdo = c.ID_Acuerdo 
                AND c.ID_Usuario_Receptor = %s
            WHERE al.ID_Trabajador = %s
            ORDER BY al.Fecha_Inicio DESC
        """, (user_id, user_id))
        
        empleos_list = []
        if empleos:
            for empleo in empleos:
                # Determinar tipo de trabajo según descripción
                descripcion_lower = (empleo['descripcion'] or '').lower()
                if 'cosecha' in descripcion_lower or 'recolección' in descripcion_lower:
                    tipo = 'Cosecha'
                elif 'siembra' in descripcion_lower:
                    tipo = 'Siembra'
                elif 'mantenimiento' in descripcion_lower or 'poda' in descripcion_lower:
                    tipo = 'Mantenimiento'
                elif 'recolección' in descripcion_lower:
                    tipo = 'Recolección'
                else:
                    tipo = 'Otro'
                
                # Calcular duración en formato legible
                dias = empleo['dias_trabajados'] or 0
                if dias == 0:
                    duracion = 'Menos de 1 día'
                elif dias == 1:
                    duracion = '1 día'
                else:
                    duracion = f'{dias} días'
                
                # Mapear estado
                estado_map = {
                    'Activo': 'En curso',
                    'Finalizado': 'Completado',
                    'Cancelado': 'Cancelado'
                }
                estado = estado_map.get(empleo['estado'], empleo['estado'])
                
                empleo_data = {
                    'id': empleo['id'],
                    'titulo': empleo['titulo'],
                    'descripcion': empleo['descripcion'],
                    'empleador': empleo['empleador'],
                    'email_empleador': empleo['email_empleador'],
                    'telefono_empleador': empleo['telefono_empleador'],
                    'empleador_id': empleo['empleador_id'],
                    'fecha_inicio': empleo['fecha_inicio'].isoformat() if empleo['fecha_inicio'] else None,
                    'fecha_fin': empleo['fecha_fin'].isoformat() if empleo['fecha_fin'] else None,
                    'duracion': duracion,
                    'pago': float(empleo['pago']) if empleo['pago'] else 0,
                    'ubicacion': empleo['ubicacion'],
                    'estado': estado,
                    'tipo': tipo,
                    'calificacion': int(empleo['calificacion']) if empleo['calificacion'] else None,
                    'comentario': empleo['comentario']
                }
                empleos_list.append(empleo_data)
        
        return jsonify({
            'success': True,
            'empleos': empleos_list,
            'total': len(empleos_list)
        })
        
    except Exception as e:
        print(f"Error obteniendo historial de empleos: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


# ================================================================
# ENDPOINTS PARA HISTORIAL DE CONTRATACIONES (AGRICULTOR)
# ================================================================

@contratos_bp.route('/api/historial_contrataciones_agricultor', methods=['GET'])
@require_login
def get_historial_contrataciones_agricultor():
    """Obtener historial completo de contrataciones del agricultor"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role')
        
        if user_role != 'Agricultor':
            return jsonify({
                'success': False,
                'message': 'Solo los agricultores pueden ver este historial'
            }), 403
        
        # Consulta para obtener historial de contrataciones
        contrataciones = execute_query("""
            SELECT 
                al.ID_Acuerdo as id,
                ot.Titulo as titulo_oferta,
                ot.Descripcion as descripcion_oferta,
                CONCAT(u.Nombre, ' ', u.Apellido) as nombre_trabajador,
                u.Correo as email_trabajador,
                u.Telefono as telefono_trabajador,
                u.URL_Foto as foto_trabajador,
                u.ID_Usuario as trabajador_id,
                al.Fecha_Inicio as fecha_inicio,
                al.Fecha_Fin as fecha_fin,
                al.Pago_Final as pago_final,
                al.Estado as estado,
                c.Puntuacion as calificacion_dada,
                c.Comentario as comentario_calificacion,
                DATEDIFF(COALESCE(al.Fecha_Fin, CURDATE()), al.Fecha_Inicio) as dias_trabajados
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            INNER JOIN Usuario u ON al.ID_Trabajador = u.ID_Usuario
            LEFT JOIN Calificacion c ON al.ID_Acuerdo = c.ID_Acuerdo 
                AND c.ID_Usuario_Emisor = %s
            WHERE ot.ID_Agricultor = %s
            ORDER BY al.Fecha_Inicio DESC
        """, (user_id, user_id))
        
        contrataciones_list = []
        if contrataciones:
            for contratacion in contrataciones:
                # Calcular duración
                dias = contratacion['dias_trabajados'] or 0
                
                # Mapear estado
                estado_map = {
                    'Activo': 'Activo',
                    'Finalizado': 'Finalizado',
                    'Cancelado': 'Cancelado'
                }
                estado = estado_map.get(contratacion['estado'], contratacion['estado'])
                
                contratacion_data = {
                    'id': contratacion['id'],
                    'titulo_oferta': contratacion['titulo_oferta'],
                    'descripcion_oferta': contratacion['descripcion_oferta'],
                    'nombre_trabajador': contratacion['nombre_trabajador'],
                    'email_trabajador': contratacion['email_trabajador'],
                    'telefono_trabajador': contratacion['telefono_trabajador'] or 'No disponible',
                    'foto_trabajador': contratacion['foto_trabajador'],
                    'trabajador_id': contratacion['trabajador_id'],
                    'fecha_inicio': contratacion['fecha_inicio'].isoformat() if contratacion['fecha_inicio'] else None,
                    'fecha_fin': contratacion['fecha_fin'].isoformat() if contratacion['fecha_fin'] else None,
                    'pago_final': float(contratacion['pago_final']) if contratacion['pago_final'] else 0,
                    'estado': estado,
                    'calificacion_dada': int(contratacion['calificacion_dada']) if contratacion['calificacion_dada'] else None,
                    'comentario_calificacion': contratacion['comentario_calificacion']
                }
                contrataciones_list.append(contratacion_data)
        
        return jsonify({
            'success': True,
            'contrataciones': contrataciones_list,
            'total': len(contrataciones_list)
        })
        
    except Exception as e:
        print(f"Error obteniendo historial de contrataciones: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


# ================================================================
# ENDPOINT PARA CALIFICAR TRABAJADOR
# ================================================================

@contratos_bp.route('/api/calificar_trabajador', methods=['POST'])
@require_login
def calificar_trabajador():
    """Calificar a un trabajador después de finalizar un acuerdo laboral"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role')
        
        if user_role != 'Agricultor':
            return jsonify({
                'success': False,
                'message': 'Solo los agricultores pueden calificar trabajadores'
            }), 403
        
        data = request.get_json()
        contratacion_id = data.get('contratacion_id')
        puntuacion = data.get('puntuacion')
        comentario = data.get('comentario', '').strip()
        
        # Validaciones
        if not contratacion_id or not puntuacion:
            return jsonify({
                'success': False,
                'message': 'Contratación y puntuación son requeridas'
            }), 400
        
        try:
            puntuacion = int(puntuacion)
            if not (1 <= puntuacion <= 5):
                raise ValueError()
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'La puntuación debe ser un número entre 1 y 5'
            }), 400
        
        # Verificar que el acuerdo existe y pertenece al agricultor
        acuerdo = execute_query("""
            SELECT 
                al.ID_Acuerdo,
                al.ID_Trabajador,
                al.Estado,
                ot.ID_Agricultor,
                CONCAT(u.Nombre, ' ', u.Apellido) as nombre_trabajador
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            INNER JOIN Usuario u ON al.ID_Trabajador = u.ID_Usuario
            WHERE al.ID_Acuerdo = %s
        """, (contratacion_id,), fetch_one=True)
        
        if not acuerdo:
            return jsonify({
                'success': False,
                'message': 'Contratación no encontrada'
            }), 404
        
        if acuerdo['ID_Agricultor'] != user_id:
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para calificar esta contratación'
            }), 403
        
        if acuerdo['Estado'] != 'Finalizado':
            return jsonify({
                'success': False,
                'message': 'Solo puedes calificar contrataciones finalizadas'
            }), 400
        
        # Verificar que no haya calificado ya
        calificacion_existente = execute_query("""
            SELECT ID_Calificacion 
            FROM Calificacion 
            WHERE ID_Acuerdo = %s 
            AND ID_Usuario_Emisor = %s
        """, (contratacion_id, user_id), fetch_one=True)
        
        if calificacion_existente:
            return jsonify({
                'success': False,
                'message': 'Ya has calificado este trabajo'
            }), 400
        
        # Insertar calificación
        execute_query("""
            INSERT INTO Calificacion 
            (ID_Acuerdo, ID_Usuario_Emisor, ID_Usuario_Receptor, Puntuacion, Comentario, Fecha)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (
            contratacion_id,
            user_id,
            acuerdo['ID_Trabajador'],
            str(puntuacion),
            comentario if comentario else None
        ))
        
        print(f"Calificación registrada: {user_id} calificó a {acuerdo['ID_Trabajador']} con {puntuacion} estrellas")
        
        return jsonify({
            'success': True,
            'message': f'Calificación enviada exitosamente a {acuerdo["nombre_trabajador"]}'
        })
        
    except Exception as e:
        print(f"Error calificando trabajador: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


# ================================================================
# RUTAS PARA SERVIR ARCHIVOS HTML
# ================================================================

@contratos_bp.route('/vista/historial-empleos.html')
def historial_empleos_page():
    """Servir página de historial de empleos"""
    try:
        if 'user_id' not in session:
            return redirect('/vista/login-trabajador.html')
        
        if session.get('user_role') != 'Trabajador':
            return redirect('/vista/index-agricultor.html')
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vista_path = os.path.join(base_dir, '..', '..', 'vista')
        vista_path = os.path.abspath(vista_path)
        return send_from_directory(vista_path, 'historial-empleos.html')
    except Exception as e:
        print(f"Error sirviendo historial-empleos.html: {e}")
        return "Archivo no encontrado", 404


@contratos_bp.route('/vista/historial-contrataciones.html')
def historial_contrataciones_page():
    """Servir página de historial de contrataciones"""
    try:
        if 'user_id' not in session:
            return redirect('/vista/login-trabajador.html')
        
        if session.get('user_role') != 'Agricultor':
            return redirect('/vista/index-trabajador.html')
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vista_path = os.path.join(base_dir, '..', '..', 'vista')
        vista_path = os.path.abspath(vista_path)
        return send_from_directory(vista_path, 'historial-contrataciones.html')
    except Exception as e:
        print(f"Error sirviendo historial-contrataciones.html: {e}")
        return "Archivo no encontrado", 404


# ================================================================
# RUTAS PARA ARCHIVOS CSS
# ================================================================

@contratos_bp.route('/assent/css/historial-contrataciones.css')
def historial_contrataciones_css():
    """CSS para historial de contrataciones"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        css_path = os.path.join(base_dir, '..', '..', 'assent', 'css')
        css_path = os.path.abspath(css_path)
        response = send_from_directory(css_path, 'historial-contrataciones.css')
        response.headers['Content-Type'] = 'text/css'
        return response
    except Exception as e:
        print(f"Error sirviendo historial-contrataciones.css: {e}")
        return "CSS no encontrado", 404


# ================================================================
# RUTAS PARA ARCHIVOS JAVASCRIPT
# ================================================================

@contratos_bp.route('/js/historial-contrataciones.js')
def historial_contrataciones_js():
    """JavaScript para historial de contrataciones"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        js_path = os.path.join(base_dir, '..', '..', 'js')
        js_path = os.path.abspath(js_path)
        response = send_from_directory(js_path, 'historial-contrataciones.js')
        response.headers['Content-Type'] = 'application/javascript'
        return response
    except Exception as e:
        print(f"Error sirviendo historial-contrataciones.js: {e}")
        return "JS no encontrado", 404


print("✅ Endpoints de historial de empleos y contrataciones cargados correctamente")
print("📋 APIs disponibles:")
print("   • GET  /api/historial_empleos_trabajador")
print("   • GET  /api/historial_contrataciones_agricultor")
print("   • POST /api/calificar_trabajador")
print("   • GET  /vista/historial-empleos.html")
print("   • GET  /vista/historial-contrataciones.html")


# ================================================================
# 6. HISTORIAL CONTRATACIONES AGRICULTOR V2 (NUEVO NOMBRE)
# ================================================================

@contratos_bp.route('/api/historial_contrataciones_v2', methods=['GET'])
def historial_contrataciones_v2():
    """Historial de contrataciones del agricultor"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        user_id = session['user_id']
        user_role = session.get('user_role', session.get('role'))
        
        if user_role != 'Agricultor':
            return jsonify({'success': False, 'message': 'Solo agricultores'}), 403
        
        contrataciones = execute_query("""
            SELECT al.ID_Acuerdo as id, al.Fecha_Inicio as fecha_inicio,
                   al.Fecha_Fin as fecha_fin, al.Pago_Final as pago_final,
                   al.Estado as estado, ot.Titulo as titulo_oferta,
                   ot.ID_Oferta as id_oferta,
                   CONCAT(u.Nombre, ' ', u.Apellido) as nombre_trabajador,
                   u.Telefono as telefono_trabajador, u.Correo as email_trabajador,
                   u.URL_Foto as foto_trabajador, u.ID_Usuario as id_trabajador,
                   c.Puntuacion as calificacion_dada, c.Comentario as comentario_calificacion
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            INNER JOIN Usuario u ON al.ID_Trabajador = u.ID_Usuario
            LEFT JOIN Calificacion c ON c.ID_Acuerdo = al.ID_Acuerdo AND c.ID_Usuario_Emisor = %s
            WHERE ot.ID_Agricultor = %s
            ORDER BY al.Fecha_Inicio DESC
        """, (user_id, user_id))
        
        contrataciones_list = []
        for cont in contrataciones:
            contrataciones_list.append({
                'id': cont['id'],
                'fecha_inicio': cont['fecha_inicio'].strftime('%Y-%m-%d') if cont['fecha_inicio'] else None,
                'fecha_fin': cont['fecha_fin'].strftime('%Y-%m-%d') if cont['fecha_fin'] else None,
                'pago_final': float(cont['pago_final']) if cont['pago_final'] else 0,
                'estado': cont['estado'],
                'titulo_oferta': cont['titulo_oferta'],
                'id_oferta': cont['id_oferta'],
                'nombre_trabajador': cont['nombre_trabajador'],
                'telefono_trabajador': cont['telefono_trabajador'] or 'No disponible',
                'email_trabajador': cont['email_trabajador'],
                'foto_trabajador': cont['foto_trabajador'],
                'id_trabajador': cont['id_trabajador'],
                'calificacion_dada': int(cont['calificacion_dada']) if cont['calificacion_dada'] else None,
                'comentario_calificacion': cont['comentario_calificacion']
            })
        
        return jsonify({'success': True, 'contrataciones': contrataciones_list, 'total': len(contrataciones_list)})
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ================================================================
# 7. HISTORIAL EMPLEOS TRABAJADOR V2 (NUEVO NOMBRE)
# ================================================================

@contratos_bp.route('/api/historial_empleos_v2', methods=['GET'])
def historial_empleos_v2():
    """Historial de empleos para trabajadores con datos de calificación"""
    try:
        trabajador_id = session.get('user_id')
        if not trabajador_id:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                a.ID_Acuerdo,
                o.ID_Oferta as id,
                o.Titulo as titulo,
                o.Descripcion as descripcion,
                o.Pago_Ofrecido as pago,
                o.Fecha_Publicacion as fecha_publicacion,
                a.Fecha_Inicio as fecha_inicio,
                a.Fecha_Fin as fecha_fin,
                a.Pago_Final as pago_final,
                a.Estado as estado,
                CONCAT(u.Nombre, ' ', u.Apellido) as empleador,
                u.ID_Usuario as id_empleador,
                DATEDIFF(COALESCE(a.Fecha_Fin, NOW()), a.Fecha_Inicio) as duracion_dias,
                c.Puntuacion as calificacion,
                c.Comentario as comentario,
                'Agricultura' as tipo,
                'Bogotá' as ubicacion
            FROM Acuerdo_Laboral a
            INNER JOIN Oferta_Trabajo o ON a.ID_Oferta = o.ID_Oferta
            INNER JOIN Usuario u ON o.ID_Agricultor = u.ID_Usuario
            LEFT JOIN Calificacion c ON a.ID_Acuerdo = c.ID_Acuerdo AND c.ID_Usuario_Emisor = %s
            WHERE a.ID_Trabajador = %s
            ORDER BY a.Fecha_Inicio DESC
        """
        
        cursor.execute(query, (trabajador_id, trabajador_id))
        empleos = cursor.fetchall()
        
        # Formatear datos
        empleos_formateados = []
        for empleo in empleos:
            duracion = f"{empleo['duracion_dias']} días" if empleo['duracion_dias'] else "1 día"
            
            empleo_data = {
                'id': empleo['id'],
                'id_acuerdo': empleo['ID_Acuerdo'],
                'id_empleador': empleo['id_empleador'],
                'titulo': empleo['titulo'],
                'descripcion': empleo['descripcion'] or '',
                'pago': float(empleo['pago_final'] or empleo['pago'] or 0),
                'fecha_inicio': empleo['fecha_inicio'].strftime('%Y-%m-%d') if empleo['fecha_inicio'] else '',
                'fecha_fin': empleo['fecha_fin'].strftime('%Y-%m-%d') if empleo['fecha_fin'] else None,
                'duracion': duracion,
                'estado': empleo['estado'],
                'empleador': empleo['empleador'],
                'tipo': empleo['tipo'],
                'ubicacion': empleo['ubicacion'],
                'calificacion': int(empleo['calificacion']) if empleo['calificacion'] else None,
                'comentario': empleo['comentario']
            }
            empleos_formateados.append(empleo_data)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'empleos': empleos_formateados
        })
        
    except Exception as e:
        print(f"❌ Error en historial_empleos_v2: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

print("✅ Endpoint de historial actualizado con datos de calificación")


# ================================================================
# 8. CALIFICAR TRABAJADOR V2 (NUEVO NOMBRE)
# ================================================================

@contratos_bp.route('/api/calificar_trabajador_v2', methods=['POST'])
def calificar_trabajador_v2():
    """Calificar trabajador"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        user_id = session['user_id']
        user_role = session.get('user_role', session.get('role'))
        
        if user_role != 'Agricultor':
            return jsonify({'success': False, 'message': 'Solo agricultores'}), 403
        
        data = request.get_json()
        contratacion_id = data.get('contratacion_id')
        puntuacion = data.get('puntuacion')
        comentario = data.get('comentario', '')
        
        if not puntuacion or int(puntuacion) < 1 or int(puntuacion) > 5:
            return jsonify({'success': False, 'message': 'Puntuación entre 1-5'}), 400
        
        acuerdo = execute_query("""
            SELECT al.ID_Acuerdo, al.ID_Trabajador, ot.ID_Agricultor
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            WHERE al.ID_Acuerdo = %s
        """, (contratacion_id,), fetch_one=True)
        
        if not acuerdo or acuerdo['ID_Agricultor'] != user_id:
            return jsonify({'success': False, 'message': 'Contratación no encontrada'}), 404
        
        existe = execute_query("""
            SELECT ID_Calificacion FROM Calificacion
            WHERE ID_Acuerdo = %s AND ID_Usuario_Emisor = %s
        """, (contratacion_id, user_id), fetch_one=True)
        
        if existe:
            return jsonify({'success': False, 'message': 'Ya has calificado'}), 400
        
        execute_query("""
            INSERT INTO Calificacion 
            (ID_Acuerdo, ID_Usuario_Emisor, ID_Usuario_Receptor, Puntuacion, Comentario)
            VALUES (%s, %s, %s, %s, %s)
        """, (contratacion_id, user_id, acuerdo['ID_Trabajador'], puntuacion, comentario))
        
        return jsonify({'success': True, 'message': 'Calificación enviada'})
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


print("=" * 70)
print("✅ ENDPOINTS V2/V3 CARGADOS (sin conflictos de nombres)")
print("=" * 70)
print("📋 Rutas nuevas:")
print("   PUT  /api/cerrar_oferta_manual_v2/<job_id>")
print("   PUT  /api/reabrir_oferta_v2/<job_id>")
print("   PUT  /api/aceptar_postulacion_v3/<application_id>")
print("   PUT  /api/rechazar_postulacion_v3/<application_id>")
print("   GET  /api/estadisticas_cierre_v2/<job_id>")
print("   GET  /api/historial_contrataciones_v2")
print("   GET  /api/historial_empleos_v2")
print("   POST /api/calificar_trabajador_v2")
print("=" * 70)


# ============================================================
# ENDPOINTS DE CALIFICACIONES - VERSIÓN SIN CONFLICTOS
# Agregar al final de app.py (antes del if __name__ == '__main__':)
# ============================================================

# ============================================================
# 1. OBTENER CALIFICACIONES RECIBIDAS POR UN USUARIO
# ============================================================

@contratos_bp.route('/api/get_ratings_received', methods=['GET'])
def get_ratings_received():
    """Obtiene las calificaciones recibidas por un usuario (nombre único)"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False, 
                'message': 'Usuario no identificado'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener todas las calificaciones recibidas
        query = """
            SELECT 
                c.ID_Calificacion,
                c.Puntuacion,
                c.Comentario,
                c.Fecha,
                CONCAT(u.Nombre, ' ', u.Apellido) as emisor_nombre,
                u.URL_Foto as emisor_foto,
                u.Rol as emisor_rol,
                o.Titulo as trabajo_titulo,
                al.Fecha_Inicio as trabajo_fecha
            FROM Calificacion c
            INNER JOIN Usuario u ON c.ID_Usuario_Emisor = u.ID_Usuario
            LEFT JOIN Acuerdo_Laboral al ON c.ID_Acuerdo = al.ID_Acuerdo
            LEFT JOIN Oferta_Trabajo o ON al.ID_Oferta = o.ID_Oferta
            WHERE c.ID_Usuario_Receptor = %s
            ORDER BY c.Fecha DESC
        """
        
        cursor.execute(query, (user_id,))
        calificaciones = cursor.fetchall()
        
        # Calcular estadísticas
        if calificaciones:
            total = len(calificaciones)
            suma = sum(int(c['Puntuacion']) for c in calificaciones)
            promedio = suma / total
            
            # Contar por estrellas
            distribucion = {
                '5': sum(1 for c in calificaciones if int(c['Puntuacion']) == 5),
                '4': sum(1 for c in calificaciones if int(c['Puntuacion']) == 4),
                '3': sum(1 for c in calificaciones if int(c['Puntuacion']) == 3),
                '2': sum(1 for c in calificaciones if int(c['Puntuacion']) == 2),
                '1': sum(1 for c in calificaciones if int(c['Puntuacion']) == 1)
            }
        else:
            total = 0
            promedio = 0.0
            distribucion = {'5': 0, '4': 0, '3': 0, '2': 0, '1': 0}
        
        # Formatear respuesta
        calificaciones_formateadas = []
        for cal in calificaciones:
            calificaciones_formateadas.append({
                'id': cal['ID_Calificacion'],
                'puntuacion': int(cal['Puntuacion']),
                'comentario': cal['Comentario'] or '',
                'fecha': cal['Fecha'].strftime('%Y-%m-%d %H:%M') if cal['Fecha'] else '',
                'emisor': {
                    'nombre': cal['emisor_nombre'],
                    'foto': cal['emisor_foto'],
                    'rol': cal['emisor_rol']
                },
                'trabajo': {
                    'titulo': cal['trabajo_titulo'] or 'Trabajo sin título',
                    'fecha': cal['trabajo_fecha'].strftime('%Y-%m-%d') if cal['trabajo_fecha'] else ''
                }
            })
        
        cursor.close()
        conn.close()
        
        print(f"✅ Calificaciones obtenidas para usuario {user_id}: {total} total, promedio {promedio:.1f}")
        
        return jsonify({
            'success': True,
            'calificaciones': calificaciones_formateadas,
            'estadisticas': {
                'total': total,
                'promedio': round(promedio, 1),
                'distribucion': distribucion
            }
        })
        
    except Exception as e:
        print(f"❌ Error en get_ratings_received: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'message': f'Error interno: {str(e)}'
        }), 500


# ============================================================
# 2. OBTENER CALIFICACIONES DADAS POR UN USUARIO
# ============================================================

@contratos_bp.route('/api/get_ratings_given', methods=['GET'])
def get_ratings_given():
    """Obtiene las calificaciones que un usuario ha dado a otros"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False, 
                'message': 'Usuario no identificado'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener calificaciones dadas
        query = """
            SELECT 
                c.ID_Calificacion,
                c.Puntuacion,
                c.Comentario,
                c.Fecha,
                CONCAT(u.Nombre, ' ', u.Apellido) as receptor_nombre,
                u.URL_Foto as receptor_foto,
                u.Rol as receptor_rol,
                o.Titulo as trabajo_titulo,
                al.Fecha_Inicio as trabajo_fecha
            FROM Calificacion c
            INNER JOIN Usuario u ON c.ID_Usuario_Receptor = u.ID_Usuario
            LEFT JOIN Acuerdo_Laboral al ON c.ID_Acuerdo = al.ID_Acuerdo
            LEFT JOIN Oferta_Trabajo o ON al.ID_Oferta = o.ID_Oferta
            WHERE c.ID_Usuario_Emisor = %s
            ORDER BY c.Fecha DESC
        """
        
        cursor.execute(query, (user_id,))
        calificaciones = cursor.fetchall()
        
        # Formatear respuesta
        calificaciones_formateadas = []
        for cal in calificaciones:
            calificaciones_formateadas.append({
                'id': cal['ID_Calificacion'],
                'puntuacion': int(cal['Puntuacion']),
                'comentario': cal['Comentario'] or '',
                'fecha': cal['Fecha'].strftime('%Y-%m-%d %H:%M') if cal['Fecha'] else '',
                'receptor': {
                    'nombre': cal['receptor_nombre'],
                    'foto': cal['receptor_foto'],
                    'rol': cal['receptor_rol']
                },
                'trabajo': {
                    'titulo': cal['trabajo_titulo'] or 'Trabajo sin título',
                    'fecha': cal['trabajo_fecha'].strftime('%Y-%m-%d') if cal['trabajo_fecha'] else ''
                }
            })
        
        cursor.close()
        conn.close()
        
        print(f"✅ Calificaciones dadas por usuario {user_id}: {len(calificaciones_formateadas)} total")
        
        return jsonify({
            'success': True,
            'calificaciones': calificaciones_formateadas,
            'total': len(calificaciones_formateadas)
        })
        
    except Exception as e:
        print(f"❌ Error en get_ratings_given: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'message': f'Error interno: {str(e)}'
        }), 500


# ============================================================
# 3. ENVIAR UNA NUEVA CALIFICACIÓN
# ============================================================

@contratos_bp.route('/api/submit_new_rating', methods=['POST'])
def submit_new_rating():
    """Permite calificar a otro usuario después de completar un trabajo"""
    try:
        # Verificar autenticación
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False, 
                'message': 'No autenticado'
            }), 401
        
        # Obtener datos del request
        data = request.get_json()
        acuerdo_id = data.get('acuerdo_id')
        receptor_id = data.get('receptor_id')
        puntuacion = data.get('puntuacion')
        comentario = data.get('comentario', '').strip()
        
        print(f"📝 Enviando calificación:")
        print(f"   Emisor: {user_id}")
        print(f"   Receptor: {receptor_id}")
        print(f"   Acuerdo: {acuerdo_id}")
        print(f"   Puntuación: {puntuacion}")
        
        # Validaciones
        if not all([acuerdo_id, receptor_id, puntuacion]):
            return jsonify({
                'success': False, 
                'message': 'Datos incompletos. Se requiere acuerdo_id, receptor_id y puntuacion'
            }), 400
        
        try:
            puntuacion = int(puntuacion)
        except ValueError:
            return jsonify({
                'success': False, 
                'message': 'La puntuación debe ser un número'
            }), 400
        
        if puntuacion < 1 or puntuacion > 5:
            return jsonify({
                'success': False, 
                'message': 'La puntuación debe estar entre 1 y 5'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar que el acuerdo existe y el usuario tiene permisos
        cursor.execute("""
            SELECT 
                al.ID_Acuerdo,
                al.ID_Trabajador,
                ot.ID_Agricultor,
                al.Estado,
                ot.Titulo
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            WHERE al.ID_Acuerdo = %s
        """, (acuerdo_id,))
        
        acuerdo = cursor.fetchone()
        
        if not acuerdo:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False, 
                'message': 'Acuerdo laboral no encontrado'
            }), 404
        
        # Verificar que el usuario sea parte del acuerdo
        if user_id not in [acuerdo['ID_Trabajador'], acuerdo['ID_Agricultor']]:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False, 
                'message': 'No tienes permisos para calificar este trabajo'
            }), 403
        
        # Verificar que el trabajo esté finalizado
        if acuerdo['Estado'] != 'Finalizado':
            cursor.close()
            conn.close()
            return jsonify({
                'success': False, 
                'message': 'Solo puedes calificar trabajos finalizados'
            }), 400
        
        # Verificar que no haya calificado ya
        cursor.execute("""
            SELECT ID_Calificacion 
            FROM Calificacion 
            WHERE ID_Acuerdo = %s 
            AND ID_Usuario_Emisor = %s
        """, (acuerdo_id, user_id))
        
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({
                'success': False, 
                'message': 'Ya has calificado este trabajo'
            }), 400
        
        # Insertar la calificación
        cursor.execute("""
            INSERT INTO Calificacion 
            (ID_Acuerdo, ID_Usuario_Emisor, ID_Usuario_Receptor, Puntuacion, Comentario, Fecha)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (acuerdo_id, user_id, receptor_id, str(puntuacion), comentario if comentario else None))
        
        conn.commit()
        
        # Obtener nombre del receptor
        cursor.execute("""
            SELECT CONCAT(Nombre, ' ', Apellido) as nombre
            FROM Usuario WHERE ID_Usuario = %s
        """, (receptor_id,))
        receptor = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        print(f"✅ Calificación enviada exitosamente: {user_id} → {receptor_id} ({puntuacion}⭐)")
        
        return jsonify({
            'success': True,
            'message': f'Calificación de {puntuacion}⭐ enviada a {receptor["nombre"] if receptor else "usuario"}',
            'calificacion': {
                'puntuacion': puntuacion,
                'comentario': comentario,
                'receptor': receptor['nombre'] if receptor else 'Usuario'
            }
        })
        
    except Exception as e:
        print(f"❌ Error en submit_new_rating: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'message': f'Error interno: {str(e)}'
        }), 500


# ============================================================
# 4. VERIFICAR SI PUEDE CALIFICAR
# ============================================================

@contratos_bp.route('/api/check_can_rate/<int:acuerdo_id>', methods=['GET'])
def check_can_rate(acuerdo_id):
    """Verifica si el usuario puede calificar un acuerdo específico"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False, 
                'can_rate': False,
                'message': 'No autenticado'
            }), 401
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar el acuerdo
        cursor.execute("""
            SELECT 
                al.ID_Acuerdo,
                al.ID_Trabajador,
                al.Estado,
                ot.ID_Agricultor,
                ot.Titulo,
                CONCAT(ut.Nombre, ' ', ut.Apellido) as trabajador_nombre,
                CONCAT(ua.Nombre, ' ', ua.Apellido) as agricultor_nombre
            FROM Acuerdo_Laboral al
            INNER JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
            INNER JOIN Usuario ut ON al.ID_Trabajador = ut.ID_Usuario
            INNER JOIN Usuario ua ON ot.ID_Agricultor = ua.ID_Usuario
            WHERE al.ID_Acuerdo = %s
        """, (acuerdo_id,))
        
        acuerdo = cursor.fetchone()
        
        if not acuerdo:
            cursor.close()
            conn.close()
            return jsonify({
                'success': True,
                'can_rate': False,
                'message': 'Acuerdo no encontrado'
            })
        
        # Determinar receptor
        if user_id == acuerdo['ID_Trabajador']:
            receptor_id = acuerdo['ID_Agricultor']
            receptor_nombre = acuerdo['agricultor_nombre']
            user_role = 'Trabajador'
        elif user_id == acuerdo['ID_Agricultor']:
            receptor_id = acuerdo['ID_Trabajador']
            receptor_nombre = acuerdo['trabajador_nombre']
            user_role = 'Agricultor'
        else:
            cursor.close()
            conn.close()
            return jsonify({
                'success': True,
                'can_rate': False,
                'message': 'No eres parte de este acuerdo'
            })
        
        # Verificar si está finalizado
        if acuerdo['Estado'] != 'Finalizado':
            cursor.close()
            conn.close()
            return jsonify({
                'success': True,
                'can_rate': False,
                'message': 'El trabajo aún no ha finalizado'
            })
        
        # Verificar si ya calificó
        cursor.execute("""
            SELECT ID_Calificacion 
            FROM Calificacion 
            WHERE ID_Acuerdo = %s AND ID_Usuario_Emisor = %s
        """, (acuerdo_id, user_id))
        
        ya_califico = cursor.fetchone() is not None
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'can_rate': not ya_califico,
            'already_rated': ya_califico,
            'info': {
                'trabajo_titulo': acuerdo['Titulo'],
                'receptor_id': receptor_id,
                'receptor_nombre': receptor_nombre,
                'user_role': user_role
            },
            'message': 'Ya has calificado este trabajo' if ya_califico else 'Puedes calificar este trabajo'
        })
        
    except Exception as e:
        print(f"❌ Error en check_can_rate: {e}")
        return jsonify({
            'success': False, 
            'can_rate': False,
            'message': str(e)
        }), 500


# ============================================================
# 5. ELIMINAR UNA CALIFICACIÓN (SOLO SI ES PROPIA)
# ============================================================

@contratos_bp.route('/api/remove_my_rating/<int:calificacion_id>', methods=['DELETE'])
def remove_my_rating(calificacion_id):
    """Eliminar una calificación propia"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False, 
                'message': 'No autenticado'
            }), 401
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar que la calificación existe y es del usuario
        cursor.execute("""
            SELECT ID_Calificacion, ID_Usuario_Emisor
            FROM Calificacion
            WHERE ID_Calificacion = %s
        """, (calificacion_id,))
        
        calificacion = cursor.fetchone()
        
        if not calificacion:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Calificación no encontrada'
            }), 404
        
        if calificacion['ID_Usuario_Emisor'] != user_id:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'No puedes eliminar calificaciones de otros usuarios'
            }), 403
        
        # Eliminar la calificación
        cursor.execute("""
            DELETE FROM Calificacion
            WHERE ID_Calificacion = %s
        """, (calificacion_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Calificación {calificacion_id} eliminada por usuario {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Calificación eliminada correctamente'
        })
        
    except Exception as e:
        print(f"❌ Error en remove_my_rating: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ============================================================
# MENSAJES DE CONFIRMACIÓN
# ============================================================

print("=" * 70)
print("✅ ENDPOINTS DE CALIFICACIONES CARGADOS (sin conflictos)")
print("=" * 70)
print("📋 Rutas disponibles:")
print("   GET    /api/get_ratings_received      - Calificaciones recibidas")
print("   GET    /api/get_ratings_given         - Calificaciones dadas")
print("   POST   /api/submit_new_rating         - Enviar nueva calificación")
print("   GET    /api/check_can_rate/<id>       - Verificar si puede calificar")
print("   DELETE /api/remove_my_rating/<id>     - Eliminar calificación propia")
print("=" * 70)
print("💡 Uso básico:")
print("   # Obtener calificaciones recibidas")
print("   GET /api/get_ratings_received?user_id=123")
print("")
print("   # Enviar calificación")
print("   POST /api/submit_new_rating")
print("   Body: {")
print("     'acuerdo_id': 456,")
print("     'receptor_id': 789,")
print("     'puntuacion': 5,")
print("     'comentario': 'Excelente trabajo!'")
print("   }")
print("=" * 70)


# ================================================================
# SISTEMA DE CALIFICACIONES - ENDPOINTS
# ================================================================

@contratos_bp.route('/api/get_user_rating/<int:user_id>', methods=['GET'])
def get_user_rating(user_id):
    """Obtiene la calificación promedio de un usuario"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Calcular promedio de calificaciones recibidas
        query = """
            SELECT 
                COALESCE(AVG(CAST(Puntuacion AS DECIMAL(3,2))), 0) as promedio,
                COUNT(*) as total_calificaciones
            FROM Calificacion
            WHERE ID_Usuario_Receptor = %s
        """
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        
        promedio = float(result['promedio']) if result['promedio'] else 0.0
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'promedio': round(promedio, 1),
            'total_calificaciones': result['total_calificaciones'],
            'estrellas_completas': int(promedio),
            'tiene_media_estrella': (promedio % 1) >= 0.5
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo calificación: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@contratos_bp.route('/api/get_rating_details/<int:user_id>', methods=['GET'])
def get_rating_details(user_id):
    """Obtiene el desglose detallado de calificaciones"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Contar calificaciones por puntuación
        query_distribucion = """
            SELECT 
                Puntuacion,
                COUNT(*) as cantidad
            FROM Calificacion
            WHERE ID_Usuario_Receptor = %s
            GROUP BY Puntuacion
            ORDER BY Puntuacion DESC
        """
        cursor.execute(query_distribucion, (user_id,))
        desglose = cursor.fetchall()
        
        # Obtener últimas calificaciones con comentarios
        query_comentarios = """
            SELECT 
                c.Puntuacion,
                c.Comentario,
                c.Fecha,
                CONCAT(u.Nombre, ' ', u.Apellido) as nombre_emisor,
                u.URL_Foto as foto_emisor,
                u.Rol as rol_emisor
            FROM Calificacion c
            JOIN Usuario u ON c.ID_Usuario_Emisor = u.ID_Usuario
            WHERE c.ID_Usuario_Receptor = %s
            AND c.Comentario IS NOT NULL
            AND c.Comentario != ''
            ORDER BY c.Fecha DESC
            LIMIT 10
        """
        cursor.execute(query_comentarios, (user_id,))
        comentarios_recientes = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Crear estructura de desglose completa (1-5 estrellas)
        desglose_completo = {str(i): 0 for i in range(1, 6)}
        for item in desglose:
            desglose_completo[item['Puntuacion']] = item['cantidad']
        
        return jsonify({
            'success': True,
            'desglose': desglose_completo,
            'comentarios_recientes': comentarios_recientes
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo detalles: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

