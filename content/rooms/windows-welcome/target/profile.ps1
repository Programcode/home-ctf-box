# WIN-SIM01 PowerShell profile (all users, all hosts).
# This box is a Linux container simulating a Windows host; PowerShell
# itself is real. The variables below stand in for values a genuine
# Windows session would populate.
$env:COMPUTERNAME = 'WIN-SIM01'
$env:OS = 'Windows_NT'
$env:USERDOMAIN = 'SIMDOMAIN'
if (-not $env:USERNAME) { $env:USERNAME = $env:USER }

# Land in the simulated C: drive so Get-ChildItem walks look familiar.
if (Test-Path "$HOME/winfs") { Set-Location "$HOME/winfs" }

function prompt {
    "PS $env:COMPUTERNAME\$(Get-Location)> "
}
