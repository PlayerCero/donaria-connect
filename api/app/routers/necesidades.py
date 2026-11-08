from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from ..config import settings
from ..db import Database, ErrorDeNegocio, get_db
from ..schemas import NecesidadIn, NecesidadOut, OlaIn, OlaOut, ResultadoIn
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


@router.get("", response_model=list[NecesidadOut], summary="Necesidades de mi institución")
def listar(usuario: Usuario = Depends(requiere("clinica")), db: Database = Depends(get_db)) -> list[NecesidadOut]:
    filas = db.consultar(
        f"SELECT {_COLUMNAS} FROM dbo.NECESIDAD WHERE id_institucion = ? ORDER BY id_necesidad DESC",
        [usuario.id_institucion],
    )
    return [NecesidadOut(**f) for f in filas]


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
    return OlaOut(
        id_necesidad=id_necesidad,
        tipo_sangre=necesidad["tipo_sangre"],
        numero_ola=numero,
        radio_km=int(r["radio_km"]),
        donantes_notificados=int(r["donantes_notificados_en_esta_ola"]),
    )


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
