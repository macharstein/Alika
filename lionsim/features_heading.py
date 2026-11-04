"""Causal heading cues from smoothed observed GPS; no hidden-state inputs."""
import math

import numpy as np
import pandas as pd

from .features_path import smoothed_observed_prefix
from .zones import ZoneMap

HEADING_EXPORT_VERSION = 'heading-v1'
HEADING_COLUMNS = ('heading_dx_km', 'heading_dy_km', 'heading_displacement_km',
                   'speed_recent', 'moving', 'in_zone', 'implied_goal',
                   'distance_to_implied_goal_km', 'distance_to_implied_goal_bin',
                   'heading_window_complete')


def heading_at_report(gps, report_time, config, window_minutes=None):
    options = config['heading_features']
    window = options['window_minutes'] if window_minutes is None else window_minutes
    if not math.isfinite(window) or window <= 0:
        raise ValueError('Heading window must be positive and finite')
    prefix = smoothed_observed_prefix(gps, report_time, config)
    result = dict.fromkeys(HEADING_COLUMNS)
    result.update(moving=False, in_zone='transit', implied_goal='none', heading_window_complete=False)
    if prefix.empty:
        return result
    zones = ZoneMap(config)
    position = prefix.iloc[-1].to_numpy()
    current = zones.lookup(*position)
    result['in_zone'] = current or 'transit'
    earlier = prefix.loc[:pd.Timestamp(report_time) - pd.Timedelta(minutes=window)]
    if earlier.empty:
        return result
    displacement = position - earlier.iloc[-1].to_numpy()
    distance = float(np.linalg.norm(displacement))
    moving = distance >= options['min_displacement_km'] and distance > 0
    result.update(heading_dx_km=float(displacement[0]), heading_dy_km=float(displacement[1]),
                  heading_displacement_km=distance, speed_recent=distance / window,
                  moving=moving, heading_window_complete=True)
    if not moving:
        return result
    candidates = []
    for name in zones.names:
        if name == current:
            continue
        vector = np.asarray(zones.center(name)) - position
        length = float(np.linalg.norm(vector))
        if length == 0:
            continue
        angle = math.degrees(math.acos(float(np.clip(np.dot(vector, displacement) / (length * distance), -1, 1))))
        candidates.append((angle, length, name))
    result['implied_goal'] = 'ambiguous'
    if candidates:
        smallest = min(c[0] for c in candidates)
        angle, length, name = min((c for c in candidates if math.isclose(c[0], smallest, abs_tol=1e-9)),
                                  key=lambda c: (c[1], c[2]))
        if angle <= options['max_angle_deg'] + 1e-9:
            result.update(implied_goal=name, distance_to_implied_goal_km=length,
                          distance_to_implied_goal_bin='<=1.5 km' if length <= 1.5 else '>1.5 km')
    return result
