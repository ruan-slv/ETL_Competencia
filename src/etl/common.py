from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CSV_ROOT = REPOSITORY_ROOT / "src" / "data" / "csv"
RAW_DIR = CSV_ROOT / "raw"
TRANSFORMED_DIR = CSV_ROOT / "transformed"
NULL_TOKEN = r"\N"
CHUNK_SIZE = 10_000
POSTGRES_IDENTIFIER_LIMIT = 63


def normalize_identifier(value: str, used: set[str]) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    normalized = normalized or "unnamed"
    candidate = normalized[:POSTGRES_IDENTIFIER_LIMIT]

    if candidate in used:
        suffix = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
        candidate = f"{normalized[:POSTGRES_IDENTIFIER_LIMIT - 9]}_{suffix}"
        sequence = 2
        while candidate in used:
            extra = f"_{sequence}"
            candidate = (
                f"{normalized[:POSTGRES_IDENTIFIER_LIMIT - len(extra)]}{extra}"
            )
            sequence += 1

    used.add(candidate)
    return candidate


def encode_csv_value(value: Any) -> Any:
    if value is None or value is pd.NA or pd.isna(value):
        return pd.NA
    if isinstance(value, (bytes, bytearray, memoryview)):
        return "0x" + bytes(value).hex()
    return str(value).replace("\\", "\\\\")


def decode_csv_value(value: str) -> str | None:
    if value == NULL_TOKEN:
        return None
    return value.replace("\\\\", "\\")


def write_manifest(path: Path, tables: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(tables, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def read_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Manifesto não encontrado: {path}. Execute a etapa anterior da ETL."
        )

    tables = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(tables, list):
        raise ValueError(f"O manifesto {path} deve conter uma lista de tabelas.")
    return tables


def csv_file(directory: Path, filename: str) -> Path:
    if Path(filename).name != filename or not filename.endswith(".csv"):
        raise ValueError(f"Nome de arquivo CSV inválido no manifesto: {filename!r}.")
    return directory / filename
