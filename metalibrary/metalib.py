# -*- coding: utf-8 -*-
"""
Homology of Mikhailov's coloured metalibrary and of Lambda(1), split by colour.

    python3 metalib.py NMAX [lambda1]      # NMAX: up to pi_NMAX(S^2) = pi_NMAX(S^3)

Mikhailov's E^1 (lecture of 2.9.2016, 0:51-0:55): words in lambda_i, mu_i (i >= 1) that start
with lambda_1 or mu_1, end with a lambda, and are admissible. In the language of lambda3.py
these are the words of Lambda(1) without mu_0 that end with a lambda. They span a subcomplex
of the quotient Lambda(1)/Lambda(1)mu_0 (words containing mu_0 are exactly those ending with
a run of mu_0, and they span the subcomplex Lambda(1)mu_0); this script checks that the
differential of every such word, with the mu_0-words dropped, again consists of such words.

Output, data/e2_metalib.csv (or data/e2_lambda1.csv with the second argument):
    n, s, colour, words, rank_out, homology
where n is the index of pi_n(S^2), s the length (Adams filtration), colour the number of mu's,
words = dim E^1, rank_out = rank of d on this block, homology = dim E^2.
Lambda(1) is cut at length LMAX = (n-3)//3 + 3 (mu_0-towers); its rows with s >= LMAX are
left out.
"""
import collections
import csv
import pathlib
import sys
import time

from lambda3 import P, add, colour, d, deg, idx, is_mu, lam, mu, rank_mod3

HERE = pathlib.Path(__file__).resolve().parent


def basis(nmax, kind):
    """Words over pi_n, n <= nmax + 1 (one more for the incoming differential), by (n, s, c)."""
    smax = nmax + 1 - 3
    lmax = smax // 3 + 3
    out = collections.defaultdict(list)

    def rec(w, st):
        if kind == "metalib" and not is_mu(w[-1]):
            out[(st + 3, len(w), colour(w))].append(w)
        if kind == "lambda1":
            out[(st + 3, len(w), colour(w))].append(w)
        if kind == "lambda1" and len(w) == lmax:
            return
        last = w[-1]
        top = P * idx(last) - (0 if is_mu(last) else 1)
        for j in range(0 if kind == "lambda1" else 1, top + 1):
            for x in ((lam(j),) if j else ()) + (mu(j),):
                if st + deg(x) <= smax:
                    rec(w + (x,), st + deg(x))

    firsts = (lam(1), mu(1)) if kind == "metalib" else (lam(1), mu(0), mu(1))
    for f in firsts:
        if deg(f) <= smax:
            rec((f,), deg(f))
    return out, lmax


def diff(w, kind):
    dw = dict(d.__wrapped__(w))  # no cache: millions of words
    if kind == "metalib":
        dw = {v: c for v, c in dw.items() if mu(0) not in v}
        for v in dw:
            assert not is_mu(v[-1]) and v[0] in (lam(1), mu(1)), ("not a subcomplex", w, v)
    return dw


def main():
    nmax = int(sys.argv[1])
    kind = "lambda1" if len(sys.argv) > 2 and sys.argv[2] == "lambda1" else "metalib"
    t0 = time.time()
    B, lmax = basis(nmax, kind)
    print(f"{kind}: {sum(len(v) for v in B.values())} words, {len(B)} blocks, {time.time() - t0:.1f}s",
          flush=True)
    rank = {}
    for key in sorted(B, key=lambda k: (k[0], k[1])):
        n, s, c = key
        rank[key] = rank_mod3([diff(w, kind) for w in B[key]])
        if s == 1 or n % 5 == 0 and s == 2:
            pass
    rows = []
    for (n, s, c), ws in sorted(B.items()):
        if n > nmax or (kind == "lambda1" and s >= lmax):
            continue
        h = len(ws) - rank[(n, s, c)] - rank.get((n + 1, s - 1, c), 0)
        rows.append({"n": n, "s": s, "colour": c, "words": len(ws), "rank_out": rank[(n, s, c)],
                     "homology": h})
    (HERE / "data").mkdir(exist_ok=True)
    fn = HERE / "data" / f"e2_{kind}.csv"
    with open(fn, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    tot = collections.Counter()
    for r in rows:
        tot[r["n"]] += r["homology"]
    print("E^2 per n:", " ".join(f"{n}:{tot[n]}" for n in range(4, nmax + 1)))
    print(f"wrote {fn}, {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
