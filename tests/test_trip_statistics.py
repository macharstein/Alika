"""Trip geometry alignment, missing values and hard guardrail semantics."""
from copy import deepcopy
from types import SimpleNamespace
import json

import pandas as pd
import pytest

from lionsim.config import load_config
from lionsim.trip_statistics import summarize_trips, attach_trip_evaluation, compare_reference


def test_trip_geometry_uses_observed_smoothing_and_inclusive_endpoint():
    times = pd.date_range('2026-01-01', periods=7, freq='min')
    gps = pd.DataFrame({'t_iso': times.astype(str), 'x_km': [0,0,0,1,1,2,99],
                        'y_km': [0,0,0,1,0,0,99], 'x_true_km': range(7), 'y_true_km': 0})
    hidden = pd.DataFrame({'trip_id': [1,1], 'trip_start_minute': [2,2],
                           'trip_end_minute': [None,5], 'trip_goal': ['Den']*2,
                           'trip_urgency': [.8]*2, 'trip_boredom': [.2]*2,
                           'trip_status': ['in_progress','interrupted']})
    day = SimpleNamespace(gps=gps, hidden_state=hidden, day_index=1)
    config=load_config(overrides=['features_path.smoothing_minutes=1'])
    trip = summarize_trips(day,config)[0]
    assert trip['status']=='interrupted'
    assert trip['true']['straightness']==1
    assert trip['observed']['max_perpendicular_distance_km']==1
    assert trip['observed']['straightness'] < 1
    assert trip['observed']['mean_speed_kmh']==pytest.approx((2**.5+2)*20)
    changed=deepcopy(day)
    changed.gps.loc[6,['x_km','y_km']]=-999
    assert summarize_trips(changed,config)==[trip]
    assert summarize_trips(day,load_config())[0]['observed'] != trip['observed']
    changed.gps['x_true_km']=0
    assert summarize_trips(changed,config)[0]['observed']==trip['observed']
    json.dumps(trip,allow_nan=False)


def report_fixture():
    return {'checks': [], 'days_simulated':1, 'hours_per_behaviour':{'walking':load_config()['targets']['guardrail_walking_hours_max'] + .1},
            'zone_entries_per_day':{'mean':6.9}, 'path_statistics':{
                'pooled_mean_walking_speed_kmh':4.1,
                'aggregates':{'abandoned_trip_count':{'mean':1.1}}},
            'validation':{'days_checked':1,'days_failed':0}}


def test_trip_targets_include_all_statuses_and_filter_only_urgency_straightness():
    trips=[{'status':status, 'goal':goal, 'boredom':b, 'urgency':1-b,
            'observed':{'straightness':1-b,'mean_speed_kmh':1-b,
                        'max_perpendicular_distance_km':deviation},
            'true':{'straightness':1-b}}
           for status,goal,b,deviation in [('arrived','Den',.1,.1),
               ('interrupted','Shade',.5,.4),('day_end','Plain',.9,None)]]
    report=report_fixture()
    attach_trip_evaluation(report,trips,load_config())
    metrics=report['trip_movement']
    assert metrics['count']==3 and metrics['missing_detour_geometry']==1
    assert metrics['detour_fraction']==pytest.approx(1/3)
    assert metrics['correlations']['boredom_straightness']['value']==pytest.approx(-1)
    assert metrics['correlations']['urgency_straightness']['count']==2
    assert metrics['correlations']['urgency_speed']['count']==3
    checks={c['name']:c for c in report['checks']}
    for name in ('walking_hours','zone_entries','walking_speed','abandoned_trips'):
        assert checks['guardrail_'+name]['status']=='FAIL'
    assert checks['guardrail_event_rules']['status']=='PASS'
    assert checks['trip_detour_fraction']['status']=='WARN'
    empty=report_fixture()
    attach_trip_evaluation(empty,[],load_config())
    assert empty['trip_movement']['correlations']['urgency_speed']['value'] is None
    json.dumps(empty,allow_nan=False)


def test_reference_comparison_lists_all_changes_and_missing_passes_fail():
    reference={'version':'4.5.0','commit':'abc','days':500,'seed':42,'checks':[
        {'name':n,'status':s,'observed':1} for n,s in [('a','PASS'),('b','WARN'),('c','PASS')]]}
    report={'checks':[{'name':n,'status':s,'observed':2} for n,s in [('a','WARN'),('b','PASS')]]}
    result=compare_reference(report,reference)
    assert result['status']=='FAIL' and result['previously_passing_failures']==['c']
    assert [(c['before'],c['after']) for c in result['status_changes']]==[('PASS','WARN'),('WARN','PASS'),('PASS','MISSING')]
    report['checks'].append({'name':'c','status':'PASS','observed':1})
    assert compare_reference(report,reference)['status']=='PASS'


def test_comparison_cli_requires_matched_complete_run(tmp_path, monkeypatch):
    from lionsim.trip_statistics import main
    reference={'version':'4.5.0','commit':'abc','days':500,'seed':42,'checks':[]}
    (tmp_path/'reference.json').write_text(json.dumps(reference))
    (tmp_path/'stats_report.json').write_text(json.dumps({'days_simulated':500,'checks':[]}))
    manifest={'status':'partial','seed':42}
    (tmp_path/'run_manifest.json').write_text(json.dumps(manifest))
    monkeypatch.setattr('sys.argv',['compare',str(tmp_path),'--reference',str(tmp_path/'reference.json')])
    with pytest.raises(SystemExit):
        main()
    manifest['status']='complete'
    (tmp_path/'run_manifest.json').write_text(json.dumps(manifest))
    main()
    assert json.loads((tmp_path/'baseline_comparison.json').read_text())['status']=='PASS'
    assert 'Guardrail: **PASS**' in (tmp_path/'baseline_comparison.md').read_text()
