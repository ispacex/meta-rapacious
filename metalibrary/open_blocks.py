# -*- coding: utf-8 -*-
"""
Blocks whose rank is needed to settle the colours colour_solver.py left open.

    python3 open_blocks.py [data/e2_colours.csv] > data/open_blocks.txt

For an open cell (n, s) and every colour c it may still have,
    dim E^2(n, s, c) = #words(n, s, c) - rank d|(n, s, c) - rank d|(n+1, s-1, c),
so both blocks are listed (once each), with their numbers of words, smallest first.
Output lines: n s c words.
"""
import collections
import csv
import pathlib
import sys

from colour_solver import word_counts

HERE = pathlib.Path(__file__).resolve().parent


def main():
    fn = sys.argv[1] if len(sys.argv) > 1 else HERE / "data" / "e2_colours.csv"
    open_cells = collections.defaultdict(set)
    for r in csv.DictReader(open(fn)):
        if r["status"] != "determined":
            open_cells[(int(r["n"]), int(r["s"]))].add(int(r["colour"]))
    nmax = max(n for n, _ in open_cells) + 1
    W = word_counts(nmax)
    blocks = set()
    for (n, s), cs in open_cells.items():
        for c in cs:
            blocks.add((n, s, c))
            if s >= 2:
                blocks.add((n + 1, s - 1, c))
    rows = []
    for (n, s, c) in blocks:
        a = W.get(n)
        w = int(a[s, c]) if a is not None and s < a.shape[0] and c < a.shape[1] else 0
        if w:
            rows.append((w, n, s, c))
    rows.sort()
    tot = sum(r[0] for r in rows)
    print(f"# {len(open_cells)} open cells, {len(rows)} blocks, {tot} words in all, largest {rows[-1][0]}",
          file=sys.stderr)
    for w, n, s, c in rows:
        print(n, s, c, w)


if __name__ == "__main__":
    main()
