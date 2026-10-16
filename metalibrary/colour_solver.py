# -*- coding: utf-8 -*-
"""
Colours of the E^2 classes of the coloured metalibrary without computing its homology.

    python3 colour_solver.py SSEQ.csv NMAX [CHECK.csv] [--out DIR]

Inputs:
  SSEQ.csv   unstable Ext of S^3 at p = 3 from sseq/ext, lines n,s,dim (n = t - s). For n > 3
             it equals the homology of the metalibrary by (n, s): checked up to n = 64
             (compare_sseq.py); beyond that it is the assumption of this method.
  CHECK.csv  optional: homology by (n, s, colour) from metalib.py / rust (e2_metalib.csv),
             to test the method where the colours are known.

Method. The differential keeps m = n + s and the colour, so for every antidiagonal m and colour c
    chi(m, c) = sum_s (-1)^s #words(m - s, s, c) = sum_s (-1)^s dim E^2(m - s, s, c),
and the word counts are cheap. Moreover colour = stem + s = m - 3 (mod 4) for every word on the
antidiagonal m, and 0 <= colour <= s - 1 (the last letter is a lambda). For every antidiagonal the
unknowns x[(n, s), c] >= 0 (how many classes of the cell (n, s) have colour c) satisfy
    sum_c x[(n, s), c] = dim E^2(n, s),      sum_{(n, s)} (-1)^s x[(n, s), c] = chi(m, c),
and an integer program gives the least and the greatest possible value of every x. Where they
coincide for all c, the colours of the cell are determined.

Word counts are kept modulo 2^64 (numpy int64 wraps); chi is a small integer, so this is exact.
Output (in DIR, default data/): e2_colours.csv  n,s,colour,dim,status   with status
"determined" (dim exact) or "range lo..hi" (cell not determined: dim is any value in the range).
"""
import collections
import csv
import pathlib
import sys
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent


def word_counts(nmax):
    """W[n] = array (length, colour) of the numbers of metalibrary words over pi_n, mod 2^64."""
    stmax = nmax - 3
    L = stmax // 3 + 2
    cnt = collections.defaultdict(dict)       # (kind, i) -> stem -> array: words ending with that letter
    out = collections.defaultdict(lambda: np.zeros((L, L), dtype=np.int64))
    for kind in (0, 1):                        # 0: lambda_1 (stem 3), 1: mu_1 (stem 4)
        a = np.zeros((L, L), dtype=np.int64)
        a[1, kind] = 1
        cnt[(kind, 1)][3 + kind] = a
    with np.errstate(over="ignore"):
        for st in range(3, stmax + 1):
            for (kind, i), bystem in list(cnt.items()):
                a = bystem.pop(st, None)
                if a is None:
                    continue
                if kind == 0:
                    out[st + 3] += a
                top = 3 * i - (0 if kind else 1)
                for j in range(1, top + 1):
                    for k2 in (0, 1):
                        d = 4 * j - (0 if k2 else 1)
                        if st + d > stmax:
                            continue
                        b = np.zeros_like(a)
                        b[1:, k2:] = a[:-1, :L - k2]
                        t = cnt[(k2, j)]
                        if st + d in t:
                            t[st + d] += b
                        else:
                            t[st + d] = b
    return out


def solve_antidiagonal(cells, h, chi, known=None):
    """cells: [(n, s)], h: dims, chi: {c: value}. Returns {(n, s): {c: (lo, hi)}}."""
    from scipy.optimize import Bounds, LinearConstraint, milp  # only here: word_counts needs numpy alone
    res = None
    var = []
    for (n, s) in cells:
        m = n + s
        for c in range((m - 3) % 4, s, 4):
            var.append(((n, s), c))
    colours = sorted({c for _, c in var} | set(chi))
    A, lb, ub = [], [], []
    for cell in cells:                         # sum over colours = dim
        A.append([1 if v[0] == cell else 0 for v in var])
        lb.append(h[cell])
        ub.append(h[cell])
    for c in colours:                          # signed sum per colour = chi
        A.append([(-1) ** v[0][1] if v[1] == c else 0 for v in var])
        lb.append(chi.get(c, 0))
        ub.append(chi.get(c, 0))
    cons = LinearConstraint(np.array(A, dtype=float), lb, ub)
    known = known or {}
    lo_b = [known.get((v[0][0], v[0][1], v[1]), 0) for v in var]
    hi_b = [known.get((v[0][0], v[0][1], v[1]), h[v[0]]) for v in var]
    bounds = Bounds(np.array(lo_b, dtype=float), np.array(hi_b, dtype=float))
    integ = np.ones(len(var))
    rng = {}
    for i in range(len(var)):
        cost = np.zeros(len(var))
        cost[i] = 1
        lo = milp(cost, constraints=cons, bounds=bounds, integrality=integ)
        hi = milp(-cost, constraints=cons, bounds=bounds, integrality=integ)
        if lo.status != 0 or hi.status != 0:
            return None
        rng[var[i]] = (round(lo.fun), round(-hi.fun))
    res = collections.defaultdict(dict)
    for (cell, c), r in rng.items():
        res[cell][c] = r
    return res


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    outdir = pathlib.Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else HERE / "data"
    if "--out" in sys.argv:
        args.remove(str(outdir))
    known = {}
    if "--known" in sys.argv:          # exact dims from merge_ranks.py: n,s,colour,dim
        kf = sys.argv[sys.argv.index("--known") + 1]
        args.remove(kf)
        for r in csv.DictReader(open(kf)):
            known[(int(r["n"]), int(r["s"]), int(r["colour"]))] = int(r["dim"])
    sseq_fn, nmax = args[0], int(args[1])
    t0 = time.time()
    h = collections.Counter()
    for line in open(sseq_fn):
        n, s, k = map(int, line.split(","))
        if n > 3 and k:
            h[(n, s)] += k
    nseq = max(n for n, _ in h)
    W = word_counts(nseq)
    print(f"word counts to n={nseq}: {time.time() - t0:.1f}s", flush=True)

    def chi(m, c):
        tot = 0
        for s in range(1, m):
            n = m - s
            if n < 4 or n > nseq:
                continue
            a = W.get(n)
            if a is None or s >= a.shape[0] or c >= a.shape[1]:
                continue
            tot += (-1) ** s * int(a[s, c])
        return tot

    result, stats, failed = {}, collections.Counter(), []
    mmax = max(n + s for (n, s) in h if n <= nmax)
    for m in range(5, mmax + 1):
        cells = sorted((n, s) for (n, s) in h if n + s == m)
        if not cells:
            continue
        if m - 1 > nseq:
            raise SystemExit(f"antidiagonal m={m} needs sseq beyond n={nseq}")
        res = (m - 3) % 4
        chis = {c: chi(m, c) for c in range(res, m, 4)}
        chis = {c: v for c, v in chis.items() if v}
        sol = solve_antidiagonal(cells, h, chis, known)
        if sol is None:
            failed.append(m)
            continue
        for cell in cells:
            if cell[0] > nmax:
                continue
            det = all(lo == hi for lo, hi in sol[cell].values())
            stats["determined" if det else "open"] += h[cell]
            for c, (lo, hi) in sol[cell].items():
                if hi > 0:
                    result[(cell[0], cell[1], c)] = (lo, hi)
    print(f"n <= {nmax}: classes in determined cells {stats['determined']}, in open cells {stats['open']}; "
          f"infeasible antidiagonals: {failed or 'none'}; {time.time() - t0:.1f}s")
    if len(args) > 2:
        true = collections.Counter()
        for r in csv.DictReader(open(args[2])):
            if int(r["homology"]) and int(r["n"]) > 3:
                true[(int(r["n"]), int(r["s"]), int(r["colour"]))] += int(r["homology"])
        nchk = max(n for n, _, _ in true)
        bad = [(k, v, true[k]) for k, v in result.items() if k[0] <= nchk and not (v[0] <= true[k] <= v[1])]
        miss = [k for k in true if k not in result]
        det_ok = sum(1 for k, v in result.items() if k[0] <= nchk and v[0] == v[1] == true[k])
        print(f"check vs {args[2]} (n <= {nchk}): {'consistent' if not bad and not miss else 'INCONSISTENT'}; "
              f"exact cells {det_ok}; bad {bad[:10]} missing {miss[:10]}")
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "e2_colours.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["n", "s", "colour", "dim", "status"])
        for (n, s, c), (lo, hi) in sorted(result.items()):
            w.writerow([n, s, c, lo if lo == hi else "", "determined" if lo == hi else f"range {lo}..{hi}"])
    print("wrote", outdir / "e2_colours.csv")


if __name__ == "__main__":
    main()
