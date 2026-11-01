"""Event invariants and bounded, streaming run statistics.

Behaviour reference budgets are diagnostics, never hard constraints imposed on
the stochastic model. A failed event invariant always remains visible in the
validation report.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import numpy as np

from .config import Config
from .events import TOKENS, ZONE_TOKENS
from .reports import END_OF_DAY, TARGET_CLASSES

if TYPE_CHECKING:
    from .simulator import DayResult


BEHAVIOURS = ("sleeping", "resting", "walking", "hunting", "grooming", "eating", "drinking")
NO_FUTURE_ENTRY = END_OF_DAY


def _minutes(clock: str) -> int:
    hour, minute = map(int, clock.split(":"))
    return hour * 60 + minute


def _start(day: DayResult, config: Config) -> datetime:
    return datetime.fromisoformat(f"{day.date}T{config['time']['day_start']}:00")


def _clock_in_window(t: datetime, start: str, end: str) -> bool:
    """Test an inclusive-start, exclusive-end clock window across midnight."""
    clock = t.hour * 60 + t.minute + t.second / 60
    lower, upper = _minutes(start), _minutes(end)
    if lower < upper:
        return lower <= clock < upper
    return clock >= lower or clock < upper


def validate_day(day: DayResult, config: Config) -> dict[str, Any]:
    """Validate one day without suppressing failures or changing its records."""
    errors: list[str] = []
    warnings: list[str] = []
    start = _start(day, config)
    minutes = config["time"]["day_minutes"]
    end = start + timedelta(minutes=minutes)
    zones = {name for name in config["map"]["zones"] if not name.startswith("_")}
    token_zones = {token: zone for zone, token in ZONE_TOKENS.items()}
    sleep_zones = {"Den", "Shade", "Feeding spot", "Plain"}
    events = day.events
    parsed: list[tuple[dict[str, Any], datetime]] = []
    previous_time: datetime | None = None

    for index, event in enumerate(events):
        context = f"event {index + 1}"
        token = event.get("token")
        if token not in TOKENS:
            errors.append(f"{context}: unknown token {token!r}.")
        if "zone" not in event:
            errors.append(f"{context}: zone must be present (a zone name or null).")
        if event.get("zone") is not None and event.get("zone") not in zones:
            errors.append(f"{context}: unknown zone {event.get('zone')!r}.")
        try:
            t = datetime.fromisoformat(event["t"])
            if t.tzinfo is not None:
                raise ValueError("expected a simulated local timestamp without UTC offset")
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{context}: invalid timestamp ({exc}).")
            continue
        if not start <= t < end:
            errors.append(f"{context}: timestamp {event['t']} is outside the simulated day.")
        if previous_time is not None and t < previous_time:
            errors.append(f"{context}: events are not sorted by timestamp.")
        previous_time = t
        parsed.append((event, t))

    if not events or events[0].get("token") != "WOKE_UP":
        errors.append("The first event must be WOKE_UP.")
    elif parsed and parsed[0][0] is events[0]:
        wake = parsed[0][1]
        low_clock, high_clock = config["randomness"]["wake_time_clip"]
        low = start + timedelta(minutes=(_minutes(low_clock) - _minutes(config['time']['day_start'])) % minutes)
        high = start + timedelta(minutes=(_minutes(high_clock) - _minutes(config['time']['day_start'])) % minutes)
        if not low <= wake <= high:
            errors.append(f"Initial WOKE_UP must be between {low_clock} and {high_clock}.")
        if "wake_time" in day.latents:
            try:
                if wake != datetime.fromisoformat(day.latents["wake_time"]):
                    errors.append("Initial WOKE_UP does not match the day's latent wake_time.")
            except (TypeError, ValueError):
                errors.append("The latent wake_time is not a valid ISO timestamp.")

    previous_event: tuple[dict[str, Any], datetime] | None = None
    previous_entry: str | None = None
    unresolved_chase = False
    catch_available = False
    entered_feed_after_catch = False
    eating = False
    meal_finished = False
    sleeping_after_meal = False
    delay_min, delay_max = config["chase"]["outcome_delay_seconds_range"]
    hunt_start, hunt_end = config["behaviours"]["hunt_start"], config["behaviours"]["hunt_end"]
    eligible = (day.latents.get("start_hunger", 1.0) > day.latents.get("hunt_threshold", 0.0))
    for event, t in parsed:
        token, zone = event.get("token"), event.get("zone")
        if token in {"ENTER_HUNT", "CHASE_START"}:
            if not _clock_in_window(t, hunt_start, hunt_end):
                errors.append(f"{event['t']}: {token} is outside the hunting window [{hunt_start}, {hunt_end}); no hunting after the cutoff.")
            if not eligible:
                errors.append(f"{event['t']}: {token} on a day whose initial hunger does not exceed its hunt threshold.")
        if token in token_zones:
            if previous_entry == token:
                errors.append(f"{event['t']}: identical consecutive zone entry {token}.")
            previous_entry = token
            if zone != token_zones[token]:
                errors.append(f"{event['t']}: {token} has inconsistent zone {zone!r}.")
            if token == "ENTER_FEED" and catch_available:
                entered_feed_after_catch = True
        if token == "FELL_ASLEEP" and zone not in sleep_zones:
            errors.append(f"{event['t']}: FELL_ASLEEP in forbidden zone {zone!r}.")
        if token == "DRINK" and zone != "Waterhole":
            errors.append(f"{event['t']}: DRINK must occur at Waterhole.")
        if sleeping_after_meal:
            errors.append(f"{event['t']}: {token} occurred after post-feeding sleep began.")
        elif meal_finished:
            if token != "FELL_ASLEEP" or zone != "Feeding spot":
                errors.append(f"{event['t']}: EAT_END must be followed by sleep in Feeding spot.")
            else:
                sleeping_after_meal = True
            meal_finished = False
        if token == "CHASE_START":
            if unresolved_chase:
                errors.append(f"{event['t']}: CHASE_START precedes resolution of the previous chase.")
            unresolved_chase = True
        elif token in {"CATCH", "FAIL"}:
            if previous_event is None or previous_event[0].get("token") != "CHASE_START":
                errors.append(f"{event['t']}: {token} does not immediately follow CHASE_START.")
            else:
                delay = (t - previous_event[1]).total_seconds()
                if not delay_min <= delay <= delay_max:
                    errors.append(f"{event['t']}: chase outcome delay {delay:g}s is outside [{delay_min}, {delay_max}].")
                chase_step = int((previous_event[1] - start).total_seconds() // 60)
                if int((t - start).total_seconds() // 60) != chase_step:
                    errors.append(f"{event['t']}: chase start and outcome occur in different minute steps.")
            unresolved_chase = False
            if token == "CATCH":
                catch_available = True
                entered_feed_after_catch = False
        elif token == "EAT_START":
            if not catch_available:
                errors.append(f"{event['t']}: EAT_START has no preceding unused CATCH.")
            elif not entered_feed_after_catch:
                errors.append(f"{event['t']}: EAT_START requires ENTER_FEED after the catch.")
            if eating:
                errors.append(f"{event['t']}: EAT_START occurred while already eating.")
            if zone != "Feeding spot":
                errors.append(f"{event['t']}: EAT_START must occur in Feeding spot.")
            catch_available = False
            eating = True
        elif token == "EAT_END":
            if not eating:
                errors.append(f"{event['t']}: EAT_END has no preceding EAT_START.")
            eating = False
            meal_finished = True
        previous_event = (event, t)
    if unresolved_chase:
        errors.append("A CHASE_START has no CATCH or FAIL outcome before the day ends.")

    previous_traffic: datetime | None = None
    for index, value in enumerate(getattr(day, "traffic_times", []), 1):
        try:
            timestamp = datetime.fromisoformat(value)
            if timestamp.tzinfo is not None:
                raise ValueError("traffic times must be naive local timestamps")
        except (TypeError, ValueError) as error:
            errors.append(f"traffic {index}: invalid timestamp ({error}).")
            continue
        if not start <= timestamp < end or not _clock_in_window(timestamp, config["tourists"]["start"], config["tourists"]["end"]):
            errors.append(f"traffic {index}: timestamp is outside the tourist window or simulated day.")
        if previous_traffic is not None and timestamp < previous_traffic:
            errors.append(f"traffic {index}: traffic timestamps are not sorted.")
        previous_traffic = timestamp

    gps = day.gps
    hidden = day.hidden_state
    required_gps = {"t_iso", "minute_index", "x_km", "y_km", "x_true_km", "y_true_km", "missing"}
    required_hidden = {"t_iso", "minute_index", "hunger", "energy", "temperature", "boredom", "mood", "goal", "behaviour", "zone"}
    for label, frame, required, count in (("GPS", gps, required_gps, minutes + 1), ("hidden_state", hidden, required_hidden, minutes)):
        missing = required - set(frame.columns)
        if missing:
            errors.append(f"{label}: missing required columns {sorted(missing)}.")
        if len(frame) != count:
            errors.append(f"{label}: expected {count} rows, found {len(frame)}.")
        if "minute_index" in frame and not np.array_equal(frame["minute_index"].to_numpy(), np.arange(count)):
            errors.append(f"{label}: minute_index must be consecutive from zero.")
    coordinate_columns = ["x_km", "y_km", "x_true_km", "y_true_km"]
    if set(coordinate_columns) <= set(gps.columns):
        try:
            values = gps[coordinate_columns].to_numpy(dtype=float)
        except (TypeError, ValueError):
            errors.append("GPS coordinates must be numeric.")
        else:
            if not np.isfinite(values).all():
                errors.append("GPS coordinates must be finite after forward-filling missing fixes.")
            for column, coordinate, extent in ((2, "x_true_km", "width_km"), (3, "y_true_km", "height_km")):
                if not ((values[:, column] >= 0) & (values[:, column] <= config["map"][extent])).all():
                    errors.append(f"True positions in {coordinate} leave the map.")
    for bar in ("hunger", "energy", "temperature", "boredom", "mood"):
        if bar in hidden:
            try:
                values = hidden[bar].to_numpy(dtype=float)
            except (TypeError, ValueError):
                errors.append(f"Hidden bar {bar} must be numeric.")
            else:
                if not ((values >= 0) & (values <= 1)).all():
                    errors.append(f"Hidden bar {bar} has non-finite values or leaves [0, 1].")
    if "behaviour" in hidden:
        unexpected = set(hidden["behaviour"].unique()) - set(BEHAVIOURS)
        if unexpected:
            errors.append(f"Unknown behaviours in hidden_state: {sorted(map(str, unexpected))}.")
        if "t_iso" in hidden:
            hunting_times = hidden.loc[hidden["behaviour"] == "hunting", "t_iso"]
            if any(not _clock_in_window(datetime.fromisoformat(str(t)), hunt_start, hunt_end) for t in hunting_times):
                errors.append("Hidden hunting behaviour occurs outside the hunting window or after the cutoff.")
            if not eligible and len(hunting_times):
                errors.append("Hidden hunting behaviour occurs on an initially non-hungry day.")
    if {"abandoned_goal", "abandoned_trip_reason"} <= set(hidden.columns):
        abandoned = hidden["abandoned_goal"].notna()
        reasons = hidden.loc[abandoned, "abandoned_trip_reason"]
        if reasons.isna().any() or reasons.astype(str).str.strip().eq("").any():
            errors.append("An abandoned trip has no logged reason in hidden_state.")
    return {"day_index": int(day.day_index), "date": day.date, "valid": not errors, "errors": errors, "warnings": warnings}


def summarize_day(day: DayResult, reports: list[dict[str, Any]], validation: dict[str, Any], config: Config) -> dict[str, Any]:
    """Return only compact primitives for a worker process to send to its parent."""
    tokens = Counter(event["token"] for event in day.events)
    entries = [event for event in day.events if event["token"] in ZONE_TOKENS.values()]
    next_zones: dict[str, str] = {}
    for report in reports:
        if "next_zone_target" in report:
            report_time = datetime.fromisoformat(report["report_time"])
            next_zones[report_time.strftime("%H:%M")] = report["next_zone_target"]
    behaviour_minutes = {name: int(count) for name, count in day.hidden_state["behaviour"].value_counts().items()}
    return {
        "day_index": int(day.day_index), "date": day.date,
        "event_count": len(day.events), "token_counts": dict(tokens),
        "behaviour_minutes": behaviour_minutes,
        "zone_entry_counts": dict(Counter(event["zone"] for event in entries)),
        "next_zone_by_report_time": next_zones,
        "car_count": len(getattr(day, "traffic_times", [])), "validation": validation,
    }


class SummaryAccumulator:
    """Retain counters and validation messages, never GPS or hidden-state frames."""

    def __init__(self, config: Config):
        self.config = config
        self.count = 0
        self.tokens: Counter[str] = Counter({token: 0 for token in TOKENS})
        # Integer minutes make aggregates identical regardless of worker order.
        self.minutes: Counter[str] = Counter({name: 0 for name in BEHAVIOURS})
        self.entries: Counter[str] = Counter({zone: 0 for zone in config["map"]["zones"] if not zone.startswith("_")})
        self.next_zones: dict[str, Counter[str]] = {time: Counter() for time in config["time"]["report_times"][:-1]}
        self.events_total = self.events_min = self.events_max = 0
        self.cars_total = self.cars_min = self.cars_max = 0
        self.catch_days = 0
        self.validations: list[dict[str, Any]] = []

    def add(self, day: DayResult, reports: list[dict[str, Any]], validation: dict[str, Any]) -> None:
        self.add_record(summarize_day(day, reports, validation, self.config))

    def add_record(self, record: dict[str, Any]) -> None:
        event_count, car_count = record["event_count"], record["car_count"]
        if self.count == 0:
            self.events_min, self.cars_min = event_count, car_count
        self.count += 1
        self.events_total += event_count
        self.events_min, self.events_max = min(self.events_min, event_count), max(self.events_max, event_count)
        self.cars_total += car_count
        self.cars_min, self.cars_max = min(self.cars_min, car_count), max(self.cars_max, car_count)
        self.tokens.update(record["token_counts"])
        self.minutes.update(record["behaviour_minutes"])
        self.entries.update(record["zone_entry_counts"])
        self.catch_days += int(record["token_counts"].get("CATCH", 0) > 0)
        for time, zone in record["next_zone_by_report_time"].items():
            self.next_zones.setdefault(time, Counter())[zone] += 1
        self.validations.append(record["validation"])

    def _mean(self, total: float) -> float:
        return round(total / self.count, 6) if self.count else 0.0

    def summary(self) -> dict[str, Any]:
        hours = {name: self._mean(self.minutes[name] / 60) for name in BEHAVIOURS}
        hours["sleeping_resting"] = self._mean((self.minutes["sleeping"] + self.minutes["resting"]) / 60)
        next_distributions = {}
        categories = TARGET_CLASSES
        for time, counts in self.next_zones.items():
            total = sum(counts.values())
            next_distributions[time] = {
                "observations": total,
                "counts": {zone: counts[zone] for zone in categories},
                "fractions": {zone: round(counts[zone] / total, 6) if total else 0.0 for zone in categories},
            }
        chases = self.tokens["CHASE_START"]
        return {
            "days_simulated": self.count,
            "events_per_day": {"mean": self._mean(self.events_total), "min": self.events_min, "max": self.events_max},
            "token_frequencies": dict(self.tokens),
            "hours_per_behaviour": hours,
            "fraction_of_days_with_catch": self._mean(self.catch_days),
            "chase_success_rate": round(self.tokens["CATCH"] / chases, 6) if chases else None,
            "chase_attempts": chases,
            "mean_zone_entries_per_zone": {zone: self._mean(count) for zone, count in self.entries.items()},
            "next_zone_after_report_time": next_distributions,
            "tourist_car_counts": {"total": self.cars_total, "per_day": {"mean": self._mean(self.cars_total), "min": self.cars_min, "max": self.cars_max}},
        }

    def validation_report(self) -> dict[str, Any]:
        days = sorted(self.validations, key=lambda record: record["day_index"])
        failed = sum(not day["valid"] for day in days)
        warnings: list[str] = []
        budgets: dict[str, dict[str, Any]] = {}
        for name, target in self.config["validation"]["hours_targets"].items():
            if name.startswith("_"):
                continue
            total = self.minutes["sleeping"] + self.minutes["resting"] if name == "resting" else self.minutes[name]
            mean = self._mean(total / 60)
            lower, upper = self.config["validation"]["hours_ranges"][name]
            within = lower <= mean <= upper
            budgets[name] = {"mean_hours": mean, "target_hours": target, "warning_range_hours": [lower, upper], "within_range": within}
            if self.count and not within:
                label = "sleeping/resting" if name == "resting" else name
                warnings.append(f"Mean {label} is {mean:.3f} h/day; reference target {target:g} h, warning range [{lower:g}, {upper:g}] h.")
        for day in days:
            warnings.extend(f"Day {day['day_index']}: {message}" for message in day["warnings"])
        return {
            "valid": failed == 0,
            "days_checked": self.count, "days_passed": self.count - failed, "days_failed": failed,
            "error_count": sum(len(day["errors"]) for day in days),
            "warnings": warnings, "behaviour_hour_checks": budgets, "days": days,
        }
