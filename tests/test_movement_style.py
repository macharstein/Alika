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
    config = load_config()
    bars = np.array([.8, .7, .6, .7, .6])
    def plan():
        return plan_style(config, ZoneMap(config), goal, bars,
                          np.array([2., 5.]), np.array([7., 5.]), np.random.default_rng(42))
    s = plan()
    u = {'Den': .3, 'Shade': .6, 'Waterhole': .6, 'Hunting ground': .8,
         'Feeding spot': .8, 'Plain': .2, 'Kopje': .2, 'Road': .2}[goal]
    assert s.urgency == pytest.approx(u)
    assert s.goal_attraction == pytest.approx(.4 * (.6 + .8 * u))
    assert s.turn_sd_degrees == pytest.approx(25 * (1 + .8 * .7 - .5 * u))
    assert s.speed_multiplier == pytest.approx(.85 + .3 * u)
    bars[4] = .39
    assert plan().turn_sd_degrees == pytest.approx(s.turn_sd_degrees + 25 * .2)


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


def controlled_trip(seed=42, boredom=.6, urgency=.5, overrides=()):
    from lionsim.simulator import _DaySimulation
    config = load_config(overrides=overrides)
    sim = _DaySimulation(config, 1, seed, '2026-01-01', np.random.SeedSequence(seed))
    sim.minute = sim.offset('16:00')
    sim.position = np.array([2., 5.5])
    sim.heading = 0.
    sim.raw_zone = None
    sim.mode, sim.goal = 'walking', 'Waterhole'
    sim.bars[:] = [.5, .8, urgency, boredom, .8]
    sim._sync_trip()
    return sim


def path_ratio_and_speed(seed, boredom, urgency):
    sim = controlled_trip(seed, boredom, urgency)
    start, target = sim.position.copy(), sim.trip['target'].copy()
    length = 0.
    for step in range(1, 501):
        before = sim.position.copy()
        sim._move_trip()
        length += float(np.linalg.norm(sim.position - before))
        if np.linalg.norm(sim.position - target) < .08:
            return length / np.linalg.norm(sim.position - start), length * 60 / step
    pytest.fail('Controlled trip did not converge to its goal')


def test_expected_path_length_ratio_rises_with_boredom_and_falls_with_urgency():
    # Same start, goal, fixed-seed ensemble and unchanged physiology within each
    # trip isolate geometry from the higher-level scheduling/arrival decisions.
    def mean(boredom, urgency):
        return np.mean([path_ratio_and_speed(seed, boredom, urgency) for seed in range(40)], axis=0)
    quiet, bored = mean(.1, .5), mean(.95, .5)
    relaxed, urgent = mean(.6, .1), mean(.6, .9)
    assert bored[0] > quiet[0] + .01
    assert relaxed[0] > urgent[0] + .01
    assert urgent[1] > relaxed[1]


def test_trip_style_survives_bar_changes_and_traffic_wait_then_interrupts():
    sim = controlled_trip(overrides=['movement_style.detour_probability_scale=2'], boredom=1)
    original = sim.trip
    frozen = original['style']
    before = sim.position.copy()
    sim._move_trip()
    sim._record_trip_step(before)
    sim.bars[:] = [.1, .1, .1, .1, .1]
    sim.mode = 'traffic_wait'
    sim._sync_trip()
    assert sim.trip is original and sim.trip['style'] is frozen
    sim._record_trip_step(sim.position.copy())
    assert sim.history['trip_rows'][-1]['trip_id'] == original['id']
    sim.mode = 'walking'
    sim._sync_trip()
    assert sim.trip is original
    sim._commit_goal('Den', reason='fatigue')
    sim.minute += 1
    sim._sync_trip()
    assert sim.trip['id'] == original['id'] + 1
    assert sim.trip['style'].urgency == pytest.approx(.9)
    assert sim.history['trip_rows'][-1]['trip_status'] == 'interrupted'
    assert sim.history['trip_rows'][-1]['trip_end_minute'] == sim.minute


def test_trip_snapshot_has_independent_waypoints_and_exact_continuation():
    from lionsim.simulator import _DaySimulation
    sim = controlled_trip(boredom=1, overrides=['movement_style.detour_probability_scale=2'])
    assert sim.trip['style'].waypoints
    saved = sim.snapshot()
    resumed = _DaySimulation.resume(saved)
    sim._move_trip()
    resumed._move_trip()
    np.testing.assert_array_equal(sim.position, resumed.position)
    resumed.trip['style'].waypoints[0][:] = 0
    assert np.any(saved.trip['style'].waypoints[0] != 0)
    assert np.any(sim.trip['style'].waypoints[0] != 0)


def test_hidden_trip_diagnostics_match_true_path_and_do_not_enter_json(tmp_path):
    import json
    import pandas as pd
    from lionsim.simulator import simulate_day
    from lionsim.io_utils import write_day
    from lionsim.reports import build_reports
    config = load_config()
    day = simulate_day(config, seed=42)
    trips = day.hidden_state.dropna(subset=['trip_id'])
    assert not trips.empty
    for trip_id, rows in trips.groupby('trip_id'):
        for column in ('trip_goal', 'trip_urgency', 'trip_boredom', 'trip_mood',
                       'trip_detour_count', 'trip_planned_straightness', 'trip_speed_multiplier'):
            assert rows[column].nunique() == 1
        first, last = rows.iloc[0], rows.iloc[-1]
        start, end = int(first.trip_start_minute), int(last.minute_index) + 1
        path = day.gps.iloc[start:end + 1][['x_true_km', 'y_true_km']].to_numpy()
        length = np.linalg.norm(np.diff(path, axis=0), axis=1).sum()
        assert last.trip_path_length_km == pytest.approx(length)
        assert last.trip_realized_straightness == pytest.approx(np.linalg.norm(path[-1] - path[0]) / length)
        assert last.trip_status in ('arrived', 'interrupted', 'day_end')
        assert last.trip_end_minute == end
        assert rows.iloc[:-1].trip_end_minute.isna().all()
        assert rows.trip_realized_straightness.between(0, 1).all()
        if last.trip_status == 'arrived':
            assert ZoneMap(config).contains(last.trip_goal, *path[-1])
    payload = write_day(day, build_reports(day, config), tmp_path, prefer_parquet=False)
    hidden = pd.read_csv(tmp_path / 'hidden_state.csv.gz')
    assert 'trip_urgency' in hidden and hidden.trip_id.notna().any()
    assert 'trip_' not in json.dumps(payload)
    assert 'trip_' not in ','.join(pd.read_csv(tmp_path / 'gps.csv.gz').columns)


def test_style_reproducibility_schema_and_resume_contract(tmp_path):
    import json
    import pandas as pd
    from lionsim import SCHEMA_VERSION, __version__
    from lionsim.run import build_parser, run
    from lionsim.simulator import simulate_day
    assert SCHEMA_VERSION == 'lionsim-v5' and __version__ == '5.0.0'
    first, second = simulate_day(load_config(), seed=42), simulate_day(load_config(), seed=42)
    pd.testing.assert_frame_equal(first.gps, second.gps)
    pd.testing.assert_frame_equal(first.hidden_state, second.hidden_state)
    assert first.events == second.events and first.latents == second.latents
    parser = build_parser()
    directory = run(parser.parse_args(['--stats-only', '--stats-days', '2', '--chunk-size', '1', '--out', str(tmp_path)]))
    manifest = json.loads((directory / 'run_manifest.json').read_text())
    assert manifest['schema_version'] == SCHEMA_VERSION
    assert manifest['config']['movement_style'] == load_config()['movement_style']
    run(parser.parse_args(['--resume', str(directory)]))
    assert json.loads((directory / 'run_manifest.json').read_text())['status'] == 'complete'
    manifest['schema_version'] = 'lionsim-v4'
    (directory / 'run_manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='schema'):
        run(parser.parse_args(['--resume', str(directory)]))


@pytest.mark.parametrize('action', ['stalk', 'chase'])
def test_style_coefficients_do_not_change_stalking_or_chase(action):
    from lionsim.simulator import _DaySimulation
    configs = [load_config(), load_config(overrides=[
        'movement_style.turn_boredom_weight=5', 'movement_style.speed_intercept=0.3',
        'movement_style.attraction_urgency_weight=2', 'movement_style.detour_probability_scale=2'])]
    sims = [_DaySimulation(c, 1, 42, '2026-01-01', np.random.SeedSequence(42)) for c in configs]
    for sim in sims:
        sim.minute = sim.offset('20:00')
        sim.position = sim.centres['Hunting ground'].copy()
        sim.raw_zone = sim.goal = 'Hunting ground'
        sim.mode = 'hunting'
        sim._sync_trip()
        assert sim.trip is None
        if action == 'chase':
            sim._chase()
        else:
            sim._move(sim.position + np.array([.5,.3]), sim.movement['stalk_speed_kmh'],
                      sim.randomness['stalk_heading_sd_degrees'], confine='Hunting ground')
    np.testing.assert_array_equal(sims[0].position, sims[1].position)
    np.testing.assert_array_equal(sims[0].bars, sims[1].bars)
    assert sims[0].events == sims[1].events
    assert sims[0].rng.bit_generator.state == sims[1].rng.bit_generator.state


def test_style_changes_preserve_daily_latents_traffic_and_report_schedule():
    from lionsim.simulator import simulate_day
    from lionsim.reports import build_reports
    configs = [load_config(), load_config(overrides=['movement_style.detour_probability_scale=2'])]
    days = [simulate_day(config, seed=42) for config in configs]
    assert days[0].latents == days[1].latents
    assert days[0].traffic_times == days[1].traffic_times
    times = [[r['report_time'] for r in build_reports(day, config)] for day, config in zip(days, configs)]
    assert times[0] == times[1] and len(times[0]) == 8
