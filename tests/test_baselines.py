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


def test_smoothed_losses_day_split_and_sparse_backoff():
    config=load_config(overrides=['learnability.l3_min_cell_count=1000'])
    result=baseline_ladder(toy_rows(),config)
    assert result['train_days']==list(range(1,22))
    assert result['test_days']==list(range(22,31))
    assert not set(result['train_days']) & set(result['test_days'])
    assert result['losses']['L0']==pytest.approx(-math.log(22/51))
    assert result['losses']['L1']==pytest.approx(-math.log(22/30))
    assert result['losses']['L2']==result['losses']['L3']
    assert result['backoff_rows']['L3']==18
    assert result['target_entropy_nats']==pytest.approx(math.log(2))
    assert 'END_OF_DAY' in result['classes']


def test_unseen_context_backs_off_and_input_order_does_not_change_split():
    rows=toy_rows()
    for row in rows:
        if row['day']>=22:
            row['current_zone']='unseen'
    first=baseline_ladder(rows,load_config())
    assert first==baseline_ladder(reversed(rows),load_config())
    assert first['backoff_rows']['L2']==18
    assert first['losses']['L1']==first['losses']['L2']


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
    assert len(result['train_days'])==140 and len(result['test_days'])==60
