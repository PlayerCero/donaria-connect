# Donaria Connect — contexto para Claude

Demo funcional de convocatoria de donantes voluntarios de sangre por olas (3 → 6 → 10 km) para bancos de sangre de
Lima. Proyecto de portafolio de Eric Salinas (ingeniería de datos), derivado del trabajo final del curso Dirección de
Proyectos (UDEP, 2026-II). El plan por fases está en `docs/PLAN.md`.

## Reglas no negociables
- Solo datos ficticios y números de prueba. Nunca DNI, nombres ni datos de salud reales.
- Ninguna donación se vincula a un paciente identificado (art. 9, Ley N.° 26454).
- La clínica solo ve cifras agregadas (`vw_reporte_institucion`), nunca nombres ni DNI; se hace cumplir con permisos en la base.
- El DNI se guarda como hash SHA-256 con sal (`'donaria-2026|' + dni`); para mostrar se usa `dni_ult4`.
- Las claves van en `.env` (no se sube); `.env.example` lista las variables.

## Stack
- Base: SQL Server / Azure SQL. `db/01_crear_y_cargar.sql` crea todo (11 tablas, 500 donantes ficticios,
  `fn_donantes_elegibles`, `sp_lanzar_ola`, `sp_ejecutar_reglas_antifraude`, vistas, rol `rol_institucion`).
  Fecha de referencia del escenario: 2026-11-09. Generación aleatoria determinista con `HASHBYTES('MD5', ...)`.
- API: Python + FastAPI + pyodbc (fase 2, pendiente).
- Web: `web/` (HTML/CSS/JS sin dependencias; hoy lee `web/js/data.js`, se reemplazará por llamadas a la API).
- Integraciones: Didit en sandbox (workflow ID + liveness + face match), WhatsApp Cloud API con número de prueba.
- Analítica: BigQuery + Looker Studio en proyecto personal de Google Cloud (nunca el de Clean Lab).

## Reglas de la base
- Elegible = verificado + consentimiento vigente + sin alerta pendiente + 90 días (M) / 120 días (F) desde la última donación.
- Olas: 1 = 3 km, 2 = 6 km, 3 = 10 km; mismo grupo sanguíneo; no se repite a quien ya fue notificado en la necesidad.
- Antifraude: R1 intervalo menor al mínimo, R2 dos instituciones el mismo día, R3 celular compartido, R4 DNI duplicado.

## Estilo
- Textos de la app en español, en oración, con verbos que dicen lo que pasa.
- Sistema de diseño en `web/css/tokens.css`: no romper colores ni tamaños mínimos (ver `web/README.md`).
