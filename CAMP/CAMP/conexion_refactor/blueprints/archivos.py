# Blueprint: archivos
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

archivos_bp = Blueprint('archivos', __name__)

def _find_root():
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        if os.path.isdir(os.path.join(current, 'vista')):
            return current
        current = os.path.dirname(current)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT_ROOT = _find_root()
from blueprints.helpers import require_login, require_role, hash_password, verify_password, no_cache


# ================================================================
# RUTAS PARA MANEJO DE FOTOS DE PERFIL
# ================================================================

@archivos_bp.route('/api/upload-profile-photo', methods=['POST'])
@require_login
def upload_profile_photo():
    """Subir foto de perfil del usuario"""
    try:
        user_id = session['user_id']
        
        if 'profilePhoto' not in request.files:
            return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'}), 400
        
        file = request.files['profilePhoto']
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'}), 400
        
        # Usar la nueva función allowed_file
        if not allowed_file(file.filename, ALLOWED_EXTENSIONS_IMAGES):
            return jsonify({
                'success': False, 
                'message': 'Formato de archivo no válido. Use PNG, JPG, JPEG o GIF'
            }), 400
        
        # Validar tamaño
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False, 
                'message': 'El archivo es muy grande. Tamaño máximo: 5MB'
            }), 400
        
        # Generar nombre único para el archivo
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"profile_{user_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
        
        # Guardar en la carpeta correcta
        file_path = os.path.join(PROFILE_PHOTOS_FOLDER, unique_filename)
        file.save(file_path)
        
        # URL relativa para la base de datos
        photo_url = f"/static/uploads/profile_photos/{unique_filename}"
        
        # Actualizar URL_Foto en la tabla Usuario (tu tabla existente)
        execute_query(
            "UPDATE Usuario SET URL_Foto = %s WHERE ID_Usuario = %s",
            (photo_url, user_id)
        )
        
        # Registrar en tabla Anexo para historial (tu tabla existente)
        execute_query(
            """INSERT INTO Anexo (ID_Usuario, Tipo_Archivo, URL_Archivo, Descripcion) 
               VALUES (%s, 'Imagen', %s, 'Foto de perfil')""",
            (user_id, photo_url)
        )
        
        print(f"Foto de perfil actualizada para usuario {user_id}: {photo_url}")
        
        return jsonify({
            'success': True,
            'message': 'Foto de perfil actualizada correctamente',
            'photoUrl': photo_url
        })
        
    except Exception as e:
        print(f"Error subiendo foto de perfil: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ================================================================
# RUTAS PARA CONFIGURACIÓN DEL TRABAJADOR
# ================================================================

@archivos_bp.route('/static/uploads/<path:filename>')
def serve_uploaded_file(filename):
    """Servir archivos subidos desde la carpeta de uploads"""
    try:
        # Obtener la ruta absoluta de la carpeta de uploads
        base_dir = PROJECT_ROOT
        uploads_path = os.path.join(base_dir, '..', 'static', 'uploads')
        uploads_path = os.path.abspath(uploads_path)
        
        # Verificar que el archivo existe
        file_path = os.path.join(uploads_path, filename)
        if not os.path.exists(file_path):
            print(f"❌ Archivo no encontrado: {file_path}")
            return "Archivo no encontrado", 404
        
        print(f"✅ Sirviendo archivo: {file_path}")
        return send_from_directory(uploads_path, filename)
        
    except Exception as e:
        print(f"❌ Error sirviendo archivo: {str(e)}")
        return f"Error sirviendo archivo: {str(e)}", 500


# ================================================================
# la función para subir documentos usando tu tabla Anexo
# ================================================================

@archivos_bp.route('/api/upload-document', methods=['POST'])
@require_login
def upload_document():
    """Subir documento usando tabla Anexo existente"""
    try:
        user_id = session['user_id']
        
        if 'document' not in request.files:
            return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'}), 400
        
        file = request.files['document']
        doc_type = request.form.get('docType', 'Documento')
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'}), 400
        
        # Verificar tipo de archivo
        if not allowed_file(file.filename, ALLOWED_EXTENSIONS_DOCS):
            return jsonify({'success': False, 'message': 'Formato de archivo no válido'}), 400
        
        # Verificar tamaño
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'success': False, 'message': 'Archivo muy grande. Máximo 5MB'}), 400
        
        # Generar nombre único
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"doc_{user_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
        
        # Guardar archivo
        file_path = os.path.abspath(os.path.join(DOCUMENTS_FOLDER, unique_filename))
        file.save(file_path)
        
        # URL relativa
        doc_url = f"/static/uploads/documents/{unique_filename}"
        
        # Guardar en tabla Anexo (tu tabla existente)
        execute_query(
            """INSERT INTO Anexo (ID_Usuario, Tipo_Archivo, URL_Archivo, Descripcion) 
               VALUES (%s, 'Documento', %s, %s)""",
            (user_id, doc_url, f"{doc_type} - {file.filename}")
        )
        
        print(f"Documento subido: {doc_url}")
        
        return jsonify({
            'success': True,
            'message': 'Documento subido correctamente',
            'documentUrl': doc_url,
            'fileName': file.filename
        })
        
    except Exception as e:
        print(f"Error subiendo documento: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ================================================================
#  función para obtener documentos subidos
# ================================================================

@archivos_bp.route('/api/get-documents', methods=['GET'])
@require_login
def get_documents():
    """Obtener documentos del usuario desde tabla Anexo"""
    try:
        user_id = session['user_id']
        
        documents = execute_query(
            """SELECT ID_Anexo, Tipo_Archivo, URL_Archivo, Descripcion, Fecha_Subida
               FROM Anexo 
               WHERE ID_Usuario = %s AND Tipo_Archivo = 'Documento'
               ORDER BY Fecha_Subida DESC""",
            (user_id,)
        )
        
        return jsonify({
            'success': True,
            'documents': documents or []
        })
        
    except Exception as e:
        print(f"Error obteniendo documentos: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ENDPOINTS FALTANTES 

# 1. Endpoint para obtener documentos del usuario
@archivos_bp.route('/api/user-documents', methods=['GET'])
@require_login
def get_user_documents():
    try:
        user_id = session['user_id']
        
        # Usar tu tabla Anexo existente
        documentos = execute_query(
            """SELECT ID_Anexo, Tipo_Archivo, URL_Archivo, Descripcion, Fecha_Subida
               FROM Anexo 
               WHERE ID_Usuario = %s 
               ORDER BY Fecha_Subida DESC""",
            (user_id,)
        )
        
        documents_list = []
        if documentos:
            for doc in documentos:
                # Extraer nombre del archivo de la URL
                archivo_nombre = os.path.basename(doc['URL_Archivo']) if doc['URL_Archivo'] else 'Sin nombre'
                
                documents_list.append({
                    'id': doc['ID_Anexo'],
                    'tipo_documento': doc['Tipo_Archivo'],
                    'nombre_archivo': archivo_nombre,
                    'url_documento': doc['URL_Archivo'],
                    'fecha_subida': doc['Fecha_Subida'].strftime('%Y-%m-%d %H:%M:%S') if doc['Fecha_Subida'] else None,
                    'estado': 'Subido',
                    'descripcion': doc['Descripcion']
                })
        
        return jsonify({
            'success': True,
            'documents': documents_list
        })
        
    except Exception as e:
        print(f"Error al obtener documentos: {e}")
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500


@archivos_bp.route('/api/documentos-usuario/<int:user_id>', methods=['GET'])
def get_documentos_usuario(user_id):
    try:
        # Verificar que el usuario esté autenticado
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        print(f"🔍 Buscando documentos para usuario: {user_id}")
        
        # Conexión directa usando mysql.connector
        conn = mysql.connector.connect(
            host='localhost',
            database='camp',
            user='root',
            password='123456',
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        
        cursor = conn.cursor()
        
        query = """
            SELECT 
                ID_Anexo,
                Tipo_Archivo,
                URL_Archivo,
                Descripcion,
                Fecha_Subida
            FROM anexo
            WHERE ID_Usuario = %s
            ORDER BY Fecha_Subida DESC
        """
        
        cursor.execute(query, (user_id,))
        documentos_raw = cursor.fetchall()
        
        print(f"📄 Registros encontrados en BD: {len(documentos_raw)}")
        
        cursor.close()
        conn.close()
        
        # Formatear documentos
        documentos = []
        for doc in documentos_raw:
            documento = {
                'id': doc[0],
                'tipo_documento': doc[3] if doc[3] else doc[1],  # Descripcion o Tipo_Archivo
                'archivo_url': doc[2],
                'descripcion': doc[3],
                'fecha_subida': doc[4].isoformat() if doc[4] else None
            }
            documentos.append(documento)
            print(f"  ✅ Doc {doc[0]}: {documento['tipo_documento']} - {documento['archivo_url']}")
        
        print(f"✅ Total documentos formateados: {len(documentos)}")
        
        return jsonify({
            'success': True,
            'documentos': documentos,
            'total': len(documentos)
        })
        
    except mysql.connector.Error as db_error:
        print(f"❌ Error de base de datos: {db_error}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error de base de datos: {str(db_error)}'
        }), 500
        
    except Exception as e:
        print(f"❌ Error general obteniendo documentos: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error al obtener documentos: {str(e)}'
        }), 500


# ===================================================================
# ENDPOINT EXCLUSIVO PARA VER DOCUMENTOS DESDE PERFIL DE POSTULACIONES
# ===================================================================

@archivos_bp.route('/api/ver-documentos-trabajador/<int:trabajador_id>', methods=['GET'])
def ver_documentos_trabajador_perfil(trabajador_id):
    """
    Endpoint exclusivo para ver documentos desde el modal de perfil
    Ruta: /api/ver-documentos-trabajador/<trabajador_id>
    """
    try:
        # Verificar que el usuario esté autenticado
        if 'user_id' not in session:
            print('❌ Usuario no autenticado')
            return jsonify({
                'success': False, 
                'message': 'No autenticado'
            }), 401
        
        # Verificar que sea agricultor
        user_role = session.get('user_role') or session.get('role')
        if user_role != 'Agricultor':
            print(f'❌ Usuario no es agricultor: {user_role}')
            return jsonify({
                'success': False,
                'message': 'Solo agricultores pueden ver documentos'
            }), 403
        
        print(f'🔍 Agricultor {session["user_id"]} solicita documentos de trabajador {trabajador_id}')
        
        # Conectar a la base de datos
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Query para obtener documentos del trabajador
        query = """
            SELECT 
                ID_Anexo,
                Tipo_Archivo,
                URL_Archivo,
                Descripcion,
                Fecha_Subida
            FROM Anexo
            WHERE ID_Usuario = %s
            ORDER BY Fecha_Subida DESC
        """
        
        cursor.execute(query, (trabajador_id,))
        documentos_raw = cursor.fetchall()
        
        print(f'📄 Documentos encontrados en BD: {len(documentos_raw)}')
        
        # Cerrar conexión
        cursor.close()
        connection.close()
        
        # Si no hay documentos, retornar lista vacía (no error)
        if not documentos_raw or len(documentos_raw) == 0:
            print('ℹ️ No se encontraron documentos para este trabajador')
            return jsonify({
                'success': True,
                'documentos': [],
                'total': 0,
                'message': 'Este trabajador no ha subido documentos'
            }), 200
        
        # Formatear documentos para el frontend
        documentos = []
        for doc in documentos_raw:
            # Determinar el nombre del documento
            nombre_documento = doc.get('Descripcion') or doc.get('Tipo_Archivo') or 'Documento'
            
            # Crear objeto de documento
            documento = {
                'id': doc['ID_Anexo'],
                'tipo_documento': nombre_documento,
                'tipo_archivo': doc.get('Tipo_Archivo'),
                'archivo_url': doc.get('URL_Archivo'),
                'descripcion': doc.get('Descripcion'),
                'fecha_subida': doc['Fecha_Subida'].isoformat() if doc.get('Fecha_Subida') else None
            }
            
            documentos.append(documento)
            print(f'  ✅ Doc {doc["ID_Anexo"]}: {nombre_documento} - {doc.get("URL_Archivo")}')
        
        print(f'✅ Total documentos formateados: {len(documentos)}')
        
        # Retornar respuesta exitosa
        return jsonify({
            'success': True,
            'documentos': documentos,
            'total': len(documentos),
            'trabajador_id': trabajador_id
        }), 200
        
    except Exception as e:
        print(f'❌ Error obteniendo documentos del trabajador: {str(e)}')
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': f'Error al obtener documentos: {str(e)}',
            'documentos': [],
            'total': 0
        }), 500

# Mensaje de confirmación
print('✅ Endpoint /api/ver-documentos-trabajador/<trabajador_id> cargado correctamente')
print('   📌 Uso: GET /api/ver-documentos-trabajador/123')
print('   📌 Exclusivo para modal de perfil de postulaciones')

