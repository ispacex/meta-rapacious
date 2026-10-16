#!/usr/bin/env bash
# One-time (idempotent) preparation of the remote box for remote/mr-remote.sh.
#
#     remote/setup-box.sh                  # uv into $ROOT/cache/bin
#     remote/setup-box.sh --rust           # also a Rust toolchain for the job user (rustup, minimal)
#     remote/setup-box.sh --rust --lean    # and elan for the Lean check (the toolchain itself is
#                                          # fetched by lake from metalibrary/cert/lean/lean-toolchain)
#
# Nothing is installed system-wide: everything lives under the job user's home directory.
# Same environment as remote/mr-remote.sh: MR_REMOTE_HOST and MR_REMOTE_USER are required.
set -eu
HOST=${MR_REMOTE_HOST:?set MR_REMOTE_HOST (ssh destination of the runner)}
SSH=${MR_REMOTE_SSH:-ssh -o BatchMode=yes -o ConnectTimeout=20 -o LogLevel=ERROR}
RUSER=${MR_REMOTE_USER:?set MR_REMOTE_USER (the user jobs run as)}
ROOT=${MR_REMOTE_ROOT:-/home/$RUSER/mr-jobs}
UV_VERSION=0.10.9
RUST=0 LEAN=0
for a in "$@"; do
  case $a in
    --rust) RUST=1 ;;
    --lean) LEAN=1 ;;
    *) echo "unknown option $a" >&2; exit 2 ;;
  esac
done

$SSH "$HOST" "set -e
  mkdir -p $ROOT/cache/bin
  if ! $ROOT/cache/bin/uv --version 2>/dev/null | grep -q '$UV_VERSION'; then
    t=\$(mktemp -d)
    curl -fsSL -o \$t/uv.tgz https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-x86_64-unknown-linux-gnu.tar.gz
    tar -xzf \$t/uv.tgz -C \$t
    install -m 755 \$t/uv-x86_64-unknown-linux-gnu/uv \$t/uv-x86_64-unknown-linux-gnu/uvx $ROOT/cache/bin/
    rm -rf \$t
  fi
  chown -R $RUSER: $ROOT
  echo \"uv: \$($ROOT/cache/bin/uv --version)\"
  if [ $RUST = 1 ]; then
    if ! sudo -u $RUSER -H bash -lc 'command -v cargo' >/dev/null; then
      sudo -u $RUSER -H bash -c 'curl -fsSL https://sh.rustup.rs | sh -s -- -y --profile minimal'
    fi
    sudo -u $RUSER -H bash -lc 'cargo --version'
  fi
  if [ $LEAN = 1 ]; then
    if ! sudo -u $RUSER -H test -x /home/$RUSER/.elan/bin/elan; then
      sudo -u $RUSER -H bash -c 'curl -fsSL https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh -s -- -y --default-toolchain none'
    fi
    sudo -u $RUSER -H /home/$RUSER/.elan/bin/elan --version
  fi"
