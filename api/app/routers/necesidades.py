from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..config import settings
from .. import whatsapp
from ..db import Database, ErrorDeNegocio, get_db
from ..schemas import EstimadoOut, NecesidadIn, NecesidadOut, OlaIn, OlaOut, OlaResumenOut, ResultadoIn, TipoSangre
from ..security import Usuario, requiere

router = APIRouter(prefix="/necesidades", tags=["necesidades y olas (clínica)"])

_COLUMNAS = "id_necesidad, tipo_sangre, zona, unidades_meta, estado, fecha_creacion"


def _ahora() -> datetime:
    """Hora actual, pero en la fecha de referencia si está configurada (para la demo)."""
    ahora = datetime.now().replace(microsecond=0)
    if settings.fecha_referencia:
        h = settings.hoy()
        ahora = ahora.replace(year=h.year, month=h.month, day=h.day)
    return ahora


def _necesidad_propia(db: Database, id_necesidad: int, usuario: Usuario) -> dict:
    fila = db.uno(
        f"SELECT {_COLUMNAS} FROM dbo.NECESIDAD WHERE id_necesidad = ? AND id_institucion = ?",
        [id_necesidad, usuario.id_institucion],
    )
    if not fila:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe esa necesidad en tu institución.")
    return fila


_SQL_LISTA = """
SELECT n.id_necesidad, n.tipo_sangre, n.zona, n.unidades_meta, n.estado, n.fecha_creacion,
       ISNULL(r.unidades_obtenidas, 0) AS unidades_obtenidas
FROM dbo.NECESIDAD n
LEFT JOIN dbo.RESULTADO_AGREGADO r ON r.id_necesidad = n.id_necesidad
WHERE n.id_institucion = ?
ORDER BY n.id_necesidad DESC;
"""

# Respondieron = cuántos dijeron «voy». Solo el conteo: la clínica nunca ve quién.
_SQL_OLAS = """
SELECT o.id_necesidad, o.numero_ola, o.radio_km, o.donantes_notificados, o.fecha_envio,
       (SELECT COUNT(*) FROM dbo.NOTIFICACION x
        JOIN dbo.RESPUESTA_CONVOCATORIA rc ON rc.id_notificacion = x.id_notificacion
        WHERE x.id_ola = o.id_ola AND rc.respuesta = 'voy') AS respondieron
FROM dbo.OLA_CONVOCATORIA o
JOIN dbo.NECESIDAD n ON n.id_necesidad = o.id_necesidad
WHERE n.id_institucion = ?
ORDER BY o.id_necesidad, o.numero_ola;
"""


@router.get("", response_model=list[NecesidadOut], summary="Necesidades de mi institución, con sus olas y unidades")
def listar(usuario: Usuario = Depends(requiere("clinica")), db: Database = Depends(get_db)) -> list[NecesidadOut]:
    necesidades = db.consultar(_SQL_LISTA, [usuario.id_institucion])
    olas: dict[int, list[OlaResumenOut]] = {}
    for o in db.consultar(_SQL_OLAS, [usuario.id_institucion]):
        olas.setdefault(int(o["id_necesidad"]), []).append(OlaResumenOut(**o))
    return [NecesidadOut(**n, olas=olas.get(int(n["id_necesidad"]), [])) for n in necesidades]


@router.get("/estimado", response_model=EstimadoOut,
            summary="Cuántos donantes elegibles hay a cierta distancia de mi clínica (solo la cifra)")
def estimado(radio_km: int = Query(3, ge=1, le=10), tipo_sangre: TipoSangre | None = None,
             usuario: Usuario = Depends(requiere("clinica")), db: Database = Depends(get_db)) -> EstimadoOut:
    sql = ("SELECT COUNT(*) AS n FROM dbo.fn_donantes_elegibles(?) e "
           "CROSS JOIN (SELECT ubicacion FROM dbo.INSTITUCION WHERE id_institucion = ?) i "
           "WHERE e.ubicacion.STDistance(i.ubicacion) <= ? * 1000.0")
    params: list = [settings.hoy(), usuario.id_institucion, radio_km]
    if tipo_sangre:
        sql += " AND e.tipo_sangre = ?"
        params.append(tipo_sangre)
    fila = db.uno(sql, params)
    return EstimadoOut(tipo_sangre=tipo_sangre, radio_km=radio_km, donantes_elegibles=int(fila["n"]) if fila else 0)


@router.post("", response_model=NecesidadOut, status_code=status.HTTP_201_CREATED,
             summary="Declarar una necesidad (sin datos de pacientes)")
def crear(datos: NecesidadIn, usuario: Usuario = Depends(requiere("clinica")),
          db: Database = Depends(get_db)) -> NecesidadOut:
    fila = db.uno(
        "INSERT INTO dbo.NECESIDAD (id_institucion, tipo_sangre, zona, unidades_meta, estado, fecha_creacion) "
        "OUTPUT INSERTED.id_necesidad, INSERTED.tipo_sangre, INSERTED.zona, INSERTED.unidades_meta, "
        "INSERTED.estado, INSERTED.fecha_creacion "
        "VALUES (?, ?, ?, ?, N'Activa', ?)",
        [usuario.id_institucion, datos.tipo_sangre, datos.zona, datos.unidades_meta, _ahora()],
    )
    return NecesidadOut(**fila)


@router.post("/{id_necesidad}/olas", response_model=OlaOut, summary="Lanzar la siguiente ola (3 → 6 → 10 km)")
def lanzar_ola(id_necesidad: int, datos: OlaIn | None = None, usuario: Usuario = Depends(requiere("clinica")),
               db: Database = Depends(get_db)) -> OlaOut:
    necesidad = _necesidad_propia(db, id_necesidad, usuario)
    numero = datos.numero_ola if datos and datos.numero_ola else None
    if numero is None:
        fila = db.uno(
            "SELECT ISNULL(MAX(numero_ola), 0) + 1 AS siguiente FROM dbo.OLA_CONVOCATORIA WHERE id_necesidad = ?",
            [id_necesidad],
        )
        numero = int(fila["siguiente"])
    if numero > 3:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya se lanzaron las 3 olas (10 km) de esta necesidad.")
    try:
        r = db.uno(
            "SET NOCOUNT ON; EXEC dbo.sp_lanzar_ola @id_necesidad = ?, @numero_ola = ?, @fecha_envio = ?, @silencioso = 0",
            [id_necesidad, numero, _ahora()],
        )
    except ErrorDeNegocio as e:
        codigo = status.HTTP_400_BAD_REQUEST if e.codigo == 50001 else status.HTTP_409_CONFLICT
        raise HTTPException(codigo, e.mensaje) from e
    enviados, error = _avisar_por_whatsapp(db, id_necesidad, numero, necesidad["tipo_sangre"], usuario)
    return OlaOut(
        id_necesidad=id_necesidad,
        tipo_sangre=necesidad["tipo_sangre"],
        numero_ola=numero,
        radio_km=int(r["radio_km"]),
        donantes_notificados=int(r["donantes_notificados_en_esta_ola"]),
        whatsapp_enviados=enviados,
        whatsapp_error=error,
    )


_SQL_AVISADOS = """
SELECT x.id_notificacion, d.telefono_whatsapp, i.razon_social AS institucion,
       CAST(d.ubicacion.STDistance(i.ubicacion) / 1000.0 AS DECIMAL(5, 1)) AS distancia_km
FROM dbo.NOTIFICACION x
JOIN dbo.OLA_CONVOCATORIA o ON o.id_ola = x.id_ola
JOIN dbo.NECESIDAD n        ON n.id_necesidad = o.id_necesidad
JOIN dbo.INSTITUCION i      ON i.id_institucion = n.id_institucion
JOIN dbo.DONANTE d          ON d.id_donante = x.id_donante
WHERE o.id_necesidad = ? AND o.numero_ola = ?;
"""


def _avisar_por_whatsapp(db: Database, id_necesidad: int, numero_ola: int, tipo: str,
                         usuario: Usuario) -> tuple[int, str | None]:
    """Envía el aviso real solo a los notificados cuyo celular es un número de prueba de Meta."""
    if not whatsapp.configurado():
        return 0, None
    enviados, error = 0, None
    for a in db.consultar(_SQL_AVISADOS, [id_necesidad, numero_ola]):
        if not whatsapp.es_de_prueba(a["telefono_whatsapp"]):
            continue  # donante ficticio: su aviso queda solo en la base
        try:
            whatsapp.enviar_plantilla(a["telefono_whatsapp"], [a["institucion"], tipo, f"{a['distancia_km']}"])
            estado = "Enviado"
            enviados += 1
        except whatsapp.ErrorWhatsApp as e:
            estado, error = "Fallido", str(e)
        db.ejecutar("UPDATE dbo.NOTIFICACION SET canal = 'WhatsApp', estado_entrega = ? WHERE id_notificacion = ?",
                    [estado, a["id_notificacion"]])
    if enviados or error:
        db.ejecutar(
            "INSERT INTO dbo.AUDITORIA (usuario, accion, tabla_afectada, fecha_hora) "
            "VALUES (?, ?, N'NOTIFICACION', SYSDATETIME())",
            [usuario.etiqueta, f"WhatsApp ola {numero_ola} de la necesidad {id_necesidad}: {enviados} enviados"
                               + (" (con errores)" if error else "")])
    return enviados, error


@router.post("/{id_necesidad}/resultado", status_code=status.HTTP_204_NO_CONTENT,
             summary="Registrar unidades obtenidas (solo la cifra, sin nombres)")
def registrar_resultado(id_necesidad: int, datos: ResultadoIn, usuario: Usuario = Depends(requiere("clinica")),
                        db: Database = Depends(get_db)) -> None:
    _necesidad_propia(db, id_necesidad, usuario)
    db.ejecutar(
        "MERGE dbo.RESULTADO_AGREGADO AS t USING (SELECT ? AS id_necesidad, ? AS unidades) AS s "
        "ON t.id_necesidad = s.id_necesidad "
        "WHEN MATCHED THEN UPDATE SET unidades_obtenidas = s.unidades, "
        "  fecha_cierre = CASE WHEN ? = 1 THEN SYSDATETIME() ELSE t.fecha_cierre END "
        "WHEN NOT MATCHED THEN INSERT (id_necesidad, unidades_obtenidas, fecha_cierre) "
        "  VALUES (s.id_necesidad, s.unidades, CASE WHEN ? = 1 THEN SYSDATETIME() END);",
        [id_necesidad, datos.unidades_obtenidas, int(datos.cerrar), int(datos.cerrar)],
    )
    if datos.cerrar:
        db.ejecutar("UPDATE dbo.NECESIDAD SET estado = N'Cerrada' WHERE id_necesidad = ?", [id_necesidad])
    db.ejecutar(
        "INSERT INTO dbo.AUDITORIA (usuario, accion, tabla_afectada, fecha_hora) VALUES (?, ?, N'RESULTADO_AGREGADO', SYSDATETIME())",
        [usuario.etiqueta, f"Resultado de la necesidad {id_necesidad}: {datos.unidades_obtenidas} unidades"],
    )
