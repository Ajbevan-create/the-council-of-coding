$ErrorActionPreference = 'Stop'
$InstallerPath = Join-Path $PSScriptRoot 'scripts/install.py'
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $InstallerPath @args
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python $InstallerPath @args
} else {
    throw 'Install Python 3.10+ from https://www.python.org/downloads/ and enable its launcher or PATH option.'
}
exit $LASTEXITCODE
