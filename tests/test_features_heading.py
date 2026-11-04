import numpy as np
import pandas as pd
import pytest
from lionsim.config import load_config
from lionsim.features_heading import heading_at_report
from lionsim.zones import ZoneMap


def track(points):
    return pd.DataFrame({'t_iso': pd.date_range('2026-01-01', periods=len(points), freq='min'),
                         'x_km': points[:, 0], 'y_km': points[:, 1], 'x_true_km': 999})


def test_stationary_and_incomplete():
    config = load_config()
    gps = track(np.tile([2., 8.], (50, 1)))
    result = heading_at_report(gps, gps.t_iso.iloc[30], config)
    assert result['implied_goal'] == 'none' and not result['moving']
    assert result['in_zone'] == 'Den' and result['speed_recent'] == 0
    assert result['distance_to_implied_goal_km'] is None
    assert not heading_at_report(gps, gps.t_iso.iloc[2], config)['heading_window_complete']


def test_straight_walk_causal_and_observed_only():
    config = load_config()
    goal = np.array(ZoneMap(config).center('Waterhole'))
    points = goal + np.column_stack((np.linspace(-3, -.5, 51), np.zeros(51)))
    gps = track(points)
    time = gps.t_iso.iloc[30]
    result = heading_at_report(gps, time, config)
    assert result['implied_goal'] == 'Waterhole'
    assert result['moving'] and result['speed_recent'] == pytest.approx(.05)
    assert result == heading_at_report(gps.iloc[:31], time, config)
    gps.loc[31:, ['x_km', 'y_km']] = -999
    gps['x_true_km'] = -999
    assert result == heading_at_report(gps, time, config)


@pytest.mark.parametrize('setting', ['heading_features.window_minutes=0',
    'heading_features.min_displacement_km=-1', 'heading_features.max_angle_deg=181',
    'l5_analysis.interpolation_k=0'])
def test_invalid_settings(setting):
    with pytest.raises(ValueError):
        load_config(overrides=[setting])


def test_export_resume_repair_and_legacy(tmp_path):
    import csv
    import json
    from lionsim.features_heading import HEADING_COLUMNS
    from lionsim.run import build_parser, run, _fingerprint
    from lionsim.config import Config
    parser = build_parser()
    directory = run(parser.parse_args(['--stats-only', '--stats-days', '2', '--out', str(tmp_path)]))
    checkpoint = sorted((directory / 'checkpoints').glob('*.json'))[0]
    original = json.loads(checkpoint.read_text())
    broken = json.loads(checkpoint.read_text())
    del broken['targets'][0]['implied_goal']
    checkpoint.write_text(json.dumps(broken))
    run(parser.parse_args(['--resume', str(directory)]))
    assert json.loads(checkpoint.read_text()) == original
    with (directory / 'targets.csv').open() as handle:
        assert csv.DictReader(handle).fieldnames[20:] == list(HEADING_COLUMNS)
    before = (directory / 'stats_report.json').read_bytes()
    # Emulate a pre-heading 5.4.0 checkpoint/config; preserve its original columns.
    manifest = json.loads((directory / 'run_manifest.json').read_text())
    del manifest['config']['heading_features']
    del manifest['config']['l5_analysis']
    del manifest['heading_export_version']
    manifest['run_fingerprint'] = _fingerprint(Config(manifest['config']), manifest['seed'], manifest['start_date'])
    for path in (directory / 'checkpoints').glob('*.json'):
        record = json.loads(path.read_text())
        record['run_fingerprint'] = manifest['run_fingerprint']
        for row in record['targets']:
            for key in HEADING_COLUMNS:
                del row[key]
        path.write_text(json.dumps(record))
    (directory / 'run_manifest.json').write_text(json.dumps(manifest))
    stamps = {p: p.stat().st_mtime_ns for p in (directory / 'checkpoints').glob('*.json')}
    run(parser.parse_args(['--resume', str(directory)]))
    assert all(p.stat().st_mtime_ns == stamp for p, stamp in stamps.items())
    assert (directory / 'stats_report.json').read_bytes() == before
    with (directory / 'targets.csv').open() as handle:
        assert len(csv.DictReader(handle).fieldnames) == 20


def test_angle_ties_nearest_bins_ambiguity_and_threshold(monkeypatch):
    import lionsim.features_heading as module
    class ToyZones:
        names = ['Current', 'Near', 'Far']
        def __init__(self, config):
            pass
        def lookup(self, x, y):
            return 'Current'
        def center(self, name):
            return {'Current': [1., 0.], 'Near': [2.9, 0.], 'Far': [4.4, 0.]}[name]
    monkeypatch.setattr(module, 'ZoneMap', ToyZones)
    config = load_config()
    gps = track(np.column_stack((np.arange(31) * .05, np.zeros(31))))
    result = heading_at_report(gps, gps.t_iso.iloc[-1], config)
    # Five-minute average at t=30 is x=1.4; current zone excluded; tie picks nearest.
    assert result['implied_goal'] == 'Near'
    assert result['distance_to_implied_goal_km'] == pytest.approx(1.5)
    assert result['distance_to_implied_goal_bin'] == '<=1.5 km'
    config.data['heading_features']['min_displacement_km'] = result['heading_displacement_km']
    assert heading_at_report(gps, gps.t_iso.iloc[-1], config)['moving']
    config.data['heading_features']['min_displacement_km'] += .001
    assert heading_at_report(gps, gps.t_iso.iloc[-1], config)['implied_goal'] == 'none'
    config.data['heading_features']['min_displacement_km'] = .15
    gps['y_km'] = gps['x_km']
    result = heading_at_report(gps, gps.t_iso.iloc[-1], config)
    assert result['implied_goal'] == 'ambiguous' and result['moving']
    assert result['distance_to_implied_goal_km'] is None


def test_frozen_simulation_and_statistics_identical_with_analysis_settings():
    from lionsim.config import Config
    from lionsim.simulator import simulate_day
    from lionsim.reports import build_reports
    from lionsim.stats import summarize_for_stats
    config = load_config()
    old = config.to_dict()
    del old['heading_features']
    del old['l5_analysis']
    legacy = Config(old)
    original, current = simulate_day(legacy, seed=91), simulate_day(config, seed=91)
    pd.testing.assert_frame_equal(original.gps, current.gps)
    pd.testing.assert_frame_equal(original.hidden_state, current.hidden_state)
    assert original.events == current.events
    assert summarize_for_stats(original, build_reports(original, legacy), legacy) == summarize_for_stats(current, build_reports(current, config), config)
