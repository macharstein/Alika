"""Run the preregistered L5 experiment on saved minute tables (analysis only)."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import Config
from .features_heading import HEADING_COLUMNS, HEADING_EXPORT_VERSION, heading_at_report
from .io_utils import write_json, write_text
from .l5_counts import MODELS, evaluate, summarize, decision, moving_flag
from .l5_truegoal import true_goal_at_report


def read_table(directory, name):
    parquet = directory / f'{name}.parquet'
    if parquet.exists():
        return pd.read_parquet(parquet)
    return pd.read_csv(directory / f'{name}.csv.gz', float_precision='round_trip')


def goal_accuracy(rows, headline):
    def scope(selected):
        moving = [r for r in selected if moving_flag(r)]
        correct = sum(r['implied_goal'] == r['true_goal'] for r in moving)
        implied = sorted({r['implied_goal'] for r in moving})
        truth = sorted({r['true_goal'] for r in moving})
        counts = Counter((r['implied_goal'], r['true_goal']) for r in moving)
        return {'moving_count': len(moving), 'correct': correct,
                'accuracy': correct / len(moving) if moving else None,
                'confusion': {'rows_implied_goal': implied, 'columns_true_goal': truth,
                              'counts': [[counts[a, b] for b in truth] for a in implied]}}
    return {'all_reports': scope(rows), 'headline': scope([r for r in rows if int(r['report_index']) in headline])}


def assert_export(row, computed):
    for key in HEADING_COLUMNS:
        saved, value = row[key], computed[key]
        if value is None:
            valid = saved == ''
        elif isinstance(value, bool):
            valid = saved == str(value)
        elif isinstance(value, (float, int)):
            valid = np.isclose(float(saved), value, rtol=1e-10, atol=1e-12)
        else:
            valid = saved == value
        if not valid:
            raise ValueError(f'Saved heading does not match observed GPS: day {row["day"]} report {row["report_index"]} {key}')


def analyze(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'run_manifest.json').read_text())
    if manifest['status'] != 'complete' or manifest['completed_days'] != manifest['days']:
        raise ValueError('Finish all resumable simulation chunks before analyzing; no partial-result tuning')
    if manifest.get('heading_export_version') != HEADING_EXPORT_VERSION or not manifest['keep_files']:
        raise ValueError('L5 needs heading-v1 exports and saved minute tables (--keep-files)')
    config = Config(manifest['config'])
    with (directory / 'targets.csv').open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    expected = {(d, r) for d in manifest['day_indices'] for r in range(1, len(config['time']['report_times']))}
    actual = {(int(r['day']), int(r['report_index'])) for r in rows}
    if actual != expected or len(rows) != len(expected):
        raise ValueError('Incomplete or duplicate targets')
    ladder = json.loads((directory / 'stats_report.json').read_text())['baseline_ladder']
    folds = [{'fold': f['fold'], 'train_days': f['train_days'], 'test_days': f['test_days']} for f in ladder['folds']]
    headline = config['learnability']['headline_reports']
    windows = sorted({10, 20, 30, config['heading_features']['window_minutes']})
    variants = {w: [] for w in windows}
    hashes = {}
    width = max(4, len(str(max(manifest['day_indices']))))
    # Incremental day caches make interrupted feature analysis resumable. Content
    # hashes invalidate only affected days; CV/report always rebuild atomically.
    cache_dir = directory / 'l5_analysis_checkpoints'
    settings = {'heading': config['heading_features'], 'smoothing': config['features_path']['smoothing_minutes'],
                'map': config['map'], 'windows': windows, 'version': HEADING_EXPORT_VERSION}
    for day in manifest['day_indices']:
        day_dir = directory / 'days' / f'day_{day:0{width}d}'
        selected = [r for r in rows if int(r['day']) == day]
        files = [day_dir / 'day.json'] + [next(iter(sorted(day_dir.glob(f'{name}.*'))), day_dir / name)
                                         for name in ('gps', 'hidden_state')]
        digest = hashlib.sha256(json.dumps([settings, selected], sort_keys=True).encode())
        for path in files:
            file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            hashes[str(path.relative_to(directory))] = file_hash
            digest.update(file_hash.encode())
        fingerprint = digest.hexdigest()
        cache = cache_dir / f'day_{day:0{width}d}.json'
        cached = None
        if cache.exists():
            try:
                candidate = json.loads(cache.read_text())
                if candidate['fingerprint'] == fingerprint and all(len(candidate['windows'][str(w)]) == len(selected) for w in windows):
                    cached = candidate['windows']
            except (ValueError, KeyError, TypeError):
                pass
        if cached is None:
            gps, hidden = read_table(day_dir, 'gps'), read_table(day_dir, 'hidden_state')
            day_json = json.loads(files[0].read_text())
            reports = {r['report_index']: r['report_time'] for r in day_json['reports']}
            cached = {str(w): [] for w in windows}
            for row in selected:
                timestamp = reports[int(row['report_index'])]
                truth = true_goal_at_report(hidden, timestamp, config['map']['zones'])
                for w in windows:
                    features = heading_at_report(gps, timestamp, config, w)
                    if w == config['heading_features']['window_minutes']:
                        assert_export(row, features)
                    cached[str(w)].append({**row, **features, 'true_goal': truth})
            write_json(cache, {'fingerprint': fingerprint, 'analysis_only_LEAKY': True, 'windows': cached}, pretty=False)
        for w in windows:
            variants[w].extend(cached[str(w)])
        if day % 100 == 0:
            print(f'L5 analysis checkpointed {day} days', flush=True)
    main_rows = variants[config['heading_features']['window_minutes']]
    predictions = evaluate(main_rows, folds, config)
    result = summarize(predictions, headline)
    # Detect L3 drift rather than silently changing any existing statistic.
    for name in ('all_reports', 'headline'):
        if not np.isclose(result[name]['losses']['L3']['mean'], ladder[name]['L3']['mean'], rtol=0, atol=1e-12):
            raise ValueError('L3 no longer matches the existing baseline ladder')
    result.update(status='complete', analysis_version='l5-v1', simulator_version=manifest['versions']['lionsim'],
                  schema_version=manifest['schema_version'], seed=manifest['seed'], days=manifest['days'],
                  heading_features=config['heading_features'], l5_analysis=config['l5_analysis'],
                  smoothing_minutes=config['features_path']['smoothing_minutes'],
                  units='Natural-log multiclass log loss; mean and population SD across five held-out day folds.',
                  classes=ladder['classes'], headline_reports=headline, folds=folds,
                  model_labels={m: ('LEAKY analysis-only current hidden goal; empirical upper-bound control' if m == 'L5_truegoal' else m) for m in MODELS},
                  cell=['report_index', 'implied_goal', 'moving'],
                  decision=decision(result['headline']['losses']),
                  goal_inference=goal_accuracy(main_rows, headline),
                  provenance={'run_fingerprint': manifest['run_fingerprint'], 'minute_file_sha256': hashes,
                              'targets_sha256': hashlib.sha256((directory / 'targets.csv').read_bytes()).hexdigest(),
                              'stats_sha256': hashlib.sha256((directory / 'stats_report.json').read_bytes()).hexdigest()},
                  methodology={'true_goal': 'Exact hidden goal at the report minute, not trip_goal. LEAKY; never exported in targets.',
                               'shuffle': 'Fixed SeedSequence(seed, fold, split, report); goals permuted separately within training/test report groups; moving flags unchanged.',
                               'counts': 'Training days only; L5=(cell counts+k*p_L3)/(n+k). L3 Laplace smoothing unchanged. Heading cuts fixed before evaluation.',
                               'gap': 'Raw gap fraction, unclipped; undefined if truegoal does not beat L3.',
                               'selection': 'Declared defaults only; sensitivity is post hoc and never selects the main model.'})
    result['fold_losses'] = [{'fold': f['fold'], **summarize([p for p in predictions if p['fold'] == f['fold']], headline)} for f in folds]
    result['sensitivity_post_hoc'] = [{'window_minutes': w,
        **summarize(evaluate(variants[w], folds, config), headline)} for w in (10, 20, 30)]
    write_json(directory / 'l5_report.json', result)
    write_text(directory / 'l5_report.md', render_markdown(result))
    return result


def render_markdown(report):
    def number(value):
        return 'N/A' if value is None else f'{value:.6f}'
    def percent(value):
        return 'N/A' if value is None else f'{value:.2%}'
    def table(scope):
        return ['| Model | CV mean log loss | Fold SD |', '|---|---:|---:|'] + [
            f'| {name + (" (LEAKY)" if name == "L5_truegoal" else "")} | {number(scope["losses"][name]["mean"])} | {number(scope["losses"][name]["std"])} |' for name in MODELS]
    result = report['decision']
    lines = ['# L5 observed-heading experiment', '',
             f'Simulator {report["simulator_version"]}; schema {report["schema_version"]}; seed {report["seed"]}; {report["days"]} days.',
             report['units'], '', f'**{result["verdict"]}**', '', result['rule'],
             f'Headline improvement over L3: **{percent(result["relative_improvement_over_L3"])}**; over L5_shuffled: **{percent(result["relative_improvement_over_L5_shuffled"])}**.',
             result['gap_sentence'], '',
             f'Declared heading settings: {json.dumps(report["heading_features"])}; trailing smoothing {report["smoothing_minutes"]} minutes; L5 settings {json.dumps(report["l5_analysis"])}.',
             'Speed_recent is displacement/window in km/min. Distance bins use zone centres: <=1.5 km and >1.5 km. The L5 cell uses report index, implied goal and moving flag only.',
             'LEAKY L5_truegoal uses hidden current goals solely as an analysis control; finite-sample counting losses need not improve on L3.', '', '## Headline reports 1–5', ''] + table(report['headline'])
    lines += ['', '## All reports', ''] + table(report['all_reports'])
    lines += ['', '## Per report index', '', '| Report | L3 | L5 | Shuffled | Truegoal (LEAKY) |', '|---|---:|---:|---:|---:|']
    for index, item in report['by_report_index'].items():
        lines.append('| ' + index + ' | ' + ' | '.join(number(item['losses'][m]['mean']) for m in MODELS) + ' |')
    for subset, scopes in report['subsets'].items():
        lines += ['', f'## {subset.title()} subsets', '']
        for name in ('headline', 'all_reports'):
            item = scopes[name]
            lines += [f'{name}: {item["count"]} examples ({percent(item["fraction"])} of this scope).', ''] + table(item) + ['']
        lines += ['| Report | Count | Fraction | L3 | L5 | Shuffled | Truegoal (LEAKY) |', '|---|---:|---:|---:|---:|---:|---:|']
        for index, item in scopes['by_report_index'].items():
            lines.append(f'| {index} | {item["count"]} | {percent(item["fraction"])} | ' + ' | '.join(number(item['losses'][m]['mean']) for m in MODELS) + ' |')
    lines += ['', '## Moving goal inference', '']
    for name, item in report['goal_inference'].items():
        lines += [f'{name}: {item["correct"]}/{item["moving_count"]} correct ({percent(item["accuracy"])}).', '']
        matrix = item['confusion']
        lines += ['| Implied \\ True | ' + ' | '.join(matrix['columns_true_goal']) + ' |',
                  '|---|' + '---:|' * len(matrix['columns_true_goal'])]
        lines += ['| ' + label + ' | ' + ' | '.join(map(str, counts)) + ' |' for label, counts in zip(matrix['rows_implied_goal'], matrix['counts'])]
        lines += ['']
    lines += ['## Window sensitivity — post hoc', '', '| Window (min) | Headline L5 | All-reports L5 |', '|---|---:|---:|']
    lines += [f'| {item["window_minutes"]} | {number(item["headline"]["losses"]["L5"]["mean"])} | {number(item["all_reports"]["losses"]["L5"]["mean"])} |' for item in report['sensitivity_post_hoc']]
    lines += ['', '## Method and reproducibility', ''] + list(report['methodology'].values())
    lines += ['', 'Day-disjoint folds exactly match L0–L4 in stats_report.json. Training/test day lists, fold losses, input hashes and post hoc details are in l5_report.json.', '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    args = parser.parse_args(argv)
    report = analyze(args.run_directory)
    print(report['decision']['verdict'])
    print(args.run_directory / 'l5_report.md')


if __name__ == '__main__':
    main()
