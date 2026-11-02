"""Exact state continuation and Monte Carlo oracle contracts."""

from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

from lionsim.config import load_config
from lionsim.reports import build_reports, report_offsets_minutes
from lionsim.simulator import _DaySimulation, simulate_day


def simulation(seed=42):
    return _DaySimulation(load_config(), 1, seed, '2026-01-01',
                          np.random.SeedSequence(seed).spawn(1)[0])


def test_original_rng_resume_reproduces_entire_day_at_every_report():
    config = load_config()
    original = simulate_day(config)
    running = simulation()
    for offset in report_offsets_minutes(config)[:-1]:
        running.advance_to(offset)
        snapshot = running.snapshot()
        resumed = _DaySimulation.resume(snapshot).run()
        assert resumed.events == original.events
        assert resumed.traffic_times == original.traffic_times
        assert resumed.latents == original.latents
        assert resumed.seed_info == original.seed_info
        pd.testing.assert_frame_equal(resumed.gps, original.gps)
        pd.testing.assert_frame_equal(resumed.hidden_state, original.hidden_state)
        assert build_reports(resumed, config) == build_reports(original, config)
        assert snapshot.next_minute == offset
        assert len(snapshot.history['behaviours']) == offset
        boundary = (snapshot.start + timedelta(minutes=offset)).isoformat()
        assert all(event['t'] < boundary for event in snapshot.events)


def test_snapshots_and_restores_do_not_share_mutable_state():
    running = simulation()
    running.advance_to(600)
    saved = running.snapshot()
    resumed = _DaySimulation.resume(saved)
    resumed.position[:] = 0
    resumed.bars[:] = 0
    resumed.latents['heat'] = 10
    resumed.events.clear()
    resumed.history['goals'].clear()
    resumed.rng.random(10)
    assert saved.events == running.events
    assert saved.history['goals'] == running.history['goals']
    assert saved.latents == running.latents
    np.testing.assert_array_equal(saved.bars, running.bars)
    assert saved.rng.bit_generator.state == running.rng.bit_generator.state
    with pytest.raises(ValueError):
        running.advance_to(599)
    with pytest.raises(ValueError):
        running.advance_to(1441)


def test_rollout_streams_are_repeatable_distinct_and_preserve_observed_traffic():
    from lionsim.oracle import branch_snapshot, rollout_sequences
    running = simulation()
    running.advance_to(12 * 60)
    snapshot = running.snapshot()
    state = snapshot.rng.bit_generator.state
    sequences = rollout_sequences(snapshot, 3)
    assert len({tuple(child.generate_state(4)) for child in sequences}) == 3
    repeated = rollout_sequences(snapshot, 3)
    assert [list(s.generate_state(4)) for s in sequences] == [list(s.generate_state(4)) for s in repeated]
    branches = [branch_snapshot(snapshot, child) for child in sequences]
    assert snapshot.rng.bit_generator.state == state
    for branch in branches:
        boundary = snapshot.next_minute * 60
        np.testing.assert_array_equal(branch.car_seconds[branch.car_seconds <= boundary],
                                      snapshot.car_seconds[snapshot.car_seconds <= boundary])
        assert branch.events == snapshot.events
        assert branch.latents == snapshot.latents
        assert branch.car_pointer == snapshot.car_pointer
        assert branch.road_pending == snapshot.road_pending
    assert len({tuple(branch.car_seconds) for branch in branches}) > 1


def test_oracle_counts_smoothing_actual_targets_and_reproducibility():
    from lionsim.oracle import evaluate_day
    from lionsim.reports import TARGET_CLASSES
    config = load_config()
    day, rows = evaluate_day(config, rollouts=3)
    expected = simulate_day(config)
    assert day.events == expected.events
    pd.testing.assert_frame_equal(day.gps, expected.gps)
    assert len(rows) == 7
    assert [r['actual_target'] for r in rows] == [r['next_zone_target'] for r in build_reports(expected, config)[:-1]]
    for row in rows:
        assert sum(row['counts'].values()) == 3
        assert set(row['counts']) == set(TARGET_CLASSES)
        assert sum(row['probabilities'].values()) == pytest.approx(1)
        assert row['actual_probability'] == pytest.approx((row['counts'][row['actual_target']] + 1) / 12)
        assert np.isfinite(row['log_loss_nats'])
        assert row['log_loss_nats'] >= row['smoothing_floor_nats']
    assert evaluate_day(config, rollouts=3)[1] == rows
    with pytest.raises(ValueError, match='at least 1'):
        evaluate_day(config, rollouts=0)


def test_oracle_comparison_uses_same_holdout_and_reports_sampling_floor():
    from lionsim.oracle import oracle_report, render_oracle_markdown
    config = load_config()
    ladder = {'status': 'complete', 'losses': dict(L0=2., L1=1.5, L2=1., L3=.9),
              'test_days': [2], 'test_rows': 1}
    rows = [{'day': 1, 'log_loss_nats': 10., 'smoothing_floor_nats': .01},
            {'day': 2, 'log_loss_nats': .05, 'smoothing_floor_nats': .01}]
    result = oracle_report(rows, ladder, config)
    assert result['losses']['oracle'] == .05
    assert result['all_days_loss_nats'] == pytest.approx(5.025)
    assert result['interpretation'] == 'oracle near zero: too deterministic'
    rows[1]['log_loss_nats'] = 2.1
    assert oracle_report(rows, ladder, config)['interpretation'] == 'oracle close to L0: too noisy'
    rows[1]['log_loss_nats'] = .5
    rows[1]['smoothing_floor_nats'] = .4
    result = oracle_report(rows, ladder, config)
    assert result['interpretation'] == 'balanced'
    assert result['near_zero_resolvable'] is False
    with pytest.raises(ValueError, match='same report rows'):
        oracle_report(rows[:1], ladder, config)
    empty = oracle_report([], {'status': 'insufficient_data', 'losses': dict.fromkeys(('L0','L1','L2','L3'))}, config)
    assert empty['status'] == 'insufficient_data'
    assert 'Need at least two' in render_oracle_markdown(empty)


def test_oracle_cli_resume_matches_uninterrupted_run(tmp_path):
    import json
    from lionsim.run import build_parser, run
    parser = build_parser()
    options = ['--oracle', '--oracle-days', '3', '--oracle-rollouts', '2']
    partial = run(parser.parse_args(options + ['--chunk-size', '1', '--out', str(tmp_path / 'partial')]))
    manifest = json.loads((partial / 'run_manifest.json').read_text())
    assert manifest['oracle'] and manifest['oracle_rollouts'] == 2
    assert manifest['status'] == 'partial' and manifest['completed_days'] == 1
    checkpoint = next((partial / 'checkpoints').glob('*.json'))
    stamp = checkpoint.stat().st_mtime_ns
    run(parser.parse_args(['--resume', str(partial), '--workers', '2']))
    assert checkpoint.stat().st_mtime_ns == stamp
    manifest = json.loads((partial / 'run_manifest.json').read_text())
    assert manifest['status'] == 'complete' and manifest['completed_days'] == 3
    assert not list(partial.rglob('gps*'))
    assert not list(partial.rglob('*.png'))
    full = run(parser.parse_args(options + ['--out', str(tmp_path / 'full')]))
    for name in ('targets.csv', 'oracle_report.json', 'oracle_report.md', 'stats_report.json', 'stats_report.md'):
        assert (partial / name).read_bytes() == (full / name).read_bytes()
    oracle = json.loads((partial / 'oracle_report.json').read_text())
    assert oracle['report_count'] == 21
    assert oracle['test_days'] == [1, 2, 3] and oracle['test_rows'] == 21
    assert '2026-01-03T08:00:00' in (partial / 'oracle_report.md').read_text()
    assert 'Hidden-state oracle' in (partial / 'stats_report.md').read_text()
    with pytest.raises(ValueError, match='Cannot change --oracle-rollouts'):
        run(parser.parse_args(['--resume', str(partial), '--oracle-rollouts', '3']))
    with pytest.raises(ValueError, match='Cannot change --oracle-days'):
        run(parser.parse_args(['--resume', str(partial), '--oracle-days', '4']))


def test_oracle_cli_defaults_overrides_keep_files_and_mode_guards(tmp_path):
    import json
    from lionsim.run import build_parser, run
    parser = build_parser()
    directory = run(parser.parse_args(['--oracle', '--keep-files', '--set', 'learnability.oracle_days=1',
                                       '--set', 'learnability.oracle_rollouts=1', '--out', str(tmp_path)]))
    manifest = json.loads((directory / 'run_manifest.json').read_text())
    assert manifest['days'] == 1 and manifest['oracle_rollouts'] == 1
    assert manifest['config']['learnability']['oracle_rollouts'] == 1
    assert list(directory.rglob('gps*'))
    assert not list(directory.rglob('*.png'))
    assert json.loads((directory / 'oracle_report.json').read_text())['status'] == 'insufficient_data'
    for options in (['--oracle-days', '2'], ['--oracle-rollouts', '1'], ['--oracle', '--days', '2']):
        with pytest.raises(ValueError):
            run(parser.parse_args(options + ['--out', str(tmp_path)]))
    normal = run(parser.parse_args(['--stats-only', '--stats-days', '1', '--out', str(tmp_path)]))
    with pytest.raises(ValueError, match='Cannot switch'):
        run(parser.parse_args(['--resume', str(normal), '--oracle']))


@pytest.mark.parametrize('at_zero', [True, False])
def test_oracle_preserves_entry_observed_at_exact_report_boundary(at_zero):
    from lionsim.oracle import branch_snapshot, rollout_sequences
    from lionsim.zones import HysteresisTracker
    snapshot = simulation()
    snapshot.advance_to(180)
    snapshot.position = snapshot.centres['Waterhole'].copy()
    snapshot.tracker = HysteresisTracker(required_minutes=1, initial_zone='Den')
    # An entry stamped exactly at the report time is observed, not a target.
    for seed in range(100):
        rng = np.random.default_rng(seed)
        if (int(rng.integers(0, 10)) == 0) == at_zero:
            snapshot.rng = np.random.default_rng(seed)
            break
    expected = _DaySimulation.resume(snapshot)
    expected.advance_to(181)
    boundary = (snapshot.start + timedelta(minutes=180)).isoformat()
    seen = [e for e in expected.events if e['t'] == boundary]
    assert bool(seen) == at_zero
    for child in rollout_sequences(snapshot, 10):
        branch = branch_snapshot(snapshot, child)
        branch.advance_to(181)
        assert [e for e in branch.events if e['t'] == boundary] == seen


def test_resume_regenerates_incomplete_oracle_checkpoint_only(tmp_path):
    import json
    from lionsim.io_utils import write_json
    from lionsim.run import build_parser, run
    parser = build_parser()
    directory = run(parser.parse_args(['--oracle', '--oracle-days', '2', '--oracle-rollouts', '1', '--out', str(tmp_path)]))
    before = (directory / 'oracle_report.json').read_bytes()
    first, second = sorted((directory / 'checkpoints').glob('*.json'))
    stamp = second.stat().st_mtime_ns
    damaged = json.loads(first.read_text())
    damaged['oracle'].pop()
    write_json(first, damaged)
    run(parser.parse_args(['--resume', str(directory)]))
    assert second.stat().st_mtime_ns == stamp
    assert (directory / 'oracle_report.json').read_bytes() == before
