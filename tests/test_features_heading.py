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
