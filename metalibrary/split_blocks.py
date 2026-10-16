# -*- coding: utf-8 -*-
"""
Split a block list (n s c words) for one 13G job: small blocks in parallel, large one at a time.

    python3 split_blocks.py LIST MAXWORDS SMALL_LIMIT OUT_PARALLEL OUT_SEQUENTIAL [DONE.csv ...]

Blocks above MAXWORDS are left out (reported); blocks already in DONE.csv files are skipped.
Measured on the worker: a block of 5e6 words takes about 1.6 GB, so 3 threads are safe up to
about SMALL_LIMIT = 1.2e7 words and larger blocks go one at a time.
"""
import csv
import sys


def main():
    fn, maxw, small = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    outp, outs = sys.argv[4], sys.argv[5]
    done = set()
    for d in sys.argv[6:]:
        for r in csv.DictReader(open(d)):
            done.add((r["n"], r["s"], r["colour"]))
    rows = [l.split() for l in open(fn) if l.strip()]
    rows = [r for r in rows if tuple(r[:3]) not in done]
    par = [r for r in rows if int(r[3]) <= small]
    seq = [r for r in rows if small < int(r[3]) <= maxw]
    left = [r for r in rows if int(r[3]) > maxw]
    open(outp, "w").write("".join(" ".join(r) + "\n" for r in par))
    open(outs, "w").write("".join(" ".join(r) + "\n" for r in seq))
    print(f"parallel: {len(par)} blocks, {sum(int(r[3]) for r in par):.3g} words; "
          f"sequential: {len(seq)}, {sum(int(r[3]) for r in seq):.3g}; left out (> {maxw:.0e}): {len(left)}")


if __name__ == "__main__":
    main()
