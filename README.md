# 🌱 CAMP — Conexión Agrícola y Mercado de Personal

**Plataforma web que conecta agricultores con trabajadores del sector agrícola en Colombia.**

CAMP permite publicar ofertas de trabajo, postularse a ellas, gestionar contratos, calificar experiencias y administrar usuarios — todo desde una sola aplicación.

---

## 📋 Tabla de contenidos

- [Descripción](#descripción)
- [Características](#características)
- [Tecnologías](#tecnologías)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Requisitos previos](#requisitos-previos)
- [Instalación](#instalación)
- [Uso](#uso)
- [Roles de usuario](#roles-de-usuario)
- [Base de datos](#base-de-datos)
- [API REST](#api-rest)
- [Credenciales por defecto](#credenciales-por-defecto)
- [Historial de versiones](#historial-de-versiones)
- [Autores](#autores)

---

## Descripción

CAMP nació como proyecto de etapa lectiva con el objetivo de digitalizar la búsqueda de empleo agrícola en Colombia. Los agricultores pueden publicar ofertas de trabajo en sus fincas, y los trabajadores del campo pueden postularse, gestionar su perfil, habilidades y disponibilidad desde cualquier dispositivo.

---

## Características

- **Registro e inicio de sesión** con soporte para Google y Facebook (OAuth)
- **Tres roles diferenciados**: Trabajador, Agricultor y Administrador
- **Publicación y gestión de ofertas de trabajo** por parte de agricultores
- **Sistema de postulaciones** con estados: Pendiente, Aceptada, Rechazada
- **Acuerdos laborales** entre agricultores y trabajadores contratados
- **Sistema de calificaciones** bidireccional al finalizar un acuerdo
- **Perfil de trabajador** con habilidades, experiencia, documentos y disponibilidad
- **Búsqueda avanzada de trabajadores** por habilidades y disponibilidad
- **Sistema de favoritos** para guardar postulaciones de interés
- **Geolocalización** para mostrar ofertas y trabajadores cercanos
- **Notificaciones dinámicas** basadas en la actividad reciente
- **Panel de administrador** con estadísticas, gestión de usuarios y reportes
- **Sistema de reportes** entre usuarios
- **Recuperación de contraseña** por correo electrónico
- **Soporte multiidioma**: español, inglés y chino
- **Subida de fotos de perfil y documentos**

---

## Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | Python 3.10+ · Flask · Flask-Login · Flask-Mail |
| Base de datos | MySQL 8.0+ |
| Frontend | HTML5 · CSS3 · JavaScript (Vanilla) |
| Autenticación social | OAuth 2.0 (Google · Facebook) |
| Seguridad | bcrypt · Flask-Session |
| Email | SMTP Gmail |

---

## Estructura del proyecto

```
CAMP/
├── conexion_refactor/          # Backend principal (refactorizado en Blueprints)
│   ├── app.py                  # Configuración de Flask y registro de blueprints
│   ├── conexion.py             # Módulo de conexión a MySQL
│   ├── crear_admin.py          # Script para crear usuario administrador
│   └── blueprints/
│       ├── helpers.py          # Funciones compartidas (decoradores, hash, DB)
│       ├── auth.py             # Login, registro, logout, OAuth, recuperación
│       ├── ofertas.py          # Ofertas de trabajo y postulaciones
│       ├── trabajadores.py     # Perfil, habilidades, disponibilidad
│       ├── contratos.py        # Acuerdos laborales, historial, calificaciones
│       ├── admin.py            # Panel de administrador
│       ├── archivos.py         # Subida de fotos y documentos
│       ├── notificaciones.py   # Notificaciones dinámicas
│       ├── favoritos.py        # Sistema de favoritos
│       ├── reportes.py         # Reportar usuarios
│       ├── mapa.py             # Geolocalización
│       └── estatico.py         # Servir archivos HTML, CSS, JS
├── vista/                      # Páginas HTML
│   ├── inicio-sesion.html      # Landing page principal
│   ├── login-trabajador.html   # Login de trabajadores
│   ├── registro.html           # Registro unificado (trabajador y agricultor)
│   ├── index-trabajador.html
│   ├── index-agricultor.html
│   ├── index-administrador.html
│   └── ...                     # Resto de vistas
├── assent/
│   └── css/                    # Hojas de estilo por vista
│       ├── inicio-sesion.css
│       ├── login-trabajador.css
│       ├── registro.css        # Estilos del registro unificado
│       └── ...
├── js/                         # Scripts JavaScript
│   ├── registro.js             # Lógica del registro unificado
│   └── ...
├── static/
│   └── uploads/                # Archivos subidos por usuarios
├── camp_database.sql           # Script de creación de la base de datos
├── requirements.txt            # Dependencias Python
└── .env.example                # Variables de entorno de ejemplo
```

---

## Requisitos previos

- Python 3.10 o superior
- MySQL 8.0 o superior
- pip

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/Nicolasparr3054/CAMP.git
cd CAMP
```

### 2. Instalar dependencias Python

```bash
pip install -r requirements.txt
```

### 3. Crear la base de datos

Importa el script SQL en tu servidor MySQL:

```bash
mysql -u root -p < camp_database.sql
```

O desde MySQL Workbench: abre y ejecuta el archivo `camp_database.sql`.

### 4. Configurar la conexión a la base de datos

Edita el archivo `conexion_refactor/blueprints/helpers.py` con tus credenciales:

```python
def get_db_connection():
    connection = mysql.connector.connect(
        host='localhost',
        database='camp',
        user='root',
        password='TU_CONTRASEÑA',  # ← cambia esto
        charset='utf8mb4'
    )
    return connection
```

### 5. Configurar variables de entorno (opcional)

Copia `.env.example` como `.env` y completa los valores:

```env
DB_HOST=localhost
DB_NAME=camp
DB_USER=root
DB_PASSWORD=tu_contraseña

MAIL_USERNAME=tu_correo@gmail.com
MAIL_PASSWORD=tu_app_password
```

### 6. Ejecutar el servidor

```bash
cd conexion_refactor
python app.py
```

El servidor estará disponible en: **http://localhost:5000**

---

## Uso

Una vez iniciado el servidor, accede desde el navegador a:

| Vista | URL |
|---|---|
| Inicio / Landing page | `http://localhost:5000` |
| Login trabajador | `http://localhost:5000/vista/login-trabajador.html` |
| Registro (unificado) | `http://localhost:5000/vista/registro.html` |

---

## Roles de usuario

### 🧑‍🌾 Trabajador
- Completa su perfil con habilidades, experiencia y documentos
- Busca y se postula a ofertas de trabajo
- Gestiona sus postulaciones y contratos activos
- Califica a los agricultores al finalizar un acuerdo
- Configura su disponibilidad horaria

### 🌾 Agricultor
- Publica y gestiona ofertas de trabajo en su finca
- Revisa postulaciones y acepta o rechaza trabajadores
- Gestiona acuerdos laborales activos
- Califica a los trabajadores al finalizar un acuerdo
- Busca trabajadores disponibles por habilidad o ubicación

### 🛡️ Administrador
- Panel de control con estadísticas generales
- Gestión completa de usuarios (crear, editar, suspender, eliminar)
- Revisión y gestión de reportes entre usuarios
- Exportación de datos en CSV, JSON y Excel
- Métricas en tiempo real del sistema

---

## Base de datos

El esquema incluye las siguientes tablas principales:

| Tabla | Descripción |
|---|---|
| `Usuario` | Todos los usuarios del sistema con su rol y estado |
| `Predio` | Fincas registradas por los agricultores (con coordenadas) |
| `Habilidad` | Habilidades agrícolas de los trabajadores |
| `Experiencia` | Historial de experiencia laboral de trabajadores |
| `Oferta_Trabajo` | Ofertas publicadas por agricultores |
| `Postulacion` | Postulaciones de trabajadores a ofertas |
| `Acuerdo_Laboral` | Contratos formalizados entre agricultor y trabajador |
| `Calificacion` | Calificaciones entre usuarios al finalizar un acuerdo |
| `Anexo` | Documentos y fotos subidos por usuarios |
| `Reportes` | Reportes entre usuarios |
| `disponibilidad_trabajador` | Disponibilidad horaria de los trabajadores |

---

## API REST

El backend expone una API REST completa. Algunos endpoints principales:

```
POST   /registro.py                          Registro de usuario
POST   /login.py                             Inicio de sesión
POST   /logout                               Cerrar sesión

GET    /api/get_jobs                         Listar ofertas disponibles
POST   /api/crear_oferta                     Crear oferta de trabajo
POST   /api/apply_job                        Postularse a una oferta
PUT    /api/aceptar_postulacion_v3/<id>      Aceptar postulación
PUT    /api/rechazar_postulacion_v3/<id>     Rechazar postulación

GET    /api/historial_empleos_trabajador     Historial del trabajador
GET    /api/historial_contrataciones_v2      Historial del agricultor
POST   /api/calificar_trabajador_v2          Enviar calificación

GET    /api/buscar-trabajadores              Búsqueda avanzada
GET    /api/get_nearby_jobs                  Ofertas cercanas (geolocalización)

GET    /api/notificaciones                   Notificaciones del usuario
GET    /api/admin/users                      Lista de usuarios (admin)
GET    /api/admin/reportes-pendientes        Reportes pendientes (admin)
```

---

## Credenciales por defecto

| Campo | Valor |
|---|---|
| Correo | `admin@camp.com` |
| Contraseña | `admin123` |

> ⚠️ Cambia la contraseña del administrador después del primer inicio de sesión.

---

## Historial de versiones

### v1.5 — Rediseño del dashboard del agricultor *(actual)*
> Rediseño completo de la interfaz principal del agricultor.

- **`index-agricultor.html`** rediseñado con nueva estructura y componentes
- **`index-agricultor.css`** reescrito con nuevos estilos y layout actualizado
- **`index-agricultor.js`** actualizado con nueva lógica de interacción
- Mejoras generales de experiencia de usuario en el panel del agricultor

---

### v1.4 — Rediseño del dashboard del trabajador
> Rediseño completo de la interfaz principal del trabajador.

- **`index-trabajador.html`** rediseñado con nueva estructura y componentes
- **`index-trabajador.css`** reescrito con nuevos estilos y layout actualizado
- **`index-trabajador.js`** actualizado con nueva lógica de interacción
- Mejoras generales de experiencia de usuario en el panel del trabajador

---

### v1.3 — Registro unificado
> Simplificación del flujo de registro con una sola interfaz para todos los roles.

- **Registro unificado** — una sola vista `registro.html` reemplaza las interfaces separadas
- **Selector de rol integrado** directamente en el formulario de registro
- **Nuevo `registro.css`** con estilos propios para la vista unificada
- **Nuevo `registro.js`** con lógica de validación y envío del formulario
- Eliminadas: `seleccion-rol.html`, `registro-trabajador.html`, `registro-agricultor.html` y sus CSS/JS correspondientes
- Simplificación del flujo de onboarding para nuevos usuarios

---

### v1.2 — Login rediseñado
> Rediseño completo de la interfaz de inicio de sesión.

- **Layout split 50/50** — panel izquierdo visual + panel derecho con formulario
- **Imagen de fondo real** con trabajadores agrícolas colombianos, sin filtros artificiales
- **Logo CAMP** con colores originales y sombra para visibilidad sobre cualquier fondo
- **Tipografía Fraunces + Instrument Sans** — display serif + sans-serif moderna
- **Titular de impacto** con `text-shadow` para legibilidad sobre imagen
- **Badge** "Plataforma agrícola · Colombia" con fondo semitransparente
- **Overlay inteligente** — transparente arriba (caras visibles), oscuro abajo (texto legible)
- **Formulario limpio** con validación en tiempo real, toggle de contraseña y recordar sesión
- **Botones sociales** Google y Facebook
- **Responsive** — panel izquierdo se oculta en tablet/móvil

---

### v1.1 — Landing page actualizada
> Mejoras visuales y de contenido en la página de inicio.

- **Sección inicio de sesión** rediseñada con nueva jerarquía visual
- **Sección de beneficios** actualizada con íconos y descripciones más claras
- **Sección de comparación** entre roles (Trabajador vs Agricultor) mejorada
- **Sección de garantías** con nuevos textos e íconos representativos
- Ajustes generales de espaciado, tipografía y paleta de colores

---

### v1.0 — Lanzamiento inicial
> Primera versión funcional de la plataforma.

- Registro e inicio de sesión con tres roles: Trabajador, Agricultor, Administrador
- Publicación y gestión de ofertas de trabajo
- Sistema de postulaciones con estados
- Acuerdos laborales y calificaciones bidireccionales
- Perfil completo de trabajador con habilidades y documentos
- Búsqueda avanzada de trabajadores por habilidad y ubicación
- Geolocalización de ofertas cercanas
- Notificaciones dinámicas
- Panel de administrador con estadísticas y gestión de reportes
- Soporte OAuth (Google · Facebook)
- Recuperación de contraseña por correo
- Soporte multiidioma: español, inglés y chino

---

## Autores

Desarrollado por Nicolas Parra.

**CAMP v1.5** — 2026

---

> *Conectando el campo colombiano, una oferta a la vez.* 🌱