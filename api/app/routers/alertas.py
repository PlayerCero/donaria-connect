from fastapi import APIRouter, Depends, HTTPException, status

from ..db import Database, get_db
from ..schemas import AlertaOut
from ..security import Usuario, requiere

router = APIRouter(prefix="/alertas", tags=["antifraude (equipo Donaria)"])


@router.get("", response_model=list[AlertaOut], summary="Alertas pendientes (plazo de 72 h)")
def pendientes(usuario: Usuario = Depends(requiere("equipo")), db: Database = Depends(get_db)) -> list[AlertaOut]:
    filas = db.consultar("SELECT * FROM dbo.vw_alertas_pendientes ORDER BY fecha DESC")
    return [AlertaOut(**f) for f in filas]


@router.post("/ejecutar-reglas", status_code=status.HTTP_204_NO_CONTENT, summary="Correr las reglas R1–R3 ahora")
def ejecutar_reglas(usuario: Usuario = Depends(requiere("equipo")), db: Database = Depends(get_db)) -> None:
    db.ejecutar("SET NOCOUNT ON; DECLARE @ahora DATETIME2(0) = SYSDATETIME(); "
                "EXEC dbo.sp_ejecutar_reglas_antifraude @ahora = @ahora")


@router.patch("/{id_alerta}/revisar", status_code=status.HTTP_204_NO_CONTENT,
              summary="Marcar una alerta como revisada (el donante vuelve a ser convocable)")
def revisar(id_alerta: int, usuario: Usuario = Depends(requiere("equipo")), db: Database = Depends(get_db)) -> None:
    cambiadas = db.ejecutar(
        "UPDATE dbo.ALERTA_ANTIFRAUDE SET estado_revision = N'Revisada' WHERE id_alerta = ? AND estado_revision = N'Pendiente'",
        [id_alerta],
    )
    if cambiadas == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay una alerta pendiente con ese id.")
    db.ejecutar(
        "INSERT INTO dbo.AUDITORIA (usuario, accion, tabla_afectada, fecha_hora) VALUES (?, ?, N'ALERTA_ANTIFRAUDE', SYSDATETIME())",
        [usuario.etiqueta, f"Alerta {id_alerta} revisada"],
    )
