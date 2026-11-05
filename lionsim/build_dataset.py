"""Stream independently seeded GPS days into SQLite, one atomic day at a time."""
from __future__ import annotations

import argparse
from collections import deque
from contextlib import closing
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import gc
import json
import multiprocessing
import os
from pathlib import Path
import resource
import sqlite3
import sys
import time

from .sqlite_common import (SCHEMA, ROOT, assert_schema, db_path, digest, git,
                           guard_source, meta_path, read_only, read_plan, write_json)


def peak_rss_mib():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024**2 if sys.platform == 'darwin' else 1024)


def run_day(job):
    """Worker result contains one day's public rows only, never a DayResult."""
    import numpy as np
    from .config import Config
    from .events import TOKENS
    from .plotting import render_reports
    from .reports import build_reports
    from .simulator import simulate_day

    config = Config(job['config'])
    config['images']['size_px'] = job['image_size']
    index = job['day_index']
    # Identical to SeedSequence(seed).spawn(N)[index-1], without an N-item list.
    sequence = np.random.SeedSequence(job['seed'], spawn_key=(index-1,))
    day = simulate_day(config, day_index=index, seed=job['seed'],
                       start_date=job['start_date'], seed_sequence=sequence)
    reports = build_reports(day, config)
    blobs = render_reports(day, reports, config, None)
    if len(blobs) != 8 or not day.weather:
        raise ValueError('expected eight reports and observable weather')
    images = []
    for report, blob in zip(reports, blobs):
        d, t = report['report_time'].split('T')
        images.append(((index-1)*8+report['report_index'], index, d, t, report['report_index'], blob))
    logs = []
    for offset, event in enumerate(day.events, 1):
        if event['token'] not in TOKENS or offset >= 1_000_000:
            raise ValueError('invalid public event')
        d, t = event['t'].split('T')
        logs.append(((index-1)*1_000_000+offset, index, d, t,
                     event['token'], event.get('zone'), day.weather))
    del day, reports, blobs, config
    gc.collect()  # Matplotlib Figure/Canvas cycles must not accumulate across days.
    return {'day_index':index, 'images':images, 'logs':logs,
            'worker_pid':os.getpid(), 'worker_peak_rss_mib':peak_rss_mib()}


def stream_days(jobs, workers):
    """At most 2*workers jobs/results resident; ordered writes give stable IDs."""
    with ProcessPoolExecutor(max_workers=workers,
                             mp_context=multiprocessing.get_context('spawn')) as pool:
        pending = deque()
        iterator = iter(jobs)
        for _ in range(2*workers):
            job = next(iterator, None)
            if job is None:
                break
            pending.append(pool.submit(run_day, job))
        while pending:
            yield pending.popleft().result()
            job = next(iterator, None)
            if job is not None:
                pending.append(pool.submit(run_day, job))


def metadata(plan, part, name, image_size):
    return {'split':name, 'seed':part['seed'], 'days':part['days'],
            'start_date':part['start_date'], 'end_date':part['end_date'],
            'version':plan['package_version'], 'schema':plan['schema'],
            'config_hash':plan['config_hash'], 'image_size':image_size,
            'plan_hash':digest(plan)}


def check_metadata(database, expected):
    actual = json.loads(meta_path(database).read_text())
    if any(actual.get(k) != v for k,v in expected.items()):
        raise ValueError('sidecar metadata mismatch: '+str(database))
    return actual


def finished_day(connection, index):
    count, unique, lo, hi = connection.execute(
        'SELECT count(*),count(DISTINCT report_index),min(report_index),max(report_index) '
        'FROM images WHERE day_index=?', (index,)).fetchone()
    logs = connection.execute('SELECT count(*) FROM logs WHERE day_index=?',(index,)).fetchone()[0]
    if count == 0 and logs == 0:
        return False
    if (count,unique,lo,hi) != (8,8,1,8) or logs == 0:
        raise ValueError(f'incomplete/corrupt committed day {index}')
    return True


def build_split(plan_path, plan, name, config, workers, resume=False, image_size=None,
                also_png=False, chunk_size=None):
    part = plan['splits'][name]
    database = db_path(plan_path, part)
    size = image_size or plan['image_size']
    expected = metadata(plan, part, name, size)
    if database.exists() or meta_path(database).exists():
        if not resume:
            raise ValueError('output already exists; use --resume')
        check_metadata(database, expected)
    else:
        database.parent.mkdir(parents=True, exist_ok=True)
        write_json(meta_path(database), dict(expected, creation_time=datetime.now(timezone.utc).isoformat()))
    # A completed read-only test DB must remain read-only even on resume.
    if database.exists() and not database.stat().st_mode & 0o222:
        with closing(read_only(database)) as connection:
            assert_schema(connection)
            if name != 'test' or any(not finished_day(connection,i) for i in range(1,part['days']+1)):
                raise ValueError('unexpected read-only/incomplete database')
        return {'split':name, 'complete':True, 'new_days':0}
    connection = sqlite3.connect(database)
    started = time.perf_counter()
    worker_peaks = {}
    new_days = 0
    try:
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA synchronous=FULL')
        connection.execute('PRAGMA cache_size=-4096')
        if connection.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0] == 0:
            connection.executescript(SCHEMA)
        assert_schema(connection)
        for table in ('images','logs'):
            if connection.execute(f'SELECT count(*) FROM {table} WHERE day_index<1 OR day_index>?',(part['days'],)).fetchone()[0]:
                raise ValueError('out-of-plan day')
        def jobs():
            submitted = 0
            for index in range(1,part['days']+1):
                if finished_day(connection,index):
                    continue
                if submitted >= (chunk_size or plan['chunk_size']):
                    break
                submitted += 1
                yield {'day_index':index,'seed':part['seed'],'start_date':part['start_date'],
                       'config':config,'image_size':size}
        for result in stream_days(jobs(), workers):
            with connection:  # Images + logs either both commit, or neither does.
                connection.executemany('INSERT INTO images VALUES (?,?,?,?,?,?)',result['images'])
                connection.executemany('INSERT INTO logs VALUES (?,?,?,?,?,?,?)',result['logs'])
            new_days += 1
            pid = str(result['worker_pid'])
            worker_peaks[pid] = max(worker_peaks.get(pid,0),result['worker_peak_rss_mib'])
            if also_png:
                publish_pngs(database, result['images'])
            if new_days % 10 == 0:
                print(f'{name}: committed day {result["day_index"]}/{part["days"]}',flush=True)
            del result
        complete = all(finished_day(connection,i) for i in range(1,part['days']+1))
        connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        if complete:
            # No WAL dependencies when the final test database becomes read-only.
            connection.execute('PRAGMA journal_mode=DELETE')
    finally:
        connection.close()
    if also_png:  # Repair optional files after interruption following a DB commit.
        with closing(read_only(database)) as reader:
            for row in reader.execute('SELECT * FROM images ORDER BY id'):
                publish_pngs(database, [row])
    if name == 'test' and complete:
        database.chmod(database.stat().st_mode & ~0o222)
        print('Test database is read-only. Open test data once, at the end of model development.',flush=True)
    elapsed = time.perf_counter()-started
    result = {'split':name,'new_days':new_days,'complete':complete,'elapsed_seconds':elapsed,
              'seconds_per_day':elapsed/new_days if new_days else None,
              'main_peak_rss_mib':peak_rss_mib(),'worker_peak_rss_mib':worker_peaks,
              'database_bytes':database.stat().st_size,'image_size':size,'workers':workers}
    with closing(read_only(database)) as reader:
        result['completed_days'] = reader.execute('SELECT count(DISTINCT day_index) FROM images').fetchone()[0]
    result['bytes_per_day'] = result['database_bytes']/max(1,result['completed_days'])
    write_json(database.with_suffix('.metrics.json'),result)
    return result


def publish_pngs(database, rows):
    from .io_utils import atomic_output
    for row in rows:
        path = database.parent/'png'/f'day_{row[1]:04d}_report_{row[4]}.png'
        if not path.exists():
            with atomic_output(path) as temporary:
                temporary.write_bytes(row[5])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--image-size',type=int,choices=(500,1000))
    parser.add_argument('--only',choices=('train','val','test'))
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--also-png',action='store_true')
    parser.add_argument('--chunk-size',type=int,default=None,help='max new days per split, <=200')
    args = parser.parse_args(argv)
    if args.workers < 1 or args.chunk_size is not None and not 1 <= args.chunk_size <= 200:
        parser.error('positive workers and chunk size1..200 required')
    try:
        plan = read_plan(args.plan)
        config = guard_source(plan)
        # Require a tracked, committed plan, including diagnostic plans.
        git(ROOT,'ls-files','--error-unmatch',str(args.plan.resolve()))
        for name in (args.only,) if args.only else ('train','val','test'):
            result = build_split(args.plan,plan,name,config,args.workers,args.resume,
                                 args.image_size,args.also_png,args.chunk_size)
            print(json.dumps(result),flush=True)
            if not result['complete']:
                print('Chunk complete. Re-run the same command with --resume.',flush=True)
                break
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1,f'ABORT: {error}\n')


if __name__ == '__main__':
    main()
