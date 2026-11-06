#!/usr/bin/env bash
# SpaSM against lowmem on blocks of the differential (MATH-106), as a tm job or anywhere with
# cargo, GNU time and the SpaSM build (spasm/build.sh).
#
#   cd metalibrary && spasm/bench.sh BLOCKS THREADS
#
# BLOCKS: lines "n s c [words]". For each block, three runs, each with THREADS threads:
#   lowmem  -- rows in parallel, elimination in one thread (rust/src/bin/lowmem.rs);
#   sms     -- the same rows written as an SMS matrix to /dev/null (the cost of the export alone);
#   spasm-plain, spasm-flip -- `sms [--flip] | rank --modulus 3`: SpaSM's elimination (OpenMP)
#              on the streamed matrix, columns in lowmem's order or reversed (SPASM_VARIANTS),
#              stopped after SPASM_TIMEOUT seconds (default 1800);
#   certlow -- the rank certificate in the format of cert/check.py (written to $JOB_OUT/cert_*/,
#              removed after the run unless KEEP_CERT=1).
# Results: $JOB_OUT/bench.csv (tool,n,s,c,rows,cols,nnz,rank,wall_s,maxrss_mb,spasm_echelon_s)
# and the raw stderr of every run in $JOB_OUT/logs/.
set -euo pipefail
blocks=$1 threads=$2
: "${JOB_OUT:=$PWD/out}"
mkdir -p "$JOB_OUT/logs"
source "$(dirname "$0")/cargo-env.sh"
export CARGO_TARGET_DIR="${JOB_CACHE:-$PWD/rust}/target"
(cd rust && cargo build --release -q --bin lowmem --bin sms --bin certlow)
B="$CARGO_TARGET_DIR/release"
SPASM_JOBS=$threads spasm/build.sh
RANK="${SPASM_HOME:-${JOB_CACHE:-$PWD}/spasm}/src/build/tools/rank"
export OMP_NUM_THREADS=$threads
csv="$JOB_OUT/bench.csv"
[ -f "$csv" ] || echo "tool,n,s,c,rows,cols,nnz,rank,wall_s,maxrss_mb,spasm_echelon_s" > "$csv"
wall() { awk -F': ' '/Elapsed \(wall clock\)/{n=split($2,a,":"); s=0; for(i=1;i<=n;i++) s=s*60+a[i]; print s}' "$1"; }
rss() { awk -F': ' '/Maximum resident/{printf "%.0f", $2/1024}' "$1"; }
grep -v '^#' "$blocks" | while read -r n s c _; do
  [ -n "$n" ] || continue
  tag="${n}_${s}_${c}"
  echo "== block $n $s $c"
  echo "$n $s $c" > "$JOB_OUT/logs/one.txt"
  /usr/bin/time -v "$B/lowmem" --blocks "$JOB_OUT/logs/one.txt" "$threads" > "$JOB_OUT/logs/lowmem_$tag.csv" 2> "$JOB_OUT/logs/lowmem_$tag.err"
  lr=$(tail -1 "$JOB_OUT/logs/lowmem_$tag.csv" | cut -d, -f5)
  grep '^block' "$JOB_OUT/logs/lowmem_$tag.err"
  /usr/bin/time -v "$B/sms" "$n" "$s" "$c" "$threads" > /dev/null 2> "$JOB_OUT/logs/sms_$tag.err"
  read -r rows cols nnz < <(sed -n 's/^sms .*: \([0-9]*\) x \([0-9]*\), \([0-9]*\) nonzeros.*/\1 \2 \3/p' "$JOB_OUT/logs/sms_$tag.err")
  echo "lowmem,$n,$s,$c,$rows,$cols,$nnz,$lr,$(wall "$JOB_OUT/logs/lowmem_$tag.err"),$(rss "$JOB_OUT/logs/lowmem_$tag.err")," >> "$csv"
  echo "sms,$n,$s,$c,$rows,$cols,$nnz,,$(wall "$JOB_OUT/logs/sms_$tag.err"),$(rss "$JOB_OUT/logs/sms_$tag.err")," >> "$csv"
  for variant in ${SPASM_VARIANTS:-plain flip}; do
    flag=; [ $variant = flip ] && flag=--flip
    set +e
    "$B/sms" "$n" "$s" "$c" "$threads" $flag 2> /dev/null | /usr/bin/time -v timeout "${SPASM_TIMEOUT:-1800}" "$RANK" --modulus 3 > /dev/null 2> "$JOB_OUT/logs/spasm_${variant}_$tag.err"
    st=$?
    set -e
    sr=$(sed -n 's/.*done in \([0-9.]*\) s rank = \([0-9]*\).*/\2/p' "$JOB_OUT/logs/spasm_${variant}_$tag.err")
    se=$(sed -n 's/.*done in \([0-9.]*\) s rank = \([0-9]*\).*/\1/p' "$JOB_OUT/logs/spasm_${variant}_$tag.err")
    if [ $st -eq 124 ]; then sr="timeout"; elif [ $st -ne 0 ]; then sr="fail($st)"; tail -5 "$JOB_OUT/logs/spasm_${variant}_$tag.err"; fi
    echo "spasm-$variant,$n,$s,$c,$rows,$cols,$nnz,$sr,$(wall "$JOB_OUT/logs/spasm_${variant}_$tag.err"),$(rss "$JOB_OUT/logs/spasm_${variant}_$tag.err"),$se" >> "$csv"
    tail -1 "$csv"
    [ "$sr" = "$lr" ] && echo "ranks agree: $lr" || echo "RANKS DIFFER: lowmem $lr, spasm-$variant $sr"
  done
  /usr/bin/time -v "$B/certlow" "$JOB_OUT/logs/one.txt" "$JOB_OUT/cert_$tag" "$threads" 2> "$JOB_OUT/logs/certlow_$tag.err"
  cr=$(sed -n 's/.*, rank \([0-9]*\), .*/\1/p' "$JOB_OUT/logs/certlow_$tag.err")
  echo "certlow,$n,$s,$c,$rows,$cols,$nnz,$cr,$(wall "$JOB_OUT/logs/certlow_$tag.err"),$(rss "$JOB_OUT/logs/certlow_$tag.err")," >> "$csv"
  grep '^block' "$JOB_OUT/logs/certlow_$tag.err"; du -sh "$JOB_OUT/cert_$tag"
  [ "${KEEP_CERT:-0}" = 1 ] || rm -rf "$JOB_OUT/cert_$tag"
done
