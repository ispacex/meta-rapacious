#!/usr/bin/env bash
# The unstable Adams E_2 of the odd spheres at p = 3, two ways, for the check of Toda's 2003
# table (check.py, MATH-442). A tm job, run from the repository root:
#
#     metalibrary/toda2003/e2_job.sh          # writes $JOB_OUT/sseq_S<n>.csv and lambda_m<m>.csv
#
#   sseq_S<n>.csv  sseq/ext (JoeyBF/sseq at SSEQ_COMMIT), resolve_unstable of the module S_<n>[3]
#                  (example ../sseq_unstable_dims.rs): lines n,s,dim, n = t - s, odd n <= NMAX,
#                  through the stem n + KMAX;
#   lambda_m<m>.csv  H(Lambda(m)) for S^{2m+1} (rust/src/bin/lambdan.rs): lines m,k,s,dim, k <= KLAM.
set -euo pipefail
NMAX=${NMAX:-37} KMAX=${KMAX:-79} SMAX=${SMAX:-40} KLAM=${KLAM:-58} THREADS=${THREADS:-4}
SSEQ_COMMIT=7d63ea964dd0e8d059f87b99c0003a3503b5d6dc
: "${JOB_OUT:?}" "${JOB_CACHE:?}" "${JOB_ROOT:?}"
HERE=$(cd "$(dirname "$0")" && pwd)
source "$HERE/../spasm/cargo-env.sh"
total=$(( (NMAX - 1) / 2 + (NMAX - 1) / 2 )); done_=0
progress() { done_=$((done_ + 1)); echo "$done_/$total" > "$JOB_ROOT/progress"; }

# 1. H(Lambda(m)), m = 1 .. (NMAX-1)/2
export CARGO_TARGET_DIR="$JOB_CACHE/target"
(cd "$HERE/../rust" && cargo build --release -q --bin lambdan)
for m in $(seq 1 $(( (NMAX - 1) / 2 ))); do
  t0=$(date +%s)
  "$CARGO_TARGET_DIR/release/lambdan" "$m" "$KLAM" "$THREADS" > "$JOB_OUT/lambda_m$m.csv"
  echo "Lambda($m) through stem $KLAM: $(( $(date +%s) - t0 )) s"
  progress
done

# 2. sseq/ext, resolve_unstable of S_n[3]
src="$JOB_CACHE/sseq-$SSEQ_COMMIT"
if [ ! -d "$src/ext" ]; then
  rm -rf "$src.tmp" && git clone -q https://github.com/JoeyBF/sseq "$src.tmp"
  git -C "$src.tmp" checkout -q "$SSEQ_COMMIT" && mv "$src.tmp" "$src"
fi
cp "$HERE/../sseq_unstable_dims.rs" "$src/ext/examples/unstable_dims.rs"
(cd "$src/ext" && CARGO_TARGET_DIR="$JOB_CACHE/target-sseq" cargo build --release -q --example unstable_dims)
for n in $(seq 3 2 "$NMAX"); do
  t0=$(date +%s)
  printf 'S_%d[3]\n\n%d\n%d\n' "$n" $((n + KMAX)) "$SMAX" \
    | "$JOB_CACHE/target-sseq/release/examples/unstable_dims" > "$JOB_OUT/sseq_S$n.csv"
  echo "sseq S_$n[3] through stem $((n + KMAX)): $(( $(date +%s) - t0 )) s"
  progress
done
