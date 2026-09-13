"""Build the teaching ZIP from an allow-list; never include private caches or student data."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parent.parent
TOP_FILES = ['README.md', '课程总体设计方案.md', 'requirements.txt', 'requirements.lock.txt',
             'requirements-models.lock.txt', 'requirements.container.txt', 'Dockerfile',
             'compose.yaml', '.gitignore', '.dockerignore', '.gitattributes']
DIRECTORIES = ['coursekit', 'docs', 'scripts', 'tests', '报告模板']


def main():
    files = [ROOT / name for name in TOP_FILES]
    directories = [ROOT / name for name in DIRECTORIES]
    directories.extend(p for p in ROOT.iterdir() if p.is_dir() and len(p.name) > 2 and p.name[:2].isdigit() and p.name[2] == '.')
    for directory in directories:
        files.extend(p for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    files = sorted(set(files))
    missing = [str(p) for p in files if not p.exists()]
    if missing:
        raise RuntimeError(f'Missing deliverable: {missing}')
    manifest = [{'file': str(p.relative_to(ROOT)).replace('\\', '/'), 'bytes': p.stat().st_size,
                 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2)
    # Write bytes so Windows newline translation cannot turn LF into CRLF.
    (ROOT / '交付文件清单.json').write_bytes(manifest_text.encode('utf-8'))
    path = ROOT / 'BDP_云计算与大数据处理_课程完整包.zip'
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            archive.write(file, 'BDP/' + file.relative_to(ROOT).as_posix())
        archive.writestr('BDP/交付文件清单.json', manifest_text)
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f'ZIP CRC check failed: {bad}')
    print(json.dumps({'archive': str(path), 'files': len(files) + 1, 'bytes': path.stat().st_size,
                      'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
