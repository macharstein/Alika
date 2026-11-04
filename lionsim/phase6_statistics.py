"""Fixed-sample diversity, environment summaries and observable weather baseline."""
from collections import Counter
from functools import lru_cache
import json
import math
from pathlib import Path

import numpy as np


def sequence_metrics(sequences):
    counts = Counter(map(tuple, sequences)); n = sum(counts.values())
    if not n:
        return dict.fromkeys(('unique_fraction','distinct_sequences','top5_share','normalised_entropy'))
    entropy = -sum((v/n)*math.log(v/n) for v in counts.values())
    return {'unique_fraction':len(counts)/n, 'distinct_sequences':len(counts),
            'top5_share':sum(sorted(counts.values(),reverse=True)[:5])/n,
            'normalised_entropy':entropy/math.log(len(counts)) if len(counts)>1 else 0.}


def fixed_diversity(sequences, options):
    result = {'days':len(sequences), 'all_available':sequence_metrics(sequences), 'fixed_samples':{}}
    for size in options['sample_sizes']:
        if len(sequences)<size:
            result['fixed_samples'][str(size)]={'status':'insufficient_days','sample_size':size,'means':sequence_metrics([])}
            continue
        rng=np.random.default_rng(np.random.SeedSequence([options['subset_seed'], size]))
        samples=[sequence_metrics([sequences[i] for i in rng.choice(len(sequences),size,replace=False)])
                 for _ in range(options['subset_repeats'])]
        result['fixed_samples'][str(size)]={'status':'complete','sample_size':size,'repeats':len(samples),
            'means':{key:float(np.mean([s[key] for s in samples])) for key in samples[0]},
            'std':{key:float(np.std([s[key] for s in samples])) for key in samples[0]}}
    return result


@lru_cache(maxsize=4)
def reference_sequences(path):
    directory=Path(path)
    if not (directory/'run_manifest.json').exists():
        return None
    manifest=json.loads((directory/'run_manifest.json').read_text())
    if manifest['versions']['lionsim']!='5.4.0' or manifest['seed']!=2026 or manifest['completed_days']!=500:
        raise ValueError('Diversity reference must be the completed 500-day v5.4.0 seed2026 run')
    zones=[]; events=[]
    for index in manifest['day_indices']:
        day=json.loads((directory/'days'/f'day_{index:04d}'/'day.json').read_text())
        tokens=tuple(e['token'] for e in day['events'])
        events.append(tokens);zones.append(tuple(t for t in tokens if t.startswith('ENTER_')))
    return tuple(zones),tuple(events)


def diversity_comparison(days, config):
    options=config['phase6_analysis']
    saved=reference_sequences(str(Path(options['reference_run']).resolve()))
    result={'reference_run':options['reference_run'], 'reference_status':'available' if saved else 'missing',
            'definition':'20 seeded subsets without replacement at fixed N; entropy divided by log(distinct sequences). Missing N is not replaced by a smaller sample.'}
    for i,(name,key) in enumerate((('zone_entries','zone_sequence'),('event_tokens','event_sequence'))):
        sequences=[d[key] for d in days if key in d]
        result[name]={'current':fixed_diversity(sequences,options),
                      'v5_4_0':fixed_diversity(saved[i],options) if saved else None}
    return result


def environment_breakdowns(days):
    def mean(values):
        values=[v for v in values if v is not None]
        return {'mean':float(np.mean(values)) if values else None,'count':len(values)}
    result={}
    for key,names in (('weather',('clear','hot','overcast','rain')),('day_type',('normal','prey_rich','rival'))):
        result[key]={}
        for name in names:
            selected=[d for d in days if d.get(key)==name]
            result[key][name]={'count':len(selected),'fraction':len(selected)/len(days) if days else None,
                'shade_entry_minutes':mean([d['time_traces_minutes_after_start']['shade_entry_time'] for d in selected]),
                'waterhole_day_fraction':mean([int(d['day_flags']['enter_water']) for d in selected]),
                'tourist_volume':mean([d['traffic_count'] for d in selected]),
                'ambient_temp_c':mean([d.get('ambient_temp_c_mean') for d in selected]),
                'first_chase_minutes':mean([d['time_traces_minutes_after_start']['first_chase_time'] for d in selected]),
                'kopje_dwell_minutes':mean([d['kopje_dwell_minutes'] for d in selected]),
                'zone_entries_per_day':mean([d['zone_entry_count'] for d in selected])}
    return result


def weather_bin(value):
    if value=='hot': return 'hot'
    if value in ('clear','overcast'): return 'clear/overcast'
    if value=='rain': return 'rain'
    raise ValueError('Missing or invalid observable weather')


def weather_baseline(rows, ladder, config):
    from .l5_counts import fit_l3, predict_l3, l3_keys
    from .reports import TARGET_CLASSES
    if ladder['status']!='complete': return {'status':'insufficient_data'}
    folds=[]
    k=config['phase6_analysis']['l3w_interpolation_k']
    headline=set(config['learnability']['headline_reports'])
    for fold in ladder['folds']:
        training=[r for r in rows if int(r['day']) in set(fold['train_days'])]
        testing=[r for r in rows if int(r['day']) in set(fold['test_days'])]
        tables=fit_l3(training,config); weather_counts={}
        def key(row): return l3_keys(row,config)[-1]+(weather_bin(row['weather']),)
        for row in training: weather_counts.setdefault(key(row),Counter())[row['next_zone_target']]+=1
        predictions=[]
        for row in testing:
            prior=predict_l3(row,tables,config);counts=weather_counts.get(key(row),Counter())
            p=(np.array([counts[c] for c in TARGET_CLASSES])+k*prior)/(sum(counts.values())+k)
            predictions.append((int(row['report_index']),-math.log(p[TARGET_CLASSES.index(row['next_zone_target'])])))
        mean=lambda values: float(np.mean(values)) if values else None
        folds.append({'fold':fold['fold'],'train_days':fold['train_days'],'test_days':fold['test_days'],
                      'headline':mean([loss for index,loss in predictions if index in headline]),
                      'all_reports':mean([loss for _,loss in predictions]),
                      'by_report_index':{str(index):mean([loss for i,loss in predictions if i==index]) for index in range(1,8)}})
    def summary(values):
        values=[v for v in values if v is not None]
        return {'mean':float(np.mean(values)) if values else None,'std':float(np.std(values)) if values else None}
    return {'status':'complete','interpolation_k':k,'weather_bins':['hot','clear/overcast','rain'],
            'definition':'Full L3 cell plus observable weather bin; (training counts+k*p_L3)/(n+k). Same day folds; no day_type input.',
            'headline':summary([f['headline'] for f in folds]),'all_reports':summary([f['all_reports'] for f in folds]),
            'by_report_index':{str(i):summary([f['by_report_index'][str(i)] for f in folds]) for i in range(1,8)},'folds':folds}


def render_phase6_statistics(report):
    def fmt(v): return 'N/A' if v is None else f'{v:.4f}'
    lines=['','## Fixed-sample sequence diversity','', '| Sequence | N | Metric | v5.4.0 | Current |','|---|---:|---|---:|---:|']
    for name in ('zone_entries','event_tokens'):
        item=report['fixed_sample_diversity'][name]
        for size,current in item['current']['fixed_samples'].items():
            old=item['v5_4_0']['fixed_samples'][size] if item['v5_4_0'] else None
            for metric,value in current['means'].items():
                lines.append(f'| {name} | {size} | {metric} | {fmt(old["means"][metric] if old else None)} | {fmt(value)} |')
    lines += ['',report['fixed_sample_diversity']['definition'],'','## Weather and hidden day-type breakdowns','',
              'Times below are minutes after day start; hidden day types are analysis only. Counts accompany every mean in JSON.','']
    for name,groups in report['environment_breakdowns'].items():
        metrics=('shade_entry_minutes','waterhole_day_fraction','tourist_volume','ambient_temp_c') if name=='weather' else ('first_chase_minutes','kopje_dwell_minutes','zone_entries_per_day','waterhole_day_fraction')
        lines += [f'| {name} | Days | Fraction | '+' | '.join(metrics)+' |', '|---|---:|---:|'+'---:|'*len(metrics)]
        for category,item in groups.items():
            lines.append(f'| {category} | {item["count"]} | {fmt(item["fraction"])} | '+' | '.join(fmt(item[m]['mean']) for m in metrics)+' |')
        lines += ['']
    weather=report.get('weather_baseline',{})
    if weather.get('status')=='complete':
        lines += ['## L3w weather baseline','',weather['definition'],'',
                  '| Scope | L3 | L3w |','|---|---:|---:|']
        for scope in ('headline','all_reports'):
            lines.append(f'| {scope} | {fmt(report["baseline_ladder"][scope]["L3"]["mean"])} | {fmt(weather[scope]["mean"])} |')
    return '\n'.join(lines)+'\n'
