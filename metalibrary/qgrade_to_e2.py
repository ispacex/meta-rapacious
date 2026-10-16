# -*- coding: utf-8 -*-
"""
E^2 with colours from sseq's Q-weight (fork ispacex/sseq, branch math-54-qgrade, example
qgrade_dims: lines n,s,e,dim with n = t - s for S_3[3]) in the format of rapacious.py.

    python3 qgrade_to_e2.py QGRADE.csv > data/e2_qgrade.csv

colour = e: checked cell by cell against the lambda-algebra computation for all n <= 75 and for
every cell computed by brute force up to n = 85 (check_qgrade.py). The tower over pi_3 is left out.
"""
import csv
import sys


def main():
    w = csv.writer(sys.stdout, lineterminator="\n")
    w.writerow(["n", "s", "colour", "words", "rank_out", "homology"])
    for line in open(sys.argv[1]):
        if not line[0].isdigit():
            continue
        n, s, e, d = map(int, line.strip().split(","))
        if n > 3 and d:
            w.writerow([n, s, e, "", "", d])


if __name__ == "__main__":
    main()
