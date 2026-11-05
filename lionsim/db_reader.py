"""Read-only, bounded-memory SQLite access; no training framework dependency."""
from __future__ import annotations

from contextlib import closing
import os
import operator
import sqlite3

from .sqlite_common import read_only


def iter_logs(db, day_range=None, batch_size=256):
    """Yield public log tuples, fetching at most batch_size rows at a time.

    day_range=(first,last) is inclusive. Connection closes on exhaustion/close().
    """
    if batch_size < 1:
        raise ValueError('batch_size must be positive')
    sql = 'SELECT id,day_index,date,time_of_day,event_name,zone,weather FROM logs'
    parameters = ()
    if day_range is not None:
        first,last = day_range
        if first > last:
            raise ValueError('reversed day range')
        sql += ' WHERE day_index BETWEEN ? AND ?'
        parameters = (first,last)
    sql += ' ORDER BY day_index,date,time_of_day,id'
    with closing(read_only(db)) as connection:
        cursor = connection.execute(sql,parameters)
        while True:
            batch = cursor.fetchmany(batch_size)
            if not batch:
                break
            yield from batch


def iter_days(db, batch_size=128):
    """Yield (day_index, image_count, log_count) using SQL aggregation only."""
    if batch_size < 1:
        raise ValueError('batch_size must be positive')
    with closing(read_only(db)) as connection:
        cursor = connection.execute('''SELECT i.day_index,count(*),
            (SELECT count(*) FROM logs l WHERE l.day_index=i.day_index)
            FROM images i GROUP BY i.day_index ORDER BY i.day_index''')
        while True:
            batch = cursor.fetchmany(batch_size)
            if not batch:
                break
            yield from batch


def get_image(db, image_id):
    """Return one PNG byte string by its primary key; missing ID raises KeyError."""
    with closing(read_only(db)) as connection:
        row = connection.execute('SELECT image FROM images WHERE id=?',(image_id,)).fetchone()
        if row is None:
            raise KeyError(image_id)
        return row[0]


class ImageDataset:
    """Map-style dataset returning one row dict (including PNG bytes) per access.

    Connection is opened lazily in the accessing process, read-only. Pickling
    discards connections so independent loader workers open their own handles.
    """
    def __init__(self, db):
        self.db = str(db)
        self._connection = None
        self._pid = None

    def _connect(self):
        if self._connection is None or self._pid != os.getpid():
            self.close()
            self._connection = read_only(self.db)
            self._connection.row_factory = sqlite3.Row
            self._pid = os.getpid()
        return self._connection

    def __len__(self):
        return self._connect().execute('SELECT count(*) FROM images').fetchone()[0]

    def __getitem__(self, index):
        index = operator.index(index)
        if index < 0:
            index += len(self)
        if index < 0:
            raise IndexError(index)
        row = self._connect().execute(
            'SELECT id,day_index,date,time_of_day,report_index,image FROM images '
            'ORDER BY id LIMIT 1 OFFSET ?', (index,)).fetchone()
        if row is None:
            raise IndexError(index)
        return dict(row)

    def close(self):
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            self._pid = None

    def __getstate__(self):
        return {'db':self.db, '_connection':None, '_pid':None}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
