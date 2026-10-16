#!/usr/bin/env bash
# The Lean check of the certificates, as a job on a remote box (remote/mr-remote.sh) or anywhere
# with elan (and, for TAG 22_23, cargo).
#
#   cd metalibrary/cert/lean && ./run.sh TAG N:HIGH:LOW [...]
#
# TAG 22_23 makes its certificates with the Rust generator; any other TAG takes
# cert_<TAG>.tar.gz from the directory $CERT_ARCHIVE if it is set, otherwise from the published
# release (certificates-2026-10-15 of ispacex/metalibrary), checked against its SHA256SUMS.
# The archives are not in git. The claim is ../cells_<TAG>.txt.
set -euo pipefail
CERT_ARCHIVE=${CERT_ARCHIVE:-}
RELEASE=https://github.com/ispacex/metalibrary/releases/download/certificates-2026-10-15
tag=$1; shift
export PATH="$HOME/.elan/bin:$PATH"
mkdir -p data
rm -rf "data/cert_$tag"
if [ "$tag" = 22_23 ]; then
  [ -f "$HOME/.cargo/env" ] && source "$HOME/.cargo/env"
  export CARGO_TARGET_DIR="${JOB_CACHE:-$PWD/../../rust}/target"
  (cd ../../rust && cargo build --release -q --bin cert)
  "$CARGO_TARGET_DIR/release/cert" ../blocks_22_23.txt ../cells_22_23.txt "data/cert_$tag" 1 2> /dev/null
else
  if [ -z "$CERT_ARCHIVE" ]; then
    CERT_ARCHIVE=data/release
    mkdir -p "$CERT_ARCHIVE"
    curl -fsSL -o "$CERT_ARCHIVE/SHA256SUMS" "$RELEASE/SHA256SUMS"
    curl -fsSL -o "$CERT_ARCHIVE/cert_$tag.tar.gz" "$RELEASE/cert_$tag.tar.gz"
    (cd "$CERT_ARCHIVE" && grep " cert_$tag.tar.gz\$" SHA256SUMS | sha256sum -c -)
  fi
  tar -C data -xzf "$CERT_ARCHIVE/cert_$tag.tar.gz"
fi
cp "../cells_$tag.txt" "data/cert_$tag/cells.txt"
python3 gen_stage.py "$tag" "$@"
lake --version
/usr/bin/time -v lake build "MetalibCert.Stage_$tag" 2> "${JOB_OUT:-.}/lean_$tag.stderr" || { tail -40 "${JOB_OUT:-.}/lean_$tag.stderr"; exit 1; }
grep -E "Maximum resident|Elapsed" "${JOB_OUT:-.}/lean_$tag.stderr"
echo "Lean: MetalibCert.Stage_$tag.rule_survivors checked"
