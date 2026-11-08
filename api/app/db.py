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
    elif cfg.db_auth == "entra-interactive":
        # Abre la ventana de inicio de sesión de Microsoft la primera vez.
        partes += ["Authentication=ActiveDirectoryInteractive", f"UID={cfg.db_user}"]
    elif cfg.db_auth == "entra-msi":
        # Identidad administrada (cuando la API corra en Azure App Service).
        partes += ["Authentication=ActiveDirectoryMsi"]
    elif cfg.db_auth == "sql":
        partes += [f"UID={cfg.db_user}", f"PWD={cfg.db_password}"]
    else:
        raise ValueError(f"DB_AUTH no reconocido: {cfg.db_auth}")
    partes.append("Connection Timeout=90")
    return ";".join(partes) + ";"


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

    def __init__(self, conexion_str: str | None = None):
        self._conexion_str = conexion_str or cadena_conexion()

    @contextmanager
    def _conexion(self, autocommit: bool = True) -> Iterator[Any]:
        import pyodbc  # import diferido: las pruebas no necesitan el driver ODBC

        conn = pyodbc.connect(self._conexion_str, autocommit=autocommit)
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
