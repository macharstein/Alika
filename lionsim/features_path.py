"""Causal path-shape features from observed GPS and public entry events only."""

from typing import Any

import numpy as np
import pandas as pd

from .config import Config
from .events import ZONE_TOKENS
from .zones import ZoneMap


METRICS = ('straightness', 'mean_speed_kmh', 'turn_circular_variance',
           'max_perpendicular_distance_km', 'area_covered_km2')
PATH_FEATURE_COLUMNS = tuple(f'{scope}_{metric}' for scope in ('last_trip', 'last_3h') for metric in METRICS)
ENTRY_ZONES = {token: zone for zone, token in ZONE_TOKENS.items()}


def smoothed_observed_prefix(gps: pd.DataFrame, report_time: str, config: Config) -> pd.DataFrame:
    """Filter before smoothing/filling; never read true coordinates or future fixes."""
    times = pd.to_datetime(gps['t_iso'])
    prefix = gps.loc[times <= pd.Timestamp(report_time), ['x_km', 'y_km']].copy()
    prefix.index = pd.DatetimeIndex(times[times <= pd.Timestamp(report_time)])
    prefix = prefix.sort_index()
    if prefix.index.has_duplicates:
        raise ValueError('Observed GPS timestamps must be unique')
    prefix = prefix.apply(pd.to_numeric, errors='coerce').replace([np.inf, -np.inf], np.nan)
    # Forward-fill from the prefix only. Leading missing coordinates stay absent.
    prefix = prefix.ffill().dropna()
    return prefix.rolling(f"{config['features_path']['smoothing_minutes']}min", min_periods=1).mean()


def path_metrics(path: pd.DataFrame, grid_cell_km: float) -> dict[str, float | None]:
    """Metrics over smoothed fixes; times and coordinates must already be causal."""
    values: dict[str, float | None] = dict.fromkeys(METRICS)
    if path.empty:
        return values
    points = path[['x_km', 'y_km']].to_numpy(dtype=float)
    cells = np.floor(points / grid_cell_km).astype(np.int64)
    values['area_covered_km2'] = float(len(np.unique(cells, axis=0)) * grid_cell_km ** 2)
    if len(points) < 2:
        return values
    steps = np.diff(points, axis=0)
    lengths = np.linalg.norm(steps, axis=1)
    length = float(lengths.sum())
    chord_vector = points[-1] - points[0]
    chord = float(np.linalg.norm(chord_vector))
    elapsed_hours = (path.index[-1] - path.index[0]).total_seconds() / 3600
    values['mean_speed_kmh'] = length / elapsed_hours if elapsed_hours > 0 else None
    values['straightness'] = min(1., chord / length) if length > np.finfo(float).eps else None
    if chord > np.finfo(float).eps:
        relative = points - points[0]
        cross = chord_vector[0] * relative[:, 1] - chord_vector[1] * relative[:, 0]
        values['max_perpendicular_distance_km'] = float(np.max(np.abs(cross)) / chord)
    else:
        # A zero chord has no direction; use maximum distance from its point.
        values['max_perpendicular_distance_km'] = float(np.max(np.linalg.norm(points - points[0], axis=1)))
    moving = steps[lengths > np.finfo(float).eps]
    if len(moving) >= 2:
        headings = np.arctan2(moving[:, 1], moving[:, 0])
        turns = np.diff(headings)
        values['turn_circular_variance'] = float(np.clip(1 - abs(np.mean(np.exp(1j * turns))), 0, 1))
    return values


def last_completed_trip(prefix: pd.DataFrame, events: list[dict[str, Any]],
                        report_time: str, config: Config) -> pd.DataFrame:
    """Observable inter-zone trip: sustained departure, then a public entry.

    Hidden trip boundaries are deliberately excluded. A road wait or unzoned
    pause does not finish a trip. An entry after report_time cannot close it.
    """
    if prefix.empty:
        return prefix
    zones = ZoneMap(config)
    options = config['features_path']
    source = zones.lookup(*prefix.iloc[0])
    anchor_time = prefix.index[0]
    anchor_point = prefix.iloc[0].to_numpy()
    completed = prefix.iloc[:0]
    entries = sorted((pd.Timestamp(e['t']), ENTRY_ZONES[e['token']]) for e in events
                     if e['token'] in ENTRY_ZONES and
                     prefix.index[0] <= pd.Timestamp(e['t']) <= pd.Timestamp(report_time))
    for arrival, destination in entries:
        if destination == source:
            continue
        segment = prefix.loc[(prefix.index >= anchor_time) & (prefix.index <= arrival)]
        points = segment.to_numpy()
        first_outside = None
        departure = None
        observed_source = source is None
        for index, point in enumerate(points):
            distance = (zones.distance_to(source, *point) if source is not None else
                        float(np.linalg.norm(point - anchor_point)))
            if distance <= options['departure_margin_km']:
                observed_source = True
                first_outside = None
                continue
            if not observed_source:
                continue  # Smoothing may still lag outside a newly entered zone.
            if (first_outside is None or index > 0 and
                    segment.index[index] - segment.index[index - 1] > pd.Timedelta(minutes=1)):
                first_outside = index
            if index - first_outside + 1 >= options['departure_confirmation_minutes']:
                departure = max(0, first_outside - 1)
                break
        if departure is not None and len(segment) - departure >= 2:
            completed = segment.iloc[departure:]
        source, anchor_time = destination, arrival
        if len(segment):
            anchor_point = points[-1]
    return completed


def features_at_report(gps: pd.DataFrame, events: list[dict[str, Any]],
                       report_time: str, config: Config) -> dict[str, float | None]:
    prefix = smoothed_observed_prefix(gps, report_time, config)
    options = config['features_path']
    recent = prefix.loc[prefix.index >= pd.Timestamp(report_time) - pd.Timedelta(minutes=options['window_minutes'])]
    trip = last_completed_trip(prefix, events, report_time, config)
    return {f'{scope}_{key}': value for scope, frame in (('last_trip', trip), ('last_3h', recent))
            for key, value in path_metrics(frame, options['grid_cell_km']).items()}
