"""Only shared paths, UTF-8 I/O and evidence envelopes; no hidden pipeline work."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get('BDP_ROOT', Path(__file__).resolve().parent.parent)).resolve()
DATA = ROOT / 'data'
OUT = ROOT / 'outputs'


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def emit(lab, stage, payload):
    identity = read_json(ROOT / 'student.json') if (ROOT / 'student.json').exists() else {'student_id': 'UNREGISTERED'}
    student = identity['student_id']
    envelope = {
        'STUDENT_ID': student, 'EXPERIMENT_ID': str(lab).zfill(2),
        'IDENTITY_CODE': hashlib.sha256(f'{student}:{lab}'.encode()).hexdigest()[:12],
        'CAPTURED_AT': datetime.now(timezone.utc).isoformat(), 'stage': stage, 'result': payload,
    }
    print(json.dumps(envelope, ensure_ascii=False, indent=2, default=str))
    return payload
