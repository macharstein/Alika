"""Monte Carlo next-zone oracle conditioned on the simulator's hidden state.

Snapshots are minute-boundary states, before executing that minute's tick.
Latents, committed durations and scheduled wakes are known hidden state; future
traffic is unobserved exogenous noise and is sampled anew for each branch.
No rollout trajectories or hidden snapshots are written to disk.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from typing import Any

import numpy as np

from .config import Config
from .events import sort_events
from .reports import END_OF_DAY, TARGET_CLASSES, build_reports, report_offsets_minutes
from .simulator import DayResult, _DaySimulation


def rollout_sequences(snapshot: _DaySimulation, count: int) -> list[np.random.SeedSequence]:
    """Derive reproducible child streams without consuming the saved RNG."""
    if count < 1:
        raise ValueError('oracle rollouts must be at least 1')
    identity = {'rng': snapshot.rng.bit_generator.state,
                'day': snapshot.day_index, 'minute': snapshot.next_minute}
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).digest()
    entropy = [int.from_bytes(digest[i:i + 4], 'little') for i in range(0, len(digest), 4)]
    return np.random.SeedSequence(entropy).spawn(count)


def branch_snapshot(snapshot: _DaySimulation, sequence: np.random.SeedSequence) -> _DaySimulation:
    """Preserve observed traffic and pending reactions; resample only future cars."""
    branch = _DaySimulation.resume(snapshot)
    branch.rng = np.random.default_rng(sequence)
    boundary = snapshot.next_minute * 60
    past = branch.car_seconds[branch.car_seconds <= boundary]
    start = max(boundary + 1, branch.offset(branch.c['tourists']['start']) * 60)
    end = branch.offset(branch.c['tourists']['end']) * 60 or branch.day_minutes * 60
    # The stored traffic process has integer-second timestamps. Independent
    # Poisson increments on the remaining seconds condition on the seen prefix.
    if start < end:
        count = int(branch.rng.poisson(branch.latents['tourist_rate_per_hour'] * (end - start) / 3600))
        future = np.sort(branch.rng.uniform(start, end, count).astype(np.int64))
        branch.car_seconds = np.concatenate((past, future))
    else:
        branch.car_seconds = past.copy()
    branch.car_minute_counts = np.bincount(branch.car_seconds // 60, minlength=branch.day_minutes)
    _condition_boundary_entry(snapshot, branch)
    return branch


def _condition_boundary_entry(snapshot: _DaySimulation, branch: _DaySimulation) -> None:
    """Keep zero-second entries in the observed prefix, never in the target.

    The engine state is immediately before the minute tick, whereas reports
    include events stamped exactly at its boundary. Zone hysteresis is already
    determined by the boundary position. Condition the first entry-time draw on
    whether that entry is observed at second zero; do not reveal its future
    second or any later outcome. All subsequent RNG draws remain independent.
    """
    zone = snapshot._lookup(snapshot.position)
    previous_minute = branch.minute
    branch.minute = snapshot.next_minute
    eligible = branch._can_hunt()
    branch.minute = previous_minute
    if zone == 'Hunting ground' and not eligible:
        zone = None
    if deepcopy(snapshot.tracker).update(zone) is None:
        return
    observed_at_zero = int(deepcopy(snapshot.rng).integers(0, 10)) == 0
    while True:
        state = branch.rng.bit_generator.state
        if (int(branch.rng.integers(0, 10)) == 0) == observed_at_zero:
            # advance_to consumes this accepted draw in its ordinary entry step.
            branch.rng.bit_generator.state = state
            return


def next_target(events: list[dict[str, Any]], report_time: str) -> str:
    return next((event['token'] for event in sort_events(events)
                 if event['t'] > report_time and event['token'] in TARGET_CLASSES), END_OF_DAY)


def evaluate_day(config: Config, day_index: int = 1, seed: int = 42,
                 start_date: str = '2026-01-01', rollouts: int = 100,
                 seed_sequence: np.random.SeedSequence | None = None,
                 ) -> tuple[DayResult, list[dict[str, Any]]]:
    """Generate the original day once, then evaluate every usable report state."""
    if day_index < 1 or rollouts < 1:
        raise ValueError('day_index and oracle rollouts must be at least 1')
    sequence = seed_sequence if seed_sequence is not None else np.random.SeedSequence(seed).spawn(day_index)[day_index - 1]
    original = _DaySimulation(config, day_index, seed, start_date, sequence)
    snapshots = []
    for offset in report_offsets_minutes(config)[:-1]:
        original.advance_to(offset)
        snapshots.append(original.snapshot())
    day = original.run()
    reports = build_reports(day, config)
    alpha = config['learnability']['laplace_alpha']
    rows = []
    for report, snapshot in zip(reports, snapshots):
        counts: Counter[str] = Counter()
        for child in rollout_sequences(snapshot, rollouts):
            branch = branch_snapshot(snapshot, child)
            branch.advance_to(branch.day_minutes)
            counts[next_target(branch.events, report['report_time'])] += 1
        probabilities = {target: (counts[target] + alpha) / (rollouts + alpha * len(TARGET_CLASSES))
                         for target in TARGET_CLASSES}
        actual = report['next_zone_target']
        rows.append({'day': day_index, 'report_index': report['report_index'],
                     'report_time': report['report_time'], 'snapshot_minute': snapshot.next_minute,
                     'actual_target': actual, 'rollouts': rollouts,
                     'counts': {target: counts[target] for target in TARGET_CLASSES},
                     'probabilities': probabilities, 'actual_probability': probabilities[actual],
                     'log_loss_nats': -math.log(probabilities[actual]),
                     'smoothing_floor_nats': -math.log((rollouts + alpha) / (rollouts + alpha * len(TARGET_CLASSES)))})
    return day, rows


def oracle_report(rows: list[dict[str, Any]], ladder: dict[str, Any], config: Config) -> dict[str, Any]:
    """Use the same holdout as the counting ladder; also show all-day oracle loss."""
    result: dict[str, Any] = {
        'status': 'insufficient_data', 'classes': list(TARGET_CLASSES),
        'units': 'Natural-log multiclass log loss (nats); lower is better.',
        'laplace_alpha': config['learnability']['laplace_alpha'],
        'rows': rows, 'report_count': len(rows),
        'all_days_loss_nats': float(np.mean([row['log_loss_nats'] for row in rows])) if rows else None,
        'losses': {**ladder['losses'], 'oracle': None},
        'interpretation': 'Need at least two completed days for the same held-out comparison.',
        'conditioning': 'Minute-boundary hidden state before its tick; fixed daily latents, goal, bars, memory and committed schedules. Future traffic and future decisions are resampled; entry timing is conditioned on the observed zero-second report boundary.',
        'seed_derivation': 'SHA-256 of snapshot PCG64 state, day and minute -> SeedSequence.spawn(rollouts); does not advance the original RNG.',
        'finite_sample_note': 'Monte Carlo estimates with Laplace smoothing; small pilots are diagnostic. The smoothing floor limits measurable loss even for unanimous rollouts. No threshold tuning is performed.',
    }
    if not rows or ladder['status'] != 'complete':
        return result
    test_days = set(ladder['test_days'])
    testing = [row for row in rows if row['day'] in test_days]
    if len(testing) != ladder['test_rows']:
        raise ValueError('Oracle and baseline holdout must contain the same report rows')
    loss = float(np.mean([row['log_loss_nats'] for row in testing]))
    if 'folds' in ladder:
        fold_losses = [float(np.mean([r['log_loss_nats'] for r in testing if r['day'] in f['test_days']])) for f in ladder['folds']]
        loss = float(np.mean(fold_losses))
        result['fold_losses_nats'] = fold_losses
        result['oracle_fold_std_nats'] = float(np.std(fold_losses))
    floor = float(np.mean([row['smoothing_floor_nats'] for row in testing]))
    l0 = ladder['losses']['L0']
    options = config['learnability']
    interpretation = ('oracle near zero: too deterministic' if loss <= options['oracle_near_zero_nats'] else
                      'oracle close to L0: too noisy' if abs(loss - l0) / l0 <= options['oracle_noise_relative_tolerance'] else
                      'balanced')
    result.update(status='complete', test_days=ladder['test_days'], test_rows=len(testing),
                  losses={**ladder['losses'], 'oracle': loss}, interpretation=interpretation,
                  smoothing_floor_nats=floor,
                  near_zero_resolvable=floor <= options['oracle_near_zero_nats'],
                  oracle_minus_L0_nats=loss - l0)
    return result


def render_oracle_markdown(report: dict[str, Any]) -> str:
    lines = ['# Hidden-state oracle', '', report['interpretation'], '', report['conditioning'], '',
             report['finite_sample_note'], '', f"All-day oracle loss: {report['all_days_loss_nats']} nats."]
    if report['status'] == 'complete':
        lines += ['', f"Same held-out days: {report['test_days']}; {report['test_rows']} report targets.", '',
                  '| Model | Held-out log loss (nats) |', '| --- | ---: |']
        lines += [f'| {name} | {value:.6f} |' for name, value in report['losses'].items()]
        lines += ['', f"Laplace smoothing floor: {report['smoothing_floor_nats']:.6f} nats.",
                  f"Can resolve the configured near-zero threshold: {report['near_zero_resolvable']}."]
    lines += ['', '## Report-level outcomes', '',
              '| Day | Report time | Actual next target | Rollouts | P(actual) | Log loss |',
              '| ---: | --- | --- | ---: | ---: | ---: |']
    lines += [f"| {r['day']} | {r['report_time']} | {r['actual_target']} | {r['rollouts']} | {r['actual_probability']:.6f} | {r['log_loss_nats']:.6f} |"
              for r in report['rows']]
    return '\n'.join(lines) + '\n'
