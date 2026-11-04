"""Behavioural contracts, reproducibility, and actual command-line integration."""

from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lionsim.config import load_config
from lionsim.io_utils import write_day
from lionsim.events import serializable_events
from lionsim.reports import build_reports
from lionsim.simulator import simulate_day
from lionsim.validate import SummaryAccumulator, validate_day
from lionsim.zones import HysteresisTracker, ZoneMap


@pytest.fixture(scope="module")
def config():
    return load_config()


@pytest.fixture(scope="module")
def day(config):
    return simulate_day(config, seed=42)


def assert_same_day(left, right):
    assert left.day_index == right.day_index
    assert left.date == right.date
    assert left.seed_info == right.seed_info
    assert left.latents == right.latents
    assert left.events == right.events
    assert left.traffic_times == right.traffic_times
    pd.testing.assert_frame_equal(left.gps, right.gps)
    pd.testing.assert_frame_equal(left.hidden_state, right.hidden_state)


def test_same_seed_is_identical(config, day):
    repeated = simulate_day(config, seed=42)
    assert_same_day(day, repeated)
    assert build_reports(day, config) == build_reports(repeated, config)
    different = simulate_day(config, seed=43)
    assert not different.gps.equals(day.gps)


def test_day_index_uses_spawned_child(config):
    child = np.random.SeedSequence(123).spawn(8)[7]
    from_batch = simulate_day(config, day_index=8, seed=123, start_date="2026-01-01", seed_sequence=child)
    standalone = simulate_day(config, day_index=8, seed=123, start_date="2026-01-01")
    assert_same_day(from_batch, standalone)
    assert standalone.date == "2026-01-08"


def test_zone_lookup_hysteresis_and_gap(config):
    zones = ZoneMap(config)
    for name in zones.names:
        assert zones.lookup(*zones.center(name)) == name
    assert zones.lookup(0, 0) is None
    assert zones.lookup(9, 0) == "Road"
    assert zones.lookup(1, 3) == "Plain"
    tracker = HysteresisTracker(required_minutes=2, initial_zone="Den")
    assert tracker.update("Den") is None
    assert tracker.update("Shade") is None
    assert tracker.update(None) is None  # A brief visit must not count.
    assert tracker.update("Shade") is None
    assert tracker.update("Shade") == "Shade"
    assert tracker.update("Shade") is None
    assert tracker.update(None) is None
    assert tracker.update("Shade") is None  # Never repeat the previous entry.
    assert tracker.update("Den") is None
    assert tracker.update("Den") == "Den"


def test_config_json_and_dotted_overrides(tmp_path):
    custom = tmp_path / "custom.json"
    custom.write_text(json.dumps({"randomness": {"gps_noise_sd_m": 7.0}}))
    config = load_config(custom, ["randomness.gps_noise_sd_m=3.5", "output.prefer_parquet=false",
                                  "goal.periods.0.priors.Den=4", "map.zones.Den.center=[2.1,8.0]"])
    assert config["randomness"]["gps_noise_sd_m"] == 3.5
    assert config["output"]["prefer_parquet"] is False
    assert config["goal"]["periods"][0]["priors"]["Den"] == 4
    assert config["map"]["zones"]["Den"]["center"] == [2.1, 8.0]
    with pytest.raises(ValueError):
        load_config(overrides=["randomness.gps_dropout_probability=1.1"])
    with pytest.raises(ValueError):
        load_config(overrides=["map.zones.Shade.center=[2,8]"])
    with pytest.raises((ValueError, KeyError)):
        load_config(overrides=["randomness.typo=1"])


def test_batch_of_twenty_passes_invariants(config):
    accumulator = SummaryAccumulator(config)
    for index, child in enumerate(np.random.SeedSequence(42).spawn(20), 1):
        result = simulate_day(config, day_index=index, seed=42, seed_sequence=child)
        validation = validate_day(result, config)
        assert validation["valid"], (index, validation["errors"])
        accumulator.add(result, build_reports(result, config), validation)
    validation = accumulator.validation_report()
    assert validation["valid"]
    assert validation["days_checked"] == 20
    summary = accumulator.summary()
    assert len(summary["token_frequencies"]) == 17
    assert "CAR_PASSED" not in summary["token_frequencies"]
    hours = summary["hours_per_behaviour"]
    assert sum(value for name, value in hours.items() if name != "sleeping_resting") == pytest.approx(24, abs=1e-5)
    assert summary["tourist_car_counts"]["total"] > 0


def test_reports_partition_events_and_reference_path_prefix(config, day):
    reports = build_reports(day, config)
    assert len(reports) == 8
    assert [report["path_up_to_index"] for report in reports] == list(range(180, 1441, 180))
    assert all("path" not in report for report in reports)
    assert [event for report in reports for event in report["new_events"]] == serializable_events(day.events)
    assert reports[6]["report_time"] == "2026-01-02T02:00:00"
    assert reports[7]["report_time"] == "2026-01-02T05:00:00"
    zones = ZoneMap(config)
    for report in reports:
        row = day.gps.iloc[report["path_up_to_index"]]
        assert report["current_zone"] == zones.lookup(row["x_true_km"], row["y_true_km"])
        assert row["t_iso"] == report["report_time"]


def test_validator_exposes_corrupted_events(config, day):
    corrupted = copy.deepcopy(day)
    corrupted.events[0]["token"] = "FAIL"
    validation = validate_day(corrupted, config)
    assert not validation["valid"]
    assert any("first event" in error for error in validation["errors"])
    assert any("CHASE_START" in error for error in validation["errors"])


def test_all_missing_after_initial_fix_is_forward_filled():
    config = load_config(overrides=["randomness.gps_dropout_probability=1"])
    day = simulate_day(config)
    assert not day.gps.iloc[0]["missing"]
    assert day.gps.iloc[1:]["missing"].all()
    assert day.gps["x_km"].nunique() == 1
    assert day.gps["y_km"].nunique() == 1
    assert validate_day(day, config)["valid"]


def test_csv_fallback_deterministic_and_no_hidden_bars(tmp_path, config, day):
    left, right = tmp_path / "left", tmp_path / "right"
    left.mkdir()
    right.mkdir()
    reports = build_reports(day, config)
    write_day(day, reports, left, prefer_parquet=False)
    write_day(day, reports, right, prefer_parquet=False)
    for name in ("day.json", "gps.csv.gz", "hidden_state.csv.gz"):
        assert (left / name).read_bytes() == (right / name).read_bytes()
    payload = json.loads((left / "day.json").read_text())
    assert set(payload) == {"day_index", "date", "events", "reports", "ground_truth_latents", "weather"}
    assert payload["ground_truth_latents"]["_analysis_only"] is True
    assert all(set(event) == {"id", "t", "token", "description", "zone"} for event in payload["events"])
    assert "hidden_state" not in payload
    assert not {"hunger", "energy", "temperature", "mood", "boredom"} & payload.keys()
    gps = pd.read_csv(left / "gps.csv.gz")
    assert len(gps) == 1441


def _cli(tmp_path: Path, label: str, *args: str) -> Path:
    out = tmp_path / label
    command = [sys.executable, "-m", "lionsim.run", "--out", str(out), "--no-images",
               "--set", "output.prefer_parquet=false", *args]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=120)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return next(out.glob("run_*"))


def test_cli_worker_count_and_single_day_regeneration(tmp_path):
    # Run metadata may differ in indentation; event JSON is always readable.
    serial = _cli(tmp_path, "serial", "--days", "6", "--workers", "1")
    parallel = _cli(tmp_path, "parallel", "--days", "6", "--workers", "2")
    standalone = _cli(tmp_path, "standalone", "--day-index", "6")
    for index in range(1, 7):
        for name in ("day.json", "gps.csv.gz", "hidden_state.csv.gz"):
            relative = Path("days") / f"day_{index:04d}" / name
            assert (serial / relative).read_bytes() == (parallel / relative).read_bytes()
            if index == 6:
                if name == "day.json":
                    assert json.loads((serial / relative).read_text()) == json.loads((standalone / relative).read_text())
                else:
                    assert (serial / relative).read_bytes() == (standalone / relative).read_bytes()
    assert json.loads((serial / "summary_stats.json").read_text()) == json.loads((parallel / "summary_stats.json").read_text())
    assert not list(serial.rglob("*.png"))
    manifest = json.loads((standalone / "run_manifest.json").read_text())
    assert manifest["days"] == 1
    assert manifest["day_indices"] == [6]


def test_images_filename_dimensions_and_black_corners(tmp_path, config, day):
    from lionsim.plotting import render_reports
    from matplotlib.image import imread

    reports = build_reports(day, config)
    paths = render_reports(day, reports, config, tmp_path)
    assert len(paths) == 9
    pattern = r"\d{4}-\d{2}-\d{2}_\d{4}_day0001_report[1-8]\.png"
    for path in paths[:8]:
        assert re.fullmatch(pattern, path.name)
        pixels = imread(path)
        assert pixels.shape[:2] == (1000, 1000)
        assert np.all(pixels[0, 0, :3] == 0)
        assert np.all(pixels[-1, -1, :3] == 0)
    assert paths[6].name.startswith("2026-01-02_0200")
    assert paths[7].name.startswith("2026-01-02_0500")
    assert paths[8].name == "2026-01-01_day0001_contact_sheet.png"
    assert imread(paths[8]).shape[:2] == (4000, 2000)
