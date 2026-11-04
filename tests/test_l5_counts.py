from collections import Counter
from copy import deepcopy

import numpy as np
import pytest

from lionsim.config import load_config
from lionsim.l5_counts import (decision, evaluate, fit_heading, fit_l3, interpolate,
                               predict_l3, shuffle_goals, summarize, validate_folds)
from lionsim.stats import baseline_ladder


def examples():
    rng = np.random.default_rng(123)
    return [{'day': d, 'report_index': r, 'current_zone': 'Den', 'last_event': 'WOKE_UP',
             'shade_entry_hour_bucket': 'not_yet', 'drinks_so_far': 0, 'chase_attempts_so_far': 0,
             'catch_so_far': 0, 'implied_goal': rng.choice(['Den', 'Waterhole', 'ambiguous']),
             'true_goal': rng.choice(['Den', 'Waterhole']), 'moving': bool(rng.integers(2)),
             'next_zone_target': rng.choice(['ENTER_DEN', 'ENTER_WATER', 'END_OF_DAY'])}
            for d in range(1, 16) for r in range(1, 8)]


def test_large_k_and_unseen_cell_equal_l3():
    config = load_config()
    rows = examples()
    prior = predict_l3(rows[-1], fit_l3(rows[:-7], config), config)
    table = fit_heading(rows[:-7])
    np.testing.assert_allclose(interpolate(rows[-1], table, prior, 1e14), prior, atol=1e-12)
    np.testing.assert_allclose(interpolate(rows[-1], {}, prior, 20), prior, atol=1e-14)
    assert prior.sum() == pytest.approx(1)


def test_shuffle_marginals_split_local_reproducible():
    rows = examples()
    original = deepcopy(rows)
    shuffled = shuffle_goals(rows, 42, 1, 0)
    assert rows == original
    assert shuffled == shuffle_goals(rows, 42, 1, 0)
    assert shuffled != shuffle_goals(rows, 42, 1, 1)
    for index in range(1, 8):
        assert Counter(r['implied_goal'] for r in rows if r['report_index'] == index) == Counter(r['implied_goal'] for r in shuffled if r['report_index'] == index)
    for left, right in zip(rows, shuffled):
        assert {k:v for k,v in left.items() if k != 'implied_goal'} == {k:v for k,v in right.items() if k != 'implied_goal'}
    assert {r['implied_goal'] for r in shuffle_goals([{**r, 'implied_goal': 'train_only'} for r in rows], 42, 1, 0)} == {'train_only'}


def test_same_l3_folds_subsets_and_truegoal_isolation():
    config = load_config()
    rows = examples()
    ladder = baseline_ladder(rows, config)
    folds = ladder['folds']
    validate_folds(rows, folds)
    for f in folds:
        assert not set(f['train_days']) & set(f['test_days'])
    predictions = evaluate(rows, folds, config)
    report = summarize(predictions, [1,2,3,4,5])
    for scope in ('headline', 'all_reports'):
        assert report[scope]['losses']['L3']['mean'] == pytest.approx(ladder[scope]['L3']['mean'], abs=1e-14)
        assert sum(s[scope]['fraction'] for s in report['subsets'].values()) == pytest.approx(1)
    for index, item in report['by_report_index'].items():
        assert item['losses']['L3']['mean'] == pytest.approx(ladder['by_report_index'][index]['L3']['mean'], abs=1e-14)
    changed = evaluate([{**r, 'true_goal': 'Kopje'} for r in rows], folds, config)
    for old, new in zip(predictions, changed):
        for model in ('L3', 'L5', 'L5_shuffled'):
            assert old['losses'][model] == new['losses'][model]
    bad = deepcopy(folds)
    bad[0]['train_days'].append(bad[0]['test_days'][0])
    with pytest.raises(ValueError, match='overlapping'):
        validate_folds(rows, bad)


@pytest.mark.parametrize('l5,shuffle,expected', [(.94,1.,'WORTH INCLUDING'), (.97,1.,'MARGINAL'), (.99,1.,'NOT HELPFUL'), (.94,.95,'NOT HELPFUL')])
def test_decision(l5, shuffle, expected):
    result = decision({k: {'mean':v} for k,v in {'L3':1., 'L5':l5, 'L5_shuffled':shuffle, 'L5_truegoal':.5}.items()})
    assert result['verdict'] == expected
    assert result['fraction_of_truegoal_gap_closed'] == pytest.approx((1-l5)/.5)
    losses = {k:{'mean':1.} for k in ('L3','L5','L5_shuffled','L5_truegoal')}
    assert decision(losses)['fraction_of_truegoal_gap_closed'] is None
