# Prototipo navegable – Donaria Connect

Abre `index.html` en el navegador (doble clic). No necesita instalar nada ni internet.

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

## Para conectarlo a la base de datos real
`js/data.js` usa los mismos nombres de tablas y columnas que el modelo de SQL Server. Reemplázalo por llamadas
a la API (por ejemplo `fetch('/api/necesidades')`) sin tocar las pantallas.

Fuente de los grupos sanguíneos: Barlow Semi Condensed (licencia OFL, en `fonts/`), solo para cifras y rótulos.
