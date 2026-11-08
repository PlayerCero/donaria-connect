"""Tokens de demostración (JWT) con tres roles: donante, clinica y equipo.

SOLO DEMO: el token se pide indicando el rol y el id; no hay contraseña. En producción el
donante entraría con un código por WhatsApp/SMS y el personal con Microsoft Entra.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings

ROLES = ("donante", "clinica", "equipo")
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Usuario:
    rol: str
    id: int  # id_donante, id_usuario (clínica) o 0 (equipo)
    id_institucion: int | None = None

    @property
    def etiqueta(self) -> str:
        return f"{self.rol}:{self.id}"


def crear_token(usuario: Usuario) -> str:
    ahora = datetime.now(timezone.utc)
    carga = {
        "rol": usuario.rol,
        "sub": str(usuario.id),
        "inst": usuario.id_institucion,
        "iat": ahora,
        "exp": ahora + timedelta(hours=settings.jwt_horas),
    }
    return jwt.encode(carga, settings.jwt_secret, algorithm="HS256")


def usuario_actual(cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> Usuario:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Falta el token. Pídelo en /auth/token-demo.")
    try:
        carga = jwt.decode(cred.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido o vencido.") from e
    if carga.get("rol") not in ROLES:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Rol desconocido en el token.")
    return Usuario(rol=carga["rol"], id=int(carga["sub"]), id_institucion=carga.get("inst"))


def requiere(*roles: str):
    """Dependencia que deja pasar solo a los roles indicados."""

    def _verificar(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Solo para: {', '.join(roles)}.")
        return usuario

    return _verificar
