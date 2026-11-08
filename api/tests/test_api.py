"""Pruebas de la API con una base simulada (no necesitan SQL Server).

Comprueban validación, roles, manejo de errores de la base y que las consultas sensibles
usen el hash del DNI. La prueba contra la base real es scripts/smoke_test.py.
"""
from __future__ import annotations

import re
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from app.db import ErrorDeNegocio, get_db
from app.main import app
from app.security import Usuario, crear_token


class BaseSimulada:
    """Responde según la primera regla cuyo patrón coincide con el SQL. Guarda cada llamada."""

    def __init__(self):
        self.reglas: list[tuple[str, object]] = []
        self.llamadas: list[tuple[str, list]] = []

    def responder(self, patron: str, respuesta):
        self.reglas.append((patron, respuesta))

    def _buscar(self, sql: str, params):
        self.llamadas.append((sql, list(params)))
        for patron, respuesta in self.reglas:
            if re.search(patron, sql, re.S):
                if isinstance(respuesta, Exception):
                    raise respuesta
                return respuesta(params) if callable(respuesta) else respuesta
        return []

    def consultar(self, sql, params=()):
        r = self._buscar(sql, params)
        return r if isinstance(r, list) else [r]

    def uno(self, sql, params=()):
        filas = self.consultar(sql, params)
        return filas[0] if filas else None

    def ejecutar(self, sql, params=()):
        r = self._buscar(sql, params)
        return r if isinstance(r, int) else 1

    def transaccion(self, pasos):
        return [self.consultar(sql, p) for sql, p in pasos]


@pytest.fixture
def db():
    base = BaseSimulada()
    app.dependency_overrides[get_db] = lambda: base
    yield base
    app.dependency_overrides.clear()


@pytest.fixture
def client(db):
    return TestClient(app)


def token(rol, id_=0, inst=None):
    return {"Authorization": f"Bearer {crear_token(Usuario(rol, id_, inst))}"}


REGISTRO = {
    "dni": "12345678", "nombres": "Prueba Ficticia", "sexo": "F", "tipo_sangre": "O-",
    "distrito": "Miraflores", "telefono_whatsapp": "987654321", "acepta_consentimiento": True,
}


# --- estado ---
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["estado"] == "ok"


# --- registro ---
def test_registro_valida_dni(client):
    r = client.post("/donantes", json={**REGISTRO, "dni": "1234567"})
    assert r.status_code == 422


def test_registro_exige_consentimiento(client):
    r = client.post("/donantes", json={**REGISTRO, "acepta_consentimiento": False})
    assert r.status_code == 422


def test_registro_rechaza_distrito_fuera_de_la_demo(client):
    r = client.post("/donantes", json={**REGISTRO, "distrito": "Arequipa"})
    assert r.status_code == 422


def test_registro_ok_devuelve_token_y_usa_hash(client, db):
    db.responder(r"SELECT id_donante FROM dbo.DONANTE WHERE dni_hash", [])
    db.responder(r"INSERT INTO dbo.DONANTE", [{"id_donante": 501}])
    r = client.post("/donantes", json=REGISTRO)
    assert r.status_code == 201, r.text
    assert r.json()["id_donante"] == 501 and r.json()["token"]
    sql_insert, params = [c for c in db.llamadas if "INSERT INTO dbo.DONANTE" in c[0]][0]
    assert "CAST(? AS VARCHAR(8))" in sql_insert  # mismo hash que el script SQL
    assert params[1] == "5678"  # solo se guardan los 4 últimos dígitos en claro
    assert "12345678" == params[0]  # el DNI completo solo entra a HASHBYTES


def test_registro_dni_duplicado_crea_alerta_r4(client, db):
    db.responder(r"SELECT id_donante FROM dbo.DONANTE WHERE dni_hash", [{"id_donante": 1}])
    r = client.post("/donantes", json=REGISTRO)
    assert r.status_code == 409
    assert any("'R4'" in sql and p == [1] for sql, p in db.llamadas)


# --- autenticación y roles ---
def test_sin_token_401(client):
    assert client.get("/donantes/me").status_code == 401


def test_token_invalido_401(client):
    r = client.get("/donantes/me", headers={"Authorization": "Bearer basura"})
    assert r.status_code == 401


def test_donante_no_puede_crear_necesidad(client):
    r = client.post("/necesidades", json={"tipo_sangre": "A+", "unidades_meta": 3}, headers=token("donante", 48))
    assert r.status_code == 403


def test_clinica_no_ve_alertas(client):
    assert client.get("/alertas", headers=token("clinica", 1, 1)).status_code == 403


def test_token_demo_clinica_incluye_institucion(client, db):
    db.responder(r"FROM dbo.USUARIO_INSTITUCION", [{"id_usuario": 1, "id_institucion": 1}])
    r = client.post("/auth/token-demo", json={"rol": "clinica", "id": 1})
    assert r.status_code == 200 and r.json()["id_institucion"] == 1


def test_token_demo_donante_inexistente(client, db):
    db.responder(r"FROM dbo.DONANTE WHERE id_donante", [])
    assert client.post("/auth/token-demo", json={"rol": "donante", "id": 9999}).status_code == 404


# --- perfil del donante ---
def test_perfil_calcula_proxima_fecha_y_motivo(client, db, monkeypatch):
    from app import config
    monkeypatch.setattr(config.settings.__class__, "hoy", lambda self: date(2026, 11, 9))
    db.responder(r"OUTER APPLY", [{
        "id_donante": 48, "nombres": "Ana Ficticia", "dni_ult4": "0637", "sexo": "F", "tipo_sangre": "O+",
        "distrito": "Lince", "estado_verificacion": "verificado", "consentimiento_vigente": True,
        "alerta_pendiente": False, "elegible": False, "ultima": date(2026, 10, 1),
    }])
    db.responder(r"FROM dbo.DONACION_CONFIRMADA dc\s+JOIN", [
        {"fecha": date(2026, 10, 1), "institucion": "Clínica Delgado Auna", "fuente": "institucion"}])
    r = client.get("/donantes/me", headers=token("donante", 48))
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["dni"] == "****0637"
    assert cuerpo["proxima_fecha_posible"] == "2027-01-29"  # 120 días (mujer)
    assert cuerpo["puede_donar_hoy"] is False
    assert "29/01/2027" in cuerpo["motivo_si_no_puede"]


# --- olas ---
def _necesidad(db):
    db.responder(r"FROM dbo.NECESIDAD WHERE id_necesidad = \? AND id_institucion", [{
        "id_necesidad": 30, "tipo_sangre": "A+", "zona": "Miraflores", "unidades_meta": 8,
        "estado": "Activa", "fecha_creacion": datetime(2026, 11, 8, 16, 40)}])


def test_lanzar_siguiente_ola(client, db):
    _necesidad(db)
    db.responder(r"MAX\(numero_ola\)", [{"siguiente": 2}])
    db.responder(r"EXEC dbo.sp_lanzar_ola", [{"radio_km": 6, "donantes_notificados_en_esta_ola": 34}])
    r = client.post("/necesidades/30/olas", headers=token("clinica", 1, 1))
    assert r.status_code == 200, r.text
    assert r.json() == {"id_necesidad": 30, "tipo_sangre": "A+", "numero_ola": 2, "radio_km": 6,
                        "donantes_notificados": 34}


def test_ola_repetida_409(client, db):
    _necesidad(db)
    db.responder(r"EXEC dbo.sp_lanzar_ola", ErrorDeNegocio(50002, "Esa ola ya fue lanzada para esta necesidad."))
    r = client.post("/necesidades/30/olas", json={"numero_ola": 1}, headers=token("clinica", 1, 1))
    assert r.status_code == 409 and "ya fue lanzada" in r.json()["detail"]


def test_no_hay_cuarta_ola(client, db):
    _necesidad(db)
    db.responder(r"MAX\(numero_ola\)", [{"siguiente": 4}])
    assert client.post("/necesidades/30/olas", headers=token("clinica", 1, 1)).status_code == 409


def test_necesidad_de_otra_clinica_404(client, db):
    db.responder(r"FROM dbo.NECESIDAD WHERE id_necesidad = \? AND id_institucion", [])
    assert client.post("/necesidades/30/olas", headers=token("clinica", 3, 2)).status_code == 404


# --- reporte ---
def test_reporte_de_la_clinica_filtra_por_institucion(client, db):
    db.responder(r"vw_reporte_institucion", [])
    client.get("/reportes", headers=token("clinica", 1, 1))
    sql, params = db.llamadas[-1]
    assert "n.id_institucion = ?" in sql and params == [1]


# --- traducción de errores de la base ---
def test_traduce_throw_de_sql_server():
    from app.db import _traducir
    texto = ("('42000', '[42000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]"
             "Esa ola ya fue lanzada para esta necesidad. (50002) (SQLExecDirectW)')")
    e = _traducir(Exception(texto))
    assert isinstance(e, ErrorDeNegocio) and e.codigo == 50002 and e.mensaje.startswith("Esa ola")


# --- fase 3: lo que necesitan las pantallas de la web ---
def test_health_trae_ahora_con_fecha_de_referencia(client):
    cuerpo = client.get("/health").json()
    assert cuerpo["ahora"].startswith(cuerpo["fecha_referencia"])


def test_necesidades_incluyen_olas_y_unidades(client, db):
    db.responder(r"LEFT JOIN dbo.RESULTADO_AGREGADO", [
        {"id_necesidad": 31, "tipo_sangre": "O-", "zona": "Miraflores", "unidades_meta": 6, "estado": "Activa",
         "fecha_creacion": datetime(2026, 11, 9, 8, 10), "unidades_obtenidas": 2},
        {"id_necesidad": 27, "tipo_sangre": "AB+", "zona": "Miraflores", "unidades_meta": 2, "estado": "Cerrada",
         "fecha_creacion": datetime(2026, 10, 3, 13, 20), "unidades_obtenidas": 2}])
    db.responder(r"FROM dbo.OLA_CONVOCATORIA o", [
        {"id_necesidad": 31, "numero_ola": 1, "radio_km": 3, "donantes_notificados": 5, "respondieron": 1,
         "fecha_envio": datetime(2026, 11, 9, 8, 12)},
        {"id_necesidad": 31, "numero_ola": 2, "radio_km": 6, "donantes_notificados": 9, "respondieron": 0,
         "fecha_envio": datetime(2026, 11, 9, 10, 15)}])
    r = client.get("/necesidades", headers=token("clinica", 1, 1))
    assert r.status_code == 200, r.text
    n31, n27 = r.json()
    assert [o["radio_km"] for o in n31["olas"]] == [3, 6] and n31["unidades_obtenidas"] == 2
    assert n27["olas"] == []
    # Las consultas filtran por la institución del token y no tocan datos de donantes
    for sql, params in db.llamadas:
        assert params == [1] and "nombres" not in sql and "dni" not in sql


def test_estimado_filtra_por_tipo_y_radio(client, db):
    db.responder(r"fn_donantes_elegibles", [{"n": 17}])
    r = client.get("/necesidades/estimado?radio_km=6&tipo_sangre=O-", headers=token("clinica", 1, 1))
    assert r.json() == {"tipo_sangre": "O-", "radio_km": 6, "donantes_elegibles": 17}
    sql, params = db.llamadas[-1]
    assert "e.tipo_sangre = ?" in sql and params[1:] == [1, 6, "O-"]


def test_convocatoria_del_donante_vacia_devuelve_null(client, db):
    db.responder(r"WHERE x.id_donante = \? AND n.estado", [])
    r = client.get("/donantes/me/convocatoria", headers=token("donante", 48))
    assert r.status_code == 200 and r.json() is None


def test_responder_aviso_guarda_respuesta(client, db):
    db.responder(r"SELECT TOP \(1\) x.id_notificacion", [{"id_notificacion": 900, "estado": "Activa"}])
    r = client.put("/donantes/me/convocatorias/31/respuesta", json={"respuesta": "voy"}, headers=token("donante", 48))
    assert r.status_code == 204
    sql, params = db.llamadas[-1]
    assert "MERGE dbo.RESPUESTA_CONVOCATORIA" in sql and params == [900, "voy"]


def test_responder_aviso_ajeno_404_y_cerrado_409(client, db):
    db.responder(r"SELECT TOP \(1\) x.id_notificacion", [])
    h = token("donante", 48)
    assert client.put("/donantes/me/convocatorias/31/respuesta", json={"respuesta": "no"}, headers=h).status_code == 404
    db.reglas.clear()
    db.responder(r"SELECT TOP \(1\) x.id_notificacion", [{"id_notificacion": 900, "estado": "Cerrada"}])
    assert client.put("/donantes/me/convocatorias/31/respuesta", json={"respuesta": "no"}, headers=h).status_code == 409


def test_token_demo_donante_0_elige_un_notificado(client, db):
    db.responder(r"ORDER BY x.fecha_envio DESC, x.id_donante", [{"id_donante": 233}])
    r = client.post("/auth/token-demo", json={"rol": "donante", "id": 0})
    assert r.status_code == 200 and r.json()["id"] == 233


def test_revisar_alerta_guarda_decision_en_auditoria(client, db):
    r = client.patch("/alertas/7/revisar", json={"decision": "escalar", "nota": "Pedí el registro"},
                     headers=token("equipo"))
    assert r.status_code == 204
    sql, params = db.llamadas[-1]
    assert "AUDITORIA" in sql and "institución" in params[1] and "Pedí el registro" in params[1]


def test_instituciones_para_el_equipo(client, db):
    db.responder(r"FROM dbo.INSTITUCION", [{"id_institucion": 1, "razon_social": "Clínica Delgado Auna",
                                            "autorizacion_sanitaria": "Vigente", "estado_afiliacion": "Piloto",
                                            "latitud": -12.1197, "longitud": -77.0386}])
    r = client.get("/instituciones", headers=token("equipo"))
    assert r.status_code == 200 and r.json()[0]["estado_afiliacion"] == "Piloto"
