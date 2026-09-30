# ULTRON GENESIS ecosystem bootstrap
# Runtime adapters are installed into ULTRON's own .venv so the live tool
# registry can import them. Heavy upstream source repositories remain external.

[CmdletBinding()]
param(
    [switch]$Everything,
    [switch]$WithEnvironments,
    [switch]$UpdateExisting
)

$ErrorActionPreference = "Stop"
$UltronRoot = "E:\ULTRON"
$ExternalRoot = Join-Path $UltronRoot "external"
$ReposRoot = Join-Path $ExternalRoot "repos"
$EnvsRoot = Join-Path $ExternalRoot "envs"
$CacheRoot = "E:\PipCache"
$TempRoot = Join-Path $ExternalRoot "tmp"
$ManifestPath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\ecosystem\components.json"))

New-Item -ItemType Directory -Force -Path $ReposRoot,$EnvsRoot,$CacheRoot,$TempRoot | Out-Null
$env:PIP_CACHE_DIR = $CacheRoot
$env:TEMP = $TempRoot
$env:TMP = $TempRoot
$env:HF_HOME = Join-Path $ExternalRoot "hf_cache"
$env:HUGGINGFACE_HUB_CACHE = Join-Path $ExternalRoot "hf_cache"
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $ExternalRoot "browser-cache"
$env:OLLAMA_MODELS = Join-Path $UltronRoot "models"
New-Item -ItemType Directory -Force -Path $env:HF_HOME,$env:PLAYWRIGHT_BROWSERS_PATH,$env:OLLAMA_MODELS | Out-Null

function Ensure-GitRepository {
    param([string]$Name,[string]$Repo,[string]$RelativePath)
    $target = Join-Path $ReposRoot $RelativePath
    if (Test-Path (Join-Path $target ".git")) {
        if ($UpdateExisting) {
            Write-Host "[UPDATE] $Name" -ForegroundColor Cyan
            git -C $target pull --ff-only
            if ($LASTEXITCODE -ne 0) { throw "Failed to update $Name." }
        } else {
            Write-Host "[SKIP] $Name already exists." -ForegroundColor Yellow
        }
        return
    }
    if (Test-Path $target) { throw "$target exists but is not a Git repository." }
    Write-Host "[CLONE] $Name -> $target" -ForegroundColor Green
    git clone --depth 1 ("https://github.com/" + $Repo + ".git") $target
    if ($LASTEXITCODE -ne 0) { throw "Failed to clone $Name." }
}

$manifest = Get-Content -Raw -Path $ManifestPath | ConvertFrom-Json
foreach ($item in $manifest.components) {
    $status = [string]$item.status
    if ($status -in @("integrated-in-core","separate-llm-repository","future","container-service-windows-skip")) {
        continue
    }
    if ($Everything -or [bool]$item.install) {
        Ensure-GitRepository -Name ([string]$item.id) -Repo ([string]$item.repo) -RelativePath ([string]$item.path)
    }
}

if ($WithEnvironments) {
    Write-Host "[RUNTIME] Syncing ULTRON runtime integrations into .venv..." -ForegroundColor Cyan
    uv sync --extra runtime
    if ($LASTEXITCODE -ne 0) { throw "Runtime integration sync failed." }

    Write-Host "[BROWSER] Installing Chromium..." -ForegroundColor Cyan
    uv run playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw "Chromium installation failed." }

    if ($Everything) {
        Write-Host "[RUNTIME] Running optional full dependency sync..." -ForegroundColor Cyan
        uv sync --extra all
        if ($LASTEXITCODE -ne 0) { throw "Full runtime sync failed." }
    }
}

Write-Host ""
Write-Host "[OK] ULTRON ecosystem bootstrap finished." -ForegroundColor Green
Write-Host "[OK] External repos: $ReposRoot"
Write-Host "[OK] Runtime environment: $UltronRoot\.venv"
Write-Host "[OK] Caches: $ExternalRoot"
Write-Host "[OK] Models: $env:OLLAMA_MODELS"
Write-Host "[OK] SearXNG source clone is skipped on Windows; its official deployment is container-oriented."
Write-Host "[OK] Model weights are never downloaded automatically."
