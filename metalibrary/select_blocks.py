# -*- coding: utf-8 -*-
"""
Choose which still-needed blocks to compute first: those that settle the open cells with the
smallest n, within a budget of words.

    python3 select_blocks.py COLOURS.csv BUDGET OUT RANKS.csv [RANKS.csv ...]

Open cells come from COLOURS.csv (colour_solver output). A cell (n, s) with possible colour c
needs the ranks of the blocks (n, s, c) and (n+1, s-1, c). Cells are taken in increasing n,
each with all its blocks, while the total number of words stays within BUDGET; blocks already
in RANKS.csv are skipped. OUT gets lines "n s c words", smallest first (lowmem takes them in
order, one block at a time, all threads on each block).
"""
import collections
import csv
import sys

from colour_solver import word_counts


def main():
    fn, budget, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    done = set()
    for f in sys.argv[4:]:
        for r in csv.DictReader(open(f)):
            done.add((int(r["n"]), int(r["s"]), int(r["colour"])))
    cells = collections.defaultdict(set)
    for r in csv.DictReader(open(fn)):
        if r["status"] != "determined":
            cells[(int(r["n"]), int(r["s"]))].add(int(r["colour"]))
    W = word_counts(max(n for n, _ in cells) + 2)

    def words(n, s, c):
        a = W.get(n)
        return int(a[s, c]) if a is not None and 0 < s < a.shape[0] and 0 <= c < a.shape[1] else 0

    chosen, total, closed = {}, 0, []
    for (n, s) in sorted(cells):
        need = {}
        for c in cells[(n, s)]:
            for b in ((n, s, c), (n + 1, s - 1, c)):
                if b[1] >= 1 and b not in done and b not in chosen and words(*b):
                    need[b] = words(*b)
        if total + sum(need.values()) > budget:
            break
        chosen.update(need)
        total += sum(need.values())
        closed.append((n, s))
    rows = sorted((w, b) for b, w in chosen.items())
    open(out, "w").write("".join(f"{b[0]} {b[1]} {b[2]} {w}\n" for w, b in rows))
    print(f"{len(rows)} blocks, {total:.3g} words, largest {rows[-1][0] if rows else 0:.3g}; "
          f"closes cells {closed}; open cells left: {sorted(set(cells) - set(closed))}")


if __name__ == "__main__":
    main()
