from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from lionsim.config import load_config
from lionsim.phase6_statistics import fixed_diversity, sequence_metrics, weather_baseline, environment_breakdowns
from lionsim.stats import baseline_ladder, summarize_for_stats, build_stats_report, render_stats_markdown
from lionsim.reports import build_reports
from lionsim.simulator import simulate_day


def test_fixed_sample_diversity_reproducible_and_insufficient():
    options=load_config()['phase6_analysis']
    sequences=[('a',str(i%100)) for i in range(500)]
    result=fixed_diversity(sequences,options)
    assert result==fixed_diversity(sequences,options)
    assert result['fixed_samples']['500']['means']['distinct_sequences']==100
    assert result['fixed_samples']['500']['means']['unique_fraction']==pytest.approx(.2)
    assert result['fixed_samples']['500']['means']['top5_share']==pytest.approx(.05)
    assert result['fixed_samples']['500']['means']['normalised_entropy']==pytest.approx(1)
    assert fixed_diversity(sequences[:100],options)['fixed_samples']['200']['status']=='insufficient_days'
    assert sequence_metrics([('a',)]*20)['normalised_entropy']==0
    assert result['fixed_samples']['200']['means']['unique_fraction']>.4


def test_weather_baseline_folds_and_hidden_type_independence():
    config=load_config(); rng=np.random.default_rng(74)
    rows=[{'day':d,'report_index':r,'current_zone':'Den','last_event':'WOKE_UP',
           'shade_entry_hour_bucket':'not_yet','drinks_so_far':0,'chase_attempts_so_far':0,'catch_so_far':0,
           'weather':rng.choice(['rain','hot','clear','overcast']),
           'next_zone_target':rng.choice(['ENTER_DEN','ENTER_WATER','END_OF_DAY'])} for d in range(1,16) for r in range(1,8)]
    ladder=baseline_ladder(rows,config);result=weather_baseline(rows,ladder,config)
    assert result==weather_baseline([{**row,'day_type':'SECRET'} for row in rows],ladder,config)
    for left,right in zip(result['folds'],ladder['folds']):
        assert left['test_days']==right['test_days'] and left['train_days']==right['train_days']
    config.data['phase6_analysis']['l3w_interpolation_k']=10**14
    large=weather_baseline(rows,ladder,config)
    assert large['headline']['mean']==pytest.approx(ladder['headline']['L3']['mean'],abs=1e-10)


def test_stats_include_both_sequences_breakdowns_and_render():
    config=load_config();day=simulate_day(config,seed=72)
    reports=build_reports(day,config);record=summarize_for_stats(day,reports,config)
    assert record['event_sequence']==[e['token'] for e in day.events]
    assert record['day_type']==day.latents['day_type']
    result=build_stats_report([record],config)
    text=render_stats_markdown(result)
    assert 'Fixed-sample sequence diversity' in text and 'Weather and hidden day-type' in text
    group=result['environment_breakdowns']['weather'][day.weather]
    assert group['count']==1 and group['ambient_temp_c']['mean']==pytest.approx(np.mean([r['ambient_temp_c'] for r in reports]))


def test_complete_comparison_report_schema_and_declared_targets(tmp_path):
    from lionsim.phase6_report import build_comparison, render
    config=load_config();day=simulate_day(config,seed=72)
    record=summarize_for_stats(day,build_reports(day,config),config)
    record['validation']={'valid':True,'errors':[]}
    current=build_stats_report([record],config)
    config.data['phase6_analysis']['reference_run']=str(tmp_path/'before')
    current['validation']={'days_checked':500,'days_failed':0}
    # Synthetic fixture for report contract, not an experiment or evaluation sample.
    for kind in ('zone_entries','event_tokens'):
        metrics=fixed_diversity([(str(i%150),) for i in range(500)],config['phase6_analysis'])
        current['fixed_sample_diversity'][kind]={'current':metrics,'v5_4_0':deepcopy(metrics)}
    base={name:{'mean':value,'std':.01} for name,value in zip(('L0','L1','L2','L3'),(1.7,1.1,.7,.6))}
    current['baseline_ladder']={'headline':base,'all_reports':base}
    current['weather_baseline']={'headline':{'mean':.59},'all_reports':{'mean':.59}}
    before=deepcopy(current)
    oracle={'comparisons':{s:{**base,'oracle':{'mean':.55,'std':.01}} for s in ('headline','all_reports')}}
    manifest={'status':'complete','days':500,'seed':3003,'config':config.to_dict()}
    def save(relative,value):
        path=tmp_path/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))
    save('run/run_manifest.json',manifest);save('oracle/run_manifest.json',{**manifest,'days':100,'oracle_rollouts':100})
    save('run/stats_report.json',current);save('before/stats_report.json',before);save('oracle/oracle_report.json',oracle)
    report=build_comparison(tmp_path/'run',tmp_path/'oracle')
    assert report['oracle']['oracle_over_l0']==pytest.approx(.55/1.7)
    assert any(c['name']=='zone_unique_fraction_N200_ratio' and c['status']=='WARN' for c in report['checks'])
    assert 'candidate' in render(report).lower()
    assert 'L3w' in render(report)
