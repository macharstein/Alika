import ast
import json
from pathlib import Path

import pandas as pd
import pytest

from lionsim.l5_analysis import analyze, goal_accuracy
from lionsim.l5_truegoal import true_goal_at_report


def test_no_export_module_can_import_truegoal_transitively():
    root = Path(__file__).parents[1] / 'lionsim'
    def imports(name, seen):
        if name in seen or not (root / f'{name}.py').exists():
            return
        seen.add(name)
        tree = ast.parse((root / f'{name}.py').read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = (node.module or '').removeprefix('lionsim.').split('.')[0]
                imports(module, seen)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith('lionsim.'):
                        imports(alias.name.split('.')[1], seen)
    for name in ('run', 'reports', 'features_heading', 'features_path', 'io_utils'):
        seen = set()
        imports(name, seen)
        assert 'l5_truegoal' not in seen and 'l5_analysis' not in seen


def test_goal_alignment_accuracy():
    hidden = pd.DataFrame({'t_iso': ['2026-01-01T08:00:00', '2026-01-01T08:01:00'], 'goal':['Den','Kopje']})
    assert true_goal_at_report(hidden, '2026-01-01T08:00:00', ['Den','Kopje']) == 'Den'
    with pytest.raises(ValueError, match='Missing exact'):
        true_goal_at_report(hidden, '2026-01-01T08:00:30', ['Den','Kopje'])
    rows = [{'moving': True, 'implied_goal': 'Den', 'true_goal':'Den', 'report_index':1},
            {'moving': True, 'implied_goal': 'ambiguous', 'true_goal':'Kopje', 'report_index':1},
            {'moving': False, 'implied_goal': 'none', 'true_goal':'Den', 'report_index':1}]
    result = goal_accuracy(rows, [1])['headline']
    assert result['moving_count'] == 2 and result['accuracy'] == .5
    assert sum(map(sum, result['confusion']['counts'])) == 2


def test_end_to_end_resumable_analysis_no_existing_changes(tmp_path):
    from lionsim.run import build_parser, run
    parser = build_parser()
    directory = run(parser.parse_args(['--stats-only','--stats-days','5','--keep-files','--no-images',
                                      '--out', str(tmp_path), '--chunk-size','3']))
    with pytest.raises(ValueError, match='Finish all'):
        analyze(directory)
    run(parser.parse_args(['--resume',str(directory),'--workers','2']))
    before = {name:(directory/name).read_bytes() for name in ('targets.csv','stats_report.json','stats_report.md','run_manifest.json')}
    result = analyze(directory)
    assert result['days'] == 5 and result['headline']['count'] == 25
    assert result['all_reports']['count'] == 35
    assert result['sensitivity_post_hoc'][1]['headline'] == result['headline']
    assert 'LEAKY' in (directory/'l5_report.md').read_text()
    assert 'post hoc' in (directory/'l5_report.md').read_text()
    assert all((directory/name).read_bytes() == value for name,value in before.items())
    caches = list((directory/'l5_analysis_checkpoints').glob('*.json'))
    stamps = {p:p.stat().st_mtime_ns for p in caches}
    assert analyze(directory) == result
    assert all(p.stat().st_mtime_ns == stamp for p,stamp in stamps.items())
    caches[0].write_text('{')
    assert analyze(directory) == result
    assert all(p.stat().st_mtime_ns == stamps[p] for p in caches[1:])
    assert not list(directory.rglob('*.png'))
    assert 'true_goal' not in (directory/'targets.csv').read_text().splitlines()[0]
