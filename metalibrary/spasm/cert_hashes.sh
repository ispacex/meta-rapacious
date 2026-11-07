#!/usr/bin/env bash
# Certificates of block ranks, checked and then thrown away (MATH-106): for each block, certlow
# writes the certificate, cert/check.py (check_block, unchanged) checks it, and only its sha256
# and the checked rank are kept. certlow is deterministic, so the file can be rebuilt and compared
# with the hash.
#
#   cd metalibrary && spasm/cert_hashes.sh BLOCKS PAR
#
# Result: $JOB_OUT/cert_hashes.csv: n,s,colour,words,rank,bytes,sha256 -- rank is the one check.py
# accepted; a block certificate proves rank >= that number (the exact rank also needs an upper
# bound, which cert/ gets from cell certificates). A block whose check fails is listed in $JOB_OUT/failed.txt. check.py needs about
# 2-6 KB per word (its caches grow with the length of the words), so PAR blocks need PAR times
# that. CHECK_MEM_GB caps each check's address space (ulimit -v): a block that needs more fails
# with MemoryError and is listed as "n s c memory" instead of the whole job being killed.
set -euo pipefail
blocks=$1 par=$2
: "${JOB_OUT:=$PWD/out}"
mkdir -p "$JOB_OUT/logs" "$JOB_OUT/tmp"
: > "$JOB_OUT/failed.txt"
rm -f "$JOB_OUT"/logs/*.csv
source "$(dirname "$0")/cargo-env.sh"
export CARGO_TARGET_DIR="${JOB_CACHE:-$PWD/rust}/target"
(cd rust && cargo build --release -q --bin certlow)
export B="$CARGO_TARGET_DIR/release" JOB_OUT CHECK_MEM_GB
one() {
  set -uo pipefail
  read -r n s c _ <<< "$1"
  tag="${n}_${s}_${c}" d="$JOB_OUT/tmp/$tag"
  mkdir -p "$d"
  echo "$n $s $c" > "$d/b.txt"
  if "$B/certlow" "$d/b.txt" "$d" 1 2> "$JOB_OUT/logs/$tag.gen" \
     && ( [ -z "${CHECK_MEM_GB:-}" ] || ulimit -v $((CHECK_MEM_GB * 1024 * 1024))
          exec python3 -I spasm/check_block.py "$d/block_$tag.txt" ) > "$d/ok" 2> "$JOB_OUT/logs/$tag.check"; then
    r=$(cut -d, -f4 "$d/ok")
    w=$(head -1 "$d/block_$tag.txt" | cut -d' ' -f6)
    echo "$n,$s,$c,$w,$r,$(wc -c < "$d/block_$tag.txt" | tr -d ' '),$( (sha256sum 2>/dev/null || shasum -a 256) < "$d/block_$tag.txt" | cut -c1-64)" > "$JOB_OUT/logs/$tag.csv"
  else
    why=check; grep -q MemoryError "$JOB_OUT/logs/$tag.check" 2>/dev/null && why=memory
    echo "$n $s $c $why" >> "$JOB_OUT/failed.txt"
  fi
  rm -rf "$d"
}
export -f one
grep -v '^#' "$blocks" | grep . | xargs -P "$par" -I{} bash -c 'one "$@"' _ {} || true
{ echo "n,s,colour,words,rank,bytes,sha256"; cat "$JOB_OUT"/logs/*.csv 2>/dev/null | sort -t, -k1,1n -k2,2n -k3,3n; } > "$JOB_OUT/cert_hashes.csv"
ok=$(($(wc -l < "$JOB_OUT/cert_hashes.csv") - 1)) bad=$(wc -l < "$JOB_OUT/failed.txt" | tr -d " ")
total=$(grep -v '^#' "$blocks" | grep -c .)
echo "$ok blocks checked; $bad failed; $((total - ok - bad)) missing (of $total)"
[ $((ok + bad)) -eq "$total" ]
