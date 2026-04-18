# Blueprint: trabajadores
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

trabajadores_bp = Blueprint('trabajadores', __name__)
from blueprints.helpers import require_login, require_role, hash_password, verify_password, no_cache


# ================================================================
# RUTAS PARA PERFIL DE TRABAJADOR
# ================================================================

@trabajadores_bp.route('/perfil-trabajador')


@trabajadores_bp.route('/perfil-trabajador.html')
def perfil_trabajador():
    """Mostrar página de perfil del trabajador"""
    if 'user_id' not in session:
        return redirect('/vista/login-trabajador.html')
    return redirect('/vista/perfil-trabajador.html')


@trabajadores_bp.route('/vista/perfil-trabajador.html')
def perfil_trabajador_html():
    """Página de perfil del trabajador"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vista_path = os.path.join(base_dir, '..', '..', 'vista')
        vista_path = os.path.abspath(vista_path)
        return send_from_directory(vista_path, 'perfil-trabajador.html')
    except Exception as e:
        print(f"Error sirviendo perfil-trabajador.html: {e}")
        return "Archivo no encontrado", 404


# ================================================================
# ENDPOINT PARA VER PERFIL DE TRABAJADOR (Para el Agricultor)
# ================================================================
@trabajadores_bp.route('/api/get_worker_profile/<int:worker_id>', methods=['GET'])
@require_login
def get_worker_profile(worker_id):
    """Obtener perfil completo de un trabajador"""
    try:
        # Información básica del trabajador
        worker = execute_query("""
            SELECT 
                u.ID_Usuario,
                u.Nombre,
                u.Apellido,
                u.Correo,
                u.Telefono,
                u.URL_Foto,
                u.Fecha_Registro,
                u.Red_Social
            FROM Usuario u
            WHERE u.ID_Usuario = %s AND u.Rol = 'Trabajador'
        """, (worker_id,), fetch_one=True)
        
        if not worker:
            return jsonify({'success': False, 'message': 'Trabajador no encontrado'}), 404
        
        # Habilidades del trabajador
        habilidades = execute_query("""
            SELECT Nombre, Clasificacion 
            FROM Habilidad 
            WHERE ID_Trabajador = %s
        """, (worker_id,))
        
        # Experiencia laboral
        experiencias = execute_query("""
            SELECT 
                Fecha_Inicio,
                Fecha_Fin,
                Ubicacion,
                Observacion
            FROM Experiencia 
            WHERE ID_Trabajador = %s
            ORDER BY Fecha_Inicio DESC
            LIMIT 5
        """, (worker_id,))
        
        # Estadísticas del trabajador
        stats = execute_query("""
            SELECT 
                COUNT(DISTINCT al.ID_Acuerdo) as trabajos_completados,
                AVG(CAST(c.Puntuacion AS DECIMAL(3,2))) as calificacion_promedio,
                COUNT(DISTINCT c.ID_Calificacion) as total_calificaciones
            FROM Usuario u
            LEFT JOIN Acuerdo_Laboral al ON u.ID_Usuario = al.ID_Trabajador AND al.Estado = 'Finalizado'
            LEFT JOIN Calificacion c ON u.ID_Usuario = c.ID_Usuario_Receptor
            WHERE u.ID_Usuario = %s
        """, (worker_id,), fetch_one=True)
        
        # Calificaciones recientes
        calificaciones = execute_query("""
            SELECT 
                c.Puntuacion,
                c.Comentario,
                c.Fecha,
                CONCAT(u.Nombre, ' ', u.Apellido) as nombre_calificador
            FROM Calificacion c
            JOIN Usuario u ON c.ID_Usuario_Emisor = u.ID_Usuario
            WHERE c.ID_Usuario_Receptor = %s
            ORDER BY c.Fecha DESC
            LIMIT 5
        """, (worker_id,))
        
        return jsonify({
            'success': True,
            'worker': {
                'id': worker['ID_Usuario'],
                'nombre': worker['Nombre'],
                'apellido': worker['Apellido'],
                'nombre_completo': f"{worker['Nombre']} {worker['Apellido']}",
                'email': worker['Correo'],
                'telefono': worker.get('Telefono', 'No disponible'),
                'foto_url': worker.get('URL_Foto'),
                'fecha_registro': worker['Fecha_Registro'].strftime('%Y-%m-%d') if worker['Fecha_Registro'] else None,
                'red_social': worker.get('Red_Social', ''),
                'habilidades': habilidades or [],
                'experiencias': experiencias or [],
                'estadisticas': {
                    'trabajos_completados': stats['trabajos_completados'] if stats else 0,
                    'calificacion_promedio': float(stats['calificacion_promedio']) if stats and stats['calificacion_promedio'] else 0.0,
                    'total_calificaciones': stats['total_calificaciones'] if stats else 0
                },
                'calificaciones_recientes': calificaciones or []
            }
        })
        
    except Exception as e:
        print(f"Error obteniendo perfil de trabajador: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ================================================================
# AGREGAR ESTAS RUTAS A TU app.py EXISTENTE
# APIs para Búsqueda de Trabajadores y Recomendaciones
# ================================================================

# ================================================================
# RF18: BÚSQUEDA Y FILTRADO DE TRABAJADORES (Para Agricultores)
# ================================================================

@trabajadores_bp.route('/api/buscar-trabajadores', methods=['GET'])
@require_login
def buscar_trabajadores():
    """Buscar trabajadores con filtros avanzados"""
    try:
        user_role = session.get('user_role')
        
        if user_role != 'Agricultor':
            return jsonify({
                'success': False,
                'message': 'Solo agricultores pueden buscar trabajadores'
            }), 403
        
        # Obtener parámetros de búsqueda
        habilidad = request.args.get('habilidad', '')
        ubicacion = request.args.get('ubicacion', '')
        experiencia_min = request.args.get('experiencia_min', '0')
        calificacion_min = request.args.get('calificacion_min', '0')
        disponibilidad = request.args.get('disponibilidad', '')
        
        # Construir query base
        query = """
            SELECT DISTINCT
                u.ID_Usuario,
                u.Nombre,
                u.Apellido,
                u.Correo,
                u.Telefono,
                u.URL_Foto,
                u.Fecha_Registro,
                -- Calcular experiencia en años
                COALESCE(
                    TIMESTAMPDIFF(YEAR, 
                        MIN(e.Fecha_Inicio), 
                        COALESCE(MAX(e.Fecha_Fin), NOW())
                    ), 0
                ) as anos_experiencia,
                -- Calificación promedio
                COALESCE(AVG(CAST(c.Puntuacion AS DECIMAL(3,2))), 0) as calificacion_promedio,
                -- Total de trabajos completados
                COUNT(DISTINCT al.ID_Acuerdo) as trabajos_completados,
                -- Ubicación más reciente
                (SELECT e2.Ubicacion 
                 FROM Experiencia e2 
                 WHERE e2.ID_Trabajador = u.ID_Usuario 
                 ORDER BY e2.Fecha_Inicio DESC 
                 LIMIT 1) as ubicacion_reciente
            FROM Usuario u
            LEFT JOIN Experiencia e ON u.ID_Usuario = e.ID_Trabajador
            LEFT JOIN Calificacion c ON u.ID_Usuario = c.ID_Usuario_Receptor
            LEFT JOIN Acuerdo_Laboral al ON u.ID_Usuario = al.ID_Trabajador AND al.Estado = 'Finalizado'
            WHERE u.Rol = 'Trabajador' AND u.Estado = 'Activo'
        """
        
        params = []
        
        # Aplicar filtros
        if habilidad:
            query += """
                AND EXISTS (
                    SELECT 1 FROM Habilidad h 
                    WHERE h.ID_Trabajador = u.ID_Usuario 
                    AND (h.Nombre LIKE %s OR h.Clasificacion LIKE %s)
                )
            """
            habilidad_like = f"%{habilidad}%"
            params.extend([habilidad_like, habilidad_like])
        
        if ubicacion:
            query += """
                AND EXISTS (
                    SELECT 1 FROM Experiencia e2 
                    WHERE e2.ID_Trabajador = u.ID_Usuario 
                    AND e2.Ubicacion LIKE %s
                )
            """
            params.append(f"%{ubicacion}%")
        
        query += """
            GROUP BY u.ID_Usuario, u.Nombre, u.Apellido, u.Correo, 
                     u.Telefono, u.URL_Foto, u.Fecha_Registro
            HAVING 1=1
        """
        
        # Filtros de HAVING (después de GROUP BY)
        if experiencia_min and int(experiencia_min) > 0:
            query += " AND anos_experiencia >= %s"
            params.append(int(experiencia_min))
        
        if calificacion_min and float(calificacion_min) > 0:
            query += " AND calificacion_promedio >= %s"
            params.append(float(calificacion_min))
        
        # Ordenamiento por relevancia
        query += " ORDER BY calificacion_promedio DESC, trabajos_completados DESC LIMIT 50"
        
        trabajadores = execute_query(query, tuple(params) if params else None)
        
        # Obtener habilidades para cada trabajador
        trabajadores_list = []
        if trabajadores:
            for trabajador in trabajadores:
                # Habilidades del trabajador
                habilidades = execute_query("""
                    SELECT Nombre, Clasificacion 
                    FROM Habilidad 
                    WHERE ID_Trabajador = %s
                """, (trabajador['ID_Usuario'],))
                
                trabajadores_list.append({
                    'id': trabajador['ID_Usuario'],
                    'nombre': f"{trabajador['Nombre']} {trabajador['Apellido']}",
                    'email': trabajador['Correo'],
                    'telefono': trabajador['Telefono'],
                    'foto_url': trabajador['URL_Foto'],
                    'anos_experiencia': int(trabajador['anos_experiencia']),
                    'calificacion': float(trabajador['calificacion_promedio']),
                    'trabajos_completados': trabajador['trabajos_completados'] or 0,
                    'ubicacion': trabajador['ubicacion_reciente'] or 'No especificada',
                    'habilidades': habilidades or [],
                    'fecha_registro': trabajador['Fecha_Registro'].strftime('%Y-%m-%d')
                })
        
        return jsonify({
            'success': True,
            'trabajadores': trabajadores_list,
            'total': len(trabajadores_list),
            'filtros_aplicados': {
                'habilidad': habilidad,
                'ubicacion': ubicacion,
                'experiencia_min': experiencia_min,
                'calificacion_min': calificacion_min
            }
        })
        
    except Exception as e:
        print(f"Error buscando trabajadores: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@trabajadores_bp.route('/api/habilidades-disponibles', methods=['GET'])
@require_login
def get_habilidades_disponibles():
    """Obtener lista de habilidades disponibles para filtros"""
    try:
        habilidades = execute_query("""
            SELECT DISTINCT Nombre, Clasificacion
            FROM Habilidad
            ORDER BY Clasificacion, Nombre
        """)
        
        # Agrupar por clasificación
        habilidades_agrupadas = {}
        if habilidades:
            for hab in habilidades:
                clasificacion = hab['Clasificacion']
                if clasificacion not in habilidades_agrupadas:
                    habilidades_agrupadas[clasificacion] = []
                habilidades_agrupadas[clasificacion].append(hab['Nombre'])
        
        return jsonify({
            'success': True,
            'habilidades': habilidades_agrupadas
        })
        
    except Exception as e:
        print(f"Error obteniendo habilidades: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@trabajadores_bp.route('/api/actualizar-preferencias', methods=['POST'])
@require_login
def actualizar_preferencias():
    """Actualizar preferencias del trabajador para mejorar recomendaciones"""
    try:
        user_id = session['user_id']
        user_role = session.get('user_role')
        
        if user_role != 'Trabajador':
            return jsonify({
                'success': False,
                'message': 'Solo trabajadores pueden actualizar preferencias'
            }), 403
        
        data = request.get_json()
        
        # Guardar preferencias en tabla Usuario (campo Configuraciones JSON)
        import json
        
        # Obtener configuraciones actuales
        current_config = execute_query("""
            SELECT Configuraciones 
            FROM Usuario 
            WHERE ID_Usuario = %s
        """, (user_id,), fetch_one=True)
        
        config = {}
        if current_config and current_config['Configuraciones']:
            try:
                config = json.loads(current_config['Configuraciones'])
            except:
                config = {}
        
        # Actualizar preferencias de búsqueda
        config['preferencias_empleo'] = {
            'ubicaciones_preferidas': data.get('ubicaciones', []),
            'tipos_trabajo_preferidos': data.get('tipos_trabajo', []),
            'rango_salarial_min': data.get('salario_minimo', 0),
            'rango_salarial_max': data.get('salario_maximo', 100000),
            'disponibilidad': data.get('disponibilidad', 'flexible')
        }
        
        # Guardar en base de datos
        execute_query("""
            UPDATE Usuario 
            SET Configuraciones = %s
            WHERE ID_Usuario = %s
        """, (json.dumps(config), user_id))
        
        return jsonify({
            'success': True,
            'message': 'Preferencias actualizadas correctamente'
        })
        
    except Exception as e:
        print(f"Error actualizando preferencias: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ====================== OBTENER HABILIDADES ======================
@trabajadores_bp.route('/api/get_worker_skills/<int:worker_id>', methods=['GET'])
def get_worker_skills(worker_id):
    """Obtener habilidades de un trabajador"""
    try:
        cursor = mysql.connection.cursor()
        
        query = """
        SELECT 
            ID_Habilidad,
            Nombre,
            Clasificacion,
            Nivel,
            Anos_Experiencia
        FROM Habilidad
        WHERE ID_Trabajador = %s
        ORDER BY Nivel DESC, Anos_Experiencia DESC
        """
        
        cursor.execute(query, (worker_id,))
        skills = cursor.fetchall()
        cursor.close()
        
        skills_list = []
        for skill in skills:
            skills_list.append({
                'id': skill[0],
                'nombre': skill[1],
                'clasificacion': skill[2],
                'nivel': skill[3],
                'anos_experiencia': skill[4]
            })
        
        return jsonify({
            'success': True,
            'skills': skills_list,
            'total': len(skills_list)
        })
        
    except Exception as e:
        print(f"Error obteniendo habilidades: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ====================== AGREGAR HABILIDAD ======================
# ================================================================
# SOLO REEMPLAZA LAS FUNCIONES CONFLICTIVAS
# ================================================================

# REEMPLAZAR la función add_skill existente con esta:
@trabajadores_bp.route('/api/add_skill', methods=['POST'])
@require_login
def add_skill():
    """Agregar nueva habilidad del trabajador"""
    try:
        data = request.get_json()
        user_id = session['user_id']
        
        # Obtener datos
        nombre = data.get('nombre', '').strip()
        clasificacion = data.get('clasificacion', '').strip()
        nivel = data.get('nivel', 'Intermedio')
        anos_experiencia = int(data.get('anos_experiencia', 0))
        
        # Validaciones
        if not nombre:
            return jsonify({'success': False, 'message': 'El nombre de la habilidad es requerido'}), 400
        
        if not clasificacion:
            return jsonify({'success': False, 'message': 'La clasificación es requerida'}), 400
        
        # Clasificaciones válidas
        clasificaciones_validas = [
            'Técnica agrícola', 'Manejo de maquinaria', 'Especializada', 'Logística',
            'Control de plagas', 'Riego y drenaje', 'Cosecha y poscosecha',
            'Fertilización', 'Preparación de suelo', 'Transporte y distribución'
        ]
        
        if clasificacion not in clasificaciones_validas:
            return jsonify({'success': False, 'message': 'Clasificación no válida'}), 400
        
        # Niveles válidos
        niveles_validos = ['Básico', 'Intermedio', 'Avanzado', 'Experto']
        if nivel not in niveles_validos:
            nivel = 'Intermedio'
        
        # Validar años de experiencia
        if anos_experiencia < 0 or anos_experiencia > 50:
            anos_experiencia = 0
        
        print(f"📝 Agregando habilidad para usuario {user_id}:")
        print(f"   Nombre: {nombre}")
        print(f"   Clasificación: {clasificacion}")
        print(f"   Nivel: {nivel}")
        print(f"   Años: {anos_experiencia}")
        
        # Insertar en tabla Habilidad
        skill_id = execute_query("""
            INSERT INTO Habilidad (ID_Trabajador, Nombre, Clasificacion, Nivel, Anos_Experiencia)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, nombre, clasificacion, nivel, anos_experiencia))
        
        print(f"✅ Habilidad insertada con ID: {skill_id}")
        
        return jsonify({
            'success': True,
            'message': 'Habilidad agregada correctamente',
            'skill_id': skill_id,
            'skill_data': {
                'id': skill_id,
                'nombre': nombre,
                'clasificacion': clasificacion,
                'nivel': nivel,
                'anos_experiencia': anos_experiencia
            }
        })
        
    except Exception as e:
        print(f"❌ Error agregando habilidad: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


# ====================== ELIMINAR HABILIDAD ======================
@trabajadores_bp.route('/api/delete_skill/<int:skill_id>', methods=['DELETE'])
def delete_skill(skill_id):
    """Eliminar una habilidad del perfil"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autenticado'}), 401
    
    try:
        user_id = session['user_id']
        cursor = mysql.connection.cursor()
        
        # Verificar que la habilidad pertenezca al usuario
        cursor.execute("""
            SELECT ID_Habilidad FROM Habilidad 
            WHERE ID_Habilidad = %s AND ID_Trabajador = %s
        """, (skill_id, user_id))
        
        if not cursor.fetchone():
            cursor.close()
            return jsonify({
                'success': False,
                'message': 'Habilidad no encontrada o no autorizado'
            }), 404
        
        cursor.execute("DELETE FROM Habilidad WHERE ID_Habilidad = %s", (skill_id,))
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({
            'success': True,
            'message': 'Habilidad eliminada correctamente'
        })
        
    except Exception as e:
        print(f"Error eliminando habilidad: {e}")
        mysql.connection.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ====================== BUSCAR TRABAJADORES ======================
@trabajadores_bp.route('/api/search_workers_by_skills', methods=['POST'])
def search_workers_by_skills():
    """Buscar trabajadores por habilidades"""
    try:
        data = request.get_json()
        skill_name = data.get('skill_name', '')
        clasificacion = data.get('clasificacion', '')
        nivel_minimo = data.get('nivel_minimo', '')
        
        cursor = mysql.connection.cursor()
        
        query = """
        SELECT DISTINCT
            u.ID_Usuario,
            CONCAT(u.Nombre, ' ', u.Apellido) as Nombre_Completo,
            u.Telefono,
            u.Correo,
            u.URL_Foto,
            h.Nombre as Habilidad,
            h.Clasificacion,
            h.Nivel,
            h.Anos_Experiencia,
            (SELECT COUNT(*) FROM Acuerdo_Laboral al 
             WHERE al.ID_Trabajador = u.ID_Usuario AND al.Estado = 'Finalizado') as Trabajos_Completados,
            (SELECT AVG(CAST(c.Puntuacion AS UNSIGNED)) 
             FROM Calificacion c 
             WHERE c.ID_Usuario_Receptor = u.ID_Usuario) as Calificacion_Promedio
        FROM Usuario u
        INNER JOIN Habilidad h ON u.ID_Usuario = h.ID_Trabajador
        WHERE u.Rol = 'Trabajador' 
        AND u.Estado = 'Activo'
        """
        
        params = []
        
        if skill_name:
            query += " AND h.Nombre LIKE %s"
            params.append(f"%{skill_name}%")
        
        if clasificacion:
            query += " AND h.Clasificacion = %s"
            params.append(clasificacion)
        
        if nivel_minimo:
            niveles = ['Básico', 'Intermedio', 'Avanzado', 'Experto']
            if nivel_minimo in niveles:
                idx = niveles.index(nivel_minimo)
                niveles_permitidos = niveles[idx:]
                placeholders = ','.join(['%s'] * len(niveles_permitidos))
                query += f" AND h.Nivel IN ({placeholders})"
                params.extend(niveles_permitidos)
        
        query += " ORDER BY h.Nivel DESC, h.Anos_Experiencia DESC"
        
        cursor.execute(query, params)
        workers = cursor.fetchall()
        cursor.close()
        
        workers_list = []
        for worker in workers:
            workers_list.append({
                'id': worker[0],
                'nombre': worker[1],
                'telefono': worker[2],
                'email': worker[3],
                'foto': worker[4],
                'habilidad': worker[5],
                'clasificacion': worker[6],
                'nivel': worker[7],
                'experiencia': worker[8],
                'trabajos_completados': worker[9] or 0,
                'calificacion': float(worker[10]) if worker[10] else 0.0
            })
        
        return jsonify({
            'success': True,
            'workers': workers_list,
            'total': len(workers_list)
        })
        
    except Exception as e:
        print(f"Error buscando trabajadores: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


print("✅ Endpoints de habilidades cargados correctamente")


# ================================================================
# RUTA PARA LA PÁGINA DE BÚSQUEDA DE TRABAJADORES
# ================================================================

@trabajadores_bp.route('/vista/buscar-trabajadores.html')
def buscar_trabajadores_html():
    """Página de búsqueda de trabajadores"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vista_path = os.path.join(base_dir, '..', '..', 'vista')
        vista_path = os.path.abspath(vista_path)
        return send_from_directory(vista_path, 'buscar-trabajadores.html')
    except Exception as e:
        print(f"Error sirviendo buscar-trabajadores.html: {e}")
        return "Archivo no encontrado", 404


# ================================================================
# API PARA BUSCAR TRABAJADORES (PARA AGRICULTORES)
# ================================================================

@trabajadores_bp.route('/api/buscar-trabajadores', methods=['GET'])
def buscar_trabajadores_api():
    """API para buscar trabajadores con filtros"""
    try:
        # Verificar sesión
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'message': 'Sesión no válida'
            }), 401
        
        user_id = session['user_id']
        user_role = session.get('user_role', session.get('role'))
        
        print(f"🔍 Búsqueda de trabajadores por usuario {user_id} - Rol: {user_role}")
        
        # Solo agricultores pueden buscar trabajadores
        if user_role != 'Agricultor':
            return jsonify({
                'success': False,
                'message': 'Solo los agricultores pueden buscar trabajadores'
            }), 403
        
        # Obtener filtros
        habilidad = request.args.get('habilidad', '').strip()
        ubicacion = request.args.get('ubicacion', '').strip()
        experiencia_min = int(request.args.get('experiencia_min', '0'))
        calificacion_min = float(request.args.get('calificacion_min', '0'))
        
        print(f"Filtros: habilidad={habilidad}, ubicacion={ubicacion}, exp={experiencia_min}, cal={calificacion_min}")
        
        # Query base para obtener trabajadores
        query = """
            SELECT 
                u.ID_Usuario as id,
                CONCAT(u.Nombre, ' ', u.Apellido) as nombre,
                u.Correo as correo,
                u.Telefono as telefono,
                u.Estado as estado
            FROM Usuario u
            WHERE u.Rol = 'Trabajador' AND u.Estado = 'Activo'
            ORDER BY u.Fecha_Registro DESC
            LIMIT 100
        """
        
        trabajadores = execute_query(query)
        
        print(f"✅ Encontrados {len(trabajadores) if trabajadores else 0} trabajadores iniciales")
        
        trabajadores_list = []
        
        if trabajadores:
            for trabajador in trabajadores:
                # Obtener ubicación desde experiencias
                ubicacion_trabajador = execute_query("""
                    SELECT Ubicacion 
                    FROM Experiencia 
                    WHERE ID_Trabajador = %s 
                    ORDER BY Fecha_Inicio DESC 
                    LIMIT 1
                """, (trabajador['id'],), fetch_one=True)
                
                ubicacion_final = ubicacion_trabajador['Ubicacion'] if ubicacion_trabajador else 'Colombia'
                
                # Filtrar por ubicación si se especificó
                if ubicacion and ubicacion.lower() not in ubicacion_final.lower():
                    continue
                
                # Obtener habilidades
                habilidades = execute_query("""
                    SELECT Nombre, Clasificacion, Nivel, Anos_Experiencia
                    FROM Habilidad 
                    WHERE ID_Trabajador = %s
                    ORDER BY Anos_Experiencia DESC
                """, (trabajador['id'],))
                
                # Filtrar por habilidad si se especificó
                if habilidad:
                    if not habilidades:
                        continue
                    habilidades_match = [h for h in habilidades 
                                       if habilidad.lower() in h['Nombre'].lower()]
                    if not habilidades_match:
                        continue
                
                # Calcular años de experiencia máximos
                anos_exp = 0
                if habilidades:
                    anos_exp = max([h['Anos_Experiencia'] or 0 for h in habilidades])
                
                # Filtrar por experiencia mínima
                if experiencia_min > 0 and anos_exp < experiencia_min:
                    continue
                
                # Obtener calificación promedio
                calificacion_data = execute_query("""
                    SELECT AVG(CAST(Puntuacion AS DECIMAL)) as promedio
                    FROM Calificacion 
                    WHERE ID_Usuario_Receptor = %s
                """, (trabajador['id'],), fetch_one=True)
                
                calificacion = 4.0  # Por defecto
                if calificacion_data and calificacion_data['promedio']:
                    calificacion = float(calificacion_data['promedio'])
                
                # Filtrar por calificación mínima
                if calificacion_min > 0 and calificacion < calificacion_min:
                    continue
                
                # Obtener trabajos completados
                trabajos = execute_query("""
                    SELECT COUNT(*) as total
                    FROM Acuerdo_Laboral 
                    WHERE ID_Trabajador = %s AND Estado = 'Finalizado'
                """, (trabajador['id'],), fetch_one=True)
                
                trabajos_completados = trabajos['total'] if trabajos else 0
                
                trabajador_data = {
                    'id': trabajador['id'],
                    'nombre': trabajador['nombre'],
                    'correo': trabajador['correo'],
                    'telefono': trabajador['telefono'] or 'No disponible',
                    'ubicacion': ubicacion_final,
                    'anos_experiencia': anos_exp,
                    'calificacion': round(calificacion, 1),
                    'trabajos_completados': trabajos_completados,
                    'habilidades': habilidades or []
                }
                
                trabajadores_list.append(trabajador_data)
        
        print(f"✅ Retornando {len(trabajadores_list)} trabajadores después de filtros")
        
        return jsonify({
            'success': True,
            'trabajadores': trabajadores_list,
            'total': len(trabajadores_list)
        })
        
    except Exception as e:
        print(f"❌ Error buscando trabajadores: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


print("✅ Rutas de búsqueda de trabajadores cargadas correctamente")


# ============================================================
# ENDPOINT 3: RECOMENDACIONES
# ============================================================

@trabajadores_bp.route('/api/recomendaciones-empleos', methods=['GET'])
def get_recomendaciones_empleos():
    """Sistema de recomendaciones basado en habilidades"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False}), 401
        
        user_id = session['user_id']
        
        conn = create_connection()
        if not conn:
            return jsonify({'success': False}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Obtener habilidades
        cursor.execute("""
            SELECT Nombre, Clasificacion, Anos_Experiencia
            FROM Habilidad 
            WHERE ID_Trabajador = %s
        """, (user_id,))
        
        habilidades = cursor.fetchall()
        
        if not habilidades:
            cursor.close()
            conn.close()
            return jsonify({
                'success': True,
                'recomendaciones': [],
                'trabajos_completados': 0
            })
        
        # Obtener ofertas disponibles
        cursor.execute("""
            SELECT 
                o.ID_Oferta,
                o.Titulo,
                o.Descripcion,
                o.Pago_Ofrecido,
                o.Fecha_Publicacion,
                u.Nombre,
                u.Apellido
            FROM Oferta_Trabajo o
            JOIN Usuario u ON o.ID_Agricultor = u.ID_Usuario
            WHERE o.Estado IN ('Abierta', 'En Proceso')
            AND o.ID_Oferta NOT IN (
                SELECT ID_Oferta FROM Postulacion WHERE ID_Trabajador = %s
            )
            ORDER BY o.Fecha_Publicacion DESC
            LIMIT 20
        """, (user_id,))
        
        ofertas = cursor.fetchall()
        
        # Calcular compatibilidad
        recomendaciones = []
        
        for oferta in ofertas:
            texto = f"{oferta['Titulo']} {oferta['Descripcion']}".lower()
            match = 50
            razones = []
            habs_req = []
            
            # Buscar habilidades
            for hab in habilidades:
                if hab['Nombre'].lower() in texto:
                    match += 15
                    razones.append(f"Requiere {hab['Nombre']}")
                    habs_req.append(hab['Nombre'])
            
            # Buscar clasificaciones
            for hab in habilidades:
                if hab['Clasificacion'].lower() in texto:
                    match += 10
                    if f"Experiencia en {hab['Clasificacion']}" not in razones:
                        razones.append(f"Experiencia en {hab['Clasificacion']}")
            
            # Experiencia
            exp_total = sum(h['Anos_Experiencia'] for h in habilidades)
            if exp_total >= 3:
                match += 10
                razones.append(f"{exp_total} años de experiencia")
            
            # Ubicación
            ubicacion = 'No especificada'
            if 'ubicación:' in oferta['Descripcion'].lower():
                try:
                    ubicacion = oferta['Descripcion'].split('Ubicación:')[1].split('\n')[0].strip()
                except:
                    pass
            
            match = min(match, 100)
            
            if match >= 50:
                recomendaciones.append({
                    'id_oferta': oferta['ID_Oferta'],
                    'titulo': oferta['Titulo'],
                    'descripcion': oferta['Descripcion'][:300],
                    'pago_ofrecido': float(oferta['Pago_Ofrecido']),
                    'fecha_publicacion': str(oferta['Fecha_Publicacion']),
                    'nombre_agricultor': f"{oferta['Nombre']} {oferta['Apellido']}",
                    'ubicacion': ubicacion,
                    'porcentaje_match': match,
                    'razones_match': razones if razones else ['Compatible con tu perfil'],
                    'habilidades_requeridas': habs_req
                })
        
        recomendaciones.sort(key=lambda x: x['porcentaje_match'], reverse=True)
        
        cursor.close()
        conn.close()
        
        print(f"✅ Generadas {len(recomendaciones)} recomendaciones")
        
        return jsonify({
            'success': True,
            'recomendaciones': recomendaciones,
            'trabajos_completados': 0
        })
        
    except Exception as e:
        print(f"Error recomendaciones: {e}")
        return jsonify({'success': False}), 500


# ============================================================
# ENDPOINT 4: GET USER SKILLS
# ============================================================

@trabajadores_bp.route('/api/get_user_skills', methods=['GET'])
def get_user_skills():
    """Obtener habilidades del usuario"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False}), 401
        
        conn = create_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                ID_Habilidad as id,
                Nombre as nombre,
                Clasificacion as clasificacion,
                Nivel as nivel,
                Anos_Experiencia as anos_experiencia
            FROM Habilidad
            WHERE ID_Trabajador = %s
        """, (session['user_id'],))
        
        skills = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'skills': skills
        })
        
    except Exception as e:
        print(f"Error get_user_skills: {e}")
        return jsonify({'success': False, 'skills': []})


# ============================================================
# ENDPOINT: UPDATE PROFILE (ÚNICA VERSIÓN)
# ============================================================

@trabajadores_bp.route('/api/update-profile', methods=['POST'])
@require_login
def update_profile():
    """Actualizar perfil - Datos básicos en columnas, profesionales en JSON"""
    try:
        data = request.get_json()
        user_id = session['user_id']
        
        print(f"\n{'='*60}")
        print(f"📝 ACTUALIZACIÓN DE PERFIL - Usuario ID: {user_id}")
        print(f"📥 Datos recibidos: {data}")
        
        # Validar datos básicos
        nombre = data.get('nombre', '').strip()
        apellido = data.get('apellido', '').strip()
        
        if not nombre or not apellido:
            return jsonify({
                'success': False, 
                'message': 'Nombre y apellido son requeridos'
            }), 400
        
        # Datos básicos
        telefono = data.get('telefono', '').strip() if data.get('telefono') else None
        red_social = data.get('red_social', '').strip() if data.get('red_social') else None
        
        # Actualizar datos básicos
        execute_query("""
            UPDATE Usuario 
            SET Nombre = %s, Apellido = %s, Telefono = %s, Red_Social = %s
            WHERE ID_Usuario = %s
        """, (nombre, apellido, telefono, red_social, user_id))
        
        # Preparar configuraciones JSON
        import json
        configuraciones = {}
        
        campos_profesionales = {
            'area_trabajo': data.get('area_trabajo'),
            'especializacion': data.get('especializacion'),
            'anos_experiencia': data.get('anos_experiencia'),
            'nivel_educativo': data.get('nivel_educativo'),
            'ubicacion': data.get('ubicacion')
        }
        
        for campo, valor in campos_profesionales.items():
            if valor and str(valor).strip():
                if campo == 'anos_experiencia':
                    try:
                        configuraciones[campo] = int(valor)
                    except:
                        configuraciones[campo] = 0
                else:
                    configuraciones[campo] = str(valor).strip()
        
        # Guardar configuraciones
        if configuraciones:
            json_data = json.dumps(configuraciones, ensure_ascii=False)
            execute_query("""
                UPDATE Usuario 
                SET Configuraciones = %s
                WHERE ID_Usuario = %s
            """, (json_data, user_id))
        
        # Actualizar sesión
        session['first_name'] = nombre
        session['last_name'] = apellido
        session['user_name'] = f"{nombre} {apellido}"
        if telefono:
            session['telefono'] = telefono
        
        print(f"✅ PERFIL ACTUALIZADO EXITOSAMENTE\n")
        
        return jsonify({
            'success': True,
            'message': 'Perfil actualizado correctamente'
        })
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'message': f'Error: {str(e)}'
        }), 500


# ================================================================
# ENDPOINT: ACTUALIZAR DISPONIBILIDAD
# ================================================================
@trabajadores_bp.route('/api/update-availability', methods=['POST'])
def update_availability():
    """Actualiza la disponibilidad del trabajador"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        data = request.get_json()
        user_id = session['user_id']
        
        # Datos de disponibilidad
        available = data.get('available', False)
        visibility = data.get('visibility', 'visible')  # visible, paused, hidden
        days = data.get('days', [])
        start_time = data.get('startTime', '08:00')
        end_time = data.get('endTime', '18:00')
        unavailable_dates = data.get('unavailableDates', [])
        
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="camp"
        )
        cursor = conexion.cursor(dictionary=True)
        
        # Verificar si existe la tabla disponibilidad_trabajador
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS disponibilidad_trabajador (
                id_disponibilidad INT AUTO_INCREMENT PRIMARY KEY,
                id_usuario INT NOT NULL,
                disponible BOOLEAN DEFAULT FALSE,
                visibilidad ENUM('visible', 'paused', 'hidden') DEFAULT 'visible',
                dias_disponibles JSON,
                hora_inicio TIME,
                hora_fin TIME,
                fechas_no_disponibles JSON,
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
                UNIQUE KEY (id_usuario)
            )
        """)
        conexion.commit()
        
        # Preparar datos JSON
        days_json = json.dumps(days)
        unavailable_dates_json = json.dumps(unavailable_dates)
        
        # Validar visibilidad
        valid_visibility = ['visible', 'paused', 'hidden']
        if visibility not in valid_visibility:
            visibility = 'visible'
        
        # Verificar si ya existe un registro para este usuario
        cursor.execute("SELECT id_disponibilidad FROM disponibilidad_trabajador WHERE id_usuario = %s", (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Actualizar registro existente
            query = """
                UPDATE disponibilidad_trabajador 
                SET disponible = %s,
                    visibilidad = %s,
                    dias_disponibles = %s, 
                    hora_inicio = %s, 
                    hora_fin = %s, 
                    fechas_no_disponibles = %s
                WHERE id_usuario = %s
            """
            cursor.execute(query, (available, visibility, days_json, start_time, end_time, unavailable_dates_json, user_id))
        else:
            # Insertar nuevo registro
            query = """
                INSERT INTO disponibilidad_trabajador 
                (id_usuario, disponible, visibilidad, dias_disponibles, hora_inicio, hora_fin, fechas_no_disponibles)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (user_id, available, visibility, days_json, start_time, end_time, unavailable_dates_json))
        
        conexion.commit()
        cursor.close()
        conexion.close()
        
        print(f"✅ Disponibilidad actualizada para usuario ID: {user_id}")
        print(f"   - Disponible: {available}")
        print(f"   - Visibilidad: {visibility}")
        print(f"   - Días: {days}")
        print(f"   - Horario: {start_time} - {end_time}")
        
        return jsonify({
            'success': True,
            'message': 'Disponibilidad actualizada correctamente'
        })
        
    except Exception as e:
        print(f"❌ Error actualizando disponibilidad: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


# ================================================================
# ENDPOINT: OBTENER DISPONIBILIDAD DEL TRABAJADOR
# ================================================================
@trabajadores_bp.route('/api/get-availability', methods=['GET'])
def get_availability():
    """Obtiene la disponibilidad actual del trabajador"""
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
        
        query = """
            SELECT disponible, dias_disponibles, hora_inicio, hora_fin, 
                   fechas_no_disponibles, fecha_actualizacion
            FROM disponibilidad_trabajador
            WHERE id_usuario = %s
        """
        cursor.execute(query, (user_id,))
        availability = cursor.fetchone()
        
        cursor.close()
        conexion.close()
        
        if availability:
            # Parsear JSON
            availability['dias_disponibles'] = json.loads(availability['dias_disponibles']) if availability['dias_disponibles'] else []
            availability['fechas_no_disponibles'] = json.loads(availability['fechas_no_disponibles']) if availability['fechas_no_disponibles'] else []
            
            # Convertir time a string
            if availability['hora_inicio']:
                availability['hora_inicio'] = str(availability['hora_inicio'])
            if availability['hora_fin']:
                availability['hora_fin'] = str(availability['hora_fin'])
            if availability['fecha_actualizacion']:
                availability['fecha_actualizacion'] = availability['fecha_actualizacion'].isoformat()
            
            return jsonify({
                'success': True,
                'availability': availability
            })
        else:
            return jsonify({
                'success': True,
                'availability': None
            })
        
    except Exception as e:
        print(f"❌ Error obteniendo disponibilidad: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


# ================================================================
# ENDPOINT: BUSCAR TRABAJADORES DISPONIBLES
# ================================================================
@trabajadores_bp.route('/api/search-available-workers', methods=['GET'])
def search_available_workers():
    """Busca trabajadores que estén disponibles"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        # Parámetros opcionales
        day = request.args.get('day')  # Día específico (monday, tuesday, etc.)
        date = request.args.get('date')  # Fecha específica
        
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="camp"
        )
        cursor = conexion.cursor(dictionary=True)
        
        query = """
            SELECT u.id_usuario, u.nombre, u.apellido, u.correo, u.telefono, u.url_foto,
                   d.disponible, d.dias_disponibles, d.hora_inicio, d.hora_fin
            FROM usuarios u
            INNER JOIN disponibilidad_trabajador d ON u.id_usuario = d.id_usuario
            WHERE u.rol = 'Trabajador' AND d.disponible = TRUE
        """
        
        cursor.execute(query)
        workers = cursor.fetchall()
        
        # Filtrar por día o fecha si se especifica
        available_workers = []
        for worker in workers:
            dias = json.loads(worker['dias_disponibles']) if worker['dias_disponibles'] else []
            
            # Si se especifica un día, verificar que esté en los días disponibles
            if day and day not in dias:
                continue
            
            worker['dias_disponibles'] = dias
            worker['hora_inicio'] = str(worker['hora_inicio']) if worker['hora_inicio'] else None
            worker['hora_fin'] = str(worker['hora_fin']) if worker['hora_fin'] else None
            
            available_workers.append(worker)
        
        cursor.close()
        conexion.close()
        
        return jsonify({
            'success': True,
            'workers': available_workers,
            'total': len(available_workers)
        })
        
    except Exception as e:
        print(f"❌ Error buscando trabajadores disponibles: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


print("✅ Nuevos endpoints cargados:")
print("   - POST /api/update-language")
print("   - POST /api/update-availability")
print("   - GET  /api/get-availability")
print("   - GET  /api/get-user-settings (actualizado)")
print("   - GET  /api/search-available-workers")


# ENDPOINT 2: ACTUALIZAR DISPONIBILIDAD (nombre único)
@trabajadores_bp.route('/api/actualizar-disponibilidad-trabajador', methods=['POST'])
def actualizar_disponibilidad_trabajador():
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        data = request.get_json()
        user_id = session['user_id']
        
        available = data.get('available', False)
        visibility = data.get('visibility', 'visible')
        days = data.get('days', [])
        start_time = data.get('startTime', '08:00')
        end_time = data.get('endTime', '18:00')
        unavailable_dates = data.get('unavailableDates', [])
        
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="camp"
        )
        cursor = conexion.cursor(dictionary=True)
        
        days_json = json.dumps(days)
        unavailable_dates_json = json.dumps(unavailable_dates)
        
        valid_visibility = ['visible', 'paused', 'hidden']
        if visibility not in valid_visibility:
            visibility = 'visible'
        
        cursor.execute("SELECT ID_Disponibilidad FROM disponibilidad_trabajador WHERE ID_Usuario = %s", (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            query = """
                UPDATE disponibilidad_trabajador 
                SET Disponible = %s,
                    Visibilidad = %s,
                    Dias_Disponibles = %s, 
                    Hora_Inicio = %s, 
                    Hora_Fin = %s, 
                    Fechas_No_Disponibles = %s
                WHERE ID_Usuario = %s
            """
            cursor.execute(query, (available, visibility, days_json, start_time, end_time, unavailable_dates_json, user_id))
        else:
            query = """
                INSERT INTO disponibilidad_trabajador 
                (ID_Usuario, Disponible, Visibilidad, Dias_Disponibles, Hora_Inicio, Hora_Fin, Fechas_No_Disponibles)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (user_id, available, visibility, days_json, start_time, end_time, unavailable_dates_json))
        
        conexion.commit()
        cursor.close()
        conexion.close()
        
        print(f"✅ Disponibilidad actualizada para usuario ID: {user_id}")
        
        return jsonify({'success': True, 'message': 'Disponibilidad actualizada correctamente'})
        
    except Exception as e:
        print(f"❌ Error actualizando disponibilidad: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


# ENDPOINT 3: OBTENER DISPONIBILIDAD (nombre único)
@trabajadores_bp.route('/api/obtener-disponibilidad-trabajador', methods=['GET'])
def obtener_disponibilidad_trabajador():
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
        
        query = """
            SELECT Disponible, Visibilidad, Dias_Disponibles, Hora_Inicio, Hora_Fin, 
                   Fechas_No_Disponibles, Fecha_Actualizacion
            FROM disponibilidad_trabajador
            WHERE ID_Usuario = %s
        """
        cursor.execute(query, (user_id,))
        availability = cursor.fetchone()
        
        cursor.close()
        conexion.close()
        
        if availability:
            availability['Dias_Disponibles'] = json.loads(availability['Dias_Disponibles']) if availability['Dias_Disponibles'] else []
            availability['Fechas_No_Disponibles'] = json.loads(availability['Fechas_No_Disponibles']) if availability['Fechas_No_Disponibles'] else []
            
            if availability['Hora_Inicio']:
                availability['Hora_Inicio'] = str(availability['Hora_Inicio'])
            if availability['Hora_Fin']:
                availability['Hora_Fin'] = str(availability['Hora_Fin'])
            if availability['Fecha_Actualizacion']:
                availability['Fecha_Actualizacion'] = availability['Fecha_Actualizacion'].isoformat()
            
            return jsonify({'success': True, 'availability': availability})
        else:
            return jsonify({'success': True, 'availability': None})
        
    except Exception as e:
        print(f"❌ Error obteniendo disponibilidad: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


# ENDPOINT 5: BUSCAR TRABAJADORES DISPONIBLES (nombre único)
@trabajadores_bp.route('/api/buscar-trabajadores-disponibles', methods=['GET'])
def buscar_trabajadores_disponibles():
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        day = request.args.get('day')
        
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="camp"
        )
        cursor = conexion.cursor(dictionary=True)
        
        query = """
            SELECT u.ID_Usuario, u.Nombre, u.Apellido, u.Correo, u.Telefono, u.URL_Foto,
                   d.Disponible, d.Visibilidad, d.Dias_Disponibles, d.Hora_Inicio, d.Hora_Fin
            FROM Usuario u
            INNER JOIN disponibilidad_trabajador d ON u.ID_Usuario = d.ID_Usuario
            WHERE u.Rol = 'Trabajador' 
            AND d.Disponible = TRUE 
            AND d.Visibilidad = 'visible'
        """
        
        cursor.execute(query)
        workers = cursor.fetchall()
        
        available_workers = []
        for worker in workers:
            dias = json.loads(worker['Dias_Disponibles']) if worker['Dias_Disponibles'] else []
            
            if day and day not in dias:
                continue
            
            worker['Dias_Disponibles'] = dias
            worker['Hora_Inicio'] = str(worker['Hora_Inicio']) if worker['Hora_Inicio'] else None
            worker['Hora_Fin'] = str(worker['Hora_Fin']) if worker['Hora_Fin'] else None
            
            available_workers.append(worker)
        
        cursor.close()
        conexion.close()
        
        return jsonify({
            'success': True,
            'workers': available_workers,
            'total': len(available_workers)
        })
        
    except Exception as e:
        print(f"❌ Error buscando trabajadores: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


print("✅ 5 Endpoints sin conflictos cargados")


# ===================================================================
# ENDPOINT PARA ESTADÍSTICAS DEL TRABAJADOR (MEJORADO)
# ===================================================================
@trabajadores_bp.route('/api/get_worker_stats', methods=['GET'])
def get_worker_stats():
    """Obtener estadísticas del trabajador - MEJORADO"""
    try:
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'message': 'Sesión no válida'
            }), 401
        
        user_id = session['user_id']
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Contar postulaciones totales
        cursor.execute("""
            SELECT COUNT(*) as total 
            FROM Postulacion 
            WHERE ID_Trabajador = %s
        """, (user_id,))
        applications = cursor.fetchone()['total']
        
        # Contar trabajos activos (Aceptados)
        cursor.execute("""
            SELECT COUNT(*) as total 
            FROM Postulacion 
            WHERE ID_Trabajador = %s AND Estado = 'Aceptada'
        """, (user_id,))
        active_jobs = cursor.fetchone()['total']
        
        # Contar trabajos finalizados
        cursor.execute("""
            SELECT COUNT(*) as total 
            FROM Acuerdo_Laboral 
            WHERE ID_Trabajador = %s AND Estado = 'Finalizado'
        """, (user_id,))
        total_jobs = cursor.fetchone()['total']
        
        # Calcular horas totales (estimado: 8 horas por trabajo)
        total_hours = total_jobs * 8
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'applications': applications,
            'active_jobs': active_jobs,
            'total_jobs': total_jobs,
            'total_hours': total_hours
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500

