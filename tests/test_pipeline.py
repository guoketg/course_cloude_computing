import sqlite3
import pytest
from coursekit.pipeline import validate_event, apply_batch


def sample(**updates):
    return dict(event_id='e1', event_time='2026-03-01T00:00:00+00:00', service='search',
                model='small', input_tokens=10, output_tokens=3, latency_ms=50, status='ok', **updates)


@pytest.fixture
def db(tmp_path):
    conn = sqlite3.connect(tmp_path / 'events.sqlite')
    conn.executescript('''CREATE TABLE events(event_id TEXT PRIMARY KEY,event_time TEXT,service TEXT,
        model TEXT,input_tokens INTEGER,output_tokens INTEGER,latency_ms INTEGER,status TEXT);
        CREATE TABLE checkpoint(id INTEGER PRIMARY KEY,offset INTEGER);''')
    yield conn
    conn.close()


def test_contract_rejects_bool_and_naive_timestamp():
    row = sample()
    assert validate_event(row) is None
    row['input_tokens'] = True
    assert validate_event(row) == 'invalid_input_tokens'
    row['input_tokens'] = 10
    row['event_time'] = '2026-03-01T00:00:00'
    assert validate_event(row) == 'non_utc_time'


def test_replay_effect_and_checkpoint_are_atomic(db):
    assert apply_batch(db, [sample()], 1) == 1
    assert apply_batch(db, [sample()], 1) == 0
    next_row = {**sample(), 'event_id': 'e2'}
    with pytest.raises(RuntimeError, match='INJECTED'):
        apply_batch(db, [next_row], 2, fail_before_commit=True)
    assert db.execute('SELECT COUNT(*) FROM events').fetchone()[0] == 1
    assert db.execute('SELECT offset FROM checkpoint').fetchone()[0] == 1
    assert apply_batch(db, [next_row], 2) == 1


def test_conflicting_duplicate_cannot_silently_change_a_fact(db):
    apply_batch(db, [sample()], 1)
    with pytest.raises(ValueError, match='Conflicting'):
        apply_batch(db, [{**sample(), 'input_tokens': 999}], 2)
    assert db.execute('SELECT input_tokens FROM events').fetchone()[0] == 10
    assert db.execute('SELECT offset FROM checkpoint').fetchone()[0] == 1
