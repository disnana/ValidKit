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

function Invoke-PythonRaw {
    & $Python @args
}

function Invoke-Python {
    Invoke-PythonRaw @args
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code ${LASTEXITCODE}: $Python $args"
    }
}

function Invoke-Checked {
    & $args[0] @($args | Select-Object -Skip 1)
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $args"
    }
}

function Remove-StaleRootCore {
    $staleCore = @()
    $staleCore += Get-ChildItem -Path $RootDir -File -Filter "validkit_core*.pyd" -ErrorAction SilentlyContinue
    $staleCore += Get-ChildItem -Path $RootDir -File -Filter "validkit_core*.so" -ErrorAction SilentlyContinue
    foreach ($file in $staleCore) {
        Write-Host "==> Removing stale root native core $($file.Name)"
        Remove-Item -LiteralPath $file.FullName -Force
    }
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
}

$srcPath = Join-Path $RootDir "src"
if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$srcPath;$env:PYTHONPATH"
} else {
    $env:PYTHONPATH = "$srcPath"
}

Write-Host "==> ValidKit import check"
Invoke-Python -c "import validkit; print('validkit:', validkit.__version__)"

$pytestDeps = Join-Path $RootDir ".pytest_deps"
if (Test-Path $pytestDeps) {
    if ($env:PYTHONPATH) {
        $env:PYTHONPATH = "$pytestDeps;$env:PYTHONPATH"
    } else {
        $env:PYTHONPATH = "$pytestDeps"
    }
}

if (-not $SkipCore) {
    Remove-StaleRootCore

    if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
        throw "cargo was not found. Install Rust or rerun with -SkipCore."
    }

    Write-Host "==> Rust"
    Invoke-Checked cargo --version

    Invoke-PythonRaw -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('maturin') else 1)"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "==> Installing maturin into .build-tools"
        $buildTools = Join-Path $RootDir ".build-tools"
        Invoke-Python -m pip install --upgrade --target $buildTools "maturin>=1.7,<2"
        if ($env:PYTHONPATH) {
            $env:PYTHONPATH = "$buildTools;$env:PYTHONPATH"
        } else {
            $env:PYTHONPATH = "$buildTools"
        }
    }

    $maturinCommand = Get-Command maturin -ErrorAction SilentlyContinue
    if ($maturinCommand) {
        $maturinExe = $maturinCommand.Source
    } else {
        $maturinExe = Join-Path $RootDir ".build-tools/bin/maturin.exe"
        if (-not (Test-Path $maturinExe)) {
            $maturinExe = Join-Path $RootDir ".build-tools/bin/maturin"
        }
    }
    if (-not (Test-Path $maturinExe)) {
        throw "maturin executable was not found after installation."
    }

    Write-Host "==> Testing Rust native core"
    Invoke-Checked cargo test --manifest-path src/validkit_core/Cargo.toml

    Write-Host "==> Building validkit-py-core wheel"
    Invoke-Python -c "import shutil; shutil.rmtree('dist-native-local', ignore_errors=True)"
    Invoke-Checked $maturinExe build --release --manifest-path src/validkit_core/Cargo.toml --out dist-native-local

    if (-not $SkipInstall) {
        $coreWheel = Get-ChildItem -Path dist-native-local -Filter "validkit_py_core-*.whl" -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -Last 1
        if (-not $coreWheel) {
            throw "validkit-py-core wheel was not produced."
        }

        Write-Host "==> Installing validkit-py-core"
        Invoke-Python -m pip install --force-reinstall --no-deps $coreWheel.FullName
    } else {
        Write-Host "==> Core install skipped; tests will use any already installed/importable core."
    }

    Remove-StaleRootCore

    Write-Host "==> Native runtime check"
    Invoke-Python -c "import validkit_core; from validkit._native import NATIVE_RUNTIME; print('validkit_core:', getattr(validkit_core, '__file__', None)); print('native available:', NATIVE_RUNTIME.available, 'disabled:', NATIVE_RUNTIME.disabled, 'error:', NATIVE_RUNTIME.error)"
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
