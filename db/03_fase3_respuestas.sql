/* =====================================================================
   DONARIA CONNECT — Fase 3: respuestas de los donantes a una convocatoria
   Se corre DESPUÉS de 01_*.sql. Se puede volver a correr (no duplica nada).
   La API lo corre sola al arrancar con scripts/migrar.py.

   Qué agrega
   - RESPUESTA_CONVOCATORIA: lo que el donante contesta al aviso
     ("voy" o "no"). Una respuesta por notificación. La clínica solo ve el
     conteo; nunca quién respondió.
   - Respuestas ficticias para las olas ya sembradas (unas 8 % "voy"), para
     que la conversión del panel tenga cifras desde el inicio.
   ===================================================================== */

SET NOCOUNT ON;
GO

IF OBJECT_ID('dbo.RESPUESTA_CONVOCATORIA') IS NULL
BEGIN
    CREATE TABLE dbo.RESPUESTA_CONVOCATORIA (
        id_respuesta    INT IDENTITY(1,1) PRIMARY KEY,
        -- ON DELETE CASCADE: la consulta 0 de 02_consultas_exposicion.sql borra la ola 2 de la
        -- necesidad 30 con sus notificaciones; sus respuestas se van con ellas.
        id_notificacion INT NOT NULL UNIQUE
            REFERENCES dbo.NOTIFICACION(id_notificacion) ON DELETE CASCADE,
        respuesta       VARCHAR(3)   NOT NULL CHECK (respuesta IN ('voy', 'no')),
        fecha_hora      DATETIME2(0) NOT NULL
    );
END;
GO

/* Respuestas ficticias, deterministas (mismo resultado siempre), solo una vez */
IF NOT EXISTS (SELECT 1 FROM dbo.RESPUESTA_CONVOCATORIA)
BEGIN
    INSERT INTO dbo.RESPUESTA_CONVOCATORIA (id_notificacion, respuesta, fecha_hora)
    SELECT x.id_notificacion,
           CASE WHEN x.p < 8 THEN 'voy' ELSE 'no' END,
           DATEADD(MINUTE, 5 + x.p * 3, x.fecha_envio)
    FROM (
        SELECT n.id_notificacion, n.fecha_envio,
               (CAST(HASHBYTES('MD5', CONCAT('resp|', n.id_notificacion)) AS INT) & 2147483647) % 100 AS p
        FROM dbo.NOTIFICACION n
    ) x
    WHERE x.p < 15;   -- 8 % dice "voy", 7 % dice "no", el resto no responde
END;
GO

SELECT respuesta, COUNT(*) AS respuestas FROM dbo.RESPUESTA_CONVOCATORIA GROUP BY respuesta;
GO
