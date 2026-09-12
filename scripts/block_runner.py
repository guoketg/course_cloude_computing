"""Execute a documented PowerShell block and retain its exact source, log and assertions.

This is a teacher QA tool, not an alternative student workflow. Prelude/path changes
are recorded explicitly. Windows PowerShell 5.1 is the default; no UTF-8 stdin
override is injected, so the manual must supply one if its Python pipe needs it.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from datetime import datetime, timezone

PROJECT = Path(__file__).resolve().parent.parent
POWERSHELL = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'


def digest(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def get_blocks(source: str | Path) -> list[str]:
    return re.findall(r'```powershell\s*\n(.*?)\n```', Path(source).read_text(encoding='utf-8-sig'), re.S)


def prepare(source, block_number, workdir, outdir, substitutions=None, prelude='', shell=None):
    source, workdir, outdir = Path(source).resolve(), Path(workdir).resolve(), Path(outdir).resolve()
    original = get_blocks(source)[block_number - 1]
    code = original
    for old, new in (substitutions or {}).items():
        code = code.replace(old, new)
    outdir.mkdir(parents=True, exist_ok=True)
    prefix = outdir / f'block-{block_number:02d}'
    prefix.with_suffix('.source.ps1').write_text(original, encoding='utf-8-sig')
    prefix.with_suffix('.executed.ps1').write_text(code, encoding='utf-8-sig')
    quote = lambda s: "'" + str(s).replace("'", "''") + "'"
    # Dot sourcing preserves PowerShell variable scope inside a block. Stdout is
    # encoded explicitly for the evidence log, but $OutputEncoding is untouched.
    wrapper = '\n'.join([
        "$ErrorActionPreference = 'Stop'",
        '[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)',
        f'Set-Location -LiteralPath {quote(workdir)}',
        prelude,
        '$global:LASTEXITCODE = 0',
        'try {',
        # Flush PowerShell's deferred object formatter before the explicit exit;
        # otherwise a short Invoke-RestMethod-only block can lose its displayed output.
        f'    . {quote(prefix.with_suffix(".executed.ps1"))} | Out-Default',
        '    exit $global:LASTEXITCODE',
        '} catch {',
        '    $_ | Format-List * -Force | Out-String | Write-Output',
        '    exit 101',
        '}',
    ])
    wrapper_path = prefix.with_suffix('.runner.ps1')
    wrapper_path.write_text(wrapper, encoding='utf-8-sig')
    relative = str(source.relative_to(PROJECT)) if source.is_relative_to(PROJECT) else str(source)
    record = {
        'source_file': relative, 'block_number': block_number,
        'source_sha256': digest(original), 'executed_code_sha256': digest(code),
        'substitutions': substitutions or {}, 'prerequisites': prelude,
        'workdir': str(workdir), 'shell': str(shell or POWERSHELL),
        'log_path': str(prefix.with_suffix('.log')),
        'source_script': str(prefix.with_suffix('.source.ps1')),
        'executed_script': str(prefix.with_suffix('.executed.ps1')),
        'started_at': datetime.now(timezone.utc).isoformat(),
    }
    return [str(shell or POWERSHELL), '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(wrapper_path)], record, prefix


def execute_block(source, block_number, workdir, outdir, *, substitutions=None, prelude='',
                  expected_exit_codes=(0,), expected_patterns=(), forbidden_patterns=(),
                  expected_outcome='Command completes and its expected output is observed', timeout=600,
                  shell=None):
    command, record, prefix = prepare(source, block_number, workdir, outdir, substitutions, prelude, shell)
    started = time.perf_counter()
    try:
        completed = subprocess.run(command, cwd=workdir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   timeout=timeout, check=False)
        log = completed.stdout.decode('utf-8', errors='replace')
        code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        log = (exc.stdout or b'').decode('utf-8', errors='replace') + '\nBLOCK TIMEOUT\n'
        code = -999
    prefix.with_suffix('.log').write_text(log, encoding='utf-8')
    patterns = {p: bool(re.search(p, log, re.S)) for p in expected_patterns}
    forbidden = {p: bool(re.search(p, log, re.S)) for p in forbidden_patterns}
    passed = code in expected_exit_codes and all(patterns.values()) and not any(forbidden.values())
    record.update(exit_code=code, expected_exit_codes=list(expected_exit_codes),
                  expected_outcome=expected_outcome, observed_outcome={'expected_patterns': patterns, 'forbidden_patterns': forbidden},
                  status=('PASS' if code == 0 else 'EXPECTED_FAILURE_VERIFIED') if passed else 'FAIL',
                  duration_seconds=time.perf_counter() - started)
    prefix.with_suffix('.result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    return record


def start_block(source, block_number, workdir, outdir, *, substitutions=None, prelude='', shell=None):
    """Start a documented long-running service. Caller verifies HTTP and stops only its PID."""
    command, record, prefix = prepare(source, block_number, workdir, outdir, substitutions, prelude, shell)
    log_file = prefix.with_suffix('.log').open('wb')
    process = subprocess.Popen(command, cwd=workdir, stdout=log_file, stderr=subprocess.STDOUT,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    record.update(status='RUNNING', pid=process.pid, expected_outcome='Persistent service starts and serves a real HTTP request')
    prefix.with_suffix('.result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    return process, log_file, record, prefix
