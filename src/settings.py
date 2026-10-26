import os
from dataclasses import dataclass

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"A variável de ambiente {name} é obrigatória.")
    return value


def _env_port(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"A variável de ambiente {name} deve ser uma porta válida.") from exc


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise ValueError(f"A variável de ambiente {name} deve ser booleana.")


@dataclass(frozen=True)
class SQLServerConfig:
    host: str
    database: str
    username: str
    password: str
    port: int = 1433
    driver: str = "ODBC Driver 18 for SQL Server"
    trust_server_certificate: bool = False

    @classmethod
    def from_env(cls) -> "SQLServerConfig":
        return cls(
            host=_required_env("SQLSERVER_HOST"),
            database=_required_env("SQLSERVER_DATABASE"),
            username=_required_env("SQLSERVER_USER"),
            password=_required_env("SQLSERVER_PASSWORD"),
            port=_env_port("SQLSERVER_PORT", 1433),
            driver=os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server"),
            trust_server_certificate=_env_bool("SQLSERVER_TRUST_SERVER_CERTIFICATE"),
        )

    def sqlalchemy_url(self) -> URL:
        query = {"driver": self.driver}
        if self.trust_server_certificate:
            query["TrustServerCertificate"] = "yes"

        return URL.create(
            "mssql+pyodbc",
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
            query=query,
        )

    def create_engine(self) -> Engine:
        return create_engine(self.sqlalchemy_url(), fast_executemany=True)


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    database: str
    username: str
    password: str
    port: int = 5432

    @classmethod
    def from_env(cls) -> "PostgresConfig":
        return cls(
            host=_required_env("POSTGRES_HOST"),
            database=_required_env("POSTGRES_DATABASE"),
            username=_required_env("POSTGRES_USER"),
            password=_required_env("POSTGRES_PASSWORD"),
            port=_env_port("POSTGRES_PORT", 5432),
        )

    def sqlalchemy_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg2",
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )

    def create_engine(self) -> Engine:
        return create_engine(self.sqlalchemy_url())