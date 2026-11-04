"""Guarded generation and whitelist-only export/verification for a frozen simulator."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

TOOL_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {42, 137, 271, 2026, 3003, 9999}
HIDDEN = {'day_type', 'heat', 'heat_true', 'ambient_temp_c_true', 'true_goal',
          'x_true_km', 'y_true_km', 'ground_truth_latents'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(value, handle, indent=2, allow_nan=False)
            handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def clean_tree(repo):
    if git(repo, 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError(f'Dirty tree: {repo}; commit or preserve changes before generation')


def source_guard(repo, plan):
    clean_tree(repo)
    tag = git(repo, 'rev-parse', plan['frozen_tag'] + '^{commit}')
    if tag != plan['frozen_commit'] or git(repo, 'rev-parse', 'HEAD') != tag:
        raise ValueError('Tag mismatch: simulator HEAD must equal the pinned frozen tag commit')
    if digest((Path(repo) / 'default_config.json').read_bytes()) != plan['default_config_sha256']:
        raise ValueError('Config hash mismatch: default_config.json')
    env = {**os.environ, 'PYTHONPATH': str(Path(repo).resolve())}
    code = ('import json,lionsim; from lionsim.config import load_config; '
            'print(json.dumps({"version":lionsim.__version__,"schema":lionsim.SCHEMA_VERSION,"config":load_config().to_dict()}))')
    state = json.loads(subprocess.check_output([sys.executable, '-c', code], cwd=repo, env=env, text=True))
    if state['version'] != plan['simulator_version'] or state['schema'] != plan['schema_version']:
        raise ValueError('Simulator version/schema mismatch')
    if digest(canonical(state['config'])) != plan['effective_config_sha256']:
        raise ValueError('Config hash mismatch: effective settings')
    if state['config']['output']['embed_cumulative_path_in_reports'] or plan['embed_cumulative_path_in_reports']:
        raise ValueError('Cumulative paths must be disabled')
    return state['config']


def resolve_plan(plan, role, days=None):
    if set(plan['forbidden_seeds']) != FORBIDDEN or plan['chunk_size'] != 200:
        raise ValueError('Forbidden seeds/chunk size differ from the release policy')
    if plan['main']['split_fractions'] != {'train': .7, 'validation': .15, 'test': .15}:
        raise ValueError('Expected the declared 70/15/15 split')
    selected = plan[role]
    seed = selected['seed']
    expected = {'main': 7001, 'robustness': 8002, 'smoke': 9999}[role]
    if seed != expected or role != 'smoke' and seed in FORBIDDEN:
        raise ValueError('Forbidden or incorrect seed for this role')
    if role == 'main':
        if days is None:
            days = selected['days']
        if selected['days'] is not None and days != selected['days']:
            raise ValueError('Main N differs from the committed plan')
    else:
        if days is not None and days != selected['days']:
            raise ValueError('Cannot change smoke/robustness day counts')
        days = selected['days']
        if days != {'smoke': 20, 'robustness': 300}[role]:
            raise ValueError('Incorrect fixed day count')
    if isinstance(days, bool) or not isinstance(days, int) or days < 7:
        raise ValueError('Main N must be explicitly supplied, integer and large enough for nonempty splits')
    if role == 'robustness':
        splits = {'robustness_test': [1, days]}
    else:
        train, validation = 70 * days // 100, 15 * days // 100
        splits = {'train': [1, train], 'validation': [train + 1, train + validation],
                  'test': [train + validation + 1, days]}
    return {'role': role, 'seed': seed, 'days': days, 'splits': splits,
            'smoke_only': role == 'smoke', 'frozen_tag': plan['frozen_tag'], 'frozen_commit': plan['frozen_commit'],
            'effective_config_sha256': plan['effective_config_sha256'], 'plan_sha256': digest(canonical(plan)),
            'chunk_size': plan['chunk_size'], 'start_date': plan['start_date'],
            'embed_cumulative_path_in_reports': False}


def split_for(day, resolved):
    matches = [name for name, (first, last) in resolved['splits'].items() if first <= day <= last]
    if len(matches) != 1:
        raise ValueError(f'Day {day} has no unique split')
    return matches[0]


def schema_columns(schema):
    columns = schema['columns']
    grouped = schema['identifiers'] + schema['labels'] + sum(schema['feature_groups'].values(), [])
    if columns != grouped or len(set(columns)) != len(columns) or HIDDEN.intersection(columns):
        raise ValueError('Unsafe or inconsistent export column whitelist')
    if not {'weather', 'ambient_temp_c'} <= set(schema['feature_groups']['context']):
        raise ValueError('Weather and ambient_temp_c must be context features')
    if schema['labels'] != ['next_zone_target']:
        raise ValueError('Unexpected label columns')
    return columns


def run_path(output):
    runs = sorted((Path(output) / 'raw').glob('run_*'))
    if len(runs) != 1:
        raise ValueError('Expected exactly one raw simulation run')
    return runs[0]


def generate(repo, output, plan, schema, role, days=None, allow_generation=False):
    if role != 'smoke' and not allow_generation:
        raise ValueError('Full generation is not authorized by default; requires an explicit --allow-generation')
    repo, output = Path(repo).resolve(), Path(output).resolve()
    clean_tree(TOOL_ROOT)
    source_guard(repo, plan)
    schema_columns(schema)
    resolved = resolve_plan(plan, role, days)
    resolved.update(export_schema_sha256=digest(canonical(schema)), tooling_commit=git(TOOL_ROOT, 'rev-parse', 'HEAD'))
    marker = output / 'resolved_plan.json'
    if marker.exists():
        if read(marker) != resolved:
            raise ValueError('Resolved plan mismatch; cannot change an existing dataset run')
    else:
        if output.exists() and any(output.iterdir()):
            raise ValueError('Output directory is not empty and has no resolved plan')
        write(marker, resolved)  # Exact N/splits published BEFORE the first simulation.
    env = {**os.environ, 'PYTHONPATH': str(repo)}
    while True:
        clean_tree(TOOL_ROOT); source_guard(repo, plan)
        existing = sorted((output / 'raw').glob('run_*'))
        command = [sys.executable, '-m', 'lionsim.run', '--workers', str(plan['workers']),
                   '--chunk-size', str(plan['chunk_size'])]
        if existing:
            run = run_path(output)
            manifest = read(run / 'run_manifest.json')
            if (manifest['seed'] != resolved['seed'] or manifest['days'] != resolved['days']
                    or digest(canonical(manifest['config'])) != resolved['effective_config_sha256']):
                raise ValueError('Existing raw run provenance/config mismatch')
            if manifest['status'] == 'complete':
                break
            command += ['--resume', str(run)]
        else:
            command += ['--stats-only', '--stats-days', str(resolved['days']), '--seed', str(resolved['seed']),
                        '--keep-files', '--no-images', '--start-date', resolved['start_date'], '--out', str(output / 'raw')]
        subprocess.run(command, cwd=repo, env=env, check=True)
    print(f'Generated {resolved["role"]}: {resolved["days"]} days; {run}', flush=True)
    return run


def source_rows(output, schema):
    output = Path(output); resolved = read(output / 'resolved_plan.json')
    columns = schema_columns(schema)
    if resolved['export_schema_sha256'] != digest(canonical(schema)):
        raise ValueError('Export schema hash mismatch')
    run = run_path(output); manifest = read(run / 'run_manifest.json')
    if manifest['status'] != 'complete' or manifest['completed_days'] != resolved['days']:
        raise ValueError('Simulation is incomplete')
    if (manifest['seed'] != resolved['seed'] or manifest['days'] != resolved['days']
            or digest(canonical(manifest['config'])) != resolved['effective_config_sha256']
            or manifest['schema_version'] != 'lionsim-v6' or manifest['versions']['lionsim'] != '6.0.0'
            or manifest['config']['output']['embed_cumulative_path_in_reports'] or manifest['image_days'] != 0):
        raise ValueError('Raw run provenance/config mismatch')
    if not read(run / 'validation_report.json')['valid']:
        raise ValueError('Raw event validation failed')
    with (run / 'targets.csv').open(newline='') as handle:
        reader = csv.DictReader(handle)
        if not set(columns) <= set(reader.fieldnames or []):
            raise ValueError('Required observable columns are missing')
        rows = [{name: row[name] for name in columns} for row in reader]
    expected = {(d, r) for d in range(1, resolved['days'] + 1) for r in range(1, 8)}
    keys = [(int(r['day']), int(r['report_index'])) for r in rows]
    if len(keys) != len(expected) or set(keys) != expected:
        raise ValueError('Missing or duplicated day/report rows')
    return resolved, columns, rows


def export_dataset(output, schema):
    output = Path(output); resolved, columns, rows = source_rows(output, schema)
    directory = output / 'export'; directory.mkdir(parents=True, exist_ok=True)
    files = {}
    for name in resolved['splits']:
        selected = [r for r in rows if split_for(int(r['day']), resolved) == name]
        path = directory / f'{name}.csv'
        with tempfile.NamedTemporaryFile(mode='w', dir=directory, prefix='.', newline='', delete=False) as handle:
            temporary = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=columns); writer.writeheader(); writer.writerows(selected)
        os.replace(temporary, path)
        files[path.name] = {'rows': len(selected), 'sha256': digest(path.read_bytes())}
    write(directory / 'export_manifest.json', {'schema_version': schema['schema_version'], 'seed': resolved['seed'],
        'smoke_only': resolved['smoke_only'], 'resolved_plan_sha256': digest(canonical(resolved)),
        'export_schema_sha256': digest(canonical(schema)), 'files': files})
    return verify(output, schema)


def verify(output, schema):
    output = Path(output); resolved, columns, source = source_rows(output, schema)
    directory = output / 'export'; manifest = read(directory / 'export_manifest.json')
    names = {name + '.csv' for name in resolved['splits']}
    if set(p.name for p in directory.iterdir()) != names | {'export_manifest.json'} or set(manifest['files']) != names:
        raise ValueError('Unexpected or missing export files')
    if (manifest['resolved_plan_sha256'] != digest(canonical(resolved))
            or manifest['export_schema_sha256'] != digest(canonical(schema))
            or manifest['seed'] != resolved['seed'] or manifest['smoke_only'] != resolved['smoke_only']):
        raise ValueError('Export provenance mismatch')
    counts = {}
    for name in resolved['splits']:
        path = directory / (name + '.csv')
        with path.open(newline='') as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != columns or HIDDEN.intersection(reader.fieldnames):
                raise ValueError('Forbidden or unexpected export columns')
            actual = list(reader)
        expected = [r for r in source if split_for(int(r['day']), resolved) == name]
        if actual != expected or manifest['files'][path.name] != {'rows': len(actual), 'sha256': digest(path.read_bytes())}:
            raise ValueError('Export differs from source rows, split assignment or saved checksum')
        counts[name] = {'days': resolved['splits'][name][1] - resolved['splits'][name][0] + 1, 'rows': len(actual)}
    result = {'status': 'PASS', 'seed': resolved['seed'], 'smoke_only': resolved['smoke_only'],
              'days': resolved['days'], 'rows': len(source), 'splits': counts,
              'columns': len(columns), 'weather_context': True, 'hidden_columns_exported': False,
              'day_disjoint': True, 'source_rows_equal': True, 'checksums_valid': True}
    write(output / 'verification_report.json', result)
    print(json.dumps(result), flush=True)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('generate', 'export', 'verify'))
    parser.add_argument('--repo', type=Path, default=TOOL_ROOT)
    parser.add_argument('--plan', type=Path, default=TOOL_ROOT / 'dataset_plan.json')
    parser.add_argument('--schema', type=Path, default=TOOL_ROOT / 'export_columns.json')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--role', choices=('main', 'robustness', 'smoke'), default='smoke')
    parser.add_argument('--days', type=int)
    parser.add_argument('--allow-generation', action='store_true', help='explicitly authorize main/robustness generation; never implicit')
    args = parser.parse_args(argv); schema = read(args.schema)
    try:
        if args.action == 'generate':
            generate(args.repo, args.out, read(args.plan), schema, args.role, args.days, args.allow_generation)
        elif args.action == 'export': export_dataset(args.out, schema)
        else: verify(args.out, schema)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(2, f'ERROR: {error}\n')


if __name__ == '__main__':
    main()
