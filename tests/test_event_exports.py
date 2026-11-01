"""Public event schema, restored daily payloads, traffic, and target contracts."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta

import pandas as pd
import pytest

from lionsim.config import load_config
from lionsim.events import TOKENS, describe_event, make_event, serializable_events
from lionsim.io_utils import write_day
from lionsim.reports import END_OF_DAY, build_reports, target_rows
from lionsim.simulator import simulate_day


@pytest.fixture(scope="module")
def simulated_day():
    config = load_config()
    return config, simulate_day(config, seed=42)


def test_all_seventeen_events_have_descriptions_and_zone_context():
    start = datetime(2026, 1, 1, 5)
    events = [make_event(start + timedelta(seconds=i), token, "Den")
              for i, token in enumerate(TOKENS)]
    records = serializable_events(events)
    assert len(records) == 17
    assert "CAR_PASSED" not in TOKENS
    assert END_OF_DAY not in TOKENS
    assert [record["id"] for record in records] == [f"E{i:03d}" for i in range(1, 18)]
    assert [record["token"] for record in records] == list(TOKENS)
    assert len({record["description"] for record in records}) == 17
    for record in records:
        assert set(record) == {"id", "t", "token", "description", "zone"}
        assert record["description"].endswith(".")
        assert "_" not in record["description"]
        assert record["zone"] == "Den"
    assert "without a catch" in describe_event({"token": "FAIL"})
    for token in ("CAR_PASSED", END_OF_DAY, "NOT_AN_EVENT"):
        with pytest.raises(ValueError, match="Unknown collar event token"):
            make_event(start, token, None)


def test_export_stable_chronology_and_null_zone_without_mutation():
    events = [
        {"t": "2026-01-01T08:00:00", "token": "GROOM", "zone": None},
        {"t": "2026-01-01T05:00:00", "token": "WOKE_UP", "zone": "Den"},
        {"t": "2026-01-01T08:00:00", "token": "FELL_ASLEEP", "zone": "Den"},
    ]
    original = copy.deepcopy(events)
    records = serializable_events(events)
    assert [record["token"] for record in records] == ["WOKE_UP", "GROOM", "FELL_ASLEEP"]
    assert [record["id"] for record in records] == ["E001", "E002", "E003"]
    assert records[1]["zone"] is None
    assert events == original


def test_restored_day_json_keeps_hidden_bars_outside_payload(tmp_path, simulated_day):
    config, day = simulated_day
    events_before = copy.deepcopy(day.events)
    reports = build_reports(day, config)
    payload = write_day(day, reports, tmp_path, prefer_parquet=False)
    document = (tmp_path / "day.json").read_text(encoding="utf-8")
    assert json.loads(document) == payload
    assert set(payload) == {"day_index", "date", "events", "reports", "ground_truth_latents"}
    assert payload["day_index"] == day.day_index
    assert payload["date"] == day.date
    assert payload["events"] == serializable_events(day.events)
    assert payload["reports"] == reports
    assert payload["ground_truth_latents"]["_analysis_only"] is True
    assert payload["ground_truth_latents"]["tourist_volume"] == len(day.traffic_times)
    for key, value in day.latents.items():
        assert payload["ground_truth_latents"][key] == value
    assert not {"hunger", "energy", "temperature", "mood", "boredom", "hidden_state"} & payload.keys()
    assert all("path" not in report for report in reports)
    assert "CAR_PASSED" not in document
    assert document.endswith("\n")
    assert day.events == events_before
    pd.testing.assert_frame_equal(pd.read_csv(tmp_path / "gps.csv.gz"), day.gps,
                                  check_dtype=False, check_exact=False)
    assert len(pd.read_csv(tmp_path / "hidden_state.csv.gz")) == len(day.hidden_state)


def test_reports_share_public_event_ids_and_default_compact_paths(simulated_day):
    config, day = simulated_day
    reports = build_reports(day, config)
    public = serializable_events(day.events)
    assert [event for report in reports for event in report["new_events"]] == public
    assert [report["path_up_to_index"] for report in reports] == list(range(180, 1441, 180))
    assert all("path" not in report for report in reports)
    assert all(report["new_events"] == [
        event for event in public
        if (index == 0 or event["t"] > reports[index - 1]["report_time"])
        and event["t"] <= report["report_time"]
    ] for index, report in enumerate(reports))
    assert all("next_zone_target" in report for report in reports[:-1])
    assert "next_zone_target" not in reports[-1]
    assert "time_to_next_zone_min" not in reports[-1]


def test_optional_cumulative_paths_contain_observed_coordinates(simulated_day):
    _, day = simulated_day
    config = load_config(overrides=["output.embed_cumulative_path_in_reports=true"])
    reports = build_reports(day, config)
    assert [len(report["path"]) for report in reports] == list(range(181, 1442, 180))
    for report in reports:
        last = day.gps.iloc[report["path_up_to_index"]]
        assert report["path"][-1] == [last["t_iso"], last["x_km"], last["y_km"]]


def test_traffic_is_context_with_exact_window_boundaries(simulated_day):
    _, original = simulated_day
    config = load_config(overrides=['time.report_times=["17:00","19:00","05:00"]'])
    day = copy.copy(original)
    day.traffic_times = [f"2026-01-01T{time}" for time in
                         ("16:00:00", "16:00:01", "17:00:00", "17:00:01", "18:59:59")]
    reports = build_reports(day, config)
    assert [r["traffic_count_since_last_report"] for r in reports] == [3, 2, 0]
    assert [r["traffic_count_last_hour"] for r in reports] == [2, 1, 0]
    assert not any(e["token"] == "CAR_PASSED" for r in reports for e in r["new_events"])


def test_target_is_strictly_future_same_day_and_final_report_is_excluded(simulated_day):
    config, original = simulated_day
    day = copy.copy(original)
    day.events = [
        make_event(datetime(2026, 1, 1, 6), "WOKE_UP", "Den"),
        make_event(datetime(2026, 1, 1, 8), "ENTER_PLAIN", "Plain"),
        make_event(datetime(2026, 1, 1, 8, 0, 30), "ENTER_KOPJE", "Kopje"),
        make_event(datetime(2026, 1, 1, 11), "ENTER_SHADE", "Shade"),
    ]
    reports = build_reports(day, config)
    assert reports[0]["next_zone_target"] == "ENTER_KOPJE"
    assert reports[0]["time_to_next_zone_min"] == 0.5
    assert reports[1]["next_zone_target"] == END_OF_DAY
    assert reports[1]["time_to_next_zone_min"] is None
    rows = target_rows(day, reports)
    assert len(rows) == 7
    assert set(rows[0]) == {"day", "report_index", "report_time_bucket", "current_zone", "last_event", "next_zone_target"}
    assert rows[0]["last_event"] == "ENTER_PLAIN"
    assert rows[0]["report_time_bucket"] == "08:00"
    assert rows[-1]["report_time_bucket"] == "02:00"
    assert rows[-1]["next_zone_target"] == END_OF_DAY


def test_next_day_entry_cannot_be_used_as_a_same_day_target(simulated_day):
    config, original = simulated_day
    day = copy.copy(original)
    day.events = [make_event(datetime(2026, 1, 2, 5, 0, 1), "ENTER_PLAIN", "Plain")]
    reports = build_reports(day, config)
    assert all(r["next_zone_target"] == END_OF_DAY for r in reports[:-1])
    assert all(r["new_events"] == [] for r in reports)
