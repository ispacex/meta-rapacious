#!/usr/bin/env bash
# Independent blocks in parallel (MATH-106, step 2): PAR copies of lowmem (or certlow) at once,
# each on its own block with THREADS threads for its rows; the single-threaded eliminations of
# different blocks then run side by side.
#
#   cd metalibrary && spasm/par_blocks.sh BLOCKS PAR THREADS [lowmem|certlow]
#
# Results: $JOB_OUT/ranks.csv (n,s,colour,words,rank), per-block logs in $JOB_OUT/logs/, and for
# certlow the certificates in $JOB_OUT/cert/ (block_n_s_c.txt.gz). Memory is PAR times one
# block's; order BLOCKS so that the large ones do not meet.
set -euo pipefail
blocks=$1 par=$2 threads=$3 tool=${4:-lowmem}
: "${JOB_OUT:=$PWD/out}"
mkdir -p "$JOB_OUT/logs" "$JOB_OUT/cert"
[ -f "$HOME/.cargo/env" ] && source "$HOME/.cargo/env"
export CARGO_TARGET_DIR="${JOB_CACHE:-$PWD/rust}/target"
(cd rust && cargo build --release -q --bin "$tool")
export B="$CARGO_TARGET_DIR/release" tool threads JOB_OUT
one() {
  set -euo pipefail
  read -r n s c _ <<< "$1"
  tag="${n}_${s}_${c}"
  echo "$n $s $c" > "$JOB_OUT/logs/$tag.txt"
  if [ "$tool" = certlow ]; then
    "$B/certlow" "$JOB_OUT/logs/$tag.txt" "$JOB_OUT/cert" "$threads" 2> "$JOB_OUT/logs/$tag.err"
    gzip -f "$JOB_OUT/cert/block_$tag.txt"
    sed -n 's/^block \([0-9]*\) \([0-9]*\) \([0-9]*\): \([0-9]*\) x [0-9]*, rank \([0-9]*\),.*/\1,\2,\3,\4,\5/p' \
      "$JOB_OUT/logs/$tag.err" > "$JOB_OUT/logs/$tag.csv"
  else
    "$B/lowmem" --blocks "$JOB_OUT/logs/$tag.txt" "$threads" 2> "$JOB_OUT/logs/$tag.err" \
      | tail -n +2 > "$JOB_OUT/logs/$tag.csv"
  fi
  cat "$JOB_OUT/logs/$tag.err"
}
export -f one
grep -v '^#' "$blocks" | grep . | xargs -P "$par" -I{} bash -c 'one "$@"' _ {}
{ echo "n,s,colour,words,rank"; cat "$JOB_OUT"/logs/*.csv | sort -t, -k1,1n -k2,2n -k3,3n; } > "$JOB_OUT/ranks.csv"
echo "$(($(wc -l < "$JOB_OUT/ranks.csv") - 1)) blocks -> $JOB_OUT/ranks.csv"
