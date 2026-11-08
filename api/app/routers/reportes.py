from fastapi import APIRouter, Depends

from ..db import Database, get_db
from ..schemas import ReporteOut
from ..security import Usuario, requiere

router = APIRouter(prefix="/reportes", tags=["reportes (solo cifras)"])


@router.get("", response_model=list[ReporteOut], summary="Reporte agregado: notificados, unidades y cumplimiento")
def reporte(usuario: Usuario = Depends(requiere("clinica", "equipo")), db: Database = Depends(get_db)) -> list[ReporteOut]:
    """Lee `vw_reporte_institucion`: nunca incluye nombres ni DNI de donantes."""
    if usuario.rol == "clinica":
        filas = db.consultar(
            "SELECT r.* FROM dbo.vw_reporte_institucion r "
            "JOIN dbo.NECESIDAD n ON n.id_necesidad = r.id_necesidad "
            "WHERE n.id_institucion = ? ORDER BY r.id_necesidad DESC",
            [usuario.id_institucion],
        )
    else:
        filas = db.consultar("SELECT * FROM dbo.vw_reporte_institucion ORDER BY id_necesidad DESC")
    return [ReporteOut(**f) for f in filas]
