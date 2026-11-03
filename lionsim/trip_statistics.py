"""Analysis-only committed-trip measurements; never predictor inputs."""

from collections import Counter

import pandas as pd

from .features_path import path_metrics, smoothed_observed_prefix


def summarize_trips(day, config):
    """Keep scalar geometry for all trips, including interruptions and day end.

    Hidden rows describe intervals; the terminal end minute is the GPS endpoint.
    Smoothing includes only earlier fixes, including history before departure.
    """
    hidden = day.hidden_state
    if 'trip_id' not in hidden or day.gps.empty:
        return []
    gps = day.gps
    observed = smoothed_observed_prefix(gps, gps.iloc[-1]['t_iso'], config)
    true = gps[['x_true_km', 'y_true_km']].rename(
        columns={'x_true_km': 'x_km', 'y_true_km': 'y_km'}).copy()
    true.index = pd.DatetimeIndex(pd.to_datetime(gps['t_iso']))
    origin = true.index[0]
    result = []
    for trip_id, rows in hidden.dropna(subset=['trip_id']).groupby('trip_id', sort=True):
        first, last = rows.iloc[0], rows.iloc[-1]
        start, end = int(first['trip_start_minute']), int(last['trip_end_minute'])
        begin, finish = origin + pd.Timedelta(minutes=start), origin + pd.Timedelta(minutes=end)
        measured = [path_metrics(path.loc[begin:finish], config['features_path']['grid_cell_km'])
                    for path in (observed, true)]
        result.append({'day': day.day_index, 'trip_id': int(trip_id),
                       'goal': first['trip_goal'], 'status': last['trip_status'],
                       'start_minute': start, 'end_minute': end,
                       'urgency': float(first['trip_urgency']), 'boredom': float(first['trip_boredom']),
                       'observed': measured[0], 'true': measured[1]})
    return result


def attach_trip_evaluation(report, trips, config):
    # Local import avoids a module cycle while sharing the established missing-data rules.
    from .stats import _correlation

    goals = {'Hunting ground', 'Waterhole', 'Shade', 'Den'}
    correlations = {
        'boredom_straightness': _correlation((t['boredom'], t['observed']['straightness']) for t in trips),
        'urgency_straightness': _correlation((t['urgency'], t['observed']['straightness']) for t in trips if t['goal'] in goals),
        'urgency_speed': _correlation((t['urgency'], t['observed']['mean_speed_kmh']) for t in trips),
        'observed_true_straightness': _correlation((t['observed']['straightness'], t['true']['straightness']) for t in trips),
    }
    deviations = [t['observed']['max_perpendicular_distance_km'] for t in trips]
    fraction = sum(v is not None and v >= config['features_path']['detour_threshold_km']
                   for v in deviations) / len(trips) if trips else None
    report['trip_movement'] = {
        'count': len(trips), 'by_status': dict(sorted(Counter(t['status'] for t in trips).items())),
        'correlations': correlations, 'detour_fraction': fraction,
        'missing_detour_geometry': sum(v is None for v in deviations), 'per_trip': trips,
        'definition': 'All hidden committed trips (including interrupted/day-end) on identical GPS start/end boundaries. '
                      'Observed positions use causal trailing smoothing; true positions are unsmoothed. '
                      'Mean trip speed includes waits. Detours use realized observed chord deviation, not planned waypoints. '
                      'Urgency/straightness uses Hunting ground, Waterhole, Shade and Den; other correlations use all trips. '
                      'These analysis-only hidden boundaries differ from observable inter-zone predictor segments.'}
    targets = config['targets']

    def check(name, value, low=None, high=None, hard=False):
        passes = value is not None and (low is None or value >= low) and (high is None or value <= high)
        report['checks'].append({'name': name, 'observed': value, 'expected': {'min': low, 'max': high},
                                 'status': 'PASS' if passes else 'FAIL' if hard or value is None else 'WARN',
                                 'message': 'Hard phase-three guardrail.' if hard else 'Phase-three trip target; paired counts in trip_movement.'})

    for name, suffix in [('boredom_straightness', 'max'), ('urgency_straightness', 'min'),
                         ('urgency_speed', 'min'), ('observed_true_straightness', 'min')]:
        limit = targets[f'trip_{name}_{suffix}']
        check(f'trip_{name}', correlations[name]['value'], **{'high' if suffix == 'max' else 'low': limit})
    check('trip_detour_fraction', fraction, *targets['trip_detour_fraction_range'])
    check('guardrail_walking_hours', report['hours_per_behaviour']['walking'], high=targets['guardrail_walking_hours_max'], hard=True)
    check('guardrail_zone_entries', report['zone_entries_per_day']['mean'], low=targets['guardrail_entries_min'], hard=True)
    check('guardrail_walking_speed', report['path_statistics']['pooled_mean_walking_speed_kmh'], high=targets['guardrail_speed_max_kmh'], hard=True)
    check('guardrail_abandoned_trips', report['path_statistics']['aggregates']['abandoned_trip_count']['mean'], high=targets['guardrail_abandoned_max'], hard=True)
    validation = report['validation']
    check('guardrail_event_rules', int(validation['days_checked'] == report['days_simulated']
                                     and report['days_simulated'] > 0 and validation['days_failed'] == 0), low=1, hard=True)
    counts = Counter(c['status'] for c in report['checks'])
    report['check_counts'] = {status: counts[status] for status in ('PASS', 'WARN', 'FAIL')}


def compare_reference(report, reference):
    """List every status change; absent formerly passing checks count as failures."""
    current = {c['name']: c for c in report['checks']}
    changes, failed = [], []
    for old in reference['checks']:
        new = current.get(old['name'], {'status': 'MISSING', 'observed': None})
        if old['status'] != new['status']:
            changes.append({'name': old['name'], 'before': old['status'], 'after': new['status'],
                            'before_value': old['observed'], 'after_value': new['observed']})
        if old['status'] == 'PASS' and new['status'] in ('FAIL', 'MISSING'):
            failed.append(old['name'])
    return {'reference_version': reference['version'], 'reference_commit': reference['commit'],
            'reference_days': reference['days'], 'reference_seed': reference['seed'],
            'status_changes': changes, 'previously_passing_failures': failed,
            'status': 'FAIL' if failed else 'PASS',
            'note': 'PASS→WARN changes are listed, not hidden or promoted to FAIL; original target semantics are unchanged.'}


def main():
    """Write an explicit comparison without silently loading a reference in normal runs."""
    import argparse
    import json
    from pathlib import Path
    from .io_utils import write_json, write_text

    parser = argparse.ArgumentParser(description='Compare completed statistics with archived accepted checks')
    parser.add_argument('run', type=Path)
    parser.add_argument('--reference', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.run / 'run_manifest.json').read_text())
    reference = json.loads(args.reference.read_text())
    report = json.loads((args.run / 'stats_report.json').read_text())
    if (manifest['status'] != 'complete' or report['days_simulated'] != reference['days']
            or manifest['seed'] != reference['seed']):
        parser.error('Comparison requires a complete run with matching reference seed and day count')
    result = compare_reference(report, reference)
    write_json(args.run / 'baseline_comparison.json', result, True)
    lines = ['# Accepted baseline comparison', '', f"Guardrail: **{result['status']}**.", '',
             result['note'], '', '| Check | Before | After | Before value | After value |',
             '| --- | --- | --- | ---: | ---: |']
    lines += [f"| {c['name']} | {c['before']} | {c['after']} | {c['before_value']} | {c['after_value']} |"
              for c in result['status_changes']]
    write_text(args.run / 'baseline_comparison.md', '\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
