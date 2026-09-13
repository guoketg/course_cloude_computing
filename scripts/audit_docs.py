"""Check student Markdown links and PowerShell block syntax (no execution)."""
import argparse
from pathlib import Path
import json
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
EXCLUDE = {'.venv', '.references', '.git', 'data', 'outputs', '.pytest_cache', 'models', 'submissions'}


def markdown_files(include_control=False):
    return sorted(
        p for p in ROOT.rglob('*.md')
        if not any(x in EXCLUDE or x.startswith('.test-tmp') for x in p.relative_to(ROOT).parts)
        and (include_control or '控制文档' not in p.relative_to(ROOT).parts)
    )


def main():
    parser = argparse.ArgumentParser(description='Audit local links and PowerShell fences')
    parser.add_argument('--include-control', action='store_true',
                        help='also audit teacher and maintainer documents under 控制文档')
    args = parser.parse_args()
    files = markdown_files(args.include_control)
    missing, ps_blocks, manuals = [], [], []
    for path in files:
        content = path.read_text(encoding='utf-8-sig')
        for target in re.findall(r'\]\((<[^>]+>|[^)]+)\)', content):
            target = unquote(target.strip('<>').split('#', 1)[0])
            if not target or re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                continue
            if not (path.parent / target).exists():
                missing.append({'source': str(path.relative_to(ROOT)), 'target': target})
        for number, block in enumerate(re.findall(r'```powershell\s*\n(.*?)\n```', content, re.S), 1):
            ps_blocks.append({'file': str(path.relative_to(ROOT)), 'block': number, 'code': block})
        if path.name == '实验手册.md':
            manuals.append({'file': str(path.relative_to(ROOT)), 'lines': len(content.splitlines()), 'chars': len(content)})
    out = ROOT / 'outputs/doc-audit'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'powershell-blocks.json').write_text(json.dumps(ps_blocks, ensure_ascii=False), encoding='utf-8')
    summary = {'scope': 'repository' if args.include_control else 'student',
               'manuals': manuals, 'markdown_files': len(files),
               'powershell_blocks': len(ps_blocks), 'missing_links': missing}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if missing:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
