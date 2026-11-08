/* =====================================================================
   DONARIA CONNECT — Base de datos del prototipo (Fase I, curso DPY UDEP)
   Paquetes EDT: 4.2.2 (script + 500 registros), 4.2.3 (consultas de
   elegibilidad y segmentación) y 4.5.1 (reglas antifraude).
   Responsable: Eric Salinas (tecnología y datos)

   VERSIÓN AZURE SQL. Requiere una base ya creada en el portal (DonariaConnect).
   En SSMS: conectarse al servidor de Azure, elegir la base DonariaConnect en el
   desplegable de bases (no master) y presionar F5 con el archivo completo.
   Se puede volver a correr: borra y recrea los objetos dentro de la base.

   TODOS LOS DATOS SON FICTICIOS. Ningún DNI, nombre ni teléfono es real.
   Fecha de referencia del escenario: lunes 09/11/2026 (exposición 3).
   ===================================================================== */

SET NOCOUNT ON;
GO

/* ---------------------------------------------------------------------
   0. Limpiar (Azure SQL no permite CREATE/DROP DATABASE ni USE dentro del
      script: la base se crea en el portal y este script borra y recrea los
      objetos dentro de ella, así que se puede volver a correr)
   --------------------------------------------------------------------- */
DROP USER IF EXISTS usuario_clinica_demo;
IF DATABASE_PRINCIPAL_ID('rol_institucion') IS NOT NULL DROP ROLE rol_institucion;
DROP VIEW IF EXISTS dbo.vw_reporte_institucion, dbo.vw_alertas_pendientes;
DROP PROCEDURE IF EXISTS dbo.sp_lanzar_ola, dbo.sp_ejecutar_reglas_antifraude;
DROP FUNCTION IF EXISTS dbo.fn_donantes_elegibles;
DROP TABLE IF EXISTS dbo.RESPUESTA_CONVOCATORIA, dbo.VERIFICACION_IDENTIDAD;   -- de 03 y 04
DROP TABLE IF EXISTS dbo.NOTIFICACION, dbo.OLA_CONVOCATORIA, dbo.RESULTADO_AGREGADO, dbo.NECESIDAD,
                     dbo.ALERTA_ANTIFRAUDE, dbo.DONACION_CONFIRMADA, dbo.CONSENTIMIENTO,
                     dbo.USUARIO_INSTITUCION, dbo.DONANTE, dbo.INSTITUCION, dbo.AUDITORIA;
GO

/* ---------------------------------------------------------------------
   1. Tablas (las 11 del modelo entidad–relación, Figura 16 del Word)
   Columnas añadidas al modelo (marcadas con [+]): DONANTE.sexo y
   DONANTE.dni_ult4, CONSENTIMIENTO.vigente, ALERTA_ANTIFRAUDE.id_institucion
   y ALERTA_ANTIFRAUDE.codigo_regla. Se necesitan para las reglas.
   --------------------------------------------------------------------- */

CREATE TABLE dbo.INSTITUCION (
    id_institucion         INT IDENTITY(1,1) PRIMARY KEY,
    ruc                    CHAR(11)      NOT NULL UNIQUE,
    razon_social           NVARCHAR(120) NOT NULL,
    autorizacion_sanitaria NVARCHAR(20)  NOT NULL
        CHECK (autorizacion_sanitaria IN (N'Vigente', N'Vencida')),
    ubicacion              GEOGRAPHY     NOT NULL,
    estado_afiliacion      NVARCHAR(20)  NOT NULL
        CHECK (estado_afiliacion IN (N'Piloto', N'En evaluación', N'Afiliada', N'No afiliada'))
);

CREATE TABLE dbo.USUARIO_INSTITUCION (
    id_usuario     INT IDENTITY(1,1) PRIMARY KEY,
    id_institucion INT NOT NULL REFERENCES dbo.INSTITUCION(id_institucion),
    correo         NVARCHAR(120) NOT NULL UNIQUE,
    rol            NVARCHAR(10)  NOT NULL CHECK (rol IN (N'admin', N'operador'))
);

CREATE TABLE dbo.DONANTE (
    id_donante            INT IDENTITY(1,1) PRIMARY KEY,
    dni_hash              VARBINARY(32) NOT NULL UNIQUE,   -- SHA-256 del DNI; el DNI nunca se guarda
    dni_ult4              CHAR(4)       NOT NULL,          -- [+] solo para mostrar ••••1234
    nombres               NVARCHAR(120) NOT NULL,
    sexo                  CHAR(1)       NOT NULL CHECK (sexo IN ('F', 'M')),   -- [+] define 90 o 120 días
    tipo_sangre           VARCHAR(3)    NOT NULL
        CHECK (tipo_sangre IN ('O+','O-','A+','A-','B+','B-','AB+','AB-')),
    distrito              NVARCHAR(60)  NOT NULL,
    ubicacion             GEOGRAPHY     NOT NULL,
    telefono_whatsapp     VARCHAR(15)   NOT NULL,
    estado_verificacion   VARCHAR(12)   NOT NULL
        CHECK (estado_verificacion IN ('verificado', 'pendiente', 'rechazado')),
    fecha_ultima_donacion DATE          NULL
);

CREATE TABLE dbo.CONSENTIMIENTO (
    id_consentimiento INT IDENTITY(1,1) PRIMARY KEY,
    id_donante        INT NOT NULL REFERENCES dbo.DONANTE(id_donante),
    version_texto     VARCHAR(10)  NOT NULL,
    fecha_hora        DATETIME2(0) NOT NULL,
    ip_origen         VARCHAR(45)  NOT NULL,
    vigente           BIT          NOT NULL DEFAULT 1        -- [+] 0 = revocado por el donante
);

CREATE TABLE dbo.NECESIDAD (                                  -- sin ningún dato de pacientes (art. 9, Ley 26454)
    id_necesidad   INT IDENTITY(1,1) PRIMARY KEY,
    id_institucion INT NOT NULL REFERENCES dbo.INSTITUCION(id_institucion),
    tipo_sangre    VARCHAR(3)    NOT NULL
        CHECK (tipo_sangre IN ('O+','O-','A+','A-','B+','B-','AB+','AB-')),
    zona           NVARCHAR(80)  NOT NULL,
    unidades_meta  INT           NOT NULL CHECK (unidades_meta > 0),
    estado         NVARCHAR(10)  NOT NULL CHECK (estado IN (N'Activa', N'Cerrada')),
    fecha_creacion DATETIME2(0)  NOT NULL
);

CREATE TABLE dbo.OLA_CONVOCATORIA (
    id_ola               INT IDENTITY(1,1) PRIMARY KEY,
    id_necesidad         INT NOT NULL REFERENCES dbo.NECESIDAD(id_necesidad),
    numero_ola           TINYINT      NOT NULL CHECK (numero_ola IN (1, 2, 3)),
    radio_km             TINYINT      NOT NULL CHECK (radio_km IN (3, 6, 10)),
    donantes_notificados INT          NOT NULL DEFAULT 0,
    fecha_envio          DATETIME2(0) NOT NULL,
    CONSTRAINT UQ_ola UNIQUE (id_necesidad, numero_ola)
);

CREATE TABLE dbo.NOTIFICACION (
    id_notificacion INT IDENTITY(1,1) PRIMARY KEY,
    id_ola          INT NOT NULL REFERENCES dbo.OLA_CONVOCATORIA(id_ola),
    id_donante      INT NOT NULL REFERENCES dbo.DONANTE(id_donante),
    canal           VARCHAR(10)  NOT NULL CHECK (canal IN ('WhatsApp', 'SMS')),
    estado_entrega  VARCHAR(12)  NOT NULL CHECK (estado_entrega IN ('Enviado', 'Entregado', 'Fallido')),
    fecha_envio     DATETIME2(0) NOT NULL
);

CREATE TABLE dbo.DONACION_CONFIRMADA (
    id_donacion    INT IDENTITY(1,1) PRIMARY KEY,
    id_donante     INT NOT NULL REFERENCES dbo.DONANTE(id_donante),
    id_institucion INT NOT NULL REFERENCES dbo.INSTITUCION(id_institucion),
    fecha          DATE        NOT NULL,
    fuente         VARCHAR(12) NOT NULL CHECK (fuente IN ('donante', 'institucion'))
);

CREATE TABLE dbo.RESULTADO_AGREGADO (                          -- 1:1 con NECESIDAD, solo cifras
    id_resultado       INT IDENTITY(1,1) PRIMARY KEY,
    id_necesidad       INT NOT NULL UNIQUE REFERENCES dbo.NECESIDAD(id_necesidad),
    unidades_obtenidas INT NOT NULL CHECK (unidades_obtenidas >= 0),
    fecha_cierre       DATETIME2(0) NULL
);

CREATE TABLE dbo.ALERTA_ANTIFRAUDE (
    id_alerta       INT IDENTITY(1,1) PRIMARY KEY,
    id_donante      INT NOT NULL REFERENCES dbo.DONANTE(id_donante),
    id_institucion  INT NULL REFERENCES dbo.INSTITUCION(id_institucion),   -- [+]
    codigo_regla    VARCHAR(4)    NOT NULL,                                -- [+] R1..R4
    regla_disparada NVARCHAR(200) NOT NULL,
    fecha           DATETIME2(0)  NOT NULL,
    estado_revision NVARCHAR(10)  NOT NULL CHECK (estado_revision IN (N'Pendiente', N'Revisada'))
);

CREATE TABLE dbo.AUDITORIA (
    id_evento      INT IDENTITY(1,1) PRIMARY KEY,
    usuario        NVARCHAR(60)  NOT NULL,
    accion         NVARCHAR(200) NOT NULL,
    tabla_afectada NVARCHAR(40)  NOT NULL,
    fecha_hora     DATETIME2(0)  NOT NULL
);

CREATE INDEX IX_donacion_donante ON dbo.DONACION_CONFIRMADA (id_donante, fecha);
CREATE INDEX IX_notif_donante    ON dbo.NOTIFICACION (id_donante);
CREATE SPATIAL INDEX SIX_donante_ubicacion ON dbo.DONANTE (ubicacion);
GO

/* ---------------------------------------------------------------------
   2. Instituciones y usuarios (ficticios; ubicaciones aproximadas)
   --------------------------------------------------------------------- */
INSERT INTO dbo.INSTITUCION (ruc, razon_social, autorizacion_sanitaria, ubicacion, estado_afiliacion) VALUES
 ('20000000001', N'Clínica Delgado Auna',                    N'Vigente', geography::Point(-12.1197, -77.0386, 4326), N'Piloto'),
 ('20000000002', N'Clínica Good Hope',                       N'Vigente', geography::Point(-12.1290, -77.0300, 4326), N'En evaluación'),
 ('20000000003', N'Hospital Rebagliati (registro del donante)', N'Vigente', geography::Point(-12.0794, -77.0397, 4326), N'No afiliada');

INSERT INTO dbo.USUARIO_INSTITUCION (id_institucion, correo, rol) VALUES
 (1, N'coordinacion.banco@clinica-demo.pe', N'admin'),
 (1, N'operador1.banco@clinica-demo.pe',    N'operador'),
 (2, N'banco.sangre@goodhope-demo.pe',      N'admin');
GO

/* ---------------------------------------------------------------------
   3. 500 donantes ficticios
   Generación determinista (siempre salen los mismos datos).
   Grupos sanguíneos con distribución aproximada de Lima:
   O+ 70 %, A+ 18 %, B+ 7 %, AB+ 1.5 %, negativos 3.5 %.
   --------------------------------------------------------------------- */
CREATE TABLE #dist (idx INT PRIMARY KEY, distrito NVARCHAR(60), lat FLOAT, lon FLOAT);
INSERT INTO #dist VALUES
 (1, N'Miraflores',        -12.1211, -77.0297), (2, N'San Isidro',        -12.0977, -77.0365),
 (3, N'Barranco',          -12.1497, -77.0219), (4, N'Surquillo',         -12.1128, -77.0103),
 (5, N'Santiago de Surco', -12.1355, -76.9925), (6, N'San Borja',         -12.1050, -76.9990),
 (7, N'Lince',             -12.0838, -77.0350), (8, N'Jesús María',       -12.0745, -77.0460),
 (9, N'Magdalena del Mar', -12.0905, -77.0700), (10, N'Pueblo Libre',     -12.0745, -77.0630),
 (11, N'San Miguel',       -12.0775, -77.0910), (12, N'La Victoria',      -12.0690, -77.0160),
 (13, N'Lima Cercado',     -12.0464, -77.0428), (14, N'Breña',            -12.0600, -77.0520),
 (15, N'Chorrillos',       -12.1690, -77.0230), (16, N'La Molina',        -12.0860, -76.9370),
 (17, N'Callao',           -12.0565, -77.1181);

CREATE TABLE #nomF (idx INT PRIMARY KEY, nombre NVARCHAR(30));
INSERT INTO #nomF VALUES (1,N'Lucía'),(2,N'María'),(3,N'Valeria'),(4,N'Camila'),(5,N'Daniela'),(6,N'Andrea'),
 (7,N'Sofía'),(8,N'Fernanda'),(9,N'Gabriela'),(10,N'Paola'),(11,N'Rosa'),(12,N'Carmen'),(13,N'Diana'),
 (14,N'Alejandra'),(15,N'Claudia'),(16,N'Mariana'),(17,N'Natalia'),(18,N'Karen'),(19,N'Milagros'),(20,N'Ximena');

CREATE TABLE #nomM (idx INT PRIMARY KEY, nombre NVARCHAR(30));
INSERT INTO #nomM VALUES (1,N'José'),(2,N'Luis'),(3,N'Carlos'),(4,N'Jorge'),(5,N'Miguel'),(6,N'Diego'),
 (7,N'Renzo'),(8,N'Andrés'),(9,N'Javier'),(10,N'Fernando'),(11,N'Gonzalo'),(12,N'Piero'),(13,N'Sebastián'),
 (14,N'Kevin'),(15,N'Bruno'),(16,N'Ricardo'),(17,N'Alonso'),(18,N'Martín'),(19,N'Eduardo'),(20,N'Raúl');

CREATE TABLE #ape (idx INT PRIMARY KEY, apellido NVARCHAR(30));
INSERT INTO #ape VALUES (1,N'Quispe'),(2,N'Flores'),(3,N'Sánchez'),(4,N'Rodríguez'),(5,N'García'),(6,N'Rojas'),
 (7,N'Huamán'),(8,N'Mamani'),(9,N'Vásquez'),(10,N'Chávez'),(11,N'Torres'),(12,N'Ramírez'),(13,N'Mendoza'),
 (14,N'Castillo'),(15,N'Paredes'),(16,N'Díaz'),(17,N'Gutiérrez'),(18,N'Romero'),(19,N'Salazar'),(20,N'Cruz'),
 (21,N'Morales'),(22,N'Vargas'),(23,N'Ríos'),(24,N'Espinoza'),(25,N'Herrera'),(26,N'Medina'),(27,N'Aguilar'),
 (28,N'Cárdenas'),(29,N'León'),(30,N'Palacios');

;WITH t AS (
    SELECT TOP (500) ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS n
    FROM sys.all_objects a CROSS JOIN sys.all_objects b
), r AS (
    SELECT t.n,
           CAST(70000000 + t.n * 13 AS VARCHAR(8)) AS dni,          -- DNI ficticio, solo para calcular el hash
           v.r_sexo % 100  AS p_sexo,
           v.r_tipo % 1000 AS p_tipo,
           v.r_dist % 17 + 1 AS idx_dist,
           v.r_lat % 161 - 80 AS j_lat,                              -- dispersión de ±0.008° (~0.9 km)
           v.r_lon % 161 - 80 AS j_lon,
           v.r_ver % 100   AS p_ver,
           v.r_nom % 20 + 1 AS idx_nom,
           v.r_ap1 % 30 + 1 AS idx_ap1,
           v.r_ap2 % 30 + 1 AS idx_ap2
    FROM t
    CROSS APPLY (SELECT
        CAST(HASHBYTES('MD5', CONCAT('sexo', t.n)) AS INT) & 2147483647 AS r_sexo,
        CAST(HASHBYTES('MD5', CONCAT('tipo', t.n)) AS INT) & 2147483647 AS r_tipo,
        CAST(HASHBYTES('MD5', CONCAT('dist', t.n)) AS INT) & 2147483647 AS r_dist,
        CAST(HASHBYTES('MD5', CONCAT('lat',  t.n)) AS INT) & 2147483647 AS r_lat,
        CAST(HASHBYTES('MD5', CONCAT('lon',  t.n)) AS INT) & 2147483647 AS r_lon,
        CAST(HASHBYTES('MD5', CONCAT('ver',  t.n)) AS INT) & 2147483647 AS r_ver,
        CAST(HASHBYTES('MD5', CONCAT('nom',  t.n)) AS INT) & 2147483647 AS r_nom,
        CAST(HASHBYTES('MD5', CONCAT('ap1',  t.n)) AS INT) & 2147483647 AS r_ap1,
        CAST(HASHBYTES('MD5', CONCAT('ap2',  t.n)) AS INT) & 2147483647 AS r_ap2) v
)
INSERT INTO dbo.DONANTE (dni_hash, dni_ult4, nombres, sexo, tipo_sangre, distrito, ubicacion,
                         telefono_whatsapp, estado_verificacion)
SELECT
    HASHBYTES('SHA2_256', 'donaria-2026|' + r.dni),
    RIGHT(r.dni, 4),
    CONCAT(CASE WHEN r.p_sexo < 52
                THEN (SELECT nombre FROM #nomF WHERE idx = r.idx_nom)
                ELSE (SELECT nombre FROM #nomM WHERE idx = r.idx_nom) END,
           N' ', (SELECT apellido FROM #ape WHERE idx = r.idx_ap1),
           N' ', (SELECT apellido FROM #ape WHERE idx = r.idx_ap2)),
    CASE WHEN r.p_sexo < 52 THEN 'F' ELSE 'M' END,
    CASE WHEN r.p_tipo < 700 THEN 'O+'  WHEN r.p_tipo < 880 THEN 'A+'
         WHEN r.p_tipo < 950 THEN 'B+'  WHEN r.p_tipo < 965 THEN 'AB+'
         WHEN r.p_tipo < 985 THEN 'O-'  WHEN r.p_tipo < 994 THEN 'A-'
         WHEN r.p_tipo < 999 THEN 'B-'  ELSE 'AB-' END,
    d.distrito,
    geography::Point(d.lat + r.j_lat / 10000.0, d.lon + r.j_lon / 10000.0, 4326),
    '9' + RIGHT('00000000' + CAST((r.n * 7907) % 100000000 AS VARCHAR(8)), 8),
    CASE WHEN r.p_ver < 90 THEN 'verificado' WHEN r.p_ver < 97 THEN 'pendiente' ELSE 'rechazado' END
FROM r
JOIN #dist d ON d.idx = r.idx_dist
ORDER BY r.n;                                    -- así id_donante = n (1..500)
GO

/* Consentimiento versión 1.0 para cada donante; ~2 % lo revocó */
DECLARE @hoy DATE = '20261109';
INSERT INTO dbo.CONSENTIMIENTO (id_donante, version_texto, fecha_hora, ip_origen, vigente)
SELECT d.id_donante, '1.0',
       DATEADD(MINUTE, v.r1 % 1440, CAST(DATEADD(DAY, -(30 + v.r2 % 600), @hoy) AS DATETIME2(0))),
       CONCAT('10.0.', d.id_donante / 250, '.', d.id_donante % 250 + 1),
       CASE WHEN v.r3 % 100 < 2 THEN 0 ELSE 1 END
FROM dbo.DONANTE d
CROSS APPLY (SELECT CAST(HASHBYTES('MD5', CONCAT('c1', d.id_donante)) AS INT) & 2147483647 AS r1,
                    CAST(HASHBYTES('MD5', CONCAT('c2', d.id_donante)) AS INT) & 2147483647 AS r2,
                    CAST(HASHBYTES('MD5', CONCAT('c3', d.id_donante)) AS INT) & 2147483647 AS r3) v;
GO

/* Historial de donaciones: 0 a 3 por donante, separadas al menos 130 días */
DECLARE @hoy DATE = '20261109';
;WITH k AS (
    SELECT d.id_donante,
           CASE WHEN v.x % 10 < 3 THEN 0 WHEN v.x % 10 < 7 THEN 1 WHEN v.x % 10 < 9 THEN 2 ELSE 3 END AS cantidad,
           1 + v.y % 420  AS dias_ultima,
           130 + v.z % 150 AS separacion
    FROM dbo.DONANTE d
    CROSS APPLY (SELECT CAST(HASHBYTES('MD5', CONCAT('k', d.id_donante)) AS INT) & 2147483647 AS x,
                        CAST(HASHBYTES('MD5', CONCAT('o', d.id_donante)) AS INT) & 2147483647 AS y,
                        CAST(HASHBYTES('MD5', CONCAT('g', d.id_donante)) AS INT) & 2147483647 AS z) v
    WHERE d.estado_verificacion <> 'rechazado'
), i AS (SELECT 1 AS i UNION ALL SELECT 2 UNION ALL SELECT 3)
INSERT INTO dbo.DONACION_CONFIRMADA (id_donante, id_institucion, fecha, fuente)
SELECT k.id_donante, s.inst,
       DATEADD(DAY, -(k.dias_ultima + (i.i - 1) * k.separacion), @hoy),
       CASE WHEN s.inst = 3 THEN 'donante' ELSE 'institucion' END
FROM k
JOIN i ON i.i <= k.cantidad
CROSS APPLY (SELECT CASE WHEN w.w % 10 < 6 THEN 1 WHEN w.w % 10 < 8 THEN 2 ELSE 3 END AS inst
             FROM (SELECT CAST(HASHBYTES('MD5', CONCAT('in', k.id_donante, '-', i.i)) AS INT) & 2147483647 AS w) w) s;
GO

/* Casos sembrados para probar las reglas antifraude (también ficticios) */
DECLARE @hoy DATE = '20261109';
UPDATE dbo.DONANTE SET estado_verificacion = 'verificado' WHERE id_donante IN (11, 12, 13, 21, 31, 32);
DELETE FROM dbo.DONACION_CONFIRMADA WHERE id_donante IN (11, 12, 13, 21);
INSERT INTO dbo.DONACION_CONFIRMADA (id_donante, id_institucion, fecha, fuente) VALUES
 (11, 1, DATEADD(DAY, -40, @hoy), 'institucion'),   -- R1: 3 donaciones en 35 días
 (11, 1, DATEADD(DAY, -25, @hoy), 'institucion'),
 (11, 2, DATEADD(DAY,  -5, @hoy), 'institucion'),
 (12, 2, DATEADD(DAY, -70, @hoy), 'institucion'),   -- R1: 2 donaciones en 60 días
 (12, 1, DATEADD(DAY, -10, @hoy), 'institucion'),
 (13, 1, DATEADD(DAY, -50, @hoy), 'institucion'),   -- R1: 2 donaciones en 45 días
 (13, 1, DATEADD(DAY,  -5, @hoy), 'institucion'),
 (21, 1, DATEADD(DAY, -20, @hoy), 'institucion'),   -- R2: 2 instituciones el mismo día
 (21, 2, DATEADD(DAY, -20, @hoy), 'institucion');
UPDATE dbo.DONANTE                                   -- R3: mismo celular en 2 DNI distintos
SET telefono_whatsapp = (SELECT telefono_whatsapp FROM dbo.DONANTE WHERE id_donante = 31)
WHERE id_donante = 32;

/* Fecha de la última donación (columna del modelo) */
UPDATE d SET fecha_ultima_donacion = x.ultima
FROM dbo.DONANTE d
JOIN (SELECT id_donante, MAX(fecha) AS ultima FROM dbo.DONACION_CONFIRMADA GROUP BY id_donante) x
  ON x.id_donante = d.id_donante;
GO

/* ---------------------------------------------------------------------
   4. Lógica: elegibilidad, convocatoria por olas y antifraude
   --------------------------------------------------------------------- */

/* 4.2.3 — Donantes elegibles en una fecha:
   verificado + consentimiento vigente + sin alerta pendiente +
   90 días (hombres) o 120 días (mujeres) desde la última donación */
CREATE FUNCTION dbo.fn_donantes_elegibles (@fecha DATE)
RETURNS TABLE
AS RETURN
SELECT d.id_donante, d.dni_ult4, d.sexo, d.tipo_sangre, d.distrito, d.ubicacion,
       u.ultima AS ultima_donacion,
       DATEADD(DAY, CASE d.sexo WHEN 'M' THEN 90 ELSE 120 END, u.ultima) AS proxima_fecha_posible
FROM dbo.DONANTE d
OUTER APPLY (SELECT MAX(dc.fecha) AS ultima
             FROM dbo.DONACION_CONFIRMADA dc
             WHERE dc.id_donante = d.id_donante AND dc.fecha < @fecha) u
WHERE d.estado_verificacion = 'verificado'
  AND EXISTS (SELECT 1 FROM dbo.CONSENTIMIENTO c WHERE c.id_donante = d.id_donante AND c.vigente = 1)
  AND NOT EXISTS (SELECT 1 FROM dbo.ALERTA_ANTIFRAUDE a
                  WHERE a.id_donante = d.id_donante AND a.estado_revision = N'Pendiente')
  AND (u.ultima IS NULL
       OR DATEDIFF(DAY, u.ultima, @fecha) >= CASE d.sexo WHEN 'M' THEN 90 ELSE 120 END);
GO

/* 4.2.3 — Lanzar una ola: ola 1 = 3 km, ola 2 = 6 km, ola 3 = 10 km.
   Notifica a elegibles del mismo grupo sanguíneo dentro del radio,
   sin repetir a quien ya fue notificado en una ola anterior. */
CREATE PROCEDURE dbo.sp_lanzar_ola
    @id_necesidad INT,
    @numero_ola   TINYINT,
    @fecha_envio  DATETIME2(0),
    @silencioso   BIT = 0
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @radio_km TINYINT = CASE @numero_ola WHEN 1 THEN 3 WHEN 2 THEN 6 WHEN 3 THEN 10 END;
    DECLARE @tipo VARCHAR(3), @punto GEOGRAPHY, @id_ola INT, @notificados INT;

    IF @radio_km IS NULL
        THROW 50001, N'Solo existen las olas 1, 2 y 3.', 1;
    IF EXISTS (SELECT 1 FROM dbo.OLA_CONVOCATORIA WHERE id_necesidad = @id_necesidad AND numero_ola = @numero_ola)
        THROW 50002, N'Esa ola ya fue lanzada para esta necesidad.', 1;

    SELECT @tipo = n.tipo_sangre, @punto = i.ubicacion
    FROM dbo.NECESIDAD n JOIN dbo.INSTITUCION i ON i.id_institucion = n.id_institucion
    WHERE n.id_necesidad = @id_necesidad AND n.estado = N'Activa';
    IF @tipo IS NULL
        THROW 50003, N'La necesidad no existe o ya está cerrada.', 1;

    BEGIN TRANSACTION;
        INSERT INTO dbo.OLA_CONVOCATORIA (id_necesidad, numero_ola, radio_km, donantes_notificados, fecha_envio)
        VALUES (@id_necesidad, @numero_ola, @radio_km, 0, @fecha_envio);
        SET @id_ola = SCOPE_IDENTITY();

        INSERT INTO dbo.NOTIFICACION (id_ola, id_donante, canal, estado_entrega, fecha_envio)
        SELECT @id_ola, e.id_donante,
               CASE WHEN e.id_donante % 10 = 0 THEN 'SMS' ELSE 'WhatsApp' END,
               'Entregado', @fecha_envio
        FROM dbo.fn_donantes_elegibles(CAST(@fecha_envio AS DATE)) e
        WHERE e.tipo_sangre = @tipo
          AND e.ubicacion.STDistance(@punto) <= @radio_km * 1000.0
          AND NOT EXISTS (SELECT 1 FROM dbo.NOTIFICACION x
                          JOIN dbo.OLA_CONVOCATORIA o ON o.id_ola = x.id_ola
                          WHERE o.id_necesidad = @id_necesidad AND x.id_donante = e.id_donante);
        SET @notificados = @@ROWCOUNT;

        UPDATE dbo.OLA_CONVOCATORIA SET donantes_notificados = @notificados WHERE id_ola = @id_ola;

        INSERT INTO dbo.AUDITORIA (usuario, accion, tabla_afectada, fecha_hora)
        VALUES (N'sistema', CONCAT(N'Ola ', @numero_ola, N' (', @radio_km, N' km) de la necesidad ',
                                   @id_necesidad, N': ', @notificados, N' donantes notificados'),
                N'NOTIFICACION', @fecha_envio);
    COMMIT TRANSACTION;

    IF @silencioso = 0
        SELECT @id_necesidad AS necesidad, @tipo AS tipo_sangre, @numero_ola AS ola,
               @radio_km AS radio_km, @notificados AS donantes_notificados_en_esta_ola;
END
GO

/* 4.5.1 — Reglas antifraude (no duplican una alerta pendiente)
   R1: dos donaciones con menos de 90 días (H) o 120 días (M) de separación
   R2: donación confirmada en 2 instituciones distintas el mismo día
   R3: mismo celular asociado a 2 o más DNI distintos
   R4: intento de registro con un DNI ya registrado (se genera al registrar) */
CREATE PROCEDURE dbo.sp_ejecutar_reglas_antifraude
    @ahora DATETIME2(0)
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @hoy DATE = CAST(@ahora AS DATE);

    -- R1
    ;WITH x AS (
        SELECT dc.id_donante, d.sexo, dc.fecha,
               LAG(dc.fecha) OVER (PARTITION BY dc.id_donante ORDER BY dc.fecha, dc.id_donacion) AS anterior
        FROM dbo.DONACION_CONFIRMADA dc JOIN dbo.DONANTE d ON d.id_donante = dc.id_donante
        WHERE dc.fecha <= @hoy
    ), v AS (
        SELECT DISTINCT id_donante, sexo FROM x
        WHERE anterior IS NOT NULL
          AND fecha >= DATEADD(DAY, -180, @hoy)
          AND DATEDIFF(DAY, anterior, fecha) BETWEEN 1 AND (CASE sexo WHEN 'M' THEN 90 ELSE 120 END) - 1
    )
    INSERT INTO dbo.ALERTA_ANTIFRAUDE (id_donante, id_institucion, codigo_regla, regla_disparada, fecha, estado_revision)
    SELECT v.id_donante, ult.id_institucion, 'R1',
           CONCAT(s.n, N' donaciones en ', s.dias, N' días (mínimo ',
                  CASE v.sexo WHEN 'M' THEN 90 ELSE 120 END, N' días entre donaciones)'),
           @ahora, N'Pendiente'
    FROM v
    CROSS APPLY (SELECT COUNT(*) AS n, DATEDIFF(DAY, MIN(fecha), MAX(fecha)) AS dias
                 FROM dbo.DONACION_CONFIRMADA
                 WHERE id_donante = v.id_donante AND fecha BETWEEN DATEADD(DAY, -180, @hoy) AND @hoy) s
    CROSS APPLY (SELECT TOP (1) id_institucion FROM dbo.DONACION_CONFIRMADA
                 WHERE id_donante = v.id_donante ORDER BY fecha DESC, id_donacion DESC) ult
    WHERE NOT EXISTS (SELECT 1 FROM dbo.ALERTA_ANTIFRAUDE a
                      WHERE a.id_donante = v.id_donante AND a.codigo_regla = 'R1' AND a.estado_revision = N'Pendiente');

    -- R2
    INSERT INTO dbo.ALERTA_ANTIFRAUDE (id_donante, id_institucion, codigo_regla, regla_disparada, fecha, estado_revision)
    SELECT g.id_donante, g.id_institucion, 'R2',
           CONCAT(N'Donación confirmada en ', g.n, N' instituciones el mismo día (',
                  CONVERT(CHAR(10), g.fecha, 103), N')'),
           @ahora, N'Pendiente'
    FROM (SELECT id_donante, fecha, COUNT(DISTINCT id_institucion) AS n, MAX(id_institucion) AS id_institucion
          FROM dbo.DONACION_CONFIRMADA
          WHERE fecha <= @hoy
          GROUP BY id_donante, fecha
          HAVING COUNT(DISTINCT id_institucion) >= 2) g
    WHERE NOT EXISTS (SELECT 1 FROM dbo.ALERTA_ANTIFRAUDE a
                      WHERE a.id_donante = g.id_donante AND a.codigo_regla = 'R2' AND a.estado_revision = N'Pendiente');

    -- R3
    INSERT INTO dbo.ALERTA_ANTIFRAUDE (id_donante, id_institucion, codigo_regla, regla_disparada, fecha, estado_revision)
    SELECT d.id_donante, NULL, 'R3',
           CONCAT(N'Mismo celular asociado a ', t.n, N' DNI distintos'),
           @ahora, N'Pendiente'
    FROM dbo.DONANTE d
    JOIN (SELECT telefono_whatsapp, COUNT(*) AS n FROM dbo.DONANTE
          GROUP BY telefono_whatsapp HAVING COUNT(*) >= 2) t ON t.telefono_whatsapp = d.telefono_whatsapp
    WHERE NOT EXISTS (SELECT 1 FROM dbo.ALERTA_ANTIFRAUDE a
                      WHERE a.id_donante = d.id_donante AND a.codigo_regla = 'R3' AND a.estado_revision = N'Pendiente');

    INSERT INTO dbo.AUDITORIA (usuario, accion, tabla_afectada, fecha_hora)
    VALUES (N'sistema', N'Ejecución de reglas antifraude R1–R3', N'ALERTA_ANTIFRAUDE', @ahora);
END
GO

/* Vista para la institución: SOLO cifras agregadas, nunca nombres ni DNI */
CREATE VIEW dbo.vw_reporte_institucion
AS
SELECT n.id_necesidad, i.razon_social AS institucion, n.tipo_sangre, n.zona, n.estado,
       n.fecha_creacion, n.unidades_meta,
       (SELECT COUNT(*) FROM dbo.OLA_CONVOCATORIA o WHERE o.id_necesidad = n.id_necesidad) AS olas_lanzadas,
       (SELECT ISNULL(SUM(o.donantes_notificados), 0) FROM dbo.OLA_CONVOCATORIA o
         WHERE o.id_necesidad = n.id_necesidad) AS donantes_notificados,
       ISNULL(r.unidades_obtenidas, 0) AS unidades_obtenidas,
       CAST(100.0 * ISNULL(r.unidades_obtenidas, 0) / n.unidades_meta AS DECIMAL(5, 1)) AS pct_cumplimiento
FROM dbo.NECESIDAD n
JOIN dbo.INSTITUCION i ON i.id_institucion = n.id_institucion
LEFT JOIN dbo.RESULTADO_AGREGADO r ON r.id_necesidad = n.id_necesidad;
GO

/* Vista para el equipo Donaria: alertas por revisar (plazo de 72 h) */
CREATE VIEW dbo.vw_alertas_pendientes
AS
SELECT a.id_alerta, a.codigo_regla,
       CONCAT('D-', RIGHT(CONCAT('0000', a.id_donante), 4)) AS codigo_donante,
       CONCAT('****', d.dni_ult4) AS dni,
       a.regla_disparada,
       ISNULL(i.razon_social, N'—') AS institucion,
       a.fecha, DATEADD(HOUR, 72, a.fecha) AS revisar_antes_de, a.estado_revision
FROM dbo.ALERTA_ANTIFRAUDE a
JOIN dbo.DONANTE d ON d.id_donante = a.id_donante
LEFT JOIN dbo.INSTITUCION i ON i.id_institucion = a.id_institucion
WHERE a.estado_revision = N'Pendiente';
GO

/* Permisos: el usuario de una clínica solo puede leer el reporte agregado */
CREATE ROLE rol_institucion;
GRANT SELECT ON dbo.vw_reporte_institucion TO rol_institucion;
DENY  SELECT ON dbo.DONANTE TO rol_institucion;
DENY  SELECT ON dbo.DONACION_CONFIRMADA TO rol_institucion;
CREATE USER usuario_clinica_demo WITHOUT LOGIN;
ALTER ROLE rol_institucion ADD MEMBER usuario_clinica_demo;
GO

/* ---------------------------------------------------------------------
   5. Escenario: antifraude, necesidades, olas y resultados
   --------------------------------------------------------------------- */

/* R4: alguien intenta registrarse con el DNI del donante 1. La restricción
   UNIQUE sobre dni_hash lo impide y se registra una alerta. */
BEGIN TRY
    INSERT INTO dbo.DONANTE (dni_hash, dni_ult4, nombres, sexo, tipo_sangre, distrito, ubicacion,
                             telefono_whatsapp, estado_verificacion)
    VALUES (HASHBYTES('SHA2_256', 'donaria-2026|' + CAST(70000013 AS VARCHAR(8))), '0013', N'Registro duplicado',
            'M', 'O+', N'Lince', geography::Point(-12.0838, -77.0350, 4326), '999000111', 'pendiente');
END TRY
BEGIN CATCH
    PRINT CONCAT(N'Registro bloqueado (esperado): ', ERROR_MESSAGE());
    INSERT INTO dbo.ALERTA_ANTIFRAUDE (id_donante, id_institucion, codigo_regla, regla_disparada, fecha, estado_revision)
    VALUES (1, NULL, 'R4', N'Intento de registro con un DNI ya registrado', '2026-11-08T21:14:00', N'Pendiente');
END CATCH;

EXEC dbo.sp_ejecutar_reglas_antifraude @ahora = '2026-11-09T07:30:00';
GO

/* Necesidades (mismos números que el prototipo navegable) */
SET IDENTITY_INSERT dbo.NECESIDAD ON;
INSERT INTO dbo.NECESIDAD (id_necesidad, id_institucion, tipo_sangre, zona, unidades_meta, estado, fecha_creacion) VALUES
 (27, 1, 'AB+', N'Miraflores y alrededores', 2,  N'Activa', '2026-10-03T13:20:00'),
 (28, 1, 'O+',  N'Miraflores y alrededores', 10, N'Activa', '2026-10-08T07:55:00'),
 (29, 1, 'B+',  N'Lima centro y sur',        4,  N'Activa', '2026-10-11T09:05:00'),
 (30, 1, 'A+',  N'Miraflores y alrededores', 8,  N'Activa', '2026-11-08T16:40:00'),
 (31, 1, 'O-',  N'Miraflores y alrededores', 6,  N'Activa', '2026-11-09T08:10:00');
SET IDENTITY_INSERT dbo.NECESIDAD OFF;

EXEC dbo.sp_lanzar_ola 27, 1, '2026-10-03T13:21:00', 1;
EXEC dbo.sp_lanzar_ola 27, 2, '2026-10-03T15:40:00', 1;
EXEC dbo.sp_lanzar_ola 28, 1, '2026-10-08T07:58:00', 1;
EXEC dbo.sp_lanzar_ola 28, 2, '2026-10-08T11:00:00', 1;
EXEC dbo.sp_lanzar_ola 29, 1, '2026-10-11T09:06:00', 1;
EXEC dbo.sp_lanzar_ola 29, 2, '2026-10-11T12:30:00', 1;
EXEC dbo.sp_lanzar_ola 30, 1, '2026-11-08T16:42:00', 1;
EXEC dbo.sp_lanzar_ola 31, 1, '2026-11-09T08:12:00', 1;
EXEC dbo.sp_lanzar_ola 31, 2, '2026-11-09T10:15:00', 1;

/* Resultados que confirma la institución: solo unidades, sin nombres */
UPDATE dbo.NECESIDAD SET estado = N'Cerrada' WHERE id_necesidad IN (27, 28, 29);
INSERT INTO dbo.RESULTADO_AGREGADO (id_necesidad, unidades_obtenidas, fecha_cierre) VALUES
 (27, 2,  '2026-10-04T18:00:00'),
 (28, 10, '2026-10-09T18:00:00'),
 (29, 4,  '2026-10-12T18:00:00'),
 (30, 5,  NULL),
 (31, 2,  NULL);
GO

/* ---------------------------------------------------------------------
   6. Verificación: cuántos registros quedaron en cada tabla
   --------------------------------------------------------------------- */
SELECT 'DONANTE' AS tabla, COUNT(*) AS registros FROM dbo.DONANTE
UNION ALL SELECT 'CONSENTIMIENTO', COUNT(*) FROM dbo.CONSENTIMIENTO
UNION ALL SELECT 'DONACION_CONFIRMADA', COUNT(*) FROM dbo.DONACION_CONFIRMADA
UNION ALL SELECT 'INSTITUCION', COUNT(*) FROM dbo.INSTITUCION
UNION ALL SELECT 'USUARIO_INSTITUCION', COUNT(*) FROM dbo.USUARIO_INSTITUCION
UNION ALL SELECT 'NECESIDAD', COUNT(*) FROM dbo.NECESIDAD
UNION ALL SELECT 'OLA_CONVOCATORIA', COUNT(*) FROM dbo.OLA_CONVOCATORIA
UNION ALL SELECT 'NOTIFICACION', COUNT(*) FROM dbo.NOTIFICACION
UNION ALL SELECT 'RESULTADO_AGREGADO', COUNT(*) FROM dbo.RESULTADO_AGREGADO
UNION ALL SELECT 'ALERTA_ANTIFRAUDE', COUNT(*) FROM dbo.ALERTA_ANTIFRAUDE
UNION ALL SELECT 'AUDITORIA', COUNT(*) FROM dbo.AUDITORIA;

PRINT N'Listo. Objetos creados en Azure SQL con 500 donantes ficticios. Siguiente: 02_consultas_exposicion.sql';
GO
