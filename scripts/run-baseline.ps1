# Instructor smoke test only. Students follow each manual and keep independent predictions.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONUTF8 = '1'
$pythonPath = Join-Path (Get-Location) '.venv\Scripts\python.exe'
$runRoot = Join-Path (Get-Location) ('outputs\smoke-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
$previousDataRoot = $env:BDP_ROOT
$env:BDP_ROOT = $runRoot
function Invoke-Lab([string[]]$Arguments) {
    & $pythonPath -m coursekit @Arguments
    if ($LASTEXITCODE -ne 0) { throw ('Lab failed: ' + ($Arguments -join ' ')) }
}
try {
    Invoke-Lab @('identity','--student-id','TEACHER-SMOKE','--lab','01')
    Invoke-Lab @('seed','--rows','20000')
    Invoke-Lab @('lab01')
    Invoke-Lab @('lab02')
    Invoke-Lab @('lab03','--workers','1','--partitions','8')
    Invoke-Lab @('lab03','--workers','2','--partitions','8')
    Invoke-Lab @('lab04')
    Invoke-Lab @('lab05','--mode','lexical')
    Invoke-Lab @('lab06','--split','dev','--generator','extractive')
    Invoke-Lab @('lab06','--split','test','--generator','extractive')
    Write-Host "Baseline 01-06 complete. Data retained at $runRoot"
    Write-Host 'For 07-08 follow the two-terminal HTTP instructions using this BDP_ROOT.'
} finally {
    if ($null -ne $previousDataRoot) { $env:BDP_ROOT = $previousDataRoot }
    else { Remove-Item Env:BDP_ROOT -ErrorAction SilentlyContinue }
}
