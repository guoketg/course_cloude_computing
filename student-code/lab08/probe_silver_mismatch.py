"""实验 08 §9 负例：用临时文件演示 silver 哈希失配，不破坏主数据。

预测：若只改动 Parquet 文件而不重跑实验04，manifest 与 latest.json 都不会更新，
silver_lineage_check 会在第一个比较 `actual == manifest['silver_sha256']` 失败。
"""
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from coursekit.governance import require_check  # noqa: E402

DATA = ROOT / 'data'


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def mismatched_lineage_check(manifest_path: Path, silver_path: Path, latest_path: Path):
    """复刻 silver_lineage_check 的比较顺序，但作用于临时副本。"""
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    actual = sha256_file(silver_path)
    require_check(actual == manifest['silver_sha256'],
                  f"silver parquet与manifest失配: actual={actual} manifest={manifest['silver_sha256']}")
    latest = json.loads(latest_path.read_text(encoding='utf-8'))
    require_check(latest['source_sha256'] == actual,
                  f"latest.json source_sha256与silver哈希失配: latest={latest['source_sha256']} actual={actual}")
    return actual


def main() -> int:
    with tempfile.TemporaryDirectory(prefix='silver_mismatch_') as tmp:
        tmpdir = Path(tmp)
        manifest_dst = tmpdir / 'silver.json'
        silver_dst = tmpdir / 'events.parquet'
        latest_dst = tmpdir / 'latest.json'

        shutil.copyfile(DATA / 'manifests/silver.json', manifest_dst)
        shutil.copyfile(DATA / 'silver/events.parquet', silver_dst)
        shutil.copyfile(DATA / 'state/latest.json', latest_dst)

        before = sha256_file(silver_dst)

        # 1) 篡改前：临时副本三方一致，检查通过
        ok = mismatched_lineage_check(manifest_dst, silver_dst, latest_dst)
        print(f'BEFORE_PASS actual={ok}')

        # 2) 只改动 Parquet 副本（追加 4 字节），不重跑实验04 → manifest/latest 不变
        with silver_dst.open('ab') as f:
            f.write(b'\x00\x01\x02\x03')
        after = sha256_file(silver_dst)
        print(f'TAMPERED actual_before={before} actual_after={after} changed={before != after}')

        # 3) 预期失败：应在第一个比较处失配
        try:
            mismatched_lineage_check(manifest_dst, silver_dst, latest_dst)
        except ValueError as e:
            print(f'EXPECTED_FAILURE: {e}')
            first_compare_failed = 'manifest' in str(e)
            print(f'FAILS_AT_FIRST_COMPARE={first_compare_failed}')
        else:
            print('ERROR: 失配未被检出')
            return 1

        # 4) 主数据未被破坏
        main_hash = sha256_file(DATA / 'silver/events.parquet')
        main_manifest = json.loads((DATA / 'manifests/silver.json').read_text(encoding='utf-8'))
        assert main_hash == main_manifest['silver_sha256'], '主数据被意外修改！'
        print(f'MAIN_DATA_INTACT {main_hash}')
        print('SILVER_MISMATCH_PROBE_PASS')
        return 0


if __name__ == '__main__':
    sys.exit(main())
