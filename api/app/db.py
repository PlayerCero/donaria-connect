"""Acceso a SQL Server / Azure SQL con pyodbc.

Toda la lógica de negocio pesada vive en la base (fn_donantes_elegibles, sp_lanzar_ola,
reglas antifraude). La API solo valida, autoriza y llama a la base.
"""
from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

from .config import Settings, settings


class ErrorDeNegocio(Exception):
    """Error lanzado por la base con THROW 5000x (por ejemplo, 'Esa ola ya fue lanzada')."""

    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


_THROW = re.compile(r"\[SQL Server\](.*?)\s*\((5000\d)\)")


def cadena_conexion(cfg: Settings = settings) -> str:
    if cfg.db_connection_string:
        return cfg.db_connection_string
    partes = [
        f"Driver={{{cfg.db_driver}}}",
        f"Server={cfg.db_server}",
        f"Database={cfg.db_name}",
        "Encrypt=yes",
    ]
    if cfg.db_auth == "windows":
        partes += ["Trusted_Connection=yes", "TrustServerCertificate=yes"]
    elif cfg.db_auth in ("entra-interactive", "entra-msi"):
        # Con Microsoft Entra no va usuario en la cadena: la API pide un token con azure-identity
        # y lo entrega al driver (ver _token_entra). Es más confiable que Authentication=... del driver.
        pass
    elif cfg.db_auth == "sql":
        partes += [f"UID={cfg.db_user}", f"PWD={cfg.db_password}"]
    else:
        raise ValueError(f"DB_AUTH no reconocido: {cfg.db_auth}")
    return ";".join(partes) + ";"


_SQL_COPT_SS_ACCESS_TOKEN = 1256  # atributo del driver ODBC para entregar un token de Entra
_ALCANCE_AZURE_SQL = "https://database.windows.net/.default"


def _credencial_entra(cfg: Settings = settings):
    """Credencial de Microsoft Entra. Se crea una vez y guarda el token en memoria (se renueva solo)."""
    if cfg.db_auth == "entra-msi":
        from azure.identity import ManagedIdentityCredential

        return ManagedIdentityCredential()
    from azure.identity import InteractiveBrowserCredential

    # Abre el navegador la primera vez para iniciar sesión con la cuenta indicada en DB_USER.
    return InteractiveBrowserCredential(login_hint=cfg.db_user or None)


def _token_entra(credencial) -> bytes:
    """Empaqueta el token como lo pide el driver: largo (4 bytes) + token en UTF-16-LE."""
    import struct

    token = credencial.get_token(_ALCANCE_AZURE_SQL).token.encode("utf-16-le")
    return struct.pack(f"<I{len(token)}s", len(token), token)


def _a_dict(cursor) -> list[dict[str, Any]]:
    columnas = [c[0] for c in cursor.description]
    return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


def _traducir(error: Exception) -> Exception:
    texto = str(error)
    # pyodbc devuelve, por ejemplo:
    # "[42000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]Esa ola ya fue lanzada... (50002) (SQLExecDirectW)"
    m = _THROW.search(texto)
    if m:
        return ErrorDeNegocio(int(m.group(2)), m.group(1).strip())
    return error


class Database:
    """Envoltorio mínimo sobre pyodbc. Las pruebas lo reemplazan por una base simulada."""

    def __init__(self, conexion_str: str | None = None, cfg: Settings = settings):
        self._conexion_str = conexion_str or cadena_conexion(cfg)
        self._usa_entra = not conexion_str and cfg.db_auth in ("entra-interactive", "entra-msi")
        self._credencial = _credencial_entra(cfg) if self._usa_entra else None

    @contextmanager
    def _conexion(self, autocommit: bool = True) -> Iterator[Any]:
        import pyodbc  # import diferido: las pruebas no necesitan el driver ODBC

        extra = {}
        if self._usa_entra:
            extra["attrs_before"] = {_SQL_COPT_SS_ACCESS_TOKEN: _token_entra(self._credencial)}
        # timeout = segundos de espera al conectar; la base sin servidor de Azure tarda en "despertar".
        conn = pyodbc.connect(self._conexion_str, autocommit=autocommit, timeout=90, **extra)
        try:
            yield conn
        finally:
            conn.close()

    def consultar(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        try:
            with self._conexion() as conn:
                cur = conn.cursor()
                cur.execute(sql, *params)
                return _a_dict(cur) if cur.description else []
        except Exception as e:  # noqa: BLE001
            raise _traducir(e) from e

    def uno(self, sql: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
        filas = self.consultar(sql, params)
        return filas[0] if filas else None

    def ejecutar(self, sql: str, params: Sequence[Any] = ()) -> int:
        try:
            with self._conexion() as conn:
                cur = conn.cursor()
                cur.execute(sql, *params)
                return cur.rowcount
        except Exception as e:  # noqa: BLE001
            raise _traducir(e) from e

    def transaccion(self, pasos: Sequence[tuple[str, Sequence[Any]]]) -> list[list[dict[str, Any]]]:
        """Ejecuta varias sentencias en una sola transacción (todo o nada)."""
        try:
            with self._conexion(autocommit=False) as conn:
                cur = conn.cursor()
                resultados: list[list[dict[str, Any]]] = []
                try:
                    for sql, params in pasos:
                        cur.execute(sql, *params)
                        resultados.append(_a_dict(cur) if cur.description else [])
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
                return resultados
        except Exception as e:  # noqa: BLE001
            raise _traducir(e) from e


_db: Database | None = None


def get_db() -> Database:
    """Dependencia de FastAPI. Se crea una sola vez por proceso."""
    global _db
    if _db is None:
        _db = Database()
    return _db
