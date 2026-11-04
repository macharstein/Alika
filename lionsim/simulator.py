"""Minute-resolution, independent-day lion movement and collar simulation.

The state machine is deliberately explicit: it can be inspected and adjusted
without a learned model. Positions are in kilometres and bars are unitless.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import math
from typing import Any

import numpy as np
import pandas as pd

from .config import Config
from .movement_style import plan_style
from .weather import draw_weather, ambient_measurements
from .events import ZONE_TOKENS, append_event, sort_events
from .zones import HysteresisTracker, ZoneMap


_CURRENT_ZONE = object()


@dataclass
class DayResult:
    """One independent day, ready for reports and streaming to disk."""

    day_index: int
    date: str
    seed_info: dict[str, Any]
    latents: dict[str, Any]
    events: list[dict[str, Any]]
    gps: pd.DataFrame
    hidden_state: pd.DataFrame
    traffic_times: list[str] = field(default_factory=list)
    weather: str | None = None


def _clock_minutes(value: str) -> int:
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def _angle_difference(target: float, source: float) -> float:
    return (target - source + math.pi) % (2 * math.pi) - math.pi


def _reflect(value: float, limit: float) -> float:
    """Reflect a displacement at map edges, including unusually large steps."""
    folded = value % (2 * limit)
    return folded if folded <= limit else 2 * limit - folded


class _DaySimulation:
    def __init__(
        self, config: Config, day_index: int, seed: int,
        start_date: str, sequence: np.random.SeedSequence,
    ) -> None:
        self.config = config
        self.c = config.data
        self.learnability = self.c["learnability"]
        self.randomness = self.c["randomness"]
        self.bar_config = self.c["bars"]
        self.behaviours = self.learnability["activity"]
        self.behaviour = self.learnability["behaviour"]
        self.movement = self.c["movement"]
        self.road_config = self.c["road_response"]
        self.goal_config = self.c["goal"]
        self.rng = np.random.default_rng(sequence)
        self.sequence = sequence
        self.seed = seed
        self.day_index = day_index
        self.start_clock = _clock_minutes(self.c["time"]["day_start"])
        self.day_minutes = self.c["time"]["day_minutes"]
        simulated_date = date.fromisoformat(start_date) + timedelta(days=day_index - 1)
        self.start = datetime.combine(simulated_date, datetime.min.time()) + timedelta(minutes=self.start_clock)
        self.zones = ZoneMap(config)
        self.zone_names = list(ZONE_TOKENS)
        self.geometry = self.c["map"]["zones"]
        self.centres = {name: self._centre(name) for name in self.zone_names}
        self.position = self.centres["Den"].copy()
        self.heading = float(self.rng.uniform(-math.pi, math.pi))
        self.tracker = HysteresisTracker(
            required_minutes=self.c["map"]["entry_hysteresis_minutes"], initial_zone="Den",
        )
        self.events: list[dict[str, Any]] = []
        self.latents = {
            name: float(self.rng.uniform(*bounds))
            for name, bounds in self.learnability["latent_ranges"].items()
            if not name.startswith("_")
        }
        self.weather, self.latents['heat'] = draw_weather(self.rng, self.c['weather'])
        weather_effects = self.c['weather'].get(self.weather, {})
        self.water_goal_bonus = weather_effects.get('water_goal_bonus', 0.)
        self.water_visit_multiplier = weather_effects.get('water_visit_multiplier', 1.)
        self.latents['tourist_rate_per_hour'] *= weather_effects.get('traffic_multiplier', 1.)
        types = self.c['day_types']
        self.day_type = str(self.rng.choice(list(types['probabilities']), p=list(types['probabilities'].values())))
        self.latents['day_type'] = self.day_type
        self.period_jitter = {name: int(self.rng.integers(-self.randomness['period_jitter_minutes'], self.randomness['period_jitter_minutes'] + 1))
                              for name in ('midday', 'hunt', 'tourist')}
        self.latents['period_jitter_minutes'] = self.period_jitter.copy()
        self.hunt_window_start = max(self.offset(self.behaviours['hunt_start']), self.offset(self.behaviours['hunt_start']) + self.period_jitter['hunt'])
        self.tourist_start_minute = int(np.clip(self.offset(self.c['tourists']['start']) + self.period_jitter['tourist'], 0, self.offset(self.c['tourists']['end']) - 1))
        self.latents["tourist_start_minute"] = self.tourist_start_minute
        self.rival_patrol_goal = None
        self.rival_patrol_remaining = 0
        if self.day_type == 'prey_rich':
            self.latents['prey_density'] *= float(self.rng.uniform(*types['prey_rich']['prey_multiplier_range']))
            self.latents['hunt_threshold'] = max(0., self.latents['hunt_threshold'] - types['prey_rich']['hunt_threshold_reduction'])
        elif self.day_type == 'rival':
            self.water_goal_bonus += types['rival']['water_goal_bonus']
            self.water_visit_multiplier *= types['rival']['water_visit_multiplier']
            low, high = types['rival']['extra_patrol_entries_range']
            self.rival_patrol_remaining = int(self.rng.integers(low, high + 1))
        self.latents['rival_extra_patrol_plan'] = self.rival_patrol_remaining
        self.true_ambient_c, self.observed_ambient_c = ambient_measurements(
            [self.ambient(t) for t in range(self.day_minutes + 1)], self.latents['heat'],
            self.bar_config, self.c['weather'], self.rng)
        prey_low, prey_high = self.behaviour["prey_reference_range"]
        self.prey_signal = float(np.clip((self.latents["prey_density"] - prey_low) / (prey_high - prey_low), 0, 1))
        self.hunt_ready_minute = self.offset(self.behaviours["hunt_start"]) + int(round((1 - self.prey_signal) * self.behaviour["prey_hunt_delay_max_minutes"]))
        self.hunt_ready_minute += self.period_jitter['hunt']
        if self.day_type == 'prey_rich':
            self.hunt_ready_minute -= types['prey_rich']['hunt_advance_minutes']
        self.hunt_ready_minute = max(self.hunt_window_start, min(self.hunt_ready_minute, self.offset(self.behaviours['hunt_end']) - 1))
        wake_clip = [self.offset(t) for t in self.randomness["wake_time_clip"]]
        wake_minutes = float(np.clip(
            self.rng.normal(self.offset(self.randomness["wake_time_mean"]) - self.latents["start_hunger"] * self.behaviour["hunger_wake_shift_minutes"], self.randomness["wake_time_sd_minutes"]),
            *wake_clip,
        ))
        self.wake_seconds = int(round(wake_minutes * 60))
        self.latents["wake_time"] = (self.start + timedelta(seconds=self.wake_seconds)).isoformat(timespec="seconds")
        self.bars = np.array([
            self.latents["start_hunger"], self.bar_config["initial_energy"],
            self.ambient(0) * self.latents["heat"], self.bar_config["initial_boredom"],
            self.bar_config["initial_mood"],
        ], dtype=float)
        self.bars = np.clip(self.bars, 0, 1)
        self.mode = "initial_sleep"
        self.goal = "Den"
        self.until = 0
        self.caught = False
        self.midday_slept = False
        self.morning_scout_considered = False
        self.morning_scout_completed = False
        self.hungry_day = self.latents["start_hunger"] > self.latents["hunt_threshold"]
        self.hunt_departed = False
        self.chase_count = 0
        self.first_chase_due: int | None = None
        self.evening_staged = False
        self.shade_trip_started = False
        self.night_nap_count = 0
        self.night_patrol_remaining: int | None = None
        self.night_visited: set[str] = set()
        self.night_water_pause = False
        self.night_pause_until = 0
        self.daytime_walking_minutes = 0
        self.nap_start_second = 0
        self.afternoon_visit_chosen = False
        self.evening_road_considered = False
        self.fatigue_latched = False
        self.heat_latched = False
        self.rest_after_arrival = False
        self.abandoned_goal_this_minute: str | None = None
        self.abandoned_reason_this_minute: str | None = None
        self.arriving = False
        self.minute = 0
        self.raw_zone: str | None = "Den"
        self.previous_zone: str | None = "Den"
        self.entered_this_minute = False
        self.car_seconds = self._cars()
        self.car_minute_counts = np.bincount(self.car_seconds // 60, minlength=self.day_minutes)
        self.car_pointer = 0
        # Road responses are short, interruptible excursions from the ordinary
        # destination. A passed car schedules a future response; it never changes
        # the sample recorded before that car's timestamp.
        self.heard_car_seconds: list[int] = []
        self.road_pending: dict[str, Any] | None = None
        self.road_target: np.ndarray | None = None
        self.road_resume_goal: str | None = None
        self.road_trigger_second: int | None = None
        self.road_until = 0
        self.road_cooldown_until = 0
        self.traffic_resume_mode = "walking"
        self.traffic_resume_until = 0
        self.delayed_by_traffic_this_minute = False
        # Heat shifts both shade seeking and wake timing, leaving observable cues.
        heat_difference = self.latents["heat"] - self.behaviour["heat_reference"]
        departure_clip = [self.offset(t) for t in self.behaviour["shade_departure_window"]]
        self.shade_departure = int(round(float(np.clip(
            self.offset(self.behaviours["midday_sleep_start"])
            - heat_difference * self.behaviour["shade_entry_heat_shift_minutes"]
            + self.rng.normal(0, self.behaviour["shade_entry_jitter_sd_minutes"]),
            *departure_clip,
        ))))
        midday_clip = [self.offset(t) for t in self.behaviours["midday_wake_clip"]]
        self.midday_wake = int(round(float(np.clip(
            self.offset(self.behaviours["midday_wake_mean"])
            + heat_difference * self.behaviour["shade_wake_heat_shift_minutes"]
            + self.rng.normal(0, self.behaviour["shade_wake_jitter_sd_minutes"]),
            *midday_clip,
        ))))

        self.shade_departure += self.period_jitter['midday']
        self.midday_wake += self.period_jitter['midday']
        if self.weather == 'rain':
            self.shade_departure += self.c['weather']['rain']['shade_delay_minutes']
            self.midday_wake = max(self.shade_departure + 1, self.midday_wake - self.c['weather']['rain']['wake_advance_minutes'])

        true_positions = np.zeros((self.day_minutes + 1, 2), dtype=float)
        bar_values = np.zeros((self.day_minutes, 5), dtype=float)
        behaviours: list[str] = []
        goals: list[str] = []
        zones: list[str | None] = []
        intents: list[str] = []
        road_triggers: list[str | None] = []
        road_distances: list[float] = []
        abandoned_goals: list[str | None] = []
        abandoned_reasons: list[str | None] = []
        patrol_speeds: list[float | None] = []
        self.history = {
            "true_positions": true_positions,
            "bar_values": bar_values,
            "behaviours": behaviours,
            "goals": goals,
            "zones": zones,
            "intents": intents,
            "road_triggers": road_triggers,
            "road_distances": road_distances,
            "abandoned_goals": abandoned_goals,
            "abandoned_reasons": abandoned_reasons,
            "patrol_speeds": patrol_speeds,
        }
        self.history["traffic_delays"] = []
        self.history["trip_rows"] = []
        self.trip: dict[str, Any] | None = None
        self.trip_count = 0
        self.next_minute = 0

    def _finish_trip(self, status: str) -> None:
        if self.trip is not None:
            rows = self.history["trip_rows"]
            if rows and rows[-1].get("trip_id") == self.trip["id"]:
                rows[-1]["trip_status"] = status
                rows[-1]["trip_end_minute"] = self.minute
            self.trip = None

    def _sync_trip(self) -> None:
        """Departure freezes style; temporary traffic responses retain it."""
        continuing = self.mode in ("walking", "traffic_wait", "road_approach", "road_retreat", "road_watch")
        if self.trip is not None and (self.trip["goal"] != self.goal or not continuing):
            self._finish_trip("interrupted")
        if self.trip is None and self.mode == "walking" and self.raw_zone != self.goal:
            target = self._travel_target().copy()
            self.trip_count += 1
            self.trip = {"id": self.trip_count, "goal": self.goal,
                         "start": self.position.copy(), "target": target,
                         "start_minute": self.minute, "distance": 0., "waypoint_index": 0,
                         "style": plan_style(self.config, self.zones, self.goal, self.bars,
                                             self.position, target, self.rng)}
            style = self.trip['style']
            first_target = style.waypoints[0] if style.waypoints else target
            bearing = math.atan2(first_target[1] - self.position[1], first_target[0] - self.position[0])
            alignment = self.c['movement_style']['departure_alignment_weight'] * style.urgency
            self.heading += alignment * _angle_difference(bearing, self.heading)

    def _move_trip(self) -> None:
        if self.trip is None:
            self._move(self._travel_target(), self._patrol_speed(), self.randomness["walk_heading_sd_degrees"])
            return
        trip = self.trip
        style = trip["style"]
        tolerance = self.c["movement_style"]["waypoint_arrival_tolerance_km"]
        while trip["waypoint_index"] < len(style.waypoints):
            waypoint = style.waypoints[trip["waypoint_index"]]
            if float(np.linalg.norm(waypoint - self.position)) > tolerance:
                break
            trip["waypoint_index"] += 1
        intermediate = trip["waypoint_index"] < len(style.waypoints)
        target = style.waypoints[trip["waypoint_index"]] if intermediate else trip["target"]
        speed = float(np.clip(self._patrol_speed() * style.speed_multiplier,
                              *self.movement["patrol_speed_kmh_range"]))
        self._move(target, speed, style.turn_sd_degrees,
                   max_step_km=float(np.linalg.norm(target - self.position)) if intermediate else None,
                   goal_attraction=style.goal_attraction)

    def _record_trip_step(self, before: np.ndarray) -> None:
        row: dict[str, Any] = {}
        if self.trip is not None:
            trip, style = self.trip, self.trip["style"]
            trip["distance"] += float(np.linalg.norm(self.position - before))
            chord = float(np.linalg.norm(self.position - trip["start"]))
            row = {"trip_id": trip["id"], "trip_goal": trip["goal"],
                   "trip_start_minute": trip["start_minute"], "trip_end_minute": None,
                   "trip_urgency": style.urgency, "trip_boredom": style.boredom, "trip_mood": style.mood,
                   "trip_detour_count": len(style.waypoints),
                   "trip_planned_straightness": style.planned_straightness,
                   "trip_realized_straightness": min(1., chord / trip["distance"]) if trip["distance"] > 0 else None,
                   "trip_goal_attraction": style.goal_attraction, "trip_turn_sd_degrees": style.turn_sd_degrees,
                   "trip_speed_multiplier": style.speed_multiplier,
                   "trip_path_length_km": trip["distance"], "trip_status": "in_progress"}
        self.history["trip_rows"].append(row)

    def _record_abandoned_trip(self, reason: str) -> None:
        """Record an interrupted journey once, at the minute of the decision."""
        if self.mode in ("walking", "traffic_wait") and self.raw_zone != self.goal:
            self.abandoned_goal_this_minute = self.goal
            self.abandoned_reason_this_minute = reason
        elif self.mode in ("road_approach", "road_retreat"):
            self.abandoned_goal_this_minute = "Road" if self.mode == "road_approach" else self.goal
            self.abandoned_reason_this_minute = reason

    def _commit_goal(self, goal: str, reason: str | None = None) -> None:
        if reason is not None and (self.goal != goal or self.mode.startswith("road_")):
            self._record_abandoned_trip(reason)
        self.goal, self.mode, self.arriving = goal, "walking", False
        if reason is not None and reason != "fatigue":
            self.rest_after_arrival = False
        self.road_pending = None
        self.road_target = None
        self.road_resume_goal = None
        self.road_trigger_second = None

    def _scheduled_interrupts(self) -> None:
        """Only explicit physiological or clock triggers can cancel a journey."""
        if self.bars[1] >= self.behaviour["fatigue_recovery_threshold"]:
            self.fatigue_latched = False
        if self.bars[2] <= self.behaviour["heat_recovery_threshold"]:
            self.heat_latched = False
        if self.caught or self.mode in ("initial_sleep", "final_sleep", "eating", "midday_sleep", "fatigue_sleep", "catnap", "night_final_sleep", "night_rest"):
            return
        if self._is_night() and self.night_patrol_remaining is None and self.mode == "resting":
            if self.raw_zone in ("Den", "Plain"):
                self._night_pause()
            else:
                self._choose_night_goal()
            return
        cutoff = self.offset(self.behaviours["hunt_end"])
        if self.minute >= cutoff and (self.mode in ("hunting", "fail_rest") or self.goal == "Hunting ground"):
            if not self._try_evening_road("hunt_cutoff"):
                self._commit_goal("Plain", "hunt_cutoff")
            return
        if self.mode in ("grooming", "drinking"):
            return
        if self.hungry_day and self._can_hunt() and not self.hunt_departed:
            if (self.goal == "Waterhole" and self.mode in ("walking", "traffic_wait")
                    and self.minute < self.offset(self.behaviours["hunt_start"]) + self.behaviour["water_trip_grace_minutes"]):
                return
            self.hunt_departed = True
            self._commit_goal("Hunting ground", "evening_hunt_window")
            return
        if self.hungry_day and not self.evening_staged and self.offset(self.behaviour["evening_staging_time"]) <= self.minute < self.offset(self.behaviours["hunt_start"]):
            if self.mode in ("walking", "traffic_wait") and self.goal in ("Road", "Waterhole") and self.raw_zone != self.goal:
                return
            self.evening_staged = True
            self._commit_goal("Plain", "evening_staging")
            return
        if not self.shade_trip_started and not self.midday_slept and self.shade_departure <= self.minute < self.midday_wake:
            self.shade_trip_started = True
            self._commit_goal("Shade", "midday_heat_schedule")
            return
        # Feeding and the committed evening hunt are complete action sequences;
        # physiological interrupts are applied to other daytime patrol journeys.
        if self.mode != "walking" or self._is_night() or self.goal in ("Shade", "Hunting ground"):
            return
        if self.goal != "Waterhole" and self.bars[2] > self.behaviour["heat_interrupt_threshold"] and not self.heat_latched:
            self.heat_latched = True
            self._commit_goal("Shade", "temperature")
        elif self.bars[1] < self.behaviour["fatigue_interrupt_threshold"] and not self.fatigue_latched:
            self.fatigue_latched = True
            resting_zone = min(("Den", "Shade", "Plain"), key=lambda name: self.zones.distance_to(name, *self.position))
            self.rest_after_arrival = True
            self._commit_goal(resting_zone, "fatigue")

    def offset(self, clock_time: str) -> int:
        return (_clock_minutes(clock_time) - self.start_clock) % 1440

    def _centre(self, name: str) -> np.ndarray:
        return np.asarray(self.zones.center(name), dtype=float)

    def _contains(self, name: str, point: np.ndarray) -> bool:
        return self.zones.contains(name, float(point[0]), float(point[1]))

    def _lookup(self, point: np.ndarray) -> str | None:
        return self.zones.lookup(float(point[0]), float(point[1]))

    def _road_distance(self) -> float:
        return self.zones.distance_to("Road", float(self.position[0]), float(self.position[1]))

    def _nearest_road_boundary(self) -> tuple[np.ndarray, np.ndarray]:
        """Nearest boundary point and an outward unit vector, for either shape."""
        road = self.geometry["Road"]
        if road["shape"] == "circle":
            centre = np.asarray(road["center"], dtype=float)
            vector = self.position - centre
            distance = float(np.linalg.norm(vector))
            normal = vector / distance if distance > 1e-12 else np.array([-1.0, 0.0])
            if distance <= road["radius"]:
                # Near an outer map edge, a radial escape may be impossible.
                # Include circle/map intersections to find the nearest feasible
                # point at the requested standoff, rather than clipping inward.
                radius = road["radius"] + self.road_config["approach_standoff_km"]
                candidates = [normal, np.array([-1., 0.]), np.array([1., 0.]),
                              np.array([0., -1.]), np.array([0., 1.])]
                limits = [self.c["map"]["width_km"], self.c["map"]["height_km"]]
                for axis in (0, 1):
                    for edge in (0., limits[axis]):
                        component = (edge - centre[axis]) / radius
                        if abs(component) <= 1:
                            other = math.sqrt(max(0., 1 - component * component))
                            for sign in (-1, 1):
                                candidate = np.zeros(2)
                                candidate[axis], candidate[1 - axis] = component, sign * other
                                candidates.append(candidate)
                feasible = [candidate for candidate in candidates
                            if np.all(centre + radius * candidate >= -1e-12)
                            and np.all(centre + radius * candidate <= np.asarray(limits) + 1e-12)]
                if feasible:
                    normal = min(feasible, key=lambda candidate: float(np.linalg.norm(centre + radius * candidate - self.position)))
            return centre + normal * road["radius"], normal
        low = np.array([road["x"][0], road["y"][0]])
        high = np.array([road["x"][1], road["y"][1]])
        point = np.clip(self.position, low, high)
        vector = self.position - point
        distance = float(np.linalg.norm(vector))
        if distance > 1e-12:
            return point, vector / distance
        # Inside/on the road, the closest edge determines the escape direction.
        margins = [self.position[0] - low[0], high[0] - self.position[0],
                   self.position[1] - low[1], high[1] - self.position[1]]
        normals = np.array([[-1., 0.], [1., 0.], [0., -1.], [0., 1.]])
        limits = np.array([self.c["map"]["width_km"], self.c["map"]["height_km"]])
        targets = [self.position + normal * (margin + self.road_config["approach_standoff_km"])
                   for normal, margin in zip(normals, margins)]
        feasible = [edge for edge, target in enumerate(targets)
                    if np.all(target >= 0) and np.all(target <= limits)]
        edge = min(feasible, key=lambda index: margins[index]) if feasible else int(np.argmin(margins))
        normal = normals[edge]
        return self.position + normal * margins[edge], normal

    def _patrol_speed(self) -> float:
        """Bounded pace retains information about the preceding internal state."""
        c = self.movement
        weights = (c["patrol_energy_weight"], c["patrol_heat_weight"], c["patrol_boredom_weight"])
        condition = (weights[0] * self.bars[1] + weights[1] * (1 - self.bars[2])
                     + weights[2] * self.bars[3]) / sum(weights)
        condition = float(np.clip(condition + self.rng.normal(0, c["patrol_speed_noise_sd"]), 0, 1))
        low, high = c["patrol_speed_kmh_range"]
        condition = c["patrol_cruise_fraction"] + (1 - c["patrol_cruise_fraction"]) * condition
        speed = low + (high - low) * condition
        if self.goal == "Hunting ground" and self._can_hunt():
            remaining = max(1, self.offset(self.behaviour["hunt_arrival_deadline"]) - self.minute)
            required = self.zones.distance_to("Hunting ground", *self.position) * 60 / remaining
            speed = max(speed, min(high, required))
        if self.raw_zone == "Road":
            speed = min(high, speed + c["road_surface_speed_bonus_kmh"])
        return speed

    def _road_time_multiplier(self) -> float:
        start = max(self.offset(self.behaviour["road_evening_start"]), self.offset(self.c["tourists"]["end"]))
        return 1.0 if start <= self.minute < self.offset(self.behaviour["road_evening_end"]) else self.behaviour["road_daytime_multiplier"]

    def _evening_road_probability(self) -> float:
        seen = int(np.count_nonzero(self.car_seconds < self.minute * 60))
        excess = max(0, seen - self.behaviour["road_volume_reference_count"])
        return float(self.behaviour["evening_road_probability"] * self.bars[3]
                     * math.exp(-self.behaviour["road_volume_decay"] * excess))

    def _try_evening_road(self, reason: str | None = None) -> bool:
        if self.caught or self.evening_road_considered or self._can_hunt() or self._road_time_multiplier() != 1.0:
            return False
        self.evening_road_considered = True
        if self.rng.random() < self._evening_road_probability():
            self._commit_goal("Road", reason)
            return True
        return False

    def _travel_target(self) -> np.ndarray:
        if self.goal == "Road" and self.raw_zone != "Road":
            point, normal = self._nearest_road_boundary()
            return point - normal * self.behaviour["road_entry_inset_km"]
        return self.centres[self.goal]

    def _consider_car_response(self, elapsed_seconds: int) -> None:
        """React only to cars that have already passed within hearing distance.

        This is a synthetic, configurable curiosity/aversion mechanism. No
        future car count is consulted, and protected activities are not paused.
        """
        c = self.road_config
        if not c["enabled"] or self._road_distance() > c["detection_distance_km"]:
            return
        self.heard_car_seconds.append(elapsed_seconds)
        oldest = elapsed_seconds - 60 * c["memory_minutes"]
        self.heard_car_seconds = [second for second in self.heard_car_seconds if second >= oldest]
        responding = self.mode in ("road_approach", "road_watch")
        if self.caught or self.mode not in ("walking", "resting", "road_approach", "road_watch"):
            return
        if self.road_pending is not None or (not responding and self.minute < self.road_cooldown_until):
            return
        bored = self.bars[3] >= c["minimum_boredom"]
        energetic = self.bars[1] >= c["minimum_energy"]
        pressured = (self.bars[4] <= c["avoidance_mood_threshold"]
                     or len(self.heard_car_seconds) >= c["avoidance_car_count"])
        # Curiosity cannot freely cancel an ordinary committed journey. A
        # nearby aversive stimulus is an explicit interruption, logged below.
        committed = self.behaviour["goal_commitment"] and self.mode == "walking"
        volume = max(0.0, self.latents["tourist_rate_per_hour"]
                     - self.learnability["latent_ranges"]["tourist_rate_per_hour"][0])
        traffic_discount = math.exp(-self.behaviour["road_entry_traffic_decay"] * volume)
        kind: str | None = None
        if pressured and self.rng.random() < c["avoidance_probability"]:
            kind = "traffic_wait" if c["traffic_wait_enabled"] else "road_retreat"
        elif not responding and not committed and bored and energetic and self.bars[4] >= c["minimum_mood"]:
            if self.rng.random() < c["approach_probability"] * traffic_discount:
                kind = "road_approach"
        if kind is None:
            return
        delay = int(self.rng.integers(c["reaction_delay_minutes_range"][0],
                                      c["reaction_delay_minutes_range"][1] + 1))
        self.road_pending = {"kind": kind, "start_minute": self.minute + delay,
                             "trigger_second": elapsed_seconds}

    def _finish_road_response(self) -> None:
        """Return to the saved destination using normal travel and arrival rules."""
        if self.road_resume_goal is not None:
            self.goal = self.road_resume_goal
        self.mode, self.arriving = "walking", False
        self.road_pending = None
        self.road_target = None
        self.road_resume_goal = None
        self.road_trigger_second = None
        self.road_cooldown_until = self.minute + self.road_config["cooldown_minutes"]

    def _advance_road_response(self) -> bool:
        """Activate delayed responses and advance approach, watching, and recovery."""
        c = self.road_config
        if self.road_pending is not None and self.minute >= self.road_pending["start_minute"]:
            pending, self.road_pending = self.road_pending, None
            if not self.caught and self.mode in ("walking", "resting", "road_approach", "road_watch"):
                self.delayed_by_traffic_this_minute = pending["kind"] in ("traffic_wait", "road_retreat")
                previous_mode, previous_until = self.mode, self.until
                if pending["kind"] == "traffic_wait":
                    self.traffic_resume_mode = previous_mode if previous_mode in ("walking", "resting") else "walking"
                    self.traffic_resume_until = previous_until
                if self.road_resume_goal is None:
                    self.road_resume_goal = self.goal
                point, normal = self._nearest_road_boundary()
                self.road_trigger_second = pending["trigger_second"]
                self.mode, self.arriving = pending["kind"], False
                if self.mode == "traffic_wait":
                    length = int(self.rng.integers(c["traffic_delay_minutes_range"][0], c["traffic_delay_minutes_range"][1] + 1))
                    self.road_until = self.minute + length
                    self.traffic_resume_until += length
                    return True
                if self.mode == "road_approach":
                    volume = max(0.0, self.latents["tourist_rate_per_hour"]
                                 - self.learnability["latent_ranges"]["tourist_rate_per_hour"][0])
                    entry_probability = self.behaviour["road_entry_probability"] * self._road_time_multiplier() * math.exp(-self.behaviour["road_entry_traffic_decay"] * volume)
                    enter = self.rng.random() < entry_probability
                    standoff = -self.behaviour["road_entry_inset_km"] if enter else c["approach_standoff_km"]
                    self.road_target = point + normal * standoff
                    self.road_until = self.minute + c["approach_max_minutes"]
                else:
                    self.road_target = self.position + normal * c["retreat_distance_km"]
                    self.road_until = self.minute + c["retreat_max_minutes"]
                self.road_target = np.clip(self.road_target, [0, 0],
                                            [self.c["map"]["width_km"], self.c["map"]["height_km"]])
        if self.mode == "traffic_wait":
            if self.minute < self.road_until:
                return True
            mode, until = self.traffic_resume_mode, self.traffic_resume_until
            self._finish_road_response()
            self.mode, self.until = mode, until
            return False
        if self.mode == "road_watch":
            if self.minute >= self.road_until:
                self._finish_road_response()
                return False
            return True
        if self.mode not in ("road_approach", "road_retreat"):
            return False
        assert self.road_target is not None
        reached = float(np.linalg.norm(self.position - self.road_target)) <= c["arrival_tolerance_km"]
        if reached and self.mode == "road_approach":
            self.mode = "road_watch"
            self.road_until = self.minute + int(self.rng.integers(c["watch_minutes_range"][0],
                                                                c["watch_minutes_range"][1] + 1))
        elif reached or self.minute >= self.road_until:
            self._finish_road_response()
            return False
        return True

    def ambient(self, minute: int) -> float:
        """Two joined cosine arcs: smooth minimum at 05:00, maximum at 14:00."""
        c = self.bar_config
        low = _clock_minutes(c["ambient_min_time"])
        high = _clock_minutes(c["ambient_max_time"])
        phase = (self.start_clock + minute - low) % 1440
        rising = (high - low) % 1440
        if phase <= rising:
            fraction = (1 - math.cos(math.pi * phase / rising)) / 2
        else:
            fraction = (1 + math.cos(math.pi * (phase - rising) / (1440 - rising))) / 2
        return c["ambient_min"] + fraction * (c["ambient_max"] - c["ambient_min"])

    def emit(self, token: str, second: int | None = None, zone: Any = _CURRENT_ZONE) -> None:
        if second is None:
            second = int(self.rng.integers(12, 60))
        append_event(self.events, self.start, self.minute * 60 + second, token,
                     self.raw_zone if zone is _CURRENT_ZONE else zone)

    def duration(self, key: str) -> int:
        low, high = self.behaviours[key]
        return max(1, int(round(float(self.rng.uniform(low, high)))))

    def _cars(self) -> np.ndarray:
        start = self.tourist_start_minute * 60
        end = self.offset(self.c["tourists"]["end"]) * 60
        if end <= start:
            end += 86400
        # Config validation ensures the window fits inside this independent day.
        count = int(self.rng.poisson(self.latents["tourist_rate_per_hour"] * (end - start) / 3600))
        seconds = np.sort(self.rng.uniform(start, end, count).astype(np.int64))
        return seconds[(seconds >= 0) & (seconds < self.day_minutes * 60)]

    def _is_night(self) -> bool:
        return self.minute >= self.offset(self.behaviours["night_start"])

    def _can_hunt(self) -> bool:
        return (
            self.hunt_ready_minute <= self.minute < self.offset(self.behaviours["hunt_end"])
            and self.hungry_day and not self.caught
            and (self.day_type != "prey_rich" or self.chase_count < self.c["day_types"]["prey_rich"]["max_chase_attempts"])
        )

    def _period(self) -> dict[str, Any]:
        clock = (self.start_clock + self.minute) % 1440
        def shifted(clock):
            shift = (self.period_jitter['midday'] if clock in (self.behaviours['midday_sleep_start'], self.behaviours['midday_wake_mean'])
                     else self.period_jitter['hunt'] if clock == self.behaviours['hunt_start'] else 0)
            return (_clock_minutes(clock) + shift) % 1440
        for period in self.goal_config["periods"]:
            first, last = shifted(period["start"]), shifted(period["end"])
            if (first < last and first <= clock < last) or (first >= last and (clock >= first or clock < last)):
                return period
        raise ValueError("Goal period table does not cover this clock time")

    def _initialize_night_patrol(self) -> None:
        if self.night_patrol_remaining is None:
            self.night_patrol_remaining = int(self.rng.choice([1, 2, 3], p=self.behaviour["night_patrol_entry_weights"]))

    def _choose_night_goal(self) -> None:
        self._initialize_night_patrol()
        if self.night_patrol_remaining <= 0:
            self._night_pause(terminal=True)
            return
        if self._try_evening_road():
            return
        candidates = [name for name in ("Plain", "Kopje", "Den", "Waterhole")
                      if name != self.tracker.considered_zone and name != self.raw_zone]
        scores = np.array([-self.behaviour["night_patrol_distance_penalty"] * self.zones.distance_to(name, *self.position)
                           + (self.water_goal_bonus if name == "Waterhole" else 0.)
                           + (math.log(self.behaviour["night_repeat_zone_weight"]) if name in self.night_visited else 0)
                           for name in candidates])
        weights = np.exp(scores - scores.max())
        self._commit_goal(str(self.rng.choice(candidates, p=weights / weights.sum())))

    def _night_pause(self, terminal: bool = False) -> None:
        self._initialize_night_patrol()
        minimum = self.behaviour["night_nap_min_minutes"]
        terminal = terminal or self.night_patrol_remaining <= 0
        safe = self.raw_zone in ("Den", "Plain")
        length = int(self.rng.integers(self.behaviour["night_pause_minutes_range"][0], self.behaviour["night_pause_minutes_range"][1] + 1))
        if not safe or self.day_minutes - self.minute <= minimum or self.night_nap_count >= self.behaviour["night_nap_max_cycles"]:
            self.mode = "night_rest"
            self.until = self.day_minutes if terminal or self.night_nap_count >= self.behaviour["night_nap_max_cycles"] else min(self.day_minutes, self.minute + length)
            return
        self.nap_start_second = int(self.rng.integers(12, 60))
        self.emit("FELL_ASLEEP", self.nap_start_second)
        self.night_nap_count += 1
        if terminal or self.night_nap_count >= self.behaviour["night_nap_max_cycles"] or self.day_minutes - self.minute < length + minimum:
            self.mode, self.until = "night_final_sleep", self.day_minutes
        else:
            nap_length = max(minimum, self.duration("catnap_minutes_range"))
            self.night_pause_until = min(self.day_minutes, self.minute + max(length, nap_length))
            self.mode, self.until = "catnap", self.minute + nap_length

    def choose_goal(self) -> None:
        """Draw a destination from the configured noisy, distance-aware logits."""
        if self.caught:
            self.goal, self.mode, self.arriving = "Feeding spot", "walking", False
            return
        if self._is_night():
            self._choose_night_goal()
            return
        if not self.morning_scout_considered and not self.midday_slept and self.minute < self.shade_departure:
            self.morning_scout_considered = True
            if self.rng.random() < self.behaviour["morning_scout_probability"]:
                self._commit_goal("Kopje")
                return
        if self.hungry_day and self.offset(self.behaviours["hunt_start"]) <= self.minute < self.hunt_ready_minute and self.raw_zone is not None:
            self.goal, self.mode, self.until = self.raw_zone, "resting", self.hunt_ready_minute
            return
        if (self.rival_patrol_remaining and self.morning_scout_considered
                and self.minute < self.offset(self.behaviour['evening_staging_time'])
                and (self.minute < self.shade_departure or self.midday_slept)):
            candidates = [z for z in self.c['day_types']['rival']['patrol_zones'] if z not in (self.raw_zone, self.tracker.considered_zone)]
            self.rival_patrol_goal = str(self.rng.choice(candidates))
            self._commit_goal(self.rival_patrol_goal)
            return
        if self._try_evening_road():
            return
        if self.midday_slept and not self.afternoon_visit_chosen and self.minute < self.offset(self.behaviour["evening_staging_time"]):
            self.afternoon_visit_chosen = True
            volume = self.latents["tourist_rate_per_hour"]
            low_volume = self.learnability["latent_ranges"]["tourist_rate_per_hour"][0]
            chance = self.behaviour["road_entry_probability"] * self._road_time_multiplier() * self.bars[3] * math.exp(-self.behaviour["road_entry_traffic_decay"] * max(0, volume - low_volume))
            if self.rng.random() < chance:
                self._commit_goal("Road")
                return
            if self.rng.random() < min(1., self.behaviour["afternoon_water_probability"] * self.water_visit_multiplier):
                self._commit_goal("Waterhole")
                return
        if self.daytime_walking_minutes >= self.behaviour["daytime_travel_budget_minutes"] and self.raw_zone is not None and not self._can_hunt():
            self.goal, self.mode, self.until = self.raw_zone, "resting", self.day_minutes
            return
        period = self._period()
        priors = period.get("caught_priors", period["priors"]) if self.caught else period["priors"]
        if self._is_night():
            candidates = ["Plain", "Den"]
        elif self.offset(self.behaviours["hunt_start"]) <= self.minute < self.offset(self.behaviours["hunt_end"]):
            candidates = ["Hunting ground"] if self._can_hunt() else ["Plain", "Kopje", "Waterhole"]
        else:
            candidates = [name for name in self.zone_names if name != "Hunting ground"]
        hunger, energy, temperature, boredom, _ = self.bars
        recent_start = max(0, self.minute - self.goal_config["road_memory_minutes"])
        recent_cars = int(self.car_minute_counts[recent_start:self.minute].sum())
        scores: list[float] = []
        for name in candidates:
            value = float(priors[name]) * self.randomness["period_prior_scale"]
            if name == "Waterhole":
                value += self.water_goal_bonus
            if name == "Hunting ground":
                if hunger > self.latents["hunt_threshold"]:
                    value += hunger * self.goal_config["hunger_weight"]
                else:
                    # A visit is possible outside hunting hours; stalking is not.
                    if period.get("hungry_hunt_only"):
                        value = min(value, self.goal_config["hunt_unavailable_prior"])
            if name in ("Den", "Shade"):
                value += (1 - energy) * self.goal_config["low_energy_weight"]
            if name in ("Shade", "Waterhole"):
                value += temperature * self.goal_config["temperature_weight"]
            if name in ("Plain", "Kopje", "Road"):
                value += boredom * self.goal_config["boredom_weight"]
            value -= self.goal_config["distance_penalty_per_km"] * float(np.linalg.norm(self.position - self.centres[name]))
            if name == "Road":
                multiplier = self._road_time_multiplier()
                value += math.log(max(multiplier, np.finfo(float).tiny))
                value -= self.goal_config["road_penalty_per_car"] * recent_cars
                value += self.behaviour["road_goal_boredom_weight"] * boredom
                value -= self.behaviour["road_goal_traffic_penalty"] * self.latents["tourist_rate_per_hour"]
            scores.append(value + float(self.rng.normal(0, self.randomness["score_noise_sd"])))
        logits = np.asarray(scores) / self.learnability["softmax_temperature"]
        probabilities = np.exp(logits - logits.max())
        probabilities /= probabilities.sum()
        self.goal = str(self.rng.choice(candidates, p=probabilities))
        self.mode, self.arriving = "walking", False

    def start_grooming(self, after_second: int | None = None) -> None:
        sigma = self.behaviours["groom_lognormal_sigma"]
        mean = self.behaviours["groom_mean_minutes"]
        length = max(1, int(round(float(self.rng.lognormal(math.log(mean) - sigma * sigma / 2, sigma)))))
        self.mode, self.until = "grooming", self.minute + length
        if after_second is None:
            self.emit("GROOM")
        else:
            elapsed = self.minute * 60 + after_second + int(self.rng.integers(1, 20))
            if elapsed < self.day_minutes * 60:
                append_event(self.events, self.start, elapsed, "GROOM", self.raw_zone)

    def arrive(self) -> None:
        self._finish_trip("arrived" if self.trip is not None and self.trip["goal"] == self.goal else "interrupted")
        self.arriving = False
        rival_arrival = self.rival_patrol_goal == self.goal and self.rival_patrol_remaining > 0
        if rival_arrival:
            self.rival_patrol_remaining -= 1
            self.rival_patrol_goal = None
            low, high = self.c['day_types']['rival']['patrol_dwell_minutes_range']
            self.mode, self.until = 'resting', self.minute + int(self.rng.integers(low, high + 1))
            return
        if self._is_night() and not self.caught:
            self._initialize_night_patrol()
            self.night_patrol_remaining = max(0, self.night_patrol_remaining - 1)
            self.night_visited.add(self.goal)
            if self.goal == "Waterhole":
                self.night_water_pause = True
            elif self.goal in ("Plain", "Den"):
                self.mode, self.until = "night_walk", self.minute + self.duration("night_walk_minutes_range")
                return
            else:
                self._night_pause()
                return
        if self.goal == "Kopje" and not self.morning_scout_completed and self.minute < self.shade_departure:
            dwell = self.behaviour["scout_base_minutes"] + self.prey_signal * self.behaviour["scout_prey_extra_minutes"]
            if self.day_type == 'prey_rich':
                dwell *= self.c['day_types']['prey_rich']['scout_dwell_multiplier']
            dwell += float(self.rng.normal(0, self.behaviour["scout_jitter_sd_minutes"]))
            self.mode, self.until = "scouting", self.minute + max(1, int(round(dwell)))
            return
        if self.goal == "Plain" and self.morning_scout_completed and not self.midday_slept and self.minute < self.shade_departure:
            self.mode, self.until = "resting", self.minute + 1 if self.rival_patrol_remaining else self.shade_departure
            return
        if self.caught and self.goal == "Feeding spot":
            self.mode, self.until = "eating", self.minute + self.behaviours["eat_max_minutes"]
            self.emit("EAT_START")
        elif self.rest_after_arrival and self.goal in ("Den", "Shade", "Plain"):
            self.rest_after_arrival = False
            self.mode, self.until = "fatigue_sleep", self.minute + self.behaviour["interrupted_rest_minutes"]
            self.emit("FELL_ASLEEP")
        elif self._is_night() and self.goal in ("Den", "Plain"):
            self.mode, self.until = "night_walk", self.minute + self.duration("night_walk_minutes_range")
        elif self.goal == "Shade" and not self.midday_slept and self.shade_departure <= self.minute < self.midday_wake:
            self.midday_slept = True
            self.mode = "midday_sleep"
            self.emit("FELL_ASLEEP")
        elif self.goal == "Waterhole":
            shape = self.behaviours["drink_gamma_shape"]
            heat_scale = max(0.0, 1 + self.behaviour["drink_heat_multiplier"] * (self.latents["heat"] - self.behaviour["heat_reference"]))
            length = max(1, int(round(float(self.rng.gamma(shape, self.behaviours["drink_mean_minutes"] * heat_scale / shape)))))
            self.mode, self.until = "drinking", self.minute + length
            self.emit("DRINK")
        elif self.goal == "Hunting ground" and self._can_hunt():
            self.mode = "hunting"
            if self.chase_count == 0 and self.first_chase_due is None:
                rate = self.behaviours["prey_encounters_per_hour"] * self.latents["prey_density"] / 60
                wait = self.rng.exponential(1 / rate) if rate > 0 else self.behaviour["first_chase_wait_max_minutes"]
                wait = np.clip(wait, self.behaviour["first_chase_wait_min_minutes"], self.behaviour["first_chase_wait_max_minutes"])
                if self.day_type == 'prey_rich':
                    wait *= self.c['day_types']['prey_rich']['first_chase_wait_multiplier']
                self.first_chase_due = min(self.minute + int(round(wait)), self.offset(self.behaviours["hunt_end"]) - 1)
        elif self.goal == "Plain" and self.hungry_day and self.evening_staged and self.minute < self.hunt_ready_minute:
            self.mode, self.until = "resting", self.hunt_ready_minute
        else:
            key = "rest_minutes_range" if self.goal in ("Den", "Shade", "Plain") else "visit_minutes_range"
            self.mode, self.until = "resting", self.minute + self.duration(key)

    def _transitions(self) -> None:
        self._scheduled_interrupts()
        if self._advance_road_response():
            return
        if self.mode == "initial_sleep":
            if self.minute == self.wake_seconds // 60:
                second = self.wake_seconds % 60
                self.emit("WOKE_UP", second=second)
                self.start_grooming(after_second=second)
            return
        if self.mode == "midday_sleep":
            cool = self.minute >= self.offset(self.behaviours["cool_wake_after"]) and self.bars[2] < self.behaviours["cool_wake_temperature"]
            if self.minute >= self.midday_wake or cool:
                second = int(self.rng.integers(12, 35))
                self.emit("WOKE_UP", second)
                self.start_grooming(after_second=second)
            return
        if self.mode in ("final_sleep", "night_final_sleep"):
            return
        if self.mode == "fatigue_sleep":
            if self.minute >= self.until:
                self.emit("WOKE_UP")
                self.choose_goal()
            return
        if self.mode == "eating":
            if self.bars[0] < self.behaviours["eat_stop_hunger"] or self.minute >= self.until:
                self.emit("EAT_END", int(self.rng.integers(12, 30)))
                self.emit("FELL_ASLEEP", int(self.rng.integers(35, 60)))
                self.mode = "final_sleep"
            return
        if self.mode == "catnap":
            if self.minute >= self.until:
                # Preserve the minimum duration in seconds, not just tick counts.
                second = max(self.nap_start_second, int(self.rng.integers(12, 60)))
                self.emit("WOKE_UP", second)
                if self.minute < self.night_pause_until:
                    self.mode, self.until = "night_rest", self.night_pause_until
                else:
                    self.choose_goal()
            return
        if self.mode == "night_walk":
            if self.minute >= self.until:
                self._night_pause()
            return
        if self.mode == "night_rest":
            if self.minute >= self.until:
                self._choose_night_goal()
            return
        if self.mode == "scouting":
            if self.minute >= self.until:
                self.morning_scout_completed = True
                self._commit_goal("Plain")
            return
        if self.mode == "hunting":
            if not self._can_hunt():
                self.choose_goal()
            return
        if self.mode == "fail_rest":
            if self.minute >= self.until:
                if self._can_hunt():
                    self.goal = "Hunting ground"
                    self.mode = "hunting" if self.raw_zone == self.goal else "walking"
                else:
                    self.choose_goal()
            return
        if self.mode in ("grooming", "drinking", "resting") and self.minute >= self.until:
            if self.mode == "drinking" and self.night_water_pause:
                self.night_water_pause = False
                self._night_pause()
            else:
                self.choose_goal()
        if self.mode == "walking" and self.raw_zone == self.goal:
            # Settle inside the boundary until entry hysteresis has confirmed it.
            self.arriving = True
            if self.tracker.considered_zone == self.goal:
                self.arrive()

    def _move(self, target: np.ndarray, speed: float, heading_sd: float, confine: str | None = None,
              max_step_km: float | None = None, goal_attraction: float | None = None) -> None:
        bearing = math.atan2(target[1] - self.position[1], target[0] - self.position[0])
        requested = bearing + float(self.rng.normal(0, math.radians(heading_sd)))
        persistence = self.movement["heading_persistence"]
        turn = (1 - persistence) * _angle_difference(requested, self.heading)
        if goal_attraction is not None:
            # Change attraction toward the goal without also amplifying noise
            # on urgent trips. Retain the legacy scale of heading perturbations.
            turn += (goal_attraction - (1 - persistence)) * _angle_difference(bearing, self.heading)
        self.heading += turn
        length = speed / 60
        if max_step_km is not None:
            length = min(length, max(0.0, max_step_km))
        proposal = self.position + length * np.array([math.cos(self.heading), math.sin(self.heading)])
        proposal[0] = _reflect(float(proposal[0]), self.c["map"]["width_km"])
        proposal[1] = _reflect(float(proposal[1]), self.c["map"]["height_km"])
        if confine is not None and not self._contains(confine, proposal):
            # Turn inward while maintaining the one-minute speed bound.
            vector = self.centres[confine] - self.position
            distance = float(np.linalg.norm(vector))
            proposal = self.position + vector * min(1.0, length / max(distance, 1e-12))
            self.heading = math.atan2(vector[1], vector[0])
        # Outside the hunting window (and on ineligible days), avoid crossing
        # through Hunt as a shortcut. A lion already inside at cutoff may exit.
        if not self._can_hunt() and not self._contains("Hunting ground", self.position) and self._contains("Hunting ground", proposal):
            outward = self.position - self.centres["Hunting ground"]
            outward /= max(float(np.linalg.norm(outward)), 1e-12)
            tangent = np.array([-outward[1], outward[0]])
            if float(np.dot(tangent, target - self.position)) < 0:
                tangent = -tangent
            proposal = self.position + tangent * length
            proposal[0] = _reflect(float(proposal[0]), self.c["map"]["width_km"])
            proposal[1] = _reflect(float(proposal[1]), self.c["map"]["height_km"])
            self.heading = math.atan2(tangent[1], tangent[0])
        self.position = proposal

    def _move_road_response(self) -> None:
        assert self.road_target is not None
        step = float(np.linalg.norm(self.position - self.road_target))
        if self.mode == "road_approach" and not self._contains("Road", self.road_target) and self._road_distance() >= self.road_config["approach_standoff_km"]:
            step = min(step, self._road_distance() - self.road_config["approach_standoff_km"])
        self._move(self.road_target, self._patrol_speed(), self.randomness["walk_heading_sd_degrees"], max_step_km=step)

    def _jitter(self) -> None:
        proposal = self.position + self.rng.normal(0, self.movement["rest_jitter_sd_m"] / 1000, 2)
        proposal[0] = _reflect(float(proposal[0]), self.c["map"]["width_km"])
        proposal[1] = _reflect(float(proposal[1]), self.c["map"]["height_km"])
        # True-position jitter never causes a resting lion to leave its zone.
        if self.raw_zone is None or self._contains(self.raw_zone, proposal):
            self.position = proposal

    def _settle_inside(self) -> None:
        """Take a bounded inward step while waiting for zone-entry confirmation."""
        direction = self.centres[self.goal] - self.position
        distance = float(np.linalg.norm(direction))
        step = min(distance, self.movement["arrival_inset_km"],
                   self.movement["patrol_speed_kmh_range"][0] / 60)
        if distance > 0:
            self.position += direction * (step / distance)

    def _chase(self) -> None:
        self.chase_count += 1
        c = self.learnability["chase"]
        duration = int(round(float(self.rng.uniform(*c["duration_seconds_range"]))))
        start_second = int(self.rng.integers(0, 60 - duration))
        self.emit("CHASE_START", start_second)
        weights = c["energy_weight"] + c["mood_weight"]
        condition = (c["energy_weight"] * self.bars[1] + c["mood_weight"] * self.bars[4]) / weights
        factor = c["factor_min"] + (c["factor_max"] - c["factor_min"]) * condition
        probability = float(np.clip(self.learnability["chase_base_probability"] * factor, *c["probability_clip"]))
        success = bool(self.rng.random() < probability)
        direction = float(self.rng.uniform(-math.pi, math.pi))
        distance = c["speed_kmh"] * duration / 3600
        self.position += distance * np.array([math.cos(direction), math.sin(direction)])
        self.position[0] = _reflect(float(self.position[0]), self.c["map"]["width_km"])
        self.position[1] = _reflect(float(self.position[1]), self.c["map"]["height_km"])
        self.emit("CATCH" if success else "FAIL", start_second + duration,
                  zone=self._lookup(self.position))
        self.bars[1] += self.bar_config["energy_per_chase"]
        self.bars[3] += self.bar_config["boredom_per_chase"]
        self.bars[4] += self.bar_config["mood_per_catch"] if success else self.bar_config["mood_per_fail"]
        if success:
            self.caught = True
            self.goal, self.mode, self.arriving = "Feeding spot", "walking", False
        else:
            # This interval already contains the chase. Rest starts with the
            # next full minute, so do not count the chase minute as recovery.
            self.mode, self.until = "fail_rest", self.minute + 1 + self.duration("fail_rest_minutes_range")

    def _activity(self) -> str:
        if self.mode in ("initial_sleep", "midday_sleep", "catnap", "final_sleep", "fatigue_sleep", "night_final_sleep"):
            return "sleeping"
        if self.mode in ("resting", "fail_rest", "road_watch", "traffic_wait", "night_rest", "scouting"):
            return "resting"
        if self.mode == "walking" and self.arriving:
            return "resting"
        if self.mode in ("night_walk", "road_approach", "road_retreat"):
            return "walking"
        return self.mode

    def _movement_intent(self) -> str:
        if self.mode.startswith("road_") or self.mode == "traffic_wait":
            return self.mode
        if self.mode == "walking":
            return "arrival" if self.arriving else "travel"
        return self._activity()

    def _update_bars(self, behaviour: str, entered: bool) -> None:
        c = self.bar_config
        asleep = behaviour == "sleeping"
        moving = behaviour in ("walking", "hunting")
        if behaviour == "eating":
            self.bars[0] += c["hunger_eating_per_hour"] / 60
        elif moving or behaviour in ("grooming", "drinking"):
            self.bars[0] += c["hunger_active_per_hour"] / 60
        else:
            self.bars[0] += c["hunger_rest_per_hour"] / 60
        energy_rate = c["energy_asleep_per_hour"] if asleep else c["energy_walking_per_hour"] if moving else c["energy_awake_per_hour"]
        self.bars[1] += energy_rate / 60
        target = self.ambient(self.minute) * self.latents["heat"]
        if moving:
            target += c["temperature_moving_bonus"]
        if self.raw_zone in c["cooling_zones"]:
            target += c["temperature_cooling_bonus"]
        relaxation = 1 - math.exp(-1 / (60 * c["temperature_time_constant_hours"]))
        self.bars[2] += (target - self.bars[2]) * relaxation
        if not asleep and self.raw_zone == self.previous_zone and not entered:
            self.bars[3] += c["boredom_same_zone_per_hour"] / 60
        if self.mode == "road_watch":
            self.bars[3] -= self.road_config["boredom_relief_per_watch_hour"] / 60
        self.bars[4] += (c["mood_equilibrium"] - self.bars[4]) * c["mood_relaxation_per_hour"] / 60
        if self.day_type == 'rival':
            self.bars[4] += self.c['day_types']['rival']['mood_drift_per_hour'] / 60
        self.bars += self.rng.normal(0, self.randomness["bar_noise_sd"], 5)
        np.clip(self.bars, 0, 1, out=self.bars)

    def snapshot(self) -> _DaySimulation:
        """Independent copy of all mutable state, history, schedules and RNG."""
        return deepcopy(self)

    @classmethod
    def resume(cls, snapshot: _DaySimulation) -> _DaySimulation:
        """Restore without consuming randomness or modifying the snapshot."""
        return deepcopy(snapshot)

    def advance_to(self, stop_minute: int) -> None:
        """Complete ticks strictly before this minute boundary (no GPS sampling)."""
        if not self.next_minute <= stop_minute <= self.day_minutes:
            raise ValueError("Cannot rewind or advance outside the simulated day")
        true_positions = self.history["true_positions"]
        bar_values = self.history["bar_values"]
        behaviours = self.history["behaviours"]
        goals = self.history["goals"]
        zones = self.history["zones"]
        intents = self.history["intents"]
        road_triggers = self.history["road_triggers"]
        road_distances = self.history["road_distances"]
        abandoned_goals = self.history["abandoned_goals"]
        abandoned_reasons = self.history["abandoned_reasons"]
        patrol_speeds = self.history["patrol_speeds"]
        for minute in range(self.next_minute, stop_minute):
            self.minute = minute
            self.abandoned_goal_this_minute = None
            self.delayed_by_traffic_this_minute = False
            self.abandoned_reason_this_minute = None
            true_positions[minute] = self.position
            self.raw_zone = self._lookup(self.position)
            entered = self.tracker.update(None if self.raw_zone == "Hunting ground" and not self._can_hunt() else self.raw_zone)
            self.entered_this_minute = entered is not None
            if entered is not None:
                self.emit(ZONE_TOKENS[entered], int(self.rng.integers(0, 10)), entered)
                self.bars[3] += self.bar_config["boredom_per_entry"]
            self._transitions()
            self._sync_trip()
            behaviour = self._activity()
            # Cars retain their independently drawn seconds and affect mood only nearby.
            while self.car_pointer < len(self.car_seconds) and self.car_seconds[self.car_pointer] // 60 == minute:
                if self._road_distance() <= self.bar_config["car_mood_distance_km"]:
                    self.bars[4] += self.bar_config["mood_per_nearby_car"]
                self._consider_car_response(int(self.car_seconds[self.car_pointer]))
                self.car_pointer += 1
            np.clip(self.bars, 0, 1, out=self.bars)
            bar_values[minute] = self.bars
            behaviours.append(behaviour)
            goals.append(self.goal)
            zones.append(self.raw_zone)
            intents.append(self._movement_intent())
            road_triggers.append(None if self.road_trigger_second is None else
                                 (self.start + timedelta(seconds=self.road_trigger_second)).isoformat(timespec="seconds"))
            road_distances.append(self._road_distance())
            if self.mode == "walking" and not self.arriving:
                self._move_trip()
            elif self.mode == "walking":
                self._settle_inside()
            elif self.mode in ("road_approach", "road_retreat"):
                self._move_road_response()
            elif self.mode in ("hunting", "night_walk"):
                confined = "Hunting ground" if self.mode == "hunting" else self.goal
                speed = self.movement["stalk_speed_kmh"] if self.mode == "hunting" else self._patrol_speed()
                angle = float(self.rng.uniform(-math.pi, math.pi))
                target = self.position + np.array([math.cos(angle), math.sin(angle)])
                first_due = self.chase_count == 0 and self.first_chase_due is not None and self.minute >= self.first_chase_due
                encounter = self.rng.random() < -math.expm1(-self.behaviours["prey_encounters_per_hour"] * self.latents["prey_density"] / 60) if self.mode == "hunting" else False
                if self.mode == "hunting" and not self.entered_this_minute and (first_due or encounter):
                    self._chase()
                else:
                    self._move(target, speed, self.randomness["stalk_heading_sd_degrees"] if self.mode == "hunting" else self.randomness["walk_heading_sd_degrees"], confine=confined)
            else:
                self._jitter()
            self._record_trip_step(true_positions[minute])
            self.history["traffic_delays"].append(self.delayed_by_traffic_this_minute)
            abandoned_goals.append(self.abandoned_goal_this_minute)
            abandoned_reasons.append(self.abandoned_reason_this_minute)
            patrol_speeds.append(float(np.linalg.norm(self.position - true_positions[minute])) * 60 if behaviour == "walking" else None)
            if behaviour == "walking" and not self._is_night():
                self.daytime_walking_minutes += 1
            self._update_bars(behaviour, entered is not None)
            self.previous_zone = self.raw_zone
            self.next_minute = minute + 1
        true_positions[stop_minute] = self.position
        if stop_minute == self.day_minutes:
            self.minute = stop_minute
            self._finish_trip("day_end")

    def run(self) -> DayResult:
        self.advance_to(self.day_minutes)
        true_positions = self.history["true_positions"]
        bar_values = self.history["bar_values"]
        behaviours = self.history["behaviours"]
        goals = self.history["goals"]
        zones = self.history["zones"]
        intents = self.history["intents"]
        road_triggers = self.history["road_triggers"]
        road_distances = self.history["road_distances"]
        abandoned_goals = self.history["abandoned_goals"]
        abandoned_reasons = self.history["abandoned_reasons"]
        patrol_speeds = self.history["patrol_speeds"]
        true_positions[-1] = self.position
        observed = true_positions + self.rng.normal(0, self.randomness["gps_noise_sd_m"] / 1000, true_positions.shape)
        missing = self.rng.random(self.day_minutes + 1) < self.randomness["gps_dropout_probability"]
        # Always acquire the first noisy fix so forward filling is well-defined.
        missing[0] = False
        for index in range(1, len(observed)):
            if missing[index]:
                observed[index] = observed[index - 1]
        timestamps = [(self.start + timedelta(minutes=index)).isoformat(timespec="seconds") for index in range(self.day_minutes + 1)]
        gps = pd.DataFrame({
            "t_iso": timestamps, "minute_index": np.arange(self.day_minutes + 1),
            "x_km": observed[:, 0], "y_km": observed[:, 1],
            "x_true_km": true_positions[:, 0], "y_true_km": true_positions[:, 1],
            "missing": missing,
            "ambient_temp_c": self.observed_ambient_c,
        })
        hidden = pd.DataFrame(bar_values, columns=["hunger", "energy", "temperature", "boredom", "mood"])
        hidden.insert(0, "minute_index", np.arange(self.day_minutes))
        hidden.insert(0, "t_iso", timestamps[:-1])
        hidden["goal"], hidden["behaviour"], hidden["zone"] = goals, behaviours, zones
        hidden["weather"] = self.weather
        hidden["day_type"] = self.day_type
        for name, value in self.period_jitter.items():
            hidden[f"{name}_jitter_minutes"] = value
        hidden["ambient_temp_c_true"] = self.true_ambient_c[:-1]
        hidden["heat_true"] = self.latents["heat"]
        hidden["movement_intent"] = intents
        hidden["road_trigger_t_iso"] = road_triggers
        hidden["road_distance_km"] = road_distances
        hidden["delayed_by_traffic"] = self.history["traffic_delays"]
        hidden["abandoned_goal"] = abandoned_goals
        hidden["abandoned_trip_reason"] = abandoned_reasons
        hidden["actual_patrol_speed_kmh"] = patrol_speeds
        trip_columns = ["trip_id", "trip_goal", "trip_start_minute", "trip_end_minute",
                        "trip_urgency", "trip_boredom", "trip_mood", "trip_detour_count",
                        "trip_planned_straightness", "trip_realized_straightness",
                        "trip_goal_attraction", "trip_turn_sd_degrees", "trip_speed_multiplier",
                        "trip_path_length_km", "trip_status"]
        trip_frame = pd.DataFrame(self.history["trip_rows"], columns=trip_columns)
        for column in ("trip_id", "trip_start_minute", "trip_end_minute", "trip_detour_count"):
            trip_frame[column] = trip_frame[column].astype("Int64")
        hidden = pd.concat([hidden, trip_frame], axis=1)
        entropy = self.sequence.entropy
        if isinstance(entropy, np.ndarray):
            entropy = entropy.tolist()
        elif isinstance(entropy, np.integer):
            entropy = int(entropy)
        seed_info = {
            "base_seed": int(self.seed), "entropy": entropy,
            "spawn_key": [int(value) for value in self.sequence.spawn_key],
            "pool_size": int(self.sequence.pool_size), "bit_generator": type(self.rng.bit_generator).__name__,
        }
        traffic_times = [(self.start + timedelta(seconds=int(second))).isoformat(timespec="seconds") for second in self.car_seconds]
        return DayResult(self.day_index, self.start.date().isoformat(), seed_info, self.latents, sort_events(self.events), gps, hidden, traffic_times, self.weather)


def simulate_day(
    config: Config,
    day_index: int = 1,
    seed: int = 42,
    start_date: str = "2026-01-01",
    seed_sequence: np.random.SeedSequence | None = None,
) -> DayResult:
    """Simulate a day using its fixed child of the run's base SeedSequence.

    Runners should pre-spawn children once and pass ``seed_sequence``. The
    standalone path deliberately uses the same child, making regeneration and
    multiprocessing produce identical data.
    """
    if day_index < 1:
        raise ValueError("day_index must be at least 1")
    sequence = seed_sequence if seed_sequence is not None else np.random.SeedSequence(seed).spawn(day_index)[day_index - 1]
    return _DaySimulation(config, day_index, seed, start_date, sequence).run()
