param([string]$Python = 'python', [switch]$SkipInstall)

# Canonical Windows core job. GitHub's required workflow wrapper calls this file.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "CI command failed: $Executable (exit $LASTEXITCODE)" }
}

Invoke-Checked $Python @('tools/check_product_boundary.py')
if (-not $SkipInstall) {
    Invoke-Checked $Python @('-m','pip','install','--require-hashes','--only-binary=:all:','-r','requirements-build.lock','-r','requirements-e2e.lock')
    Invoke-Checked $Python @('-m','playwright','install','chromium')
}
Invoke-Checked $Python @('-m','unittest','discover','-s','tests','-v')
Invoke-Checked 'node' @('--check','sessiondesk/static/app.js')
Invoke-Checked 'node' @('--check','sessiondesk/static/home.js')
Get-ChildItem -LiteralPath 'sessiondesk/static/prepared' -Filter '*.js' | ForEach-Object {
    Invoke-Checked 'node' @('--check',$_.FullName)
}
Invoke-Checked 'node' @('--test','tests/book-renderer.test.mjs')
Invoke-Checked $Python @('tools/e2e_core.py')
Invoke-Checked $Python @('tools/e2e_prepared.py')
Invoke-Checked $Python @('tools/e2e_experience.py')
Invoke-Checked $Python @('tools/build_windows.py')
$taskArchive = @(Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'dist') -Filter '*windows-x64.zip' |
    Sort-Object LastWriteTime -Descending)[0].FullName
Invoke-Checked $Python @('tools/smoke_core.py','--archive',$taskArchive)
Invoke-Checked $Python @('tools/e2e_core.py','--exe','dist/SessionDesk/SessionDesk.exe')
Invoke-Checked $Python @('tools/e2e_prepared.py','--exe','dist/SessionDesk/SessionDesk.exe')
Invoke-Checked $Python @('tools/e2e_experience.py','--exe','dist/SessionDesk/SessionDesk.exe')
