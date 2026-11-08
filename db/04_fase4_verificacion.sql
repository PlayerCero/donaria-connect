/* =====================================================================
   DONARIA CONNECT — Fase 4: verificación de identidad con Didit (sandbox)
   Se corre DESPUÉS de 01_*.sql. Se puede volver a correr (no duplica nada).
   La API lo corre sola al arrancar con scripts/migrar.py.

   Qué agrega
   - VERIFICACION_IDENTIDAD: una fila por sesión de Didit. Solo guarda el id de
     la sesión, el enlace y el estado ("Approved", "Declined"…). Nunca la foto
     del DNI, la selfie ni los datos que lee Didit: esos quedan en Didit.
   - Cuando Didit aprueba, DONANTE.estado_verificacion pasa a 'verificado'.
   ===================================================================== */

SET NOCOUNT ON;
GO

IF OBJECT_ID('dbo.VERIFICACION_IDENTIDAD') IS NULL
BEGIN
    CREATE TABLE dbo.VERIFICACION_IDENTIDAD (
        id_verificacion     INT IDENTITY(1,1) PRIMARY KEY,
        id_donante          INT NOT NULL REFERENCES dbo.DONANTE(id_donante),
        session_id          VARCHAR(64)   NOT NULL UNIQUE,   -- id de la sesión en Didit
        url                 VARCHAR(500)  NOT NULL,          -- enlace del flujo (vence solo)
        estado_didit        VARCHAR(20)   NOT NULL,          -- Not Started, In Progress, Approved, Declined…
        fecha_creacion      DATETIME2(0)  NOT NULL,
        fecha_actualizacion DATETIME2(0)  NOT NULL
    );
    CREATE INDEX IX_verificacion_donante ON dbo.VERIFICACION_IDENTIDAD (id_donante, fecha_creacion);
END;
GO

SELECT COUNT(*) AS verificaciones FROM dbo.VERIFICACION_IDENTIDAD;
GO
