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
