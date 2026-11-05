"""Small SQLite release contract; no simulation or model inputs live here."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
from datetime import date, timedelta

from . import __version__, SCHEMA_VERSION

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_SEEDS = {42, 137, 271, 2026, 3003, 9999}
SCHEMA = '''
CREATE TABLE images(id INTEGER PRIMARY KEY, day_index INTEGER NOT NULL,
 date TEXT NOT NULL, time_of_day TEXT NOT NULL, report_index INTEGER NOT NULL,
 image BLOB NOT NULL);
CREATE TABLE logs(id INTEGER PRIMARY KEY, day_index INTEGER NOT NULL,
 date TEXT NOT NULL, time_of_day TEXT NOT NULL, event_name TEXT NOT NULL,
 zone TEXT, weather TEXT NOT NULL);
CREATE INDEX logs_day_time ON logs(day_index, date, time_of_day);
CREATE INDEX logs_event ON logs(event_name);
CREATE INDEX images_day_report ON images(day_index, report_index);
CREATE INDEX images_time ON images(date, time_of_day);
'''
COLUMNS = {
 'images': [('id','INTEGER',0,1),('day_index','INTEGER',1,0),('date','TEXT',1,0),
            ('time_of_day','TEXT',1,0),('report_index','INTEGER',1,0),('image','BLOB',1,0)],
 'logs': [('id','INTEGER',0,1),('day_index','INTEGER',1,0),('date','TEXT',1,0),
          ('time_of_day','TEXT',1,0),('event_name','TEXT',1,0),('zone','TEXT',0,0),('weather','TEXT',1,0)],
}
INDEXES = {'logs_day_time': ('logs', ['day_index','date','time_of_day']),
           'logs_event': ('logs', ['event_name']),
           'images_day_report': ('images', ['day_index','report_index']),
           'images_time': ('images', ['date','time_of_day'])}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.'+path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(value, out, indent=2, allow_nan=False)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_plan(path):
    plan = json.loads(Path(path).read_text())
    if plan['package_version'] != __version__ or plan['schema'] != SCHEMA_VERSION:
        raise ValueError('plan version/schema mismatch')
    if plan['image_size'] not in (500, 1000) or plan['chunk_size'] not in range(1,201):
        raise ValueError('invalid image size/chunk size')
    if set(plan['splits']) != {'train','val','test'}:
        raise ValueError('plan must contain train, val and test')
    seeds, paths = set(), set()
    previous = None
    for name in ('train','val','test'):
        part = plan['splits'][name]
        seed, days = part['seed'], part['days']
        if type(seed) is not int or seed < 0 or seed in FORBIDDEN_SEEDS or seed in seeds:
            raise ValueError('forbidden or duplicate seed')
        if type(days) is not int or days < 1:
            raise ValueError('days must be positive integers')
        start, end = date.fromisoformat(part['start_date']), date.fromisoformat(part['end_date'])
        if end != start + timedelta(days=days-1) or (previous and start != previous+timedelta(days=1)):
            raise ValueError('date ranges do not chain')
        database = (Path(path).resolve().parent / part['database']).resolve()
        if database in paths:
            raise ValueError('split databases must be distinct')
        previous = end
        seeds.add(seed)
        paths.add(database)
    return plan


def git(root, *args):
    return subprocess.check_output(['git','-C',str(root),*args], text=True).strip()


def guard_source(plan, root=ROOT):
    """Pin the frozen tag and unchanged simulation, allowing new export tooling."""
    if git(root, 'status','--porcelain','--untracked-files=all'):
        raise ValueError('dirty git tree; commit changes or use a clean worktree')
    if plan['frozen_tag'] != 'sim-v6.0.0-frozen':
        raise ValueError('unexpected frozen tag')
    pinned = plan['frozen_commit']
    if git(root, 'tag','--list',plan['frozen_tag']):
        if git(root, 'rev-parse',plan['frozen_tag']+'^{commit}') != pinned:
            raise ValueError('frozen tag mismatch')
    # Verify the historical source, not HEAD equality: this CLI is necessarily newer.
    files = git(root, 'ls-tree','-r','--name-only',pinned,'--','lionsim','default_config.json').splitlines()
    if not files:
        raise ValueError('missing frozen source')
    for filename in files:
        if filename == 'lionsim/plotting.py':
            continue  # Only existing-file change: the tested in-memory renderer branch.
        expected = git(root, 'rev-parse',f'{pinned}:{filename}')
        if git(root, 'hash-object',filename) != expected:
            raise ValueError('frozen simulator source mismatch: '+filename)
    if hashlib.sha256((Path(root)/'default_config.json').read_bytes()).hexdigest() != plan['default_config_sha256']:
        raise ValueError('default config hash mismatch')
    if hashlib.sha256((Path(root)/'lionsim/plotting.py').read_bytes()).hexdigest() != plan['renderer_sha256']:
        raise ValueError('renderer hash mismatch')
    from .config import load_config
    config = load_config()
    if digest(config.to_dict()) != plan['config_hash']:
        raise ValueError('config hash mismatch')
    return config.to_dict()


def db_path(plan_path, part):
    return (Path(plan_path).resolve().parent / part['database']).resolve()


def meta_path(database):
    return Path(database).with_suffix('.meta.json')


def read_only(database):
    return sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro', uri=True)


def assert_schema(connection):
    tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if tables != set(COLUMNS):
        raise ValueError('unexpected tables')
    for table, expected in COLUMNS.items():
        actual = [(r[1],r[2],r[3],r[5]) for r in connection.execute(f'PRAGMA table_info({table})')]
        if actual != expected:
            raise ValueError('schema mismatch: '+table)
    indexes = {r[0]:r[1] for r in connection.execute("SELECT name,tbl_name FROM sqlite_master WHERE type='index'")}
    if indexes != {name: table for name,(table,_) in INDEXES.items()}:
        raise ValueError('index mismatch')
    for name, (_, columns) in INDEXES.items():
        if [r[2] for r in connection.execute(f'PRAGMA index_info({name})')] != columns:
            raise ValueError('index columns mismatch')
