"""
Script para crear el usuario administrador inicial de CAMP.
Ejecutar una sola vez después de configurar la base de datos.

Uso:
    cd conexion
    python crear_admin.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import hash_password
from conexion import execute_query

# Datos del administrador
ADMIN_EMAIL = "admin@camp.com"
ADMIN_PASSWORD = "admin123"

# Hashear la contraseña
hashed_password = hash_password(ADMIN_PASSWORD)

# Insertar en la base de datos
try:
    user_id = execute_query(
        """INSERT INTO Usuario (Nombre, Apellido, Correo, Contrasena, Rol, Estado) 
           VALUES (%s, %s, %s, %s, %s, %s)""",
        ("Admin", "Principal", ADMIN_EMAIL, hashed_password, "Administrador", "Activo")
    )
    print(f"✅ Administrador creado con ID: {user_id}")
    print(f"   Email: {ADMIN_EMAIL}")
    print(f"   Contraseña: {ADMIN_PASSWORD}")
    print("\n⚠️  Cambia la contraseña después del primer inicio de sesión.")
except Exception as e:
    print(f"❌ Error creando administrador: {e}")
