#!/usr/bin/env bash
# Write and check the certificates for the columns N, as a job on a remote box (remote/mr-remote.sh)
# or anywhere with cargo, python3 and GNU time; JOB_OUT and JOB_CACHE say where results and the
# Rust build go.
#
#   cd metalibrary && cert/run.sh N [N ...]
#
# Needs cert/blocks_<N_N...>.txt and cert/cells_<N_N...>.txt (cert/plan.py N ...). Results in
# $JOB_OUT/cert_<tag>/ (certificates), $JOB_OUT/check_<tag>.txt (the checker's report).
set -euo pipefail
tag=$(IFS=_; echo "$*")
: "${JOB_OUT:?set JOB_OUT (a directory for the results)}"
[ -f "$HOME/.cargo/env" ] && source "$HOME/.cargo/env"
export CARGO_TARGET_DIR="${JOB_CACHE:-$PWD/rust}/target"
(cd rust && cargo build --release -q --bin cert)
out="$JOB_OUT/cert_$tag"
echo "== cert (untrusted generator), threads 3"
/usr/bin/time -v "$CARGO_TARGET_DIR/release/cert" "cert/blocks_$tag.txt" "cert/cells_$tag.txt" "$out" 3 \
  2> "$JOB_OUT/cert_$tag.stderr"
grep -E "Maximum resident|Elapsed" "$JOB_OUT/cert_$tag.stderr"
du -sh "$out"
echo "== checker self-test on pi_22, pi_23"
small="$JOB_OUT/cert_22_23"
"$CARGO_TARGET_DIR/release/cert" cert/blocks_22_23.txt cert/cells_22_23.txt "$small" 1 2> /dev/null
python3 cert/selftest.py cert/cells_22_23.txt "$small" 22 23
echo "== check (independent), columns $*"
/usr/bin/time -v python3 cert/check.py "cert/cells_$tag.txt" "$out" "$@" > "$JOB_OUT/check_$tag.txt" \
  2> "$JOB_OUT/check_$tag.stderr" || { tail -3 "$JOB_OUT/check_$tag.stderr"; exit 1; }
grep -E "Maximum resident|Elapsed" "$JOB_OUT/check_$tag.stderr"
grep -v "^  " "$JOB_OUT/check_$tag.txt"
tar -C "$JOB_OUT" -czf "$JOB_OUT/cert_$tag.tar.gz" "cert_$tag"
