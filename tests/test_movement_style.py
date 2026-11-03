"""S8.1 frozen movement style, geometry and trip lifecycle contracts."""

import numpy as np
import pytest

from lionsim.config import load_config
from lionsim.movement_style import plan_style
from lionsim.zones import ZoneMap


def style(goal='Waterhole', boredom=.7, urgency=.8, mood=.6, seed=42, overrides=()):
    config = load_config(overrides=overrides)
    bars = np.array([urgency, 1 - urgency, urgency, boredom, mood])
    return plan_style(config, ZoneMap(config), goal, bars,
                      np.array([2., 5.]), np.array([7., 5.]), np.random.default_rng(seed))


@pytest.mark.parametrize('goal', ['Den', 'Shade', 'Waterhole', 'Hunting ground', 'Feeding spot', 'Plain', 'Kopje', 'Road'])
def test_goal_urgency_and_exact_style_formulas(goal):
    s = style(goal=goal)
    u = .2 if goal in ('Plain', 'Kopje', 'Road') else .8
    assert s.urgency == pytest.approx(u)
    assert s.goal_attraction == pytest.approx(.4 * (.6 + .8 * u))
    assert s.turn_sd_degrees == pytest.approx(25 * (1 + .8 * .7 - .5 * u))
    assert s.speed_multiplier == pytest.approx(.85 + .3 * u)
    assert style(goal=goal, mood=.39).turn_sd_degrees == pytest.approx(s.turn_sd_degrees + 25 * .2)


def test_detour_plan_bounds_and_zone_exclusions():
    config = load_config(overrides=['movement_style.detour_probability_scale=2'])
    zones = ZoneMap(config)
    points = [([.05,.05],[9.95,.05]), ([.05,9.95],[9.95,9.95]),
              ([.05,.05],[.05,9.95]), ([9.95,.05],[9.95,9.95]), ([2.,5.],[7.,5.])]
    for seed, (a, b) in enumerate(points):
        start, target = np.array(a), np.array(b)
        s = plan_style(config, zones, 'Waterhole', np.array([.2,.8,.2,1.,.8]),
                       start, target, np.random.default_rng(seed))
        assert 1 <= len(s.waypoints) <= 2
        for point in s.waypoints:
            assert 0 <= point[0] <= zones.width and 0 <= point[1] <= zones.height
            direction = target - start
            distance = abs(direction[0]*(point-start)[1] - direction[1]*(point-start)[0]) / np.linalg.norm(direction)
            assert .4 <= distance <= 1.
            if seed == 4:  # Open corridor: exclusions are feasible.
                assert all(zones.distance_to(name, *point) > .05 for name in zones.names
                           if name not in (zones.lookup(*start), 'Waterhole'))
        assert 0 < s.planned_straightness < 1


def test_detours_are_probabilistic_and_zero_length_trip_is_defined():
    samples = [style(boredom=1, seed=i) for i in range(100)]
    assert .15 < sum(bool(s.waypoints) for s in samples) / len(samples) < .55
    assert all(not style(boredom=.5, seed=i).waypoints for i in range(10))
    config = load_config()
    s = plan_style(config, ZoneMap(config), 'Den', np.ones(5),
                   np.array([2.,8.]), np.array([2.,8.]), np.random.default_rng(42))
    assert not s.waypoints and s.planned_straightness is None


@pytest.mark.parametrize('override', ['movement_style.detour_count_range=[0,2]',
    'movement_style.detour_offset_km_range=[1,0.4]', 'movement_style.speed_intercept=0',
    'movement_style.low_mood_threshold=1.1', 'movement_style.waypoint_sampling_attempts=1'])
def test_invalid_style_settings_are_rejected(override):
    with pytest.raises(ValueError):
        load_config(overrides=[override])
