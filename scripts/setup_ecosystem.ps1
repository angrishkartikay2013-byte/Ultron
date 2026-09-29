# ULTRON GENESIS External Ecosystem Bootstrap
# Windows PowerShell.
# Clones external projects to E:\Titan\repos and keeps Python stacks isolated.
# This script intentionally does NOT download large AI model weights.

[CmdletBinding()]
param(
    [switch]$Everything,
    [switch]$WithEnvironments,
    [switch]$UpdateExisting
)

$ErrorActionPreference = "Stop"

$TitanRoot = "E:\Titan"
$ReposRoot = Join-Path $TitanRoot "repos"
$EnvsRoot = Join-Path $TitanRoot "envs"
$CacheRoot = "E:\PipCache"
$TempRoot = Join-Path $TitanRoot "tmp"
$ManifestPath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\ecosystem\components.json"))

if (-not (Test-Path $ManifestPath)) { throw "ULTRON ecosystem manifest not found: $ManifestPath" }

New-Item -ItemType Directory -Force -Path $ReposRoot | Out-Null
New-Item -ItemType Directory -Force -Path $EnvsRoot | Out-Null
New-Item -ItemType Directory -Force -Path $CacheRoot | Out-Null
New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null

$env:PIP_CACHE_DIR = $CacheRoot
$env:TEMP = $TempRoot
$env:TMP = $TempRoot
$env:HF_HOME = Join-Path $TitanRoot "hf_cache"
$env:HUGGINGFACE_HUB_CACHE = Join-Path $TitanRoot "hf_cache"
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $TitanRoot "browser-cache"
$env:OLLAMA_MODELS = Join-Path $TitanRoot "models"

New-Item -ItemType Directory -Force -Path $env:HF_HOME | Out-Null
New-Item -ItemType Directory -Force -Path $env:PLAYWRIGHT_BROWSERS_PATH | Out-Null
New-Item -ItemType Directory -Force -Path $env:OLLAMA_MODELS | Out-Null

$manifest = Get-Content -Raw -Path $ManifestPath | ConvertFrom-Json

function Resolve-Python312 {
    $candidates = @(
        "E:\Programs\Python312\python.exe",
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) { return $candidate }
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $python) { return $python.Source }
    throw "Python 3.12 was not found. Use E:\Programs\Python312 if available."
}

function Ensure-GitRepository {
    param([string]$Name,[string]$Repo,[string]$RelativePath)
    $target = Join-Path $ReposRoot $RelativePath
    if (Test-Path (Join-Path $target ".git")) {
        if ($UpdateExisting) {
            Write-Host "[UPDATE] $Name" -ForegroundColor Cyan
            git -C $target pull --ff-only
            if ($LASTEXITCODE -ne 0) { throw "Failed to update $Name." }
        } else { Write-Host "[SKIP]   $Name already exists." -ForegroundColor Yellow }
        return
    }
    if (Test-Path $target) {
        Write-Host "[ERROR]  $target exists but is not a Git repository." -ForegroundColor Red
        return
    }
    Write-Host "[CLONE]  $Name -> $target" -ForegroundColor Green
    git clone --depth 1 ("https://github.com/" + $Repo + ".git") $target
    if ($LASTEXITCODE -ne 0) { throw "Failed to clone $Name." }
}

function Ensure-Venv {
    param([string]$Name)
    $python = Resolve-Python312
    $venvPath = Join-Path $EnvsRoot $Name
    $pythonInVenv = Join-Path $venvPath "Scripts\python.exe"
    if (-not (Test-Path $pythonInVenv)) {
        Write-Host "[VENV]   Creating $Name" -ForegroundColor Cyan
        & $python -m venv $venvPath
        if ($LASTEXITCODE -ne 0) { throw "Failed to create environment $Name." }
    }
    return $pythonInVenv
}

function Install-AgentStack {
    $python = Ensure-Venv "agent-stack"
    Write-Host "[PIP]    Updating agent-stack tooling" -ForegroundColor Cyan
    & $python -m pip install --upgrade pip wheel
    if ($LASTEXITCODE -ne 0) { throw "Failed to update pip." }
    Write-Host "[PIP]    Installing agent integrations" -ForegroundColor Cyan
    & $python -m pip install "a2a-sdk" "langgraph" "mcp" "pydantic-ai" "huggingface_hub" "pywinauto"
    if ($LASTEXITCODE -ne 0) { throw "Agent-stack installation failed." }
}

function Install-BrowserStack {
    $python = Ensure-Venv "browser-use"
    Write-Host "[PIP]    Installing browser agent stack" -ForegroundColor Cyan
    & $python -m pip install --upgrade pip wheel
    if ($LASTEXITCODE -ne 0) { throw "Failed to update browser-use pip." }
    & $python -m pip install "browser-use" "playwright"
    if ($LASTEXITCODE -ne 0) { throw "Browser stack installation failed." }
    Write-Host "[BROWSER] Installing Chromium into E:\Titan\browser-cache" -ForegroundColor Cyan
    & $python -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw "Chromium installation failed." }
}

function Install-FullOptionalStack {
    $python = Ensure-Venv "model-gateway"
    Write-Host "[PIP]    Installing optional model gateway" -ForegroundColor Cyan
    & $python -m pip install --upgrade pip wheel
    if ($LASTEXITCODE -ne 0) { throw "Failed to update model-gateway pip." }
    & $python -m pip install "litellm"
    if ($LASTEXITCODE -ne 0) { throw "LiteLLM installation failed." }
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "             ULTRON GENESIS ECOSYSTEM             " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Repos : $ReposRoot"
Write-Host "Envs  : $EnvsRoot"
Write-Host "Models: $($env:OLLAMA_MODELS)"
Write-Host ""

$skipStatuses = @("integrated-in-core","separate-llm-repository","future")

foreach ($item in $manifest.components) {
    if ($skipStatuses -contains [string]$item.status) { continue }
    $shouldClone = [bool]$item.install
    if ($Everything) { $shouldClone = $true }
    if (-not $shouldClone) { continue }
    Ensure-GitRepository -Name ([string]$item.id) -Repo ([string]$item.repo) -RelativePath ([string]$item.path)
}

if ($WithEnvironments) {
    Install-AgentStack
    Install-BrowserStack
}

if ($Everything -and $WithEnvironments) { Install-FullOptionalStack }

Write-Host ""
Write-Host "[OK] Ecosystem bootstrap finished." -ForegroundColor Green
Write-Host "[OK] No large model weights were downloaded." -ForegroundColor Green
Write-Host "[OK] Python/model/browser caches were directed to E:\Titan." -ForegroundColor Green
Write-Host ""
Write-Host "Run 'uv run diagnostics.py' and then 'uv run genesis.py' from the ULTRON repository." -ForegroundColor Cyan