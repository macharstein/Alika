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


def test_stats_explicit_images_are_limited_and_repaired_on_resume(tmp_path):
    parser = build_parser()
    directory = run(parser.parse_args([
        '--stats-only', '--stats-days', '4', '--image-days', '3', '--chunk-size', '2',
        '--set', 'images.size_px=128', '--out', str(tmp_path)]))
    before = {p: p.stat().st_mtime_ns for p in (directory / 'checkpoints').glob('*.json')}
    images = sorted(directory.rglob('*.png'))
    assert len(images) == 18  # eight reports plus one contact sheet per day
    missing = images[0]
    missing.unlink()
    run(parser.parse_args(['--resume', str(directory), '--chunk-size', '2']))
    assert missing.is_file()
    assert sum(p.stat().st_mtime_ns == stamp for p, stamp in before.items()) == 1
    run(parser.parse_args(['--resume', str(directory), '--chunk-size', '2']))
    assert len(list(directory.rglob('*.png'))) == 27
    assert not list(directory.rglob('gps*'))
    assert not list(directory.rglob('hidden_state*'))
    assert not list(directory.rglob('day.json'))
    manifest = json.loads((directory / 'run_manifest.json').read_text())
    assert manifest['status'] == 'complete' and manifest['image_days'] == 3
    assert not manifest['keep_files']
    checkpoints = [json.loads(p.read_text()) for p in (directory / 'checkpoints').glob('*.json')]
    assert all(len(r['files']) == (9 if r['day_index'] <= 3 else 0) for r in checkpoints)
    stamps = {p: p.stat().st_mtime_ns for p in directory.rglob('*.png')}
    run(parser.parse_args(['--resume', str(directory)]))
    assert all(p.stat().st_mtime_ns == stamp for p, stamp in stamps.items())
