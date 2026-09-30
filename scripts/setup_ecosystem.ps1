# ULTRON GENESIS external ecosystem bootstrap
# All external repositories, caches, browser binaries and isolated environments live on E:.

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

function Resolve-Python312 {
    $candidates = @("E:\Programs\Python312\python.exe",(Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"))
    foreach ($candidate in $candidates) { if (Test-Path $candidate) { return $candidate } }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $python) { return $python.Source }
    throw "Python 3.12 was not found. Install it at E:\Programs\Python312."
}

function Ensure-GitRepository {
    param([string]$Name,[string]$Repo,[string]$RelativePath)
    $target = Join-Path $ReposRoot $RelativePath
    if (Test-Path (Join-Path $target ".git")) {
        if ($UpdateExisting) { git -C $target pull --ff-only }
        return
    }
    if (Test-Path $target) { throw "$target exists but is not a Git repository." }
    Write-Host "[CLONE] $Name -> $target" -ForegroundColor Green
    git clone --depth 1 ("https://github.com/" + $Repo + ".git") $target
    if ($LASTEXITCODE -ne 0) { throw "Failed to clone $Name." }
}

function Ensure-Venv {
    param([string]$Name)
    $python = Resolve-Python312
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
    if ($status -in @("integrated-in-core","separate-llm-repository","future")) { continue }
    if ($Everything -or [bool]$item.install) {
        Ensure-GitRepository -Name ([string]$item.id) -Repo ([string]$item.repo) -RelativePath ([string]$item.path)
    }
}

if ($WithEnvironments) {
    $agent = Ensure-Venv "agent-stack"
    & $agent -m pip install --upgrade pip wheel
    & $agent -m pip install "mcp" "a2a-sdk" "langgraph" "pydantic-ai" "huggingface_hub" "pywinauto"
    if ($LASTEXITCODE -ne 0) { throw "Agent stack installation failed." }

    $browser = Ensure-Venv "browser-use"
    & $browser -m pip install --upgrade pip wheel
    & $browser -m pip install "browser-use" "playwright"
    if ($LASTEXITCODE -ne 0) { throw "Browser stack installation failed." }
    & $browser -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw "Chromium installation failed." }

    if ($Everything) {
        $vad = Ensure-Venv "voice"
        & $vad -m pip install "silero-vad"
        $gateway = Ensure-Venv "model-gateway"
        & $gateway -m pip install "litellm"
    }
}

Write-Host ""
Write-Host "[OK] ULTRON ecosystem bootstrap finished." -ForegroundColor Green
Write-Host "[OK] External repos: $ReposRoot"
Write-Host "[OK] Isolated environments: $EnvsRoot"
Write-Host "[OK] Models: $env:OLLAMA_MODELS"
Write-Host "[OK] Model weights are never downloaded automatically."
