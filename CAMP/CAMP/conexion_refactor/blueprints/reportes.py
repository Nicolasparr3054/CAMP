# Blueprint: reportes
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

reportes_bp = Blueprint('reportes', __name__)
from blueprints.helpers import require_login, require_role, hash_password, verify_password, no_cache


# ================================================================
# API PARA REPORTAR USUARIOS
# ================================================================

@reportes_bp.route('/api/reportar-usuario', methods=['POST'])
def reportar_usuario():
    """API para reportar usuarios problemáticos"""
    try:
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'message': 'Sesión no válida'
            }), 401
        
        data = request.get_json()
        usuario_reportado = data.get('usuario_reportado')
        motivo = data.get('motivo', '').strip()
        
        if not usuario_reportado or not motivo:
            return jsonify({
                'success': False,
                'message': 'Datos incompletos'
            }), 400
        
        # Crear tabla de reportes si no existe
        execute_query("""
            CREATE TABLE IF NOT EXISTS Reporte_Usuario (
                ID_Reporte INT PRIMARY KEY AUTO_INCREMENT,
                ID_Usuario_Reportante INT NOT NULL,
                ID_Usuario_Reportado INT NOT NULL,
                Motivo TEXT NOT NULL,
                Fecha_Reporte DATETIME DEFAULT CURRENT_TIMESTAMP,
                Estado ENUM('Pendiente', 'Revisado', 'Resuelto') DEFAULT 'Pendiente',
                FOREIGN KEY (ID_Usuario_Reportante) REFERENCES Usuario(ID_Usuario),
                FOREIGN KEY (ID_Usuario_Reportado) REFERENCES Usuario(ID_Usuario)
            )
        """)
        
        # Insertar reporte
        execute_query("""
            INSERT INTO Reporte_Usuario (ID_Usuario_Reportante, ID_Usuario_Reportado, Motivo)
            VALUES (%s, %s, %s)
        """, (session['user_id'], usuario_reportado, motivo))
        
        print(f"⚠️ Usuario {session['user_id']} reportó al usuario {usuario_reportado}: {motivo}")
        
        return jsonify({
            'success': True,
            'message': 'Reporte enviado correctamente'
        })
        
    except Exception as e:
        print(f"❌ Error reportando usuario: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


print("✅ Sistema de reportes cargado correctamente")


# ================================================================
# SISTEMA DE REPORTES - BACKEND COMPLETO
# AGREGAR AL FINAL DE app.py (ANTES DE if __name__ == '__main__':)
# ================================================================

# ================================================================
# API PARA REPORTAR USUARIO - ÚNICA VERSIÓN
# ================================================================
@reportes_bp.route('/api/reportar-usuario-v2', methods=['POST'])
def reportar_usuario_v2():
    """Endpoint para que un usuario reporte a otro - VERSIÓN MEJORADA"""
    try:
        if 'user_id' not in session:
            return jsonify({
                'success': False, 
                'message': 'Debes iniciar sesión para reportar'
            }), 401
        
        data = request.get_json()
        
        if not data.get('usuario_reportado') or not data.get('motivo'):
            return jsonify({
                'success': False,
                'message': 'Datos incompletos. Se requiere usuario y motivo'
            }), 400
        
        usuario_reportante = session['user_id']
        usuario_reportado = data['usuario_reportado']
        motivo = data['motivo'].strip()
        
        if len(motivo) < 10:
            return jsonify({
                'success': False,
                'message': 'El motivo debe tener al menos 10 caracteres'
            }), 400
        
        usuario_existe = execute_query("""
            SELECT ID_Usuario, Nombre, Apellido, Correo, Rol 
            FROM Usuario 
            WHERE ID_Usuario = %s
        """, (usuario_reportado,), fetch_one=True)
        
        if not usuario_existe:
            return jsonify({
                'success': False,
                'message': 'Usuario reportado no encontrado'
            }), 404
        
        if usuario_reportante == usuario_reportado:
            return jsonify({
                'success': False,
                'message': 'No puedes reportarte a ti mismo'
            }), 400
        
        reporte_existente = execute_query("""
            SELECT ID_Reporte 
            FROM Reportes 
            WHERE ID_Usuario_Reportante = %s 
              AND ID_Usuario_Reportado = %s 
              AND Estado = 'Pendiente'
        """, (usuario_reportante, usuario_reportado), fetch_one=True)
        
        if reporte_existente:
            return jsonify({
                'success': False,
                'message': 'Ya tienes un reporte pendiente sobre este usuario'
            }), 400
        
        reportante_info = execute_query("""
            SELECT Nombre, Apellido, Correo, Rol 
            FROM Usuario 
            WHERE ID_Usuario = %s
        """, (usuario_reportante,), fetch_one=True)
        
        reporte_id = execute_query("""
            INSERT INTO Reportes (
                ID_Usuario_Reportante, 
                ID_Usuario_Reportado, 
                Motivo, 
                Estado, 
                Fecha_Reporte
            )
            VALUES (%s, %s, %s, 'Pendiente', NOW())
        """, (usuario_reportante, usuario_reportado, motivo))
        
        reporte_data = {
            'id_reporte': reporte_id,
            'reportante': {
                'id': usuario_reportante,
                'nombre': f"{reportante_info['Nombre']} {reportante_info['Apellido']}",
                'email': reportante_info['Correo'],
                'rol': reportante_info['Rol']
            },
            'reportado': {
                'id': usuario_reportado,
                'nombre': f"{usuario_existe['Nombre']} {usuario_existe['Apellido']}",
                'email': usuario_existe['Correo'],
                'rol': usuario_existe['Rol']
            },
            'motivo': motivo,
            'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            enviar_notificacion_reporte_admin(reporte_data)
        except Exception as email_error:
            print(f"⚠️ Error enviando email: {email_error}")
        
        print(f"📢 NUEVO REPORTE:")
        print(f"   ID Reporte: {reporte_id}")
        print(f"   Reportante: {reporte_data['reportante']['nombre']} (ID: {usuario_reportante})")
        print(f"   Reportado: {reporte_data['reportado']['nombre']} (ID: {usuario_reportado})")
        print(f"   Motivo: {motivo}")
        
        return jsonify({
            'success': True,
            'message': 'Reporte enviado correctamente. Será revisado por un administrador.',
            'reporte_id': reporte_id
        })
        
    except Exception as e:
        print(f"❌ Error creando reporte: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error al procesar el reporte: {str(e)}'
        }), 500


# ================================================================
# 3. API: CREAR REPORTE
# ================================================================
@reportes_bp.route('/api/reportar-usuario-v2', methods=['POST'])
def reportar_usuario_nuevo():
    """Endpoint para reportar usuarios - VERSIÓN NUEVA"""
    try:
        # 1. Verificar autenticación
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'message': 'Debes iniciar sesión para reportar'
            }), 401
        
        # 2. Obtener datos
        data = request.get_json()
        usuario_reportante = session['user_id']
        usuario_reportado = data.get('usuario_reportado')
        motivo = data.get('motivo', '').strip()
        
        print(f"\n📋 NUEVO REPORTE:")
        print(f"   Reportante: {usuario_reportante}")
        print(f"   Reportado: {usuario_reportado}")
        print(f"   Motivo: {motivo}")
        
        # 3. Validaciones
        if not usuario_reportado or not motivo:
            return jsonify({
                'success': False,
                'message': 'Faltan datos: usuario_reportado y motivo son requeridos'
            }), 400
        
        if len(motivo) < 10:
            return jsonify({
                'success': False,
                'message': 'El motivo debe tener al menos 10 caracteres'
            }), 400
        
        if usuario_reportante == usuario_reportado:
            return jsonify({
                'success': False,
                'message': 'No puedes reportarte a ti mismo'
            }), 400
        
        # 4. Verificar que el usuario reportado existe
        usuario_existe = ejecutar_query_segura(
            "SELECT ID_Usuario, Nombre, Apellido, Correo FROM Usuario WHERE ID_Usuario = %s",
            (usuario_reportado,),
            fetch_one=True
        )
        
        if not usuario_existe:
            return jsonify({
                'success': False,
                'message': 'El usuario reportado no existe'
            }), 404
        
        # 5. Verificar que no hay reporte duplicado pendiente
        reporte_existente = ejecutar_query_segura(
            """SELECT ID_Reporte FROM Reportes 
               WHERE ID_Usuario_Reportante = %s 
               AND ID_Usuario_Reportado = %s 
               AND Estado = 'Pendiente'""",
            (usuario_reportante, usuario_reportado),
            fetch_one=True
        )
        
        if reporte_existente:
            return jsonify({
                'success': False,
                'message': 'Ya tienes un reporte pendiente sobre este usuario'
            }), 400
        
        # 6. Insertar el reporte en la base de datos
        reporte_id = ejecutar_query_segura(
            """INSERT INTO Reportes 
               (ID_Usuario_Reportante, ID_Usuario_Reportado, Motivo, Estado, Fecha_Reporte)
               VALUES (%s, %s, %s, 'Pendiente', NOW())""",
            (usuario_reportante, usuario_reportado, motivo)
        )
        
        if not reporte_id:
            return jsonify({
                'success': False,
                'message': 'Error al guardar el reporte en la base de datos'
            }), 500
        
        print(f"✅ Reporte #{reporte_id} creado exitosamente")
        
        # 7. Obtener información del reportante para el email
        reportante_info = ejecutar_query_segura(
            "SELECT Nombre, Apellido, Correo FROM Usuario WHERE ID_Usuario = %s",
            (usuario_reportante,),
            fetch_one=True
        )
        
        # 8. Enviar notificación por email a administradores
        try:
            reporte_data = {
                'id_reporte': reporte_id,
                'reportante': {
                    'nombre': f"{reportante_info['Nombre']} {reportante_info['Apellido']}",
                    'email': reportante_info['Correo']
                },
                'reportado': {
                    'nombre': f"{usuario_existe['Nombre']} {usuario_existe['Apellido']}",
                    'email': usuario_existe['Correo']
                },
                'motivo': motivo,
                'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            enviar_email_reporte(reporte_data)
        except Exception as email_error:
            print(f"⚠️ Error enviando email (no crítico): {email_error}")
        
        # 9. Respuesta exitosa
        return jsonify({
            'success': True,
            'message': 'Reporte enviado correctamente. Un administrador lo revisará pronto.',
            'reporte_id': reporte_id
        }), 200
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO en reportar_usuario_nuevo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno del servidor: {str(e)}'
        }), 500

