"""Trip-start movement parameters and bounded, map-aware detour planning."""

from dataclasses import dataclass

import numpy as np

from .config import Config
from .zones import ZoneMap


@dataclass(frozen=True)
class MovementStyle:
    urgency: float
    boredom: float
    mood: float
    goal_attraction: float
    turn_sd_degrees: float
    speed_multiplier: float
    waypoints: tuple[np.ndarray, ...]
    planned_straightness: float | None


def plan_style(config: Config, zones: ZoneMap, goal: str, bars: np.ndarray,
               start: np.ndarray, target: np.ndarray, rng: np.random.Generator) -> MovementStyle:
    """Freeze style from bars at departure; never consult future internal state."""
    c = config['movement_style']
    hunger, energy, temperature, boredom, mood = np.clip(bars, 0, 1)
    urgency = (hunger if goal in ('Hunting ground', 'Feeding spot') else
               temperature if goal in ('Shade', 'Waterhole') else
               1 - energy if goal == 'Den' else c['boredom_goal_urgency'])
    attraction = (1 - config['movement']['heading_persistence']) * (
        c['attraction_intercept'] + c['attraction_urgency_weight'] * urgency)
    turn = float(np.clip(c['turn_intercept'] + c['turn_boredom_weight'] * boredom
                         - c['turn_urgency_weight'] * urgency, *c['turn_multiplier_range']))
    if mood < c['low_mood_threshold']:
        turn += c['low_mood_turn_increment']
    waypoints = []
    chord = float(np.linalg.norm(target - start))
    probability = float(np.clip(c['detour_probability_scale'] *
                                (boredom - c['detour_boredom_threshold']), 0, 1))
    if chord > 0 and probability > 0 and rng.random() < probability:
        count = int(rng.integers(c['detour_count_range'][0], c['detour_count_range'][1] + 1))
        normal = np.array([-(target - start)[1], (target - start)[0]]) / chord
        source = zones.lookup(*start)
        sign = float(rng.choice([-1, 1]))
        for index in range(1, count + 1):
            anchor = start + (target - start) * (index / (count + 1))
            fallback = None
            for attempt in range(c['waypoint_sampling_attempts']):
                # Alternate sides; rejecting rather than clipping preserves the
                # configured minimum sideways distance even at map boundaries.
                offset = float(rng.uniform(*c['detour_offset_km_range']))
                candidate = anchor + normal * offset * sign * (-1 if attempt % 2 else 1)
                if not (0 <= candidate[0] <= zones.width and 0 <= candidate[1] <= zones.height):
                    continue
                if fallback is None:
                    fallback = candidate
                if all(zones.distance_to(name, *candidate) > c['zone_exclusion_margin_km']
                       for name in zones.names if name not in (source, goal)):
                    waypoints.append(candidate)
                    break
            else:
                # If exclusions are unavoidable, prefer an in-map point. If
                # neither side fits, omit this waypoint instead of leaving map.
                if fallback is not None:
                    waypoints.append(fallback)
    points = [start, *waypoints, target]
    length = sum(float(np.linalg.norm(b - a)) for a, b in zip(points, points[1:]))
    return MovementStyle(float(urgency), float(boredom), float(mood), float(attraction),
                         config['randomness']['walk_heading_sd_degrees'] * turn,
                         c['speed_intercept'] + c['speed_urgency_weight'] * float(urgency),
                         tuple(waypoints), chord / length if length > 0 else None)
