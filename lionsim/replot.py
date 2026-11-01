"""Rebuild text-free images from an existing run's saved GPS, without simulation."""

from __future__ import annotations

import argparse
import json
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd

from . import __version__
from .config import Config
from .io_utils import write_json
from .reports import report_offsets_minutes

LOGGER = logging.getLogger("lionsim.replot")


def _render_saved_day(job: tuple[str, dict[str, Any]]) -> int:
    from .plotting import render_reports

    folder, data = job
    directory = Path(folder)
    config = Config(data)
    parquet, csv = directory / "gps.parquet", directory / "gps.csv.gz"
    gps = pd.read_parquet(parquet) if parquet.exists() else pd.read_csv(csv)
    if len(gps) != config["time"]["day_minutes"] + 1:
        raise ValueError(f"Unexpected GPS row count in {directory}")
    day = SimpleNamespace(day_index=int(directory.name.removeprefix("day_")),
                          date=str(gps.iloc[0]["t_iso"])[:10], gps=gps)
    reports = [{"report_index": index, "report_time": str(gps.iloc[offset]["t_iso"]),
                "path_up_to_index": offset}
               for index, offset in enumerate(report_offsets_minutes(config), 1)]
    render_reports(day, reports, config, directory / "images")
    return day.day_index


def replot_run(run_directory: str | Path, workers: int = 1) -> int:
    """Replace report PNGs and fill missing days using the original observations.

    Simulation records are never rewritten. Rendering provenance is appended to
    the manifest; its original simulation configuration and command are kept.
    """
    if workers < 1:
        raise ValueError("workers must be at least 1")
    directory = Path(run_directory).resolve()
    manifest_path = directory / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    data = Config().to_dict()
    original = manifest["config"]
    # Geometry, report times and image dimensions belong to the recorded run.
    # Annotation/cap settings are intentionally absent from the current renderer.
    for section in ("map", "time"):
        data[section] = original[section]
    for key, value in original.get("images", {}).items():
        if key in data["images"] and not key.startswith("_"):
            data["images"][key] = value
    config = Config(data)
    folders = sorted((directory / "days").glob("day_*"))
    actual = {int(folder.name.removeprefix("day_")) for folder in folders}
    expected = set(manifest.get("day_indices", range(1, manifest["days"] + 1)))
    if not folders or actual != expected:
        raise ValueError("Saved day folders do not match the run manifest")
    for folder in folders:
        if not (folder / "gps.parquet").exists() and not (folder / "gps.csv.gz").exists():
            raise FileNotFoundError(f"No saved GPS table in {folder}")
    jobs = [(str(folder), config.to_dict()) for folder in folders]
    if workers == 1:
        results = map(_render_saved_day, jobs)
        for count, _ in enumerate(results, 1):
            if count == 1 or count % 25 == 0 or count == len(folders):
                LOGGER.info("Rendered %d/%d saved days", count, len(folders))
    else:
        with ProcessPoolExecutor(max_workers=min(workers, len(folders)),
                                 mp_context=multiprocessing.get_context("spawn")) as pool:
            for count, _ in enumerate(pool.map(_render_saved_day, jobs), 1):
                if count == 1 or count % 25 == 0 or count == len(folders):
                    LOGGER.info("Rendered %d/%d saved days", count, len(folders))
    manifest["image_days"] = len(folders)
    manifest.setdefault("image_regenerations", []).append({
        "rendered_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "original saved GPS tables; simulation data unchanged",
        "lionsim_version": __version__, "workers": workers,
        "image_days": len(folders), "images": config["images"],
    })
    write_json(manifest_path, manifest, pretty=len(folders) <= config["output"]["json_pretty_max_days"])
    LOGGER.info("All %d days now have text-free images in %s", len(folders), directory)
    return len(folders)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        replot_run(args.run_directory, args.workers)
    except (OSError, ValueError, KeyError) as error:
        LOGGER.error("%s", error)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
