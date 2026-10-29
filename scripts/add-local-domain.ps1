$ErrorActionPreference = 'Stop'

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell.exe -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $MyInvocation.MyCommand.Path) -Verb RunAs
    exit
}

$hostsPath = Join-Path $env:SystemRoot 'System32\drivers\etc\hosts'
$entries = @('127.0.0.1 kairos.com', '127.0.0.1 www.kairos.com')
$content = Get-Content -Path $hostsPath -Raw
$changed = $false

foreach ($entry in $entries) {
    if ($content -notmatch ('(?m)^' + [regex]::Escape($entry) + '\s*$')) {
        Add-Content -Path $hostsPath -Value "`r`n$entry"
        $changed = $true
    }
}

if (-not (Get-Content -Path $hostsPath -Raw).Contains('# Kairos local development')) {
    Add-Content -Path $hostsPath -Value "`r`n# Kairos local development"
}

ipconfig /flushdns | Out-Null
Write-Host "Kairos local domain configured. Open http://kairos.com:8088"
