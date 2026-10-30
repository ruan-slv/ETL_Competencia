from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import Engine, Text, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.schema import CreateSchema

from src.etl.common import (
    CSV_ROOT,
    REPOSITORY_ROOT,
    TRANSFORMED_DIR,
    csv_file,
    decode_csv_value,
    read_manifest,
)
from src.settings import PostgresConfig


def load_files(
    engine: Engine, input_dir: str = str(TRANSFORMED_DIR)
) -> int:
    source_directory = Path(input_dir)
    manifest = read_manifest(CSV_ROOT / "transformed_manifest.json")
    if not manifest:
        raise RuntimeError("O manifesto transformado não contém tabelas.")

    with engine.begin() as connection:
        existing_schemas = set(inspect(connection).get_schema_names())
        for table in manifest:
            target_schema = str(table["target_schema"])
            if target_schema not in existing_schemas:
                connection.execute(CreateSchema(target_schema, if_not_exists=True))
                existing_schemas.add(target_schema)

            source_path = csv_file(source_directory, str(table["filename"]))
            frame = pd.read_csv(
                source_path,
                dtype=str,
                keep_default_na=False,
                encoding="utf-8",
            )
            expected_columns = [
                str(column["target_name"]) for column in table["columns"]
            ]
            if list(frame.columns) != expected_columns:
                raise ValueError(
                    f"As colunas de {source_path} não correspondem ao manifesto."
                )

            frame = frame.map(decode_csv_value)
            frame.to_sql(
                name=str(table["target_table"]),
                schema=target_schema,
                con=connection,
                if_exists="replace",
                index=False,
                chunksize=1_000,
                dtype={column: Text() for column in expected_columns},
            )
            print(
                f"Carregado: {source_path} -> "
                f"{target_schema}.{table['target_table']}"
            )

    return len(manifest)


def main() -> int:
    load_dotenv(REPOSITORY_ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Carrega os CSVs transformados no PostgreSQL."
    )
    parser.add_argument(
        "--input-dir",
        default=str(TRANSFORMED_DIR),
        help="Diretório dos CSVs transformados.",
    )
    args = parser.parse_args()

    engine: Engine | None = None
    try:
        engine = PostgresConfig.from_env().create_engine()
        count = load_files(engine, args.input_dir)
    except (OSError, ValueError, RuntimeError, SQLAlchemyError) as exc:
        print(f"Falha na carga: {exc}", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()

    print(f"Carga concluída: {count} tabelas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())