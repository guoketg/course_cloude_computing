"""Prepare an ordinary, portable model directory on the teacher's connected PC."""
from pathlib import Path
import hashlib
import json
import shutil
from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parent.parent
MODEL_ID = 'BAAI/bge-small-zh-v1.5'
REVISION = '7999e1d3359715c523056ef9478215996d62a620'


def main():
    snapshot = Path(snapshot_download(MODEL_ID, revision=REVISION,
                    allow_patterns=['*.json', '*.txt', 'model.safetensors'],
                    ignore_patterns=['onnx/*', 'openvino/*']))
    target = ROOT / 'models/bge-small-zh-v1.5'
    files = []
    for source in sorted(snapshot.rglob('*')):
        if not source.is_file() or any(p.startswith('.') for p in source.relative_to(snapshot).parts):
            continue
        relative = source.relative_to(snapshot)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Copy file content: do not depend on Windows symlink privileges or external cache layout.
        shutil.copyfile(source, destination)
        files.append({'path': relative.as_posix(), 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()})
    if not (target / 'model.safetensors').exists():
        raise RuntimeError('Required safetensors weight missing')
    manifest = {'model_id': MODEL_ID, 'upstream_revision': REVISION, 'files': files,
                'purpose': 'Teacher may distribute this verified model directory separately from the small course ZIP.'}
    (ROOT / 'models/embedding-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'MODEL_DIRECTORY={target}')
    print(f'FILES={len(files)}')


if __name__ == '__main__':
    main()
