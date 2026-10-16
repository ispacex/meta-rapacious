#!/usr/bin/env bash
# Converts the site's flat search index into the two-tier form that ispacex.github.io's search
# engine reads (https://github.com/tombouctou/sitesearch, FORMAT.md).
#
#   site/two_tier.sh OUT_DIR
#
# The engine is used from the main site (/sitesearch/search.js on the same origin), so the index
# has to be built with the same engine version that site serves: the word fold of the map must be
# the fold of the engine in the browser. The version is read from the submodule pointer of
# ispacex/ispacex.github.io and checked out into a temporary directory; nothing of the engine is
# copied into this repository. (The flat-index path of that version cannot read a flat index:
# `called is not defined`, fixed upstream in 5105088; the two-tier path is what the main site
# itself uses.)
set -euo pipefail
out=$(cd "$1" && pwd)
rev=$(curl -fsSL https://api.github.com/repos/ispacex/ispacex.github.io/contents/sitesearch \
  | python3 -c 'import json, sys; print(json.load(sys.stdin)["sha"])')
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
git clone -q https://github.com/tombouctou/sitesearch.git "$tmp/sitesearch"
git -C "$tmp/sitesearch" checkout -q "$rev"
mkdir -p "$tmp/root/metalibrary"
cp "$out/search-index.json" "$tmp/root/metalibrary/"
node "$tmp/sitesearch/node/two-tier.js" "$tmp/root" /metalibrary/search-index.json
rm -rf "$out/search-index-text"
cp -R "$tmp/root/metalibrary/." "$out/"
echo "two-tier index from sitesearch $rev: $(ls "$out/search-index-text" | wc -l | tr -d ' ') chunks"
