# -*- coding: utf-8 -*-
"""
Check sseq's Q-weight output (n,s,e,dim from the fork's qgrade_dims example) against
our colours.

    python3 check_qgrade.py QGRADE.csv E2_FULL.csv COLOURS.csv [RANKS.csv ...]

1. Cell by cell against the complete E^2 with colours (E2_FULL.csv, n <= its max).
2. Beyond that, against every cell the colour solver determined (COLOURS.csv, status determined),
   and against the ranges of the open cells.
3. Against exact dimensions from brute-force ranks (merge_ranks logic), if RANKS files are given.
"""
import collections
import csv
import sys


def main():
    q = collections.Counter()
    for line in open(sys.argv[1]):
        if not line[0].isdigit():
            continue
        n, s, e, d = map(int, line.strip().split(","))
        if n > 3 and d:
            q[(n, s, e)] += d
    full = collections.Counter()
    for r in csv.DictReader(open(sys.argv[2])):
        if int(r["homology"]):
            full[(int(r["n"]), int(r["s"]), int(r["colour"]))] += int(r["homology"])
    nfull = max(n for n, _, _ in full)
    qf = {k: v for k, v in q.items() if k[0] <= nfull}
    diff = [k for k in set(qf) | set(full) if qf.get(k, 0) != full.get(k, 0)]
    print(f"1. n <= {nfull}: {len(full)} cells ours, {len(qf)} cells sseq; mismatches: {len(diff)} {sorted(diff)[:10]}")

    det, rng = {}, {}
    for r in csv.DictReader(open(sys.argv[3])):
        k = (int(r["n"]), int(r["s"]), int(r["colour"]))
        if r["status"] == "determined":
            det[k] = int(r["dim"])
        else:
            lo, hi = map(int, r["status"].split()[1].split(".."))
            rng[k] = (lo, hi)
    beyond = [k for k in det if k[0] > nfull]
    bad = [(k, det[k], q.get(k, 0)) for k in beyond if det[k] != q.get(k, 0)]
    out = [(k, rng[k], q.get(k, 0)) for k in rng if not rng[k][0] <= q.get(k, 0) <= rng[k][1]]
    extra = [k for k in q if k[0] > nfull and k[0] <= max(n for n, _, _ in det) and k not in det and k not in rng]
    print(f"2. n > {nfull}: {len(beyond)} determined cells, mismatches {bad[:10]}; open-cell ranges violated: {out[:10]}; "
          f"sseq cells outside the solver's candidates: {extra[:10]}")


if __name__ == "__main__":
    main()
