"""Metric definitions and honest target diagnostics from controlled trajectories."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from lionsim.config import load_config
from lionsim.events import TOKENS, make_event
from lionsim.reports import END_OF_DAY, TARGET_CLASSES
from lionsim.stats import build_stats_report, render_stats_markdown, summarize_for_stats


def _day(index: int = 1):
    start = datetime(2026, 1, index, 5)
    # A right-angle route makes path length, speeds and tortuosity hand-checkable.
    xy = np.asarray([[0, 0], [0.03, 0], [0.03, 0.04], [0.06, 0.04], [0.06, 0.08]])
    events = [make_event(start, "WOKE_UP", "Den"),
              make_event(start, "ENTER_PLAIN", "Plain"),
              make_event(start + timedelta(minutes=2), "ENTER_SHADE", "Shade"),
              make_event(start + timedelta(minutes=3, seconds=5), "WOKE_UP", "Shade")]
    gps = pd.DataFrame({"t_iso": [(start + timedelta(minutes=i)).isoformat() for i in range(5)],
                        "minute_index": range(5), "x_true_km": xy[:, 0], "y_true_km": xy[:, 1],
                        "x_km": xy[:, 0] + np.array([0, .1, 0, .1, 0]), "y_km": xy[:, 1],
                        "missing": False})
    hidden = pd.DataFrame({"behaviour": ["walking", "walking", "drinking", "drinking"],
                           "zone": ["Plain", "Plain", "Shade", "Waterhole"],
                           "abandoned_trip_reason": [None, "temperature", "", None]})
    return SimpleNamespace(day_index=index, date=start.date().isoformat(), gps=gps,
                           hidden_state=hidden, events=events,
                           traffic_times=[(start + timedelta(minutes=1)).isoformat()],
                           latents={"start_hunger": .6, "hunt_threshold": .4, "heat": 1.,
                                    "prey_density": 1., "tourist_rate_per_hour": 5.})


def _reports(day):
    start = datetime.fromisoformat(day.gps.iloc[0].t_iso)
    return [{"report_index": 1, "report_time": (start + timedelta(minutes=1)).isoformat(),
             "current_zone": "Plain", "next_zone_target": "ENTER_SHADE"},
            {"report_index": 2, "report_time": (start + timedelta(minutes=4)).isoformat(),
             "current_zone": "Waterhole", "next_zone_target": END_OF_DAY},
            {"report_index": 8, "report_time": (start + timedelta(days=1)).isoformat(),
             "current_zone": "Waterhole"}]


def _record(index=1):
    config = load_config()
    day = _day(index)
    result = summarize_for_stats(day, _reports(day), config)
    result["validation"] = {"day_index": index, "valid": True, "errors": [], "warnings": []}
    return result


def test_true_path_speed_tortuosity_and_context_are_measured():
    config = load_config()
    day = _day()
    record = summarize_for_stats(day, _reports(day), config)
    path = record["path"]
    assert path["total_length_km"] == pytest.approx(.14)
    assert path["observed_total_length_km"] > path["total_length_km"]
    assert path["walking_distance_km"] == pytest.approx(.07)
    assert path["walking_minutes"] == 2
    assert path["mean_walking_speed_kmh"] == pytest.approx(2.1)
    assert path["tortuosity"] == pytest.approx(.07 / .05)
    assert path["map_coverage_fraction"] == pytest.approx(1 / 400)
    assert path["abandoned_trip_count"] == 1
    assert path["abandoned_trips_by_reason"] == {"temperature": 1}
    assert record["traffic_count"] == 1
    assert "CAR_PASSED" not in record["token_counts"]
    assert record["time_traces_minutes_after_start"]["shade_entry_time"] == 2
    assert record["time_traces_minutes_after_start"]["shade_exit_time"] == 3
    assert record["mean_drinking_bout_minutes"] == 2
    assert len(record["target_rows"]) == 2
    assert record["target_rows"][0]["last_event"] == "ENTER_PLAIN"
    json.dumps(record, allow_nan=False)


def test_grid_boundary_is_in_last_inside_cell_and_grid_size_is_configurable():
    config = load_config(overrides=["statistics.coverage_grid_km=1"])
    day = _day()
    day.gps.loc[:, "x_true_km"] = 10
    day.gps.loc[:, "y_true_km"] = 10
    record = summarize_for_stats(day, _reports(day), config)
    assert record["path"]["visited_grid_cells"] == 1
    assert record["path"]["total_grid_cells"] == 100
    assert record["path"]["map_coverage_fraction"] == .01


def test_no_walking_no_entries_no_chases_and_constant_correlations_use_null():
    day = _day()
    day.events = []
    day.hidden_state.loc[:, "behaviour"] = "sleeping"
    record = summarize_for_stats(day, [], load_config())
    assert record["path"]["mean_walking_speed_kmh"] is None
    assert record["path"]["tortuosity"] is None
    report = build_stats_report([record], load_config())
    assert report["chase_success_rate"] is None
    assert report["correlations"]["start_hunger_vs_hunting_day"]["value"] is None
    assert report["time_distributions"]["first_chase_time"]["missing"] == 1
    assert report["time_distributions"]["first_chase_time"]["mean"] is None
    json.dumps(report, allow_nan=False)


def test_report_has_all_required_sections_and_all_seventeen_tokens():
    report = build_stats_report([_record()], load_config())
    assert set(report) >= {"events_per_day", "zone_entries_per_day", "token_frequencies", "zone_entry_shares",
                           "day_fractions", "chase_success_rate", "hours_per_behaviour", "behaviour_comparison",
                           "time_distributions", "sequence_diversity", "path_statistics",
                           "next_zone_target_balance", "correlations", "checks", "check_counts"}
    assert len(report["token_frequencies"]) == 17
    assert set(report["token_frequencies"]) == set(TOKENS)
    assert set(report["day_fractions"]) == {"any_chase", "catch", "feast", "enter_road", "enter_hunt", "enter_water"}
    assert set(report["next_zone_target_balance"]["by_report_index"]) == {str(i) for i in range(1, 8)}
    assert set(report["next_zone_target_balance"]["overall"]["counts"]) == set(TARGET_CLASSES)
    assert report["next_zone_target_balance"]["overall"]["counts"]["END_OF_DAY"] == 1
    assert report["next_zone_target_balance"]["overall"]["observations"] == 2
    markdown = render_stats_markdown(report)
    for text in ("Target checks", "Behaviour hours", "Time distributions", "zone-sequence diversity",
                 "Path statistics", "Next-zone target class balance", "correlations", "WARN", "PASS"):
        assert text in markdown
    assert "L0" not in markdown and "oracle log loss" not in markdown


def test_aggregation_is_order_independent_and_walking_speed_is_time_weighted():
    short = _record(1)
    long = _record(2)
    long["path"]["walking_minutes"] = 10
    long["path"]["walking_distance_km"] = .5
    long["path"]["mean_walking_speed_kmh"] = 3.
    left = build_stats_report([short, long], load_config())
    right = build_stats_report([long, short], load_config())
    assert left == right
    assert left["path_statistics"]["pooled_mean_walking_speed_kmh"] == pytest.approx((.07 + .5) / 12 * 60)
    assert left["path_statistics"]["aggregates"]["mean_walking_speed_kmh"]["mean"] == pytest.approx(2.55)
    with pytest.raises(ValueError, match="duplicate"):
        build_stats_report([short, short], load_config())


def test_diversity_counts_sequences_and_pearson_uses_daily_pairs():
    records = [_record(index) for index in range(1, 7)]
    for index, record in enumerate(records):
        record["latents"]["start_hunger"] = index / 6
        record["latents"]["heat"] = .7 + index / 10
        record["day_flags"]["any_chase"] = index >= 3
        record["traffic_count"] = index
        record["zone_entry_counts"]["Road"] = 5 - index
        record["time_traces_minutes_after_start"]["shade_entry_time"] = 300 - index * 10
        record["zone_sequence"] = ["ENTER_PLAIN"] * (index + 1)
    report = build_stats_report(records, load_config())
    diversity = report["sequence_diversity"]
    assert diversity["unique_daily_sequence_fraction"] == 1.
    assert diversity["top_five_sequence_share"] == pytest.approx(5 / 6)
    assert diversity["length_counts"] == {str(i): 1 for i in range(1, 7)}
    assert report["correlations"]["heat_vs_shade_entry_time"]["value"] == pytest.approx(-1.)
    assert report["correlations"]["tourist_volume_vs_road_entries"]["value"] == pytest.approx(-1.)
    assert report["correlations"]["start_hunger_vs_hunting_day"]["value"] > .8


def test_target_statuses_distinguish_statistical_warnings_from_invalid_data():
    record = _record()
    record["validation"] = {"day_index": 1, "valid": False, "errors": ["bad event"], "warnings": []}
    report = build_stats_report([record], load_config())
    checks = {check["name"]: check for check in report["checks"]}
    assert checks["event_invariants"]["status"] == "FAIL"
    assert checks["zone_entries_per_day"]["status"] == "WARN"
    assert checks["zone_entry_share.Road"]["status"] == "WARN"
    assert checks["mean_walking_speed_kmh"]["status"] == "PASS"
    assert report["validation"]["days_failed"] == 1
    assert report["check_counts"]["FAIL"] >= 1


def test_road_share_uses_its_own_phase_two_range():
    record = _record()
    record["zone_entry_counts"] = {"Den": 99, "Road": 1}
    report = build_stats_report([record], load_config())
    check = next(check for check in report["checks"] if check["name"] == "zone_entry_share.Road")
    assert check["observed"] == .01
    assert check["status"] == "WARN"


def test_empty_report_and_next_day_clock_format_are_json_safe():
    report = build_stats_report([], load_config())
    assert report["days_simulated"] == 0
    assert report["check_counts"]["FAIL"] > 0
    json.dumps(report, allow_nan=False)
    record = _record()
    record["time_traces_minutes_after_start"]["first_chase_time"] = 1200
    report = build_stats_report([record], load_config())
    assert report["time_distributions"]["first_chase_time"]["clock_times"]["mean"] == "25:00:00"


def test_five_minute_rest_smoothing_reduces_stationary_observation_noise():
    from lionsim.simulator import simulate_day
    day = simulate_day(load_config(), seed=42)
    day.hidden_state.loc[:, 'behaviour'] = 'resting'
    rng = np.random.default_rng(42)
    xy = rng.normal(0, .008, (len(day.gps), 2))
    day.gps.loc[:, ['x_true_km','y_true_km']] = 0.
    day.gps.loc[:, ['x_km','y_km']] = xy
    record = summarize_for_stats(day, [], load_config())
    raw = record['path']['raw_rest_apparent_speed_kmh']
    smooth = record['path']['smoothed_rest_apparent_speed_kmh']
    assert .6 < raw < 1.1
    assert 0 < smooth < raw / 3
    assert record['path']['observed_true_path_ratio'] is None
    day.hidden_state.loc[:, 'behaviour'] = 'walking'
    none = summarize_for_stats(day, [], load_config())
    assert none['path']['smoothed_rest_apparent_speed_kmh'] is None
