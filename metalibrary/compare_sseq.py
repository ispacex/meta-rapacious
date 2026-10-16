# -*- coding: utf-8 -*-
"""
Compare the homology of the coloured metalibrary with the unstable Adams E_2 of S^3 at p = 3
computed independently by sseq/ext (resolve_unstable, module S_3[3]; lines n,s,dim).

    python3 compare_sseq.py e2_metalib.csv sseq_S3_p3.csv

Both are indexed by n (pi_n(S^3)) and s. The tower over pi_3 = Z is left out: the metalibrary
has no mu_0 and so no words over pi_3.
"""
import collections
import csv
import sys


def main():
    mine = collections.Counter()
    nmax = 0
    for r in csv.DictReader(open(sys.argv[1])):
        n, s, h = int(r["n"]), int(r["s"]), int(r["homology"])
        nmax = max(nmax, n)
        if h:
            mine[(n, s)] += h
    ref = collections.Counter()
    for line in open(sys.argv[2]):
        n, s, k = map(int, line.split(","))
        if 3 < n <= nmax and k:
            ref[(n, s)] += k
    diff = sorted(k for k in set(mine) | set(ref) if mine[k] != ref[k])
    print(f"metalibrary vs sseq, 4 <= n <= {nmax}: {sum(mine.values())} classes,",
          "identical in every (n, s)" if not diff else f"DIFFER at {[(k, mine[k], ref[k]) for k in diff[:20]]}")
    return not diff


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
