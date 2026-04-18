"""
Script para verificar la conexión a la base de datos.

Uso:
    cd conexion
    python test_connection.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from conexion import get_connection

try:
    conn = get_connection()
    if conn and conn.is_connected():
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"✅ Conexión exitosa a MySQL {version[0]}")
        cursor.execute("SELECT DATABASE()")
        db = cursor.fetchone()
        print(f"   Base de datos activa: {db[0]}")
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"   Tablas encontradas: {len(tables)}")
        for table in tables:
            print(f"   • {table[0]}")
        cursor.close()
        conn.close()
except Exception as e:
    print(f"❌ Error de conexión: {e}")
    print("\nVerifica tu configuración en conexion/conexion.py")
