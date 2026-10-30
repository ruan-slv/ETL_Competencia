from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from src.etl.common import (
    CSV_ROOT,
    RAW_DIR,
    REPOSITORY_ROOT,
    TRANSFORMED_DIR,
    csv_file,
    decode_csv_value,
    encode_csv_value,
    read_manifest,
    write_manifest,
)


def transform_files(
    input_dir: str = str(RAW_DIR),
    output_dir: str = str(TRANSFORMED_DIR),
) -> int:
    source_directory = Path(input_dir)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    manifest = read_manifest(CSV_ROOT / "raw_manifest.json")

    for table in manifest:
        source_path = csv_file(source_directory, table["filename"])
        frame = pd.read_csv(
            source_path,
            dtype=str,
            keep_default_na=False,
            encoding="utf-8",
        )
        columns = table["columns"]
        expected_columns = [column["source_name"] for column in columns]
        if list(frame.columns) != expected_columns:
            raise ValueError(
                f"As colunas de {source_path} não correspondem ao manifesto."
            )

        frame = frame.map(decode_csv_value)
        frame.columns = [column["target_name"] for column in columns]
        output_path = destination / table["filename"]
        frame.map(encode_csv_value).to_csv(
            output_path,
            index=False,
            na_rep=r"\N",
            encoding="utf-8",
            lineterminator="\n",
        )
        print(f"Transformado: {source_path} -> {output_path}")

    write_manifest(CSV_ROOT / "transformed_manifest.json", manifest)
    return len(manifest)


def main() -> int:
    load_dotenv(REPOSITORY_ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Normaliza os nomes de colunas dos CSVs extraídos."
    )
    parser.add_argument(
        "--input-dir",
        default=str(RAW_DIR),
        help="Diretório de CSVs brutos (padrão: src/data/csv/raw).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(TRANSFORMED_DIR),
        help="Diretório dos CSVs transformados (padrão: src/data/csv/transformed).",
    )
    args = parser.parse_args()

    try:
        count = transform_files(args.input_dir, args.output_dir)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Falha na transformação: {exc}", file=sys.stderr)
        return 1

    print(f"Transformação concluída: {count} arquivos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())