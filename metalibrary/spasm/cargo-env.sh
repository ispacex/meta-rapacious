# Sourced by bench.sh and par_blocks.sh: puts cargo on PATH, installing a private rustup
# toolchain under $JOB_CACHE/rust (or ~/.cache/metalib/rust) if the box has none (no root needed).
[ -f "$HOME/.cargo/env" ] && source "$HOME/.cargo/env"
if ! command -v cargo > /dev/null; then
  export CARGO_HOME="${JOB_CACHE:-$HOME/.cache/metalib}/rust/cargo" RUSTUP_HOME="${JOB_CACHE:-$HOME/.cache/metalib}/rust/rustup"
  if [ ! -x "$CARGO_HOME/bin/cargo" ]; then
    curl -fsSL https://sh.rustup.rs | sh -s -- -y -q --profile minimal --no-modify-path > /dev/null
  fi
  export PATH="$CARGO_HOME/bin:$PATH"
fi
