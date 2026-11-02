"""Descriptive signal/noise diagnostics from compact, resumable daily records.

This module uses only counting tables for diagnostic prediction baselines. It measures the generated data and
compares transparent statistics with configured reference ranges. All geometry
metrics use noise-free positions; an observed-path length is reported separately.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import math
from typing import Any, Iterable

import numpy as np

from .config import Config
from .events import TOKENS, ZONE_TOKENS
from .reports import TARGET_CLASSES, target_rows


BEHAVIOURS = ("sleeping", "resting", "walking", "hunting", "grooming", "eating", "drinking")
TIME_TRACES = ("wake_time", "shade_entry_time", "shade_exit_time",
               "waterhole_arrival_time", "first_chase_time", "shade_wake_time")


def _finite(value: Any) -> float | None:
    """Convert numeric results to strict JSON numbers, never NaN or Infinity."""
    if value is None:
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _distribution(values: Iterable[Any], total: int | None = None) -> dict[str, Any]:
    finite = [number for value in values if (number := _finite(value)) is not None]
    array = np.asarray(finite, dtype=float)
    result: dict[str, Any] = {"count": len(array), "missing": max(0, (total or len(array)) - len(array))}
    if not len(array):
        return {**result, **dict.fromkeys(("mean", "std", "min", "p05", "median", "p95", "max"))}
    result.update(mean=float(array.mean()), std=float(array.std()), min=float(array.min()),
                  p05=float(np.quantile(array, 0.05)), median=float(np.median(array)),
                  p95=float(np.quantile(array, 0.95)), max=float(array.max()))
    return result


def _clock_label(minutes_after_start: float | None, start_clock: str) -> str | None:
    if minutes_after_start is None:
        return None
    hours, minutes = map(int, start_clock.split(":"))
    seconds = int(round((hours * 60 + minutes + minutes_after_start) * 60))
    # Hours 24..29 explicitly represent the next calendar morning.
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def _first_event_minute(events: list[dict[str, Any]], token: str,
                        start: datetime, *, zone: str | None = None,
                        after: float | None = None) -> float | None:
    for event in events:
        if event["token"] != token or zone is not None and event.get("zone") != zone:
            continue
        minute = (datetime.fromisoformat(event["t"]) - start).total_seconds() / 60
        if after is None or minute > after:
            return minute
    return None


def _run_lengths(values: np.ndarray, wanted: str) -> list[int]:
    lengths: list[int] = []
    current = 0
    for value in values:
        if value == wanted:
            current += 1
        elif current:
            lengths.append(current)
            current = 0
    if current:
        lengths.append(current)
    return lengths


def summarize_for_stats(day: Any, reports: list[dict[str, Any]], config: Config) -> dict[str, Any]:
    """Reduce one day to JSON primitives before discarding its minute tables.

    The caller can attach ``record['validation']`` to reuse its already-computed
    invariant result. No DataFrame or full coordinate array is retained here.
    """
    start = datetime.fromisoformat(f"{day.date}T{config['time']['day_start']}:00")
    events = sorted(day.events, key=lambda event: event["t"])
    token_counts = Counter(event["token"] for event in events)
    entries = [event for event in events if event["token"] in ZONE_TOKENS.values()]
    token_to_zone = {token: zone for zone, token in ZONE_TOKENS.items()}
    behaviour = day.hidden_state["behaviour"].to_numpy()
    minute_counts = Counter(str(value) for value in behaviour)
    true_xy = day.gps[["x_true_km", "y_true_km"]].to_numpy(dtype=float)
    observed_xy = day.gps[["x_km", "y_km"]].to_numpy(dtype=float)
    true_steps = np.linalg.norm(np.diff(true_xy, axis=0), axis=1)
    observed_steps = np.linalg.norm(np.diff(observed_xy, axis=0), axis=1)
    resting = np.isin(behaviour[:len(observed_steps)], ("sleeping", "resting"))
    width = config["statistics"]["rest_smoothing_minutes"]
    if len(resting) >= width:
        smooth_rest = np.convolve(resting.astype(int), np.ones(width, dtype=int), mode="valid") == width
        smooth_steps = np.linalg.norm(observed_xy[width:] - observed_xy[:-width], axis=1) / width
        smooth_distance = float(smooth_steps[smooth_rest].sum())
        smooth_minutes = int(smooth_rest.sum())
    else:
        smooth_distance, smooth_minutes = 0.0, 0
    raw_rest_distance = float(observed_steps[resting].sum())
    rest_minutes = int(resting.sum())
    walking = behaviour[:len(true_steps)] == "walking"
    walking_distance = float(true_steps[:len(walking)][walking].sum())
    walking_minutes = int(walking.sum())

    entry_indices = [max(0, min(len(true_xy) - 1,
                     int((datetime.fromisoformat(event["t"]) - start).total_seconds() // 60)))
                     for event in entries]
    arc_total = chord_total = 0.0
    segment_ratios: list[float] = []
    for begin, end in zip(entry_indices[:-1], entry_indices[1:]):
        chord = float(np.linalg.norm(true_xy[end] - true_xy[begin]))
        if end <= begin or chord <= np.finfo(float).eps:
            continue
        arc = float(true_steps[begin:end].sum())
        arc_total += arc
        chord_total += chord
        segment_ratios.append(arc / chord)
    grid_km = config["statistics"]["coverage_grid_km"]
    grid_shape = np.ceil(np.asarray([config["map"]["width_km"], config["map"]["height_km"]]) / grid_km).astype(int)
    finite_xy = true_xy[np.isfinite(true_xy).all(axis=1)]
    cells = np.floor(finite_xy / grid_km).astype(int)
    cells = np.clip(cells, 0, grid_shape - 1)
    visited = len(np.unique(cells, axis=0)) if len(cells) else 0
    cell_count = int(np.prod(grid_shape))

    abandoned: Counter[str] = Counter()
    if "abandoned_trip_reason" in day.hidden_state:
        for value in day.hidden_state["abandoned_trip_reason"]:
            if isinstance(value, str) and value.strip():
                abandoned[value] += 1
    shade_entry = _first_event_minute(events, "ENTER_SHADE", start)
    shade_exit: float | None = None
    if shade_entry is not None and "zone" in day.hidden_state:
        first_index = math.ceil(shade_entry)
        for index in range(first_index, len(day.hidden_state)):
            if day.hidden_state.iloc[index]["zone"] != "Shade":
                shade_exit = float(index)
                break
    traces = {
        "wake_time": _first_event_minute(events, "WOKE_UP", start),
        "shade_entry_time": shade_entry,
        "shade_exit_time": shade_exit,
        "waterhole_arrival_time": _first_event_minute(events, "ENTER_WATER", start),
        "first_chase_time": _first_event_minute(events, "CHASE_START", start),
        "shade_wake_time": (_first_event_minute(events, "WOKE_UP", start,
                              zone="Shade", after=shade_entry) if shade_entry is not None else None),
    }
    drinking_runs = _run_lengths(behaviour, "drinking")
    traffic_count = len(getattr(day, "traffic_times", []))
    return {
        "day_index": int(day.day_index), "date": day.date,
        "event_count": len(events), "token_counts": dict(token_counts),
        "zone_entry_count": len(entries),
        "zone_entry_counts": dict(Counter(token_to_zone[event["token"]] for event in entries)),
        "zone_sequence": [event["token"] for event in entries],
        "behaviour_minutes": {name: int(minute_counts[name]) for name in BEHAVIOURS},
        "day_flags": {
            "any_chase": token_counts["CHASE_START"] > 0,
            "catch": token_counts["CATCH"] > 0,
            "feast": token_counts["EAT_START"] > 0,
            "enter_road": token_counts["ENTER_ROAD"] > 0,
            "enter_hunt": token_counts["ENTER_HUNT"] > 0,
        },
        "time_traces_minutes_after_start": traces,
        "mean_drinking_bout_minutes": float(np.mean(drinking_runs)) if drinking_runs else None,
        "path": {
            "total_length_km": _finite(true_steps.sum()),
            "observed_total_length_km": _finite(observed_steps.sum()),
            "observed_true_path_ratio": _finite(observed_steps.sum() / true_steps.sum()) if true_steps.sum() else None,
            "raw_rest_apparent_speed_kmh": raw_rest_distance * 60 / rest_minutes if rest_minutes else None,
            "smoothed_rest_apparent_speed_kmh": smooth_distance * 60 / smooth_minutes if smooth_minutes else None,
            "raw_rest_distance_km": raw_rest_distance, "rest_minutes": rest_minutes,
            "smoothed_rest_distance_km": smooth_distance, "smoothed_rest_minutes": smooth_minutes,
            "walking_distance_km": _finite(walking_distance),
            "walking_minutes": walking_minutes,
            "mean_walking_speed_kmh": _finite(walking_distance * 60 / walking_minutes) if walking_minutes else None,
            "tortuosity": _finite(arc_total / chord_total) if chord_total else None,
            "tortuosity_segment_count": len(segment_ratios),
            "map_coverage_fraction": visited / cell_count,
            "visited_grid_cells": visited, "total_grid_cells": cell_count,
            "abandoned_trip_count": sum(abandoned.values()),
            "abandoned_trips_by_reason": dict(abandoned),
        },
        "latents": {key: _finite(day.latents.get(key)) for key in (
            "start_hunger", "hunt_threshold", "heat", "prey_density", "tourist_rate_per_hour")},
        "traffic_count": traffic_count,
        "target_rows": target_rows(day, reports),
    }


def _correlation(pairs: Iterable[tuple[Any, Any]]) -> dict[str, Any]:
    valid = [(float(x), float(y)) for x, y in pairs
             if _finite(x) is not None and _finite(y) is not None]
    if len(valid) < 2:
        return {"value": None, "count": len(valid), "reason": "Fewer than two paired observations."}
    array = np.asarray(valid)
    if np.ptp(array[:, 0]) == 0 or np.ptp(array[:, 1]) == 0:
        return {"value": None, "count": len(valid), "reason": "At least one variable is constant."}
    value = _finite(np.corrcoef(array[:, 0], array[:, 1])[0, 1])
    return {"value": value, "count": len(valid), "reason": None if value is not None else "Non-finite correlation."}


def _balance(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(row["next_zone_target"] for row in rows)
    total = sum(counts.values())
    classes = list(TARGET_CLASSES)
    for label in counts:
        if label not in classes:
            classes.append(label)
    return {"observations": total,
            "counts": {label: int(counts[label]) for label in classes},
            "fractions": {label: counts[label] / total if total else 0.0 for label in classes}}


def build_stats_report(records: Iterable[dict[str, Any]], config: Config) -> dict[str, Any]:
    """Aggregate compact day records deterministically, with explicit checks."""
    days = sorted(records, key=lambda record: record["day_index"])
    count = len(days)
    if len({record["day_index"] for record in days}) != count:
        raise ValueError("Statistics contain duplicate day indices")
    token_counts: Counter[str] = Counter({token: 0 for token in TOKENS})
    zone_names = list(ZONE_TOKENS)
    zone_counts: Counter[str] = Counter({name: 0 for name in zone_names})
    minutes: Counter[str] = Counter({name: 0 for name in BEHAVIOURS})
    sequences: Counter[tuple[str, ...]] = Counter()
    rows: list[dict[str, Any]] = []
    for record in days:
        token_counts.update(record["token_counts"])
        zone_counts.update(record["zone_entry_counts"])
        minutes.update(record["behaviour_minutes"])
        sequences[tuple(record["zone_sequence"])] += 1
        rows.extend(record["target_rows"])
    total_entries = sum(zone_counts.values())
    entry_shares = {name: zone_counts[name] / total_entries if total_entries else 0.0 for name in zone_names}
    fractions = {flag: sum(bool(record["day_flags"][flag]) for record in days) / count if count else None
                 for flag in ("any_chase", "catch", "feast", "enter_road", "enter_hunt")}
    hours = {name: minutes[name] / (count * 60) if count else None for name in BEHAVIOURS}
    hours["sleeping_resting"] = ((minutes["sleeping"] + minutes["resting"]) / (count * 60) if count else None)
    traces = {}
    for name in TIME_TRACES:
        summary = _distribution((record["time_traces_minutes_after_start"].get(name) for record in days), count)
        summary["unit"] = "minutes_after_day_start"
        summary["clock_times"] = {key: _clock_label(summary[key], config["time"]["day_start"])
                                  for key in ("mean", "min", "p05", "median", "p95", "max")}
        traces[name] = summary
    ordered_sequences = sorted(sequences.items(), key=lambda item: (-item[1], item[0]))
    unique_fraction = len(sequences) / count if count else None
    top_five_share = sum(frequency for _, frequency in ordered_sequences[:5]) / count if count else None
    sequence_lengths = Counter(len(record["zone_sequence"]) for record in days)
    path_keys = ("total_length_km", "observed_total_length_km", "mean_walking_speed_kmh",
                 "tortuosity", "map_coverage_fraction", "abandoned_trip_count",
                 "observed_true_path_ratio", "raw_rest_apparent_speed_kmh", "smoothed_rest_apparent_speed_kmh")
    path_aggregates = {key: _distribution((record["path"].get(key) for record in days), count) for key in path_keys}
    walking_minutes = sum(record["path"]["walking_minutes"] for record in days)
    walking_distance = sum(record["path"]["walking_distance_km"] or 0.0 for record in days)
    pooled_speed = walking_distance * 60 / walking_minutes if walking_minutes else None
    true_length = sum(r["path"]["total_length_km"] or 0 for r in days)
    observed_length = sum(r["path"]["observed_total_length_km"] or 0 for r in days)
    gps_metrics = {"observed_true_path_ratio": observed_length / true_length if true_length else None}
    for name, distance, duration in (("raw_rest_apparent_speed_kmh", "raw_rest_distance_km", "rest_minutes"),
                                     ("smoothed_rest_apparent_speed_kmh", "smoothed_rest_distance_km", "smoothed_rest_minutes")):
        total_minutes = sum(r["path"].get(duration, 0) for r in days)
        gps_metrics[name] = sum(r["path"].get(distance, 0) for r in days) * 60 / total_minutes if total_minutes else None
    reason_counts: Counter[str] = Counter()
    for record in days:
        reason_counts.update(record["path"]["abandoned_trips_by_reason"])
    correlations = {
        "start_hunger_vs_hunting_day": _correlation((record["latents"]["start_hunger"], int(record["day_flags"]["any_chase"])) for record in days),
        "heat_vs_shade_entry_time": _correlation((record["latents"]["heat"], record["time_traces_minutes_after_start"]["shade_entry_time"]) for record in days),
        "heat_vs_shade_wake_time": _correlation((record["latents"]["heat"], record["time_traces_minutes_after_start"]["shade_wake_time"]) for record in days),
        "heat_vs_mean_drinking_bout": _correlation((record["latents"]["heat"], record["mean_drinking_bout_minutes"]) for record in days),
        "tourist_volume_vs_road_entries": _correlation((record["traffic_count"], record["zone_entry_counts"].get("Road", 0)) for record in days),
        "tourist_rate_vs_road_entries": _correlation((record["latents"]["tourist_rate_per_hour"], record["zone_entry_counts"].get("Road", 0)) for record in days),
    }
    report_indices = sorted({row["report_index"] for row in rows})
    # Include every configured non-final report even if no days completed.
    report_indices = sorted(set(report_indices) | set(range(1, len(config["time"]["report_times"]))))
    class_balance = {str(index): _balance(row for row in rows if row["report_index"] == index)
                     for index in report_indices}
    validations = [record["validation"] for record in days if "validation" in record]
    failed = [validation for validation in validations if not validation["valid"]]
    checks: list[dict[str, Any]] = []

    def check(name: str, observed: Any, expected: Any, *, lower: float | None = None,
              upper: float | None = None, lower_strict: bool = False,
              upper_strict: bool = False, note: str = "") -> None:
        number = _finite(observed)
        if number is None:
            status, message = "FAIL", "No finite statistic is available."
        else:
            inside = ((lower is None or (number > lower if lower_strict else number >= lower))
                      and (upper is None or (number < upper if upper_strict else number <= upper)))
            status = "PASS" if inside else "WARN"
            message = "Within the configured reference range." if inside else "Outside the configured reference range."
        checks.append({"name": name, "status": status, "observed": number,
                       "expected": expected, "message": (message + " " + note).strip()})

    targets = config["targets"]
    check("observed_true_path_ratio", gps_metrics["observed_true_path_ratio"],
          targets["observed_true_path_ratio_max"], upper=targets["observed_true_path_ratio_max"])
    check("smoothed_rest_apparent_speed_kmh", gps_metrics["smoothed_rest_apparent_speed_kmh"],
          targets["smoothed_rest_speed_max_kmh"], upper=targets["smoothed_rest_speed_max_kmh"], upper_strict=True)
    entries_distribution = _distribution((record["zone_entry_count"] for record in days), count)
    low, high = targets["zone_entries_per_day"]
    check("zone_entries_per_day", entries_distribution["mean"], [low, high], lower=low, upper=high)
    low, high = targets["zone_entry_share"]
    for zone in zone_names:
        road = zone == "Road"
        check(f"zone_entry_share.{zone}", entry_shares[zone] if total_entries else None,
              {"minimum_exclusive": 0, "maximum": high} if road else [low, high],
              lower=0 if road else low, upper=high, lower_strict=road,
              note="Road may be below the common minimum; zero still warns." if road else "")
    for setting, flag in (("hunt_attempt_day_fraction", "any_chase"),
                          ("catch_day_fraction", "catch"), ("road_entry_day_fraction", "enter_road")):
        low, high = targets[setting]
        check(setting, fractions[flag], [low, high], lower=low, upper=high)
    check("unique_sequence_fraction", unique_fraction,
          {"minimum_exclusive": targets["unique_sequence_fraction_min"]},
          lower=targets["unique_sequence_fraction_min"], lower_strict=True)
    check("top_five_sequence_share", top_five_share,
          {"maximum_exclusive": targets["top_five_sequence_share_max"]},
          upper=targets["top_five_sequence_share_max"], upper_strict=True)
    low, high = targets["mean_walking_speed_kmh"]
    check("mean_walking_speed_kmh", pooled_speed, [low, high], lower=low, upper=high)
    behaviour_comparison = {}
    for name, interval in targets["hours_per_behaviour"].items():
        if name.startswith("_"):
            continue
        actual = hours["sleeping_resting"] if name == "resting" else hours[name]
        behaviour_comparison[name] = {"mean_hours": actual,
                                      "target_hours": config["validation"]["hours_targets"][name],
                                      "range_hours": interval}
        check(f"hours_per_behaviour.{name}", actual, interval, lower=interval[0], upper=interval[1])
    checks.append({"name": "event_invariants", "status": "FAIL" if failed or not count else "PASS" if len(validations) == count else "WARN",
                   "observed": len(failed), "expected": 0,
                   "message": (f"{len(validations)}/{count} days checked; {len(failed)} days failed hard validation."
                               if count else "No completed days are available.")})
    status_counts = Counter(check["status"] for check in checks)
    return {
        "schema_version": "statistics-v2", "days_simulated": count,
        "day_indices": [record["day_index"] for record in days],
        "events_per_day": _distribution((record["event_count"] for record in days), count),
        "zone_entries_per_day": entries_distribution,
        "token_frequencies": {token: int(token_counts[token]) for token in TOKENS},
        "zone_entry_counts": {name: int(zone_counts[name]) for name in zone_names},
        "zone_entry_shares": entry_shares,
        "day_fractions": fractions,
        "chase_success_rate": token_counts["CATCH"] / token_counts["CHASE_START"] if token_counts["CHASE_START"] else None,
        "chase_attempts": token_counts["CHASE_START"],
        "hours_per_behaviour": hours, "behaviour_comparison": behaviour_comparison,
        "time_distributions": traces,
        "sequence_diversity": {
            "unique_sequences": len(sequences), "unique_daily_sequence_fraction": unique_fraction,
            "top_five_sequence_share": top_five_share,
            "top_five_sequences": [{"sequence": list(sequence), "days": frequency,
                                     "fraction": frequency / count if count else None}
                                    for sequence, frequency in ordered_sequences[:5]],
            "length_distribution": _distribution((len(record["zone_sequence"]) for record in days), count),
            "length_counts": {str(length): sequence_lengths[length] for length in sorted(sequence_lengths)},
        },
        "path_statistics": {
            "aggregates": path_aggregates, "pooled_mean_walking_speed_kmh": pooled_speed,
            "gps_observation": gps_metrics,
            "abandoned_trips_by_reason": dict(sorted(reason_counts.items())),
            "per_day": [{"day_index": record["day_index"], **record["path"]} for record in days],
        },
        "next_zone_target_balance": {"by_report_index": class_balance, "overall": _balance(rows)},
        "correlations": correlations,
        "tourist_volume": _distribution((record["traffic_count"] for record in days), count),
        "checks": checks, "check_counts": {status: status_counts[status] for status in ("PASS", "WARN", "FAIL")},
        "validation": {"days_checked": len(validations), "days_failed": len(failed), "failed_days": failed},
        "definitions": {
            "time_origin": f"Minutes after {config['time']['day_start']} on the simulated start date; clock hours 24+ denote the next morning.",
            "shade_exit_time": "First minute sampled outside Shade after its first confirmed entry; missing when the lion never leaves before day end.",
            "feast": "A day containing at least one EAT_START (not necessarily a completed meal before the day boundary).",
            "mean_walking_speed": "Measured true displacement in all intervals labelled walking, including short settling/arrival intervals; pooled by walking time across days.",
            "gps_observation": "Pooled observed/true path ratio; apparent rest speeds pool sleeping/quiet-rest intervals. Smoothing uses trailing mean positions and excludes any window spanning non-rest activity.",
            "tortuosity": "Sum of true path lengths divided by sum of endpoint straight-line distances between consecutive confirmed zone entries; zero-length chords excluded, null without an eligible pair.",
            "coverage": f"Fraction of {config['statistics']['coverage_grid_km']:g} km square grid cells visited by true GPS fixes; boundary fixes assigned to the final inside cell.",
            "abandoned_trips": "Count of nonempty abandoned_trip_reason rows; the simulator emits a reason only on the interrupt minute.",
            "correlations": "Pearson coefficients using available paired daily values; null with an explanation for insufficient/constant observations. These describe synthetic association, not causal proof.",
            "target_status": "PASS is inside the configured range; WARN is a finite statistic outside it; FAIL means no finite statistic or a hard validation failure. Requested strict sequence bounds are exclusive.",
            "scope": "Descriptive statistics plus optional held-out counting baselines and hidden-state oracle evaluation. No ML libraries are used.",
        },
    }


def _display(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    if isinstance(value, (dict, list)):
        return str(value)
    return str(value)


def render_stats_markdown(report: dict[str, Any]) -> str:
    """Produce the human report from exactly the same JSON statistics."""
    lines = ["# Lion simulator statistics", "",
             f"Completed days: **{report['days_simulated']}**. Checks: "
             + ", ".join(f"**{report['check_counts'][status]} {status}**" for status in ("PASS", "WARN", "FAIL")) + ".", "",
             "## Target checks", "",
             "PASS means within the reference range; WARN means a statistical deviation; FAIL means an unavailable statistic or hard validation failure.", "",
             "| Check | Status | Observed | Expected |", "| --- | --- | ---: | --- |"]
    for check in report["checks"]:
        lines.append(f"| {check['name']} | **{check['status']}** | {_display(check['observed'])} | {_display(check['expected'])} |")
    lines += ["", "## Counts and outcomes", "", "| Statistic | Value |", "| --- | ---: |"]
    for field in ("events_per_day", "zone_entries_per_day"):
        distribution = report[field]
        lines.append(f"| {field}: mean / min / max | " + " / ".join(_display(distribution[key]) for key in ("mean", "min", "max")) + " |")
    for name, value in report["day_fractions"].items():
        lines.append(f"| Fraction of days: {name} | {_display(value)} |")
    lines += [f"| Chase success rate | {_display(report['chase_success_rate'])} |", "",
              "| Token | Frequency |", "| --- | ---: |"]
    lines += [f"| {name} | {value} |" for name, value in report["token_frequencies"].items()]
    lines += ["", "| Zone | Entries | Share of entries |", "| --- | ---: | ---: |"]
    lines += [f"| {name} | {report['zone_entry_counts'][name]} | {_display(value)} |" for name, value in report["zone_entry_shares"].items()]
    lines += ["", "## Behaviour hours per day", "", "| Behaviour | Mean | Target | Range |", "| --- | ---: | ---: | --- |"]
    for name, comparison in report["behaviour_comparison"].items():
        label = "sleeping + resting" if name == "resting" else name
        lines.append(f"| {label} | {_display(comparison['mean_hours'])} | {_display(comparison['target_hours'])} | {_display(comparison['range_hours'])} |")
    lines += ["", "## Time distributions", "", report["definitions"]["time_origin"], "",
              "| Trace | Observed days | Missing | Mean clock | Min clock | Median clock | Max clock |",
              "| --- | ---: | ---: | --- | --- | --- | --- |"]
    for name, dist in report["time_distributions"].items():
        clocks = dist["clock_times"]
        lines.append(f"| {name} | {dist['count']} | {dist['missing']} | " + " | ".join(_display(clocks[key]) for key in ("mean", "min", "median", "max")) + " |")
    diversity = report["sequence_diversity"]
    lines += ["", "## Daily zone-sequence diversity", "",
              f"Unique fraction: **{_display(diversity['unique_daily_sequence_fraction'])}**. Top five coverage: **{_display(diversity['top_five_sequence_share'])}**.", "",
              "| Days | Share | Sequence |", "| ---: | ---: | --- |"]
    for sequence in diversity["top_five_sequences"]:
        names = " → ".join(token.removeprefix("ENTER_") for token in sequence["sequence"]) or "(no entries)"
        lines.append(f"| {sequence['days']} | {_display(sequence['fraction'])} | {names} |")
    lines += ["", "Sequence-length histogram (entries: days): " + ", ".join(f"{length}: {frequency}" for length, frequency in diversity["length_counts"].items()) + ".", "",
              "## Path statistics", "", "| Metric | Mean | Min | Median | Max | Missing days |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for name, dist in report["path_statistics"]["aggregates"].items():
        lines.append(f"| {name} | " + " | ".join(_display(dist[key]) for key in ("mean", "min", "median", "max", "missing")) + " |")
    lines += ["", f"Pooled measured walking speed: **{_display(report['path_statistics']['pooled_mean_walking_speed_kmh'])} km/h**.",
              "GPS observation diagnostics: " + _display(report["path_statistics"]["gps_observation"]) + ".",
              "Abandoned trip reasons: " + _display(report["path_statistics"]["abandoned_trips_by_reason"]) + ".", "",
              "Per-day path metrics are included in `stats_report.json`.", "", "## Next-zone target class balance", ""]
    balances = report["next_zone_target_balance"]
    classes = list(balances["overall"]["counts"])
    lines += ["Each cell is count (fraction); the final day-ending report is excluded.", "",
              "| Report | " + " | ".join(classes) + " |", "| --- | " + " | ".join("---:" for _ in classes) + " |"]
    for label, balance in [*balances["by_report_index"].items(), ("overall", balances["overall"])]:
        lines.append(f"| {label} | " + " | ".join(f"{balance['counts'][target]} ({balance['fractions'][target]:.3f})" for target in classes) + " |")
    lines += ["", "## Latent / observable-trace correlations", "", "| Pair | Pearson r | Paired days | Note |", "| --- | ---: | ---: | --- |"]
    for name, correlation in report["correlations"].items():
        lines.append(f"| {name} | {_display(correlation['value'])} | {correlation['count']} | {correlation['reason'] or ''} |")
    volume = report["tourist_volume"]
    lines += ["", "Actual tourist volume per day (mean / min / max): " + " / ".join(_display(volume[key]) for key in ("mean", "min", "max")) + ".", "",
              "## Definitions and limitations", ""]
    lines += [f"- **{name}:** {definition}" for name, definition in report["definitions"].items() if name != "time_origin"]
    if "baseline_ladder" in report:
        ladder = report["baseline_ladder"]
        lines += ["", "## Baseline ladder", "", ladder["interpretation"], ""]
        if ladder["status"] == "complete":
            lines += ["| Scope | L0 mean ± std | L1 mean ± std | L2 mean ± std | L3 mean ± std |",
                      "| --- | ---: | ---: | ---: | ---: |"]
            for scope, values in [("Headline", ladder["headline"]), ("All reports", ladder["all_reports"]), *ladder["by_report_index"].items()]:
                lines.append(f"| {scope} | " + " | ".join(
                    "n/a" if values[name]["mean"] is None else f"{values[name]['mean']:.6f} ± {values[name]['std']:.6f}"
                    for name in ("L0", "L1", "L2", "L3")) + " |")
            lines += ["", ladder["split_rule"], ladder["backoff_rule"],
                      f"Effective folds: {ladder['cv_folds']}; headline reports: {ladder['headline_reports']}.",
                      f"L3 zero-training-cell fraction: {ladder['l3_zero_training_fraction']:.4f}.",
                      "", "Per-fold headline L3−L2 and standard error of paired day losses (diagnostic only):", "",
                      "| Fold | L3−L2 nats | Paired day SE |", "| --- | ---: | ---: |"]
            lines += [f"| {f['fold']} | {_display(f['headline_l3_minus_l2_nats'])} | {_display(f['paired_day_standard_error_nats'])} |" for f in ladder["folds"]]
    if "oracle" in report:
        oracle = report["oracle"]
        lines += ["", "## Hidden-state oracle", "", oracle["interpretation"], "", oracle["finite_sample_note"]]
        if oracle["status"] == "complete":
            lines += ["", "| Model | Same held-out log loss (nats) |", "| --- | ---: |"]
            lines += [f"| {name} | {value:.6f} |" for name, value in oracle["losses"].items()]
            lines += ["", f"Smoothing floor: {oracle['smoothing_floor_nats']:.6f} nats."]
        lines += ["", "See oracle_report.md and oracle_report.json for timestamped per-report probabilities."]
    return "\n".join(lines) + "\n"


def _cue_bins(row: dict[str, Any], config: Config) -> tuple[str, ...]:
    shade = row['shade_entry_hour_bucket']
    shade_bin = ('not_yet' if str(shade) == 'not_yet' else
                 'early' if int(shade) < config['learnability']['shade_hour_cut'] else 'late')
    return (shade_bin, *(str(min(2, max(0, int(row[name])))) for name in
                         ('drinks_so_far', 'chase_attempts_so_far', 'catch_so_far')))


def baseline_ladder(rows: Iterable[dict[str, Any]], config: Config) -> dict[str, Any]:
    """Out-of-fold counting losses; each day is held out exactly once."""
    options = config['learnability']
    alpha, strength = options['laplace_alpha'], options['l3_interpolation_k']
    rows = sorted(list(rows), key=lambda r: (int(r['day']), int(r['report_index'])))
    if len({(int(r['day']), int(r['report_index'])) for r in rows}) != len(rows):
        raise ValueError('Duplicate day/report target row')
    classes = list(TARGET_CLASSES)
    if any(r['next_zone_target'] not in classes for r in rows):
        raise ValueError('Unknown next-zone target class')
    required = ('shade_entry_hour_bucket', 'drinks_so_far', 'chase_attempts_so_far', 'catch_so_far')
    if any(any(key not in r or r[key] == '' for key in required) for r in rows):
        raise ValueError('Baseline evaluation requires observable history cue columns')
    days = sorted({int(r['day']) for r in rows})
    names = ('L0', 'L1', 'L2', 'L3')
    if len(days) < 2:
        return {'status': 'insufficient_data', 'interpretation': 'Need at least two days for day-disjoint cross-validation.',
                'losses': dict.fromkeys(names), 'classes': classes}
    count = min(options['cv_folds'], len(days))
    headline = set(options['headline_reports'])

    def keys(row):
        bucket = (str(int(row['report_index'])),)
        state = bucket + tuple('' if row[k] is None else str(row[k]) for k in ('current_zone', 'last_event'))
        return [(), bucket, state, state + _cue_bins(row, config)]

    def mean_losses(records):
        return {name: float(np.mean([r['losses'][name] for r in records])) if records else None for name in names}

    folds, predictions = [], []
    backoffs = Counter()
    for fold_index in range(count):
        test_days = days[fold_index::count]
        train_days = sorted(set(days) - set(test_days))
        training = [r for r in rows if int(r['day']) in set(train_days)]
        testing = [r for r in rows if int(r['day']) in set(test_days)]
        tables: list[dict[tuple[str, ...], Counter[str]]] = [{} for _ in names]
        for row in training:
            for level, key in enumerate(keys(row)):
                tables[level].setdefault(key, Counter())[row['next_zone_target']] += 1
        fold_rows = []
        for row in testing:
            cell_keys, probabilities = keys(row), []
            for level in range(3):
                counts = tables[level].get(cell_keys[level], Counter())
                if not counts and level:
                    probabilities.append(probabilities[level - 1])
                    backoffs[f'L{level}'] += 1
                else:
                    probabilities.append(np.array([(counts[target] + alpha) / (sum(counts.values()) + alpha * len(classes)) for target in classes]))
            counts = tables[3].get(cell_keys[3], Counter())
            total = sum(counts.values())
            probabilities.append((np.array([counts[target] for target in classes]) + strength * probabilities[2]) / (total + strength))
            target_index = classes.index(row['next_zone_target'])
            fold_rows.append({'day': int(row['day']), 'report_index': int(row['report_index']),
                              'fold': fold_index + 1, 'l3_zero_cell': total == 0,
                              'losses': {name: -math.log(probabilities[i][target_index]) for i, name in enumerate(names)}})
        predictions.extend(fold_rows)
        paired = [float(np.mean([r['losses']['L3'] - r['losses']['L2'] for r in fold_rows
                                 if r['day'] == day and r['report_index'] in headline]))
                  for day in test_days if any(r['day'] == day and r['report_index'] in headline for r in fold_rows)]
        folds.append({'fold': fold_index + 1, 'train_days': train_days, 'test_days': test_days,
                      'test_rows': len(fold_rows), 'training_rows': len(training),
                      'all_reports': mean_losses(fold_rows),
                      'headline': mean_losses([r for r in fold_rows if r['report_index'] in headline]),
                      'by_report_index': {str(index): mean_losses([r for r in fold_rows if r['report_index'] == index])
                                          for index in range(1, len(config['time']['report_times']))},
                      'l3_zero_training_fraction': sum(r['l3_zero_cell'] for r in fold_rows) / len(fold_rows),
                      'headline_l3_minus_l2_nats': float(np.mean(paired)) if paired else None,
                      'paired_day_standard_error_nats': float(np.std(paired, ddof=1) / math.sqrt(len(paired))) if len(paired) > 1 else None})

    def summary(select):
        result = {}
        for name in names:
            values = [select(f)[name] for f in folds if select(f)[name] is not None]
            result[name] = {'mean': float(np.mean(values)) if values else None,
                            'std': float(np.std(values)) if values else None}
        return result

    all_reports = summary(lambda f: f['all_reports'])
    head = summary(lambda f: f['headline'])
    losses = {name: all_reports[name]['mean'] for name in names}
    absolute = {f'L{i}-L{i+1}': losses[f'L{i}'] - losses[f'L{i+1}'] for i in range(3)}
    relative = {key: value / losses[f'L{i}'] for i, (key, value) in enumerate(absolute.items())}
    spread = (max(losses[n] for n in names[:3]) - min(losses[n] for n in names[:3])) / losses['L0']
    interpretation = ('mostly noise' if spread <= options['mostly_noise_relative_tolerance'] else
                      'nearly deterministic' if losses['L2'] < options['near_deterministic_ratio'] * losses['L0'] else 'learnable')
    frequencies = Counter(r['next_zone_target'] for r in rows)
    entropy = -sum(n / len(rows) * math.log(n / len(rows)) for n in frequencies.values())
    return {'status': 'complete', 'classes': classes, 'losses': losses,
            'all_reports': all_reports, 'headline': head, 'headline_reports': sorted(headline),
            'by_report_index': {str(index): summary(lambda f, index=index: f['by_report_index'][str(index)])
                                for index in range(1, len(config['time']['report_times']))},
            'folds': folds, 'cv_folds': count, 'test_days': days, 'test_rows': len(rows),
            'target_entropy_nats': entropy, 'absolute_gaps_nats': absolute, 'relative_gaps': relative,
            'interpretation': interpretation, 'laplace_alpha': alpha, 'l3_interpolation_k': strength,
            'l3_zero_training_fraction': sum(r['l3_zero_cell'] for r in predictions) / len(predictions),
            'backoff_rows': dict(backoffs),
            'split_rule': 'Sorted day IDs assigned round-robin to folds. Every day is held out once; no reports from a test day enter its training counts.',
            'backoff_rule': 'Unseen L1 -> L0; unseen L2 -> L1; L3 interpolates cell counts with k times its L2 probabilities, including zero cells.',
            'units': 'Natural-log multiclass log loss, mean and population standard deviation across day folds; all-reports and headline scopes are separate.'}

def baselines_from_csv(path: Any, config: Config) -> dict[str, Any]:
    """Read the persisted target table; null zones remain ordinary empty strings."""
    import csv
    from pathlib import Path

    with Path(path).open(newline='', encoding='utf-8') as handle:
        return baseline_ladder(list(csv.DictReader(handle)), config)
