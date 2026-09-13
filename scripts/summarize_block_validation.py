"""Match executed evidence to the current distributable PowerShell source blocks.

No command is executed by this script. Successful records only count when their
source hash still matches the manual; failed attempts remain in the evidence.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.audit_docs import markdown_files
from scripts.block_runner import get_blocks, digest
from scripts.capture_validation import public_metadata

EVIDENCE = ROOT / 'outputs/full-validation'
GOOD = {'PASS', 'EXPECTED_FAILURE_VERIFIED'}

def norm(value):
    return str(value).replace('\\', '/')

def portable(value):
    path = Path(value)
    return norm(path.relative_to(EVIDENCE)) if path.is_relative_to(EVIDENCE) else norm(value)

def evidence_valid(row):
    """Require saved source/executed bytes and a real retained log, not just PASS."""
    try:
        source = Path(row['source_script'])
        executed = Path(row['executed_script'])
        log = Path(row['log_path'])
        return (source.is_file() and executed.is_file() and log.is_file()
                and digest(source.read_text(encoding='utf-8-sig')) == row['source_sha256']
                and digest(executed.read_text(encoding='utf-8-sig')) == row['executed_code_sha256'])
    except (KeyError, OSError, UnicodeError):
        return False

def main():
    records = {}
    # Per-block files preserve original attempts. Group summaries may contain
    # additional postcondition assertions and clarified native exit semantics.
    paths = [p for p in EVIDENCE.rglob('*.result.json') if 'course' not in p.relative_to(EVIDENCE).parts]
    paths += [p for p in EVIDENCE.rglob('results.json') if 'course' not in p.relative_to(EVIDENCE).parts]
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding='utf-8-sig'))
        except (ValueError, OSError):
            continue
        for row in data if isinstance(data, list) else [data]:
            if not isinstance(row, dict) or not {'source_file','block_number','log_path'} <= row.keys():
                continue
            key = norm(row['log_path'])
            records[key] = {**records.get(key, {}), **row}
    grouped = {}
    for row in records.values():
        grouped.setdefault((norm(row['source_file']),row['block_number']),[]).append(row)
    ledger = []
    for source in markdown_files():
        for number, code in enumerate(get_blocks(source), 1):
            source_name = source.relative_to(ROOT).as_posix()
            attempts = sorted(grouped.get((source_name,number),[]),key=lambda r:r.get('started_at',''))
            matching = [r for r in attempts if r.get('source_sha256') == digest(code)]
            good = [r for r in matching if r.get('status') in GOOD and evidence_valid(r)]
            # Prefer successful completed workflow over an extra negative probe.
            positive = [r for r in good if r.get('status') == 'PASS']
            eligible = positive or good
            unchanged = [r for r in eligible if r.get('executed_code_sha256') == digest(code)]
            selected = (unchanged or eligible or matching or attempts or [None])[-1]
            status = selected.get('status') if good else 'UNVERIFIED_CURRENT_SOURCE'
            no_op = not any(line.strip() and not line.lstrip().startswith('#') for line in code.splitlines())
            if no_op and good:
                status = 'PASS_NOOP_TEMPLATE'
            entry = {'id': len(ledger)+1,'source_file':source_name,'block_number':number,
                     'source_sha256':digest(code),'status':status,'attempt_count':len(attempts),
                     'current_source_attempts':len(matching),'comment_only':no_op}
            if selected:
                log = Path(selected['log_path'])
                entry.update(executed_code_sha256=selected.get('executed_code_sha256'),
                             source_was_substituted=selected.get('executed_code_sha256')!=digest(code),
                             expected_outcome=selected.get('expected_outcome'),exit_code=selected.get('exit_code'),
                             duration_seconds=selected.get('duration_seconds'),
                             substitutions=selected.get('substitutions',{}),
                             prerequisites=selected.get('prerequisites',''),
                             workdir=selected.get('workdir'),
                             observed_outcome=selected.get('observed_outcome'),
                             evidence_files_verified=evidence_valid(selected),
                             evidence_log=portable(log),
                             evidence_log_sha256=hashlib.sha256(log.read_bytes()).hexdigest() if log.exists() else None,
                             record_status=selected.get('status'))
            ledger.append(entry)
    summary = {'created_at':datetime.now(timezone.utc).isoformat(),
               'scope':'All distributable powershell fenced blocks, matched to current source hashes. A comment-only template is counted separately.',
               'blocks':len(ledger),'counts':dict(Counter(e['status'] for e in ledger)),
               'retained_attempt_records':len(records),'unverified':[e['id'] for e in ledger if e['status']=='UNVERIFIED_CURRENT_SOURCE']}
    target=ROOT/'控制文档/验证证据/powershell-block-coverage.json'
    published = public_metadata({'summary':summary,'blocks':ledger})
    published['summary']['path_redaction'] = 'Local user directories are shown as <USER_PROFILE>. Original paths and logs remain in the separate teacher evidence archive.'
    target.write_text(json.dumps(published,ensure_ascii=False,indent=2),encoding='utf-8')
    (EVIDENCE/'all-attempts.json').write_text(json.dumps(list(records.values()),ensure_ascii=False,indent=2),encoding='utf-8')
    rows=['# 全量 PowerShell 命令验证清单','',
          '这份清单由当前文档代码散列与真实执行记录匹配生成。更改代码块后，旧记录不会自动计为通过。完整日志、初次失败及复验过程保存在独立的《BDP_全量验证证据_教师留存.zip》中。','',
          'PASS 表示实际执行并满足该块的输出或产物检查；EXPECTED_FAILURE_VERIFIED 表示故障演示按预期拒绝；PASS_NOOP_TEMPLATE 仅表示注释模板可解析，不代表一次计算实验。人工操作、跨窗口环境和测试路径替换见全量验证报告。','',
          f'共 {len(ledger)} 个代码块；状态计数：`{json.dumps(summary["counts"],ensure_ascii=False)}`。','',
          '[机器可读清单](../验证证据/powershell-block-coverage.json) · [验证报告](全量验证报告.md)','',
          '| 编号 | 文档 | 块号 | 状态 | 当前源码 SHA256 前12位 |','|---|---|---:|---|---|']
    for row in ledger:
        link=quote('../../'+row['source_file'],safe='/')
        rows.append(f'| {row["id"]:03d} | [{row["source_file"]}]({link}) | {row["block_number"]} | {row["status"]} | `{row["source_sha256"][:12]}` |')
    (ROOT/'控制文档/验证记录/全量命令验证清单.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    if summary['unverified']:
        raise SystemExit(1)

if __name__=='__main__': main()
