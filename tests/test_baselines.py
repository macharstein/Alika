from copy import deepcopy
from lionsim.config import load_config
from lionsim.simulator import simulate_day
from lionsim.reports import build_reports, target_rows


def test_history_cues_exclude_future_and_include_report_boundary():
    config=load_config()
    day=simulate_day(config)
    day.events=[{'t':'2026-01-01T07:00:00','token':'ENTER_SHADE','zone':'Shade'},
                {'t':'2026-01-01T08:00:00','token':'DRINK','zone':'Waterhole'},
                {'t':'2026-01-01T08:00:01','token':'CATCH','zone':'Hunting ground'}]
    reports=build_reports(day,config)
    row=target_rows(day,reports)[0]
    assert row['shade_entry_hour_bucket']==7
    assert row['drinks_so_far']==1
    assert row['catch_so_far']==0
    changed=deepcopy(day)
    changed.latents={}
    changed.events[-1]['token']='CHASE_START'
    changed_row=target_rows(changed,reports)[0]
    assert changed_row==row


import math
import pytest
from lionsim.stats import baseline_ladder, baselines_from_csv
from lionsim.run import build_parser, run


def toy_rows():
    return [{'day':day,'report_index':report,'report_time_bucket':str(report),
             'current_zone':'Den','last_event':'WOKE_UP','next_zone_target':target,
             'shade_entry_hour_bucket':'not_yet','drinks_so_far':0,
             'chase_attempts_so_far':0,'catch_so_far':0}
            for day in range(1,31) for report,target in [(1,'ENTER_DEN'),(2,'ENTER_PLAIN')]]


def test_cross_validation_day_split_and_interpolation():
    result=baseline_ladder(toy_rows(),load_config())
    assert result['cv_folds']==5
    tested=[]
    for fold in result['folds']:
        assert len(fold['train_days'])==24 and len(fold['test_days'])==6
        assert not set(fold['train_days']) & set(fold['test_days'])
        tested.extend(fold['test_days'])
    assert sorted(tested)==list(range(1,31))
    assert result['losses']['L0']==pytest.approx(-math.log(25/57))
    assert result['losses']['L1']==pytest.approx(-math.log(25/33))
    assert result['losses']['L3'] < result['losses']['L2']
    assert result['target_entropy_nats']==pytest.approx(math.log(2))
    assert result['all_reports']['L0']['std']==pytest.approx(0)
    assert 'END_OF_DAY' in result['classes']


def test_unseen_context_interpolates_to_l2_and_order_is_irrelevant():
    rows=toy_rows()
    for row in rows:
        row['current_zone']=str(row['day'])
    first=baseline_ladder(rows,load_config())
    assert first==baseline_ladder(reversed(rows),load_config())
    assert first['l3_zero_training_fraction']==1
    assert first['losses']['L1']==first['losses']['L2']==first['losses']['L3']


def test_large_prior_approaches_l2_and_headline_excludes_late_reports():
    rows=toy_rows()
    for day in range(1,31):
        rows.append({**rows[0], 'day':day, 'report_index':7, 'next_zone_target':'END_OF_DAY'})
    result=baseline_ladder(rows,load_config(overrides=['learnability.l3_interpolation_k=1000000000000']))
    assert result['losses']['L3']==pytest.approx(result['losses']['L2'],abs=1e-9)
    for fold in result['folds']:
        for values in (fold['headline'], fold['all_reports'], *fold['by_report_index'].values()):
            if values['L2'] is not None:
                assert values['L3'] == pytest.approx(values['L2'], abs=1e-9)
    assert result['headline']['L0']['mean'] != result['all_reports']['L0']['mean']
    assert set(result['by_report_index'])==set(map(str,range(1,8)))
    assert result['by_report_index']['3']['L0']['mean'] is None


def test_insufficient_data_and_invalid_smoothing():
    assert baseline_ladder([],load_config())['status']=='insufficient_data'
    with pytest.raises(ValueError):
        load_config(overrides=['learnability.laplace_alpha=0'])
    with pytest.raises(ValueError):
        load_config(overrides=['learnability.train_fraction=1'])


def test_200_day_baseline_ladder_is_finite_and_ordered_with_tolerance(tmp_path):
    directory=run(build_parser().parse_args(['--stats-only','--stats-days','200','--seed','42','--out',str(tmp_path)]))
    result=baselines_from_csv(directory/'targets.csv',load_config())
    losses=result['losses']
    assert all(math.isfinite(value) and value>=0 for value in losses.values())
    assert losses['L0']+0.03>=losses['L1']
    assert losses['L1']+0.03>=losses['L2']
    assert len(result['folds'])==5 and len(result['test_days'])==200
    assert all(len(f['train_days'])==160 and len(f['test_days'])==40 for f in result['folds'])


def path_rows():
    rows = toy_rows()
    for row in rows:
        direct = row['day'] % 2 == 0
        row.update(next_zone_target='ENTER_DEN' if direct else 'ENTER_PLAIN',
                   last_trip_straightness=.98 if direct else .5,
                   last_3h_mean_speed_kmh=None, last_trip_max_perpendicular_distance_km=None)
    return rows


def test_l4_learns_path_cue_on_same_folds_and_reports_fixed_ablations():
    result = baseline_ladder(path_rows(), load_config())
    assert result['headline']['L4']['mean'] < result['headline']['L3']['mean']
    assert result['path_cue_diagnostics']['straightness']['mean'] < result['path_cue_diagnostics']['speed']['mean']
    assert 'no_path_control' in result['path_cue_diagnostics']
    for fold in result['folds']:
        assert not set(fold['train_days']) & set(fold['test_days'])
        assert math.isfinite(fold['headline']['L4'])
    changed = deepcopy(path_rows())
    for row in changed:
        row.update(urgency=999, boredom=-999, x_true_km=1e9, future_target='ENTER_ROAD')
    assert baseline_ladder(changed, load_config()) == result
    assert baseline_ladder(reversed(path_rows()), load_config()) == result


def test_l4_large_prior_equals_l3_in_each_fold_and_report():
    result = baseline_ladder(path_rows(), load_config(overrides=['learnability.l4_interpolation_k=1e12']))
    for fold in result['folds']:
        for values in (fold['headline'], fold['all_reports'], *fold['by_report_index'].values()):
            if values['L3'] is not None:
                assert values['L4'] == pytest.approx(values['L3'], abs=1e-9)


def test_l4_zero_training_cell_is_exact_l3_and_bins_are_fixed():
    from lionsim.stats import _path_cue_bins
    config = load_config()
    assert _path_cue_bins({}, config) == ('missing', 'missing', 'missing')
    assert _path_cue_bins({'last_trip_straightness':.9, 'last_3h_mean_speed_kmh':1.,
                           'last_trip_max_perpendicular_distance_km':.4}, config) == ('high','high','yes')
    rows = path_rows()
    for row in rows:
        row['current_zone'] = str(row['day'])
    result = baseline_ladder(rows, config)
    assert result['l4_zero_training_fraction'] == 1
    assert result['losses']['L4'] == result['losses']['L3']
