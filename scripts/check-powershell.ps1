$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$blocks = Get-Content -LiteralPath 'outputs\doc-audit\powershell-blocks.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$syntaxFailures = @()
foreach ($block in $blocks) {
    $tokens = $null
    $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseInput($block.code, [ref]$tokens, [ref]$parseErrors) | Out-Null
    if ($parseErrors.Count -gt 0) {
        $syntaxFailures += [pscustomobject]@{ File=$block.file; Block=$block.block; Errors=($parseErrors.Message -join ' | ') }
    }
}
if ($syntaxFailures.Count -gt 0) {
    $syntaxFailures | Format-List
    throw 'PowerShell syntax check failed'
}
Write-Host ('PowerShell syntax valid: ' + $blocks.Count + ' blocks. Commands have not been executed by this check.')
