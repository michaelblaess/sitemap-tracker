#Requires -Version 5.1
<#
.SYNOPSIS
    Rendert eine VHS-.tape unter WSL (vhs scheitert auf Windows-Host nativ).
.EXAMPLE
    .\tape.ps1 intro      # rendert demo/intro.tape -> demo/intro.gif
    .\tape.ps1            # listet verfuegbare Tapes
#>
$ErrorActionPreference = "Stop"

$tape = $args[0]
if (-not $tape) {
    Get-ChildItem demo\*.tape | ForEach-Object { Write-Host "  $($_.BaseName)" }
    exit 0
}
if (-not $tape.EndsWith(".tape")) { $tape = "$tape.tape" }

$wslRepo = "/mnt/c/Users/Michael/Repos/sitemap-tracker"
wsl -d Ubuntu-22.04 -- bash "$wslRepo/demo/render-wsl.sh" "demo/$tape"
