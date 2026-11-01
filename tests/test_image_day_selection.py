"""Regressions for rendering every day unless the CLI explicitly limits images."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import lionsim.run as runner


@pytest.mark.parametrize(
    ("image_args", "expected_image_days"),
    [
        ([], 6),
        (["--image-days", "2"], 2),
        (["--image-days", "2", "--no-images"], 0),
    ],
    ids=["all-six-days-by-default", "explicit-first-two-days", "no-images-takes-precedence"],
)
def test_cli_writes_images_for_exactly_the_selected_days(tmp_path, image_args, expected_image_days):
    command = [
        sys.executable, "-m", "lionsim.run", "--days", "6", "--out", str(tmp_path),
        "--set", "images.size_px=128", "--set", "images.dpi=64",
        "--set", "output.prefer_parquet=false", *image_args,
    ]
    completed = subprocess.run(
        command, cwd=Path(__file__).resolve().parents[1],
        capture_output=True, text=True, timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    directory, = tmp_path.glob("run_*")
    manifest = json.loads((directory / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "complete"
    assert manifest["image_days"] == expected_image_days
    assert len(list(directory.rglob("*.png"))) == expected_image_days * 9
    for day_index in range(1, 7):
        day_directory = directory / "days" / f"day_{day_index:04d}"
        assert (day_directory / "day.json").is_file()
        images_directory = day_directory / "images"
        if day_index <= expected_image_days:
            reports = sorted(images_directory.glob("*_report*.png"))
            assert len(reports) == 8
            assert {int(path.stem.rsplit("report", 1)[1]) for path in reports} == set(range(1, 9))
            assert len(list(images_directory.glob("*_contact_sheet.png"))) == 1
            assert all(path.stat().st_size > 0 for path in images_directory.glob("*.png"))
        else:
            assert not images_directory.exists()


@pytest.mark.parametrize(
    ("cli_args", "expected_indices", "expected_render_count"),
    [
        (["--days", "200"], list(range(1, 201)), 200),
        (["--days", "200", "--image-days", "2"], list(range(1, 201)), 2),
        (["--days", "200", "--image-days", "250"], list(range(1, 201)), 200),
        (["--days", "200", "--image-days", "0"], list(range(1, 201)), 0),
        (["--days", "200", "--image-days", "2", "--no-images"], list(range(1, 201)), 0),
        (["--day-index", "200"], [200], 1),
    ],
    ids=["all-200-days", "explicit-limit", "limit-clamped-to-count", "explicit-zero",
         "disabled-overrides-limit", "standalone-day-200"],
)
def test_large_run_schedules_all_image_jobs_by_default(
    tmp_path, monkeypatch, cli_args, expected_indices, expected_render_count,
):
    captured_jobs = []

    def capture_jobs(jobs, workers):
        captured_jobs.extend(jobs)
        return iter(())

    # Inspect scheduling without generating hundreds of images in the test suite.
    # The CLI test above also exercises real day serialization and rendering.
    monkeypatch.setattr(runner, "_stream_jobs", capture_jobs)
    args = runner.build_parser().parse_args(["--out", str(tmp_path), *cli_args])
    directory = runner.run(args)
    assert [job["day_index"] for job in captured_jobs] == expected_indices
    assert [job["render"] for job in captured_jobs] == [
        index < expected_render_count for index in range(len(expected_indices))
    ]
    manifest = json.loads((directory / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["image_days"] == expected_render_count


def test_legacy_automatic_image_cap_does_not_reduce_the_default(tmp_path, monkeypatch):
    legacy_config = tmp_path / "legacy_config.json"
    legacy_config.write_text(json.dumps({
        "images": {"automatic_all_days_threshold": 5, "automatic_image_days": 5},
    }), encoding="utf-8")
    captured_jobs = []

    def capture_jobs(jobs, workers):
        captured_jobs.extend(jobs)
        return iter(())

    monkeypatch.setattr(runner, "_stream_jobs", capture_jobs)
    args = runner.build_parser().parse_args([
        "--days", "200", "--config", str(legacy_config), "--out", str(tmp_path / "output"),
    ])
    runner.run(args)
    assert len(captured_jobs) == 200
    assert all(job["render"] for job in captured_jobs)
