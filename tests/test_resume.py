import json
from pathlib import Path
import pytest
from lionsim.run import build_parser, run
from lionsim.io_utils import write_json


def test_atomic_failure_preserves_destination(tmp_path):
    target=tmp_path/'record.json'
    write_json(target, {'ok': True})
    before=target.read_bytes()
    with pytest.raises(ValueError):
        write_json(target, {'bad':float('nan')})
    assert target.read_bytes()==before
    assert list(tmp_path.iterdir())==[target]


def test_stats_resume_matches_full_run_and_skips_completed_days(tmp_path):
    parser=build_parser()
    partial=run(parser.parse_args(['--stats-only','--stats-days','3','--chunk-size','2','--out',str(tmp_path/'chunk')]))
    manifest=json.loads((partial/'run_manifest.json').read_text())
    assert manifest['status']=='partial' and manifest['completed_days']==2
    checkpoints=list((partial/'checkpoints').glob('*.json'))
    stamps={p:p.stat().st_mtime_ns for p in checkpoints}
    run(parser.parse_args(['--resume',str(partial)]))
    assert all(p.stat().st_mtime_ns==t for p,t in stamps.items())
    assert json.loads((partial/'run_manifest.json').read_text())['completed_days']==3
    assert not list((partial/'days').rglob('*.parquet'))
    full=run(parser.parse_args(['--stats-only','--stats-days','3','--out',str(tmp_path/'full')]))
    for name in ('targets.csv','stats_report.json','stats_report.md'):
        assert (partial/name).read_bytes()==(full/name).read_bytes()
