# Activate the isolated ForgeHacks project environment and local caches.
# Run this script from the project root:
#   . .\scripts\activate-project.ps1

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"

if (-not (Test-Path (Join-Path $VenvPath "Scripts\Activate.ps1"))) {
    throw "Project virtual environment not found at $VenvPath. Create it first with: python -m venv .venv"
}

$env:PIP_CACHE_DIR = Join-Path $ProjectRoot ".cache\pip"
$env:HF_HOME = Join-Path $ProjectRoot ".cache\huggingface"
$env:HF_HUB_CACHE = Join-Path $env:HF_HOME "hub"
$env:TRANSFORMERS_CACHE = $env:HF_HOME

New-Item -ItemType Directory -Force -Path $env:PIP_CACHE_DIR, $env:HF_HOME | Out-Null
. (Join-Path $VenvPath "Scripts\Activate.ps1")

Write-Host "ForgeHacks project environment active: $env:VIRTUAL_ENV"
Write-Host "PIP cache: $env:PIP_CACHE_DIR"
Write-Host "Hugging Face cache: $env:HF_HOME"
