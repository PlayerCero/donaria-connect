# Base de datos de Donaria Connect (SQL Server)

Paquetes de la EDT que cubre: **4.2.2** (script + 500 registros ficticios), **4.2.3** (consultas de
elegibilidad y segmentación) y **4.5.1** (reglas antifraude). Responsable: Eric Salinas.

| Archivo | Qué hace |
|---|---|
| `01_crear_y_cargar.sql` | Crea la base `DonariaConnect`, las 11 tablas, 500 donantes ficticios, la lógica (elegibilidad, olas, antifraude), las vistas y los permisos. Se puede volver a correr: borra y recrea todo. |
| `02_consultas_exposicion.sql` | Las 10 consultas para mostrar el lunes, incluida una ola lanzada en vivo. |
| `03_fase3_respuestas.sql` | Fase 3: tabla `RESPUESTA_CONVOCATORIA` (lo que el donante contesta al aviso) y respuestas ficticias. Se corre después de `01`; también lo aplica `scripts/migrar.py`. |

Funciona en SQL Server 2016 o superior (Express sirve). Escenario fechado al **lunes 09/11/2026**.

## 1. Saber a qué servidor conectarte

Abre SSMS. En la ventana *Connect to Server*:
- **Server name:** prueba `localhost\SQLEXPRESS`; si falla, `localhost` o `.`
- **Authentication:** Windows Authentication
- Si aparece un error de certificado: pestaña *Options* o casilla **Trust server certificate** ✔

Para ver la versión: *New Query* → escribe `SELECT @@VERSION;` → F5.

## 2. Correrlo en SSMS

1. **File → Open → File** → `01_crear_y_cargar.sql` → **F5**. Tarda segundos.
   Al final sale una tabla con los registros por tabla (DONANTE debe decir **500**) y en *Messages*:
   `Registro bloqueado (esperado)…` — eso es la regla antifraude R4 funcionando, no un error.
2. **File → Open → File** → `02_consultas_exposicion.sql`. Selecciona una consulta con el mouse y
   presiona **F5**: SSMS ejecuta solo lo seleccionado.

**Por terminal** (o pedírselo a Claude Code en VS Code), desde esta carpeta:

```
sqlcmd -S localhost\SQLEXPRESS -E -C -f 65001 -i 01_crear_y_cargar.sql
```

Si sale un error, copia el mensaje completo con su número de línea y pégaselo a Claude.

## 3. Capturas para el Word (Figura 17)

1. **Diagrama:** en el Object Explorer, `DonariaConnect` → clic derecho en *Database Diagrams* →
   *New Database Diagram* (si pide instalar objetos de soporte, acepta) → selecciona las 11 tablas →
   *Add* → acomódalas → captura.
2. **Consulta de elegibilidad:** resultado de las consultas 1 y 2 del archivo `02`.
3. Opcional para la exposición: consulta 4 (segmentación por distancia) y 8 (prueba de privacidad).

## 4. Qué demostrar el lunes (5 minutos)

| # | Consulta | Qué dice |
|---|---|---|
| 1–2 | Elegibilidad | De 500 registrados, cuántos pueden donar hoy y por qué no los demás: Didit, consentimiento, antifraude o intervalo de 90/120 días. |
| 4 | Segmentación | Hay pocos donantes O− cerca de la clínica: por eso se convoca por olas de 3 → 6 → 10 km y no a todos de golpe. |
| 6 | Ola en vivo | La clínica amplía la necesidad A+ a 6 km. El sistema notifica solo a los nuevos, sin repetir. |
| 7–8 | Privacidad | La clínica ve cifras; si intenta leer la tabla de donantes, SQL Server se lo niega (Ley 26454, art. 9; Ley 29733). |
| 9 | Antifraude | Las 4 reglas disparadas sobre casos sembrados, con plazo de revisión de 72 h. |

Antes de exponer, corre la **consulta 0** del archivo `02`: deja lista la ola en vivo.

## 5. Reglas antifraude (paquete 4.5.1)

| Código | Regla | Caso de prueba sembrado |
|---|---|---|
| R1 | Dos donaciones con menos de 90 días (hombres) o 120 días (mujeres) de separación | Donantes 11, 12 y 13 |
| R2 | Donación confirmada en 2 instituciones distintas el mismo día | Donante 21 |
| R3 | Mismo celular asociado a 2 o más DNI distintos | Donantes 31 y 32 |
| R4 | Intento de registro con un DNI ya registrado (bloqueado por `UNIQUE` sobre el hash) | DNI del donante 1 |

Un donante con alerta pendiente queda fuera de las convocatorias hasta que el equipo la revise.

## 6. Diferencias con el modelo de la Figura 16

Se añadieron 5 columnas, necesarias para las reglas: `DONANTE.sexo`, `DONANTE.dni_ult4` (para mostrar
`****1234` sin guardar el DNI), `CONSENTIMIENTO.vigente`, `ALERTA_ANTIFRAUDE.id_institucion` y
`ALERTA_ANTIFRAUDE.codigo_regla`. Conviene mencionarlas en la nota de la Figura 16 o actualizar el diagrama.

Otras decisiones: el DNI se guarda como hash SHA-256 con sal; la convocatoria busca el **mismo grupo
sanguíneo** que la necesidad (el banco repone stock de ese grupo); las cifras de notificados no
coinciden con las del prototipo navegable, porque estas salen de los 500 registros ficticios.

> Nota: el script se escribió el 07/11/2026 sin poder ejecutarlo en un SQL Server de prueba. La primera
> corrida en la PC de Eric es la prueba real.
