# Reproduction complète en PowerShell. Écrase les rapports génériques construits par les scripts.
param([switch]$SansInstallation)
$ErrorActionPreference = 'Stop'
$racineTP = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $racineTP
$env:PYTHONUTF8 = '1'
$env:QT_QPA_PLATFORM = 'offscreen'
New-Item -ItemType Directory -Force data,workflows,models,reports,scripts,figures,tmp | Out-Null

function Invoke-PythonTP {
    param([string]$InterpreteurTP, [string[]]$ArgumentsTP)
    & $InterpreteurTP @ArgumentsTP
    if ($LASTEXITCODE -ne 0) { throw "Échec Python : $($ArgumentsTP -join ' ')" }
}

if (-not (Test-Path '.venv/Scripts/python.exe')) {
    Invoke-PythonTP 'python' @('-m','venv','.venv')
}
if (-not (Test-Path '.venv-orange/Scripts/python.exe')) {
    Invoke-PythonTP 'python' @('-m','venv','.venv-orange')
}
$pythonTP = Join-Path $racineTP '.venv/Scripts/python.exe'
$pythonOrangeTP = Join-Path $racineTP '.venv-orange/Scripts/python.exe'
if (-not $SansInstallation) {
    Invoke-PythonTP $pythonTP @('-m','pip','install','--no-cache-dir','-r','requirements.txt')
    Invoke-PythonTP $pythonOrangeTP @('-m','pip','install','--no-cache-dir','-r','requirements-orange.txt')
}
Invoke-PythonTP $pythonTP @('scripts/extrait_pdf.py')
Invoke-PythonTP $pythonTP @('scripts/donnees.py')
Invoke-PythonTP $pythonOrangeTP @('scripts/audit_orange.py')
Invoke-PythonTP $pythonOrangeTP @('scripts/orange_experiences.py')
Invoke-PythonTP $pythonOrangeTP @('scripts/workflow_orange.py')
& (Join-Path $PSScriptRoot 'verifie_knime.ps1')
Invoke-PythonTP $pythonTP @('scripts/knime_simulation_sklearn.py')
Invoke-PythonTP $pythonTP @('scripts/flaml_reference.py')
Invoke-PythonTP $pythonTP @('scripts/synthese.py')
Invoke-PythonTP $pythonTP @('scripts/questions.py')
Invoke-PythonTP $pythonTP @('scripts/compte_rendu.py')
Invoke-PythonTP $pythonTP @('scripts/cree_docx.py')
Invoke-PythonTP $pythonTP @('scripts/valide_compte_rendu.py')
Invoke-PythonTP $pythonTP @('scripts/valide_livrables.py')
Invoke-PythonTP $pythonTP @('scripts/finalise.py')
Write-Output 'Reproduction terminée. Captures, exécution KNIME réelle et contrôle visuel Word restent manuels.'
