import copy
import json
import sqlite3
import subprocess
from pathlib import Path

import pytest

from lionsim import build_dataset as build
from lionsim.config import load_config
from lionsim.sqlite_common import (COLUMNS, assert_schema, db_path, digest,
                                   guard_source, meta_path, read_plan)


@pytest.fixture
def plan(tmp_path):
    value = read_plan('data/check_plans/smoke.json')
    starts = ['2026-01-01','2026-01-03','2026-01-05']
    ends = ['2026-01-02','2026-01-04','2026-01-06']
    for (name,part),start,end in zip(value['splits'].items(),starts,ends):
        part.update(days=2,start_date=start,end_date=end,database=f'{name}/lion.db')
    path = tmp_path/'plan.json'
    path.write_text(json.dumps(value))
    return path, value


def fake_day(job):
    index = job['day_index']
    return {'day_index':index,'images':[((index-1)*8+i,index,'2026-01-01','08:00:00',i,b'png') for i in range(1,9)],
            'logs':[((index-1)*1000000+1,index,'2026-01-01','05:00:00','WOKE_UP','Den','hot')],
            'worker_pid':123,'worker_peak_rss_mib':100}


@pytest.fixture
def fake_workers(monkeypatch):
    monkeypatch.setattr(build,'stream_days',lambda jobs,workers:map(fake_day,jobs))


def test_schema_resume_matches_uninterrupted(plan,fake_workers,tmp_path):
    path,p = plan
    original=build.build_split(path,p,'train',{},1)
    database=db_path(path,p['splits']['train'])
    raw=database.read_bytes()
    with sqlite3.connect(database) as con:
        assert_schema(con)
        assert con.execute('SELECT count(*) FROM images').fetchone()[0]==16
        assert con.execute('SELECT count(*) FROM logs').fetchone()[0]==2
    p2=copy.deepcopy(p)
    p2['splits']['train']['database']='resumed/lion.db'
    first=build.build_split(path,p2,'train',{},1,chunk_size=1)
    assert first['new_days']==1 and not first['complete']
    second=build.build_split(path,p2,'train',{},1,resume=True)
    assert second['new_days']==1 and second['complete']
    assert db_path(path,p2['splits']['train']).read_bytes()==raw
    assert build.build_split(path,p2,'train',{},1,resume=True)['new_days']==0


@pytest.mark.parametrize('field,value',[('seed',1),('version','bad'),('config_hash','bad'),('image_size',500)])
def test_sidecar_mismatch_aborts(plan,fake_workers,field,value):
    path,p=plan
    build.build_split(path,p,'train',{},1)
    side=meta_path(db_path(path,p['splits']['train']))
    data=json.loads(side.read_text()); data[field]=value
    side.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='metadata mismatch'):
        build.build_split(path,p,'train',{},1,resume=True)


def test_read_only_test_db(plan,fake_workers):
    path,p=plan
    build.build_split(path,p,'test',{},1)
    db=db_path(path,p['splits']['test'])
    assert not db.stat().st_mode & 0o222
    assert build.build_split(path,p,'test',{},1,resume=True)['new_days']==0


def test_dirty_tree_aborts(tmp_path):
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    (tmp_path/'dirty').write_text('x')
    with pytest.raises(ValueError,match='dirty git tree'):
        guard_source({},tmp_path)


def test_plan_rejects_dates_and_seeds(plan):
    path,p=plan
    p['splits']['test']['seed']=42
    path.write_text(json.dumps(p))
    with pytest.raises(ValueError,match='forbidden'):
        read_plan(path)
    p['splits']['test']['seed']=9103
    p['splits']['test']['start_date']='2027-01-01'
    path.write_text(json.dumps(p))
    with pytest.raises(ValueError,match='date ranges'):
        read_plan(path)


def test_real_worker_and_memory_renderer_match_disk(tmp_path):
    from lionsim.plotting import render_reports
    from lionsim.reports import build_reports
    from lionsim.simulator import simulate_day
    config=load_config()
    job={'config':config.to_dict(),'seed':9104,'start_date':'2026-01-01','day_index':2,'image_size':1000}
    result=build.run_day(job)
    day=simulate_day(config,seed=9104,day_index=2)
    reports=build_reports(day,config)
    disk=render_reports(day,[reports[0]],config,tmp_path)
    assert result['images'][0][-1]==disk[0].read_bytes()
    assert len(result['images'])==8
    assert result['images'][-1][2:5]==('2026-01-03','05:00:00',8)
    assert {row[4] for row in result['logs']}=={event['token'] for event in day.events}
    assert all(row[-1]==day.weather for row in result['logs'])
    assert set(result)=={'day_index','images','logs','worker_pid','worker_peak_rss_mib'}


def test_atomic_rollback(plan,monkeypatch):
    def bad(jobs,workers):
        result=fake_day(next(iter(jobs)))
        result['logs'][0]=tuple([None]*7)  # Violates NOT NULL after images insert.
        yield result
    monkeypatch.setattr(build,'stream_days',bad)
    path,p=plan
    with pytest.raises(sqlite3.IntegrityError):
        build.build_split(path,p,'train',{},1)
    with sqlite3.connect(db_path(path,p['splits']['train'])) as con:
        assert con.execute('SELECT count(*) FROM images').fetchone()[0]==0
        assert con.execute('SELECT count(*) FROM logs').fetchone()[0]==0
