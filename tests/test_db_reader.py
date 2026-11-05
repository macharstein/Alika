import pickle
import sqlite3
from unittest.mock import Mock

import pytest

from lionsim import db_reader
from lionsim.sqlite_common import SCHEMA


def test_streams_only_one_batch(monkeypatch):
    connection=Mock()
    cursor=connection.execute.return_value
    cursor.fetchmany.side_effect=[[(1,),(2,)],[(3,)],[]]
    monkeypatch.setattr(db_reader,'read_only',lambda db:connection)
    rows=db_reader.iter_logs('unused',(1,2),batch_size=2)
    assert next(rows)==(1,)
    assert cursor.fetchmany.call_count==1
    assert next(rows)==(2,)
    assert cursor.fetchmany.call_count==1
    assert list(rows)==[(3,)]
    assert all(call.args==(2,) for call in cursor.fetchmany.call_args_list)
    cursor.fetchall.assert_not_called()
    connection.close.assert_called_once()


def test_days_aggregate_without_blobs(monkeypatch):
    connection=Mock()
    cursor=connection.execute.return_value
    cursor.fetchmany.side_effect=[[(1,8,20)],[]]
    monkeypatch.setattr(db_reader,'read_only',lambda db:connection)
    assert list(db_reader.iter_days('unused',batch_size=1))==[(1,8,20)]
    sql=connection.execute.call_args.args[0]
    assert 'GROUP BY' in sql and 'SELECT image ' not in sql
    cursor.fetchall.assert_not_called()


def test_lazy_image_dataset_one_blob_per_access(tmp_path):
    db=tmp_path/'tiny.db'
    with sqlite3.connect(db) as con:
        con.executescript(SCHEMA)
        con.executemany('INSERT INTO images VALUES(?,?,?,?,?,?)',[
            (1,1,'2026-01-01','08:00:00',1,b'one'),(2,1,'2026-01-01','11:00:00',2,b'two')])
    dataset=db_reader.ImageDataset(db)
    assert dataset._connection is None
    assert len(dataset)==2
    trace=[]
    dataset._connection.set_trace_callback(trace.append)
    assert dataset[1]['image']==b'two'
    assert len(trace)==1 and 'LIMIT 1 OFFSET 1' in trace[0]
    with pytest.raises(sqlite3.OperationalError):
        dataset._connection.execute('DELETE FROM images')
    clone=pickle.loads(pickle.dumps(dataset))
    assert clone._connection is None
    assert clone[-1]['image']==b'two'
    with pytest.raises(IndexError):
        clone[2]
    with pytest.raises(KeyError):
        db_reader.get_image(db,3)
    assert db_reader.get_image(db,1)==b'one'
    dataset.close(); clone.close()
