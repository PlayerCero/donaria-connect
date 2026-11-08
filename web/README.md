# Web de Donaria Connect (prototipo conectado)

Funciona de dos formas, sin instalar nada en la web:

- **Conectada a la base (fase 3).** Si la API responde en `http://127.0.0.1:8000`, `js/api.js` carga los datos de
  Azure SQL y las acciones se guardan de verdad. En el mapa de pantallas y en el panel aparece *Conectado a la base*.
  La forma más simple de levantar todo es `scripts/abrir_demo.ps1` (abre <http://127.0.0.1:5500>).
- **Con datos de ejemplo.** Si la API no responde (o con `index.html?modo=ejemplo`), usa `js/data.js`, como el
  prototipo original: basta abrir `index.html` con doble clic.

Otra dirección de API: `index.html?api=https://mi-api…` (se recuerda en el navegador).

| Superficie | Rutas |
| --- | --- |
| Mapa de pantallas | `#inicio` |
| App del donante (celular) | `#d-registro`, `#d-verificacion`, `#d-consentimiento`, `#d-hoy`, `#d-convocatoria`, `#d-historial`, `#d-perfil` |
| Panel institucional (escritorio) | `#p-resumen`, `#p-nueva`, `#p-conv-31`, `#p-necesidades`, `#p-reportes` |
| Equipo Donaria | `#a-alertas`, `#a-instituciones` |
| Público | `#preregistro` |

## Capturas para el Word
- Pantallas del donante: ventana del navegador angosta (unos 420 px) o modo dispositivo de las herramientas
  de desarrollador (F12 → icono de celular → iPhone 14).
- Panel: ventana ancha (1360 px o más).
- Modo oscuro: cambia el tema del sistema operativo; la app lo sigue sola.

## Qué se guarda en la base cuando está conectada

| Pantalla | Acción | Ruta de la API |
| --- | --- | --- |
| Registro (paso 3) | Crear mi registro | `POST /donantes` (DNI con hash, consentimiento) |
| Hoy / Convocatoria | Voy a ir · Esta vez no puedo | `PUT /donantes/me/convocatorias/{id}/respuesta` |
| Perfil | Retirar consentimiento | `DELETE /donantes/me/consentimiento` |
| Nueva necesidad | Lanzar convocatoria (olas hasta el radio elegido) | `POST /necesidades` + `POST /necesidades/{id}/olas` |
| Convocatoria | Lanzar ola · Guardar unidades · Cerrar | `POST …/olas` · `POST …/resultado` |
| Alertas | Guardar revisión (la decisión queda en auditoría) | `PATCH /alertas/{id}/revisar` |

Con la API conectada, el registro va datos → consentimiento → verificación. Si la API tiene las claves de Didit,
la verificación es real (sandbox): la pantalla muestra un código QR para hacerla en el celular y se actualiza sola
cuando Didit aprueba. Sin claves, sigue simulada. La app del donante muestra al donante que recibió el
último aviso (o al que te registraste desde ese navegador; en el mapa de pantallas puedes volver al de demostración).
El panel entra como la clínica 1 (Clínica Delgado Auna). Dirección y horario de cada clínica vienen de `data.js`
porque la base no los guarda.

Fuente de los grupos sanguíneos: Barlow Semi Condensed (licencia OFL, en `fonts/`), solo para cifras y rótulos.
