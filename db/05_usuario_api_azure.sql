/* =====================================================================
   DONARIA CONNECT — Fase 6: permiso para la API publicada en Azure App Service
   Se corre UNA vez en Azure SQL (base DonariaConnect) con tu cuenta de Microsoft Entra,
   desde SSMS o desde el Editor de consultas del portal.

   La API publicada entra con su identidad administrada (sin contraseñas): el usuario se
   llama igual que la aplicación web (donaria-eric-api). Solo lee, escribe y ejecuta los
   procedimientos; no puede cambiar tablas ni permisos.
   ===================================================================== */
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'donaria-eric-api')
    CREATE USER [donaria-eric-api] FROM EXTERNAL PROVIDER;
ALTER ROLE db_datareader ADD MEMBER [donaria-eric-api];
ALTER ROLE db_datawriter ADD MEMBER [donaria-eric-api];
GRANT EXECUTE TO [donaria-eric-api];
SELECT name, type_desc FROM sys.database_principals WHERE name = 'donaria-eric-api';
