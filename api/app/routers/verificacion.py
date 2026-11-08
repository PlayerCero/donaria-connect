"""Verificación de identidad con Didit (fase 4).

Flujo de la demo (la API corre en la PC, Didit no puede llamarla):
1. POST /verificacion crea la sesión en Didit y devuelve el enlace y un código QR.
2. El donante abre el enlace en el celular: foto del DNI, selfie con prueba de vida y comparación de rostro.
3. La web consulta GET /verificacion cada pocos segundos; la API le pregunta a Didit y, si aprobó,
   marca al donante como verificado.
Cuando la API esté publicada (fase 6), Didit también avisará por POST /webhooks/didit.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from .. import didit
from ..config import settings
from ..db import Database, get_db
from ..schemas import VerificacionOut
from ..security import Usuario, requiere

router = APIRouter(tags=["verificación de identidad (Didit)"])


def _no_configurado() -> HTTPException:
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                         "Didit no está configurado en la API (faltan DIDIT_API_KEY y DIDIT_WORKFLOW_ID en .env).")


def _aplicar_estado(db: Database, id_donante: int, session_id: str, estado: str, origen: str) -> None:
    """Guarda el estado de la sesión y, si es definitivo, actualiza al donante."""
    db.ejecutar(
        "UPDATE dbo.VERIFICACION_IDENTIDAD SET estado_didit = ?, fecha_actualizacion = SYSDATETIME() "
        "WHERE session_id = ?", [estado[:20], session_id])
    nuevo = didit.A_ESTADO_DONANTE.get(estado)
    if nuevo:
        db.ejecutar("UPDATE dbo.DONANTE SET estado_verificacion = ? WHERE id_donante = ?", [nuevo, id_donante])
        db.ejecutar(
            "INSERT INTO dbo.AUDITORIA (usuario, accion, tabla_afectada, fecha_hora) "
            "VALUES (?, ?, N'DONANTE', SYSDATETIME())",
            [origen, f"Didit: identidad del donante {id_donante} {'aprobada' if nuevo == 'verificado' else 'rechazada'}"])


def _ultima(db: Database, id_donante: int) -> dict | None:
    return db.uno(
        "SELECT TOP (1) v.session_id, v.url, v.estado_didit, d.estado_verificacion "
        "FROM dbo.DONANTE d LEFT JOIN dbo.VERIFICACION_IDENTIDAD v ON v.id_donante = d.id_donante "
        "WHERE d.id_donante = ? ORDER BY v.fecha_creacion DESC", [id_donante])


def _salida(fila: dict, con_qr: bool = True) -> VerificacionOut:
    url = fila.get("url")
    abierta = bool(url) and fila.get("estado_didit") not in didit.FINALES
    return VerificacionOut(
        estado_verificacion=fila["estado_verificacion"],
        estado_didit=fila.get("estado_didit"),
        url=url if abierta else None,
        qr_svg=didit.qr_svg(url) if abierta and con_qr else None,
        didit_configurado=didit.configurado(),
    )


@router.post("/verificacion", response_model=VerificacionOut, summary="Iniciar la verificación con Didit")
def iniciar(usuario: Usuario = Depends(requiere("donante")), db: Database = Depends(get_db)) -> VerificacionOut:
    if not didit.configurado():
        raise _no_configurado()
    actual = _ultima(db, usuario.id)
    if not actual:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe ese donante.")
    if actual["estado_verificacion"] == "verificado":
        raise HTTPException(status.HTTP_409_CONFLICT, "Tu identidad ya está verificada.")
    try:
        # vendor_data identifica al donante en Didit sin datos personales.
        s = didit.crear_sesion(f"donante-{usuario.id}")
    except didit.ErrorDidit as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e
    # Didit devuelve la misma sesión si sigue abierta: solo se inserta si es nueva.
    db.ejecutar(
        "IF NOT EXISTS (SELECT 1 FROM dbo.VERIFICACION_IDENTIDAD WHERE session_id = ?) "
        "INSERT INTO dbo.VERIFICACION_IDENTIDAD (id_donante, session_id, url, estado_didit, fecha_creacion, fecha_actualizacion) "
        "VALUES (?, ?, ?, ?, SYSDATETIME(), SYSDATETIME())",
        [s["session_id"], usuario.id, s["session_id"], s["url"], str(s.get("status") or "Not Started")[:20]])
    return _salida({"estado_verificacion": actual["estado_verificacion"], "url": s["url"],
                    "estado_didit": s.get("status") or "Not Started"})


@router.get("/verificacion", response_model=VerificacionOut, summary="¿Cómo va mi verificación? (consulta a Didit)")
def consultar(usuario: Usuario = Depends(requiere("donante")), db: Database = Depends(get_db)) -> VerificacionOut:
    fila = _ultima(db, usuario.id)
    if not fila:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe ese donante.")
    if fila.get("session_id") and fila.get("estado_didit") not in didit.FINALES and didit.configurado():
        try:
            estado = didit.estado_sesion(fila["session_id"])
        except didit.ErrorDidit:
            estado = ""  # Didit aún no tiene decisión (o no respondió): se mantiene lo guardado
        if estado and estado != fila["estado_didit"]:
            _aplicar_estado(db, usuario.id, fila["session_id"], estado, f"donante:{usuario.id}")
            fila = _ultima(db, usuario.id)
    return _salida(fila, con_qr=False)


@router.post("/webhooks/didit", status_code=status.HTTP_204_NO_CONTENT,
             summary="Didit avisa el resultado (requiere la API publicada y DIDIT_WEBHOOK_SECRET)")
async def webhook(request: Request, db: Database = Depends(get_db)) -> None:
    cuerpo = await request.json()
    if not didit.firma_valida(cuerpo, request.headers.get("x-signature-v2", ""),
                              request.headers.get("x-timestamp", ""), settings.didit_webhook_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Firma de Didit inválida.")
    session_id, estado = str(cuerpo.get("session_id", "")), str(cuerpo.get("status", ""))
    fila = db.uno("SELECT id_donante FROM dbo.VERIFICACION_IDENTIDAD WHERE session_id = ?", [session_id])
    if fila and estado:
        _aplicar_estado(db, int(fila["id_donante"]), session_id, estado, "didit:webhook")


