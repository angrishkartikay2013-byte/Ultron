# ULTRON GENESIS ecosystem bootstrap
# Runtime adapters are installed into ULTRON's own .venv. Browser Use stays
# isolated because it pins Requests separately from ULTRON core.

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

function Invoke-Uv {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
    $savedVirtualEnv = $env:VIRTUAL_ENV
    try {
        Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue
        & uv @Arguments
        if ($LASTEXITCODE -ne 0) { throw "uv command failed: uv $($Arguments -join ' ')" }
    }
    finally {
        if ($savedVirtualEnv) { $env:VIRTUAL_ENV = $savedVirtualEnv }
    }
}

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

function Ensure-Venv {
    param([string]$Name)
    $pythonCandidates = @(
        "E:\Programs\Python312\python.exe",
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe")
    )
    $python = $null
    foreach ($candidate in $pythonCandidates) {
        if (Test-Path $candidate) { $python = $candidate; break }
    }
    if (-not $python) {
        $cmd = Get-Command python -ErrorAction SilentlyContinue
        if ($cmd) { $python = $cmd.Source }
    }
    if (-not $python) { throw "Python 3.12 was not found. Install it at E:\Programs\Python312." }

    $venvPath = Join-Path $EnvsRoot $Name
    $pythonInVenv = Join-Path $venvPath "Scripts\python.exe"
    if (-not (Test-Path $pythonInVenv)) {
        & $python -m venv $venvPath
        if ($LASTEXITCODE -ne 0) { throw "Failed to create $Name." }
    }
    return $pythonInVenv
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
    Invoke-Uv sync --extra runtime

    Write-Host "[BROWSER] Installing Playwright Chromium for ULTRON..." -ForegroundColor Cyan
    Invoke-Uv run playwright install chromium

    $browser = Ensure-Venv "browser-use"
    Write-Host "[BROWSER] Installing Browser Use into isolated E-drive environment..." -ForegroundColor Cyan
    & $browser -m pip install --upgrade pip wheel
    if ($LASTEXITCODE -ne 0) { throw "Failed to update browser-use pip." }
    & $browser -m pip install "browser-use==0.13.10" "playwright>=1.50,<2"
    if ($LASTEXITCODE -ne 0) { throw "Browser Use installation failed." }
    & $browser -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw "Browser Use Chromium installation failed." }

    if ($Everything) {
        Write-Host "[RUNTIME] Syncing optional full ULTRON adapters..." -ForegroundColor Cyan
        Invoke-Uv sync --extra all

        $vad = Ensure-Venv "voice"
        & $vad -m pip install "silero-vad"
        if ($LASTEXITCODE -ne 0) { throw "Silero VAD installation failed." }

        $gateway = Ensure-Venv "model-gateway"
        & $gateway -m pip install "litellm"
        if ($LASTEXITCODE -ne 0) { throw "LiteLLM installation failed." }
    }
}

Write-Host ""
Write-Host "[OK] ULTRON ecosystem bootstrap finished." -ForegroundColor Green
Write-Host "[OK] External repos: $ReposRoot"
Write-Host "[OK] Runtime environment: $UltronRoot\.venv"
Write-Host "[OK] Browser Use environment: $EnvsRoot\browser-use"
Write-Host "[OK] Caches: $ExternalRoot"
Write-Host "[OK] Models: $env:OLLAMA_MODELS"
Write-Host "[OK] SearXNG source clone is skipped on Windows; its official deployment is container-oriented."
Write-Host "[OK] Model weights are never downloaded automatically."
