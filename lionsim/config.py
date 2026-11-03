"""Dataclass configuration, documented JSON defaults, and dotted CLI overrides."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import re
from typing import Any

from .zones import ZONE_NAMES, ZoneMap


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "default_config.json"

# Saved configurations from earlier versions remain loadable. These controls
# cannot reintroduce annotations or silently cap image coverage in a new run.
LEGACY_IMAGE_KEYS = frozenset({
    "label_color", "label_fontsize", "timestamp_fontsize", "mark_new_events",
    "highlight_recent_segment", "recent_segment_color", "event_marker_size",
    "automatic_all_days_threshold", "automatic_image_days", "annotation_mode",
    "time_label_interval_minutes", "arrow_interval_minutes", "max_event_rows",
})


# Canonical settings live under learnability; old files and CLI expressions
# are migrated before validation. Manifests store only canonical values.
LEARNABILITY_ALIASES = {
    "behaviour": "learnability.behaviour",
    "behaviours": "learnability.activity",
    "chase": "learnability.chase",
    "randomness.latent_ranges": "learnability.latent_ranges",
    "randomness.softmax_temperature": "learnability.softmax_temperature",
    "randomness.chase_base_probability": "learnability.chase_base_probability",
}


def _canonical_path(path: str) -> str:
    for old, new in LEARNABILITY_ALIASES.items():
        if path == old or path.startswith(old + "."):
            return new + path[len(old):]
    return path


def _migrate_legacy(data: dict[str, Any]) -> dict[str, Any]:
    """Explicit canonical values win over corresponding legacy file values."""
    data = deepcopy(data)
    if not isinstance(data, dict):
        raise ValueError("Configuration must be a JSON object")
    for old, new in LEARNABILITY_ALIASES.items():
        parts = old.split(".")
        parent = data
        for part in parts[:-1]:
            parent = parent.get(part, {})
            if not isinstance(parent, dict):
                break
        if not isinstance(parent, dict) or parts[-1] not in parent:
            continue
        value = parent.pop(parts[-1])
        if isinstance(parent.get("_comments"), dict):
            parent["_comments"].pop(parts[-1], None)
        destination = data.setdefault("learnability", {})
        if not isinstance(destination, dict):
            raise ValueError("learnability must be an object")
        key = new.split(".", 1)[1]
        if key not in destination:
            destination[key] = value
        elif isinstance(value, dict) and isinstance(destination[key], dict):
            destination[key] = {**value, **destination[key]}
    return data


def _defaults() -> dict[str, Any]:
    """Keep the shipped, commented JSON as the single source of default values."""
    with DEFAULT_CONFIG_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def clock_minutes(value: str) -> int:
    """Parse an exact HH:MM clock string, raising a useful configuration error."""
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}:\d{2}", value):
        raise ValueError(f"Expected an HH:MM clock time, got {value!r}")
    hour, minute = map(int, value.split(":"))
    if hour > 23 or minute > 59:
        raise ValueError(f"Clock time is outside 00:00..23:59: {value!r}")
    return hour * 60 + minute


def minute_offset(value: str, day_start: str = "05:00") -> int:
    """Clock time measured forward from day start, in the range 0..1439."""
    return (clock_minutes(value) - clock_minutes(day_start)) % 1440


@dataclass
class Config:
    """Independent, validated configuration snapshot with dataclass defaults.

    ``data`` is the complete nested mapping. ``to_dict`` returns a defensive
    deep copy suitable for worker processes and run manifests.
    """

    data: dict[str, Any] = field(default_factory=_defaults)

    def __post_init__(self) -> None:
        self.data = _migrate_legacy(self.data)
        images = self.data.get("images")
        if isinstance(images, dict):
            for key in LEGACY_IMAGE_KEYS:
                images.pop(key, None)
                if isinstance(images.get("_comments"), dict):
                    images["_comments"].pop(key, None)
        validate_config(self.data)

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(self.data)


def _merge(base: dict[str, Any], changes: dict[str, Any], prefix: str = "") -> None:
    if not isinstance(changes, dict):
        raise ValueError(f"{prefix or 'Configuration'} must be a JSON object")
    geometry_fields = {"shape", "center", "radius", "x", "y", "color"}
    for key, value in changes.items():
        path = f"{prefix}.{key}" if prefix else key
        if prefix == "images" and key in LEGACY_IMAGE_KEYS:
            continue
        if key.startswith("_"):
            base[key] = deepcopy(value)
            continue
        if key not in base:
            if prefix.startswith("map.zones.") and key in geometry_fields:
                base[key] = deepcopy(value)
                continue
            raise ValueError(f"Unknown configuration key: {path}")
        if isinstance(base[key], dict) and isinstance(value, dict):
            _merge(base[key], value, path)
        else:
            base[key] = deepcopy(value)


def _parse_override(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        # Unquoted strings such as HH:MM and hex colours are convenient on CLI.
        lowered = value.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        if lowered in {"none", "null"}:
            return None
        return value


def _override(data: dict[str, Any], expression: str) -> None:
    if "=" not in expression:
        raise ValueError(f"Override must use dotted.key=value, got {expression!r}")
    path, value_text = expression.split("=", 1)
    parts = _canonical_path(path.strip()).split(".")
    if not parts or any(not part for part in parts):
        raise ValueError(f"Invalid dotted override key: {path!r}")
    current: Any = data
    for index, part in enumerate(parts):
        final = index == len(parts) - 1
        if isinstance(current, dict):
            if part not in current:
                raise ValueError(f"Unknown configuration key in override: {path}")
            if final:
                current[part] = _parse_override(value_text)
            else:
                current = current[part]
        elif isinstance(current, list):
            if not part.isdigit() or int(part) >= len(current):
                raise ValueError(f"Invalid list index in override: {path}")
            if final:
                current[int(part)] = _parse_override(value_text)
            else:
                current = current[int(part)]
        else:
            raise ValueError(f"Cannot traverse scalar configuration value: {path}")


def load_config(path: str | Path | None = None, overrides: list[str] | None = None) -> Config:
    """Merge optional partial JSON and repeated dotted overrides into defaults."""
    data = _defaults()
    if path is not None:
        try:
            with Path(path).open(encoding="utf-8") as handle:
                custom = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot load configuration {path}: {exc}") from exc
        _merge(data, _migrate_legacy(custom))
    for expression in overrides or []:
        _override(data, expression)
    return Config(data)


def validate_config(data: dict[str, Any]) -> None:
    """Reject malformed and contradictory settings before starting a run."""
    defaults = _defaults()

    def types(value: Any, reference: Any, path: str) -> None:
        if isinstance(reference, dict):
            if not isinstance(value, dict):
                raise ValueError(f"{path or 'Configuration'} must be an object")
            for key, expected in reference.items():
                if key.startswith("_"):
                    continue
                child = f"{path}.{key}" if path else key
                if key not in value:
                    raise ValueError(f"Missing configuration key: {child}")
                # Geometry shape changes are valid; ZoneMap checks their fields.
                if path == "map.zones":
                    continue
                types(value[key], expected, child)
        elif isinstance(reference, bool):
            if not isinstance(value, bool):
                raise ValueError(f"{path} must be true or false")
        elif isinstance(reference, (int, float)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{path} must be a finite number")
            if isinstance(reference, int) and not isinstance(value, int):
                raise ValueError(f"{path} must be an integer")
        elif isinstance(reference, str):
            if not isinstance(value, str):
                raise ValueError(f"{path} must be a string")
        elif isinstance(reference, list):
            if not isinstance(value, list) or not value:
                raise ValueError(f"{path} must be a nonempty list")
            # Periods have optional flags and are validated separately below.
            if path != "goal.periods":
                for index, element in enumerate(value):
                    types(element, reference[0], f"{path}.{index}")

    types(data, defaults, "")

    def get(path: str) -> Any:
        value: Any = data
        for key in _canonical_path(path).split("."):
            value = value[key]
        return value

    def bound(path: str, low: float | None = None, high: float | None = None,
              positive: bool = False) -> None:
        value = get(path)
        if positive and value <= 0:
            raise ValueError(f"{path} must be positive")
        if low is not None and value < low or high is not None and value > high:
            raise ValueError(f"{path} must lie in [{low}, {high}], got {value}")

    def interval(path: str, low: float | None = None, high: float | None = None,
                 positive: bool = False, integer: bool = False) -> tuple[float, float]:
        value = get(path)
        if len(value) != 2:
            raise ValueError(f"{path} must contain exactly [minimum, maximum]")
        left, right = value
        if (isinstance(left, bool) or isinstance(right, bool)
                or not isinstance(left, (int, float)) or not isinstance(right, (int, float))
                or not math.isfinite(left) or not math.isfinite(right)):
            raise ValueError(f"{path} endpoints must be finite numbers")
        if integer and (not isinstance(left, int) or not isinstance(right, int)):
            raise ValueError(f"{path} endpoints must be integers")
        if left > right or positive and left <= 0 or low is not None and left < low or high is not None and right > high:
            raise ValueError(f"{path} has invalid ordered bounds: {value}")
        return left, right

    if data["time"]["day_minutes"] != 1440 or data["time"]["step_minutes"] != 1:
        raise ValueError("This simulator requires time.day_minutes=1440 and time.step_minutes=1")
    start = data["time"]["day_start"]
    clock_minutes(start)
    offsets = [minute_offset(value, start) or 1440 for value in data["time"]["report_times"]]
    if offsets != sorted(set(offsets)) or offsets[-1] != 1440:
        raise ValueError("time.report_times must be unique, chronological after day_start, and end at day_start next day")
    bound("map.entry_hysteresis_minutes", 1, 1440)
    ZoneMap(data)
    for name, zone in data["map"]["zones"].items():
        if name.startswith("_"):
            continue
        if not isinstance(zone.get("color"), str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", zone["color"]):
            raise ValueError(f"map.zones.{name}.color must be a #RRGGBB color")

    for name in ("start_hunger", "hunt_threshold"):
        interval(f"randomness.latent_ranges.{name}", 0, 1)
    interval("randomness.latent_ranges.heat", positive=True)
    for name in ("prey_density", "tourist_rate_per_hour"):
        interval(f"randomness.latent_ranges.{name}", 0)
    for name in ("wake_time_sd_minutes", "bar_noise_sd", "score_noise_sd", "walk_heading_sd_degrees", "stalk_heading_sd_degrees", "gps_noise_sd_m"):
        bound(f"randomness.{name}", 0)
    bound("randomness.softmax_temperature", positive=True)
    for name in ("gps_dropout_probability", "chase_base_probability"):
        bound(f"randomness.{name}", 0, 1)
    clips = data["randomness"]["wake_time_clip"]
    if len(clips) != 2:
        raise ValueError("randomness.wake_time_clip must contain two clock times")
    wake_min, wake_max = [minute_offset(value, start) for value in clips]
    wake_mean = minute_offset(data["randomness"]["wake_time_mean"], start)
    if not wake_min <= wake_mean <= wake_max:
        raise ValueError("randomness wake times must satisfy clip_min <= mean <= clip_max after day_start")
    car_start = minute_offset(data["tourists"]["start"], start)
    car_end = minute_offset(data["tourists"]["end"], start) or 1440
    if car_start < wake_max or car_end <= car_start:
        raise ValueError("tourists window must start at/after the latest initial wake time and end later within the simulated day, so WOKE_UP is always first")

    for name in ("initial_energy", "initial_boredom", "initial_mood", "ambient_min", "ambient_max", "mood_equilibrium"):
        bound(f"bars.{name}", 0, 1)
    if data["bars"]["ambient_min"] >= data["bars"]["ambient_max"]:
        raise ValueError("bars.ambient_min must be less than bars.ambient_max")
    if clock_minutes(data["bars"]["ambient_min_time"]) == clock_minutes(data["bars"]["ambient_max_time"]):
        raise ValueError("Ambient minimum and maximum clock times must differ")
    bound("bars.temperature_time_constant_hours", positive=True)
    for name in ("car_mood_distance_km", "mood_relaxation_per_hour"):
        bound(f"bars.{name}", 0)
    if not set(data["bars"]["cooling_zones"]) <= set(ZONE_NAMES):
        raise ValueError("bars.cooling_zones contains an unknown zone name")
    for name in ("distance_penalty_per_km", "road_penalty_per_car", "hunger_weight", "low_energy_weight", "temperature_weight", "boredom_weight"):
        bound(f"goal.{name}", 0)
    bound("goal.road_memory_minutes", 1, 1440)
    coverage = [0] * 1440
    for period in data["goal"]["periods"]:
        if not isinstance(period, dict):
            raise ValueError("Each goal.periods entry must be an object")
        left, right = clock_minutes(period.get("start")), clock_minutes(period.get("end"))
        duration = (right - left) % 1440
        if duration == 0:
            raise ValueError("Goal periods must have distinct start and end times")
        for index in range(duration):
            coverage[(left + index) % 1440] += 1
        for key in ("priors", "caught_priors"):
            if key not in period and key == "caught_priors":
                continue
            priors = period.get(key)
            if not isinstance(priors, dict) or {name for name in priors if not name.startswith("_")} != set(ZONE_NAMES):
                raise ValueError(f"Each goal period {key} must define all eight zone names")
            for name, value in priors.items():
                if name.startswith("_"):
                    continue
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError(f"Goal prior for {name} must be a finite number")
        if "hungry_hunt_only" in period and not isinstance(period["hungry_hunt_only"], bool):
            raise ValueError("goal.periods hungry_hunt_only must be a boolean")
    if any(count != 1 for count in coverage):
        raise ValueError("goal.periods must cover every clock minute exactly once, with no gaps or overlaps")

    for name in ("groom_mean_minutes", "drink_mean_minutes", "drink_gamma_shape", "eat_max_minutes"):
        bound(f"behaviours.{name}", positive=True)
    for name in ("groom_lognormal_sigma", "midday_wake_sd_minutes", "prey_encounters_per_hour"):
        bound(f"behaviours.{name}", 0)
    for name in ("cool_wake_temperature", "eat_stop_hunger"):
        bound(f"behaviours.{name}", 0, 1)
    for name in ("rest_minutes_range", "visit_minutes_range", "fail_rest_minutes_range", "catnap_minutes_range", "night_walk_minutes_range"):
        interval(f"behaviours.{name}", 1, 1440, integer=True)
    for name in ("midday_sleep_start", "midday_wake_mean", "cool_wake_after", "hunt_start", "hunt_end", "night_start"):
        clock_minutes(data["learnability"]["activity"][name])
    midday_clips = data["learnability"]["activity"]["midday_wake_clip"]
    if len(midday_clips) != 2:
        raise ValueError("behaviours.midday_wake_clip must contain two clock times")
    midday_left, midday_right = [minute_offset(value, start) for value in midday_clips]
    if not midday_left <= minute_offset(data["learnability"]["activity"]["midday_wake_mean"], start) <= midday_right:
        raise ValueError("Midday wake mean must fall within ordered midday_wake_clip bounds")
    if minute_offset(data["learnability"]["activity"]["hunt_start"], start) >= minute_offset(data["learnability"]["activity"]["hunt_end"], start):
        raise ValueError("behaviours.hunt_start must precede hunt_end in the simulated day")
    for name in ("boredom_goal_urgency", "low_mood_threshold", "detour_boredom_threshold"):
        bound(f"movement_style.{name}", 0, 1)
    for name in ("attraction_intercept", "turn_intercept", "speed_intercept"):
        bound(f"movement_style.{name}", positive=True)
    for name in ("attraction_urgency_weight", "turn_boredom_weight", "turn_urgency_weight",
                 "low_mood_turn_increment", "speed_urgency_weight", "detour_probability_scale",
                 "zone_exclusion_margin_km"):
        bound(f"movement_style.{name}", 0)
    interval("movement_style.turn_multiplier_range", positive=True)
    interval("movement_style.detour_offset_km_range", positive=True)
    interval("movement_style.detour_count_range", 1, 2, integer=True)
    bound("movement_style.waypoint_sampling_attempts", 2)
    bound("movement_style.waypoint_arrival_tolerance_km", positive=True)
    interval("movement.patrol_speed_kmh_range", positive=True)
    bound("movement.stalk_speed_kmh", positive=True)
    bound("movement.heading_persistence", 0, 1)
    if data["movement"]["heading_persistence"] == 1:
        raise ValueError("movement.heading_persistence must be less than 1 so heading can change")
    for name in ("rest_jitter_sd_m", "arrival_inset_km"):
        bound(f"movement.{name}", 0)
    for name in ("patrol_energy_weight", "patrol_heat_weight", "patrol_boredom_weight", "patrol_speed_noise_sd"):
        bound(f"movement.{name}", 0)
    if sum(data["movement"][name] for name in ("patrol_energy_weight", "patrol_heat_weight", "patrol_boredom_weight")) <= 0:
        raise ValueError("At least one patrol speed state weight must be positive")
    for name in ("minimum_boredom", "minimum_energy", "minimum_mood", "approach_probability", "avoidance_probability", "avoidance_mood_threshold"):
        bound(f"road_response.{name}", 0, 1)
    for name in ("detection_distance_km", "arrival_tolerance_km", "retreat_distance_km"):
        bound(f"road_response.{name}", positive=True)
    for name in ("approach_standoff_km", "boredom_relief_per_watch_hour"):
        bound(f"road_response.{name}", 0)
    for name in ("avoidance_car_count", "memory_minutes", "approach_max_minutes", "retreat_max_minutes", "cooldown_minutes"):
        bound(f"road_response.{name}", 1, 1440)
    for name in ("reaction_delay_minutes_range", "watch_minutes_range"):
        interval(f"road_response.{name}", 1, 1440, integer=True)
    bound("chase.speed_kmh", positive=True)
    duration = interval("chase.duration_seconds_range", 1, 59, integer=True)
    delay = interval("chase.outcome_delay_seconds_range", 1, 60, integer=True)
    if duration[0] < delay[0] or duration[1] > delay[1]:
        raise ValueError("chase.duration_seconds_range must lie inside outcome_delay_seconds_range")
    bound("chase.factor_min", 0)
    bound("chase.factor_max", positive=True)
    if data["learnability"]["chase"]["factor_min"] > data["learnability"]["chase"]["factor_max"]:
        raise ValueError("chase.factor_min cannot exceed factor_max")
    for name in ("energy_weight", "mood_weight"):
        bound(f"chase.{name}", 0)
    if data["learnability"]["chase"]["energy_weight"] + data["learnability"]["chase"]["mood_weight"] <= 0:
        raise ValueError("At least one chase energy/mood weight must be positive")
    interval("chase.probability_clip", 0, 1)
    interval("road_response.traffic_delay_minutes_range", 1, 1440, integer=True)
    for name in ("morning_scout_probability",):
        bound(f"behaviour.{name}", 0, 1)
    for name in ("scout_base_minutes", "scout_prey_extra_minutes", "scout_jitter_sd_minutes", "hunger_wake_shift_minutes", "prey_hunt_delay_max_minutes"):
        bound(f"behaviour.{name}", 0)
    left, right = interval("behaviour.prey_reference_range", 0)
    if left >= right:
        raise ValueError("prey_reference_range must have positive width")
    for name in ("prey_kopje_dwell_correlation_min", "prey_first_chase_correlation_max", "hunger_wake_correlation_max", "heat_shade_entry_correlation_max"):
        bound(f"targets.{name}", -1, 1)
    bound("targets.headline_l3_improvement_min", 0, 1)
    interval("targets.oracle_l0_ratio_range", 0, 1)
    bound("targets.oracle_l2_improvement_min", 0, 1)
    bound("movement.patrol_cruise_fraction", 0, 1)
    weights = data["learnability"]["behaviour"]["night_patrol_entry_weights"]
    if len(weights) != 3 or any(w < 0 for w in weights) or not math.isclose(sum(weights), 1):
        raise ValueError("night_patrol_entry_weights must be three nonnegative probabilities summing to one")
    interval("behaviour.night_pause_minutes_range", 1, 1440, integer=True)
    bound("behaviour.night_patrol_distance_penalty", 0)
    bound("behaviour.night_repeat_zone_weight", positive=True)
    bound("behaviour.daytime_travel_budget_minutes", 0, 1440)
    bound("behaviour.water_trip_grace_minutes", 0, 90)
    interval("targets.events_per_day", 0)
    for name in ("non_feast_late_entry_fraction_min", "feast_post_meal_entry_fraction_max"):
        bound(f"targets.{name}", 0, 1)
    for name in ("end_of_day_report_6_range", "end_of_day_report_7_range"):
        interval(f"targets.{name}", 0, 1)
    bound("movement.road_surface_speed_bonus_kmh", 0)
    for name in ("evening_road_probability", "road_daytime_multiplier"):
        bound(f"behaviour.{name}", 0, 1)
    bound("behaviour.road_volume_reference_count", 0)
    bound("behaviour.road_volume_decay", 0)
    for name in ("road_evening_start", "road_evening_end"):
        clock_minutes(data["learnability"]["behaviour"][name])
    if minute_offset(data["learnability"]["behaviour"]["road_evening_start"], start) >= minute_offset(data["learnability"]["behaviour"]["road_evening_end"], start):
        raise ValueError("road evening start must precede end")
    interval("targets.road_entry_share", 0, 1)
    bound("targets.road_tourist_correlation_max", -1, 1)
    bound("targets.road_evening_fraction_min", 0, 1)
    bound("targets.road_tourist_window_fraction_max", 0, 1)
    bound("targets.abandoned_trip_mean_max", 0)
    bound("targets.traffic_abandonment_share_max", 0, 1)
    interval("targets.waterhole_day_fraction", 0, 1)
    for name in ("fatigue_interrupt_threshold", "fatigue_recovery_threshold", "heat_interrupt_threshold", "heat_recovery_threshold", "road_entry_probability"):
        bound(f"behaviour.{name}", 0, 1)
    if data["learnability"]["behaviour"]["fatigue_interrupt_threshold"] >= data["learnability"]["behaviour"]["fatigue_recovery_threshold"]:
        raise ValueError("Fatigue recovery threshold must exceed interrupt threshold")
    if data["learnability"]["behaviour"]["heat_recovery_threshold"] >= data["learnability"]["behaviour"]["heat_interrupt_threshold"]:
        raise ValueError("Heat recovery threshold must be below interrupt threshold")
    for name in ("heat_reference", "night_nap_min_minutes", "night_nap_max_cycles", "interrupted_rest_minutes", "first_chase_wait_min_minutes", "first_chase_wait_max_minutes"):
        bound(f"behaviour.{name}", positive=True)
    if data["learnability"]["behaviour"]["first_chase_wait_min_minutes"] > data["learnability"]["behaviour"]["first_chase_wait_max_minutes"]:
        raise ValueError("First chase wait bounds must be ordered")
    for name in ("shade_entry_heat_shift_minutes", "shade_entry_jitter_sd_minutes", "shade_wake_heat_shift_minutes", "shade_wake_jitter_sd_minutes", "drink_heat_multiplier", "road_goal_boredom_weight", "road_goal_traffic_penalty", "road_entry_traffic_decay", "road_entry_inset_km"):
        bound(f"behaviour.{name}", 0)
    window = data["learnability"]["behaviour"]["shade_departure_window"]
    if len(window) != 2 or minute_offset(window[0], start) > minute_offset(window[1], start):
        raise ValueError("behaviour.shade_departure_window must contain ordered clock times")
    for name in ("evening_staging_time", "hunt_arrival_deadline"):
        clock_minutes(data["learnability"]["behaviour"][name])
    for name in ("zone_entry_share", "hunt_attempt_day_fraction", "catch_day_fraction", "road_entry_day_fraction"):
        interval(f"targets.{name}", 0, 1)
    interval("targets.zone_entries_per_day", 0)
    interval("targets.mean_walking_speed_kmh", 0)
    for name in ("unique_sequence_fraction_min", "top_five_sequence_share_max"):
        bound(f"targets.{name}", 0, 1)
    for name in data["targets"]["hours_per_behaviour"]:
        if not name.startswith("_"):
            interval(f"targets.hours_per_behaviour.{name}", 0, 24)
    bound("statistics.coverage_grid_km", positive=True)
    bound("statistics.rest_smoothing_minutes", 1, 1440)
    bound("targets.observed_true_path_ratio_max", positive=True)
    bound("targets.smoothed_rest_speed_max_kmh", positive=True)
    bound("behaviour.afternoon_water_probability", 0, 1)
    bound("learnability.oracle_days", 1)
    bound("learnability.oracle_rollouts", 1)
    bound("learnability.oracle_near_zero_nats", 0)
    bound("learnability.oracle_noise_relative_tolerance", 0, 1)
    bound("learnability.laplace_alpha", positive=True)
    bound("learnability.train_fraction", 0, 1)
    if not 0 < data["learnability"]["train_fraction"] < 1:
        raise ValueError("learnability.train_fraction must be strictly between zero and one")
    bound("learnability.l3_min_cell_count", 1)
    bound("learnability.cv_folds", 2)
    bound("learnability.l3_interpolation_k", positive=True)
    bound("learnability.shade_hour_cut", 0, 23)
    headline = data["learnability"]["headline_reports"]
    if len(headline) != len(set(headline)) or any(i < 1 or i > 7 for i in headline):
        raise ValueError("learnability.headline_reports must contain distinct report indices 1..7")
    for name in ("mostly_noise_relative_tolerance", "near_deterministic_ratio"):
        bound(f"learnability.{name}", 0, 1)
    bound("output.json_pretty_max_days", 0)
    for name in ("size_px", "dpi", "path_linewidth", "current_point_size", "contact_sheet_columns", "contact_sheet_rows"):
        bound(f"images.{name}", positive=True)
    bound("images.zone_alpha", 0, 1)
    for name in ("background_color", "path_color"):
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", data["images"][name]):
            raise ValueError(f"images.{name} must be a #RRGGBB color")
    if data["images"]["contact_sheet_columns"] * data["images"]["contact_sheet_rows"] < len(offsets):
        raise ValueError("Contact-sheet grid must have at least as many cells as report times")
    for name in data["validation"]["hours_targets"]:
        if not name.startswith("_"):
            bound(f"validation.hours_targets.{name}", 0, 24)
            interval(f"validation.hours_ranges.{name}", 0, 24)
