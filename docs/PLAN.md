# Donaria Connect — de prototipo a demo funcional (opción 1)

**Decidido:** 07/11/2026. **Arranque sugerido:** después del 18/11 (fin del ciclo); la fase 0 se puede hacer antes.
**Objetivo:** demo de punta a punta con usuarios de prueba y datos ficticios, publicada y presentable como proyecto de
portafolio de ingeniería de datos. **No** es un lanzamiento real: sin donantes reales, sin datos de salud reales.
**Esfuerzo:** ~58 h → 5–6 semanas a ~10 h/semana.

## Arquitectura

```
[Web del donante y panel de la clínica]  (prototipo actual, HTML/JS)
              │ HTTPS (JSON)
              ▼
[API en Python · FastAPI]  ──►  [Didit sandbox]  (verificación de identidad)
              │            ──►  [WhatsApp Cloud API · número de prueba]  (olas)
              ▼
[Azure SQL Database]  (operación: las 11 tablas, sp_lanzar_ola, reglas antifraude)
              │ extracción diaria (Python)
              ▼
[BigQuery]  ──►  [Looker Studio]  (análisis: respuesta por ola, cobertura, tiempos)
```

**Por qué dos bases:** SQL Server opera la app (transacciones, claves únicas, respuestas en milisegundos);
BigQuery analiza el histórico (no hace cumplir claves únicas ni sirve para miles de escrituras pequeñas).

## Cuentas que tiene que crear Eric (gratis; nadie más puede hacerlo)

| Cuenta | Para qué | Nota |
|---|---|---|
| GitHub | Repositorio | Ya la tiene |
| Azure (Azure for Students) | Azure SQL + hosting de la API | Con el correo `@alum.udep.edu.pe`; verificar si pide tarjeta |
| Didit (consola) | Verificación en sandbox | Pide correo de trabajo: probar con el de la UDEP |
| Meta for Developers | WhatsApp Cloud API, número de prueba | Con su cuenta de Facebook |
| Google Cloud | BigQuery (modo sandbox) y Looker Studio | El sandbox de BigQuery no pide tarjeta |

Las condiciones de los niveles gratuitos cambian: se verifican al crear cada cuenta.

## Fases

### Fase 0 · Repositorio (2 h)
1. Crear el repo `donaria-connect` en GitHub (público, con licencia MIT).
2. Clonarlo en la PC, fuera del segundo cerebro (p. ej. `C:\Users\User\proyectos\donaria-connect`).
3. Estructura:
   ```
   db/        scripts SQL (01, 02 y la versión para Azure)
   api/       FastAPI (main.py, rutas, conexión, requirements.txt)
   web/       el prototipo navegable
   pipeline/  extracción a BigQuery
   docs/      arquitectura y decisiones
   .env.example  .gitignore  README.md
   ```
4. Copiar `06-base-de-datos/*.sql` a `db/` y `02-prototipo/` a `web/`. Primer commit.
**Listo cuando:** el repo está en GitHub con las 5 carpetas y ningún secreto.

### Fase 1 · Base en la nube (4 h)
1. Crear en Azure un servidor SQL y una base `donaria` con la oferta gratuita de Azure SQL.
2. Regla de firewall para la IP de la PC.
3. Versión `db/01_azure.sql`: sin `USE master`, `CREATE DATABASE`, `DROP DATABASE` ni `ALTER DATABASE … SINGLE_USER` (Azure no los permite dentro de la base); el resto igual.
4. Correrlo desde SSMS conectado al servidor de Azure; correr las consultas 1, 2 y 4 y comparar con la PC (354 elegibles).
**Listo cuando:** las mismas cifras salen en Azure.

### Fase 2 · API (15 h)
1. `api/` con FastAPI + `pyodbc` (driver ODBC 18 de SQL Server).
2. Rutas:
   | Método y ruta | Rol | Qué hace |
   |---|---|---|
   | `POST /donantes` | público | Registro (guarda hash del DNI; responde 409 si ya existe → alerta R4) |
   | `POST /auth/login` | todos | Devuelve un token (JWT) con el rol |
   | `GET /donantes/me` | donante | Perfil, última donación, próxima fecha posible |
   | `POST /consentimiento` / `DELETE /consentimiento` | donante | Aceptar / revocar |
   | `POST /necesidades` | clínica | Declarar tipo de sangre, zona y meta |
   | `POST /necesidades/{id}/olas` | clínica | Llama a `sp_lanzar_ola` |
   | `GET /reportes` | clínica | Lee `vw_reporte_institucion` (solo cifras) |
   | `GET /alertas` · `PATCH /alertas/{id}` | equipo | Revisar alertas antifraude |
3. Pruebas automáticas mínimas (pytest) de elegibilidad y de la ola.
**Listo cuando:** `/docs` permite registrar un donante, lanzar una ola y ver el reporte.

### Fase 3 · Conectar el prototipo (8 h)
1. En `web/js/`, reemplazar `data.js` por un `api.js` con `fetch` a la API.
2. Pantallas que pasan a datos reales: registro, consentimiento, hoy, historial, perfil; panel: resumen, nueva necesidad, convocatoria, reportes; alertas.
**Listo cuando:** registrarse en la web crea la fila en Azure SQL.

### Fase 4 · Didit en sandbox (6 h)
1. Crear un flujo de verificación (documento + liveness + face match) en la consola.
2. `POST /verificacion` crea la sesión y devuelve el enlace; el donante lo abre desde la pantalla de verificación.
3. `POST /webhooks/didit` recibe el resultado, valida la firma y actualiza `DONANTE.estado_verificacion`.
**Listo cuando:** un donante de prueba pasa de "pendiente" a "verificado" sin tocar la base a mano.

### Fase 5 · WhatsApp de prueba (6 h)
1. App en Meta for Developers con WhatsApp; registrar hasta 5 números de prueba (el de Eric y compañeros).
2. Plantilla de mensaje: "Hay una necesidad de sangre {tipo} cerca de ti en {clínica}…".
3. Al lanzar una ola, la API envía la plantilla a los notificados que tengan número de prueba y guarda el estado en `NOTIFICACION.estado_entrega`.
**Listo cuando:** el celular de Eric recibe la convocatoria al lanzar una ola desde el panel.

### Fase 6 · Publicar (4 h)
1. API en Azure App Service (o Render); variables de entorno en el servicio, no en el código.
2. Web en GitHub Pages apuntando a la API.
**Listo cuando:** la demo funciona desde un enlace público.

### Fase 7 · Capa analítica en BigQuery (10 h)
1. Proyecto en Google Cloud, dataset `donaria_analitica`.
2. `pipeline/extraer_a_bigquery.py`: lee de Azure SQL solo tablas sin datos personales (NECESIDAD, OLA_CONVOCATORIA, RESULTADO_AGREGADO, NOTIFICACION sin teléfono, DONACION_CONFIRMADA con id seudonimizado) y carga en BigQuery; carga incremental por fecha.
3. Programarlo a diario (GitHub Actions con cron).
4. Dashboard en Looker Studio: tasa de respuesta por ola y radio, tiempo hasta cubrir la meta, cobertura por distrito y grupo sanguíneo.
**Listo cuando:** el dashboard se actualiza solo cada día.

### Fase 8 · Portafolio (3 h)
README con el diagrama de arquitectura, cómo correrlo, decisiones (por qué dos bases, por qué hash del DNI), un video de 2 minutos y enlace en el CV y en el portafolio de GitHub.

## Reglas
- Solo datos ficticios y números de prueba. Nunca DNI ni datos de salud reales.
- Una fase a la vez; cada fase termina con su "listo cuando" verificado.
- Si una fase se pasa del doble de sus horas, se para y se decide si se recorta.

## Historial
- 2026-11-07 — Plan creado dos días antes de la exposición preliminar 3 del curso DPY. Elegida la opción 1 (demo funcional) sobre el piloto real y sobre solo documentar.
