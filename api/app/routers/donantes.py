from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..config import settings
from ..db import Database, get_db
from ..distritos import DISTRITOS
from ..schemas import DonacionOut, PerfilDonanteOut, RegistroDonanteIn, RegistroDonanteOut
from ..security import Usuario, crear_token, requiere

router = APIRouter(prefix="/donantes", tags=["donantes"])

# El hash se calcula igual que en db/01_crear_y_cargar.sql: SHA-256 de 'donaria-2026|' + DNI en VARCHAR.
# Ojo: sin el CAST a VARCHAR, pyodbc enviaría NVARCHAR y el hash saldría distinto.
_HASH_DNI = "HASHBYTES('SHA2_256', 'donaria-2026|' + CAST(? AS VARCHAR(8)))"

_SQL_REGISTRO = f"""
SET NOCOUNT ON;
DECLARE @id INT;
INSERT INTO dbo.DONANTE (dni_hash, dni_ult4, nombres, sexo, tipo_sangre, distrito, ubicacion,
                         telefono_whatsapp, estado_verificacion)
VALUES ({_HASH_DNI}, ?, ?, ?, ?, ?, geography::Point(?, ?, 4326), ?, 'pendiente');
SET @id = SCOPE_IDENTITY();
INSERT INTO dbo.CONSENTIMIENTO (id_donante, version_texto, fecha_hora, ip_origen, vigente)
VALUES (@id, '1.0', SYSDATETIME(), ?, 1);
INSERT INTO dbo.AUDITORIA (usuario, accion, tabla_afectada, fecha_hora)
VALUES (N'api', CONCAT(N'Registro del donante ', @id), N'DONANTE', SYSDATETIME());
SELECT @id AS id_donante;
"""

_SQL_PERFIL = """
SELECT d.id_donante, d.nombres, d.dni_ult4, d.sexo, d.tipo_sangre, d.distrito, d.estado_verificacion,
       CAST(CASE WHEN EXISTS (SELECT 1 FROM dbo.CONSENTIMIENTO c
                              WHERE c.id_donante = d.id_donante AND c.vigente = 1) THEN 1 ELSE 0 END AS BIT) AS consentimiento_vigente,
       CAST(CASE WHEN EXISTS (SELECT 1 FROM dbo.ALERTA_ANTIFRAUDE a
                              WHERE a.id_donante = d.id_donante AND a.estado_revision = N'Pendiente') THEN 1 ELSE 0 END AS BIT) AS alerta_pendiente,
       CAST(CASE WHEN EXISTS (SELECT 1 FROM dbo.fn_donantes_elegibles(?) e
                              WHERE e.id_donante = d.id_donante) THEN 1 ELSE 0 END AS BIT) AS elegible,
       u.ultima
FROM dbo.DONANTE d
OUTER APPLY (SELECT MAX(dc.fecha) AS ultima FROM dbo.DONACION_CONFIRMADA dc
             WHERE dc.id_donante = d.id_donante AND dc.fecha < ?) u
WHERE d.id_donante = ?;
"""

_SQL_HISTORIAL = """
SELECT dc.fecha, i.razon_social AS institucion, dc.fuente
FROM dbo.DONACION_CONFIRMADA dc
JOIN dbo.INSTITUCION i ON i.id_institucion = dc.id_institucion
WHERE dc.id_donante = ?
ORDER BY dc.fecha DESC;
"""


def _motivo(p: dict, hoy, proxima) -> str | None:
    if p["elegible"]:
        return None
    if p["estado_verificacion"] != "verificado":
        return "Falta verificar tu identidad."
    if not p["consentimiento_vigente"]:
        return "Revocaste tu consentimiento."
    if p["alerta_pendiente"]:
        return "Tu cuenta está en revisión."
    if proxima and proxima > hoy:
        return f"Podrás volver a donar desde el {proxima:%d/%m/%Y}."
    return "Por ahora no puedes recibir convocatorias."


@router.post("", response_model=RegistroDonanteOut, status_code=status.HTTP_201_CREATED,
             summary="Registrar un donante")
def registrar(datos: RegistroDonanteIn, request: Request, db: Database = Depends(get_db)) -> RegistroDonanteOut:
    existente = db.uno(f"SELECT id_donante FROM dbo.DONANTE WHERE dni_hash = {_HASH_DNI}", [datos.dni])
    if existente:
        # Regla R4: intento de registro con un DNI que ya existe.
        db.ejecutar(
            "INSERT INTO dbo.ALERTA_ANTIFRAUDE (id_donante, id_institucion, codigo_regla, regla_disparada, fecha, estado_revision) "
            "VALUES (?, NULL, 'R4', N'Intento de registro con un DNI ya registrado', SYSDATETIME(), N'Pendiente')",
            [existente["id_donante"]],
        )
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese DNI ya está registrado.")

    lat, lon = DISTRITOS[datos.distrito]
    ip = request.client.host if request.client else "desconocida"
    resultado = db.transaccion([(
        _SQL_REGISTRO,
        [datos.dni, datos.dni[-4:], datos.nombres, datos.sexo, datos.tipo_sangre, datos.distrito,
         lat, lon, datos.telefono_whatsapp, ip[:45]],
    )])
    id_donante = int(resultado[0][0]["id_donante"])
    token = crear_token(Usuario("donante", id_donante))
    return RegistroDonanteOut(id_donante=id_donante, estado_verificacion="pendiente", token=token)


@router.get("/me", response_model=PerfilDonanteOut, summary="Mi perfil y si puedo donar hoy")
def mi_perfil(usuario: Usuario = Depends(requiere("donante")), db: Database = Depends(get_db)) -> PerfilDonanteOut:
    hoy = settings.hoy()
    p = db.uno(_SQL_PERFIL, [hoy, hoy, usuario.id])
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe ese donante.")
    ultima = p["ultima"]
    proxima = ultima + timedelta(days=90 if p["sexo"] == "M" else 120) if ultima else None
    historial = [DonacionOut(**h) for h in db.consultar(_SQL_HISTORIAL, [usuario.id])]
    return PerfilDonanteOut(
        id_donante=p["id_donante"],
        nombres=p["nombres"],
        dni=f"****{p['dni_ult4']}",
        sexo=p["sexo"],
        tipo_sangre=p["tipo_sangre"],
        distrito=p["distrito"],
        estado_verificacion=p["estado_verificacion"],
        consentimiento_vigente=bool(p["consentimiento_vigente"]),
        ultima_donacion=ultima,
        proxima_fecha_posible=proxima,
        puede_donar_hoy=bool(p["elegible"]),
        motivo_si_no_puede=_motivo(p, hoy, proxima),
        historial=historial,
    )


@router.post("/me/consentimiento", status_code=status.HTTP_204_NO_CONTENT, summary="Aceptar el consentimiento")
def aceptar_consentimiento(request: Request, usuario: Usuario = Depends(requiere("donante")),
                           db: Database = Depends(get_db)) -> None:
    ip = request.client.host if request.client else "desconocida"
    db.ejecutar(
        "IF NOT EXISTS (SELECT 1 FROM dbo.CONSENTIMIENTO WHERE id_donante = ? AND vigente = 1) "
        "INSERT INTO dbo.CONSENTIMIENTO (id_donante, version_texto, fecha_hora, ip_origen, vigente) "
        "VALUES (?, '1.0', SYSDATETIME(), ?, 1)",
        [usuario.id, usuario.id, ip[:45]],
    )


@router.delete("/me/consentimiento", status_code=status.HTTP_204_NO_CONTENT,
               summary="Revocar el consentimiento (deja de recibir convocatorias)")
def revocar_consentimiento(usuario: Usuario = Depends(requiere("donante")), db: Database = Depends(get_db)) -> None:
    db.ejecutar("UPDATE dbo.CONSENTIMIENTO SET vigente = 0 WHERE id_donante = ? AND vigente = 1", [usuario.id])
    db.ejecutar(
        "INSERT INTO dbo.AUDITORIA (usuario, accion, tabla_afectada, fecha_hora) "
        "VALUES (?, N'Revocó el consentimiento', N'CONSENTIMIENTO', SYSDATETIME())",
        [usuario.etiqueta],
    )
