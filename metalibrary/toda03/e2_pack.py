# -*- coding: utf-8 -*-
"""Packs (KLAM as in e2_job.sh) the output of e2_job.sh into one text file (e2_packed.txt, read by check.py):

    L n k s:dim,s:dim,...      H(Lambda(m)) for S^n, n = 2m + 1, stem k
    S n k s:dim,s:dim,...      sseq/ext, resolve_unstable of S_3[n] (S^n), stem k = (t - s) - n

    python3 -I e2_pack.py JOB_OUT > e2_packed.txt
"""
import collections
import os
import pathlib
import re
import sys

d = pathlib.Path(sys.argv[1])
for f in sorted(d.glob("lambda_m*.csv"), key=lambda p: int(re.search(r"(\d+)", p.name).group(1))):
    acc = collections.defaultdict(dict)
    for line in f.read_text().splitlines()[1:]:
        m, k, s, x = map(int, line.split(","))
        acc[(2 * m + 1, k)][s] = x
    m = int(re.search(r"(\d+)", f.name).group(1))
    print("#L", 2 * m + 1, "kmax", os.environ.get("KLAM", "58"))
    for (n, k), v in sorted(acc.items()):
        print("L", n, k, ",".join(f"{s}:{x}" for s, x in sorted(v.items())))
for f in sorted(d.glob("sseq_S*.csv"), key=lambda p: int(re.search(r"(\d+)", p.name).group(1))):
    n = int(re.search(r"S(\d+)", f.name).group(1))
    acc, kmax = collections.defaultdict(dict), None
    for line in f.read_text().splitlines():
        ts, s, x = map(int, line.split(","))   # ts = t - s, the homotopy degree
        kmax = ts - n if kmax is None else max(kmax, ts - n)
        if x and ts - n >= 1:
            acc[ts - n][s] = x
    if kmax is None:
        continue
    print("#S", n, "kmax", kmax)
    for k, v in sorted(acc.items()):
        print("S", n, k, ",".join(f"{s}:{x}" for s, x in sorted(v.items())))
