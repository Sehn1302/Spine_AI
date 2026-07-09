# Package Spine AI for sale (run from repo root)

$root = Split-Path $PSScriptRoot -Parent
$out = Join-Path $root "Spine_AI_Release.zip"
$staging = Join-Path $env:TEMP "Spine_AI_Release"

if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Path $staging | Out-Null

$include = @(
    "Install Spine.bat",
    "Launch Spine.bat",
    "README.md",
    "requirements.txt",
    "spine",
    "agents",
    "Scripts",
    "installer",
    "memory\knowledge"
)

foreach ($item in $include) {
    $src = Join-Path $root $item
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $staging $item) -Recurse -Force
    }
}

Copy-Item (Join-Path $PSScriptRoot "LICENSE.txt") $staging -Force

if (Test-Path $out) { Remove-Item $out -Force }
Compress-Archive -Path "$staging\*" -DestinationPath $out -Force
Remove-Item $staging -Recurse -Force

Write-Host "Release package ready: $out"
