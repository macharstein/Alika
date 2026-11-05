"""Stream-check SQLite datasets against their committed split plan."""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import struct
import sqlite3
import zlib

from .build_dataset import check_metadata, metadata
from .events import TOKENS, ZONE_TOKENS
from .sqlite_common import (assert_schema, db_path, meta_path, read_only, read_plan)


def valid_png(blob, size):
    """Check full PNG framing, CRCs and decompressed RGBA scanlines, one image only."""
    if not blob.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('invalid PNG signature')
    offset = 8
    idat = bytearray()
    header = False
    ended = False
    while offset < len(blob):
        if offset+12 > len(blob):
            raise ValueError('truncated PNG chunk')
        length = struct.unpack('>I',blob[offset:offset+4])[0]
        kind = blob[offset+4:offset+8]
        end = offset+8+length
        if end+4 > len(blob):
            raise ValueError('truncated PNG payload')
        payload = blob[offset+8:end]
        crc = struct.unpack('>I',blob[end:end+4])[0]
        if zlib.crc32(kind+payload)&0xffffffff != crc:
            raise ValueError('PNG checksum mismatch')
        if kind == b'IHDR':
            if header or offset != 8 or length != 13:
                raise ValueError('invalid PNG header')
            w,h,depth,color,compression,filtering,interlace = struct.unpack('>IIBBBBB',payload)
            if (w,h,depth,color,compression,filtering,interlace) != (size,size,8,6,0,0,0):
                raise ValueError('PNG dimensions/encoding mismatch')
            header = True
        elif kind == b'IDAT':
            if not header:
                raise ValueError('PNG missing header')
            idat.extend(payload)
        elif kind == b'IEND':
            if length or end+4 != len(blob):
                raise ValueError('invalid PNG end')
            ended = True
        offset = end+4
    if not header or not ended or not idat:
        raise ValueError('incomplete PNG')
    expected = size*(size*4+1)
    decoder = zlib.decompressobj()
    raw = decoder.decompress(idat, expected+1)
    if len(raw) != expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError('invalid PNG pixel stream')
    if any(raw[i] > 4 for i in range(0,expected,size*4+1)):
        raise ValueError('invalid PNG scanline filter')


def verify_split(plan_path, plan, name, emit=print):
    part = plan['splits'][name]
    database = db_path(plan_path,part)
    checks = {}
    def check(label, work):
        try:
            work()
            checks[label] = True
            emit(f'PASS {name}: {label}')
        except (ValueError, AssertionError, OSError, KeyError, json.JSONDecodeError, zlib.error, sqlite3.Error, struct.error) as error:
            checks[label] = False
            emit(f'FAIL {name}: {label}: {error}')
    def require(value,message):
        if not value:
            raise ValueError(message)
    def sidecar():
        saved = json.loads(meta_path(database).read_text())
        require(saved['image_size'] in (500,1000),'invalid image size')
        check_metadata(database,metadata(plan,part,name,saved['image_size']))
        datetime.fromisoformat(saved['creation_time'])
    check('sidecar provenance',sidecar)
    if not database.exists():
        check('database exists',lambda: require(False,'missing file'))
        return checks
    with closing(read_only(database)) as connection:
        check('exact schema and indexes; no hidden fields',lambda: assert_schema(connection))
        check('SQLite integrity',lambda: require(connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok','integrity failure'))
        if not checks['exact schema and indexes; no hidden fields']:
            return checks
        def days():
            for table in ('images','logs'):
                n,lo,hi = connection.execute(f'SELECT count(DISTINCT day_index),min(day_index),max(day_index) FROM {table}').fetchone()
                require((n,lo,hi)==(part['days'],1,part['days']),f'{table}: wrong day coverage')
            invalid = connection.execute('''SELECT count(*) FROM (SELECT day_index FROM images
                GROUP BY day_index HAVING count(*)<>8 OR count(DISTINCT report_index)<>8
                OR min(report_index)<>1 OR max(report_index)<>8)''').fetchone()[0]
            require(invalid==0,'not exactly reports1..8 per day')
        check('planned day count and eight images per day',days)
        def timestamps():
            start = datetime.fromisoformat(part['start_date']+'T05:00:00')
            for table in ('logs','images'):
                columns = 'day_index,date,time_of_day' + (',report_index' if table=='images' else '')
                for row in connection.execute(f'SELECT {columns} FROM {table} ORDER BY day_index,date,time_of_day'):
                    index,d,t = row[:3]
                    stamp = datetime.fromisoformat(d+'T'+t)
                    beginning = start+timedelta(days=index-1)
                    require(d==stamp.date().isoformat() and t==stamp.strftime('%H:%M:%S'),'noncanonical time')
                    if table=='images':
                        require(stamp==beginning+timedelta(hours=3*row[3]),'report time inconsistent with day')
                    else:
                        require(beginning<=stamp<beginning+timedelta(days=1),'event outside simulation day')
        check('simulated dates and times consistent with day',timestamps)
        def logs():
            for token,zone,weather in connection.execute('SELECT DISTINCT event_name,zone,weather FROM logs'):
                require(token in TOKENS,'invalid event token')
                require(zone is None or zone in ZONE_TOKENS,'invalid zone')
                require(weather in {'hot','clear','overcast','rain'},'invalid weather')
                if token.startswith('ENTER_'):
                    require(ZONE_TOKENS.get(zone)==token,'entry zone mismatch')
            require(connection.execute('''SELECT count(*) FROM (SELECT day_index FROM logs
                GROUP BY day_index HAVING count(DISTINCT weather)<>1)''').fetchone()[0]==0,'weather changes within day')
        check('public vocabulary, zones and daily weather',logs)
        def pngs():
            size = json.loads(meta_path(database).read_text())['image_size']
            for (blob,) in connection.execute('SELECT image FROM images ORDER BY id'):
                valid_png(blob,size)
        check('every image is a complete valid PNG',pngs)
    if name=='test':
        check('test file read-only',lambda: require(not database.stat().st_mode & 0o222,'write permission remains'))
        check('test file standalone',lambda: require(not Path(str(database)+'-wal').exists(),'WAL file remains'))
    return checks


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--only',choices=('train','val','test'),help='diagnostic partial build only')
    args = parser.parse_args(argv)
    try:
        plan = read_plan(args.plan)
    except (ValueError,KeyError,OSError) as error:
        parser.exit(1,f'FAIL plan: {error}\n')
    print('PASS plan: distinct allowed seeds; fixed day counts; contiguous non-overlapping simulation-day ranges')
    results = [verify_split(args.plan,plan,name) for name in ((args.only,) if args.only else ('train','val','test'))]
    if not all(all(checks.values()) for checks in results):
        parser.exit(1,'FAIL dataset verification\n')
    print('PASS dataset verification (integrity only; test outcomes not inspected)')


if __name__ == '__main__':
    main()
