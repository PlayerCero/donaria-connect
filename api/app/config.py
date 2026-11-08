"""Configuración leída de variables de entorno (archivo .env en la raíz del repo o en api/)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

# Busca .env en api/ y en la raíz del repositorio.
_AQUI = Path(__file__).resolve().parent
for candidato in (_AQUI.parent / ".env", _AQUI.parent.parent / ".env"):
    if candidato.exists():
        load_dotenv(candidato)
        break


def _lista(valor: str) -> list[str]:
    return [v.strip() for v in valor.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    # Base de datos
    db_connection_string: str = field(default_factory=lambda: os.getenv("DB_CONNECTION_STRING", ""))
    db_server: str = field(default_factory=lambda: os.getenv("DB_SERVER", "localhost"))
    db_name: str = field(default_factory=lambda: os.getenv("DB_NAME", "DonariaConnect"))
    # windows | entra-interactive | entra-msi | sql
    db_auth: str = field(default_factory=lambda: os.getenv("DB_AUTH", "windows").lower())
    db_user: str = field(default_factory=lambda: os.getenv("DB_USER", ""))
    db_password: str = field(default_factory=lambda: os.getenv("DB_PASSWORD", ""))
    db_driver: str = field(default_factory=lambda: os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server"))

    # Seguridad (token de demostración)
    # El valor por defecto es público (está en el repo): en .env poner una clave propia de 32+ caracteres.
    jwt_secret: str = field(
        default_factory=lambda: os.getenv("JWT_SECRET", "solo-demo-cambia-esta-clave-en-tu-archivo-env")
    )
    jwt_horas: int = field(default_factory=lambda: int(os.getenv("JWT_HORAS", "8")))

    # Fecha "de hoy" para elegibilidad. Vacío = fecha real del servidor.
    # Los datos ficticios están pensados para 2026-11-09.
    fecha_referencia: str = field(default_factory=lambda: os.getenv("FECHA_REFERENCIA", ""))

    # Didit (verificación de identidad). Vacío = la verificación queda simulada en la web.
    didit_api_key: str = field(default_factory=lambda: os.getenv("DIDIT_API_KEY", ""))
    didit_workflow_id: str = field(default_factory=lambda: os.getenv("DIDIT_WORKFLOW_ID", ""))
    didit_webhook_secret: str = field(default_factory=lambda: os.getenv("DIDIT_WEBHOOK_SECRET", ""))
    didit_base_url: str = field(default_factory=lambda: os.getenv("DIDIT_BASE_URL", "https://verification.didit.me"))

    # WhatsApp Cloud API (fase 5). Solo se envía a los números de prueba registrados en Meta.
    whatsapp_token: str = field(default_factory=lambda: os.getenv("WHATSAPP_TOKEN", ""))
    whatsapp_phone_number_id: str = field(default_factory=lambda: os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""))
    whatsapp_numeros_prueba: list[str] = field(default_factory=lambda: _lista(os.getenv("WHATSAPP_NUMEROS_PRUEBA", "")))
    whatsapp_plantilla: str = field(default_factory=lambda: os.getenv("WHATSAPP_PLANTILLA", "convocatoria_donacion"))
    whatsapp_idioma: str = field(default_factory=lambda: os.getenv("WHATSAPP_IDIOMA", "es"))
    whatsapp_version: str = field(default_factory=lambda: os.getenv("WHATSAPP_VERSION", "v25.0"))

    cors_origins: list[str] = field(default_factory=lambda: _lista(os.getenv("CORS_ORIGINS", "*")))

    def hoy(self) -> date:
        if self.fecha_referencia:
            return date.fromisoformat(self.fecha_referencia)
        return date.today()


settings = Settings()
