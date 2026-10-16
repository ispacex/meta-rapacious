# -*- coding: utf-8 -*-
"""
Plan: which E^2 cells, and which differential blocks, a certificate of the
rapacious rule's survivors in the given columns needs.

    python3 cert/plan.py [N ...]      (default: 49 50 51 59 60)

Locality: the rule (rapacious.run) only ever draws an arrow (n,s,c) -> (n-1,s+r,c+1) between
cells that are nonzero on E^2, so it runs separately on every connected component of the graph
of such possible arrows. The survivors of column N are therefore fixed by
  * the exact dimension of every cell in the components meeting column N, and
  * dimension 0 for every other cell one possible arrow away from them.
dim E^2(n,s,c) = words(n,s,c) - rank d(n,s,c) - rank d(n+1,s-1,c); d goes (n,s,c) -> (n-1,s+1,c).
"""
import collections
import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import rapacious as R  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent.parent
rows = list(csv.DictReader(open(HERE / "data" / "e2_metalib.csv")))
W = {(int(r["n"]), int(r["s"]), int(r["colour"])): int(r["words"]) for r in rows}
H = {(int(r["n"]), int(r["s"]), int(r["colour"])): int(r["homology"]) for r in rows}
NMAX = max(n for n, _, _ in W)
SMAX = max(s for _, s, _ in W) + 1


def nbrs(v):
    n, s, c = v
    for r in range(2, SMAX + 1):
        yield (n - 1, s + r, c + 1)
        yield (n + 1, s - r, c - 1)


def target(b):
    return (b[0] - 1, b[1] + 1, b[2])


def main():
    cols = [int(a) for a in sys.argv[1:]] or [49, 50, 51, 59, 60]
    nz = {k for k, h in H.items() if h and k[0] > 3}
    comp, zeros = set(), set()
    stack = [k for k in nz if k[0] in cols]
    while stack:
        v = stack.pop()
        if v in comp:
            continue
        comp.add(v)
        for u in nbrs(v):
            if u in nz:
                stack.append(u)
            elif W.get(u):
                zeros.add(u)
    zeros |= {k for k in W if k[0] in cols and W[k] and k not in comp}  # the whole columns
    assert max(n for n, _, _ in comp | zeros) < NMAX, "component reaches the last computed column"
    blocks = set()
    for (n, s, c) in comp | zeros:
        blocks.add((n, s, c))
        blocks.add((n + 1, s - 1, c))
    blocks = {b for b in blocks if W.get(b) and W.get(target(b))}
    E2 = R.load_e2(str(HERE / "data" / "e2_metalib.csv"))
    sub = collections.Counter({k: E2[k] for k in comp})
    for fill in ("high", "low"):
        _, left, _ = R.run(sub, +1, fill, NMAX)
        _, full, _ = R.run(E2, +1, fill, NMAX)
        print(fill, "left (component only, full run):", {n: (left[n], full[n]) for n in cols})
    print(f"columns {cols}: {len(comp)} nonzero cells in n = {min(n for n, _, _ in comp)}..{max(n for n, _, _ in comp)}, "
          f"{len(zeros)} zero cells, {len(blocks)} blocks")
    sz = sorted(((W[b], W[target(b)], b) for b in blocks), reverse=True)
    print("largest blocks (words, targets, block):", sz[:8])
    print("sum words*targets = %.3g" % sum(a * b for a, b, _ in sz))
    for N in cols:
        print(N, sorted(k for k in comp if k[0] == N))
    tag = "_".join(map(str, cols))
    out = HERE / "cert" / f"blocks_{tag}.txt"
    out.write_text("# n s c   (block d: (n,s,c) -> (n-1,s+1,c)), columns %s\n" % cols
                   + "".join(f"{n} {s} {c}\n" for n, s, c in sorted(blocks)))
    out2 = HERE / "cert" / f"cells_{tag}.txt"
    out2.write_text("# n s c dim   (cells whose dimension the certificate fixes; dim 0 = a zero next to the component)\n"
                    + "".join(f"{n} {s} {c} {H[(n, s, c)]}\n" for n, s, c in sorted(comp | zeros)))
    print("wrote", out, out2)


if __name__ == "__main__":
    main()
