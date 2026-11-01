"""Deterministic JSON/table serialization and unique run directories."""

from __future__ import annotations

import gzip
import importlib.util
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

from .events import serializable_events


def create_run_directory(output_root: str | Path) -> Path:
    """Never replace an earlier run, including two runs in the same second."""
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    basename = datetime.now().astimezone().strftime("run_%Y%m%d_%H%M%S")
    for suffix in range(10000):
        candidate = root / (basename if suffix == 0 else f"{basename}_{suffix:02d}")
        try:
            candidate.mkdir()
            (candidate / "days").mkdir()
            return candidate
        except FileExistsError:
            continue
    raise FileExistsError("Could not allocate a unique run directory")


def day_directory(run_directory: str | Path, day_index: int, width: int = 4) -> Path:
    path = Path(run_directory) / "days" / f"day_{day_index:0{width}d}"
    path.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def atomic_output(path: str | Path) -> Iterator[Path]:
    """Publish a complete file with a same-directory atomic rename.

    A failed writer leaves any previous destination intact. An interrupted
    process may leave an unreferenced temporary file, never a partial output.
    """
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{destination.stem}.",
                                      suffix=destination.suffix, dir=destination.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        yield temporary
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def write_text(path: str | Path, content: str) -> None:
    with atomic_output(path) as temporary:
        temporary.write_text(content, encoding="utf-8")


def write_json(path: str | Path, payload: Any, pretty: bool = True) -> None:
    """Reject NaN/Infinity rather than silently writing invalid JSON."""
    with atomic_output(path) as temporary:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2 if pretty else None,
                      separators=None if pretty else (",", ":"), allow_nan=False)
            handle.write("\n")


def write_table(frame: pd.DataFrame, path_without_suffix: str | Path,
                prefer_parquet: bool = True) -> Path:
    path = Path(path_without_suffix)
    if prefer_parquet and importlib.util.find_spec("pyarrow") is not None:
        destination = path.with_suffix(".parquet")
        with atomic_output(destination) as temporary:
            frame.to_parquet(temporary, engine="pyarrow", index=False)
    else:
        destination = path.with_suffix(".csv.gz")
        # Suppress the gzip wall-clock timestamp and original filename so that
        # regenerations are byte-identical on the same software versions.
        with atomic_output(destination) as temporary:
            with temporary.open("wb") as raw:
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
                    frame.to_csv(zipped, index=False, float_format="%.17g")
    return destination


def write_day(day: Any, reports: list[dict[str, Any]], directory: Path,
              prefer_parquet: bool = True) -> dict[str, Any]:
    """Write daily reports and analysis-only latents; bars remain in their table."""
    write_table(day.gps, directory / "gps", prefer_parquet)
    write_table(day.hidden_state, directory / "hidden_state", prefer_parquet)
    payload = {"day_index": day.day_index, "date": day.date,
               "events": serializable_events(day.events), "reports": reports,
               "ground_truth_latents": {**day.latents,
                   "tourist_volume": len(getattr(day, "traffic_times", [])), "_analysis_only": True}}
    write_json(directory / "day.json", payload, pretty=True)
    return payload
