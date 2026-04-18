# ================================================================
# CAMP - app.py REFACTORIZADO
# Ruta: conexion/app.py
# ================================================================

from flask import Flask
from datetime import timedelta
import secrets
import logging

app = Flask(__name__)

# ================================================================
# CONFIGURACIÓN
# ================================================================
app.secret_key = secrets.token_hex(32)
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)

# Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'camp2025@gmail.com'
app.config['MAIL_PASSWORD'] = 'wfme fcns ubgw viju'
app.config['MAIL_DEFAULT_SENDER'] = 'camp2025@gmail.com'

try:
    from flask_mail import Mail
    mail = Mail(app)
except ImportError:
    mail = None

logging.basicConfig(level=logging.INFO)

# ================================================================
# REGISTRO DE BLUEPRINTS
# ================================================================
from blueprints.auth import auth_bp
from blueprints.ofertas import ofertas_bp
from blueprints.trabajadores import trabajadores_bp
from blueprints.contratos import contratos_bp
from blueprints.admin import admin_bp
from blueprints.archivos import archivos_bp
from blueprints.notificaciones import notif_bp
from blueprints.favoritos import favoritos_bp
from blueprints.reportes import reportes_bp
from blueprints.mapa import mapa_bp
from blueprints.estatico import estatico_bp

app.register_blueprint(auth_bp)
app.register_blueprint(ofertas_bp)
app.register_blueprint(trabajadores_bp)
app.register_blueprint(contratos_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(archivos_bp)
app.register_blueprint(notif_bp)
app.register_blueprint(favoritos_bp)
app.register_blueprint(reportes_bp)
app.register_blueprint(mapa_bp)
app.register_blueprint(estatico_bp)

print("✅ CAMP iniciado - todos los blueprints registrados")

# ================================================================
# INICIO DEL SERVIDOR
# ================================================================
if __name__ == '__main__':
    print("🌱 CAMP corriendo en http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

# ================================================================
# MANEJO DE ERRORES
# ================================================================
from flask import jsonify, request as flask_request

@app.errorhandler(404)
def not_found(error):
    import os
    requested_url = flask_request.url
    if '.html' in requested_url:
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            vista_path = os.path.join(base_dir, '..', 'vista')
            if os.path.exists(vista_path):
                html_files = [f for f in os.listdir(vista_path) if f.endswith('.html')]
                return jsonify({'error': True, 'message': 'Página no encontrada',
                                'status': 404, 'available': html_files}), 404
        except:
            pass
    return jsonify({'error': True, 'message': 'Página no encontrada', 'status': 404}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': True, 'message': 'Error interno del servidor',
                    'status': 500, 'details': str(error)}), 500

@app.before_request
def log_request_info():
    from flask import session
    if flask_request.endpoint and not any(s in flask_request.path for s in ['/css/', '/js/', '/img/', '/assent/']):
        print(f"🔍 {flask_request.method} {flask_request.path} | User: {session.get('user_name', 'Anónimo')}")
