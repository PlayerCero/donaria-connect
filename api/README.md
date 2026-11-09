# API de Donaria Connect (FastAPI) — fases 2 a 5

API en Python que conecta la web con la base de datos. La lógica pesada vive en SQL Server
(`fn_donantes_elegibles`, `sp_lanzar_ola`, reglas antifraude); la API valida, autoriza y llama a la base.

## Rutas

| Método y ruta | Quién | Qué hace |
|---|---|---|
| `POST /auth/token-demo` | cualquiera | Token de demostración por rol (`donante` + id, `clinica` + id_usuario, `equipo`) |
| `POST /donantes` | público | Registro: guarda hash del DNI, ubica al donante en el centro de su distrito y registra el consentimiento. DNI repetido → 409 y alerta R4 |
| `GET /donantes/me` | donante | Perfil, historial, próxima fecha posible y si puede donar hoy (con el motivo si no) |
| `POST` / `DELETE /donantes/me/consentimiento` | donante | Aceptar / revocar |
| `GET /donantes/me/convocatoria` | donante | Último aviso de una necesidad activa (o `null`), con distancia y su respuesta |
| `PUT /donantes/me/convocatorias/{id}/respuesta` | donante | Responder «voy» / «no» (o `null` para borrar). La clínica solo ve el conteo |
| `GET` / `POST /necesidades` | clínica | Listar (con olas, respondieron y unidades) / declarar una necesidad (sin datos de pacientes) |
| `GET /necesidades/estimado` | clínica | Cuántos donantes elegibles hay a `radio_km` de la clínica (opcional `tipo_sangre`) |
| `POST /necesidades/{id}/olas` | clínica | Lanza la siguiente ola (3 → 6 → 10 km) con `sp_lanzar_ola`. Si WhatsApp está configurado, envía la plantilla real **solo** a los notificados cuyo celular está en `WHATSAPP_NUMEROS_PRUEBA` y guarda *Enviado* o *Fallido* en `NOTIFICACION` |
| `POST /necesidades/{id}/resultado` | clínica | Unidades obtenidas (solo la cifra) y cierre |
| `GET /reportes` | clínica, equipo | `vw_reporte_institucion`: solo cifras |
| `GET /alertas` · `GET /alertas/resumen` · `PATCH /alertas/{id}/revisar` · `POST /alertas/ejecutar-reglas` | equipo | Antifraude. La revisión acepta `decision` y `nota`, que quedan en auditoría |
| `POST /verificacion` · `GET /verificacion` | donante | Crea la sesión de Didit (enlace + código QR para el celular) y consulta cómo va; si Didit aprueba, el donante pasa a *verificado*. Solo se guarda el id de la sesión y su estado, nunca imágenes |
| `POST /webhooks/didit` | Didit | Resultado firmado (HMAC-SHA256, `X-Signature-V2`). Sirve con la API publicada: `https://donaria-eric-api-eqg0dpfxgneubpbs.brazilsouth-01.azurewebsites.net/webhooks/didit` |
| `POST /whatsapp/prueba` | equipo | Envía un aviso de ejemplo a los números de prueba (para comprobar el token y la plantilla) |
| `GET /instituciones` | todos con token | Bancos de sangre de la red (sin datos de donantes) |
| `GET /health` · `GET /health/db` | público | Estado de la API y de la conexión a la base |

> **Login de demostración:** el token se pide indicando rol e id, sin contraseña. Sirve para la demo con
> datos ficticios; en producción el donante entraría con un código por WhatsApp/SMS y la clínica con Microsoft Entra.

## Correrla en Windows

**Una sola vez:**

1. Driver ODBC 18 para SQL Server. Para ver si ya lo tienes, en PowerShell:
   `Get-OdbcDriver | Select-Object Name` → debe aparecer *ODBC Driver 18 for SQL Server*.
   Si no está: <https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server>.
2. Clonar el repo y crear el entorno:
   ```powershell
   git clone https://github.com/PlayerCero/donaria-connect.git
   cd donaria-connect
   copy .env.example .env      # y completa JWT_SECRET y DB_USER
   cd api
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```

Después de cargar `db/01_*.sql`, aplica los cambios de la fase 3 (tabla de respuestas):
`python ..\scripts\migrar.py` (con el entorno activo). `scripts\abrir_demo.ps1` hace todo esto solo.

**Cada vez:**

```powershell
cd donaria-connect\api
.venv\Scripts\activate
uvicorn app.main:app --reload
```

Abre <http://127.0.0.1:8000/docs>. Con Azure SQL (`DB_AUTH=entra-interactive`), la primera consulta abre la
ventana de inicio de sesión de Microsoft.

## Probar

- **Pruebas automáticas** (no necesitan base): `python -m pytest -q` desde `api/`.
- **Prueba de punta a punta contra la base real**, con la API levantada, desde otra terminal en la raíz del repo:
  `python scripts\smoke_test.py`. Crea datos ficticios: una necesidad O+ de prueba con sus 3 olas y un donante de prueba.
