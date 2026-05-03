-- ============================================
-- BASE DE DATOS: CAMP
-- ============================================
CREATE DATABASE camp;
USE camp;

-- ============================================
-- TABLAS
-- ============================================

-- Tabla Usuario: Almacena información de usuarios del sistema (Agricultores, Trabajadores, Administradores)
CREATE TABLE Usuario (
    ID_Usuario INT PRIMARY KEY AUTO_INCREMENT,
    Nombre VARCHAR(100) NOT NULL,
    Apellido VARCHAR(100) NOT NULL,
    Correo VARCHAR(150) UNIQUE NOT NULL,
    Contrasena VARCHAR(255) NOT NULL,
    Telefono VARCHAR(20),
    URL_Foto VARCHAR(255),
    Red_Social VARCHAR(255),
    Rol ENUM('Agricultor', 'Trabajador', 'Administrador') NOT NULL,
    Estado ENUM('Activo', 'Inactivo') DEFAULT 'Activo',
    Fecha_Registro DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla Predio: Almacena información de las fincas/predios de los agricultores
CREATE TABLE Predio (
    ID_Predio INT AUTO_INCREMENT PRIMARY KEY,
    ID_Usuario INT NOT NULL,
    Nombre_Finca VARCHAR(150) NOT NULL,
    Ubicacion_Latitud DECIMAL(10,8) NOT NULL,
    Ubicacion_Longitud DECIMAL(11,8) NOT NULL,
    Descripcion TEXT,
    FOREIGN KEY (ID_Usuario) REFERENCES Usuario(ID_Usuario)
);

-- Tabla Experiencia: Registra la experiencia laboral de los trabajadores
CREATE TABLE Experiencia (
    ID_Experiencia INT PRIMARY KEY AUTO_INCREMENT,
    ID_Trabajador INT NOT NULL,
    Fecha_Inicio DATE NOT NULL,
    Fecha_Fin DATE,
    Ubicacion VARCHAR(255),
    Observacion TEXT,
    Telefono_CEM VARCHAR(20),
    Nombre_Contacto VARCHAR(100),
    RS_Empleado VARCHAR(100),
    FOREIGN KEY (ID_Trabajador) REFERENCES Usuario(ID_Usuario)
);

-- Tabla Habilidad: Registra las habilidades y competencias de los trabajadores
CREATE TABLE Habilidad (
    ID_Habilidad INT PRIMARY KEY AUTO_INCREMENT,
    ID_Trabajador INT NOT NULL,
    Nombre VARCHAR(100) NOT NULL,
    Clasificacion ENUM(
        'Técnica agrícola',
        'Manejo de maquinaria',
        'Especializada',
        'Logística',
        'Control de plagas',
        'Riego y drenaje',
        'Cosecha y poscosecha',
        'Fertilización',
        'Preparación de suelo',
        'Transporte y distribución'
    ) NOT NULL,
    FOREIGN KEY (ID_Trabajador) REFERENCES Usuario(ID_Usuario)
);

-- Tabla Oferta_Trabajo: Almacena las ofertas de trabajo publicadas por agricultores
CREATE TABLE Oferta_Trabajo (
    ID_Oferta INT PRIMARY KEY AUTO_INCREMENT,
    ID_Agricultor INT NOT NULL,
    Titulo VARCHAR(200) NOT NULL,
    Descripcion TEXT,
    Pago_Ofrecido DECIMAL(10,2) NOT NULL,
    Fecha_Publicacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    Estado ENUM('Abierta', 'Cerrada', 'En Proceso') DEFAULT 'Abierta',
    FOREIGN KEY (ID_Agricultor) REFERENCES Usuario(ID_Usuario)
);

-- Tabla Postulacion: Registra las postulaciones de trabajadores a ofertas de trabajo
CREATE TABLE Postulacion (
    ID_Postulacion INT PRIMARY KEY AUTO_INCREMENT,
    ID_Oferta INT NOT NULL,
    ID_Trabajador INT NOT NULL,
    Fecha_Postulacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    Estado ENUM('Pendiente', 'Aceptada', 'Rechazada', 'Favorito') DEFAULT 'Pendiente',
    FOREIGN KEY (ID_Oferta) REFERENCES Oferta_Trabajo(ID_Oferta),
    FOREIGN KEY (ID_Trabajador) REFERENCES Usuario(ID_Usuario)
);

-- Tabla Acuerdo_Laboral: Almacena los acuerdos laborales formalizados entre agricultor y trabajador
CREATE TABLE Acuerdo_Laboral (
    ID_Acuerdo INT PRIMARY KEY AUTO_INCREMENT,
    ID_Oferta INT NOT NULL,
    ID_Trabajador INT NOT NULL,
    Fecha_Inicio DATE NOT NULL,
    Fecha_Fin DATE,
    Pago_Final DECIMAL(10,2),
    Estado ENUM('Activo', 'Finalizado', 'Cancelado') DEFAULT 'Activo',
    FOREIGN KEY (ID_Oferta) REFERENCES Oferta_Trabajo(ID_Oferta),
    FOREIGN KEY (ID_Trabajador) REFERENCES Usuario(ID_Usuario)
);

-- Tabla Calificacion: Registra las calificaciones entre usuarios después de un acuerdo laboral
CREATE TABLE Calificacion (
    ID_Calificacion INT PRIMARY KEY AUTO_INCREMENT,
    ID_Acuerdo INT NOT NULL,
    ID_Usuario_Emisor INT NOT NULL,
    ID_Usuario_Receptor INT NOT NULL,
    Puntuacion ENUM('1','2','3','4','5') NOT NULL,
    Comentario TEXT,
    Fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ID_Acuerdo) REFERENCES Acuerdo_Laboral(ID_Acuerdo),
    FOREIGN KEY (ID_Usuario_Emisor) REFERENCES Usuario(ID_Usuario),
    FOREIGN KEY (ID_Usuario_Receptor) REFERENCES Usuario(ID_Usuario)
);

-- Tabla Anexo: Almacena archivos adjuntos de los usuarios (certificados, documentos, imágenes)
CREATE TABLE Anexo (
    ID_Anexo INT PRIMARY KEY AUTO_INCREMENT,
    ID_Usuario INT NOT NULL,
    Tipo_Archivo ENUM('Imagen', 'Documento', 'Certificado', 'Otro') NOT NULL,
    URL_Archivo VARCHAR(255) NOT NULL,
    Descripcion TEXT,
    Fecha_Subida DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ID_Usuario) REFERENCES Usuario(ID_Usuario)
);

-- Tabla disponibilidad_trabajador: Gestiona la disponibilidad y visibilidad de los trabajadores
CREATE TABLE disponibilidad_trabajador (
    ID_Disponibilidad INT AUTO_INCREMENT PRIMARY KEY,
    ID_Usuario INT NOT NULL,
    Disponible BOOLEAN DEFAULT FALSE,
    Visibilidad ENUM('visible', 'paused', 'hidden') DEFAULT 'visible',
    Dias_Disponibles JSON,
    Hora_Inicio TIME,
    Hora_Fin TIME,
    Fechas_No_Disponibles JSON,
    Fecha_Actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (ID_Usuario) REFERENCES Usuario(ID_Usuario) ON DELETE CASCADE,
    UNIQUE KEY (ID_Usuario)
);

-- Tabla Reportes: Registra reportes de usuarios sobre otros usuarios
CREATE TABLE Reportes (
    ID_Reporte INT PRIMARY KEY AUTO_INCREMENT,
    ID_Usuario_Reportante INT NOT NULL,
    ID_Usuario_Reportado INT NOT NULL,
    Motivo TEXT NOT NULL,
    Estado ENUM('Pendiente', 'Revisado', 'Resuelto') DEFAULT 'Pendiente',
    Fecha_Reporte DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ID_Usuario_Reportante) REFERENCES Usuario(ID_Usuario) ON DELETE CASCADE,
    FOREIGN KEY (ID_Usuario_Reportado) REFERENCES Usuario(ID_Usuario) ON DELETE CASCADE
);

-- ============================================
-- MODIFICACIONES A TABLAS EXISTENTES
-- ============================================

-- Agregar columnas adicionales a la tabla Usuario
ALTER TABLE Usuario 
ADD COLUMN Configuraciones JSON,
ADD COLUMN Fecha_Actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
ADD COLUMN Idioma VARCHAR(5) DEFAULT 'es';

-- Agregar columnas de nivel y experiencia a la tabla Habilidad
ALTER TABLE Habilidad 
ADD COLUMN Nivel ENUM('Básico', 'Intermedio', 'Avanzado', 'Experto') DEFAULT 'Intermedio' AFTER Clasificacion,
ADD COLUMN Anos_Experiencia INT DEFAULT 0 AFTER Nivel;

-- Modificar campo Estado de Oferta_Trabajo (confirmar estructura)
ALTER TABLE Oferta_Trabajo 
MODIFY COLUMN Estado ENUM('Abierta', 'Cerrada', 'En Proceso') DEFAULT 'Abierta';

-- Modificar campo Estado de Postulacion (confirmar estructura)
ALTER TABLE Postulacion 
MODIFY COLUMN Estado ENUM('Pendiente', 'Aceptada', 'Rechazada', 'Favorito') DEFAULT 'Pendiente';

-- ============================================
-- ÍNDICES PARA OPTIMIZACIÓN
-- ============================================

-- Índices para tabla disponibilidad_trabajador

-- Índice para búsquedas por disponibilidad (consultas que filtran trabajadores disponibles/no disponibles)
CREATE INDEX idx_disponible ON disponibilidad_trabajador(Disponible);

-- Índice para búsquedas por visibilidad (consultas que filtran por estado de visibilidad: visible, paused, hidden)
CREATE INDEX idx_visibilidad ON disponibilidad_trabajador(Visibilidad);

-- Índice compuesto para búsquedas por usuario y disponibilidad (optimiza consultas que buscan la disponibilidad de un usuario específico)
CREATE INDEX idx_usuario_disponible ON disponibilidad_trabajador(ID_Usuario, Disponible);

-- Índices para tabla Reportes

-- Índice para búsquedas por estado del reporte (consultas que filtran reportes por: Pendiente, Revisado, Resuelto)
CREATE INDEX idx_estado_reporte ON Reportes(Estado);

-- Índice para búsquedas y ordenamientos por fecha de reporte (optimiza consultas que ordenan o filtran por fecha)
CREATE INDEX idx_fecha_reporte ON Reportes(Fecha_Reporte);

-- Índice para búsquedas de reportes realizados por un usuario específico (consultas que buscan todos los reportes que hizo un usuario)
CREATE INDEX idx_reportante ON Reportes(ID_Usuario_Reportante);

-- Índice para búsquedas de reportes recibidos por un usuario específico (consultas que buscan todos los reportes que recibió un usuario)
CREATE INDEX idx_reportado ON Reportes(ID_Usuario_Reportado);

-- ============================================
-- DATOS INICIALES
-- ============================================

-- Insertar usuario administrador principal
INSERT INTO Usuario (Nombre, Apellido, Correo, Contrasena, Rol, Estado) 
VALUES ('Admin', 'Principal', 'admin@agriwork.com', '$2b$12$encrypted_password_here', 'Administrador', 'Activo');

-- Insertar segundo usuario administrador
INSERT INTO Usuario (Nombre, Apellido, Correo, Contrasena, Rol, Estado) 
VALUES ('Admin', 'Principal', 'admin@agromatch.com', '$2b$12$KIXv0gOMZOUfhEAWN6B7mOyKL6.7ZJfYHGrMJOZHGBJOz8y4kJa8K', 'Administrador', 'Activo');

UPDATE camp.Usuario 
SET Contrasena = '$2b$12$JsUFfeNNuR.FuRLdzBrX6uKDykEYLhFg2DTUO1fxREQAz0mTPjUpK'
WHERE ID_Usuario = 1;