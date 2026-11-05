# Phase 4 : inventaire non exhaustif, sans lancer l'interface KNIME.
$ErrorActionPreference = 'Stop'
$racineTP = Split-Path -Parent $PSScriptRoot
$commandeKnime = Get-Command knime,knime.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
$dossiersKnime = @('C:\Program Files', 'C:\Program Files (x86)', "$env:LOCALAPPDATA", "$env:USERPROFILE\Downloads", "$env:USERPROFILE\Documents") |
    ForEach-Object { Get-ChildItem -LiteralPath $_ -Directory -ErrorAction SilentlyContinue } |
    Where-Object Name -Match 'knime' | Select-Object -ExpandProperty FullName
$logicielsKnime = @('HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*') |
    ForEach-Object { Get-ItemProperty -Path $_ -ErrorAction SilentlyContinue } |
    Where-Object DisplayName -Match 'KNIME' | Select-Object DisplayName,DisplayVersion,InstallLocation
$etatKnime = [ordered]@{
    provenance = "Vérification locale PowerShell, sans exécution KNIME"
    commandes = @($commandeKnime)
    dossiers = @($dossiersKnime)
    logiciels = @($logicielsKnime)
    limite = "Recherche PATH, dossiers courants et registre ; installation portable ailleurs possible. Toute exécution KNIME reste [À FAIRE PAR L'ÉTUDIANT]."
}
$etatKnime | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 (Join-Path $racineTP 'reports/knime_installation.json')
$etatKnime | ConvertTo-Json -Depth 4
