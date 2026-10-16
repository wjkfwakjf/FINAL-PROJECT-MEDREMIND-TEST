from __future__ import annotations

import os
import re
import sqlite3
from collections.abc import Iterator, Mapping
from typing import Any, Optional, Union
from urllib.parse import unquote, urlparse

import mysql.connector
from mysql.connector import Error as MySQLError
from mysql.connector import IntegrityError as MySQLIntegrityError

DatabasePath = Union[str, os.PathLike[str]]


class _MySQLRow(Mapping[str, Any]):
    def __init__(self, values: dict[str, Any]) -> None:
        self._values = values
        self._columns = tuple(values)

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, int):
            key = self._columns[key]
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._columns)

    def __len__(self) -> int:
        return len(self._columns)


class _MySQLCursor:
    def __init__(self, cursor) -> None:
        self._cursor = cursor
        self.rowcount = cursor.rowcount
        self.lastrowid = cursor.lastrowid

    def fetchone(self) -> Optional[_MySQLRow]:
        row = self._cursor.fetchone()
        return _MySQLRow(row) if row is not None else None

    def fetchall(self) -> list[_MySQLRow]:
        return [_MySQLRow(row) for row in self._cursor.fetchall()]


class _MySQLConnection:
    row_factory = None

    def __init__(self, connection) -> None:
        self._connection = connection

    def execute(self, statement: str, parameters=()) -> _MySQLCursor:
        if statement.strip().upper() == "BEGIN IMMEDIATE":
            self._connection.start_transaction()
            return _MySQLCursor(self._connection.cursor(dictionary=True))
        statement = re.sub(r"\bcondition\b", "`condition`", statement, flags=re.IGNORECASE)
        statement = re.sub(r"\?", "%s", statement)
        cursor = self._connection.cursor(dictionary=True)
        try:
            cursor.execute(statement, parameters)
        except MySQLIntegrityError as exc:
            cursor.close()
            raise sqlite3.IntegrityError(str(exc)) from exc
        except MySQLError as exc:
            cursor.close()
            raise sqlite3.OperationalError(str(exc)) from exc
        return _MySQLCursor(cursor)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


def _mysql_settings() -> Optional[dict[str, Any]]:
    database_url = (
        os.environ.get("MEDREMIND_DATABASE_URL")
        or os.environ.get("MYSQL_URL")
        or os.environ.get("MYSQL_PUBLIC_URL")
    )
    if database_url:
        parsed = urlparse(database_url)
        if parsed.scheme not in {"mysql", "mysql+mysqlconnector"}:
            raise ValueError("MEDREMIND_DATABASE_URL must be a MySQL connection URL.")
        settings: dict[str, Any] = {
            "host": parsed.hostname,
            "port": parsed.port or 3306,
            "user": unquote(parsed.username or ""),
            "password": unquote(parsed.password or ""),
            "database": unquote(parsed.path.lstrip("/")),
        }
        if not all((settings["host"], settings["user"], settings["database"])):
            raise ValueError("The MySQL connection URL is missing host, user, or database.")
        return settings

    railway_variables = {
        name: os.environ.get(name)
        for name in ("MYSQLHOST", "MYSQLPORT", "MYSQLUSER", "MYSQLPASSWORD", "MYSQLDATABASE")
    }
    if any(value is not None for value in railway_variables.values()):
        host = railway_variables["MYSQLHOST"]
        settings = {
            "host": host,
            "port": int(railway_variables["MYSQLPORT"] or "3306"),
            "user": railway_variables["MYSQLUSER"] or "",
            "password": railway_variables["MYSQLPASSWORD"] or "",
            "database": railway_variables["MYSQLDATABASE"] or "",
        }
        if not all((settings["host"], settings["user"], settings["database"])):
            raise ValueError(
                "Railway MySQL variables must include MYSQLHOST, MYSQLUSER, and MYSQLDATABASE."
            )
        return settings
    return None


def is_mysql(db_path: Optional[DatabasePath] = None) -> bool:
    if db_path is not None:
        value = os.fspath(db_path)
        return value.startswith(("mysql://", "mysql+mysqlconnector://"))
    return _mysql_settings() is not None


def connect_db(db_path: Optional[DatabasePath] = None):
    """Connect to configured MySQL or the local SQLite database."""
    if db_path is None:
        settings = _mysql_settings()
    else:
        value = os.fspath(db_path)
        settings = None
        if value.startswith(("mysql://", "mysql+mysqlconnector://")):
            parsed = urlparse(value)
            settings = {
                "host": parsed.hostname,
                "port": parsed.port or 3306,
                "user": unquote(parsed.username or ""),
                "password": unquote(parsed.password or ""),
                "database": unquote(parsed.path.lstrip("/")),
            }
    if settings is not None:
        try:
            connection = mysql.connector.connect(**settings)
        except MySQLError as exc:
            raise sqlite3.OperationalError(f"Could not connect to configured MySQL database: {exc}") from exc
        return _MySQLConnection(connection)

    path = os.fspath(db_path) if db_path is not None else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "medremind.db"
    )
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_mysql_schema(db_path: Optional[DatabasePath] = None) -> None:
    if not is_mysql(db_path):
        return
    connection = connect_db(db_path)
    try:
        statements = (
            """
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(60) PRIMARY KEY,
                full_name VARCHAR(120) NOT NULL,
                password_salt CHAR(32) NOT NULL,
                password_hash CHAR(64) NOT NULL,
                role VARCHAR(32) NOT NULL DEFAULT 'Caregiver',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
            """,
            """
            CREATE TABLE IF NOT EXISTS consultations (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                client_username VARCHAR(60) NOT NULL,
                medicine_name VARCHAR(255) NOT NULL,
                question TEXT NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'Pending',
                admin_reply TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
            """,
        )
        for statement in statements:
            connection.execute(statement)
        consultation_columns = {
            row["COLUMN_NAME"]
            for row in connection.execute(
                """
                SELECT COLUMN_NAME
                FROM information_schema.columns
                WHERE table_schema = DATABASE() AND table_name = 'consultations'
                """
            ).fetchall()
        }
        if "admin_reply" not in consultation_columns:
            connection.execute(
                "ALTER TABLE consultations ADD COLUMN admin_reply TEXT"
            )
        connection.commit()
    finally:
        connection.close()


def test_connection(db_path: Optional[DatabasePath] = None) -> list[tuple[str]]:
    connection = connect_db(db_path)
    try:
        if is_mysql(db_path):
            rows = connection.execute(
                """
                SELECT table_name AS name
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                ORDER BY table_name
                """
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            ).fetchall()
        return [(row["name"],) for row in rows]
    finally:
        connection.close()


if __name__ == "__main__":
    print("Connected to MedRemind Care database successfully.")
    print(test_connection())
