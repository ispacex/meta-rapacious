# -*- coding: utf-8 -*-
"""
Exact dimensions of E^2 cells from block ranks computed on the worker.

    python3 merge_ranks.py RANKS.csv [RANKS.csv ...] > data/e2_known.csv

RANKS.csv: "n,s,colour,words,rank" from `metalib --blocks`. For a cell (n, s, c)
    dim E^2(n, s, c) = #words(n, s, c) - rank(n, s, c) - rank(n+1, s-1, c),
known when both ranks are (a block without words has rank 0; word counts come from
colour_solver.word_counts and are checked against the counts the ranks came with).
Output: n,s,colour,dim for every cell whose dimension is now known.
"""
import csv
import sys

from colour_solver import word_counts


def main():
    rank, words = {}, {}
    for fn in sys.argv[1:]:
        for r in csv.DictReader(open(fn)):
            k = (int(r["n"]), int(r["s"]), int(r["colour"]))
            rank[k], words[k] = int(r["rank"]), int(r["words"])
    nmax = max(n for n, _, _ in rank) + 1
    W = word_counts(nmax)

    def nwords(n, s, c):
        a = W.get(n)
        return int(a[s, c]) if a is not None and 0 < s < a.shape[0] and 0 <= c < a.shape[1] else 0

    for k, w in words.items():
        assert nwords(*k) == w, f"word count mismatch at {k}: {nwords(*k)} vs {w}"

    def rk(n, s, c):
        if (n, s, c) in rank:
            return rank[(n, s, c)]
        return 0 if nwords(n, s, c) == 0 else None

    out = csv.writer(sys.stdout, lineterminator="\n")
    out.writerow(["n", "s", "colour", "dim"])
    for (n, s, c) in sorted(rank):
        a, b = rk(n, s, c), rk(n + 1, s - 1, c)
        if a is not None and b is not None:
            out.writerow([n, s, c, nwords(n, s, c) - a - b])


if __name__ == "__main__":
    main()
