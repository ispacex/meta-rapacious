# -*- coding: utf-8 -*-
"""
Pick K blocks of a rank file with words in [LO, HI], spread evenly over sizes.

    python3 pick_blocks.py RANKS.csv LO HI K OUT       # OUT: lines "n s c words"
"""
import csv
import sys


def main():
    fn, lo, hi, k, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    rows = sorted((int(r["words"]), r["n"], r["s"], r["colour"]) for r in csv.DictReader(open(fn))
                  if lo <= int(r["words"]) <= hi)
    pick = [rows[round(i * (len(rows) - 1) / (k - 1))] for i in range(k)] if len(rows) >= k else rows
    pick = sorted(set(pick))
    open(out, "w").write("".join(f"{n} {s} {c} {w}\n" for w, n, s, c in pick))
    print(f"{len(pick)} blocks, {sum(p[0] for p in pick)} words, largest {pick[-1][0]} -> {out}")


if __name__ == "__main__":
    main()
