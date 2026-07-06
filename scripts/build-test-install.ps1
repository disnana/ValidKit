param(
    [switch]$SkipInstall,
    [switch]$SkipCore,
    [switch]$SkipTests,
    [switch]$Bench,
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RootDir

if (-not $Python) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
    }
    if (-not $pythonCmd) {
        throw "Python was not found. Pass -Python <path> and retry."
    }
    $Python = $pythonCmd.Source
}

function Invoke-Python {
    & $Python @args
}

Write-Host "==> Python"
Invoke-Python --version

if (-not $SkipInstall) {
    if ($Bench) {
        Write-Host "==> Installing validkit-py in editable mode with benchmark extras"
        Invoke-Python -m pip install -e ".[benchmark]"
    } else {
        Write-Host "==> Installing validkit-py in editable mode"
        Invoke-Python -m pip install -e .
    }
} else {
    $srcPath = Join-Path $RootDir "src"
    if ($env:PYTHONPATH) {
        $env:PYTHONPATH = "$srcPath;$env:PYTHONPATH"
    } else {
        $env:PYTHONPATH = "$srcPath"
    }
}

$pytestDeps = Join-Path $RootDir ".pytest_deps"
if (Test-Path $pytestDeps) {
    if ($env:PYTHONPATH) {
        $env:PYTHONPATH = "$pytestDeps;$env:PYTHONPATH"
    } else {
        $env:PYTHONPATH = "$pytestDeps"
    }
}

if (-not $SkipCore) {
    if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
        throw "cargo was not found. Install Rust or rerun with -SkipCore."
    }

    Write-Host "==> Rust"
    cargo --version

    Invoke-Python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('maturin') else 1)"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "==> Installing maturin"
        Invoke-Python -m pip install "maturin>=1.7,<2"
    }

    Write-Host "==> Testing Rust native core"
    cargo test --manifest-path src/validkit_core/Cargo.toml

    Write-Host "==> Building validkit-py-core wheel"
    Invoke-Python -c "import shutil; shutil.rmtree('dist-native-local', ignore_errors=True)"
    Invoke-Python -m maturin build --release --manifest-path src/validkit_core/Cargo.toml --out dist-native-local

    if (-not $SkipInstall) {
        $coreWheel = Get-ChildItem -Path dist-native-local -Filter "validkit_py_core-*.whl" | Sort-Object Name | Select-Object -Last 1
        if (-not $coreWheel) {
            throw "validkit-py-core wheel was not produced."
        }

        Write-Host "==> Installing validkit-py-core"
        Invoke-Python -m pip install --force-reinstall --no-deps $coreWheel.FullName
    } else {
        Write-Host "==> Core install skipped; tests will use any already installed/importable core."
    }

    Write-Host "==> Native runtime check"
    Invoke-Python -c "from validkit._native import NATIVE_RUNTIME; print('native available:', NATIVE_RUNTIME.available, 'disabled:', NATIVE_RUNTIME.disabled, 'error:', NATIVE_RUNTIME.error)"
}

if (-not $SkipTests) {
    Write-Host "==> Running pytest"
    Invoke-Python -m pytest -q
}

if ($Bench) {
    Write-Host "==> Running benchmark"
    Invoke-Python benchmarks/benchmark_validation.py --iterations 5000 --native-mode both
}

Write-Host "==> Done"
