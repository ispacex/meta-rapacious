#!/usr/bin/env bash
# Build SpaSM (https://github.com/cbouilla/spasm) at a pinned commit, with Givaro and FFLAS-FFPACK
# from conda-forge (micromamba; no root needed). Idempotent: an existing build is reused.
#
#   SPASM_HOME=... metalibrary/spasm/build.sh     # default $JOB_CACHE/spasm (or ./spasm-build)
#
# The tools end up in $SPASM_HOME/src/build/tools (rank, echelonize, kernel, check_cert, ...).
set -euo pipefail
SPASM_COMMIT=09c40943f1d4b754f89fb97fc9ddf2b8e53e967e   # master of 2024-11-04 (v1.3 + argp patch)
SPASM_HOME=${SPASM_HOME:-${JOB_CACHE:-$PWD}/spasm}
mkdir -p "$SPASM_HOME/bin"
export PATH="$SPASM_HOME/bin:$PATH"
if ! command -v micromamba > /dev/null; then
  curl -fsSL https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj -C "$SPASM_HOME" bin/micromamba
fi
ENV="$SPASM_HOME/env"
if [ ! -x "$ENV/bin/cmake" ]; then
  MAMBA_ROOT_PREFIX="$SPASM_HOME/mamba" micromamba create -y -q -p "$ENV" -c conda-forge \
    cmake make pkg-config c-compiler cxx-compiler fflas-ffpack givaro gmp "libblas=*=*openblas" \
    > /dev/null
fi
export PATH="$ENV/bin:$PATH" PKG_CONFIG_PATH="$ENV/lib/pkgconfig:$ENV/share/pkgconfig"
if [ ! -d "$SPASM_HOME/src/.git" ]; then
  git clone -q https://github.com/cbouilla/spasm "$SPASM_HOME/src"
fi
cd "$SPASM_HOME/src"
if [ "$(git rev-parse HEAD)" != "$SPASM_COMMIT" ]; then
  git fetch -q origin && git checkout -q "$SPASM_COMMIT" && rm -rf build
fi
if [ ! -x build/tools/rank ]; then
  cmake -S . -B build -DCMAKE_PREFIX_PATH="$ENV" -DCMAKE_INSTALL_RPATH="$ENV/lib" \
    -DCMAKE_BUILD_RPATH="$ENV/lib" -DBUILD_TESTING=OFF > build.log 2>&1 || { tail -30 build.log; exit 1; }
  cmake --build build -j "${SPASM_JOBS:-2}" >> build.log 2>&1 || { tail -30 build.log; exit 1; }
fi
echo "SpaSM $(git rev-parse --short HEAD) in $SPASM_HOME/src/build/tools"
