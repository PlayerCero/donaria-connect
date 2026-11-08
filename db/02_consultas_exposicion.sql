/* =====================================================================
   DONARIA CONNECT — Consultas para la exposición (lunes 09/11/2026)
   Requiere haber corrido antes 01_crear_y_cargar.sql.
   Para la demo: seleccionar UNA consulta con el mouse y presionar F5
   (SSMS ejecuta solo lo seleccionado). Todo es ficticio.
   ===================================================================== */
USE DonariaConnect;
SET NOCOUNT ON;
GO

/* ---- 0. Preparar la demo en vivo (deja la ola 2 de la necesidad 30 sin lanzar).
         Correrlo antes de exponer; se puede repetir cuantas veces se quiera. ---- */
DELETE x FROM dbo.NOTIFICACION x
JOIN dbo.OLA_CONVOCATORIA o ON o.id_ola = x.id_ola
WHERE o.id_necesidad = 30 AND o.numero_ola >= 2;
DELETE FROM dbo.OLA_CONVOCATORIA WHERE id_necesidad = 30 AND numero_ola >= 2;
GO

/* ---- 1. ¿Cuántos donantes pueden donar hoy, por grupo sanguíneo? ---- */
DECLARE @hoy DATE = '20261109';
SELECT d.tipo_sangre,
       COUNT(*) AS registrados,
       SUM(CASE WHEN e.id_donante IS NOT NULL THEN 1 ELSE 0 END) AS elegibles_hoy
FROM dbo.DONANTE d
LEFT JOIN dbo.fn_donantes_elegibles(@hoy) e ON e.id_donante = d.id_donante
GROUP BY d.tipo_sangre
ORDER BY registrados DESC;
GO

/* ---- 2. ¿Por qué no pueden donar los demás? (primer motivo que aplica) ---- */
DECLARE @hoy DATE = '20261109';
SELECT motivo, COUNT(*) AS donantes
FROM (
    SELECT CASE
        WHEN d.estado_verificacion <> 'verificado' THEN N'Identidad no verificada (Didit)'
        WHEN NOT EXISTS (SELECT 1 FROM dbo.CONSENTIMIENTO c
                         WHERE c.id_donante = d.id_donante AND c.vigente = 1) THEN N'Revocó el consentimiento'
        WHEN EXISTS (SELECT 1 FROM dbo.ALERTA_ANTIFRAUDE a
                     WHERE a.id_donante = d.id_donante AND a.estado_revision = N'Pendiente') THEN N'Alerta antifraude pendiente'
        WHEN d.fecha_ultima_donacion IS NOT NULL
             AND DATEDIFF(DAY, d.fecha_ultima_donacion, @hoy) < CASE d.sexo WHEN 'M' THEN 90 ELSE 120 END
             THEN N'Donó hace poco (90 días H / 120 días M)'
        ELSE N'Elegible' END AS motivo
    FROM dbo.DONANTE d
) t
GROUP BY motivo
ORDER BY donantes DESC;
GO

/* ---- 3. Lo que ve un donante en su perfil: ¿cuándo puede volver a donar? ---- */
DECLARE @hoy DATE = '20261109';
SELECT TOP (10)
       CONCAT('D-', RIGHT(CONCAT('0000', d.id_donante), 4)) AS donante,
       d.sexo, d.tipo_sangre, d.fecha_ultima_donacion,
       DATEADD(DAY, CASE d.sexo WHEN 'M' THEN 90 ELSE 120 END, d.fecha_ultima_donacion) AS proxima_fecha_posible,
       CASE WHEN DATEDIFF(DAY, d.fecha_ultima_donacion, @hoy) >= CASE d.sexo WHEN 'M' THEN 90 ELSE 120 END
            THEN N'Puede donar' ELSE N'Aún no' END AS estado_hoy
FROM dbo.DONANTE d
WHERE d.fecha_ultima_donacion IS NOT NULL AND d.estado_verificacion = 'verificado'
ORDER BY d.fecha_ultima_donacion DESC;
GO

/* ---- 4. Segmentación por distancia: donantes elegibles del grupo pedido
         a 3, 6 y 10 km de la clínica (por qué hacen falta olas) ---- */
DECLARE @hoy DATE = '20261109';
SELECT n.id_necesidad, n.tipo_sangre,
       SUM(CASE WHEN e.ubicacion.STDistance(i.ubicacion) <=  3000 THEN 1 ELSE 0 END) AS hasta_3_km,
       SUM(CASE WHEN e.ubicacion.STDistance(i.ubicacion) <=  6000 THEN 1 ELSE 0 END) AS hasta_6_km,
       SUM(CASE WHEN e.ubicacion.STDistance(i.ubicacion) <= 10000 THEN 1 ELSE 0 END) AS hasta_10_km
FROM dbo.NECESIDAD n
JOIN dbo.INSTITUCION i ON i.id_institucion = n.id_institucion
JOIN dbo.fn_donantes_elegibles(@hoy) e ON e.tipo_sangre = n.tipo_sangre
WHERE n.estado = N'Activa'
GROUP BY n.id_necesidad, n.tipo_sangre;
GO

/* ---- 4b. Detalle: los 15 donantes A+ más cercanos a la Clínica Delgado ---- */
DECLARE @hoy DATE = '20261109';
DECLARE @clinica GEOGRAPHY = (SELECT ubicacion FROM dbo.INSTITUCION WHERE id_institucion = 1);
SELECT TOP (15)
       CONCAT('D-', RIGHT(CONCAT('0000', e.id_donante), 4)) AS donante,
       e.tipo_sangre, e.distrito,
       CAST(e.ubicacion.STDistance(@clinica) / 1000.0 AS DECIMAL(5, 2)) AS distancia_km,
       CASE WHEN e.ubicacion.STDistance(@clinica) <= 3000 THEN 1
            WHEN e.ubicacion.STDistance(@clinica) <= 6000 THEN 2 ELSE 3 END AS ola_que_le_toca
FROM dbo.fn_donantes_elegibles(@hoy) e
WHERE e.tipo_sangre = 'A+'
ORDER BY e.ubicacion.STDistance(@clinica);
GO

/* ---- 5. Olas ya lanzadas por necesidad ---- */
SELECT o.id_necesidad, n.tipo_sangre, o.numero_ola, o.radio_km, o.donantes_notificados, o.fecha_envio
FROM dbo.OLA_CONVOCATORIA o
JOIN dbo.NECESIDAD n ON n.id_necesidad = o.id_necesidad
ORDER BY o.id_necesidad, o.numero_ola;
GO

/* ---- 6. DEMO EN VIVO: la clínica no llegó a su meta de A+ y amplía a 6 km ---- */
EXEC dbo.sp_lanzar_ola @id_necesidad = 30, @numero_ola = 2, @fecha_envio = '2026-11-09T10:00:00';
GO

/* ---- 7. Lo que ve la clínica: solo cifras, sin nombres ni DNI ---- */
SELECT * FROM dbo.vw_reporte_institucion ORDER BY id_necesidad DESC;
GO

/* ---- 8. Prueba de privacidad: un usuario de la clínica intenta ver donantes ---- */
EXECUTE AS USER = 'usuario_clinica_demo';
    SELECT TOP (3) id_necesidad, tipo_sangre, donantes_notificados, unidades_obtenidas
    FROM dbo.vw_reporte_institucion;                       -- permitido
    BEGIN TRY
        SELECT TOP (3) nombres FROM dbo.DONANTE;           -- bloqueado
    END TRY
    BEGIN CATCH
        SELECT N'Acceso denegado a DONANTE (esperado)' AS resultado, ERROR_MESSAGE() AS detalle;
    END CATCH;
REVERT;
GO

/* ---- 9. Alertas antifraude por revisar (plazo de 72 h) ---- */
SELECT * FROM dbo.vw_alertas_pendientes ORDER BY fecha DESC;
GO

/* ---- 10. Rastro de auditoría ---- */
SELECT TOP (15) * FROM dbo.AUDITORIA ORDER BY id_evento DESC;
GO
