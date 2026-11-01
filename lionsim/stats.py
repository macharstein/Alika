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
                 "tortuosity", "map_coverage_fraction", "abandoned_trip_count")
    path_aggregates = {key: _distribution((record["path"].get(key) for record in days), count) for key in path_keys}
    walking_minutes = sum(record["path"]["walking_minutes"] for record in days)
    walking_distance = sum(record["path"]["walking_distance_km"] or 0.0 for record in days)
    pooled_speed = walking_distance * 60 / walking_minutes if walking_minutes else None
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
        "schema_version": "statistics-v1", "days_simulated": count,
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
            "tortuosity": "Sum of true path lengths divided by sum of endpoint straight-line distances between consecutive confirmed zone entries; zero-length chords excluded, null without an eligible pair.",
            "coverage": f"Fraction of {config['statistics']['coverage_grid_km']:g} km square grid cells visited by true GPS fixes; boundary fixes assigned to the final inside cell.",
            "abandoned_trips": "Count of nonempty abandoned_trip_reason rows; the simulator emits a reason only on the interrupt minute.",
            "correlations": "Pearson coefficients using available paired daily values; null with an explanation for insufficient/constant observations. These describe synthetic association, not causal proof.",
            "target_status": "PASS is inside the configured range; WARN is a finite statistic outside it; FAIL means no finite statistic or a hard validation failure. Requested strict sequence bounds are exclusive.",
            "scope": "Descriptive statistics plus optional held-out counting baselines. The oracle remains outside this phase.",
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
            lines += ["| Baseline | Held-out log loss (nats) |", "| --- | ---: |"]
            lines += [f"| {name} | {value:.6f} |" for name, value in ladder["losses"].items()]
            lines += ["", f"Target entropy: {ladder['target_entropy_nats']:.6f} nats.",
                      f"Whole-day split: {len(ladder['train_days'])} training / {len(ladder['test_days'])} test days.",
                      "Absolute gaps: " + str(ladder["absolute_gaps_nats"]),
                      "Relative gaps: " + str(ladder["relative_gaps"]),
                      ladder["backoff_rule"], "Backoff row counts: " + str(ladder["backoff_rows"])]
    return "\n".join(lines) + "\n"


def baseline_ladder(rows: Iterable[dict[str, Any]], config: Config) -> dict[str, Any]:
    """Evaluate smoothed frequency tables using a disjoint holdout of whole days.

    No latent values or test outcomes affect fitted counts or backoff decisions.
    L1/L2 unseen cells back off one level; sparse L3 cells back off to L2.
    """
    options = config['learnability']
    alpha = options['laplace_alpha']
    rows = sorted(list(rows), key=lambda row: (int(row['day']), int(row['report_index'])))
    if len({(int(r['day']), int(r['report_index'])) for r in rows}) != len(rows):
        raise ValueError('Duplicate day/report target row')
    classes = list(TARGET_CLASSES)
    if any(r['next_zone_target'] not in classes for r in rows):
        raise ValueError('Unknown next-zone target class')
    required = ('shade_entry_hour_bucket', 'drinks_so_far', 'chase_attempts_so_far', 'catch_so_far')
    if any(any(key not in row or row[key] == '' for key in required) for row in rows):
        raise ValueError('Baseline evaluation requires observable history cue columns')
    days = sorted({int(r['day']) for r in rows})
    if len(days) < 2:
        return {'status': 'insufficient_data', 'interpretation': 'Need at least two days for a day-separated holdout.',
                'losses': dict.fromkeys(('L0', 'L1', 'L2', 'L3')), 'classes': classes}
    cut = max(1, min(len(days)-1, int(len(days)*options['train_fraction'])))
    train_days, test_days = days[:cut], days[cut:]
    training = [r for r in rows if int(r['day']) in set(train_days)]
    testing = [r for r in rows if int(r['day']) in set(test_days)]

    def clean(value: Any) -> str:
        return '' if value is None else str(value)

    def keys(row: dict[str, Any]) -> list[tuple[str, ...]]:
        bucket = (str(int(row['report_index'])),)
        state = bucket + (clean(row['current_zone']), clean(row['last_event']))
        return [(), bucket, state, state + tuple(clean(row[name]) for name in required)]

    tables: list[dict[tuple[str, ...], Counter[str]]] = [{} for _ in range(4)]
    for row in training:
        for level, key in enumerate(keys(row)):
            tables[level].setdefault(key, Counter())[row['next_zone_target']] += 1
    losses = np.zeros(4)
    backoffs = Counter()
    for row in testing:
        cell_keys = keys(row)
        for level in range(4):
            used = level
            while used:
                counts = tables[used].get(cell_keys[used], Counter())
                minimum = options['l3_min_cell_count'] if used == 3 else 1
                if sum(counts.values()) >= minimum:
                    break
                used -= 1
            if used != level:
                backoffs[f'L{level}'] += 1
            counts = tables[used].get(cell_keys[used], Counter())
            probability = (counts[row['next_zone_target']] + alpha) / (sum(counts.values()) + alpha * len(classes))
            losses[level] -= math.log(probability)
    losses /= len(testing)
    named = {f'L{i}': float(value) for i, value in enumerate(losses)}
    absolute = {f'L{i}-L{i+1}': float(losses[i]-losses[i+1]) for i in range(3)}
    relative = {key: value / losses[i] if losses[i] else None for i, (key, value) in enumerate(absolute.items())}
    spread = (max(losses[:3])-min(losses[:3])) / losses[0]
    interpretation = ('mostly noise' if spread <= options['mostly_noise_relative_tolerance'] else
                      'nearly deterministic' if losses[2] < options['near_deterministic_ratio'] * losses[0] else 'learnable')
    target_counts = Counter(r['next_zone_target'] for r in testing)
    entropy = -sum((n/len(testing))*math.log(n/len(testing)) for n in target_counts.values())
    return {'status': 'complete', 'classes': classes, 'losses': named,
            'target_entropy_nats': entropy, 'absolute_gaps_nats': absolute,
            'relative_gaps': relative, 'interpretation': interpretation,
            'train_days': train_days, 'test_days': test_days,
            'training_rows': len(training), 'test_rows': len(testing),
            'backoff_rows': {f'L{i}': backoffs[f'L{i}'] for i in range(1,4)},
            'laplace_alpha': alpha, 'l3_min_cell_count': options['l3_min_cell_count'],
            'split_rule': 'First 70% of sorted day IDs for training (fraction configurable); remaining whole days held out.',
            'backoff_rule': 'Unseen L1 -> L0; unseen L2 -> L1; L3 below minimum training count -> L2, then the same unseen-cell rules.',
            'units': 'Natural-log multiclass log loss (nats); entropy uses held-out empirical targets.'}


def baselines_from_csv(path: Any, config: Config) -> dict[str, Any]:
    """Read the persisted target table; null zones remain ordinary empty strings."""
    import csv
    from pathlib import Path

    with Path(path).open(newline='', encoding='utf-8') as handle:
        return baseline_ladder(list(csv.DictReader(handle)), config)
