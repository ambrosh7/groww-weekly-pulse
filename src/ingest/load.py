"""Load raw Play review exports from CSV/JSON (Phase 1)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


class IngestError(ValueError):
    """Unreadable or unsupported raw export."""


SUPPORTED_SUFFIXES = {".csv", ".json"}


def load_raw_file(path: Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        raise IngestError(f"Raw file not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise IngestError(
            f"Unsupported file type '{suffix}' for {path.name}. "
            f"Supported: {sorted(SUPPORTED_SUFFIXES)}"
        )

    if suffix == ".csv":
        return _load_csv(path)
    return _load_json(path)


def load_raw_paths(paths: list[Path]) -> list[dict[str, Any]]:
    if not paths:
        raise IngestError("No raw files provided. Place a Play export under data/raw/.")
    rows: list[dict[str, Any]] = []
    for path in paths:
        rows.extend(load_raw_file(path))
    return rows


def discover_raw_files(raw_dir: Path) -> list[Path]:
    raw_dir = Path(raw_dir)
    if not raw_dir.exists():
        raise IngestError(f"Raw directory missing: {raw_dir}")
    files = sorted(
        p
        for p in raw_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES and not p.name.startswith(".")
    )
    return files


def _load_csv(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as fh:
            sample = fh.read(4096)
            fh.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
            except csv.Error:
                dialect = csv.excel
            reader = csv.DictReader(fh, dialect=dialect)
            if not reader.fieldnames:
                raise IngestError(f"CSV has no header: {path}")
            return [dict(row) for row in reader]
    except IngestError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise IngestError(f"Corrupt or unreadable CSV {path}: {exc}") from exc


def _load_json(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open(encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except Exception as exc:  # noqa: BLE001
        raise IngestError(f"Corrupt or unreadable JSON {path}: {exc}") from exc

    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        for key in ("reviews", "data", "items"):
            if isinstance(data.get(key), list):
                rows = data[key]
                break
        else:
            raise IngestError(f"JSON root must be a list or contain reviews[]: {path}")
    else:
        raise IngestError(f"JSON root must be a list or object: {path}")

    out: list[dict[str, Any]] = []
    for i, item in enumerate(rows):
        if not isinstance(item, dict):
            raise IngestError(f"JSON row {i} is not an object in {path}")
        out.append(item)
    return out
