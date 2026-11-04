"""Frozen source guards, split contracts and hidden-column exclusion."""
from copy import deepcopy
import csv
import json
from pathlib import Path
import subprocess

import pytest

from tools import dataset as ds

ROOT = Path(__file__).parents[1]


def template():
    return ds.read(ROOT / 'dataset_plan.json')


def schema():
    return ds.read(ROOT / 'export_columns.json')


def test_plan_seeds_days_and_exact_day_splits():
    plan = template()
    assert plan['main']['days'] is None
    with pytest.raises(ValueError, match='explicitly supplied'):
        ds.resolve_plan(plan, 'main')
    main = ds.resolve_plan(plan, 'main', 1000)
    assert main['seed'] == 7001 and main['splits'] == {'train':[1,700], 'validation':[701,850], 'test':[851,1000]}
    assert ds.resolve_plan(plan, 'robustness')['splits'] == {'robustness_test':[1,300]}
    assert ds.resolve_plan(plan, 'robustness')['seed'] == 8002
    smoke = ds.resolve_plan(plan, 'smoke')
    assert smoke['days'] == 20 and smoke['seed'] == 9999 and smoke['smoke_only']
    assert smoke['splits'] == {'train':[1,14], 'validation':[15,17], 'test':[18,20]}
    assert not main['embed_cumulative_path_in_reports'] and main['chunk_size'] == 200
    odd = ds.resolve_plan(plan, 'main', 101)
    assert [ds.split_for(i, odd) for i in range(1,102)].count('train') == 70
    assert [ds.split_for(i, odd) for i in range(1,102)].count('validation') == 15
    assert [ds.split_for(i, odd) for i in range(1,102)].count('test') == 16


@pytest.mark.parametrize('seed', [42,137,271,2026,3003,9999])
def test_forbidden_seeds_cannot_be_main_or_robustness(seed):
    for role in ('main','robustness'):
        plan = template(); plan[role]['seed'] = seed
        with pytest.raises(ValueError, match='seed'):
            ds.resolve_plan(plan, role, 1000 if role == 'main' else None)


def test_smoke_exception_cannot_change_size_or_seed():
    with pytest.raises(ValueError): ds.resolve_plan(template(), 'smoke', 500)
    plan = template(); plan['smoke']['seed'] = 7001
    with pytest.raises(ValueError): ds.resolve_plan(plan, 'smoke')


@pytest.fixture
def frozen_repo(tmp_path):
    repo = tmp_path / 'repo'; repo.mkdir()
    cfg = {'output':{'embed_cumulative_path_in_reports':False}}
    (repo/'default_config.json').write_text(json.dumps(cfg))
    (repo/'.gitignore').write_text('__pycache__/\n')
    (repo/'lionsim').mkdir()
    (repo/'lionsim/__init__.py').write_text('__version__="6.0.0"\nSCHEMA_VERSION="lionsim-v6"\n')
    (repo/'lionsim/config.py').write_text('import json\nfrom pathlib import Path\nclass Config:\n def to_dict(self): return json.loads((Path(__file__).parents[1]/"default_config.json").read_text())\ndef load_config(): return Config()\n')
    subprocess.run(['git','init','-q',str(repo)],check=True)
    def commit():
        subprocess.run(['git','-C',str(repo),'add','.'],check=True)
        subprocess.run(['git','-C',str(repo),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture'],check=True)
    commit()
    subprocess.run(['git','-C',str(repo),'tag','sim-v6.0.0-frozen'],check=True)
    plan = template(); plan['frozen_commit'] = ds.git(repo,'rev-parse','HEAD')
    plan['default_config_sha256'] = ds.digest((repo/'default_config.json').read_bytes())
    plan['effective_config_sha256'] = ds.digest(ds.canonical(cfg))
    return repo, plan, cfg, commit


def test_guards_clean_tree_exact_tag_and_config_hashes(frozen_repo):
    repo, plan, cfg, commit = frozen_repo
    assert ds.source_guard(repo,plan) == cfg
    (repo/'untracked.txt').write_text('user work')
    with pytest.raises(ValueError,match='Dirty tree'): ds.source_guard(repo,plan)
    (repo/'untracked.txt').unlink()
    wrong = deepcopy(plan); wrong['default_config_sha256'] = '0'*64
    with pytest.raises(ValueError,match='Config hash mismatch'): ds.source_guard(repo,wrong)
    wrong = deepcopy(plan); wrong['effective_config_sha256'] = '0'*64
    with pytest.raises(ValueError,match='effective settings'): ds.source_guard(repo,wrong)
    (repo/'note.txt').write_text('committed descendant'); commit()
    with pytest.raises(ValueError,match='Tag mismatch'): ds.source_guard(repo,plan)


def test_generator_requires_clean_tooling_and_predeclared_plan(frozen_repo, tmp_path, monkeypatch):
    repo, plan, cfg, _ = frozen_repo
    monkeypatch.setattr(ds,'TOOL_ROOT',repo)
    output = tmp_path/'data'
    calls = []
    original_run = subprocess.run
    def fake_run(command, **kwargs):
        if command[1:3] != ["-m", "lionsim.run"]:
            return original_run(command, **kwargs)
        resolved = ds.read(output/'resolved_plan.json')
        assert resolved['days'] == 20 and resolved['splits']['train'] == [1,14]
        assert '--seed' in command and command[command.index('--seed')+1] == '9999'
        assert command[command.index('--chunk-size')+1] == '200'
        calls.append(command)
        ds.write(output/'raw/run_fake/run_manifest.json', {'seed':9999,'days':20,'config':cfg,'status':'complete'})
    monkeypatch.setattr(ds.subprocess,'run',fake_run)
    with pytest.raises(ValueError,match='not authorized'):
        ds.generate(repo,output,plan,schema(),'main',1000)
    ds.generate(repo,output,plan,schema(),'smoke')
    assert len(calls) == 1
    ds.generate(repo,output,plan,schema(),'smoke')
    assert len(calls) == 1  # Finished generation is safely idempotent.
    modified = deepcopy(plan); modified['start_date'] = '2027-01-01'
    with pytest.raises(ValueError,match='Resolved plan mismatch'):
        ds.generate(repo,output,modified,schema(),'smoke')


@pytest.fixture
def raw_dataset(tmp_path):
    output = tmp_path/'data'; plan = template(); spec = schema()
    cfg = {'output':{'embed_cumulative_path_in_reports':False}}
    plan['effective_config_sha256'] = ds.digest(ds.canonical(cfg))
    resolved = ds.resolve_plan(plan,'smoke')
    resolved.update(export_schema_sha256=ds.digest(ds.canonical(spec)),tooling_commit='fixture')
    ds.write(output/'resolved_plan.json', resolved)
    run = output/'raw/run_fixture'; run.mkdir(parents=True)
    ds.write(run/'run_manifest.json', {'status':'complete','completed_days':20,'days':20,'seed':9999,'config':cfg,
                                     'schema_version':'lionsim-v6','versions':{'lionsim':'6.0.0'},'image_days':0})
    ds.write(run/'validation_report.json', {'valid':True})
    with (run/'targets.csv').open('w',newline='') as handle:
        writer = csv.DictWriter(handle,fieldnames=spec['columns']+['day_type','heat']);writer.writeheader()
        for day in range(1,21):
            for report in range(1,8):
                row = dict.fromkeys(spec['columns'],'')
                row.update(day=day,report_index=report,weather='rain',ambient_temp_c='23.25',next_zone_target='END_OF_DAY',day_type='TOP_SECRET_TYPE',heat='TOP_SECRET_HEAT')
                writer.writerow(row)
    return output,spec


def test_weather_context_export_never_includes_day_type_or_heat(raw_dataset):
    output,spec = raw_dataset
    assert {'weather','ambient_temp_c'} <= set(spec['feature_groups']['context'])
    result = ds.export_dataset(output,spec)
    assert result['status'] == 'PASS' and result['rows'] == 140
    assert result['splits'] == {'train':{'days':14,'rows':98},'validation':{'days':3,'rows':21},'test':{'days':3,'rows':21}}
    for path in (output/'export').glob('*.csv'):
        rows = list(csv.DictReader(path.open()))
        assert all(r['weather']=='rain' and r['ambient_temp_c']=='23.25' for r in rows)
        assert 'day_type' not in rows[0] and 'heat' not in rows[0]
        assert 'TOP_SECRET' not in path.read_text()
    for hidden in ('day_type','heat'):
        bad = deepcopy(spec); bad['feature_groups']['context'].append(hidden)
        bad['columns'] = bad['identifiers']+bad['labels']+sum(bad['feature_groups'].values(),[])
        with pytest.raises(ValueError,match='Unsafe'): ds.schema_columns(bad)


def test_verifier_rejects_leakage_and_corrupt_exports(raw_dataset):
    output,spec = raw_dataset
    ds.export_dataset(output,spec)
    path = output/'export/train.csv'
    path.write_text(path.read_text().replace('rain','hot',1))
    with pytest.raises(ValueError,match='differs'): ds.verify(output,spec)
    ds.export_dataset(output,spec)
    (output/'export/hidden_state.csv').write_text('day_type,heat\n')
    with pytest.raises(ValueError,match='Unexpected'): ds.verify(output,spec)


def test_duplicate_day_report_and_schema_mismatch_abort(raw_dataset):
    output,spec = raw_dataset
    run = ds.run_path(output); target = run/'targets.csv'
    lines = target.read_text().splitlines(); lines[-1] = lines[-2]
    target.write_text('\n'.join(lines)+'\n')
    with pytest.raises(ValueError,match='duplicated'): ds.export_dataset(output,spec)
    bad = deepcopy(spec); bad['schema_version'] = 'wrong'
    with pytest.raises(ValueError,match='schema hash'): ds.export_dataset(output,bad)
