from datetime import datetime, timedelta
import json
import sqlite3
import struct
import zlib

import pytest

from lionsim.build_dataset import metadata
from lionsim.sqlite_common import SCHEMA, db_path, meta_path, read_plan, write_json
from lionsim.verify_db import valid_png, verify_split


def png(size=500):
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(size*(4*size+1))))+chunk(b'IEND',b'')


@pytest.fixture
def saved(tmp_path):
    p=read_plan('data/check_plans/smoke.json'); p['image_size']=500
    for i,(name,part) in enumerate(p['splits'].items()):
        d=f'2026-01-0{i+1}'
        part.update(days=1,start_date=d,end_date=d,database=f'{name}/lion.db')
    path=tmp_path/'plan.json'; path.write_text(json.dumps(p))
    for name,part in p['splits'].items():
        db=db_path(path,part); db.parent.mkdir()
        write_json(meta_path(db),dict(metadata(p,part,name,500),creation_time='2026-11-05T00:00:00+00:00'))
        start=datetime.fromisoformat(part['start_date']+'T05:00:00')
        with sqlite3.connect(db) as con:
            con.executescript(SCHEMA)
            for index in range(1,9):
                t=start+timedelta(hours=3*index)
                con.execute('INSERT INTO images VALUES(?,?,?,?,?,?)',(index,1,str(t.date()),str(t.time()),index,png()))
            con.execute('INSERT INTO logs VALUES(1,1,?,?,?,NULL,?)',(str(start.date()),str(start.time()),'WOKE_UP','clear'))
        if name=='test':
            db.chmod(0o444)
    return path,p


def test_complete_and_readonly_checks(saved):
    path,p=saved
    for name in p['splits']:
        assert all(verify_split(path,p,name).values())
    db=db_path(path,p['splits']['test']); db.chmod(0o644)
    assert not verify_split(path,p,'test')['test file read-only']


@pytest.mark.parametrize('statement,label',[
 ('UPDATE images SET image=x\'001122\' WHERE id=1','every image is a complete valid PNG'),
 ("UPDATE logs SET event_name='CAR_PASSED'",'public vocabulary, zones and daily weather'),
 ("UPDATE logs SET date='2025-01-01'",'simulated dates and times consistent with day'),
 ('DELETE FROM images WHERE id=8','planned day count and eight images per day'),
 ('ALTER TABLE logs ADD COLUMN day_type TEXT','exact schema and indexes; no hidden fields'),
])
def test_reject_corruption(saved,statement,label):
    path,p=saved
    with sqlite3.connect(db_path(path,p['splits']['train'])) as con:
        con.execute(statement)
    assert not verify_split(path,p,'train')[label]


def test_png_payload_checked_not_only_signature():
    raw=png()
    valid_png(raw,500)
    with pytest.raises(ValueError):
        valid_png(raw[:-1],500)
    with pytest.raises(ValueError):
        valid_png(raw,1000)
    raw=bytearray(raw); raw[60]^=1
    with pytest.raises(ValueError):
        valid_png(bytes(raw),500)
