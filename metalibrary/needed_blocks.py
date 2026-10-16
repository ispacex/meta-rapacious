# -*- coding: utf-8 -*-
"""
Which block ranks are still needed after the colour solver and the ranks already computed.

    python3 needed_blocks.py COLOURS.csv RANKS.csv [RANKS.csv ...] > data/needed_blocks.txt

Lines "n s c words", smallest first; a summary goes to stderr: how many, how many words, and
which of them are larger than 3e7 words (too big for one 13G job with the current code).
"""
import collections
import csv
import sys

from colour_solver import word_counts


def main():
    open_cells = collections.defaultdict(set)
    for r in csv.DictReader(open(sys.argv[1])):
        if r["status"] != "determined":
            open_cells[(int(r["n"]), int(r["s"]))].add(int(r["colour"]))
    done = set()
    for fn in sys.argv[2:]:
        for r in csv.DictReader(open(fn)):
            done.add((int(r["n"]), int(r["s"]), int(r["colour"])))
    W = word_counts(max(n for n, _ in open_cells) + 2)
    need = set()
    for (n, s), cs in open_cells.items():
        for c in cs:
            need.add((n, s, c))
            if s >= 2:
                need.add((n + 1, s - 1, c))
    rows = []
    for (n, s, c) in need - done:
        a = W.get(n)
        w = int(a[s, c]) if a is not None and s < a.shape[0] and c < a.shape[1] else 0
        if w:
            rows.append((w, n, s, c))
    rows.sort()
    big = [r for r in rows if r[0] > 30_000_000]
    print(f"open cells: {sorted(open_cells)}", file=sys.stderr)
    print(f"blocks still needed: {len(rows)}, {sum(r[0] for r in rows):.3g} words; "
          f"over 3e7 words: {len(big)} ({sum(r[0] for r in big):.3g}): {[(n, s, c, f'{w:.2g}') for w, n, s, c in big]}",
          file=sys.stderr)
    for w, n, s, c in rows:
        print(n, s, c, w)


if __name__ == "__main__":
    main()
