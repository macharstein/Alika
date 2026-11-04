"""Declared phase-six measurement comparison; never tunes or simulates."""
import argparse
from collections import Counter
import json
from pathlib import Path

from .io_utils import write_json, write_text


def build_comparison(run, oracle_run):
    run, oracle_run = Path(run), Path(oracle_run)
    manifest=json.loads((run/'run_manifest.json').read_text())
    om=json.loads((oracle_run/'run_manifest.json').read_text())
    if manifest['status']!='complete' or manifest['days']!=500 or om['status']!='complete' or om['days']!=100 or om['oracle_rollouts']!=100:
        raise ValueError('Complete 500 measurement days and 100 oracle days x100 rollouts first')
    if manifest['config']!=om['config'] or manifest['seed']!=om['seed'] or manifest['seed']!=3003:
        raise ValueError('Measurement and oracle must use identical frozen settings and seed3003')
    config=manifest['config'];options=config['phase6_analysis'];t=options['targets']
    current=json.loads((run/'stats_report.json').read_text())
    before=json.loads((Path(options['reference_run'])/'stats_report.json').read_text())
    oracle=json.loads((oracle_run/'oracle_report.json').read_text())
    checks=[]
    def check(name,value,low=None,high=None,hard=False,knob=''):
        passed=value is not None and (low is None or value>=low) and (high is None or value<=high)
        checks.append({'name':name,'observed':value,'min':low,'max':high,'status':'PASS' if passed else 'FAIL' if hard or value is None else 'WARN',
                       'candidate_knob_if_missed':None if passed else knob})
    def ratio(a,b):return a/b if a is not None and b is not None and b!=0 else None
    diversity=current['fixed_sample_diversity']
    for kind in ('zone_entries','event_tokens'):
        if diversity[kind]['current']['fixed_samples']['500']['status']!='complete' or diversity[kind]['v5_4_0'] is None:
            raise ValueError('Missing fixed-sample diversity/reference')
    def metric(kind,version,n,name):return diversity[kind][version]['fixed_samples'][str(n)]['means'][name]
    check('zone_unique_fraction_N200_ratio',ratio(metric('zone_entries','current',200,'unique_fraction'),metric('zone_entries','v5_4_0',200,'unique_fraction')),t['zone_unique_200_ratio_min'],knob='randomness.period_prior_scale / softmax_temperature')
    check('zone_distinct_N500_ratio',ratio(metric('zone_entries','current',500,'distinct_sequences'),metric('zone_entries','v5_4_0',500,'distinct_sequences')),t['zone_distinct_500_ratio_min'],knob='day_types.rival.extra_patrol_entries_range / period prior scale')
    check('zone_top5_share_N500',metric('zone_entries','current',500,'top5_share'),high=t['zone_top5_500_max'],knob='randomness.period_prior_scale')
    check('event_unique_fraction_N200',metric('event_tokens','current',200,'unique_fraction'),t['event_unique_200_min'],knob='randomness.period_jitter_minutes / day-type diversity')
    # Oracle scopes are matched on its own 100-day baseline folds.
    oracle_head = oracle['comparisons']['headline']
    oracle_ratio=oracle_head['oracle']['mean'] / oracle_head['L0']['mean']
    check('oracle_over_L0_headline_100_days',oracle_ratio,*t['oracle_l0_range'],knob='randomness.softmax_temperature / period_prior_scale')
    head=current['baseline_ladder']['headline']
    check('L2_improvement_over_L1',(head['L1']['mean']-head['L2']['mean'])/head['L1']['mean'],t['l2_l1_improvement_min'],knob='randomness.period_prior_scale (balance with contextual signal)')
    check('L3_improvement_over_L2',(head['L2']['mean']-head['L3']['mean'])/head['L2']['mean'],t['l3_l2_improvement_min'],knob='weather heat links / day_types.prey_rich.scout_dwell_multiplier')
    check('event_invariant_failures',current['validation']['days_failed'],0,0,True,'fix event-rule defect; do not tune thresholds')
    check('hunt_cutoff_respected',int(current['validation']['days_checked']==500 and current['validation']['days_failed']==0),1,1,True,'fix hunt cutoff defect')
    check('zone_entries_per_day',current['zone_entries_per_day']['mean'],7.5,11,True,'day_types.rival.extra_patrol_entries_range')
    check('events_per_day',current['events_per_day']['mean'],t['events_per_day_min'],hard=True,knob='day_types.rival patrol dwell / entry plan')
    check('walking_hours',current['hours_per_behaviour']['walking'],high=6.5,hard=True,knob='daytime_travel_budget_minutes / rival patrol distance choices')
    check('walking_speed_kmh',current['path_statistics']['pooled_mean_walking_speed_kmh'],2,4,True,'movement.patrol_speed_kmh_range')
    check('resting_hours',current['hours_per_behaviour']['sleeping_resting'],15.5,20,True,'weather.rain wake_advance/shade_delay; rival patrol dwell')
    for name,low,high in (('any_chase',.5,.7),('catch',.2,.4),('enter_road',.1,.18),('enter_water',.65,.88)):
        check(name+'_day_fraction',current['day_fractions'][name],low,high,True,{'any_chase':'day_types.prey_rich.hunt_threshold_reduction','catch':'day_types.prey_rich.max_chase_attempts','enter_road':'weather.rain.traffic_multiplier / evening road probability','enter_water':'weather and day_types water_visit_multiplier'}[name])
    check('abandoned_trips_per_day',current['path_statistics']['aggregates']['abandoned_trip_count']['mean'],high=1.,hard=True,knob='rival patrol scheduling around committed shade/hunt windows')
    groups=current['environment_breakdowns'];w=groups['weather'];d=groups['day_type']
    for name,probability in config['weather']['probabilities'].items():
        check('weather_frequency.'+name,w[name]['fraction'],probability-t['weather_frequency_tolerance'],probability+t['weather_frequency_tolerance'],knob='weather.probabilities (sampling variability; no post-hoc adjustment)')
    def mean(group,name,key):return group[name][key]['mean']
    def difference(a,b):return a-b if a is not None and b is not None else None
    check('rain_clear_tourist_ratio',ratio(mean(w,'rain','tourist_volume'),mean(w,'clear','tourist_volume')),high=t['rain_clear_traffic_ratio_max'],knob='weather.rain.traffic_multiplier')
    for category in ('overcast','rain'):
        check('hot_shade_advance_vs_'+category,difference(mean(w,category,'shade_entry_minutes'),mean(w,'hot','shade_entry_minutes')),t['hot_shade_advance_minutes_min'],knob='shade_entry_heat_shift_minutes / weather heat ranges')
    check('rain_waterhole_day_fraction',mean(w,'rain','waterhole_day_fraction'),high=t['rain_water_max'],knob='weather.rain.water_visit_multiplier / water_goal_bonus')
    check('hot_waterhole_day_fraction',mean(w,'hot','waterhole_day_fraction'),t['hot_water_min'],knob='weather.hot.water_visit_multiplier / water_goal_bonus')
    check('prey_rich_first_chase_advance',difference(mean(d,'normal','first_chase_minutes'),mean(d,'prey_rich','first_chase_minutes')),t['prey_chase_advance_minutes_min'],knob='day_types.prey_rich.hunt_advance_minutes / first_chase_wait_multiplier')
    check('prey_rich_kopje_dwell_ratio',ratio(mean(d,'prey_rich','kopje_dwell_minutes'),mean(d,'normal','kopje_dwell_minutes')),t['prey_kopje_ratio_min'],knob='day_types.prey_rich.scout_dwell_multiplier')
    check('rival_extra_zone_entries',difference(mean(d,'rival','zone_entries_per_day'),mean(d,'normal','zone_entries_per_day')),t['rival_extra_entries_min'],knob='day_types.rival.extra_patrol_entries_range / patrol dwell')
    check('rival_waterhole_day_fraction',mean(d,'rival','waterhole_day_fraction'),high=t['rival_water_max'],knob='day_types.rival.water_visit_multiplier / water_goal_bonus')
    old_checks={c['name']:c for c in before['checks']}
    links=[c for c in current['checks'] if c['name'] in old_checks and old_checks[c['name']]['status']=='PASS' and c['status']!='PASS'
           and ('_vs_' in c['name'] or c['name'] in ('road_tourist_correlation','trip_boredom_straightness','trip_urgency_straightness','trip_urgency_speed','trip_observed_true_straightness'))]
    new_fails=[c for c in current['checks'] if c['status']=='FAIL' and old_checks.get(c['name'],{}).get('status')!='FAIL']
    check('new_hard_failures_vs_v5',len(new_fails),0,0,True,'review listed regressions; no silent retuning')
    return {'status':'complete','version':'6.0.0','seed':manifest['seed'],'days':500,'oracle_days':100,'oracle_rollouts':100,
            'run':str(run),'oracle_run':str(oracle_run),'before_run':options['reference_run'],
            'no_post_result_tuning':True,'production_defect_retries':0,
            'diversity':diversity,'breakdowns':groups,'checks':checks,'check_counts':dict(Counter(c['status'] for c in checks)),
            'prior_link_regressions':links,'new_hard_failures':new_fails,
            'correlations':{'before':before['correlations'],'current':current['correlations']},
            'headline_baselines':{'before':before['baseline_ladder']['headline'],'current':head,'L3w':current['weather_baseline']['headline']},
            'all_report_baselines':{'before':before['baseline_ladder']['all_reports'],'current':current['baseline_ladder']['all_reports'],'L3w':current['weather_baseline']['all_reports']},
            'oracle':{**oracle_head, 'oracle_over_l0':oracle_ratio}, 'oracle_all_reports':oracle['comparisons']['all_reports'], 'before_oracle_L0_approx':.249,
            'oracle_comparison_note':'Before ratio about0.249 is the historical v5.4.0 seed42 oracle, not a matched seed2026 oracle; current ratio uses 100 seed3003 days and their own L0.',
            'behaviour':{k:{'before':before[k],'current':current[k]} for k in ('events_per_day','zone_entries_per_day','hours_per_behaviour','day_fractions')},
            'settings':config}


def render(report):
    def fmt(value):return 'N/A' if value is None else f'{value:.5f}'
    lines=['# Phase 6 measurement: weather, day types and randomness','',
           'Simulator6.0.0 / lionsim-v6; seed3003; 500 days; oracle100 days x100 continuations at each of seven reports.',
           'One frozen measurement, no post-result tuning. Candidate knobs below are suggestions only, not applied changes.',
           '',f'Checks: {report["check_counts"]}.','',
           '| Target | Observed | Min | Max | Status |','|---|---:|---:|---:|---|']
    lines += [f'| {c["name"]} | {fmt(c["observed"])} | {fmt(c["min"])} | {fmt(c["max"])} | {c["status"]} |' for c in report['checks']]
    lines += ['','## Missed targets and candidate knobs','']
    lines += [f'- **{c["status"]}: {c["name"]} = {fmt(c["observed"])}**, expected [{c["min"]}, {c["max"]}]. Candidate: {c["candidate_knob_if_missed"]}.' for c in report['checks'] if c['status']!='PASS']
    lines += ['','## Baseline losses (five day folds; lower is better)','', '| Model | Before headline | Current headline | Before all | Current all |','|---|---:|---:|---:|---:|']
    for name in ('L0','L1','L2','L3'):
        values=[report[scope][version][name]['mean'] for scope,version in (('headline_baselines','before'),('headline_baselines','current'),('all_report_baselines','before'),('all_report_baselines','current'))]
        lines.append('| '+name+' | '+' | '.join(fmt(v) for v in values)+' |')
    lines += [f'| L3w | — | {fmt(report["headline_baselines"]["L3w"]["mean"])} | — | {fmt(report["all_report_baselines"]["L3w"]["mean"])} |','',
              f'Oracle/L0 headline: before ~0.249; current {fmt(report["oracle"]["oracle_over_l0"])}.',report['oracle_comparison_note'],'',
              '## Prior correlation regressions','',json.dumps(report['prior_link_regressions'],indent=2),
              '', 'New hard failures versus the old check table: '+json.dumps(report['new_hard_failures']), '']
    from .phase6_statistics import render_phase6_statistics
    lines.append(render_phase6_statistics({'fixed_sample_diversity':report['diversity'],'environment_breakdowns':report['breakdowns']}))
    lines += ['## Behaviour before/current','', '| Metric | v5.4.0 | v6.0.0 |','|---|---:|---:|']
    for name in ('events_per_day','zone_entries_per_day'):
        lines.append(f'| {name} | {fmt(report["behaviour"][name]["before"]["mean"])} | {fmt(report["behaviour"][name]["current"]["mean"])} |')
    for name in ('walking','sleeping_resting'):
        lines.append(f'| {name} hours | {fmt(report["behaviour"]["hours_per_behaviour"]["before"][name])} | {fmt(report["behaviour"]["hours_per_behaviour"]["current"][name])} |')
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run');parser.add_argument('--oracle-run',required=True)
    args=parser.parse_args(argv);report=build_comparison(args.run,args.oracle_run)
    write_json(Path(args.run)/'phase6_report.json',report)
    write_text(Path(args.run)/'phase6_report.md',render(report))
    print(report['check_counts'])


if __name__=='__main__':main()
