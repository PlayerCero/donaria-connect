from fastapi import APIRouter, Depends

from ..db import Database, get_db
from ..schemas import InstitucionOut
from ..security import Usuario, requiere

router = APIRouter(prefix="/instituciones", tags=["instituciones"])


@router.get("", response_model=list[InstitucionOut], summary="Bancos de sangre de la red (sin datos de donantes)")
def listar(usuario: Usuario = Depends(requiere("clinica", "equipo", "donante")),
           db: Database = Depends(get_db)) -> list[InstitucionOut]:
    filas = db.consultar(
        "SELECT id_institucion, razon_social, autorizacion_sanitaria, estado_afiliacion, "
        "       ubicacion.Lat AS latitud, ubicacion.Long AS longitud "
        "FROM dbo.INSTITUCION ORDER BY id_institucion"
    )
    return [InstitucionOut(**f) for f in filas]
