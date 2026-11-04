"""Analysis-only counting baselines; no learned features or simulator changes."""
from collections import Counter
import math

import numpy as np

from .reports import TARGET_CLASSES
from .stats import _cue_bins

MODELS = ('L3', 'L5', 'L5_shuffled', 'L5_truegoal')


def l3_keys(row, config):
    bucket = (str(int(row['report_index'])),)
    state = bucket + tuple('' if row[k] is None else str(row[k]) for k in ('current_zone', 'last_event'))
    return (), bucket, state, state + _cue_bins(row, config)


def fit_l3(training, config):
    tables = [{} for _ in range(4)]
    for row in training:
        for table, key in zip(tables, l3_keys(row, config)):
            table.setdefault(key, Counter())[row['next_zone_target']] += 1
    return tables


def predict_l3(row, tables, config):
    options = config['learnability']
    prior = None
    for level, (table, key) in enumerate(zip(tables, l3_keys(row, config))):
        counts = table.get(key, Counter())
        values = np.array([counts[target] for target in TARGET_CLASSES], dtype=float)
        total = values.sum()
        if level == 3:
            prior = (values + options['l3_interpolation_k'] * prior) / (total + options['l3_interpolation_k'])
        elif total or level == 0:
            alpha = options['laplace_alpha']
            prior = (values + alpha) / (total + alpha * len(TARGET_CLASSES))
    return prior


def moving_flag(row):
    value = row['moving']
    if value in (True, 'True', 'true'):
        return True
    if value in (False, 'False', 'false'):
        return False
    raise ValueError('Invalid moving flag')


def heading_key(row, cue='implied_goal'):
    return int(row['report_index']), row[cue], moving_flag(row)


def fit_heading(training, cue='implied_goal'):
    table = {}
    for row in training:
        table.setdefault(heading_key(row, cue), Counter())[row['next_zone_target']] += 1
    return table


def interpolate(row, table, prior, k, cue='implied_goal'):
    if not math.isfinite(k) or k <= 0:
        raise ValueError('L5 k must be positive and finite')
    counts = table.get(heading_key(row, cue), Counter())
    values = np.array([counts[target] for target in TARGET_CLASSES], dtype=float)
    return (values + k * prior) / (values.sum() + k)


def shuffle_goals(rows, seed, fold, split):
    """Preserve per-report goal marginals within this split; do not mutate inputs."""
    result = [dict(row) for row in rows]
    for index in sorted({int(row['report_index']) for row in result}):
        positions = [i for i, row in enumerate(result) if int(row['report_index']) == index]
        rng = np.random.default_rng(np.random.SeedSequence([seed, fold, split, index]))
        goals = rng.permutation([result[i]['implied_goal'] for i in positions])
        for i, goal in zip(positions, goals):
            result[i]['implied_goal'] = str(goal)
    return result


def validate_folds(rows, folds):
    days = {int(row['day']) for row in rows}
    tested = []
    if len(folds) != 5:
        raise ValueError('L5 requires five day folds')
    if len({(int(r['day']), int(r['report_index'])) for r in rows}) != len(rows):
        raise ValueError('Duplicate day/report')
    for fold in folds:
        training, testing = set(fold['train_days']), set(fold['test_days'])
        if not training or not testing or training & testing or training | testing != days:
            raise ValueError('Invalid or overlapping day folds')
        tested.extend(fold['test_days'])
    if Counter(tested) != Counter({d: 1 for d in days}):
        raise ValueError('Every day must be held out exactly once')


def evaluate(rows, folds, config):
    rows = sorted(rows, key=lambda r: (int(r['day']), int(r['report_index'])))
    validate_folds(rows, folds)
    predictions = []
    options = config['l5_analysis']
    for fold in folds:
        training = [r for r in rows if int(r['day']) in set(fold['train_days'])]
        testing = [r for r in rows if int(r['day']) in set(fold['test_days'])]
        shuffled_train = shuffle_goals(training, options['shuffle_seed'], fold['fold'], 0)
        shuffled_test = shuffle_goals(testing, options['shuffle_seed'], fold['fold'], 1)
        base = fit_l3(training, config)
        main, shuffled, leaky = fit_heading(training), fit_heading(shuffled_train), fit_heading(training, 'true_goal')
        for row, shuffled_row in zip(testing, shuffled_test):
            prior = predict_l3(row, base, config)
            probabilities = (prior, interpolate(row, main, prior, options['interpolation_k']),
                             interpolate(shuffled_row, shuffled, prior, options['interpolation_k']),
                             interpolate(row, leaky, prior, options['interpolation_k'], 'true_goal'))
            target = TARGET_CLASSES.index(row['next_zone_target'])
            predictions.append({'day': int(row['day']), 'report_index': int(row['report_index']),
                                'fold': fold['fold'], 'moving': moving_flag(row),
                                'losses': {name: -math.log(p[target]) for name, p in zip(MODELS, probabilities)}})
    return predictions


def summarize(predictions, headline):
    def scope(records):
        result = {'count': len(records), 'fraction': len(records) / len(predictions) if predictions else 0,
                  'losses': {}}
        for name in MODELS:
            means = [float(np.mean([r['losses'][name] for r in records if r['fold'] == fold]))
                     for fold in sorted({r['fold'] for r in records})]
            result['losses'][name] = {'mean': float(np.mean(means)) if means else None,
                                      'std': float(np.std(means)) if means else None, 'folds': len(means)}
        return result
    def scopes(records):
        return {'all_reports': scope(records),
                'headline': scope([r for r in records if r['report_index'] in headline]),
                'by_report_index': {str(i): scope([r for r in records if r['report_index'] == i])
                                    for i in sorted({r['report_index'] for r in predictions})}}
    result = scopes(predictions)
    result['subsets'] = {name: scopes([r for r in predictions if r['moving'] == flag])
                         for name, flag in (('moving', True), ('stationary', False))}
    # Fractions use each corresponding scope as denominator.
    for subset in result['subsets'].values():
        for name in ('all_reports', 'headline'):
            subset[name]['fraction'] = subset[name]['count'] / result[name]['count'] if result[name]['count'] else 0
        for index, item in subset['by_report_index'].items():
            total = result['by_report_index'][index]['count']
            item['fraction'] = item['count'] / total if total else 0
    return result


def decision(losses):
    l3, l5, shuffled, truegoal = [losses[m]['mean'] for m in MODELS]
    gain = (l3 - l5) / l3 if l3 > 0 else None
    shuffle_gain = (shuffled - l5) / shuffled if shuffled > 0 else None
    verdict = ('WORTH INCLUDING' if gain is not None and shuffle_gain is not None and gain >= .05 and shuffle_gain >= .03
               else 'MARGINAL' if gain is not None and .02 <= gain < .05 else 'NOT HELPFUL')
    gap = (l3 - l5) / (l3 - truegoal) if l3 > truegoal else None
    sentence = (f'The heading cue closes {gap:.1%} of the L3-to-LEAKY-L5_truegoal loss gap.' if gap is not None else
                'The gap closed is undefined because LEAKY L5_truegoal does not improve on L3.')
    return {'verdict': verdict, 'relative_improvement_over_L3': gain,
            'relative_improvement_over_L5_shuffled': shuffle_gain,
            'fraction_of_truegoal_gap_closed': gap, 'gap_sentence': sentence,
            'rule': 'WORTH INCLUDING: >=5% over L3 AND >=3% over shuffled; MARGINAL: >=2% and <5% over L3; NOT HELPFUL otherwise.'}
