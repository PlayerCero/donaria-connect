from fastapi import APIRouter, Depends, HTTPException, status

from ..db import Database, get_db
from ..schemas import TokenDemoIn, TokenOut
from ..security import Usuario, crear_token

router = APIRouter(prefix="/auth", tags=["autenticación (demo)"])


@router.post("/token-demo", response_model=TokenOut, summary="Pedir un token de demostración")
def token_demo(datos: TokenDemoIn, db: Database = Depends(get_db)) -> TokenOut:
    """**Solo para la demo.** Entrega un token según el rol:

    - `donante` con su `id_donante` (por ejemplo, 48). Con id 0 se elige un donante que recibió
      el último aviso de una necesidad activa (sirve para mostrar la app del donante)
    - `clinica` con su `id_usuario` (1 o 2 = Clínica Delgado, 3 = Good Hope)
    - `equipo` (equipo Donaria, revisa alertas) con id 0
    """
    if datos.rol == "donante" and datos.id == 0:
        fila = db.uno(
            "SELECT TOP (1) x.id_donante FROM dbo.NOTIFICACION x "
            "JOIN dbo.OLA_CONVOCATORIA o ON o.id_ola = x.id_ola "
            "JOIN dbo.NECESIDAD n ON n.id_necesidad = o.id_necesidad "
            "WHERE n.estado = N'Activa' ORDER BY x.fecha_envio DESC, x.id_donante"
        )
        if not fila:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Todavía nadie recibió un aviso de una necesidad activa.")
        usuario = Usuario("donante", int(fila["id_donante"]))
    elif datos.rol == "donante":
        if not db.uno("SELECT id_donante FROM dbo.DONANTE WHERE id_donante = ?", [datos.id]):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe ese donante.")
        usuario = Usuario("donante", datos.id)
    elif datos.rol == "clinica":
        fila = db.uno(
            "SELECT id_usuario, id_institucion FROM dbo.USUARIO_INSTITUCION WHERE id_usuario = ?", [datos.id]
        )
        if not fila:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe ese usuario de clínica.")
        usuario = Usuario("clinica", datos.id, int(fila["id_institucion"]))
    else:
        usuario = Usuario("equipo", 0)
    return TokenOut(token=crear_token(usuario), rol=usuario.rol, id=usuario.id, id_institucion=usuario.id_institucion)
