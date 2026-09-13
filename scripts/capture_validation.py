"""Preserve base or default-model instructor evidence without overwriting history."""
import argparse
from pathlib import Path
import hashlib
import json
import platform
import re
import sys
from datetime import datetime, timezone
import importlib.metadata

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from coursekit.model_config import (
    BGE_MODEL_ID,
    BGE_REVISION,
    BGE_SOURCE_REVISION,
    DEFAULT_OLLAMA_CONTEXT,
    DEFAULT_OLLAMA_GPU_LAYERS,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_PREDICT,
    GENERATION_GGUF_BYTES,
    GENERATION_GGUF_FILE,
    GENERATION_GGUF_SHA256,
    GENERATION_QUANTIZATION,
    GENERATION_REPO_ID,
    GENERATION_REPO_REVISION,
    GENERATION_SOURCE_REVISION,
    MODELSCOPE_ENDPOINT,
)

BASE_PATHS = [
    'outputs/lab01/storage.json', 'outputs/lab02/quality.json', 'outputs/lab02/quarantine.json',
    'outputs/lab03/benchmark-w1-p8.json', 'outputs/lab03/benchmark-w2-p8.json',
    'outputs/lab04/replay.json', 'outputs/lab05/retrieval_lexical.json',
    'outputs/lab06/evaluation_dev_extractive.json', 'outputs/lab06/evaluation_test_extractive.json',
    'outputs/lab07/load_test.json', 'outputs/lab08/release_checks.json',
]
DEFAULT_MODEL_PATHS = BASE_PATHS + [
    'outputs/lab05/retrieval_semantic.json',
    'outputs/lab06/evaluation_dev_ollama.json', 'outputs/lab06/evaluation_test_ollama.json',
    'outputs/local-model-probe/result.json',
    'models/embedding-manifest.json', 'models/generation-manifest.json',
]
BASE_PACKAGES = ['duckdb', 'pyarrow', 'dask', 'distributed', 'moto', 'fastapi', 'uvicorn', 'numpy']
MODEL_PACKAGES = ['sentence-transformers', 'torch', 'transformers', 'huggingface-hub']


def public_metadata(value):
    """Redact local user directories in public summaries; keep raw logs untouched."""
    if isinstance(value, str):
        return re.sub(r'(?i)\b[A-Z]:[/\\]+Users[/\\]+[^/\\\r\n\"\'<>]+', '<USER_PROFILE>', value)
    if isinstance(value, list):
        return [public_metadata(item) for item in value]
    if isinstance(value, dict):
        return {public_metadata(key): public_metadata(item) for key, item in value.items()}
    return value


def package_versions(names):
    versions = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def implementation_versions(checkout: Path, profile: str):
    paths = sorted((checkout / 'coursekit').glob('*.py'))
    paths.extend([checkout / 'scripts/capture_validation.py', checkout / 'scripts/run-baseline.ps1'])
    if profile == 'default-model':
        paths.extend([
            checkout / 'scripts/prepare_embedding.py',
            checkout / 'scripts/prepare_generation.py',
            checkout / 'scripts/artifact_manifest.py',
        ])
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f'Validation implementation file missing: {missing}')
    return [
        {'file': path.relative_to(checkout).as_posix(), 'sha256': file_sha256(path)}
        for path in paths
    ]


def validate_default_model(root: Path, model_root: Path | None = None):
    model_root = model_root or root
    generation = json.loads((model_root / 'models/generation-manifest.json').read_text(encoding='utf-8-sig'))
    expected_generation = {
        'repo_id': GENERATION_REPO_ID, 'repo_revision': GENERATION_REPO_REVISION,
        'source_repo_id': GENERATION_REPO_ID, 'source_revision': GENERATION_SOURCE_REVISION,
        'filename': GENERATION_GGUF_FILE, 'quantization': GENERATION_QUANTIZATION,
        'artifact_bytes': GENERATION_GGUF_BYTES, 'artifact_sha256': GENERATION_GGUF_SHA256,
        'ollama_tag': DEFAULT_OLLAMA_MODEL,
        'source_reference_url': (
            f'{MODELSCOPE_ENDPOINT}/models/{GENERATION_REPO_ID}/resolve/'
            f'{GENERATION_SOURCE_REVISION}/{GENERATION_GGUF_FILE}'
        ),
    }
    for key, value in expected_generation.items():
        if generation.get(key) != value:
            raise RuntimeError(f'Default generation manifest mismatch for {key}')
    if not generation.get('ollama_digest'):
        raise RuntimeError('Default generation manifest lacks the imported Ollama digest')
    gguf = model_root / 'models/qwen35' / GENERATION_GGUF_FILE
    if not gguf.is_file() or gguf.stat().st_size != GENERATION_GGUF_BYTES or file_sha256(gguf) != GENERATION_GGUF_SHA256:
        raise RuntimeError('Default generation GGUF is missing or does not match the frozen SHA256')
    if generation.get('runtime_defaults') != {
        'think': False, 'num_ctx': DEFAULT_OLLAMA_CONTEXT,
        'num_predict': DEFAULT_OLLAMA_PREDICT, 'num_gpu': DEFAULT_OLLAMA_GPU_LAYERS,
    }:
        raise RuntimeError('Default generation manifest runtime settings differ from the release profile')
    modelfile = model_root / 'models/qwen35/Modelfile'
    if not modelfile.is_file() or file_sha256(modelfile) != generation.get('modelfile_sha256'):
        raise RuntimeError('Default generation Modelfile is missing or does not match its manifest')
    embedding = json.loads((model_root / 'models/embedding-manifest.json').read_text(encoding='utf-8-sig'))
    if (embedding.get('model_id') != BGE_MODEL_ID
            or embedding.get('upstream_revision') != BGE_REVISION
            or embedding.get('source_revision') != BGE_SOURCE_REVISION):
        raise RuntimeError(f'Default embedding manifest must use frozen {BGE_MODEL_ID}')
    if not embedding.get('files'):
        raise RuntimeError('Default embedding manifest has no files')
    revision_input = []
    for item in embedding.get('files', []):
        path = model_root / 'models/bge-small-zh-v1.5' / item['path']
        if (not path.is_file() or path.stat().st_size != item.get('bytes')
                or file_sha256(path) != item['sha256']):
            raise RuntimeError(f'Default BGE artifact mismatch: {item["path"]}')
        revision_input.append(item['path'] + item['sha256'])
    directory_revision = hashlib.sha256(''.join(revision_input).encode()).hexdigest()
    if embedding.get('directory_revision') != directory_revision:
        raise RuntimeError('Default embedding directory revision does not match its files')
    semantic = json.loads((root / 'outputs/lab05/retrieval_semantic.json').read_text(encoding='utf-8-sig'))
    if semantic.get('mode') != 'semantic' or semantic.get('model_revision') != embedding['directory_revision']:
        raise RuntimeError('Default-model profile requires a real semantic retrieval result')
    probe = json.loads((root / 'outputs/local-model-probe/result.json').read_text(encoding='utf-8-sig'))
    if probe.get('mode') != 'semantic' or probe.get('model_revision') != embedding['directory_revision']:
        raise RuntimeError('Default BGE probe does not match the frozen directory revision')
    retrieval_identities = set()
    for name in ('evaluation_dev_ollama.json', 'evaluation_test_ollama.json'):
        report = json.loads((root / 'outputs/lab06' / name).read_text(encoding='utf-8-sig'))
        retrieval_identity = (
            report.get('retrieval_mode'), report.get('embedding_model_id'),
            report.get('embedding_model_revision'), report.get('index_version'),
        )
        allowed_retrievals = {
            ('lexical', 'character-bigram-tfidf', 'coursekit-v1'),
            ('semantic', BGE_MODEL_ID, embedding['directory_revision']),
        }
        if retrieval_identity[:3] not in allowed_retrievals or not retrieval_identity[3]:
            raise RuntimeError(f'{name} does not identify a validated lexical or frozen-BGE index')
        retrieval_identities.add(retrieval_identity)
        model_ids = {row.get('result', {}).get('model_id') for row in report.get('details', [])
                     if row.get('result', {}).get('model_id')}
        if model_ids != {DEFAULT_OLLAMA_MODEL}:
            raise RuntimeError(f'{name} does not contain only {DEFAULT_OLLAMA_MODEL}: {sorted(model_ids)}')
        digests = {row.get('result', {}).get('model_digest') for row in report.get('details', [])
                   if row.get('result', {}).get('model_id')}
        if digests != {generation['ollama_digest']}:
            raise RuntimeError(f'{name} digest does not match the imported default model')
    if len(retrieval_identities) != 1:
        raise RuntimeError('Default dev/test Ollama evaluations do not use the same retrieval index')


def capture(profile: str, root: Path = ROOT, target_root: Path | None = None,
            model_root: Path | None = None):
    if profile not in {'base', 'default-model'}:
        raise ValueError('profile must be base or default-model')
    paths = BASE_PATHS if profile == 'base' else DEFAULT_MODEL_PATHS
    target_root = target_root or root / 'docs/validation-evidence'
    model_root = model_root or root
    target = target_root / profile
    target.mkdir(parents=True, exist_ok=True)
    if profile == 'default-model':
        validate_default_model(root, model_root)
    files = []
    for relative in paths:
        path = (model_root if relative.startswith('models/') else root) / relative
        if not path.exists():
            raise FileNotFoundError(f'Run actual validation first: {relative}')
        destination = target / (path.parent.name + '-' + path.name)
        destination.write_bytes(json.dumps(
            public_metadata(json.loads(path.read_text(encoding='utf-8-sig'))),
            ensure_ascii=False, indent=2,
        ).encode('utf-8'))
        files.append({'source': relative, 'file': destination.name,
                      'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                      'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()})
    packages = BASE_PACKAGES + (MODEL_PACKAGES if profile == 'default-model' else [])
    report = {'captured_at_utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
              'platform': platform.platform(), 'profile': profile, 'packages': package_versions(packages),
              'implementation': implementation_versions(model_root, profile),
              'evidence': files,
              'note': 'Current instructor evidence stored in a profile directory; legacy root evidence is not overwritten. Public summaries replace local user directories with <USER_PROFILE>.'}
    manifest_path = target / 'manifest.json'
    manifest_path.write_bytes(json.dumps(report, ensure_ascii=False, indent=2).encode('utf-8'))
    return {'profile': profile, 'files': len(files), 'manifest': str(manifest_path)}


def main():
    parser = argparse.ArgumentParser(description='Capture current base or default-model validation evidence')
    parser.add_argument('--profile', choices=['base', 'default-model'], default='base')
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--model-root', type=Path,
                        help='Course checkout containing models; defaults to the checkout when source-root is isolated')
    parser.add_argument('--target-root', type=Path)
    args = parser.parse_args()
    model_root = args.model_root.resolve() if args.model_root else ROOT
    result = capture(args.profile, args.source_root.resolve(),
                     args.target_root.resolve() if args.target_root else None, model_root)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
