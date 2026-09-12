"""Preserve actual instructor outputs for an auditable teaching release."""
from pathlib import Path
import hashlib
import json
import platform
import re
from datetime import datetime, timezone
import importlib.metadata

ROOT = Path(__file__).resolve().parent.parent


def public_metadata(value):
    """Redact local user directories in public summaries; keep raw logs untouched."""
    if isinstance(value, str):
        return re.sub(r'(?i)\b[A-Z]:[/\\]+Users[/\\]+[^/\\\r\n\"\'<>]+', '<USER_PROFILE>', value)
    if isinstance(value, list):
        return [public_metadata(item) for item in value]
    if isinstance(value, dict):
        return {public_metadata(key): public_metadata(item) for key, item in value.items()}
    return value


def main():
    paths = [
        'outputs/lab01/storage.json', 'outputs/lab02/quality.json', 'outputs/lab02/quarantine.json',
        'outputs/lab03/benchmark-w1-p8.json', 'outputs/lab03/benchmark-w2-p8.json',
        'outputs/lab04/replay.json', 'outputs/lab05/retrieval_lexical.json',
        'outputs/lab05/retrieval_semantic.json', 'outputs/lab06/evaluation_dev_extractive.json',
        'outputs/lab06/evaluation_test_extractive.json', 'outputs/lab06/evaluation_dev_semantic_extractive.json',
        'outputs/lab06/evaluation_dev_ollama.json', 'outputs/lab06/evaluation_test_ollama.json',
        'outputs/lab07/load_test.json', 'outputs/lab08/release_checks.json',
        'outputs/local-model-probe/result.json',
    ]
    target = ROOT / 'docs/validation-evidence'
    target.mkdir(parents=True, exist_ok=True)
    files = []
    for relative in paths:
        path = ROOT / relative
        if not path.exists():
            raise FileNotFoundError(f'Run actual validation first: {relative}')
        destination = target / (path.parent.name + '-' + path.name)
        destination.write_text(json.dumps(public_metadata(json.loads(path.read_text(encoding='utf-8-sig'))),
                                          ensure_ascii=False, indent=2), encoding='utf-8')
        files.append({'source': relative, 'file': destination.name,
                      'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                      'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()})
    packages = ['duckdb', 'pyarrow', 'dask', 'distributed', 'moto', 'fastapi', 'uvicorn',
                'numpy', 'sentence-transformers', 'torch', 'transformers', 'huggingface-hub']
    report = {'captured_at_utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
              'platform': platform.platform(), 'packages': {p: importlib.metadata.version(p) for p in packages},
              'evidence': files, 'note': 'Actual instructor artifacts, not student submission evidence. Public summaries replace local user directories with <USER_PROFILE>; raw outputs remain unchanged.'}
    (target / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Preserved {len(files)} instructor evidence files')


if __name__ == '__main__':
    main()
