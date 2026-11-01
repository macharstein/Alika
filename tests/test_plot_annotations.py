"""PNG reports contain only zones and the GPS prefix available at that time."""

from __future__ import annotations

import copy

import numpy as np
import pytest
from matplotlib.image import imread
from matplotlib.figure import Figure
from matplotlib.text import Text

from lionsim.config import load_config
from lionsim.plotting import render_reports
from lionsim.reports import build_reports
from lionsim.simulator import simulate_day


@pytest.fixture(scope="module")
def config():
    return load_config()


@pytest.fixture(scope="module")
def day(config):
    return simulate_day(config, seed=42)


def test_pngs_have_only_filled_zones_path_and_endpoint(tmp_path, monkeypatch, config, day):
    reports = build_reports(day, config)
    savefig = Figure.savefig
    inspected = []

    def inspect_and_save(figure, *args, **kwargs):
        assert len(figure.axes) == 1
        axis = figure.axes[0]
        assert not any(text.get_text() for text in figure.findobj(Text))
        assert not axis.axison
        assert axis.get_legend() is None
        assert axis.get_xlim() == (0, config["map"]["width_km"])
        assert axis.get_ylim() == (0, config["map"]["height_km"])
        assert axis.get_aspect() == 1
        assert len(axis.patches) == 8  # Filled zones, with no arrow patches.
        assert len(axis.lines) == 1  # One uniformly styled cumulative path.
        assert len(axis.collections) == 1  # The only dot marks the endpoint.
        report = reports[len(inspected)]
        last = report["path_up_to_index"]
        np.testing.assert_array_equal(axis.lines[0].get_xdata(), day.gps["x_km"][:last + 1])
        np.testing.assert_array_equal(axis.lines[0].get_ydata(), day.gps["y_km"][:last + 1])
        np.testing.assert_array_equal(axis.collections[0].get_offsets(),
                                      [[day.gps.iloc[last]["x_km"], day.gps.iloc[last]["y_km"]]])
        inspected.append(last)
        return savefig(figure, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", inspect_and_save)
    paths = render_reports(day, reports, config, tmp_path)
    assert inspected == list(range(180, 1441, 180))
    assert len(paths) == 9
    assert paths[6].name.startswith("2026-01-02_0200")


def test_report_pixels_ignore_events_hidden_state_and_future_gps(tmp_path, config, day):
    report = build_reports(day, config)[0]
    original = render_reports(day, [report], config, tmp_path / "original")[0]
    modified = copy.deepcopy(day)
    last = report["path_up_to_index"]
    modified.gps.loc[last + 1:, ["x_km", "y_km"]] = 9.8
    modified.gps = modified.gps[["x_km", "y_km"]]
    modified.events = None
    modified.hidden_state = None
    modified_report = {"path_up_to_index": last, "report_index": 8,
                       "report_time": "2030-02-10T23:59:00"}
    changed = render_reports(modified, [modified_report], config, tmp_path / "modified")[0]
    assert original.read_bytes() == changed.read_bytes()


def test_legacy_annotation_options_cannot_add_pixels(tmp_path, config, day):
    report = build_reports(day, config)[0]
    original = render_reports(day, [report], config, tmp_path / "original")[0]
    legacy = copy.deepcopy(config)
    legacy["images"].update({"annotation_mode": "annotated", "mark_new_events": True,
                             "highlight_recent_segment": True, "label_color": "#FF0000",
                             "label_fontsize": 40, "timestamp_fontsize": 40,
                             "time_label_interval_minutes": 1, "arrow_interval_minutes": 1})
    changed = render_reports(day, [report], legacy, tmp_path / "legacy")[0]
    assert original.read_bytes() == changed.read_bytes()


def test_contact_sheet_is_exact_report_tiles_without_added_text(tmp_path, config, day):
    reports = build_reports(day, config)
    paths = render_reports(day, reports, config, tmp_path)
    sheet = imread(paths[-1])
    assert sheet.shape[:2] == (4000, 2000)
    for index, path in enumerate(paths[:-1]):
        pixels = imread(path)
        assert pixels.shape[:2] == (1000, 1000)
        assert np.all(pixels[0, 0, :3] == 0)
        assert np.all(pixels[-1, -1, :3] == 0)
        row, column = divmod(index, 2)
        np.testing.assert_array_equal(sheet[row * 1000:(row + 1) * 1000,
                                             column * 1000:(column + 1) * 1000], pixels)
