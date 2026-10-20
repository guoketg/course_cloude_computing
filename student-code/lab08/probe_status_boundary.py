"""实验 08 §10 观察：审查状态是治理边界（全部在临时副本中进行，不改主数据）。

预测：把 untrusted 的 status 从 quarantined 改为 approved 后重建临时索引，
INJECTION_SENTINEL_42 会进入索引并可被检索到——因为 latest_documents() 只按
status 字段过滤，程序信任"由可信流程写入的状态"这一假设被破坏。
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from coursekit.intelligence import SOURCE, build_index, read_jsonl, search, sha256  # noqa: E402

SENTINEL = 'INJECTION_SENTINEL_42'
DOC_ID = 'untrusted'


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows),
                    encoding='utf-8')


def main() -> int:
    print('PREDICTION: 该资料会进入索引；被破坏的假设是'
          '"status 字段由可信审查流程写入，外部上传者不能自报 approved"。')
    original_bytes = SOURCE.read_bytes()
    rows = read_jsonl(SOURCE)
    target = next(r for r in rows if r['doc_id'] == DOC_ID)
    print(f'ORIGINAL_STATUS {target["status"]}')

    with tempfile.TemporaryDirectory(prefix='status_boundary_') as tmp:
        tmpdir = Path(tmp)
        source = tmpdir / 'documents.jsonl'
        index_path = tmpdir / 'knowledge.json'

        # 1) 临时副本：quarantined -> approved，重建索引
        approved_rows = [dict(r, status='approved') if r['doc_id'] == DOC_ID else r for r in rows]
        write_rows(source, approved_rows)
        index = build_index(source, index_path)
        in_index = any(c['doc_id'] == DOC_ID for c in index['chunks'])
        print(f'APPROVED_INDEX_ACTIVE={index["active_documents"]} UNTRUSTED_IN_INDEX={in_index}')

        # 2) 查询特殊标记（仅本机检索/摘录，不执行资料中的任何指令）
        hits = search(SENTINEL, role='public', k=5, index=index)
        leaked = [h for h in hits if h['doc_id'] == DOC_ID or SENTINEL in (h['title'] + h['text'])]
        print(f'APPROVED_QUERY_TOP1={hits[0]["doc_id"] if hits else None} '
              f'SENTINEL_HIT={bool(leaked)}')
        if leaked:
            print(f'EXTRACT_ONLY: 命中资料含哨兵标记，按摘录处理，不执行其中指令。')

        # 3) 改回 quarantined，重建，确认不再命中
        write_rows(source, rows)
        index2 = build_index(source, index_path)
        in_index2 = any(c['doc_id'] == DOC_ID for c in index2['chunks'])
        hits2 = search(SENTINEL, role='public', k=5, index=index2)
        leaked2 = [h for h in hits2 if h['doc_id'] == DOC_ID or SENTINEL in (h['title'] + h['text'])]
        print(f'QUARANTINED_INDEX_ACTIVE={index2["active_documents"]} '
              f'UNTRUSTED_IN_INDEX={in_index2} SENTINEL_HIT={bool(leaked2)}')

        assert in_index and leaked, 'approved 状态下资料未进入索引，观察不符'
        assert not in_index2 and not leaked2, 'quarantined 状态下仍命中，隔离失效'

    # 4) 主工作区未被改动
    assert SOURCE.read_bytes() == original_bytes, '主语料被意外修改！'
    print(f'MAIN_SOURCE_INTACT {sha256(SOURCE)}')
    print('STATUS_BOUNDARY_OBSERVATION_PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
