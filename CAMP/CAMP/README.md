# CAMP 🌱
**Plataforma de conexión entre agricultores y trabajadores agrícolas**

## Descripción
CAMP es una aplicación web que conecta agricultores con trabajadores del sector agrícola en Colombia. Permite publicar ofertas de trabajo, postularse, gestionar contratos y calificaciones.

## Estructura del Proyecto
```
CAMP/
├── conexion/          # Backend Python/Flask
│   ├── app.py         # Aplicación principal (API REST)
│   └── conexion.py    # Módulo de conexión a MySQL
├── vista/             # Páginas HTML
├── assent/
│   └── css/           # Hojas de estilo
├── js/                # Scripts JavaScript
├── static/
│   └── uploads/       # Archivos subidos por usuarios
├── requirements.txt   # Dependencias Python
└── .env.example       # Variables de entorno (ejemplo)
```

## Requisitos
- Python 3.10+
- MySQL 8.0+
- Las dependencias listadas en `requirements.txt`

## Instalación

### 1. Base de datos
Importa el script SQL para crear la base de datos `camp`:
```sql
-- Ejecuta el archivo camp_database.sql en tu servidor MySQL
```

### 2. Instalar dependencias Python
```bash
pip install -r requirements.txt
```

### 3. Configurar conexión
Edita `conexion/conexion.py` con tus credenciales de MySQL:
```python
DB_CONFIG = {
    'host': 'localhost',
    'database': 'camp',
    'user': 'root'
}
PASSWORDS_TO_TRY = ['tu_contraseña']
```

### 4. Ejecutar el servidor
```bash
cd conexion
python app.py
```

El servidor estará disponible en `http://localhost:5000`

## Roles de Usuario
- **Trabajador**: Busca y aplica a ofertas de trabajo
- **Agricultor**: Publica ofertas y gestiona contrataciones
- **Administrador**: Panel de control completo

## Credenciales por defecto
- Admin: `admin@camp.com` / `admin123`

## Tecnologías
- **Backend**: Python + Flask
- **Base de datos**: MySQL
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
