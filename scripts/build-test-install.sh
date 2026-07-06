#!/usr/bin/env sh
set -eu

case "$(uname -s 2>/dev/null || echo unknown)" in
  MINGW*|MSYS*|CYGWIN*)
    PATH="/usr/bin:/bin:$PATH"
    ;;
esac

usage() {
  echo "Usage: scripts/build-test-install.sh [options]"
  echo
  echo "Build, install, and test ValidKit plus the optional Rust native core."
  echo
  echo "Options:"
  echo "  --skip-install   Build and test without installing packages."
  echo "  --skip-core      Skip validkit-py-core build/install."
  echo "  --skip-tests     Skip pytest."
  echo "  --bench          Run the validation benchmark after tests."
  echo "  -h, --help       Show this help."
  echo
  echo "Environment:"
  echo "  PYTHON           Python executable to use. Defaults to python3, then python."
}

SKIP_INSTALL=0
SKIP_CORE=0
SKIP_TESTS=0
RUN_BENCH=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --skip-install) SKIP_INSTALL=1 ;;
    --skip-core) SKIP_CORE=1 ;;
    --skip-tests) SKIP_TESTS=1 ;;
    --bench) RUN_BENCH=1 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

case "$0" in
  */*) SCRIPT_PATH_DIR=${0%/*} ;;
  *) SCRIPT_PATH_DIR=. ;;
esac
SCRIPT_DIR=$(CDPATH= cd -- "$SCRIPT_PATH_DIR" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$ROOT_DIR"

if [ -z "${PYTHON:-}" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
  elif command -v python >/dev/null 2>&1; then
    PYTHON=python
  else
    echo "Python was not found. Set PYTHON=/path/to/python and retry." >&2
    exit 1
  fi
fi

case "$(uname -s 2>/dev/null || echo unknown)" in
  MINGW*|MSYS*|CYGWIN*) PATH_SEP=";" ;;
  *) PATH_SEP=":" ;;
esac

prepend_pythonpath() {
  path_to_add=$1
  if [ -n "${PYTHONPATH:-}" ]; then
    PYTHONPATH="${path_to_add}${PATH_SEP}${PYTHONPATH}"
  else
    PYTHONPATH="${path_to_add}"
  fi
  export PYTHONPATH
}

echo "==> Python"
"$PYTHON" --version

if [ "$SKIP_INSTALL" -eq 0 ]; then
  if [ "$RUN_BENCH" -eq 1 ]; then
    echo "==> Installing validkit-py in editable mode with benchmark extras"
    "$PYTHON" -m pip install -e ".[benchmark]"
  else
    echo "==> Installing validkit-py in editable mode"
    "$PYTHON" -m pip install -e .
  fi
else
  prepend_pythonpath "$ROOT_DIR/src"
fi

if [ -d "$ROOT_DIR/.pytest_deps" ]; then
  prepend_pythonpath "$ROOT_DIR/.pytest_deps"
fi

if [ "$SKIP_CORE" -eq 0 ]; then
  if ! command -v cargo >/dev/null 2>&1; then
    echo "cargo was not found. Install Rust or rerun with --skip-core." >&2
    exit 1
  fi

  echo "==> Rust"
  cargo --version

  if ! "$PYTHON" -c "import maturin" >/dev/null 2>&1; then
    echo "==> Installing maturin"
    "$PYTHON" -m pip install "maturin>=1.7,<2"
  fi

  echo "==> Testing Rust native core"
  cargo test --manifest-path src/validkit_core/Cargo.toml

  echo "==> Building validkit-py-core wheel"
  "$PYTHON" -c "import shutil; shutil.rmtree('dist-native-local', ignore_errors=True)"
  "$PYTHON" -m maturin build --release \
    --manifest-path src/validkit_core/Cargo.toml \
    --out dist-native-local

  if [ "$SKIP_INSTALL" -eq 0 ]; then
    CORE_WHEEL=$("$PYTHON" -c "from pathlib import Path; wheels=sorted(Path('dist-native-local').glob('validkit_py_core-*.whl')); print(wheels[-1] if wheels else '')")
    if [ -z "$CORE_WHEEL" ]; then
      echo "validkit-py-core wheel was not produced." >&2
      exit 1
    fi

    echo "==> Installing validkit-py-core"
    "$PYTHON" -m pip install --force-reinstall --no-deps "$CORE_WHEEL"
  else
    echo "==> Core install skipped; tests will use any already installed/importable core."
  fi

  echo "==> Native runtime check"
  "$PYTHON" -c "from validkit._native import NATIVE_RUNTIME; print('native available:', NATIVE_RUNTIME.available, 'disabled:', NATIVE_RUNTIME.disabled, 'error:', NATIVE_RUNTIME.error)"
fi

if [ "$SKIP_TESTS" -eq 0 ]; then
  echo "==> Running pytest"
  "$PYTHON" -m pytest -q
fi

if [ "$RUN_BENCH" -eq 1 ]; then
  echo "==> Running benchmark"
  "$PYTHON" benchmarks/benchmark_validation.py --iterations 5000 --native-mode both
fi

echo "==> Done"
