# -*- coding: utf-8 -*-
"""
Checks of lambda3.py:

  1. every rewrite rule and every d(letter) is homogeneous (stem, length, colour);
  2. d(d(w)) = 0 for every admissible word of Lambda(1) up to the given stem;
  3. d maps Lambda(1) into Lambda(1);
  4. H(Lambda(1)) agrees with the unstable Ext of S^3 computed by an independent program
     (sseq/ext, resolve_unstable, file given as argument: lines n,s,dim with n = stem + 3).

    python3 check_lambda.py MAX_STEM [sseq.csv]
"""
import collections
import sys
import time

from lambda3 import (add, admissible, basis_lambda1, colour, d, d_letter, deg, idx, is_mu, lam, mu,
                     name, rank_mod3, rewrite, stem, P)


def homogeneity(maxidx=40):
    for i in range(0, maxidx):
        for a in ([lam(i)] if i else []) + [mu(i)]:
            for j in range(0, P * maxidx):
                for b in ([lam(j)] if j else []) + [mu(j)]:
                    if admissible((a, b)):
                        continue
                    for c, (y, z) in rewrite(a, b):
                        assert deg(y) + deg(z) == deg(a) + deg(b), (name((a, b)), name((y, z)))
                        assert is_mu(y) + is_mu(z) == is_mu(a) + is_mu(b)
                        assert admissible((y, z)) or (y, z) != (a, b)
            for c, (y, z) in d_letter(a):
                assert deg(y) + deg(z) == deg(a) - 1 and is_mu(y) + is_mu(z) == is_mu(a)
    print("1. relations and d(letter) homogeneous: ok")


def main():
    max_stem = int(sys.argv[1])
    max_len = max_stem // 3 + 3
    t = time.time()
    B = basis_lambda1(max_stem + 1, max_len + 1)
    print(f"basis: {sum(len(v) for v in B.values())} words in {len(B)} blocks, {time.time() - t:.1f}s")
    homogeneity()

    t = time.time()
    bad = 0
    for (s, st, c), ws in B.items():
        if st > max_stem or s > max_len:
            continue
        for w in ws:
            dw = dict(d(w))
            for v in dw:
                assert v[0] in (lam(1), mu(0), mu(1)), ("leaves Lambda(1)", name(w), name(v))
                assert stem(v) == st - 1 and len(v) == s + 1 and colour(v) == c and admissible(v)
            acc = {}
            for v, cv in dw.items():
                for u, cu in d(v):
                    add(acc, u, cv * cu)
            if acc:
                bad += 1
                if bad < 5:
                    print("  d^2 != 0 on", name(w), {name(u): x for u, x in acc.items()})
    assert bad == 0, f"d^2 != 0 on {bad} words"
    print(f"2-3. d^2 = 0 and d(Lambda(1)) in Lambda(1) on all words of stem <= {max_stem}: ok, "
          f"{time.time() - t:.1f}s")

    # homology by (stem, length): dim C - rank(out) - rank(in)
    t = time.time()
    rk = {}
    for (s, st, c), ws in B.items():
        if st <= max_stem + 1 and s <= max_len:
            rk[(s, st, c)] = rank_mod3([dict(d(w)) for w in ws])
    H = collections.Counter()
    for (s, st, c), ws in B.items():
        if st > max_stem or s >= max_len:
            continue
        h = len(ws) - rk[(s, st, c)] - rk.get((s - 1, st + 1, c), 0)
        if h:
            H[(st, s)] += h
    print(f"homology: {time.time() - t:.1f}s")
    if len(sys.argv) > 2:
        ref = collections.Counter()
        for line in open(sys.argv[2]):
            n, s, k = map(int, line.split(","))
            if 0 < n - 3 <= max_stem and s < max_len and k:
                ref[(n - 3, s)] += k
        mine = {key: v for key, v in H.items() if key[0] > 0}
        diff = {k: (mine.get(k, 0), ref.get(k, 0)) for k in set(mine) | set(ref) if mine.get(k, 0) != ref.get(k, 0)}
        print(f"4. H(Lambda(1)) vs sseq, stems 1..{max_stem}, s < {max_len}:",
              "ok" if not diff else f"DIFFER at {sorted(diff.items())[:20]}")
        assert not diff
    return H


if __name__ == "__main__":
    main()
