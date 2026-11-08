"""Modelos de entrada y salida (validación con Pydantic)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .distritos import DISTRITOS

TipoSangre = Literal["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]


# --- Autenticación (demo) ---
class TokenDemoIn(BaseModel):
    rol: Literal["donante", "clinica", "equipo"]
    id: int = Field(0, ge=0, description="id_donante para donante, id_usuario para clínica; 0 para equipo")


class TokenOut(BaseModel):
    token: str
    rol: str
    id: int
    id_institucion: int | None = None


# --- Donantes ---
class RegistroDonanteIn(BaseModel):
    dni: str = Field(..., description="8 dígitos. Solo se guarda su hash y los 4 últimos dígitos.")
    nombres: str = Field(..., min_length=3, max_length=120)
    sexo: Literal["F", "M"]
    tipo_sangre: TipoSangre
    distrito: str
    telefono_whatsapp: str = Field(..., description="Celular peruano de 9 dígitos que empieza con 9")
    acepta_consentimiento: bool

    @field_validator("dni")
    @classmethod
    def _dni(cls, v: str) -> str:
        v = v.strip()
        if len(v) != 8 or not v.isdigit():
            raise ValueError("El DNI debe tener 8 dígitos.")
        return v

    @field_validator("telefono_whatsapp")
    @classmethod
    def _telefono(cls, v: str) -> str:
        v = v.replace(" ", "")
        if len(v) != 9 or not v.isdigit() or not v.startswith("9"):
            raise ValueError("El celular debe tener 9 dígitos y empezar con 9.")
        return v

    @field_validator("distrito")
    @classmethod
    def _distrito(cls, v: str) -> str:
        if v not in DISTRITOS:
            raise ValueError(f"Distrito no disponible en la demo. Opciones: {', '.join(DISTRITOS)}.")
        return v

    @field_validator("acepta_consentimiento")
    @classmethod
    def _consentimiento(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Sin consentimiento no se puede registrar al donante.")
        return v


class RegistroDonanteOut(BaseModel):
    id_donante: int
    estado_verificacion: str
    token: str


class DonacionOut(BaseModel):
    fecha: date
    institucion: str
    fuente: str


class PerfilDonanteOut(BaseModel):
    id_donante: int
    nombres: str
    dni: str
    sexo: str
    tipo_sangre: str
    distrito: str
    telefono_whatsapp: str | None = None
    estado_verificacion: str
    consentimiento_vigente: bool
    consentimiento_fecha: datetime | None = None
    ultima_donacion: date | None
    proxima_fecha_posible: date | None
    puede_donar_hoy: bool
    motivo_si_no_puede: str | None
    historial: list[DonacionOut]
    unidades_convocatorias: int = Field(
        0, description="Unidades que reunieron las convocatorias a las que respondió «voy» (cifra agregada)")


class ConvocatoriaDonanteOut(BaseModel):
    """El último aviso que recibió el donante, de una necesidad todavía activa."""
    id_necesidad: int
    tipo_sangre: str
    id_institucion: int
    institucion: str
    numero_ola: int
    radio_km: int
    distancia_km: float
    fecha_envio: datetime
    respuesta: Literal["voy", "no"] | None


class RespuestaIn(BaseModel):
    respuesta: Literal["voy", "no"] | None = Field(..., description="null = borrar mi respuesta")


# --- Necesidades y olas ---
class NecesidadIn(BaseModel):
    tipo_sangre: TipoSangre
    zona: str = Field("Miraflores y alrededores", max_length=80)
    unidades_meta: int = Field(..., gt=0, le=100)


class OlaResumenOut(BaseModel):
    numero_ola: int
    radio_km: int
    donantes_notificados: int
    respondieron: int = Field(0, description="Cuántos respondieron «voy» (sin decir quiénes)")
    fecha_envio: datetime


class NecesidadOut(BaseModel):
    id_necesidad: int
    tipo_sangre: str
    zona: str
    unidades_meta: int
    estado: str
    fecha_creacion: datetime
    unidades_obtenidas: int = 0
    olas: list[OlaResumenOut] = []


class EstimadoOut(BaseModel):
    tipo_sangre: str | None
    radio_km: int
    donantes_elegibles: int


class OlaIn(BaseModel):
    numero_ola: int | None = Field(None, ge=1, le=3, description="Vacío = la siguiente ola (1 → 2 → 3)")


class OlaOut(BaseModel):
    id_necesidad: int
    tipo_sangre: str
    numero_ola: int
    radio_km: int
    donantes_notificados: int


class ResultadoIn(BaseModel):
    unidades_obtenidas: int = Field(..., ge=0, le=1000)
    cerrar: bool = False


# --- Reportes y alertas ---
class ReporteOut(BaseModel):
    id_necesidad: int
    institucion: str
    tipo_sangre: str
    zona: str
    estado: str
    fecha_creacion: datetime
    unidades_meta: int
    olas_lanzadas: int
    donantes_notificados: int
    unidades_obtenidas: int
    pct_cumplimiento: float


class InstitucionOut(BaseModel):
    id_institucion: int
    razon_social: str
    autorizacion_sanitaria: str
    estado_afiliacion: str
    latitud: float
    longitud: float


class RevisionIn(BaseModel):
    decision: Literal["falsa", "pausar", "escalar"] = "falsa"
    nota: str = Field("", max_length=300)


class AlertasResumenOut(BaseModel):
    pendientes: int
    revisadas: int


class AlertaOut(BaseModel):
    id_alerta: int
    codigo_regla: str
    codigo_donante: str
    dni: str
    regla_disparada: str
    institucion: str
    fecha: datetime
    revisar_antes_de: datetime
    estado_revision: str
