# ================================================================
# helpers.py — Funciones compartidas entre todos los blueprints
# Importar desde cualquier blueprint con:
#   from blueprints.helpers import require_login, require_role, hash_password, verify_password
# ================================================================

from flask import session, request, redirect, jsonify
from functools import wraps
import bcrypt
import mysql.connector
import logging

logger = logging.getLogger(__name__)


def get_db_connection():
    """Crear conexión a la base de datos MySQL"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='camp',
            user='root',
            password='123456',
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        return connection
    except mysql.connector.Error as e:
        logger.error(f"Error conectando a la base de datos: {e}")
        raise

create_connection = get_db_connection


def require_login(f):
    """Decorador para rutas que requieren autenticación"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': True, 'message': 'Autenticación requerida'}), 401
            else:
                return redirect('/vista/login-trabajador.html')
        return f(*args, **kwargs)
    return decorated_function


def require_role(required_role):
    """Decorador para rutas que requieren un rol específico"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.is_json:
                    return jsonify({'error': True, 'message': 'Autenticación requerida'}), 401
                else:
                    return redirect('/vista/login-trabajador.html')
            if session.get('user_role') != required_role:
                if request.is_json:
                    return jsonify({'error': True, 'message': 'Permisos insuficientes'}), 403
                else:
                    current_role = session.get('user_role', 'Trabajador')
                    if current_role == 'Agricultor':
                        return redirect('/vista/dashboard-agricultor.html')
                    elif current_role == 'Administrador':
                        return redirect('/vista/index-administrador.html')
                    else:
                        return redirect('/vista/index-trabajador.html')
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def hash_password(password):
    """Hashea la contraseña usando bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password, hashed):
    """Verifica una contraseña contra su hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def no_cache(view):
    """Decorador para prevenir caché del navegador"""
    from flask import make_response
    @wraps(view)
    def no_cache_view(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
    return no_cache_view
