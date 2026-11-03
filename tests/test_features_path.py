"""Observable path geometry and strict report-time causality."""

from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from lionsim.config import load_config
from lionsim.features_path import (PATH_FEATURE_COLUMNS, features_at_report,
                                   last_completed_trip, path_metrics, smoothed_observed_prefix)


def gps(points, start='2026-01-01T05:00:00'):
    return pd.DataFrame({'t_iso': pd.date_range(start, periods=len(points), freq='min').astype(str),
                         'x_km': [p[0] for p in points], 'y_km': [p[1] for p in points],
                         'x_true_km': 999., 'y_true_km': -999.})


def frame(points):
    g = gps(points)
    return g.set_index(pd.to_datetime(g.t_iso))[['x_km', 'y_km']]


def test_path_metrics_known_straight_turning_closed_and_stationary_paths():
    straight = path_metrics(frame([[0,0],[1,0],[2,0]]), .25)
    assert straight['straightness'] == 1
    assert straight['mean_speed_kmh'] == pytest.approx(60)
    assert straight['turn_circular_variance'] == pytest.approx(0)
    assert straight['max_perpendicular_distance_km'] == 0
    assert straight['area_covered_km2'] == pytest.approx(3*.25**2)
    bent = path_metrics(frame([[0,0],[1,1],[2,0]]), .25)
    assert bent['straightness'] == pytest.approx(1/np.sqrt(2))
    assert bent['max_perpendicular_distance_km'] == pytest.approx(1)
    closed = path_metrics(frame([[0,0],[1,0],[0,0]]), .25)
    assert closed['straightness'] == 0 and closed['max_perpendicular_distance_km'] == 1
    still = path_metrics(frame([[1,1]]*4), .25)
    assert still['straightness'] is None and still['turn_circular_variance'] is None
    assert still['mean_speed_kmh'] == 0
    assert still['area_covered_km2'] == .0625
    empty = path_metrics(frame([[1,1]]).iloc[:0], .25)
    assert all(v is None for v in empty.values())
    single = path_metrics(frame([[1,1]]), .25)
    assert single['mean_speed_kmh'] is None


def test_trailing_five_minute_smoothing_changes_features_and_ignores_true_positions():
    g = gps([[i,0] for i in range(6)])
    config = load_config()
    smooth = smoothed_observed_prefix(g, '2026-01-01T05:05:00', config)
    np.testing.assert_allclose(smooth.x_km, [0,.5,1,1.5,2,3])
    result = features_at_report(g, [], '2026-01-01T05:05:00', config)
    assert result['last_3h_mean_speed_kmh'] == pytest.approx(36)
    assert result['last_trip_straightness'] is None
    changed = g.copy()
    changed[['x_true_km','y_true_km']] = -1e8
    assert features_at_report(changed, [], '2026-01-01T05:05:00', config) == result


def trip_data():
    # Leave Den, arrive at Kopje, rest, then begin a second uncompleted trip.
    first = np.column_stack((np.linspace(2,3.5,21),np.linspace(8,6,21)))
    points = np.concatenate((np.repeat([[2.,8.]],10,axis=0), first,
                             np.repeat([[3.5,6.]],10,axis=0),
                             np.column_stack((np.linspace(3.5,7.5,21),np.linspace(6,6.5,21)))))
    events = [{'t':'2026-01-01T05:30:30','token':'ENTER_KOPJE','zone':'Kopje'},
              {'t':'2026-01-01T06:01:30','token':'ENTER_WATER','zone':'Waterhole'}]
    return gps(points), events


def test_last_completed_trip_uses_departure_not_dwell_and_waits_for_public_arrival():
    g, events = trip_data()
    config = load_config()
    before = features_at_report(g, events, '2026-01-01T05:30:00', config)
    assert before['last_trip_straightness'] is None
    first = features_at_report(g, events, '2026-01-01T05:31:00', config)
    assert first['last_trip_straightness'] is not None
    later = features_at_report(g, events, '2026-01-01T05:55:00', config)
    assert {k:v for k,v in first.items() if k.startswith('last_trip')} == {
        k:v for k,v in later.items() if k.startswith('last_trip')}
    prefix = smoothed_observed_prefix(g, '2026-01-01T05:55:00', config)
    trip = last_completed_trip(prefix, events, '2026-01-01T05:55:00', config)
    assert trip.index[0] > pd.Timestamp('2026-01-01T05:10:00')  # rest at source excluded
    assert trip.index[-1] == pd.Timestamp('2026-01-01T05:30:00')  # no future fix at 05:31
    assert features_at_report(g, events, '2026-01-01T06:01:30', config)['last_trip_mean_speed_kmh'] != first['last_trip_mean_speed_kmh']


def test_future_gps_and_events_cannot_change_any_report_feature():
    g, events = trip_data()
    report = '2026-01-01T05:31:00'
    config = load_config()
    expected = features_at_report(g, events, report, config)
    changed = g.copy()
    changed.loc[pd.to_datetime(changed.t_iso) > pd.Timestamp(report), ['x_km','y_km']] = np.nan
    altered_events = deepcopy(events)
    altered_events[-1]['token'] = 'ENTER_ROAD'
    assert features_at_report(changed, altered_events, report, config) == expected
    prefix = g.loc[pd.to_datetime(g.t_iso) <= pd.Timestamp(report)]
    assert features_at_report(prefix, events[:1], report, config) == expected
    # The fix exactly at report time is allowed and affects the recent window.
    changed = g.copy()
    changed.loc[pd.to_datetime(g.t_iso) == pd.Timestamp(report), 'x_km'] += 1
    assert features_at_report(changed, events, report, config)['last_3h_mean_speed_kmh'] != expected['last_3h_mean_speed_kmh']


def test_last_three_hours_excludes_older_smoothed_fixes():
    g = gps([[i,0] for i in range(241)])
    config = load_config()
    result = features_at_report(g, [], '2026-01-01T09:00:00', config)
    prefix = smoothed_observed_prefix(g, '2026-01-01T09:00:00', config)
    expected = path_metrics(prefix.loc['2026-01-01T06:00:00':], .25)
    assert {k.removeprefix('last_3h_'):v for k,v in result.items() if k.startswith('last_3h_')} == expected
    assert set(result) == set(PATH_FEATURE_COLUMNS)


@pytest.mark.parametrize('expression', ['features_path.smoothing_minutes=0',
    'features_path.window_minutes=1441','features_path.grid_cell_km=0',
    'features_path.departure_margin_km=-1','features_path.departure_confirmation_minutes=1.5'])
def test_invalid_feature_settings_are_rejected(expression):
    with pytest.raises(ValueError):
        load_config(overrides=[expression])


def test_csv_features_resume_workers_and_checkpoint_repair(tmp_path):
    import csv
    import json
    from lionsim.run import build_parser, run
    from lionsim.simulator import simulate_day
    from lionsim.reports import build_reports
    parser = build_parser()
    partial = run(parser.parse_args(['--stats-only','--stats-days','3','--chunk-size','2',
                                    '--out',str(tmp_path/'partial')]))
    checkpoints = sorted((partial/'checkpoints').glob('*.json'))
    stamps = {p:p.stat().st_mtime_ns for p in checkpoints}
    # Missing a feature is an incomplete day, not a legitimate missing value.
    broken = json.loads(checkpoints[0].read_text())
    del broken['targets'][0][PATH_FEATURE_COLUMNS[0]]
    checkpoints[0].write_text(json.dumps(broken))
    run(parser.parse_args(['--resume',str(partial),'--workers','2']))
    assert checkpoints[1].stat().st_mtime_ns == stamps[checkpoints[1]]
    assert PATH_FEATURE_COLUMNS[0] in json.loads(checkpoints[0].read_text())['targets'][0]
    full = run(parser.parse_args(['--stats-only','--stats-days','3','--out',str(tmp_path/'full')]))
    for name in ('targets.csv','stats_report.json','stats_report.md'):
        assert (partial/name).read_bytes() == (full/name).read_bytes()
    with (full/'targets.csv').open() as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames[-10:] == list(PATH_FEATURE_COLUMNS)
        rows = list(reader)
    assert len(rows) == 21
    config = load_config()
    day = simulate_day(config)
    timestamp = build_reports(day, config)[0]['report_time']
    features = features_at_report(day.gps, day.events, timestamp, config)
    for name, value in features.items():
        assert rows[0][name] == '' if value is None else float(rows[0][name]) == pytest.approx(value)
    assert all(row['report_index'] != '8' for row in rows)
    assert any(row['last_trip_straightness'] != '' for row in rows)
    assert not list(full.rglob('*.png'))
    assert not list(full.rglob('hidden_state*'))
    assert not list(full.rglob('gps*'))


def test_report_features_do_not_read_hidden_state_or_latents():
    from lionsim.simulator import simulate_day
    from lionsim.reports import build_reports
    config = load_config()
    day = simulate_day(config)
    timestamp = build_reports(day, config)[1]['report_time']
    before = features_at_report(day.gps, day.events, timestamp, config)
    day.hidden_state = None
    day.latents.clear()
    day.gps[['x_true_km','y_true_km']] = np.nan
    assert features_at_report(day.gps, day.events, timestamp, config) == before
