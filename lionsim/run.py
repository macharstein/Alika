"""Command line entry point: python -m lionsim.run --days 1 --seed 42."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import importlib.metadata
import logging
import multiprocessing
import platform
import sys
import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator

import numpy as np

from . import __version__, SCHEMA_VERSION
from .config import Config, load_config
from .io_utils import atomic_output, create_run_directory, day_directory, write_day, write_json, write_text
from .events import TOKENS
from .features_path import PATH_FEATURE_COLUMNS, features_at_report
from .reports import build_reports, target_rows
from .stats import summarize_for_stats, build_stats_report, render_stats_markdown, baselines_from_csv, add_headline_check
from .simulator import simulate_day
from .validate import SummaryAccumulator, summarize_day, validate_day

LOGGER = logging.getLogger("lionsim")


def _positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def _nonnegative(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be nonnegative")
    return number


def _date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
        if value != parsed.isoformat():
            raise ValueError
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD") from error
    return parsed.isoformat()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=_positive, default=None, help="independent days (default: 1)")
    parser.add_argument("--seed", type=_nonnegative, default=None, help="base seed (default: 42)")
    parser.add_argument("--config", type=Path, help="partial or complete JSON configuration")
    parser.add_argument("--set", dest="overrides", action="append", default=[], metavar="KEY=VALUE",
                        help="repeatable dotted configuration override")
    parser.add_argument("--start-date", type=_date, default=None,
                        help="simulated calendar date of day 1")
    parser.add_argument("--out", type=Path, default=Path("outputs"), help="output root")
    parser.add_argument("--image-days", type=_nonnegative, metavar="K",
                        help="render first K selected days (default: all normal days; none in stats/oracle mode)")
    parser.add_argument("--no-images", action="store_true", help="disable report PNGs and contact sheets")
    parser.add_argument("--workers", type=_positive, default=1, metavar="W",
                        help="worker processes (default: 1)")
    parser.add_argument("--day-index", type=_positive, metavar="I",
                        help="regenerate exactly one 1-based day; overrides --days")
    parser.add_argument("--stats-only", action="store_true", help="collect statistics without minute tables; images require --image-days")
    parser.add_argument("--stats-days", type=_positive, default=None, help="statistics days (default: 200)")
    parser.add_argument("--oracle", action="store_true", help="evaluate hidden-state rollout oracle and counting baselines")
    parser.add_argument("--oracle-days", type=_positive, default=None, help="oracle days (default: learnability.oracle_days, 100)")
    parser.add_argument("--oracle-rollouts", type=_positive, default=None, help="rollouts per usable report (default: learnability.oracle_rollouts, 100)")
    parser.add_argument("--keep-files", action="store_true", help="retain daily JSON and minute tables in statistics/oracle mode")
    parser.add_argument("--resume", type=Path, metavar="RUN_DIR", help="resume/checkpoint a run using the current schema and simulator version")
    parser.add_argument("--chunk-size", type=_positive, default=200, help="maximum new days per invocation (default: 200)")
    return parser


def _versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {"python": platform.python_version(), "lionsim": __version__}
    for package in ("numpy", "pandas", "matplotlib", "pyarrow"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def _run_day(job: dict[str, Any]) -> dict[str, Any]:
    """Publish all outputs before the per-day completion checkpoint."""
    config = Config(job["config"])
    oracle_rows = None
    if job.get("oracle"):
        from .oracle import evaluate_day

        day, oracle_rows = evaluate_day(config, day_index=job["day_index"], seed=job["seed"],
                                       start_date=job["start_date"], seed_sequence=job["seed_sequence"],
                                       rollouts=job["oracle_rollouts"])
    else:
        day = simulate_day(config, day_index=job["day_index"], seed=job["seed"],
                           start_date=job["start_date"], seed_sequence=job["seed_sequence"])
    reports = build_reports(day, config)
    validation = validate_day(day, config)
    written: list[dict[str, Any]] = []
    if job["keep_files"] or job["render"]:
        directory = day_directory(job["run_directory"], day.day_index, job["folder_width"])
        if job["keep_files"]:
            write_day(day, reports, directory, prefer_parquet=config["output"]["prefer_parquet"])
        if job["render"]:
            from .plotting import render_reports

            render_reports(day, reports, config, directory / "images")
        written = [{"path": str(path.relative_to(job["run_directory"])), "bytes": path.stat().st_size}
                   for path in sorted(directory.rglob("*")) if path.is_file() and not path.name.startswith(".")]
    stats = summarize_for_stats(day, reports, config)
    stats["validation"] = validation
    targets = target_rows(day, reports)
    for row in targets:
        report_time = reports[row["report_index"] - 1]["report_time"]
        row.update(features_at_report(day.gps, day.events, report_time, config))
    record = {"day_index": day.day_index, "run_fingerprint": job["run_fingerprint"],
              "summary": summarize_day(day, reports, validation, config), "stats": stats,
              "targets": targets, "files": written}
    if oracle_rows is not None:
        record["oracle"] = oracle_rows
    checkpoint = Path(job["run_directory"]) / "checkpoints" / f"day_{day.day_index:0{job['folder_width']}d}.json"
    write_json(checkpoint, record, pretty=False)
    return record


def _stream_jobs(jobs: Iterable[dict[str, Any]], workers: int) -> Iterator[dict[str, Any]]:
    if workers == 1:
        for job in jobs:
            yield _run_day(job)
        return
    # Bounded submission avoids retaining thousands of results or configurations
    # in executor queues. Consume in day order for deterministic aggregation.
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        iterator = iter(jobs)
        pending = deque()
        for _ in range(2 * workers):
            job = next(iterator, None)
            if job is None:
                break
            pending.append(pool.submit(_run_day, job))
        while pending:
            yield pending.popleft().result()
            job = next(iterator, None)
            if job is not None:
                pending.append(pool.submit(_run_day, job))


def _fingerprint(config: Config, seed: int, start_date: str) -> str:
    value = {"config": config.to_dict(), "seed": seed, "start_date": start_date}
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _load_records(directory: Path, manifest: dict[str, Any]) -> dict[int, dict[str, Any]]:
    records = {}
    expected = set(manifest["day_indices"])
    for path in sorted((directory / "checkpoints").glob("day_*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            index = record["day_index"]
            if index not in expected or record["run_fingerprint"] != manifest["run_fingerprint"]:
                raise ValueError("checkpoint does not belong to this run")
            targets = record["targets"]
            expected_reports = len(manifest["config"]["time"]["report_times"]) - 1
            if (len(targets) != expected_reports
                    or [row["report_index"] for row in targets] != list(range(1, expected_reports + 1))
                    or any(row["day"] != index or any(column not in row for column in PATH_FEATURE_COLUMNS)
                           for row in targets)):
                raise ValueError("incomplete path-feature checkpoint")
            for row in targets:
                for column in PATH_FEATURE_COLUMNS:
                    value = row[column]
                    if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                              or not np.isfinite(value)):
                        raise ValueError("invalid path-feature checkpoint value")
            if manifest.get("oracle"):
                rows = record["oracle"]
                expected_reports = len(manifest["config"]["time"]["report_times"]) - 1
                if (len(rows) != expected_reports
                        or [row["report_index"] for row in rows] != list(range(1, expected_reports + 1))
                        or any(row["day"] != index or row["rollouts"] != manifest["oracle_rollouts"]
                               or sum(row["counts"].values()) != row["rollouts"] for row in rows)):
                    raise ValueError("incomplete oracle checkpoint")
            for item in record["files"]:
                artifact = directory / item["path"]
                if not artifact.is_file() or artifact.stat().st_size != item["bytes"]:
                    raise ValueError(f"missing or incomplete output {item['path']}")
            records[index] = record
        except (OSError, ValueError, KeyError, TypeError) as error:
            LOGGER.warning("Will regenerate incomplete checkpoint %s: %s", path.name, error)
    return records


def _write_aggregates(directory: Path, records: dict[int, dict[str, Any]], config: Config,
                      pretty: bool, execution_error: str | None = None, oracle: bool = False) -> dict[str, Any]:
    ordered = [records[index] for index in sorted(records)]
    accumulator = SummaryAccumulator(config)
    for record in ordered:
        accumulator.add_record(record["summary"])
    validation = accumulator.validation_report()
    if execution_error is not None:
        validation.update(valid=False, execution_error=execution_error)
    write_json(directory / "summary_stats.json", accumulator.summary(), pretty)
    write_json(directory / "validation_report.json", validation, pretty)
    columns = ["day", "report_index", "report_time_bucket", "current_zone", "last_event", "next_zone_target",
               "shade_entry_hour_bucket", "drinks_so_far", "chase_attempts_so_far", "catch_so_far"]
    columns += list(PATH_FEATURE_COLUMNS)
    with atomic_output(directory / "targets.csv") as temporary:
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for record in ordered:
                writer.writerows(record["targets"])
    report = build_stats_report([record["stats"] for record in ordered], config)
    report["baseline_ladder"] = baselines_from_csv(directory / "targets.csv", config)
    add_headline_check(report, config)
    if oracle:
        from .oracle import oracle_report, render_oracle_markdown

        evaluation = oracle_report([row for record in ordered for row in record["oracle"]],
                                   report["baseline_ladder"], config)
        write_json(directory / "oracle_report.json", evaluation, pretty=True)
        write_text(directory / "oracle_report.md", render_oracle_markdown(evaluation))
        report["oracle"] = {key: value for key, value in evaluation.items() if key != "rows"}
        for check in evaluation["checks"]:
            report["checks"].append(check)
            report["check_counts"][check["status"]] += 1
    write_json(directory / "stats_report.json", report, pretty=True)
    write_text(directory / "stats_report.md", render_stats_markdown(report))
    return validation


def run(args: argparse.Namespace) -> Path:
    if args.resume is not None:
        directory = args.resume.resolve()
        manifest = json.loads((directory / "run_manifest.json").read_text(encoding="utf-8"))
        if manifest.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("--resume requires the current schema and daily checkpoints")
        if manifest["versions"]["lionsim"] != __version__:
            raise ValueError("Resume requires the same simulator version as the original run")
        if args.config is not None or args.overrides:
            raise ValueError("Resume uses the saved configuration; do not pass --config or --set")
        for supplied, original, name in ((args.seed, manifest["seed"], "seed"),
                                        (args.start_date, manifest["start_date"], "start-date"),
                                        (args.days, manifest["days"], "days"),
                                        (args.stats_days, manifest["days"], "stats-days"),
                                        (args.oracle_days, manifest["days"], "oracle-days"),
                                        (args.oracle_rollouts, manifest.get("oracle_rollouts"), "oracle-rollouts")):
            if supplied is not None and supplied != original:
                raise ValueError(f"Cannot change --{name} while resuming")
        if (args.oracle or args.oracle_days is not None or args.oracle_rollouts is not None) and not manifest.get("oracle"):
            raise ValueError("Cannot switch an existing run to oracle mode")
        if args.day_index is not None and manifest["day_indices"] != [args.day_index]:
            raise ValueError("Cannot change --day-index while resuming")
        if args.stats_only and not manifest["stats_only"]:
            raise ValueError("Cannot switch a normal run to statistics-only while resuming")
        if args.keep_files and not manifest["keep_files"]:
            raise ValueError("Cannot enable --keep-files after starting a statistics-only run")
        if args.no_images and manifest["image_days"] or args.image_days is not None and args.image_days != manifest["image_days"]:
            raise ValueError("Resume uses the original image selection")
        config = Config(manifest["config"])
        indices, seed, start_date = manifest["day_indices"], manifest["seed"], manifest["start_date"]
        manifest.pop("error", None)
    else:
        if args.stats_days is not None and not args.stats_only:
            raise ValueError("--stats-days requires --stats-only")
        if not args.oracle and (args.oracle_days is not None or args.oracle_rollouts is not None):
            raise ValueError("--oracle-days and --oracle-rollouts require --oracle")
        if args.oracle and (args.days is not None or args.stats_days is not None or args.day_index is not None):
            raise ValueError("Oracle runs use --oracle-days, not --days, --stats-days or --day-index")
        config = load_config(args.config, args.overrides)
        seed, start_date = args.seed if args.seed is not None else 42, args.start_date or "2026-01-01"
        days = (args.stats_days or 200) if args.stats_only else (args.days or 1)
        if args.oracle:
            days = args.oracle_days or config["learnability"]["oracle_days"]
        indices = [args.day_index] if args.day_index is not None else list(range(1, days + 1))
        image_days = len(indices) if args.image_days is None else min(len(indices), args.image_days)
        if args.no_images or ((args.stats_only or args.oracle) and args.image_days is None):
            image_days = 0
        directory = create_run_directory(args.out).resolve()
        manifest = {
            "config": config.to_dict(), "seed": seed, "versions": _versions(),
            "start_date": start_date, "days": len(indices), "day_indices": indices,
            "image_days": image_days, "stats_only": args.stats_only,
            "keep_files": not (args.stats_only or args.oracle) or args.keep_files,
            "oracle": args.oracle,
            "oracle_rollouts": (args.oracle_rollouts or config["learnability"]["oracle_rollouts"]) if args.oracle else None,
            "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "runtime_seconds": 0.0, "status": "running", "completed_days": 0,
            "schema_version": SCHEMA_VERSION, "day_log_schema": "lionsim-v3", "vocabulary": list(TOKENS),
            "ground_truth_latents_analysis_only": True,
            "seed_derivation": "numpy.random.SeedSequence(seed).spawn(max_day_index)[day_index - 1]",
            "run_fingerprint": _fingerprint(config, seed, start_date), "command": sys.argv,
        }
    records = _load_records(directory, manifest)
    pending = [index for index in indices if index not in records][:args.chunk_size]
    manifest.update(status="running", completed_days=len(records), workers=args.workers,
                    chunk_size=args.chunk_size, last_command=sys.argv)
    pretty = len(indices) <= config["output"]["json_pretty_max_days"]
    write_json(directory / "run_manifest.json", manifest, pretty)
    started = time.perf_counter()
    children = np.random.SeedSequence(seed).spawn(max(indices))
    ordinals = {index: ordinal for ordinal, index in enumerate(indices)}
    jobs = ({"config": config.to_dict(), "day_index": index, "seed": seed,
             "start_date": start_date, "seed_sequence": children[index - 1],
             "run_directory": str(directory), "folder_width": max(4, len(str(max(indices)))),
             "render": ordinals[index] < manifest["image_days"],
             "keep_files": manifest["keep_files"], "run_fingerprint": manifest["run_fingerprint"],
             "oracle": manifest.get("oracle", False), "oracle_rollouts": manifest.get("oracle_rollouts")}
            for index in pending)
    try:
        for record in _stream_jobs(jobs, min(args.workers, max(1, len(pending)))):
            records[record["day_index"]] = record
            manifest["completed_days"] = len(records)
            write_json(directory / "run_manifest.json", manifest, pretty)
            if len(records) == 1 or len(records) % 50 == 0 or len(records) == len(indices):
                LOGGER.info("Checkpointed %d/%d day(s)", len(records), len(indices))
        # Include worker checkpoints committed just before an interrupted parent
        # or a result-delivery delay; checkpoint files are the source of truth.
        records = _load_records(directory, manifest)
        validation = _write_aggregates(directory, records, config, pretty, oracle=manifest.get("oracle", False))
        manifest["status"] = ("partial" if len(records) < len(indices) else
                              "complete" if validation["valid"] else "validation_failed")
        for warning in validation.get("warnings", []):
            LOGGER.warning("%s", warning)
    except BaseException as error:
        manifest.update(status="failed", error=f"{type(error).__name__}: {error}")
        records = _load_records(directory, manifest)
        _write_aggregates(directory, records, config, pretty, manifest["error"], oracle=manifest.get("oracle", False))
        raise
    finally:
        manifest["completed_days"] = len(records)
        manifest["runtime_seconds"] = round(manifest.get("runtime_seconds", 0) + time.perf_counter() - started, 6)
        manifest["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        write_json(directory / "run_manifest.json", manifest, pretty)
    LOGGER.info("Run saved to %s (%s; %d/%d days)", directory, manifest["status"], len(records), len(indices))
    if manifest["status"] == "partial":
        LOGGER.info("Continue the next chunk: python -m lionsim.run --resume %s", directory)
    return directory


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        directory = run(args)
        import json

        with (directory / "validation_report.json").open(encoding="utf-8") as handle:
            return 0 if json.load(handle)["valid"] else 1
    except (ValueError, TypeError, KeyError, OSError) as error:
        LOGGER.error("%s", error)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
