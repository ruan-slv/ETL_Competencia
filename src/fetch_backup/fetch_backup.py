from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath

import pyodbc
from dotenv import load_dotenv

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BACKUP_PATH = "/var/opt/mssql/backup/AdventureWorks2025.bak"
DEFAULT_DATABASE = "AdventureWorks2025"


@dataclass(frozen=True)
class BackupFile:
    file_id: int
    logical_name: str
    file_type: str


def _sql_identifier(value: str) -> str:
    return f"[{value.replace(']', ']]')}]"


def _sql_string(value: str) -> str:
    return "N'" + value.replace("'", "''") + "'"


def _odbc_value(value: str) -> str:
    return "{" + value.replace("}", "}}") + "}"


def _environment_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise ValueError(f"A variável de ambiente {name} deve ser booleana.")


def _connection_string() -> str:
    password = os.getenv("SQLSERVER_PASSWORD")
    if not password:
        raise ValueError(
            "Defina SQLSERVER_PASSWORD no ambiente ou no arquivo .env."
        )

    host = os.getenv("SQLSERVER_HOST", "localhost")
    port = os.getenv("SQLSERVER_PORT", "1433")
    try:
        port_number = int(port)
    except ValueError as exc:
        raise ValueError("SQLSERVER_PORT deve ser uma porta válida.") from exc
    if not 1 <= port_number <= 65535:
        raise ValueError("SQLSERVER_PORT deve estar entre 1 e 65535.")

    driver = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")
    username = os.getenv("SQLSERVER_USER", "sa")
    trust_certificate = _environment_bool(
        "SQLSERVER_TRUST_SERVER_CERTIFICATE", True
    )
    return (
        f"DRIVER={_odbc_value(driver)};"
        f"SERVER={_odbc_value(f'tcp:{host},{port_number}')};"
        f"DATABASE=master;"
        f"UID={_odbc_value(username)};"
        f"PWD={_odbc_value(password)};"
        f"Encrypt=yes;"
        f"TrustServerCertificate={'yes' if trust_certificate else 'no'};"
    )


def _backup_files(cursor: pyodbc.Cursor, backup_path: str) -> list[BackupFile]:
    cursor.execute(
        f"RESTORE FILELISTONLY FROM DISK = {_sql_string(backup_path)}"
    )
    return [
        BackupFile(
            file_id=int(row.FileId),
            logical_name=str(row.LogicalName),
            file_type=str(row.Type),
        )
        for row in cursor.fetchall()
    ]


def _database_directories(
    cursor: pyodbc.Cursor,
) -> tuple[PurePosixPath, PurePosixPath]:
    cursor.execute(
        """
        SELECT type_desc, physical_name
        FROM sys.master_files
        WHERE database_id = DB_ID(N'master')
          AND type_desc IN ('ROWS', 'LOG')
        ORDER BY file_id
        """
    )
    directories = {
        str(row.type_desc): PurePosixPath(str(row.physical_name)).parent
        for row in cursor.fetchall()
    }
    if "ROWS" not in directories or "LOG" not in directories:
        raise RuntimeError(
            "Não foi possível localizar os diretórios de dados do SQL Server."
        )
    return directories["ROWS"], directories["LOG"]


def _restore_statement(
    cursor: pyodbc.Cursor,
    backup_path: str,
    database_name: str,
    replace: bool,
) -> str:
    files = _backup_files(cursor, backup_path)
    if not files:
        raise RuntimeError("O arquivo de backup não contém arquivos restauráveis.")

    unsupported_types = sorted({file.file_type for file in files} - {"D", "L"})
    if unsupported_types:
        raise RuntimeError(
            "O backup contém tipos de arquivo não suportados: "
            + ", ".join(unsupported_types)
        )

    data_directory, log_directory = _database_directories(cursor)
    data_files = sorted(
        (file for file in files if file.file_type == "D"),
        key=lambda file: file.file_id,
    )
    log_files = sorted(
        (file for file in files if file.file_type == "L"),
        key=lambda file: file.file_id,
    )
    if not data_files or not log_files:
        raise RuntimeError(
            "O backup precisa conter ao menos um arquivo de dados e um log."
        )

    moves: list[str] = []
    for index, file in enumerate(data_files, start=1):
        extension = "mdf" if index == 1 else "ndf"
        destination = data_directory / f"AdventureWorks2025_data_{index}.{extension}"
        moves.append(
            f"MOVE {_sql_string(file.logical_name)} TO {_sql_string(str(destination))}"
        )
    for index, file in enumerate(log_files, start=1):
        destination = log_directory / f"AdventureWorks2025_log_{index}.ldf"
        moves.append(
            f"MOVE {_sql_string(file.logical_name)} TO {_sql_string(str(destination))}"
        )

    options = ["FILE = 1", *moves, "RECOVERY"]
    if replace:
        options.append("REPLACE")
    options.append("STATS = 5")
    return (
        f"RESTORE DATABASE {_sql_identifier(database_name)} "
        f"FROM DISK = {_sql_string(backup_path)} "
        f"WITH {', '.join(options)}"
    )


def _database_state(cursor: pyodbc.Cursor, database_name: str) -> str | None:
    cursor.execute(
        "SELECT state_desc FROM sys.databases WHERE name = ?", database_name
    )
    row = cursor.fetchone()
    return None if row is None else str(row[0])


def _execute_restore(cursor: pyodbc.Cursor, statement: str) -> None:
    """Executa o RESTORE consumindo todos os resultados enviados pelo servidor.

    O SQL Server envia o andamento do RESTORE (opção STATS) como resultados
    adicionais. O pyodbc entrega apenas o primeiro em ``execute()``; sem
    consumir os demais com ``nextset()`` o comando ainda está em execução e o
    banco permanece no estado RESTORING quando a conexão é encerrada.
    """
    cursor.execute(statement)
    while cursor.nextset():
        pass


def restore_database(backup_path: str, database_name: str, replace: bool) -> None:
    connection = pyodbc.connect(_connection_string(), autocommit=True)
    try:
        cursor = connection.cursor()
        state = _database_state(cursor, database_name)
        database_exists = state is not None
        if database_exists and not replace:
            raise RuntimeError(
                f"O banco {database_name!r} já existe ({state}). "
                "Use --replace para substituí-lo."
            )

        quoted_database = _sql_identifier(database_name)
        if state == "RESTORING":
            # Restauração anterior interrompida: o banco não abre e também não
            # aceita ALTER DATABASE. Descarte-o antes de restaurar novamente.
            cursor.execute(f"DROP DATABASE {quoted_database}")

        statement = _restore_statement(
            cursor, backup_path, database_name, replace=database_exists and replace
        )
        if database_exists and state != "RESTORING":
            cursor.execute(
                f"ALTER DATABASE {quoted_database} "
                "SET SINGLE_USER WITH ROLLBACK IMMEDIATE"
            )
        try:
            _execute_restore(cursor, statement)
        except pyodbc.Error as restore_error:
            if database_exists and state != "RESTORING":
                try:
                    cursor.execute(f"ALTER DATABASE {quoted_database} SET MULTI_USER")
                except pyodbc.Error as cleanup_error:
                    raise RuntimeError(
                        f"A restauração falhou ({restore_error}) e não foi possível "
                        f"retornar {database_name!r} para MULTI_USER ({cleanup_error})."
                    ) from cleanup_error
            raise
        if database_exists and state != "RESTORING":
            cursor.execute(f"ALTER DATABASE {quoted_database} SET MULTI_USER")

        final_state = _database_state(cursor, database_name)
        if final_state != "ONLINE":
            raise RuntimeError(
                f"O banco {database_name!r} ficou no estado {final_state!r} após a "
                "restauração. Execute o programa novamente com --replace."
            )
    finally:
        connection.close()


def _version_mismatch_hint(error: pyodbc.Error) -> str | None:
    if "3169" not in str(error):
        return None
    return (
        "o backup foi criado por uma versão mais nova do SQL Server do que a "
        "instância de destino. Restaure-o em um SQL Server da mesma versão ou "
        "mais recente (AdventureWorks2025.bak exige SQL Server 2025, imagem "
        "mcr.microsoft.com/mssql/server:2025-latest) ou use um backup compatível."
    )


def main() -> int:
    load_dotenv(REPOSITORY_ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Restaura o backup AdventureWorks no SQL Server do Docker Compose."
    )
    parser.add_argument(
        "--backup",
        default=os.getenv("SQLSERVER_BACKUP_PATH", DEFAULT_BACKUP_PATH),
        help="Caminho do arquivo .bak visto pelo contêiner SQL Server.",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("SQLSERVER_DATABASE", DEFAULT_DATABASE),
        help="Nome do banco de dados a restaurar.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Substitui o banco de mesmo nome, encerrando as conexões ativas.",
    )
    args = parser.parse_args()

    try:
        restore_database(args.backup, args.database, replace=args.replace)
    except pyodbc.Error as exc:
        hint = _version_mismatch_hint(exc)
        print(f"Falha ao restaurar o backup: {hint or exc}", file=sys.stderr)
        if hint:
            print(f"Detalhe técnico: {exc}", file=sys.stderr)
        return 1
    except (RuntimeError, ValueError) as exc:
        print(f"Falha ao restaurar o backup: {exc}", file=sys.stderr)
        return 1

    print(f"Banco {args.database!r} restaurado com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())