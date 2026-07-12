$ErrorActionPreference = "Stop"
$Installer = Join-Path $PSScriptRoot "scripts/install.py"

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $Installer @args
    exit $LASTEXITCODE
}

if (Get-Command python3 -ErrorAction SilentlyContinue) {
    & python3 $Installer @args
    exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    & python $Installer @args
    exit $LASTEXITCODE
}

Write-Error "Relay Orchestra requires Python 3."
exit 1
