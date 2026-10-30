from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import Engine, inspect
from sqlalchemy.exc import SQLAlchemyError

from src.etl.common import (
    CHUNK_SIZE,
    CSV_ROOT,
    NULL_TOKEN,
    RAW_DIR,
    REPOSITORY_ROOT,
    encode_csv_value,
    normalize_identifier,
    write_manifest,
)
from src.settings import SQLServerConfig


def extract_tables(engine: Engine, output_dir: str = str(RAW_DIR)) -> int:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    inspector = inspect(engine)
    preparer = engine.dialect.identifier_preparer
    schema_names = sorted(
        schema
        for schema in inspector.get_schema_names()
        if schema.casefold() not in {"sys", "information_schema"}
    )

    schema_names_used: set[str] = set()
    schema_mapping = {
        schema: normalize_identifier(schema, schema_names_used)
        for schema in schema_names
    }
    used_tables: dict[str, set[str]] = {}
    manifest: list[dict[str, Any]] = []

    with engine.connect() as connection:
        for source_schema in schema_names:
            for source_table in sorted(inspector.get_table_names(schema=source_schema)):
                source_columns = inspector.get_columns(
                    source_table, schema=source_schema
                )
                if not source_columns:
                    continue

                target_schema = schema_mapping[source_schema]
                target_table = normalize_identifier(
                    source_table, used_tables.setdefault(target_schema, set())
                )
                target_columns_used: set[str] = set()
                columns = [
                    {
                        "source_name": str(column["name"]),
                        "target_name": normalize_identifier(
                            str(column["name"]), target_columns_used
                        ),
                    }
                    for column in source_columns
                ]
                filename = f"{target_schema}__{target_table}.csv"
                output_path = destination / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)

                quoted_table = (
                    f"{preparer.quote_schema(source_schema)}."
                    f"{preparer.quote(source_table)}"
                )
                query = f"SELECT * FROM {quoted_table}"
                with output_path.open("w", encoding="utf-8", newline="") as stream:
                    pd.DataFrame(
                        columns=[column["source_name"] for column in columns]
                    ).to_csv(stream, index=False, lineterminator="\n")
                    chunks = pd.read_sql_query(
                        query, connection, chunksize=CHUNK_SIZE
                    )
                    for chunk in chunks:
                        chunk.map(encode_csv_value).to_csv(
                            stream,
                            index=False,
                            header=False,
                            na_rep=NULL_TOKEN,
                            lineterminator="\n",
                        )

                manifest.append(
                    {
                        "source_schema": source_schema,
                        "source_table": source_table,
                        "target_schema": target_schema,
                        "target_table": target_table,
                        "filename": filename,
                        "columns": columns,
                    }
                )
                print(
                    f"Extraído: {source_schema}.{source_table} -> {output_path}"
                )

    if not manifest:
        raise RuntimeError("Nenhuma tabela de usuário foi encontrada no SQL Server.")

    write_manifest(CSV_ROOT / "raw_manifest.json", manifest)
    return len(manifest)


def main() -> int:
    load_dotenv(REPOSITORY_ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Extrai todas as tabelas de usuário do SQL Server para CSV."
    )
    parser.add_argument(
        "--output-dir",
        default=str(RAW_DIR),
        help="Diretório dos CSVs brutos (padrão: src/data/csv/raw).",
    )
    args = parser.parse_args()

    engine: Engine | None = None
    try:
        engine = SQLServerConfig.from_env().create_engine()
        count = extract_tables(engine, args.output_dir)
    except (OSError, RuntimeError, ValueError, SQLAlchemyError) as exc:
        print(f"Falha na extração: {exc}", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()

    print(f"Extração concluída: {count} tabelas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())