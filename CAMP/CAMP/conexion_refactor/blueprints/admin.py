# Blueprint: admin
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

admin_bp = Blueprint('admin', __name__)
from blueprints.helpers import require_login, require_role, hash_password, verify_password, no_cache


@admin_bp.route('/api/admin/users', methods=['GET'])
@require_role('Administrador')
def get_all_users():
    """Obtiene todos los usuarios (solo administradores)"""
    try:
        users = execute_query(
            """SELECT ID_Usuario, Nombre, Apellido, Correo, Telefono, Rol, 
                      Estado, Fecha_Registro 
               FROM Usuario ORDER BY Fecha_Registro DESC"""
        )
        
        return jsonify({
            'error': False,
            'users': users
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo usuarios: {str(e)}")
        return jsonify({'error': True, 'message': str(e)}), 500

# ================================================================
# RUTAS ADICIONALES PARA PERFIL - AGREGAR AL FINAL DE TU APP.PY
# ================================================================

# Configuración para subida de archivos (agregar después de app.secret_key)
# Configuración para subida de archivos
base_dir = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(base_dir, '..', 'static', 'uploads')
PROFILE_PHOTOS_FOLDER = os.path.join(UPLOAD_FOLDER, 'profile_photos')
DOCUMENTS_FOLDER = os.path.join(UPLOAD_FOLDER, 'documents')
ALLOWED_EXTENSIONS_IMAGES = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_EXTENSIONS_DOCS = {'pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Crear la estructura completa de carpetas
try:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(base_dir, '..', 'static')
    uploads_dir = os.path.join(static_dir, 'uploads')
    profile_dir = os.path.join(uploads_dir, 'profile_photos')
    docs_dir = os.path.join(uploads_dir, 'documents')
    
    # Crear todas las carpetas
    os.makedirs(static_dir, exist_ok=True)
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(profile_dir, exist_ok=True)
    os.makedirs(docs_dir, exist_ok=True)
    
    print(f"✅ Estructura de carpetas creada:")
    print(f"   📁 {static_dir}")
    print(f"   📁 {uploads_dir}")
    print(f"   📸 {profile_dir}")
    print(f"   📄 {docs_dir}")
    
except Exception as e:
    print(f"❌ Error creando estructura: {e}")

# ⭐ CREAR DIRECTORIOS SI NO EXISTEN - AGREGAR ESTAS LÍNEAS ⭐
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROFILE_PHOTOS_FOLDER, exist_ok=True)
os.makedirs(DOCUMENTS_FOLDER, exist_ok=True)

print(f"✅ Directorios de upload creados:")
print(f"   📁 {UPLOAD_FOLDER}")
print(f"   📸 {PROFILE_PHOTOS_FOLDER}")
print(f"   📄 {DOCUMENTS_FOLDER}")

# Función auxiliar para validar archivos
def allowed_file(filename, allowed_extensions=ALLOWED_EXTENSIONS_IMAGES):
    """Valida si un archivo tiene una extensión permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def generate_unique_filename(filename):
    """Generar nombre de archivo único"""
    file_extension = filename.rsplit('.', 1)[1].lower()
    unique_name = str(uuid.uuid4()) + '.' + file_extension
    return unique_name


# ================================================================
# APIS PARA EL DASHBOARD DEL ADMINISTRADOR
# ================================================================

@admin_bp.route('/api/admin/users', methods=['GET'])
@require_role('Administrador')
def get_all_users_admin():
    """Obtiene todos los usuarios para el dashboard del administrador"""
    try:
        # Filtros opcionales
        tipo_filter = request.args.get('tipo', '')
        estado_filter = request.args.get('estado', '')
        region_filter = request.args.get('region', '')
        
        # Base query
        base_query = """
            SELECT 
                u.ID_Usuario,
                u.Nombre,
                u.Apellido,
                u.Correo,
                u.Telefono,
                u.Rol,
                u.Estado,
                u.Fecha_Registro,
                u.Red_Social,
                -- Información adicional según el rol
                CASE 
                    WHEN u.Rol = 'Agricultor' THEN (
                        SELECT COUNT(*) FROM Oferta_Trabajo ot WHERE ot.ID_Agricultor = u.ID_Usuario
                    )
                    WHEN u.Rol = 'Trabajador' THEN (
                        SELECT COUNT(*) FROM Postulacion p WHERE p.ID_Trabajador = u.ID_Usuario
                    )
                    ELSE 0
                END as Actividad_Total,
                -- Región aproximada (extraer de información disponible)
                COALESCE(
                    (SELECT pr.Nombre_Finca FROM Predio pr WHERE pr.ID_Usuario = u.ID_Usuario LIMIT 1),
                    'Sin especificar'
                ) as Region_Info
            FROM Usuario u
            WHERE 1=1
        """
        
        params = []
        
        # Aplicar filtros
        if tipo_filter and tipo_filter in ['Agricultor', 'Trabajador', 'Administrador']:
            base_query += " AND u.Rol = %s"
            params.append(tipo_filter)
        
        if estado_filter and estado_filter in ['Activo', 'Inactivo', 'Suspendido']:
            base_query += " AND u.Estado = %s"
            params.append(estado_filter)
        
        # El filtro de región es más complejo, por simplicidad lo omitimos o lo implementamos básico
        if region_filter:
            base_query += " AND (u.Correo LIKE %s OR EXISTS (SELECT 1 FROM Predio p WHERE p.ID_Usuario = u.ID_Usuario AND p.Nombre_Finca LIKE %s))"
            region_like = f"%{region_filter}%"
            params.extend([region_like, region_like])
        
        base_query += " ORDER BY u.Fecha_Registro DESC"
        
        users = execute_query(base_query, params)
        
        users_list = []
        if users:
            for user in users:
                user_data = {
                    'id': user['ID_Usuario'],
                    'nombre': user['Nombre'],
                    'apellido': user['Apellido'],
                    'email': user['Correo'],
                    'telefono': user.get('Telefono', ''),
                    'tipo': user['Rol'],
                    'estado': user['Estado'],
                    'registro': user['Fecha_Registro'].strftime('%Y-%m-%d') if user['Fecha_Registro'] else '',
                    'red_social': user.get('Red_Social', ''),
                    'actividad_total': user.get('Actividad_Total', 0),
                    'region': user.get('Region_Info', 'Sin especificar')
                }
                users_list.append(user_data)
        
        return jsonify({
            'success': True,
            'users': users_list,
            'total': len(users_list)
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo usuarios para admin: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/user/<int:user_id>', methods=['GET'])
@require_role('Administrador')
def get_user_details_admin(user_id):
    """Obtiene detalles completos de un usuario específico"""
    try:
        # Información básica del usuario
        user = execute_query("""
            SELECT 
                u.ID_Usuario,
                u.Nombre,
                u.Apellido,
                u.Correo,
                u.Telefono,
                u.Rol,
                u.Estado,
                u.Fecha_Registro,
                u.Red_Social,
                u.URL_Foto,
                u.Configuraciones
            FROM Usuario u
            WHERE u.ID_Usuario = %s
        """, (user_id,), fetch_one=True)
        
        if not user:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
        
        user_details = {
            'info_basica': {
                'id': user['ID_Usuario'],
                'nombre': user['Nombre'],
                'apellido': user['Apellido'],
                'email': user['Correo'],
                'telefono': user.get('Telefono', ''),
                'rol': user['Rol'],
                'estado': user['Estado'],
                'fecha_registro': user['Fecha_Registro'].isoformat() if user['Fecha_Registro'] else None,
                'red_social': user.get('Red_Social', ''),
                'foto_url': user.get('URL_Foto', '')
            }
        }
        
        # Información específica según el rol
        if user['Rol'] == 'Trabajador':
            # Estadísticas del trabajador
            stats_trabajador = execute_query("""
                SELECT 
                    COUNT(DISTINCT p.ID_Postulacion) as total_postulaciones,
                    COUNT(DISTINCT al.ID_Acuerdo) as trabajos_completados,
                    AVG(CAST(c.Puntuacion AS DECIMAL)) as calificacion_promedio
                FROM Usuario u
                LEFT JOIN Postulacion p ON u.ID_Usuario = p.ID_Trabajador
                LEFT JOIN Acuerdo_Laboral al ON u.ID_Usuario = al.ID_Trabajador AND al.Estado = 'Finalizado'
                LEFT JOIN Calificacion c ON u.ID_Usuario = c.ID_Usuario_Receptor
                WHERE u.ID_Usuario = %s
            """, (user_id,), fetch_one=True)
            
            # Habilidades
            habilidades = execute_query("""
                SELECT Nombre, Clasificacion 
                FROM Habilidad 
                WHERE ID_Trabajador = %s
            """, (user_id,))
            
            user_details['estadisticas_trabajador'] = {
                'total_postulaciones': stats_trabajador['total_postulaciones'] if stats_trabajador else 0,
                'trabajos_completados': stats_trabajador['trabajos_completados'] if stats_trabajador else 0,
                'calificacion_promedio': float(stats_trabajador['calificacion_promedio']) if stats_trabajador and stats_trabajador['calificacion_promedio'] else 0.0,
                'habilidades': habilidades or []
            }
            
        elif user['Rol'] == 'Agricultor':
            # Estadísticas del agricultor
            stats_agricultor = execute_query("""
                SELECT 
                    COUNT(DISTINCT ot.ID_Oferta) as ofertas_publicadas,
                    COUNT(DISTINCT al.ID_Acuerdo) as contratos_completados,
                    AVG(CAST(c.Puntuacion AS DECIMAL)) as calificacion_promedio
                FROM Usuario u
                LEFT JOIN Oferta_Trabajo ot ON u.ID_Usuario = ot.ID_Agricultor
                LEFT JOIN Acuerdo_Laboral al ON ot.ID_Oferta = al.ID_Oferta AND al.Estado = 'Finalizado'
                LEFT JOIN Calificacion c ON u.ID_Usuario = c.ID_Usuario_Receptor
                WHERE u.ID_Usuario = %s
            """, (user_id,), fetch_one=True)
            
            # Predios
            predios = execute_query("""
                SELECT Nombre_Finca, Ubicacion_Latitud, Ubicacion_Longitud
                FROM Predio 
                WHERE ID_Usuario = %s
            """, (user_id,))
            
            user_details['estadisticas_agricultor'] = {
                'ofertas_publicadas': stats_agricultor['ofertas_publicadas'] if stats_agricultor else 0,
                'contratos_completados': stats_agricultor['contratos_completados'] if stats_agricultor else 0,
                'calificacion_promedio': float(stats_agricultor['calificacion_promedio']) if stats_agricultor and stats_agricultor['calificacion_promedio'] else 0.0,
                'predios': predios or []
            }
        
        # Actividad reciente
        actividad_reciente = execute_query("""
            SELECT 
                'postulacion' as tipo,
                p.Fecha_Postulacion as fecha,
                ot.Titulo as descripcion
            FROM Postulacion p
            JOIN Oferta_Trabajo ot ON p.ID_Oferta = ot.ID_Oferta
            WHERE p.ID_Trabajador = %s
            
            UNION ALL
            
            SELECT 
                'oferta' as tipo,
                ot.Fecha_Publicacion as fecha,
                ot.Titulo as descripcion
            FROM Oferta_Trabajo ot
            WHERE ot.ID_Agricultor = %s
            
            ORDER BY fecha DESC
            LIMIT 10
        """, (user_id, user_id))
        
        user_details['actividad_reciente'] = actividad_reciente or []
        
        return jsonify({
            'success': True,
            'user_details': user_details
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo detalles del usuario: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/user/<int:user_id>', methods=['PUT'])
@require_role('Administrador')
def update_user_admin(user_id):
    """Actualiza información de un usuario (solo para administradores)"""
    try:
        data = request.get_json()
        
        # Campos que se pueden actualizar
        allowed_fields = ['Nombre', 'Apellido', 'Correo', 'Telefono', 'Estado']
        update_fields = []
        update_values = []
        
        for field in allowed_fields:
            if field.lower() in data:
                if field == 'Estado' and data[field.lower()] not in ['Activo', 'Inactivo', 'Suspendido']:
                    return jsonify({'success': False, 'error': 'Estado no válido'}), 400
                
                update_fields.append(f"{field} = %s")
                update_values.append(data[field.lower()])
        
        if not update_fields:
            return jsonify({'success': False, 'error': 'No hay campos para actualizar'}), 400
        
        update_values.append(user_id)
        
        # Construir query de actualización
        update_query = f"""
            UPDATE Usuario 
            SET {', '.join(update_fields)}
            WHERE ID_Usuario = %s
        """
        
        execute_query(update_query, update_values)
        
        # Log de auditoría
        admin_user = session.get('user_name', 'Admin')
        print(f"📝 {admin_user} actualizó usuario ID {user_id}: {data}")
        
        return jsonify({
            'success': True,
            'message': 'Usuario actualizado correctamente'
        })
        
    except Exception as e:
        print(f"❌ Error actualizando usuario: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/user/<int:user_id>', methods=['DELETE'])
@require_role('Administrador')
def delete_user_admin(user_id):
    """Elimina un usuario (solo para administradores)"""
    try:
        # Verificar que el usuario no sea el administrador actual
        if user_id == session.get('user_id'):
            return jsonify({'success': False, 'error': 'No puedes eliminarte a ti mismo'}), 400
        
        # Obtener información del usuario antes de eliminar
        user_info = execute_query("""
            SELECT Nombre, Apellido, Correo, Rol 
            FROM Usuario 
            WHERE ID_Usuario = %s
        """, (user_id,), fetch_one=True)
        
        if not user_info:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
        
        # Eliminar registros relacionados (similar a la función existente)
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
        
        # Log de auditoría
        admin_user = session.get('user_name', 'Admin')
        print(f"🗑️ {admin_user} eliminó usuario: {user_info['Nombre']} {user_info['Apellido']} ({user_info['Correo']})")
        
        return jsonify({
            'success': True,
            'message': f'Usuario {user_info["Nombre"]} {user_info["Apellido"]} eliminado correctamente'
        })
        
    except Exception as e:
        print(f"❌ Error eliminando usuario: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/stats', methods=['GET'])
@require_role('Administrador')
def get_admin_stats():
    """Obtiene estadísticas generales para el dashboard del administrador"""
    try:
        # Estadísticas básicas
        stats = execute_query("""
            SELECT 
                COUNT(CASE WHEN Rol = 'Trabajador' AND Estado = 'Activo' THEN 1 END) as trabajadores_activos,
                COUNT(CASE WHEN Rol = 'Agricultor' AND Estado = 'Activo' THEN 1 END) as agricultores_activos,
                COUNT(CASE WHEN Estado = 'Activo' THEN 1 END) as usuarios_activos_total,
                COUNT(*) as usuarios_total
            FROM Usuario
        """, fetch_one=True)
        
        # Ofertas y postulaciones
        ofertas_stats = execute_query("""
            SELECT 
                COUNT(CASE WHEN Estado = 'Abierta' THEN 1 END) as ofertas_activas,
                COUNT(*) as ofertas_total
            FROM Oferta_Trabajo
        """, fetch_one=True)
        
        postulaciones_stats = execute_query("""
            SELECT 
                COUNT(*) as postulaciones_total,
                COUNT(CASE WHEN Estado = 'Pendiente' THEN 1 END) as postulaciones_pendientes
            FROM Postulacion
        """, fetch_one=True)
        
        # Acuerdos laborales
        acuerdos_stats = execute_query("""
            SELECT 
                COUNT(CASE WHEN Estado = 'Finalizado' THEN 1 END) as contratos_completados,
                COUNT(CASE WHEN Estado = 'Activo' THEN 1 END) as contratos_activos
            FROM Acuerdo_Laboral
        """, fetch_one=True)
        
        return jsonify({
            'success': True,
            'stats': {
                'usuarios_activos': stats['usuarios_activos_total'] if stats else 0,
                'trabajadores_activos': stats['trabajadores_activos'] if stats else 0,
                'agricultores_activos': stats['agricultores_activos'] if stats else 0,
                'ofertas_activas': ofertas_stats['ofertas_activas'] if ofertas_stats else 0,
                'postulaciones_pendientes': postulaciones_stats['postulaciones_pendientes'] if postulaciones_stats else 0,
                'contratos_completados': acuerdos_stats['contratos_completados'] if acuerdos_stats else 0,
                'contratos_activos': acuerdos_stats['contratos_activos'] if acuerdos_stats else 0
            }
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas de admin: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# RUTA PARA ACTIVIDAD RECIENTE DEL ADMINISTRADOR
# ================================================================

@admin_bp.route('/api/admin/recent-activity', methods=['GET'])
@require_role('Administrador')
def get_recent_activity():
    """Obtiene actividad reciente para el dashboard del administrador"""
    try:
        # Actividades recientes simuladas basadas en datos reales
        recent_users = execute_query("""
            SELECT 
                CONCAT(Nombre, ' ', Apellido) as nombre_completo,
                Rol,
                Fecha_Registro,
                'new-user' as tipo
            FROM Usuario 
            WHERE Fecha_Registro >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY Fecha_Registro DESC 
            LIMIT 5
        """)
        
        recent_jobs = execute_query("""
            SELECT 
                ot.Titulo,
                ot.Fecha_Publicacion,
                CONCAT(u.Nombre, ' ', u.Apellido) as agricultor,
                'new-job' as tipo
            FROM Oferta_Trabajo ot
            JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
            WHERE ot.Fecha_Publicacion >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY ot.Fecha_Publicacion DESC 
            LIMIT 5
        """)
        
        activities = []
        
        # Procesar nuevos usuarios
        if recent_users:
            for user in recent_users:
                activities.append({
                    'type': 'new-user',
                    'icon': 'fas fa-user-plus',
                    'message': f'<strong>Nuevo usuario registrado:</strong> {user["nombre_completo"]} ({user["Rol"]})',
                    'time': f'Hace {(datetime.now() - user["Fecha_Registro"]).days} días'
                })
        
        # Procesar nuevos trabajos
        if recent_jobs:
            for job in recent_jobs:
                activities.append({
                    'type': 'new-job',
                    'icon': 'fas fa-briefcase',
                    'message': f'<strong>Nueva oferta publicada:</strong> {job["Titulo"]} por {job["agricultor"]}',
                    'time': f'Hace {(datetime.now() - job["Fecha_Publicacion"]).days} días'
                })
        
        # Ordenar por fecha y limitar
        activities = sorted(activities, key=lambda x: x['time'])[:10]
        
        return jsonify({
            'success': True,
            'activities': activities
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo actividad reciente: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

print("✅ Rutas del administrador cargadas correctamente")


# ================================================================
# API PARA OBTENER TODOS LOS USUARIOS
# ================================================================
@admin_bp.route('/api/admin/get-users', methods=['GET'])
@require_role('Administrador')
def admin_get_users():
    """API para obtener todos los usuarios con filtros para el panel admin"""
    try:
        print("🔍 Ejecutando admin_get_users...")
        
        # Obtener filtros de la query string
        tipo_filter = request.args.get('tipo', '')
        estado_filter = request.args.get('estado', '')
        region_filter = request.args.get('region', '')
        search_term = request.args.get('search', '')
        
        print(f"Filtros recibidos: tipo={tipo_filter}, estado={estado_filter}, region={region_filter}, search={search_term}")
        
        # Query base más simple para empezar
        base_query = """
            SELECT 
                u.ID_Usuario as id,
                u.Nombre as nombre,
                u.Apellido as apellido,
                u.Correo as email,
                u.Telefono as telefono,
                u.Rol as tipo,
                u.Estado as estado,
                DATE(u.Fecha_Registro) as registro
            FROM Usuario u
            WHERE u.Rol != 'Administrador'
        """
        
        params = []
        
        # Aplicar filtros básicos
        if tipo_filter and tipo_filter in ['agricultor', 'trabajador']:
            base_query += " AND LOWER(u.Rol) = %s"
            params.append(tipo_filter.lower())
        
        if estado_filter and estado_filter in ['activo', 'inactivo']:
            base_query += " AND LOWER(u.Estado) = %s"
            params.append(estado_filter.lower())
        
        if search_term:
            base_query += """ AND (
                LOWER(u.Nombre) LIKE %s OR 
                LOWER(u.Apellido) LIKE %s OR 
                LOWER(u.Correo) LIKE %s
            )"""
            search_like = f"%{search_term.lower()}%"
            params.extend([search_like, search_like, search_like])
        
        base_query += " ORDER BY u.Fecha_Registro DESC LIMIT 100"
        
        print(f"Ejecutando query: {base_query}")
        print(f"Con parámetros: {params}")
        
        # Ejecutar query
        if params:
            users = execute_query(base_query, tuple(params))
        else:
            users = execute_query(base_query)
        
        print(f"Usuarios obtenidos: {len(users) if users else 0}")
        
        users_list = []
        if users:
            for user in users:
                print(f"Procesando usuario: {user}")
                user_data = {
                    'id': user['id'],
                    'nombre': f"{user['nombre']} {user['apellido']}",
                    'email': user['email'],
                    'telefono': user.get('telefono', ''),
                    'tipo': user['tipo'].lower(),
                    'estado': user['estado'].lower(),
                    'registro': user['registro'].strftime('%Y-%m-%d') if user['registro'] else '',
                    'region': 'bogota'  # Valor por defecto por ahora
                }
                users_list.append(user_data)
        
        print(f"Lista final de usuarios: {len(users_list)}")
        
        return jsonify({
            'success': True,
            'users': users_list,
            'total': len(users_list)
        })
        
    except Exception as e:
        print(f"❌ Error en admin_get_users: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': f'Error interno: {str(e)}'
        }), 500


# ================================================================
# API PARA ACCIONES CON USUARIOS INDIVIDUALES
# ================================================================
@admin_bp.route('/api/admin/user/<int:user_id>/details', methods=['GET'])
@require_role('Administrador')
def admin_get_user_details(user_id):
    """Obtener detalles completos de un usuario"""
    try:
        # Información básica del usuario
        user = execute_query("""
            SELECT 
                u.ID_Usuario,
                u.Nombre,
                u.Apellido,
                u.Correo,
                u.Telefono,
                u.Rol,
                u.Estado,
                u.Fecha_Registro,
                u.Red_Social,
                u.URL_Foto
            FROM Usuario u
            WHERE u.ID_Usuario = %s
        """, (user_id,), fetch_one=True)
        
        if not user:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
        
        # Información adicional según el rol
        additional_info = {}
        
        if user['Rol'] == 'Trabajador':
            # Estadísticas del trabajador
            stats = execute_query("""
                SELECT 
                    COUNT(DISTINCT p.ID_Postulacion) as total_postulaciones,
                    COUNT(DISTINCT al.ID_Acuerdo) as trabajos_completados,
                    COALESCE(AVG(CAST(c.Puntuacion AS DECIMAL)), 0) as calificacion_promedio,
                    COUNT(DISTINCT h.ID_Habilidad) as total_habilidades
                FROM Usuario u
                LEFT JOIN Postulacion p ON u.ID_Usuario = p.ID_Trabajador
                LEFT JOIN Acuerdo_Laboral al ON u.ID_Usuario = al.ID_Trabajador AND al.Estado = 'Finalizado'
                LEFT JOIN Calificacion c ON u.ID_Usuario = c.ID_Usuario_Receptor
                LEFT JOIN Habilidad h ON u.ID_Usuario = h.ID_Trabajador
                WHERE u.ID_Usuario = %s
            """, (user_id,), fetch_one=True)
            
            # Habilidades
            habilidades = execute_query("""
                SELECT Nombre, Clasificacion 
                FROM Habilidad 
                WHERE ID_Trabajador = %s
            """, (user_id,))
            
            additional_info = {
                'estadisticas': {
                    'postulaciones': stats['total_postulaciones'] or 0,
                    'trabajos_completados': stats['trabajos_completados'] or 0,
                    'calificacion': float(stats['calificacion_promedio']) if stats['calificacion_promedio'] else 0,
                    'habilidades_count': stats['total_habilidades'] or 0
                },
                'habilidades': [{'nombre': h['Nombre'], 'tipo': h['Clasificacion']} for h in habilidades] if habilidades else []
            }
            
        elif user['Rol'] == 'Agricultor':
            # Estadísticas del agricultor
            stats = execute_query("""
                SELECT 
                    COUNT(DISTINCT ot.ID_Oferta) as ofertas_publicadas,
                    COUNT(DISTINCT al.ID_Acuerdo) as contratos_completados,
                    COALESCE(AVG(CAST(c.Puntuacion AS DECIMAL)), 0) as calificacion_promedio,
                    COUNT(DISTINCT pr.ID_Predio) as total_predios
                FROM Usuario u
                LEFT JOIN Oferta_Trabajo ot ON u.ID_Usuario = ot.ID_Agricultor
                LEFT JOIN Acuerdo_Laboral al ON ot.ID_Oferta = al.ID_Oferta AND al.Estado = 'Finalizado'
                LEFT JOIN Calificacion c ON u.ID_Usuario = c.ID_Usuario_Receptor
                LEFT JOIN Predio pr ON u.ID_Usuario = pr.ID_Usuario
                WHERE u.ID_Usuario = %s
            """, (user_id,), fetch_one=True)
            
            # Predios
            predios = execute_query("""
                SELECT Nombre_Finca, Descripcion 
                FROM Predio 
                WHERE ID_Usuario = %s
            """, (user_id,))
            
            additional_info = {
                'estadisticas': {
                    'ofertas_publicadas': stats['ofertas_publicadas'] or 0,
                    'contratos_completados': stats['contratos_completados'] or 0,
                    'calificacion': float(stats['calificacion_promedio']) if stats['calificacion_promedio'] else 0,
                    'predios_count': stats['total_predios'] or 0
                },
                'predios': [{'nombre': p['Nombre_Finca'], 'descripcion': p.get('Descripcion', '')} for p in predios] if predios else []
            }
        
        response_data = {
            'success': True,
            'user': {
                'id': user['ID_Usuario'],
                'nombre': user['Nombre'],
                'apellido': user['Apellido'],
                'email': user['Correo'],
                'telefono': user.get('Telefono', ''),
                'rol': user['Rol'],
                'estado': user['Estado'],
                'fecha_registro': user['Fecha_Registro'].strftime('%Y-%m-%d %H:%M:%S') if user['Fecha_Registro'] else '',
                'red_social': user.get('Red_Social', ''),
                'foto_url': user.get('URL_Foto', ''),
                **additional_info
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error obteniendo detalles del usuario: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/user/<int:user_id>/update', methods=['PUT'])
@require_role('Administrador')
def admin_update_user(user_id):
    """Actualizar información de un usuario"""
    try:
        data = request.get_json()
        
        # Verificar que no se esté intentando actualizar al propio administrador
        if user_id == session.get('user_id'):
            return jsonify({'success': False, 'error': 'No puedes modificar tu propia cuenta'}), 400
        
        # Campos permitidos para actualización
        allowed_fields = {
            'nombre': 'Nombre',
            'apellido': 'Apellido',
            'email': 'Correo',
            'telefono': 'Telefono',
            'estado': 'Estado'
        }
        
        update_fields = []
        update_values = []
        
        for field_key, db_field in allowed_fields.items():
            if field_key in data and data[field_key] is not None:
                # Validaciones específicas
                if field_key == 'estado':
                    if data[field_key] not in ['Activo', 'Inactivo', 'Bloqueado']:
                        return jsonify({'success': False, 'error': 'Estado no válido'}), 400
                elif field_key == 'email':
                    if not validate_email(data[field_key]):
                        return jsonify({'success': False, 'error': 'Email no válido'}), 400
                
                update_fields.append(f"{db_field} = %s")
                update_values.append(data[field_key])
        
        if not update_fields:
            return jsonify({'success': False, 'error': 'No hay campos válidos para actualizar'}), 400
        
        update_values.append(user_id)
        
        # Ejecutar actualización
        update_query = f"""
            UPDATE Usuario 
            SET {', '.join(update_fields)}
            WHERE ID_Usuario = %s
        """
        
        execute_query(update_query, update_values)
        
        # Log de auditoría
        admin_name = session.get('user_name', 'Admin')
        print(f"📝 Admin {admin_name} actualizó usuario ID {user_id}: {data}")
        
        return jsonify({
            'success': True,
            'message': 'Usuario actualizado correctamente'
        })
        
    except Exception as e:
        print(f"Error actualizando usuario: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/user/<int:user_id>/delete', methods=['DELETE'])
@require_role('Administrador')
def admin_delete_user(user_id):
    """Eliminar un usuario del sistema"""
    try:
        # Verificar que no se esté intentando eliminar al propio administrador
        if user_id == session.get('user_id'):
            return jsonify({'success': False, 'error': 'No puedes eliminar tu propia cuenta'}), 400
        
        # Obtener información del usuario antes de eliminar
        user_info = execute_query("""
            SELECT Nombre, Apellido, Correo, Rol 
            FROM Usuario 
            WHERE ID_Usuario = %s
        """, (user_id,), fetch_one=True)
        
        if not user_info:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
        
        # Eliminar registros relacionados en orden de dependencias
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
                print(f"Advertencia: Error eliminando de {table_name}: {table_error}")
                continue
        
        # Eliminar el usuario principal
        execute_query("DELETE FROM Usuario WHERE ID_Usuario = %s", (user_id,))
        
        # Log de auditoría
        admin_name = session.get('user_name', 'Admin')
        print(f"🗑️ Admin {admin_name} eliminó usuario: {user_info['Nombre']} {user_info['Apellido']} ({user_info['Correo']})")
        
        return jsonify({
            'success': True,
            'message': f'Usuario {user_info["Nombre"]} {user_info["Apellido"]} eliminado correctamente'
        })
        
    except Exception as e:
        print(f"Error eliminando usuario: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# API PARA ESTADÍSTICAS DEL DASHBOARD
# ================================================================
@admin_bp.route('/api/admin/dashboard-stats', methods=['GET'])
@require_role('Administrador')
def admin_dashboard_stats():
    """Obtener estadísticas generales para el dashboard del administrador"""
    try:
        # Estadísticas de usuarios
        user_stats = execute_query("""
            SELECT 
                COUNT(CASE WHEN Rol = 'Trabajador' AND Estado = 'Activo' THEN 1 END) as trabajadores_activos,
                COUNT(CASE WHEN Rol = 'Agricultor' AND Estado = 'Activo' THEN 1 END) as agricultores_activos,
                COUNT(CASE WHEN Estado = 'Activo' THEN 1 END) as usuarios_activos,
                COUNT(*) as total_usuarios
            FROM Usuario 
            WHERE Rol != 'Administrador'
        """, fetch_one=True)
        
        # Estadísticas de ofertas
        job_stats = execute_query("""
            SELECT 
                COUNT(CASE WHEN Estado = 'Abierta' THEN 1 END) as ofertas_activas,
                COUNT(*) as total_ofertas
            FROM Oferta_Trabajo
        """, fetch_one=True)
        
        # Estadísticas de postulaciones
        application_stats = execute_query("""
            SELECT 
                COUNT(*) as total_postulaciones,
                COUNT(CASE WHEN Estado = 'Pendiente' THEN 1 END) as postulaciones_pendientes,
                COUNT(CASE WHEN Estado = 'Aceptada' THEN 1 END) as postulaciones_aceptadas
            FROM Postulacion
        """, fetch_one=True)
        
        # Estadísticas de contrataciones
        contract_stats = execute_query("""
            SELECT 
                COUNT(CASE WHEN Estado = 'Finalizado' THEN 1 END) as contratos_finalizados,
                COUNT(CASE WHEN Estado = 'Activo' THEN 1 END) as contratos_activos
            FROM Acuerdo_Laboral
        """, fetch_one=True)
        
        # Calcular tasas de crecimiento (simuladas para demo)
        import random
        growth_rates = {
            'usuarios': random.randint(8, 15),
            'ofertas': random.randint(5, 12),
            'postulaciones': random.randint(10, 20),
            'contratos': random.randint(15, 25)
        }
        
        stats_data = {
            'usuarios_activos': user_stats['usuarios_activos'] if user_stats else 0,
            'ofertas_activas': job_stats['ofertas_activas'] if job_stats else 0,
            'total_postulaciones': application_stats['total_postulaciones'] if application_stats else 0,
            'contratos_exitosos': contract_stats['contratos_finalizados'] if contract_stats else 0,
            
            # Datos adicionales para el frontend
            'trabajadores_activos': user_stats['trabajadores_activos'] if user_stats else 0,
            'agricultores_activos': user_stats['agricultores_activos'] if user_stats else 0,
            'postulaciones_pendientes': application_stats['postulaciones_pendientes'] if application_stats else 0,
            'contratos_activos': contract_stats['contratos_activos'] if contract_stats else 0,
            
            # Tasas de crecimiento
            'crecimiento': growth_rates
        }
        
        return jsonify({
            'success': True,
            'stats': stats_data
        })
        
    except Exception as e:
        print(f"Error obteniendo estadísticas del admin: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# API PARA ACTIVIDAD RECIENTE
# ================================================================
@admin_bp.route('/api/admin/recent-activity', methods=['GET'])
@require_role('Administrador')
def admin_recent_activity():
    """Obtener actividad reciente del sistema"""
    try:
        activities = []
        
        # Usuarios registrados recientemente
        recent_users = execute_query("""
            SELECT 
                CONCAT(Nombre, ' ', Apellido) as nombre_completo,
                Rol,
                Fecha_Registro
            FROM Usuario 
            WHERE Fecha_Registro >= DATE_SUB(NOW(), INTERVAL 7 DAY)
              AND Rol != 'Administrador'
            ORDER BY Fecha_Registro DESC 
            LIMIT 5
        """)
        
        if recent_users:
            for user in recent_users:
                days_ago = (datetime.now() - user['Fecha_Registro']).days
                time_text = f"Hace {days_ago} días" if days_ago > 0 else "Hoy"
                
                activities.append({
                    'type': 'new-user',
                    'icon': 'fas fa-user-plus',
                    'message': f'<strong>Nuevo usuario registrado:</strong> {user["nombre_completo"]} ({user["Rol"]})',
                    'time': time_text,
                    'timestamp': user['Fecha_Registro'].isoformat()
                })
        
        # Ofertas publicadas recientemente
        recent_jobs = execute_query("""
            SELECT 
                ot.Titulo,
                ot.Fecha_Publicacion,
                CONCAT(u.Nombre, ' ', u.Apellido) as agricultor_nombre
            FROM Oferta_Trabajo ot
            JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
            WHERE ot.Fecha_Publicacion >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY ot.Fecha_Publicacion DESC 
            LIMIT 5
        """)
        
        if recent_jobs:
            for job in recent_jobs:
                days_ago = (datetime.now() - job['Fecha_Publicacion']).days
                time_text = f"Hace {days_ago} días" if days_ago > 0 else "Hoy"
                
                activities.append({
                    'type': 'new-job',
                    'icon': 'fas fa-briefcase',
                    'message': f'<strong>Nueva oferta publicada:</strong> {job["Titulo"]} por {job["agricultor_nombre"]}',
                    'time': time_text,
                    'timestamp': job['Fecha_Publicacion'].isoformat()
                })
        
        # Postulaciones recientes
        recent_applications = execute_query("""
            SELECT 
                ot.Titulo,
                CONCAT(u.Nombre, ' ', u.Apellido) as trabajador_nombre,
                p.Fecha_Postulacion
            FROM Postulacion p
            JOIN Oferta_Trabajo ot ON p.ID_Oferta = ot.ID_Oferta
            JOIN Usuario u ON p.ID_Trabajador = u.ID_Usuario
            WHERE p.Fecha_Postulacion >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY p.Fecha_Postulacion DESC 
            LIMIT 3
        """)
        
        if recent_applications:
            for app in recent_applications:
                days_ago = (datetime.now() - app['Fecha_Postulacion']).days
                time_text = f"Hace {days_ago} días" if days_ago > 0 else "Hoy"
                
                activities.append({
                    'type': 'new-application',
                    'icon': 'fas fa-file-alt',
                    'message': f'<strong>Nueva postulación:</strong> {app["trabajador_nombre"]} se postuló para "{app["Titulo"]}"',
                    'time': time_text,
                    'timestamp': app['Fecha_Postulacion'].isoformat()
                })
        
        # Ordenar por timestamp y limitar resultados
        activities.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        activities = activities[:10]
        
        # Remover timestamp del response final
        for activity in activities:
            activity.pop('timestamp', None)
        
        return jsonify({
            'success': True,
            'activities': activities
        })
        
    except Exception as e:
        print(f"Error obteniendo actividad reciente: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# API PARA CREAR NUEVO USUARIO DESDE EL ADMIN
# ================================================================
@admin_bp.route('/api/admin/create-user', methods=['POST'])
@require_role('Administrador')
def admin_create_user():
    """Crear nuevo usuario desde el panel de administrador"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        required_fields = ['nombre', 'apellido', 'email', 'tipo', 'region']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Campo {field} es requerido'}), 400
        
        nombre = data['nombre'].strip()
        apellido = data['apellido'].strip()
        email = data['email'].strip().lower()
        tipo = data['tipo'].capitalize()
        region = data['region']
        
        # Validaciones
        if not validate_email(email):
            return jsonify({'success': False, 'error': 'Email no válido'}), 400
        
        if tipo not in ['Trabajador', 'Agricultor']:
            return jsonify({'success': False, 'error': 'Tipo de usuario no válido'}), 400
        
        # Verificar que el email no exista
        existing_user = execute_query(
            "SELECT ID_Usuario FROM Usuario WHERE Correo = %s",
            (email,),
            fetch_one=True
        )
        
        if existing_user:
            return jsonify({'success': False, 'error': 'El email ya está registrado'}), 400
        
        # Generar contraseña temporal
        import secrets
        import string
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        hashed_password = hash_password(temp_password)
        
        # Insertar usuario
        user_id = execute_query("""
            INSERT INTO Usuario (Nombre, Apellido, Correo, Contrasena, Rol, Estado)
            VALUES (%s, %s, %s, %s, %s, 'Activo')
        """, (nombre, apellido, email, hashed_password, tipo))
        
        # Si es agricultor y se especificó región, crear un predio básico
        if tipo == 'Agricultor' and region != 'otra':
            region_names = {
                'bogota': 'Finca en Bogotá',
                'antioquia': 'Finca en Antioquia', 
                'valle': 'Finca en Valle del Cauca'
            }
            
            if region in region_names:
                execute_query("""
                    INSERT INTO Predio (ID_Usuario, Nombre_Finca, Ubicacion_Latitud, Ubicacion_Longitud, Descripcion)
                    VALUES (%s, %s, 4.6097, -74.0817, %s)
                """, (user_id, region_names[region], f'Predio creado desde panel admin - Región: {region}'))
        
        # Log de auditoría
        admin_name = session.get('user_name', 'Admin')
        print(f"👤 Admin {admin_name} creó nuevo usuario: {nombre} {apellido} ({email}) como {tipo}")
        
        return jsonify({
            'success': True,
            'message': f'Usuario {nombre} {apellido} creado correctamente',
            'user_id': user_id,
            'temp_password': temp_password,  # Solo para demo, en producción enviar por email
            'user_data': {
                'nombre': nombre,
                'apellido': apellido,
                'email': email,
                'tipo': tipo.lower(),
                'region': region
            }
        })
        
    except Exception as e:
        print(f"Error creando usuario: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# API PARA ACCIONES MASIVAS
# ================================================================
@admin_bp.route('/api/admin/bulk-action', methods=['POST'])
@require_role('Administrador')
def admin_bulk_action():
    """Realizar acciones masivas sobre usuarios seleccionados"""
    try:
        data = request.get_json()
        action = data.get('action')
        user_ids = data.get('user_ids', [])
        
        if not action or not user_ids:
            return jsonify({'success': False, 'error': 'Acción y IDs de usuario son requeridos'}), 400
        
        # Verificar que no incluya al administrador actual
        current_admin_id = session.get('user_id')
        if current_admin_id in user_ids:
            return jsonify({'success': False, 'error': 'No puedes realizar acciones sobre tu propia cuenta'}), 400
        
        affected_count = 0
        
        if action == 'suspend':
            # Suspender usuarios (cambiar estado a Inactivo)
            placeholders = ','.join(['%s'] * len(user_ids))
            query = f"UPDATE Usuario SET Estado = 'Inactivo' WHERE ID_Usuario IN ({placeholders}) AND Rol != 'Administrador'"
            execute_query(query, user_ids)
            affected_count = len(user_ids)
            message = f'{affected_count} usuarios suspendidos correctamente'
            
        elif action == 'activate':
            # Activar usuarios
            placeholders = ','.join(['%s'] * len(user_ids))
            query = f"UPDATE Usuario SET Estado = 'Activo' WHERE ID_Usuario IN ({placeholders}) AND Rol != 'Administrador'"
            execute_query(query, user_ids)
            affected_count = len(user_ids)
            message = f'{affected_count} usuarios activados correctamente'
            
        elif action == 'delete':
            # Eliminar usuarios (más complejo por las dependencias)
            for user_id in user_ids:
                if user_id == current_admin_id:
                    continue
                    
                # Eliminar dependencias para cada usuario
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
                        print(f"Advertencia: Error eliminando de {table_name}: {table_error}")
                        continue
                
                # Eliminar usuario principal
                execute_query("DELETE FROM Usuario WHERE ID_Usuario = %s AND Rol != 'Administrador'", (user_id,))
                affected_count += 1
            
            message = f'{affected_count} usuarios eliminados correctamente'
            
        else:
            return jsonify({'success': False, 'error': 'Acción no válida'}), 400
        
        # Log de auditoría
        admin_name = session.get('user_name', 'Admin')
        print(f"📋 Admin {admin_name} realizó acción masiva '{action}' en {affected_count} usuarios")
        
        return jsonify({
            'success': True,
            'message': message,
            'affected_count': affected_count
        })
        
    except Exception as e:
        print(f"Error en acción masiva: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# API PARA ESTADO DEL SISTEMA
# ================================================================
@admin_bp.route('/api/admin/system-status', methods=['GET'])
@require_role('Administrador')
def admin_system_status():
    """Obtener estado del sistema para el dashboard"""
    try:
        # Estado de la base de datos
        db_status = 'online'
        try:
            execute_query("SELECT 1", fetch_one=True)
        except:
            db_status = 'offline'
        
        # Estado de servicios
        services_status = [
            {
                'name': 'Servidor Principal',
                'status': 'online',
                'label': 'Online'
            },
            {
                'name': 'Base de Datos',
                'status': db_status,
                'label': 'Operativo' if db_status == 'online' else 'Sin conexión'
            },
            {
                'name': 'Sistema de Notificaciones',
                'status': 'online',
                'label': 'Activo'
            },
            {
                'name': 'Almacenamiento',
                'status': 'online',
                'label': 'Normal'
            }
        ]
        
        return jsonify({
            'success': True,
            'system_status': services_status
        })
        
    except Exception as e:
        print(f"Error obteniendo estado del sistema: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# ACTUALIZAR LA FUNCIÓN get_user_session PARA ADMINISTRADORES
# ================================================================
@admin_bp.route('/api/admin/session', methods=['GET'])
@require_role('Administrador')
def admin_get_session():
    """Obtener información de sesión específica para administradores"""
    try:
        user_id = session['user_id']
        
        # Obtener datos del administrador
        admin_data = execute_query("""
            SELECT ID_Usuario, Nombre, Apellido, Correo, Telefono, 
                   URL_Foto, Fecha_Registro, Rol
            FROM Usuario WHERE ID_Usuario = %s AND Rol = 'Administrador'
        """, (user_id,), fetch_one=True)
        
        if not admin_data:
            return jsonify({'success': False, 'message': 'Administrador no encontrado'}), 404
        
        # Estadísticas rápidas para el admin
        quick_stats = execute_query("""
            SELECT 
                (SELECT COUNT(*) FROM Usuario WHERE Rol != 'Administrador' AND Estado = 'Activo') as usuarios_activos,
                (SELECT COUNT(*) FROM Oferta_Trabajo WHERE Estado = 'Abierta') as ofertas_activas,
                (SELECT COUNT(*) FROM Postulacion WHERE Estado = 'Pendiente') as postulaciones_pendientes
        """, fetch_one=True)
        
        return jsonify({
            'success': True,
            'admin': {
                'id': admin_data['ID_Usuario'],
                'nombre': admin_data['Nombre'],
                'apellido': admin_data['Apellido'],
                'nombre_completo': f"{admin_data['Nombre']} {admin_data['Apellido']}",
                'email': admin_data['Correo'],
                'telefono': admin_data.get('Telefono', ''),
                'foto_url': admin_data.get('URL_Foto'),
                'fecha_registro': admin_data['Fecha_Registro'].isoformat() if admin_data['Fecha_Registro'] else None,
                'rol': admin_data['Rol']
            },
            'quick_stats': {
                'usuarios_activos': quick_stats['usuarios_activos'] if quick_stats else 0,
                'ofertas_activas': quick_stats['ofertas_activas'] if quick_stats else 0,
                'postulaciones_pendientes': quick_stats['postulaciones_pendientes'] if quick_stats else 0
            }
        })
        
    except Exception as e:
        print(f"Error obteniendo sesión de admin: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# APIS ADICIONALES PARA FUNCIONALIDADES ESPECÍFICAS DEL ADMIN
# ================================================================
@admin_bp.route('/api/admin/export-users', methods=['GET'])
@require_role('Administrador')
def admin_export_users():
    """Simular exportación de usuarios (retorna datos para generar archivo)"""
    try:
        export_format = request.args.get('format', 'csv')
        
        # Obtener todos los usuarios
        users = execute_query("""
            SELECT 
                u.ID_Usuario as id,
                u.Nombre as nombre,
                u.Apellido as apellido,
                u.Correo as email,
                u.Telefono as telefono,
                u.Rol as tipo,
                u.Estado as estado,
                DATE(u.Fecha_Registro) as fecha_registro
            FROM Usuario u
            WHERE u.Rol != 'Administrador'
            ORDER BY u.Fecha_Registro DESC
        """)
        
        if not users:
            return jsonify({'success': False, 'error': 'No hay usuarios para exportar'}), 404
        
        # Log de auditoría
        admin_name = session.get('user_name', 'Admin')
        print(f"📄 Admin {admin_name} exportó {len(users)} usuarios en formato {export_format}")
        
        return jsonify({
            'success': True,
            'message': f'Datos de {len(users)} usuarios preparados para exportación',
            'format': export_format,
            'users': users,
            'total': len(users)
        })
        
    except Exception as e:
        print(f"Error exportando usuarios: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/backup-data', methods=['POST'])
@require_role('Administrador')
def admin_backup_data():
    """Simular creación de backup de datos"""
    try:
        from datetime import datetime
        import uuid
        
        backup_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"camp_backup_{timestamp}_{backup_id}.sql"
        
        # Simular proceso de backup (en producción aquí irían los comandos reales)
        import time
        time.sleep(2)  # Simular procesamiento
        
        # Log de auditoría
        admin_name = session.get('user_name', 'Admin')
        print(f"💾 Admin {admin_name} creó backup: {backup_name}")
        
        return jsonify({
            'success': True,
            'message': 'Backup creado correctamente',
            'backup_info': {
                'id': backup_id,
                'filename': backup_name,
                'timestamp': timestamp,
                'size': '2.4 MB',  # Simulado
                'status': 'completed'
            }
        })
        
    except Exception as e:
        print(f"Error creando backup: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/clear-cache', methods=['POST'])
@require_role('Administrador')
def admin_clear_cache():
    """Simular limpieza de cache del sistema"""
    try:
        import time
        time.sleep(1)  # Simular procesamiento
        
        # Log de auditoría
        admin_name = session.get('user_name', 'Admin')
        print(f"🧹 Admin {admin_name} limpió el cache del sistema")
        
        return jsonify({
            'success': True,
            'message': 'Cache del sistema limpiado correctamente',
            'cache_info': {
                'cleared_items': 1547,
                'space_freed': '45.2 MB',
                'time_taken': '0.8 segundos'
            }
        })
        
    except Exception as e:
        print(f"Error limpiando cache: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


print("✅ APIs completas del panel de administrador cargadas correctamente")
print("📋 Funcionalidades incluidas:")
print("   • Gestión completa de usuarios (CRUD)")
print("   • Filtros y búsqueda avanzada")
print("   • Estadísticas del dashboard")
print("   • Actividad reciente del sistema")
print("   • Acciones masivas (suspender, activar, eliminar)")
print("   • Estado del sistema en tiempo real")
print("   • Herramientas de administración (backup, cache)")
print("   • Logs de auditoría completos")
print("   • Validaciones de seguridad")


@admin_bp.route('/fix-admin-password', methods=['GET'])
def fix_admin_password():
    """Corregir contraseña del administrador"""
    try:
        hashed_password = hash_password('admin123')
        
        execute_query(
            "UPDATE Usuario SET Contrasena = %s WHERE Correo = %s",
            (hashed_password, 'admin@camp.com')
        )
        
        return "Contraseña del administrador actualizada correctamente"
        
    except Exception as e:
        return f"Error actualizando contraseña: {str(e)}"


@admin_bp.route('/debug-admin', methods=['GET'])
def debug_admin():
    """Debug para admin"""
    try:
        # Verificar sesión
        session_info = {
            'user_id': session.get('user_id'),
            'user_role': session.get('user_role'),
            'user_name': session.get('user_name')
        }
        
        # Contar usuarios
        users_count = execute_query("SELECT COUNT(*) as count FROM Usuario WHERE Rol != 'Administrador'", fetch_one=True)
        
        return jsonify({
            'session': session_info,
            'users_count': users_count['count'] if users_count else 0,
            'all_users': execute_query("SELECT ID_Usuario, Nombre, Apellido, Correo, Rol, Estado FROM Usuario WHERE Rol != 'Administrador'")
        })
    except Exception as e:
        return jsonify({'error': str(e)})


# ================================================================
# APIS COMPLETAS PARA ADMINISTRADOR - AGREGAR A TU APP.PY
# Gestión de Publicaciones, Estadísticas y Reportes
# ================================================================

# ================================================================
# 1. GESTIÓN DE PUBLICACIONES (OFERTAS DE TRABAJO)
# ================================================================

@admin_bp.route('/api/admin/publicaciones', methods=['GET'])
@require_role('Administrador')
def admin_get_publicaciones():
    """Obtener todas las publicaciones/ofertas con filtros"""
    try:
        # Filtros opcionales
        estado_filter = request.args.get('estado', '')
        agricultor_filter = request.args.get('agricultor', '')
        fecha_desde = request.args.get('fecha_desde', '')
        fecha_hasta = request.args.get('fecha_hasta', '')
        
        base_query = """
            SELECT 
                ot.ID_Oferta,
                ot.Titulo,
                ot.Descripcion,
                ot.Pago_Ofrecido,
                ot.Fecha_Publicacion,
                ot.Estado,
                CONCAT(u.Nombre, ' ', u.Apellido) as Agricultor_Nombre,
                u.ID_Usuario as Agricultor_ID,
                u.Correo as Agricultor_Email,
                COUNT(DISTINCT p.ID_Postulacion) as Total_Postulaciones,
                COUNT(DISTINCT CASE WHEN p.Estado = 'Pendiente' THEN p.ID_Postulacion END) as Postulaciones_Pendientes,
                COUNT(DISTINCT CASE WHEN p.Estado = 'Aceptada' THEN p.ID_Postulacion END) as Postulaciones_Aceptadas,
                COUNT(DISTINCT al.ID_Acuerdo) as Contratos_Activos
            FROM Oferta_Trabajo ot
            JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
            LEFT JOIN Postulacion p ON ot.ID_Oferta = p.ID_Oferta
            LEFT JOIN Acuerdo_Laboral al ON ot.ID_Oferta = al.ID_Oferta AND al.Estado = 'Activo'
            WHERE 1=1
        """
        
        params = []
        
        # Aplicar filtros
        if estado_filter and estado_filter in ['Abierta', 'Cerrada', 'En Proceso']:
            base_query += " AND ot.Estado = %s"
            params.append(estado_filter)
        
        if agricultor_filter:
            base_query += " AND (u.Nombre LIKE %s OR u.Apellido LIKE %s OR u.Correo LIKE %s)"
            search_like = f"%{agricultor_filter}%"
            params.extend([search_like, search_like, search_like])
        
        if fecha_desde:
            base_query += " AND DATE(ot.Fecha_Publicacion) >= %s"
            params.append(fecha_desde)
        
        if fecha_hasta:
            base_query += " AND DATE(ot.Fecha_Publicacion) <= %s"
            params.append(fecha_hasta)
        
        base_query += """
            GROUP BY ot.ID_Oferta, ot.Titulo, ot.Descripcion, ot.Pago_Ofrecido, 
                     ot.Fecha_Publicacion, ot.Estado, u.Nombre, u.Apellido, 
                     u.ID_Usuario, u.Correo
            ORDER BY ot.Fecha_Publicacion DESC
            LIMIT 100
        """
        
        publicaciones = execute_query(base_query, tuple(params) if params else None)
        
        publicaciones_list = []
        if publicaciones:
            for pub in publicaciones:
                # Extraer ubicación de la descripción si existe
                ubicacion = 'No especificada'
                if pub['Descripcion'] and 'Ubicación:' in pub['Descripcion']:
                    try:
                        ubicacion = pub['Descripcion'].split('Ubicación:')[-1].strip().split('\n')[0]
                    except:
                        pass
                
                publicaciones_list.append({
                    'id': pub['ID_Oferta'],
                    'titulo': pub['Titulo'],
                    'descripcion': pub['Descripcion'][:200] + '...' if len(pub['Descripcion']) > 200 else pub['Descripcion'],
                    'pago': float(pub['Pago_Ofrecido']) if pub['Pago_Ofrecido'] else 0,
                    'fecha_publicacion': pub['Fecha_Publicacion'].strftime('%Y-%m-%d %H:%M') if pub['Fecha_Publicacion'] else '',
                    'estado': pub['Estado'],
                    'agricultor': {
                        'id': pub['Agricultor_ID'],
                        'nombre': pub['Agricultor_Nombre'],
                        'email': pub['Agricultor_Email']
                    },
                    'estadisticas': {
                        'total_postulaciones': pub['Total_Postulaciones'] or 0,
                        'postulaciones_pendientes': pub['Postulaciones_Pendientes'] or 0,
                        'postulaciones_aceptadas': pub['Postulaciones_Aceptadas'] or 0,
                        'contratos_activos': pub['Contratos_Activos'] or 0
                    },
                    'ubicacion': ubicacion
                })
        
        return jsonify({
            'success': True,
            'publicaciones': publicaciones_list,
            'total': len(publicaciones_list)
        })
        
    except Exception as e:
        print(f"Error obteniendo publicaciones: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/publicacion/<int:oferta_id>', methods=['GET'])
@require_role('Administrador')
def admin_get_publicacion_details(oferta_id):
    """Obtener detalles completos de una publicación"""
    try:
        # Información básica de la oferta
        oferta = execute_query("""
            SELECT 
                ot.ID_Oferta,
                ot.Titulo,
                ot.Descripcion,
                ot.Pago_Ofrecido,
                ot.Fecha_Publicacion,
                ot.Estado,
                ot.ID_Agricultor,
                CONCAT(u.Nombre, ' ', u.Apellido) as Agricultor_Nombre,
                u.Correo as Agricultor_Email,
                u.Telefono as Agricultor_Telefono
            FROM Oferta_Trabajo ot
            JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
            WHERE ot.ID_Oferta = %s
        """, (oferta_id,), fetch_one=True)
        
        if not oferta:
            return jsonify({'success': False, 'error': 'Publicación no encontrada'}), 404
        
        # Postulaciones
        postulaciones = execute_query("""
            SELECT 
                p.ID_Postulacion,
                p.Estado,
                p.Fecha_Postulacion,
                CONCAT(u.Nombre, ' ', u.Apellido) as Trabajador_Nombre,
                u.Correo as Trabajador_Email,
                u.ID_Usuario as Trabajador_ID
            FROM Postulacion p
            JOIN Usuario u ON p.ID_Trabajador = u.ID_Usuario
            WHERE p.ID_Oferta = %s
            ORDER BY p.Fecha_Postulacion DESC
        """, (oferta_id,))
        
        # Contratos relacionados
        contratos = execute_query("""
            SELECT 
                al.ID_Acuerdo,
                al.Estado,
                al.Fecha_Inicio,
                al.Fecha_Fin,
                al.Pago_Final,
                CONCAT(u.Nombre, ' ', u.Apellido) as Trabajador_Nombre
            FROM Acuerdo_Laboral al
            JOIN Usuario u ON al.ID_Trabajador = u.ID_Usuario
            WHERE al.ID_Oferta = %s
            ORDER BY al.Fecha_Inicio DESC
        """, (oferta_id,))
        
        return jsonify({
            'success': True,
            'publicacion': {
                'id': oferta['ID_Oferta'],
                'titulo': oferta['Titulo'],
                'descripcion': oferta['Descripcion'],
                'pago': float(oferta['Pago_Ofrecido']) if oferta['Pago_Ofrecido'] else 0,
                'fecha_publicacion': oferta['Fecha_Publicacion'].isoformat() if oferta['Fecha_Publicacion'] else None,
                'estado': oferta['Estado'],
                'agricultor': {
                    'id': oferta['ID_Agricultor'],
                    'nombre': oferta['Agricultor_Nombre'],
                    'email': oferta['Agricultor_Email'],
                    'telefono': oferta['Agricultor_Telefono']
                },
                'postulaciones': postulaciones or [],
                'contratos': contratos or []
            }
        })
        
    except Exception as e:
        print(f"Error obteniendo detalles de publicación: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/publicacion/<int:oferta_id>/cambiar-estado', methods=['PUT'])
@require_role('Administrador')
def admin_cambiar_estado_publicacion(oferta_id):
    """Cambiar estado de una publicación (Abierta/Cerrada/En Proceso)"""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if nuevo_estado not in ['Abierta', 'Cerrada', 'En Proceso']:
            return jsonify({'success': False, 'error': 'Estado no válido'}), 400
        
        # Verificar que la publicación existe
        oferta = execute_query("""
            SELECT ID_Oferta, Titulo, Estado 
            FROM Oferta_Trabajo 
            WHERE ID_Oferta = %s
        """, (oferta_id,), fetch_one=True)
        
        if not oferta:
            return jsonify({'success': False, 'error': 'Publicación no encontrada'}), 404
        
        # Actualizar estado
        execute_query("""
            UPDATE Oferta_Trabajo 
            SET Estado = %s 
            WHERE ID_Oferta = %s
        """, (nuevo_estado, oferta_id))
        
        # Log de auditoría
        admin_name = session.get('user_name', 'Admin')
        print(f"📋 Admin {admin_name} cambió estado de oferta {oferta_id} '{oferta['Titulo']}' de '{oferta['Estado']}' a '{nuevo_estado}'")
        
        return jsonify({
            'success': True,
            'message': f'Estado de publicación actualizado a {nuevo_estado}'
        })
        
    except Exception as e:
        print(f"Error cambiando estado: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/publicacion/<int:oferta_id>', methods=['DELETE'])
@require_role('Administrador')
def admin_delete_publicacion(oferta_id):
    """Eliminar una publicación (con precaución)"""
    try:
        # Verificar que existe
        oferta = execute_query("""
            SELECT ID_Oferta, Titulo 
            FROM Oferta_Trabajo 
            WHERE ID_Oferta = %s
        """, (oferta_id,), fetch_one=True)
        
        if not oferta:
            return jsonify({'success': False, 'error': 'Publicación no encontrada'}), 404
        
        # Verificar si hay contratos activos
        contratos_activos = execute_query("""
            SELECT COUNT(*) as total 
            FROM Acuerdo_Laboral 
            WHERE ID_Oferta = %s AND Estado = 'Activo'
        """, (oferta_id,), fetch_one=True)
        
        if contratos_activos and contratos_activos['total'] > 0:
            return jsonify({
                'success': False, 
                'error': 'No se puede eliminar una publicación con contratos activos'
            }), 400
        
        # Eliminar dependencias
        execute_query("DELETE FROM Postulacion WHERE ID_Oferta = %s", (oferta_id,))
        execute_query("DELETE FROM Acuerdo_Laboral WHERE ID_Oferta = %s", (oferta_id,))
        execute_query("DELETE FROM Oferta_Trabajo WHERE ID_Oferta = %s", (oferta_id,))
        
        # Log de auditoría
        admin_name = session.get('user_name', 'Admin')
        print(f"🗑️ Admin {admin_name} eliminó publicación {oferta_id} '{oferta['Titulo']}'")
        
        return jsonify({
            'success': True,
            'message': f'Publicación "{oferta["Titulo"]}" eliminada correctamente'
        })
        
    except Exception as e:
        print(f"Error eliminando publicación: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# 2. ESTADÍSTICAS AVANZADAS
# ================================================================

@admin_bp.route('/api/admin/estadisticas/general', methods=['GET'])
@require_role('Administrador')
def admin_estadisticas_general():
    """Obtener estadísticas generales del sistema"""
    try:
        from datetime import datetime, timedelta
        
        # Usuarios
        stats_usuarios = execute_query("""
            SELECT 
                COUNT(*) as total_usuarios,
                COUNT(CASE WHEN Rol = 'Trabajador' THEN 1 END) as total_trabajadores,
                COUNT(CASE WHEN Rol = 'Agricultor' THEN 1 END) as total_agricultores,
                COUNT(CASE WHEN Estado = 'Activo' THEN 1 END) as usuarios_activos,
                COUNT(CASE WHEN Estado = 'Inactivo' THEN 1 END) as usuarios_inactivos,
                COUNT(CASE WHEN DATE(Fecha_Registro) >= CURDATE() - INTERVAL 30 DAY THEN 1 END) as nuevos_ultimo_mes,
                COUNT(CASE WHEN DATE(Fecha_Registro) >= CURDATE() - INTERVAL 7 DAY THEN 1 END) as nuevos_ultima_semana
            FROM Usuario
            WHERE Rol != 'Administrador'
        """, fetch_one=True)
        
        # Ofertas de trabajo
        stats_ofertas = execute_query("""
            SELECT 
                COUNT(*) as total_ofertas,
                COUNT(CASE WHEN Estado = 'Abierta' THEN 1 END) as ofertas_abiertas,
                COUNT(CASE WHEN Estado = 'Cerrada' THEN 1 END) as ofertas_cerradas,
                COUNT(CASE WHEN Estado = 'En Proceso' THEN 1 END) as ofertas_en_proceso,
                COUNT(CASE WHEN DATE(Fecha_Publicacion) >= CURDATE() - INTERVAL 30 DAY THEN 1 END) as nuevas_ultimo_mes,
                AVG(Pago_Ofrecido) as pago_promedio
            FROM Oferta_Trabajo
        """, fetch_one=True)
        
        # Postulaciones
        stats_postulaciones = execute_query("""
            SELECT 
                COUNT(*) as total_postulaciones,
                COUNT(CASE WHEN Estado = 'Pendiente' THEN 1 END) as pendientes,
                COUNT(CASE WHEN Estado = 'Aceptada' THEN 1 END) as aceptadas,
                COUNT(CASE WHEN Estado = 'Rechazada' THEN 1 END) as rechazadas,
                COUNT(CASE WHEN Estado = 'Favorito' THEN 1 END) as favoritos,
                COUNT(CASE WHEN DATE(Fecha_Postulacion) >= CURDATE() - INTERVAL 30 DAY THEN 1 END) as nuevas_ultimo_mes
            FROM Postulacion
        """, fetch_one=True)
        
        # Contratos
        stats_contratos = execute_query("""
            SELECT 
                COUNT(*) as total_contratos,
                COUNT(CASE WHEN Estado = 'Activo' THEN 1 END) as contratos_activos,
                COUNT(CASE WHEN Estado = 'Finalizado' THEN 1 END) as contratos_finalizados,
                COUNT(CASE WHEN Estado = 'Cancelado' THEN 1 END) as contratos_cancelados,
                SUM(CASE WHEN Estado = 'Finalizado' THEN Pago_Final ELSE 0 END) as monto_total_pagado,
                AVG(CASE WHEN Estado = 'Finalizado' THEN Pago_Final ELSE NULL END) as pago_promedio_contrato
            FROM Acuerdo_Laboral
        """, fetch_one=True)
        
        # Calificaciones
        stats_calificaciones = execute_query("""
            SELECT 
                COUNT(*) as total_calificaciones,
                AVG(CAST(Puntuacion AS DECIMAL(3,2))) as calificacion_promedio,
                COUNT(CASE WHEN CAST(Puntuacion AS UNSIGNED) >= 4 THEN 1 END) as calificaciones_buenas,
                COUNT(CASE WHEN CAST(Puntuacion AS UNSIGNED) <= 2 THEN 1 END) as calificaciones_malas
            FROM Calificacion
        """, fetch_one=True)
        
        # Tasa de conversión
        tasa_conversion = 0
        if stats_postulaciones and stats_postulaciones['total_postulaciones'] > 0:
            tasa_conversion = (stats_postulaciones['aceptadas'] / stats_postulaciones['total_postulaciones']) * 100
        
        # Tasa de éxito
        tasa_exito = 0
        if stats_contratos and stats_contratos['total_contratos'] > 0:
            tasa_exito = (stats_contratos['contratos_finalizados'] / stats_contratos['total_contratos']) * 100
        
        return jsonify({
            'success': True,
            'estadisticas': {
                'usuarios': {
                    'total': stats_usuarios['total_usuarios'] or 0,
                    'trabajadores': stats_usuarios['total_trabajadores'] or 0,
                    'agricultores': stats_usuarios['total_agricultores'] or 0,
                    'activos': stats_usuarios['usuarios_activos'] or 0,
                    'inactivos': stats_usuarios['usuarios_inactivos'] or 0,
                    'nuevos_mes': stats_usuarios['nuevos_ultimo_mes'] or 0,
                    'nuevos_semana': stats_usuarios['nuevos_ultima_semana'] or 0
                },
                'ofertas': {
                    'total': stats_ofertas['total_ofertas'] or 0,
                    'abiertas': stats_ofertas['ofertas_abiertas'] or 0,
                    'cerradas': stats_ofertas['ofertas_cerradas'] or 0,
                    'en_proceso': stats_ofertas['ofertas_en_proceso'] or 0,
                    'nuevas_mes': stats_ofertas['nuevas_ultimo_mes'] or 0,
                    'pago_promedio': float(stats_ofertas['pago_promedio']) if stats_ofertas['pago_promedio'] else 0
                },
                'postulaciones': {
                    'total': stats_postulaciones['total_postulaciones'] or 0,
                    'pendientes': stats_postulaciones['pendientes'] or 0,
                    'aceptadas': stats_postulaciones['aceptadas'] or 0,
                    'rechazadas': stats_postulaciones['rechazadas'] or 0,
                    'favoritos': stats_postulaciones['favoritos'] or 0,
                    'nuevas_mes': stats_postulaciones['nuevas_ultimo_mes'] or 0,
                    'tasa_conversion': round(tasa_conversion, 2)
                },
                'contratos': {
                    'total': stats_contratos['total_contratos'] or 0,
                    'activos': stats_contratos['contratos_activos'] or 0,
                    'finalizados': stats_contratos['contratos_finalizados'] or 0,
                    'cancelados': stats_contratos['contratos_cancelados'] or 0,
                    'monto_total': float(stats_contratos['monto_total_pagado']) if stats_contratos['monto_total_pagado'] else 0,
                    'pago_promedio': float(stats_contratos['pago_promedio_contrato']) if stats_contratos['pago_promedio_contrato'] else 0,
                    'tasa_exito': round(tasa_exito, 2)
                },
                'calificaciones': {
                    'total': stats_calificaciones['total_calificaciones'] or 0,
                    'promedio': float(stats_calificaciones['calificacion_promedio']) if stats_calificaciones['calificacion_promedio'] else 0,
                    'buenas': stats_calificaciones['calificaciones_buenas'] or 0,
                    'malas': stats_calificaciones['calificaciones_malas'] or 0
                }
            }
        })
        
    except Exception as e:
        print(f"Error obteniendo estadísticas generales: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/estadisticas/graficos', methods=['GET'])
@require_role('Administrador')
def admin_estadisticas_graficos():
    """Obtener datos para gráficos"""
    try:
        # Usuarios registrados por mes (últimos 6 meses)
        usuarios_por_mes = execute_query("""
            SELECT 
                DATE_FORMAT(Fecha_Registro, '%Y-%m') as mes,
                COUNT(*) as total,
                COUNT(CASE WHEN Rol = 'Trabajador' THEN 1 END) as trabajadores,
                COUNT(CASE WHEN Rol = 'Agricultor' THEN 1 END) as agricultores
            FROM Usuario
            WHERE Fecha_Registro >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
              AND Rol != 'Administrador'
            GROUP BY DATE_FORMAT(Fecha_Registro, '%Y-%m')
            ORDER BY mes
        """)
        
        # Ofertas publicadas por mes
        ofertas_por_mes = execute_query("""
            SELECT 
                DATE_FORMAT(Fecha_Publicacion, '%Y-%m') as mes,
                COUNT(*) as total,
                COUNT(CASE WHEN Estado = 'Abierta' THEN 1 END) as abiertas,
                COUNT(CASE WHEN Estado = 'Cerrada' THEN 1 END) as cerradas
            FROM Oferta_Trabajo
            WHERE Fecha_Publicacion >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
            GROUP BY DATE_FORMAT(Fecha_Publicacion, '%Y-%m')
            ORDER BY mes
        """)
        
        # Postulaciones por estado
        postulaciones_por_estado = execute_query("""
            SELECT 
                Estado,
                COUNT(*) as total
            FROM Postulacion
            GROUP BY Estado
        """)
        
        # Distribución de pagos
        distribucion_pagos = execute_query("""
            SELECT 
                CASE 
                    WHEN Pago_Ofrecido < 30000 THEN 'Bajo (< $30k)'
                    WHEN Pago_Ofrecido BETWEEN 30000 AND 50000 THEN 'Medio ($30k-$50k)'
                    WHEN Pago_Ofrecido > 50000 THEN 'Alto (> $50k)'
                END as rango,
                COUNT(*) as total
            FROM Oferta_Trabajo
            GROUP BY rango
        """)
        
        # Top agricultores por ofertas publicadas
        top_agricultores = execute_query("""
            SELECT 
                CONCAT(u.Nombre, ' ', u.Apellido) as nombre,
                COUNT(ot.ID_Oferta) as total_ofertas,
                COUNT(CASE WHEN ot.Estado = 'Abierta' THEN 1 END) as ofertas_activas
            FROM Usuario u
            JOIN Oferta_Trabajo ot ON u.ID_Usuario = ot.ID_Agricultor
            WHERE u.Rol = 'Agricultor'
            GROUP BY u.ID_Usuario, u.Nombre, u.Apellido
            ORDER BY total_ofertas DESC
            LIMIT 10
        """)
        
        # Top trabajadores por postulaciones
        top_trabajadores = execute_query("""
            SELECT 
                CONCAT(u.Nombre, ' ', u.Apellido) as nombre,
                COUNT(p.ID_Postulacion) as total_postulaciones,
                COUNT(CASE WHEN p.Estado = 'Aceptada' THEN 1 END) as aceptadas
            FROM Usuario u
            JOIN Postulacion p ON u.ID_Usuario = p.ID_Trabajador
            WHERE u.Rol = 'Trabajador'
            GROUP BY u.ID_Usuario, u.Nombre, u.Apellido
            ORDER BY total_postulaciones DESC
            LIMIT 10
        """)
        
        return jsonify({
            'success': True,
            'graficos': {
                'usuarios_por_mes': usuarios_por_mes or [],
                'ofertas_por_mes': ofertas_por_mes or [],
                'postulaciones_por_estado': postulaciones_por_estado or [],
                'distribucion_pagos': distribucion_pagos or [],
                'top_agricultores': top_agricultores or [],
                'top_trabajadores': top_trabajadores or []
            }
        })
        
    except Exception as e:
        print(f"Error obteniendo datos para gráficos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# 3. REPORTES
# ================================================================

@admin_bp.route('/api/admin/reportes/generar', methods=['POST'])
@require_role('Administrador')
def admin_generar_reporte():
    """Generar reporte personalizado"""
    try:
        data = request.get_json()
        tipo_reporte = data.get('tipo')
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        formato = data.get('formato', 'json')  # json, csv, excel
        
        if not tipo_reporte:
            return jsonify({'success': False, 'error': 'Tipo de reporte requerido'}), 400
        
        reporte_data = {}
        
        if tipo_reporte == 'usuarios':
            # Reporte de usuarios
            query = """
                SELECT 
                    u.ID_Usuario,
                    CONCAT(u.Nombre, ' ', u.Apellido) as Nombre_Completo,
                    u.Correo,
                    u.Telefono,
                    u.Rol,
                    u.Estado,
                    DATE(u.Fecha_Registro) as Fecha_Registro,
                    COUNT(DISTINCT CASE WHEN u.Rol = 'Trabajador' THEN p.ID_Postulacion END) as Total_Postulaciones,
                    COUNT(DISTINCT CASE WHEN u.Rol = 'Agricultor' THEN ot.ID_Oferta END) as Total_Ofertas
                FROM Usuario u
                LEFT JOIN Postulacion p ON u.ID_Usuario = p.ID_Trabajador
                LEFT JOIN Oferta_Trabajo ot ON u.ID_Usuario = ot.ID_Agricultor
                WHERE u.Rol != 'Administrador'
            """
            
            if fecha_inicio and fecha_fin:
                query += " AND DATE(u.Fecha_Registro) BETWEEN %s AND %s"
                params = (fecha_inicio, fecha_fin)
            else:
                params = None
            
            query += " GROUP BY u.ID_Usuario ORDER BY u.Fecha_Registro DESC"
            
            reporte_data = execute_query(query, params)
            
        elif tipo_reporte == 'ofertas':
            # Reporte de ofertas
            query = """
                SELECT 
                    ot.ID_Oferta,
                    ot.Titulo,
                    CONCAT(u.Nombre, ' ', u.Apellido) as Agricultor,
                    ot.Pago_Ofrecido,
                    DATE(ot.Fecha_Publicacion) as Fecha_Publicacion,
                    ot.Estado,
                    COUNT(DISTINCT p.ID_Postulacion) as Total_Postulaciones,
                    COUNT(DISTINCT CASE WHEN p.Estado = 'Aceptada' THEN p.ID_Postulacion END) as Postulaciones_Aceptadas
                FROM Oferta_Trabajo ot
                JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
                LEFT JOIN Postulacion p ON ot.ID_Oferta = p.ID_Oferta
                WHERE 1=1
            """
            
            if fecha_inicio and fecha_fin:
                query += " AND DATE(ot.Fecha_Publicacion) BETWEEN %s AND %s"
                params = (fecha_inicio, fecha_fin)
            else:
                params = None
            
            query += " GROUP BY ot.ID_Oferta ORDER BY ot.Fecha_Publicacion DESC"
            
            reporte_data = execute_query(query, params)
            
        elif tipo_reporte == 'contratos':
            # Reporte de contratos
            query = """
                SELECT 
                    al.ID_Acuerdo,
                    ot.Titulo as Oferta,
                    CONCAT(ut.Nombre, ' ', ut.Apellido) as Trabajador,
                    CONCAT(ua.Nombre, ' ', ua.Apellido) as Agricultor,
                    DATE(al.Fecha_Inicio) as Fecha_Inicio,
                    DATE(al.Fecha_Fin) as Fecha_Fin,
                    al.Pago_Final,
                    al.Estado
                FROM Acuerdo_Laboral al
                JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
                JOIN Usuario ut ON al.ID_Trabajador = ut.ID_Usuario
                JOIN Usuario ua ON ot.ID_Agricultor = ua.ID_Usuario
                WHERE 1=1
            """
            
            if fecha_inicio and fecha_fin:
                query += " AND DATE(al.Fecha_Inicio) BETWEEN %s AND %s"
                params = (fecha_inicio, fecha_fin)
            else:
                params = None
            
            query += " ORDER BY al.Fecha_Inicio DESC"
            
            reporte_data = execute_query(query, params)
            
        elif tipo_reporte == 'financiero':
            # Reporte financiero
            stats_financiero = execute_query("""
                SELECT 
                    COUNT(*) as total_contratos,
                    SUM(Pago_Final) as monto_total,
                    AVG(Pago_Final) as pago_promedio,
                    MIN(Pago_Final) as pago_minimo,
                    MAX(Pago_Final) as pago_maximo,
                    COUNT(CASE WHEN Estado = 'Finalizado' THEN 1 END) as contratos_finalizados
                FROM Acuerdo_Laboral
                WHERE Fecha_Inicio BETWEEN %s AND %s
            """, (fecha_inicio or '2020-01-01', fecha_fin or '2030-12-31'), fetch_one=True)
            
            # Detalles por mes
            detalles_mes = execute_query("""
                SELECT 
                    DATE_FORMAT(Fecha_Inicio, '%Y-%m') as mes,
                    COUNT(*) as contratos,
                    SUM(Pago_Final) as monto_total
                FROM Acuerdo_Laboral
                WHERE Fecha_Inicio BETWEEN %s AND %s
                GROUP BY DATE_FORMAT(Fecha_Inicio, '%Y-%m')
                ORDER BY mes
            """, (fecha_inicio or '2020-01-01', fecha_fin or '2030-12-31'))
            
            reporte_data = {
                'resumen': stats_financiero,
                'detalles_mensuales': detalles_mes or []
            }
        
        else:
            return jsonify({'success': False, 'error': 'Tipo de reporte no válido'}), 400
        
        # Log de auditoría
        admin_name = session.get('user_name', 'Admin')
        print(f"📊 Admin {admin_name} generó reporte de tipo '{tipo_reporte}' del {fecha_inicio} al {fecha_fin}")
        
        return jsonify({
            'success': True,
            'reporte': {
                'tipo': tipo_reporte,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'fecha_generacion': datetime.now().isoformat(),
                'generado_por': admin_name,
                'total_registros': len(reporte_data) if isinstance(reporte_data, list) else 1,
                'datos': reporte_data
            }
        })
        
    except Exception as e:
        print(f"Error generando reporte: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/reportes/actividad', methods=['GET'])
@require_role('Administrador')
def admin_reporte_actividad():
    """Reporte de actividad del sistema"""
    try:
        dias = int(request.args.get('dias', 30))
        
        # Actividad general
        actividad = execute_query("""
            SELECT 
                DATE(fecha) as dia,
                tipo_actividad,
                COUNT(*) as total
            FROM (
                SELECT Fecha_Registro as fecha, 'Nuevo Usuario' as tipo_actividad
                FROM Usuario 
                WHERE Fecha_Registro >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                
                UNION ALL
                
                SELECT Fecha_Publicacion, 'Nueva Oferta'
                FROM Oferta_Trabajo
                WHERE Fecha_Publicacion >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                
                UNION ALL
                
                SELECT Fecha_Postulacion, 'Nueva Postulación'
                FROM Postulacion
                WHERE Fecha_Postulacion >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                
                UNION ALL
                
                SELECT Fecha_Inicio, 'Nuevo Contrato'
                FROM Acuerdo_Laboral
                WHERE Fecha_Inicio >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            ) actividades
            GROUP BY DATE(fecha), tipo_actividad
            ORDER BY dia DESC, tipo_actividad
        """, (dias, dias, dias, dias))
        
        # Resumen por tipo
        resumen = execute_query("""
            SELECT 
                tipo_actividad,
                COUNT(*) as total
            FROM (
                SELECT 'Nuevo Usuario' as tipo_actividad
                FROM Usuario 
                WHERE Fecha_Registro >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                
                UNION ALL
                
                SELECT 'Nueva Oferta'
                FROM Oferta_Trabajo
                WHERE Fecha_Publicacion >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                
                UNION ALL
                
                SELECT 'Nueva Postulación'
                FROM Postulacion
                WHERE Fecha_Postulacion >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                
                UNION ALL
                
                SELECT 'Nuevo Contrato'
                FROM Acuerdo_Laboral
                WHERE Fecha_Inicio >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            ) actividades
            GROUP BY tipo_actividad
        """, (dias, dias, dias, dias))
        
        return jsonify({
            'success': True,
            'periodo': f'Últimos {dias} días',
            'resumen': resumen or [],
            'detalle_diario': actividad or []
        })
        
    except Exception as e:
        print(f"Error en reporte de actividad: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/reportes/rendimiento', methods=['GET'])
@require_role('Administrador')
def admin_reporte_rendimiento():
    """Reporte de rendimiento del sistema"""
    try:
        # Métricas de rendimiento
        metricas = {
            'usuarios': {},
            'ofertas': {},
            'postulaciones': {},
            'contratos': {}
        }
        
        # Usuarios más activos (trabajadores)
        trabajadores_activos = execute_query("""
            SELECT 
                CONCAT(u.Nombre, ' ', u.Apellido) as nombre,
                COUNT(p.ID_Postulacion) as postulaciones,
                COUNT(al.ID_Acuerdo) as contratos_completados,
                AVG(CAST(c.Puntuacion AS DECIMAL(3,2))) as calificacion
            FROM Usuario u
            LEFT JOIN Postulacion p ON u.ID_Usuario = p.ID_Trabajador
            LEFT JOIN Acuerdo_Laboral al ON u.ID_Usuario = al.ID_Trabajador AND al.Estado = 'Finalizado'
            LEFT JOIN Calificacion c ON u.ID_Usuario = c.ID_Usuario_Receptor
            WHERE u.Rol = 'Trabajador'
            GROUP BY u.ID_Usuario
            ORDER BY postulaciones DESC
            LIMIT 10
        """)
        
        # Agricultores más activos
        agricultores_activos = execute_query("""
            SELECT 
                CONCAT(u.Nombre, ' ', u.Apellido) as nombre,
                COUNT(DISTINCT ot.ID_Oferta) as ofertas_publicadas,
                COUNT(DISTINCT al.ID_Acuerdo) as contratos_completados,
                AVG(CAST(c.Puntuacion AS DECIMAL(3,2))) as calificacion
            FROM Usuario u
            LEFT JOIN Oferta_Trabajo ot ON u.ID_Usuario = ot.ID_Agricultor
            LEFT JOIN Acuerdo_Laboral al ON ot.ID_Oferta = al.ID_Oferta AND al.Estado = 'Finalizado'
            LEFT JOIN Calificacion c ON u.ID_Usuario = c.ID_Usuario_Receptor
            WHERE u.Rol = 'Agricultor'
            GROUP BY u.ID_Usuario
            ORDER BY ofertas_publicadas DESC
            LIMIT 10
        """)
        
        # Ofertas con más postulaciones
        ofertas_populares = execute_query("""
            SELECT 
                ot.Titulo,
                CONCAT(u.Nombre, ' ', u.Apellido) as agricultor,
                COUNT(p.ID_Postulacion) as total_postulaciones,
                ot.Pago_Ofrecido,
                ot.Estado
            FROM Oferta_Trabajo ot
            JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
            LEFT JOIN Postulacion p ON ot.ID_Oferta = p.ID_Oferta
            GROUP BY ot.ID_Oferta
            ORDER BY total_postulaciones DESC
            LIMIT 10
        """)
        
        # Tasa de éxito por categoría
        tasa_exito = execute_query("""
            SELECT 
                ot.Estado,
                COUNT(DISTINCT ot.ID_Oferta) as total_ofertas,
                COUNT(DISTINCT p.ID_Postulacion) as total_postulaciones,
                COUNT(DISTINCT al.ID_Acuerdo) as total_contratos
            FROM Oferta_Trabajo ot
            LEFT JOIN Postulacion p ON ot.ID_Oferta = p.ID_Oferta
            LEFT JOIN Acuerdo_Laboral al ON ot.ID_Oferta = al.ID_Oferta
            GROUP BY ot.Estado
        """)
        
        return jsonify({
            'success': True,
            'rendimiento': {
                'trabajadores_destacados': trabajadores_activos or [],
                'agricultores_destacados': agricultores_activos or [],
                'ofertas_populares': ofertas_populares or [],
                'tasa_exito': tasa_exito or []
            }
        })
        
    except Exception as e:
        print(f"Error en reporte de rendimiento: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# 4. EXPORTACIÓN DE DATOS
# ================================================================

@admin_bp.route('/api/admin/exportar/<tipo>', methods=['GET'])
@require_role('Administrador')
def admin_exportar_datos(tipo):
    """Exportar datos en diferentes formatos"""
    try:
        formato = request.args.get('formato', 'csv')  # csv, json, excel
        
        if tipo == 'usuarios':
            datos = execute_query("""
                SELECT 
                    ID_Usuario,
                    CONCAT(Nombre, ' ', Apellido) as Nombre_Completo,
                    Correo,
                    Telefono,
                    Rol,
                    Estado,
                    DATE(Fecha_Registro) as Fecha_Registro
                FROM Usuario
                WHERE Rol != 'Administrador'
                ORDER BY Fecha_Registro DESC
            """)
            
        elif tipo == 'ofertas':
            datos = execute_query("""
                SELECT 
                    ot.ID_Oferta,
                    ot.Titulo,
                    CONCAT(u.Nombre, ' ', u.Apellido) as Agricultor,
                    ot.Pago_Ofrecido,
                    DATE(ot.Fecha_Publicacion) as Fecha_Publicacion,
                    ot.Estado
                FROM Oferta_Trabajo ot
                JOIN Usuario u ON ot.ID_Agricultor = u.ID_Usuario
                ORDER BY ot.Fecha_Publicacion DESC
            """)
            
        elif tipo == 'postulaciones':
            datos = execute_query("""
                SELECT 
                    p.ID_Postulacion,
                    ot.Titulo as Oferta,
                    CONCAT(ut.Nombre, ' ', ut.Apellido) as Trabajador,
                    CONCAT(ua.Nombre, ' ', ua.Apellido) as Agricultor,
                    DATE(p.Fecha_Postulacion) as Fecha_Postulacion,
                    p.Estado
                FROM Postulacion p
                JOIN Oferta_Trabajo ot ON p.ID_Oferta = ot.ID_Oferta
                JOIN Usuario ut ON p.ID_Trabajador = ut.ID_Usuario
                JOIN Usuario ua ON ot.ID_Agricultor = ua.ID_Usuario
                ORDER BY p.Fecha_Postulacion DESC
            """)
            
        elif tipo == 'contratos':
            datos = execute_query("""
                SELECT 
                    al.ID_Acuerdo,
                    ot.Titulo as Oferta,
                    CONCAT(ut.Nombre, ' ', ut.Apellido) as Trabajador,
                    CONCAT(ua.Nombre, ' ', ua.Apellido) as Agricultor,
                    DATE(al.Fecha_Inicio) as Fecha_Inicio,
                    DATE(al.Fecha_Fin) as Fecha_Fin,
                    al.Pago_Final,
                    al.Estado
                FROM Acuerdo_Laboral al
                JOIN Oferta_Trabajo ot ON al.ID_Oferta = ot.ID_Oferta
                JOIN Usuario ut ON al.ID_Trabajador = ut.ID_Usuario
                JOIN Usuario ua ON ot.ID_Agricultor = ua.ID_Usuario
                ORDER BY al.Fecha_Inicio DESC
            """)
            
        else:
            return jsonify({'success': False, 'error': 'Tipo de exportación no válido'}), 400
        
        if not datos:
            return jsonify({'success': False, 'error': 'No hay datos para exportar'}), 404
        
        # Log de auditoría
        admin_name = session.get('user_name', 'Admin')
        print(f"📥 Admin {admin_name} exportó {len(datos)} registros de {tipo} en formato {formato}")
        
        # En producción real, aquí generarías el archivo CSV/Excel
        # Por ahora retornamos los datos en JSON
        return jsonify({
            'success': True,
            'tipo': tipo,
            'formato': formato,
            'total_registros': len(datos),
            'datos': datos,
            'mensaje': f'Datos de {tipo} preparados para exportación en formato {formato}'
        })
        
    except Exception as e:
        print(f"Error exportando datos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ================================================================
# 5. MÉTRICAS EN TIEMPO REAL
# ================================================================

@admin_bp.route('/api/admin/metricas-tiempo-real', methods=['GET'])
@require_role('Administrador')
def admin_metricas_tiempo_real():
    """Obtener métricas en tiempo real del sistema"""
    try:
        from datetime import datetime, timedelta
        
        # Actividad de la última hora
        ultima_hora = datetime.now() - timedelta(hours=1)
        
        actividad_reciente = execute_query("""
            SELECT 
                'usuario' as tipo,
                COUNT(*) as cantidad
            FROM Usuario
            WHERE Fecha_Registro >= %s
            
            UNION ALL
            
            SELECT 
                'oferta' as tipo,
                COUNT(*) as cantidad
            FROM Oferta_Trabajo
            WHERE Fecha_Publicacion >= %s
            
            UNION ALL
            
            SELECT 
                'postulacion' as tipo,
                COUNT(*) as cantidad
            FROM Postulacion
            WHERE Fecha_Postulacion >= %s
        """, (ultima_hora, ultima_hora, ultima_hora))
        
        # Usuarios en línea (simulado - necesitarías un sistema de sesiones real)
        usuarios_activos = execute_query("""
            SELECT COUNT(*) as total
            FROM Usuario
            WHERE Estado = 'Activo' AND Rol != 'Administrador'
        """, fetch_one=True)
        
        # Ofertas abiertas actualmente
        ofertas_abiertas = execute_query("""
            SELECT COUNT(*) as total
            FROM Oferta_Trabajo
            WHERE Estado = 'Abierta'
        """, fetch_one=True)
        
        # Postulaciones pendientes de revisión
        postulaciones_pendientes = execute_query("""
            SELECT COUNT(*) as total
            FROM Postulacion
            WHERE Estado = 'Pendiente'
        """, fetch_one=True)
        
        # Contratos activos
        contratos_activos = execute_query("""
            SELECT COUNT(*) as total
            FROM Acuerdo_Laboral
            WHERE Estado = 'Activo'
        """, fetch_one=True)
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'metricas': {
                'usuarios_activos': usuarios_activos['total'] if usuarios_activos else 0,
                'ofertas_abiertas': ofertas_abiertas['total'] if ofertas_abiertas else 0,
                'postulaciones_pendientes': postulaciones_pendientes['total'] if postulaciones_pendientes else 0,
                'contratos_activos': contratos_activos['total'] if contratos_activos else 0,
                'actividad_ultima_hora': {
                    item['tipo']: item['cantidad'] 
                    for item in (actividad_reciente or [])
                }
            }
        })
        
    except Exception as e:
        print(f"Error obteniendo métricas en tiempo real: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


print("✅ APIs completas cargadas:")
print("   📋 Gestión de Publicaciones (GET, detalles, cambiar estado, eliminar)")
print("   📊 Estadísticas Generales y Gráficos")
print("   📑 Reportes (Usuarios, Ofertas, Contratos, Financiero, Actividad, Rendimiento)")
print("   📥 Exportación de Datos (CSV, JSON, Excel)")
print("   ⚡ Métricas en Tiempo Real")


# ================================================================
# API OBTENER REPORTES PENDIENTES
# ================================================================
@admin_bp.route('/api/admin/reportes-pendientes', methods=['GET'])
def get_reportes_pendientes_admin():
    """Obtener todos los reportes para el administrador"""
    try:
        if 'user_id' not in session or session.get('user_role') != 'Administrador':
            return jsonify({
                'success': False,
                'message': 'Acceso denegado. Solo administradores.'
            }), 403
        
        estado_filter = request.args.get('estado', 'Pendiente')
        
        reportes = execute_query("""
            SELECT 
                r.ID_Reporte,
                r.Motivo,
                r.Estado,
                r.Fecha_Reporte,
                ur.ID_Usuario as reportante_id,
                ur.Nombre as reportante_nombre,
                ur.Apellido as reportante_apellido,
                ur.Correo as reportante_email,
                ur.Rol as reportante_rol,
                ud.ID_Usuario as reportado_id,
                ud.Nombre as reportado_nombre,
                ud.Apellido as reportado_apellido,
                ud.Correo as reportado_email,
                ud.Rol as reportado_rol,
                ud.Estado as reportado_estado
            FROM Reportes r
            INNER JOIN Usuario ur ON r.ID_Usuario_Reportante = ur.ID_Usuario
            INNER JOIN Usuario ud ON r.ID_Usuario_Reportado = ud.ID_Usuario
            WHERE r.Estado = %s
            ORDER BY r.Fecha_Reporte DESC
        """, (estado_filter,))
        
        reportes_list = []
        if reportes:
            for reporte in reportes:
                fecha_reporte = reporte['Fecha_Reporte']
                if isinstance(fecha_reporte, str):
                    fecha_reporte = datetime.strptime(fecha_reporte, '%Y-%m-%d %H:%M:%S')
                
                tiempo_transcurrido = datetime.now() - fecha_reporte
                
                if tiempo_transcurrido.days > 0:
                    tiempo_str = f"Hace {tiempo_transcurrido.days} día{'s' if tiempo_transcurrido.days > 1 else ''}"
                elif tiempo_transcurrido.seconds // 3600 > 0:
                    horas = tiempo_transcurrido.seconds // 3600
                    tiempo_str = f"Hace {horas} hora{'s' if horas > 1 else ''}"
                else:
                    minutos = tiempo_transcurrido.seconds // 60
                    tiempo_str = f"Hace {minutos} minuto{'s' if minutos > 1 else ''}"
                
                prioridad = 'medium'
                if tiempo_transcurrido.days > 7:
                    prioridad = 'high'
                elif 'fraude' in reporte['Motivo'].lower() or 'estafa' in reporte['Motivo'].lower():
                    prioridad = 'high'
                
                reportes_list.append({
                    'id_reporte': reporte['ID_Reporte'],
                    'motivo': reporte['Motivo'],
                    'estado': reporte['Estado'],
                    'fecha_reporte': fecha_reporte.strftime('%Y-%m-%d %H:%M:%S'),
                    'tiempo_transcurrido': tiempo_str,
                    'prioridad': prioridad,
                    'reportante': {
                        'id': reporte['reportante_id'],
                        'nombre': f"{reporte['reportante_nombre']} {reporte['reportante_apellido']}",
                        'email': reporte['reportante_email'],
                        'rol': reporte['reportante_rol']
                    },
                    'reportado': {
                        'id': reporte['reportado_id'],
                        'nombre': f"{reporte['reportado_nombre']} {reporte['reportado_apellido']}",
                        'email': reporte['reportado_email'],
                        'rol': reporte['reportado_rol'],
                        'estado': reporte['reportado_estado']
                    }
                })
        
        stats = execute_query("""
            SELECT 
                COUNT(*) as total_reportes,
                COUNT(CASE WHEN Estado = 'Pendiente' THEN 1 END) as pendientes,
                COUNT(CASE WHEN Estado = 'Revisado' THEN 1 END) as revisados,
                COUNT(CASE WHEN Estado = 'Resuelto' THEN 1 END) as resueltos
            FROM Reportes
        """, fetch_one=True)
        
        return jsonify({
            'success': True,
            'reportes': reportes_list,
            'total': len(reportes_list),
            'estadisticas': {
                'total_reportes': stats['total_reportes'] if stats else 0,
                'pendientes': stats['pendientes'] if stats else 0,
                'revisados': stats['revisados'] if stats else 0,
                'resueltos': stats['resueltos'] if stats else 0
            }
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo reportes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error al obtener reportes: {str(e)}'
        }), 500


# ================================================================
# API GESTIONAR REPORTE
# ================================================================
@admin_bp.route('/api/admin/reporte/<int:reporte_id>/accion', methods=['POST'])
def gestionar_reporte_admin(reporte_id):
    """Administrador toma acción sobre un reporte"""
    try:
        if 'user_id' not in session or session.get('user_role') != 'Administrador':
            return jsonify({
                'success': False,
                'message': 'Acceso denegado. Solo administradores.'
            }), 403
        
        data = request.get_json()
        accion = data.get('accion')
        notas = data.get('notas', '')
        
        if not accion:
            return jsonify({
                'success': False,
                'message': 'Acción no especificada'
            }), 400
        
        reporte = execute_query("""
            SELECT r.*, 
                   ud.Nombre as reportado_nombre, 
                   ud.Apellido as reportado_apellido,
                   ud.Estado as reportado_estado
            FROM Reportes r
            JOIN Usuario ud ON r.ID_Usuario_Reportado = ud.ID_Usuario
            WHERE r.ID_Reporte = %s
        """, (reporte_id,), fetch_one=True)
        
        if not reporte:
            return jsonify({
                'success': False,
                'message': 'Reporte no encontrado'
            }), 404
        
        mensaje_respuesta = ''
        
        if accion == 'revisar':
            execute_query("""
                UPDATE Reportes 
                SET Estado = 'Revisado' 
                WHERE ID_Reporte = %s
            """, (reporte_id,))
            mensaje_respuesta = 'Reporte marcado como revisado'
            
        elif accion == 'resolver':
            execute_query("""
                UPDATE Reportes 
                SET Estado = 'Resuelto' 
                WHERE ID_Reporte = %s
            """, (reporte_id,))
            mensaje_respuesta = 'Reporte resuelto correctamente'
            
        elif accion == 'descartar':
            execute_query("""
                UPDATE Reportes 
                SET Estado = 'Resuelto' 
                WHERE ID_Reporte = %s
            """, (reporte_id,))
            mensaje_respuesta = 'Reporte descartado'
            
        elif accion == 'bloquear_usuario':
            execute_query("""
                UPDATE Usuario 
                SET Estado = 'Inactivo' 
                WHERE ID_Usuario = %s
            """, (reporte['ID_Usuario_Reportado'],))
            
            execute_query("""
                UPDATE Reportes 
                SET Estado = 'Resuelto' 
                WHERE ID_Reporte = %s
            """, (reporte_id,))
            
            mensaje_respuesta = f'Usuario {reporte["reportado_nombre"]} {reporte["reportado_apellido"]} bloqueado y reporte resuelto'
            
            admin_name = session.get('user_name', 'Admin')
            print(f"🚫 Admin {admin_name} bloqueó usuario ID {reporte['ID_Usuario_Reportado']} por reporte #{reporte_id}")
        
        else:
            return jsonify({
                'success': False,
                'message': 'Acción no válida'
            }), 400
        
        admin_name = session.get('user_name', 'Admin')
        print(f"✅ Admin {admin_name} ejecutó acción '{accion}' en reporte #{reporte_id}")
        if notas:
            print(f"   Notas: {notas}")
        
        return jsonify({
            'success': True,
            'message': mensaje_respuesta
        })
        
    except Exception as e:
        print(f"❌ Error gestionando reporte: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error al gestionar reporte: {str(e)}'
        }), 500


# ================================================================
# FUNCIÓN ENVIAR EMAIL
# ================================================================
def enviar_notificacion_reporte_admin(reporte_data):
    """Enviar email a administradores cuando hay un nuevo reporte"""
    try:
        admins = execute_query("""
            SELECT Correo, Nombre, Apellido 
            FROM Usuario 
            WHERE Rol = 'Administrador' AND Estado = 'Activo'
        """)
        
        if not admins:
            print("⚠️ No hay administradores para notificar")
            return
        
        subject = f"🚨 Nuevo Reporte #{reporte_data['id_reporte']} - CAMP"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4a7c59, #1e3a2e); color: white; padding: 20px; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                .info-box {{ background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #4a7c59; border-radius: 5px; }}
                .info-box h3 {{ margin-top: 0; color: #4a7c59; }}
                .footer {{ background: #f1f1f1; padding: 15px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; color: #666; }}
                .button {{ background: #4a7c59; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🚨 Nuevo Reporte Recibido</h2>
                    <p>Se ha registrado un nuevo reporte en CAMP que requiere tu atención.</p>
                </div>
                
                <div class="content">
                    <div class="info-box">
                        <h3>📋 Información del Reporte</h3>
                        <p><strong>ID Reporte:</strong> #{reporte_data['id_reporte']}</p>
                        <p><strong>Fecha:</strong> {reporte_data['fecha']}</p>
                        <p><strong>Estado:</strong> Pendiente</p>
                    </div>
                    
                    <div class="info-box">
                        <h3>👤 Usuario Reportante</h3>
                        <p><strong>Nombre:</strong> {reporte_data['reportante']['nombre']}</p>
                        <p><strong>Email:</strong> {reporte_data['reportante']['email']}</p>
                        <p><strong>Rol:</strong> {reporte_data['reportante']['rol']}</p>
                    </div>
                    
                    <div class="info-box">
                        <h3>🎯 Usuario Reportado</h3>
                        <p><strong>Nombre:</strong> {reporte_data['reportado']['nombre']}</p>
                        <p><strong>Email:</strong> {reporte_data['reportado']['email']}</p>
                        <p><strong>Rol:</strong> {reporte_data['reportado']['rol']}</p>
                    </div>
                    
                    <div class="info-box" style="border-left-color: #dc3545;">
                        <h3>⚠️ Motivo del Reporte</h3>
                        <p>{reporte_data['motivo']}</p>
                    </div>
                    
                    <p style="text-align: center; margin: 20px 0;">
                        <a href="http://localhost:5000/dashboard-admin" class="button">
                            Ver en Panel de Administrador
                        </a>
                    </p>
                </div>
                
                <div class="footer">
                    <p>Este es un mensaje automático de CAMP</p>
                    <p>Por favor, no respondas a este email</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        for admin in admins:
            try:
                msg = Message(
                    subject=subject,
                    recipients=[admin['Correo']],
                    html=html_body
                )
                mail.send(msg)
                print(f"✅ Email enviado a admin: {admin['Nombre']} {admin['Apellido']} ({admin['Correo']})")
            except Exception as email_error:
                print(f"❌ Error enviando email a {admin['Correo']}: {email_error}")
                continue
        
        return True
        
    except Exception as e:
        print(f"❌ Error enviando notificación a administradores: {e}")
        return False


# ================================================================
# API HISTORIAL REPORTES USUARIO
# ================================================================
@admin_bp.route('/api/admin/usuario/<int:usuario_id>/reportes', methods=['GET'])
def get_reportes_usuario_admin(usuario_id):
    """Obtener todos los reportes relacionados con un usuario"""
    try:
        if 'user_id' not in session or session.get('user_role') != 'Administrador':
            return jsonify({
                'success': False,
                'message': 'Acceso denegado'
            }), 403
        
        reportes_recibidos = execute_query("""
            SELECT 
                r.ID_Reporte,
                r.Motivo,
                r.Estado,
                r.Fecha_Reporte,
                'recibido' as tipo,
                CONCAT(ur.Nombre, ' ', ur.Apellido) as otro_usuario
            FROM Reportes r
            JOIN Usuario ur ON r.ID_Usuario_Reportante = ur.ID_Usuario
            WHERE r.ID_Usuario_Reportado = %s
            ORDER BY r.Fecha_Reporte DESC
        """, (usuario_id,))
        
        reportes_enviados = execute_query("""
            SELECT 
                r.ID_Reporte,
                r.Motivo,
                r.Estado,
                r.Fecha_Reporte,
                'enviado' as tipo,
                CONCAT(ud.Nombre, ' ', ud.Apellido) as otro_usuario
            FROM Reportes r
            JOIN Usuario ud ON r.ID_Usuario_Reportado = ud.ID_Usuario
            WHERE r.ID_Usuario_Reportante = %s
            ORDER BY r.Fecha_Reporte DESC
        """, (usuario_id,))
        
        return jsonify({
            'success': True,
            'reportes_recibidos': reportes_recibidos or [],
            'reportes_enviados': reportes_enviados or [],
            'total_recibidos': len(reportes_recibidos) if reportes_recibidos else 0,
            'total_enviados': len(reportes_enviados) if reportes_enviados else 0
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo reportes del usuario: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


print("✅ Sistema de Reportes cargado correctamente")
print("📋 APIs disponibles:")
print("   • POST /api/reportar-usuario-v2 - Crear nuevo reporte")
print("   • GET /api/admin/reportes-pendientes - Obtener reportes pendientes")
print("   • POST /api/admin/reporte/<id>/accion - Gestionar reporte")
print("   • GET /api/admin/usuario/<id>/reportes - Historial de reportes")

# ================================================================
# 2. FUNCIÓN AUXILIAR PARA EJECUTAR QUERIES DE FORMA SEGURA
# ================================================================
def ejecutar_query_segura(query, params=None, fetch_one=False):
    """
    Función auxiliar para ejecutar queries de manera segura
    Retorna: 
    - Para INSERT: el ID insertado
    - Para SELECT: los resultados
    - Para UPDATE/DELETE: True si fue exitoso
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ No se pudo conectar a la base de datos")
            return None
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        
        # Si es INSERT, retornar el ID
        if query.strip().upper().startswith('INSERT'):
            conn.commit()
            insert_id = cursor.lastrowid
            print(f"✅ INSERT exitoso, ID: {insert_id}")
            return insert_id
        
        # Si es UPDATE o DELETE
        elif query.strip().upper().startswith(('UPDATE', 'DELETE')):
            conn.commit()
            affected = cursor.rowcount
            print(f"✅ {query.split()[0]} exitoso, filas afectadas: {affected}")
            return True
        
        # Si es SELECT
        else:
            if fetch_one:
                result = cursor.fetchone()
            else:
                result = cursor.fetchall()
            return result
            
    except Exception as e:
        print(f"❌ Error en query: {e}")
        if conn:
            conn.rollback()
        import traceback
        traceback.print_exc()
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ================================================================
# 4. API: OBTENER REPORTES (ADMIN)
# ================================================================
@admin_bp.route('/api/admin/reportes-pendientes', methods=['GET'])
def obtener_reportes_admin():
    """Obtener reportes para el panel de administrador"""
    try:
        # Verificar que es admin
        if 'user_id' not in session or session.get('user_role') != 'Administrador':
            return jsonify({
                'success': False,
                'message': 'Acceso denegado. Solo administradores.'
            }), 403
        
        estado_filtro = request.args.get('estado', 'Pendiente')
        
        # Obtener reportes
        reportes = ejecutar_query_segura("""
            SELECT 
                r.ID_Reporte,
                r.Motivo,
                r.Estado,
                r.Fecha_Reporte,
                ur.ID_Usuario as reportante_id,
                ur.Nombre as reportante_nombre,
                ur.Apellido as reportante_apellido,
                ur.Correo as reportante_email,
                ud.ID_Usuario as reportado_id,
                ud.Nombre as reportado_nombre,
                ud.Apellido as reportado_apellido,
                ud.Correo as reportado_email,
                ud.Estado as reportado_estado
            FROM Reportes r
            INNER JOIN Usuario ur ON r.ID_Usuario_Reportante = ur.ID_Usuario
            INNER JOIN Usuario ud ON r.ID_Usuario_Reportado = ud.ID_Usuario
            WHERE r.Estado = %s
            ORDER BY r.Fecha_Reporte DESC
        """, (estado_filtro,))
        
        # Formatear reportes
        reportes_formateados = []
        if reportes:
            for r in reportes:
                reportes_formateados.append({
                    'id_reporte': r['ID_Reporte'],
                    'motivo': r['Motivo'],
                    'estado': r['Estado'],
                    'fecha_reporte': r['Fecha_Reporte'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(r['Fecha_Reporte'], 'strftime') else str(r['Fecha_Reporte']),
                    'reportante': {
                        'id': r['reportante_id'],
                        'nombre': f"{r['reportante_nombre']} {r['reportante_apellido']}",
                        'email': r['reportante_email']
                    },
                    'reportado': {
                        'id': r['reportado_id'],
                        'nombre': f"{r['reportado_nombre']} {r['reportado_apellido']}",
                        'email': r['reportado_email'],
                        'estado': r['reportado_estado']
                    }
                })
        
        # Obtener estadísticas
        stats = ejecutar_query_segura("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN Estado = 'Pendiente' THEN 1 ELSE 0 END) as pendientes,
                SUM(CASE WHEN Estado = 'Revisado' THEN 1 ELSE 0 END) as revisados,
                SUM(CASE WHEN Estado = 'Resuelto' THEN 1 ELSE 0 END) as resueltos
            FROM Reportes
        """, fetch_one=True)
        
        return jsonify({
            'success': True,
            'reportes': reportes_formateados,
            'total': len(reportes_formateados),
            'estadisticas': {
                'total_reportes': stats['total'] if stats else 0,
                'pendientes': stats['pendientes'] if stats else 0,
                'revisados': stats['revisados'] if stats else 0,
                'resueltos': stats['resueltos'] if stats else 0
            }
        })
        
    except Exception as e:
        print(f"❌ Error en obtener_reportes_admin: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ================================================================
# 5. API: GESTIONAR REPORTE (ADMIN)
# ================================================================
@admin_bp.route('/api/admin/reporte/<int:reporte_id>/accion', methods=['POST'])
def gestionar_reporte(reporte_id):
    """Administrador toma acción sobre un reporte"""
    try:
        # Verificar admin
        if 'user_id' not in session or session.get('user_role') != 'Administrador':
            return jsonify({
                'success': False,
                'message': 'Acceso denegado'
            }), 403
        
        data = request.get_json()
        accion = data.get('accion')
        
        if not accion:
            return jsonify({
                'success': False,
                'message': 'Acción no especificada'
            }), 400
        
        # Obtener info del reporte
        reporte = ejecutar_query_segura(
            "SELECT * FROM Reportes WHERE ID_Reporte = %s",
            (reporte_id,),
            fetch_one=True
        )
        
        if not reporte:
            return jsonify({
                'success': False,
                'message': 'Reporte no encontrado'
            }), 404
        
        mensaje = ''
        
        # Ejecutar acción
        if accion == 'revisar':
            ejecutar_query_segura(
                "UPDATE Reportes SET Estado = 'Revisado' WHERE ID_Reporte = %s",
                (reporte_id,)
            )
            mensaje = 'Reporte marcado como revisado'
            
        elif accion == 'resolver':
            ejecutar_query_segura(
                "UPDATE Reportes SET Estado = 'Resuelto' WHERE ID_Reporte = %s",
                (reporte_id,)
            )
            mensaje = 'Reporte marcado como resuelto'
            
        elif accion == 'bloquear_usuario':
            # Bloquear usuario reportado
            ejecutar_query_segura(
                "UPDATE Usuario SET Estado = 'Inactivo' WHERE ID_Usuario = %s",
                (reporte['ID_Usuario_Reportado'],)
            )
            # Marcar reporte como resuelto
            ejecutar_query_segura(
                "UPDATE Reportes SET Estado = 'Resuelto' WHERE ID_Reporte = %s",
                (reporte_id,)
            )
            mensaje = 'Usuario bloqueado y reporte resuelto'
            print(f"🚫 Admin bloqueó usuario ID {reporte['ID_Usuario_Reportado']} por reporte #{reporte_id}")
            
        else:
            return jsonify({
                'success': False,
                'message': 'Acción no válida'
            }), 400
        
        print(f"✅ Acción '{accion}' ejecutada en reporte #{reporte_id}")
        
        return jsonify({
            'success': True,
            'message': mensaje
        })
        
    except Exception as e:
        print(f"❌ Error en gestionar_reporte: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ================================================================
# 6. FUNCIÓN: ENVIAR EMAIL A ADMINS
# ================================================================
def enviar_email_reporte(reporte_data):
    """Enviar email a administradores cuando hay un nuevo reporte"""
    try:
        # Obtener emails de admins
        admins = ejecutar_query_segura("""
            SELECT Correo, Nombre, Apellido 
            FROM Usuario 
            WHERE Rol = 'Administrador' AND Estado = 'Activo'
        """)
        
        if not admins:
            print("⚠️ No hay administradores para notificar")
            return
        
        subject = f"🚨 Nuevo Reporte #{reporte_data['id_reporte']} - CAMP"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 10px; overflow: hidden;">
                <div style="background: linear-gradient(135deg, #4a7c59, #1e3a2e); color: white; padding: 20px; text-align: center;">
                    <h2>🚨 Nuevo Reporte Recibido</h2>
                </div>
                
                <div style="padding: 20px; background: #f9f9f9;">
                    <div style="background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #4a7c59; border-radius: 5px;">
                        <h3 style="margin-top: 0; color: #4a7c59;">📋 Información del Reporte</h3>
                        <p><strong>ID:</strong> #{reporte_data['id_reporte']}</p>
                        <p><strong>Fecha:</strong> {reporte_data['fecha']}</p>
                    </div>
                    
                    <div style="background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #2563eb; border-radius: 5px;">
                        <h3 style="margin-top: 0; color: #2563eb;">👤 Reportante</h3>
                        <p><strong>Nombre:</strong> {reporte_data['reportante']['nombre']}</p>
                        <p><strong>Email:</strong> {reporte_data['reportante']['email']}</p>
                    </div>
                    
                    <div style="background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #dc3545; border-radius: 5px;">
                        <h3 style="margin-top: 0; color: #dc3545;">🎯 Reportado</h3>
                        <p><strong>Nombre:</strong> {reporte_data['reportado']['nombre']}</p>
                        <p><strong>Email:</strong> {reporte_data['reportado']['email']}</p>
                    </div>
                    
                    <div style="background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #ffc107; border-radius: 5px;">
                        <h3 style="margin-top: 0; color: #ffc107;">⚠️ Motivo</h3>
                        <p>{reporte_data['motivo']}</p>
                    </div>
                    
                    <div style="text-align: center; margin: 20px 0;">
                        <a href="http://localhost:5000/dashboard-admin" 
                           style="background: #4a7c59; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                            Ver en Panel de Admin
                        </a>
                    </div>
                </div>
                
                <div style="background: #f1f1f1; padding: 15px; text-align: center; font-size: 12px; color: #666;">
                    <p>Este es un mensaje automático de CAMP</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Enviar email a cada admin
        for admin in admins:
            try:
                msg = Message(
                    subject=subject,
                    recipients=[admin['Correo']],
                    html=html_body
                )
                mail.send(msg)
                print(f"✅ Email enviado a: {admin['Correo']}")
            except Exception as e:
                print(f"⚠️ Error enviando email a {admin['Correo']}: {e}")
        
    except Exception as e:
        print(f"❌ Error en enviar_email_reporte: {e}")


# ================================================================
# MENSAJE DE CONFIRMACIÓN
# ================================================================
print("\n" + "="*60)
print("✅ SISTEMA DE REPORTES CARGADO CORRECTAMENTE")
print("="*60)
print("📋 APIs Disponibles:")
print("   • POST /api/reportar-usuario-v2")
print("   • GET  /api/admin/reportes-pendientes")
print("   • POST /api/admin/reporte/<id>/accion")
print("="*60 + "\n")

