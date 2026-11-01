"""Deliberate corruptions and report-boundary contracts, independent of RNG."""

from dataclasses import replace

import pytest

from lionsim.config import load_config
from lionsim.events import TOKENS, serializable_events
from lionsim.reports import build_reports
from lionsim.simulator import simulate_day
from lionsim.validate import SummaryAccumulator, summarize_day, validate_day


@pytest.fixture(scope="module")
def sample():
    config = load_config()
    return config, simulate_day(config, seed=7)


def event(clock, token, zone=None, date="2026-01-01"):
    return {"t": f"{date}T{clock}", "token": token, "zone": zone}


def with_events(day, extras, wake="06:00:00"):
    initial = event(wake, "WOKE_UP", "Den")
    return replace(day, events=[initial, *extras],
                   latents={**day.latents, "wake_time": initial["t"], "start_hunger": 1.0, "hunt_threshold": 0.5})


@pytest.mark.parametrize(("extras", "fragment"), [
    ([event("18:00:20", "CATCH")], "immediately follow CHASE_START"),
    ([event("18:00:20", "FAIL")], "immediately follow CHASE_START"),
    ([event("18:00:00", "CHASE_START")], "no CATCH or FAIL"),
    ([event("18:00:00", "CHASE_START"), event("18:00:05", "GROOM"), event("18:00:30", "FAIL")], "immediately follow CHASE_START"),
    ([event("18:00:00", "CHASE_START"), event("18:00:05", "FAIL")], "outcome delay"),
    ([event("18:00:50", "CHASE_START"), event("18:01:10", "FAIL")], "different minute steps"),
    ([event("20:00:00", "EAT_START", "Feeding spot")], "preceding unused CATCH"),
    ([event("20:00:00", "EAT_END", "Feeding spot")], "preceding EAT_START"),
    ([event("07:00:00", "ENTER_PLAIN", "Plain"), event("07:01:00", "GROOM", "Plain"), event("07:02:00", "ENTER_PLAIN", "Plain")], "identical consecutive zone entry"),
    ([event("07:00:00", "ENTER_KOPJE", "Plain")], "inconsistent zone"),
    ([event("14:00:00", "FELL_ASLEEP", "Waterhole")], "forbidden zone"),
    ([event("14:00:00", "FELL_ASLEEP")], "forbidden zone"),
    ([event("14:00:00", "DRINK", "Plain")], "DRINK must occur"),
    ([event("16:30:00", "CAR_PASSED")], "unknown token"),
    ([event("22:00:00", "ENTER_HUNT", "Hunting ground")], "after the cutoff"),
    ([event("22:00:00", "CHASE_START", "Hunting ground")], "after the cutoff"),
    ([event("18:29:59", "ENTER_HUNT", "Hunting ground")], "outside the hunting window"),
    ([{"t": "2026-01-01T08:00:00", "token": "GROOM"}], "zone must be present"),
    ([event("08:00:00", "GROOM"), event("07:00:00", "GROOM")], "not sorted"),
    ([event("05:00:00", "GROOM", date="2026-01-02")], "outside the simulated day"),
    ([event("08:00:00", "INVALID")], "unknown token"),
    ([{"t": "not-an-iso-time", "token": "GROOM", "zone": None}], "invalid timestamp"),
])
def test_bad_events_fail_with_useful_errors(sample, extras, fragment):
    config, day = sample
    result = validate_day(with_events(day, extras), config)
    assert not result["valid"]
    assert any(fragment in error for error in result["errors"]), result["errors"]


@pytest.mark.parametrize("wake", ["04:59:59", "07:00:01"])
def test_initial_wake_time_limits(sample, wake):
    config, day = sample
    result = validate_day(with_events(day, [], wake=wake), config)
    assert not result["valid"]
    assert any("between 05:00 and 07:00" in error for error in result["errors"])


def test_traffic_context_does_not_interrupt_chase_pair(sample):
    config, day = sample
    day = with_events(day, [
        event("18:30:00", "CHASE_START", "Hunting ground"),
        event("18:30:30", "FAIL", "Hunting ground"),
        event("18:40:00", "CHASE_START", "Hunting ground"),
        event("18:40:30", "CATCH", "Hunting ground"),
        event("19:00:00", "ENTER_FEED", "Feeding spot"),
        event("19:00:10", "EAT_START", "Feeding spot"),
        event("20:00:00", "EAT_END", "Feeding spot"),
        event("20:00:01", "FELL_ASLEEP", "Feeding spot"),
    ])
    day.traffic_times = ["2026-01-01T18:30:12"]
    assert validate_day(day, config)["valid"]
    day.events.append(event("20:01:00", "GROOM", "Feeding spot"))
    assert any("after post-feeding sleep" in error for error in validate_day(day, config)["errors"])


def test_report_boundaries_include_events_exactly_once(sample):
    config, day = sample
    day = with_events(day, [
        event("08:00:00", "GROOM", "Den"),
        event("08:00:01", "GROOM", "Den"),
        event("11:00:00", "GROOM", "Den"),
    ], wake="05:00:00")
    reports = build_reports(day, config)
    public = serializable_events(day.events)
    assert reports[0]["new_events"] == public[:2]
    assert reports[1]["new_events"] == public[2:]
    assert [event for report in reports for event in report["new_events"]] == public
    assert day.gps.iloc[reports[0]["path_up_to_index"]]["t_iso"] == "2026-01-01T08:00:00"
    assert day.gps.iloc[reports[-1]["path_up_to_index"]]["t_iso"] == "2026-01-02T05:00:00"


def test_next_zone_uses_strictly_future_entries_and_explicit_none(sample):
    config, day = sample
    day = with_events(day, [
        event("08:00:00", "ENTER_PLAIN", "Plain"),
        event("08:00:01", "ENTER_KOPJE", "Kopje"),
        event("11:00:00", "ENTER_SHADE", "Shade"),
    ])
    records = [summarize_day(day, build_reports(day, config), validate_day(day, config), config)]
    second = replace(day, day_index=2)
    records.append(summarize_day(second, build_reports(second, config), validate_day(second, config), config))
    forward, reverse = SummaryAccumulator(config), SummaryAccumulator(config)
    for record in records:
        forward.add_record(record)
    for record in reversed(records):
        reverse.add_record(record)
    assert forward.summary() == reverse.summary()
    assert forward.validation_report() == reverse.validation_report()
    summary = forward.summary()
    assert set(summary["token_frequencies"]) == set(TOKENS)
    assert summary["chase_success_rate"] is None
    assert summary["next_zone_after_report_time"]["08:00"]["counts"]["ENTER_KOPJE"] == 2
    assert summary["next_zone_after_report_time"]["11:00"]["counts"]["END_OF_DAY"] == 2
    assert "05:00" not in summary["next_zone_after_report_time"]


def test_custom_reports_and_tourist_window_crossing_midnight(sample):
    _, base = sample
    config = load_config(overrides=[
        'time.report_times=["06:30","23:00","05:00"]',
        'tourists.start="23:00"', 'tourists.end="02:00"',
    ])
    day = with_events(base, [])
    day.traffic_times = ["2026-01-01T23:00:00", "2026-01-02T01:59:59"]
    assert validate_day(day, config)["valid"]
    reports = build_reports(day, config)
    assert [report["path_up_to_index"] for report in reports] == [90, 1080, 1440]
    assert [len(report["new_events"]) for report in reports] == [1, 0, 0]
    assert [report["traffic_count_since_last_report"] for report in reports] == [0, 1, 1]
    day.traffic_times.append("2026-01-02T02:00:00")
    assert any("outside the tourist window" in error for error in validate_day(day, config)["errors"])


def test_initial_hunger_determines_hunting_eligibility(sample):
    config, original = sample
    day = with_events(original, [event("19:00:00", "ENTER_HUNT", "Hunting ground")])
    day.latents.update(start_hunger=0.1, hunt_threshold=0.5)
    validation = validate_day(day, config)
    assert any("initial hunger" in error for error in validation["errors"])


def test_traffic_summary_uses_context_not_event_vocabulary(sample):
    config, original = sample
    day = with_events(original, [])
    day.traffic_times = ["2026-01-01T16:00:00", "2026-01-01T17:00:00"]
    accumulator = SummaryAccumulator(config)
    accumulator.add(day, build_reports(day, config), validate_day(day, config))
    summary = accumulator.summary()
    assert summary["tourist_car_counts"]["total"] == 2
    assert len(summary["token_frequencies"]) == 17
    assert "CAR_PASSED" not in summary["token_frequencies"]


def test_behaviour_budget_mismatch_warns_without_hiding_event_failures(sample):
    _, day = sample
    config = load_config(overrides=['validation.hours_ranges.resting=[23.0,24.0]'])
    day = with_events(day, [event("08:00:00", "FAIL")])
    accumulator = SummaryAccumulator(config)
    accumulator.add(day, build_reports(day, config), validate_day(day, config))
    report = accumulator.validation_report()
    assert not report["valid"]
    assert report["days_failed"] == 1
    assert report["days"][0]["errors"]
    assert any("sleeping/resting" in warning for warning in report["warnings"])
