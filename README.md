# Donaria Connect

Convocatoria de **donantes voluntarios de sangre** para bancos de sangre de Lima. La clínica declara una necesidad
(grupo sanguíneo + zona) y el sistema avisa por **olas de 3 → 6 → 10 km** solo a donantes compatibles, elegibles y
cercanos, que acuden directo al banco de sangre.

> **Demo con datos ficticios.** No contiene ni procesa DNI, nombres ni datos de salud reales.

## Por qué existe

Avisar a todos los donantes de golpe agota la base con mensajes; no avisar a nadie deja la necesidad sin cubrir.
Las olas avisan primero a los más cercanos y amplían el radio solo si no se llega a la meta.

## Reglas de diseño

- Ninguna donación se vincula a un paciente identificado (art. 9, Ley N.° 26454).
- La clínica solo ve cifras agregadas, nunca nombres ni DNI (se hace cumplir con permisos en la base).
- El DNI se guarda como hash SHA-256; datos personales bajo la Ley N.° 29733.
- Elegibilidad: identidad verificada, consentimiento vigente, sin alerta antifraude y 90 días (H) / 120 días (M) desde la última donación.

## Arquitectura

```
Web del donante y panel de la clínica (HTML/JS)
        │
        ▼
API en Python (FastAPI) ──► Didit (verificación de identidad, sandbox)
        │               ──► WhatsApp Cloud API (número de prueba)
        ▼
Azure SQL / SQL Server  ── extracción diaria ──►  BigQuery ──► Looker Studio
(operación)                                        (análisis)
```

SQL Server opera la app (transacciones, claves únicas, respuestas en milisegundos); BigQuery analiza el histórico.

## Estructura

| Carpeta | Contenido | Estado |
|---|---|---|
| `db/` | Script de creación + 500 donantes ficticios, olas, antifraude, vistas y permisos; consultas de demo. `01_azure.sql` es la versión para Azure SQL | ✅ local y en Azure SQL |
| `web/` | Prototipo navegable (sin dependencias). Abrir `web/index.html` | ✅ con datos de ejemplo |
| `api/` | API en FastAPI | 🔲 fase 2 |
| `pipeline/` | Extracción a BigQuery | 🔲 fase 7 |
| `docs/` | Plan por fases y diagrama de la base | ✅ |

## Probar la base de datos

1. SQL Server 2016+ (Express sirve) y SSMS.
2. Abrir `db/01_crear_y_cargar.sql` → F5. Crea la base `DonariaConnect` con 500 donantes ficticios.
3. Abrir `db/02_consultas_exposicion.sql` y ejecutar cada consulta por separado.

## Origen

Trabajo final del curso Dirección de Proyectos (UDEP, 2026-II, Grupo 5). Esta demo funcional la desarrolla
Eric Salinas (tecnología y datos). Licencia MIT.
