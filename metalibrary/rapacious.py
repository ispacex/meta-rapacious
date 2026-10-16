# -*- coding: utf-8 -*-
"""
The "rapacious" (хищная) spectral sequence of Mikhailov's 2016 lecture, run on the E^2 page
of the coloured metalibrary.

    python3 rapacious.py [data/e2_metalib.csv]

Rule, as stated in the lecture (0:59-1:06): from E^2 on, a differential d_r goes from
(n, s) to (n-1, s+r) and changes the colour by exactly one; the spectral sequence "eats
itself as fast as possible": on every page r = 2, 3, ... every differential the colours
allow is taken with maximal rank. What survives is compared with Toda.

Two things the lecture leaves open are made explicit and varied here:
  * the direction of the colour change: delta = +1 (colour grows along d_r) or -1;
  * where a page kills when a class could be both hit and a source: on page r the
    possible differentials form chains (n,s,c) -> (n-1,s+r,c+delta) -> ...; the maximal
    total rank on a chain is unique, its placement is not. "high" fills each chain from
    its high-n end, "low" from its low-n end.
Every variant reports the classes left over pi_n(S^2) and what it disagrees with:
Toda's 3-torsion (n <= 22), the Toda elements (n = 4k+2) and sandwiches (n = 4m+1) that are
proven to survive, and the lecture: no 3-torsion in pi_44, (Z/3)^2 in pi_71, 3-torsion for
every n >= 49. Results for n = NMAX are not final: d_r from pi_{NMAX+1} is not computed.
"""
import collections
import csv
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
TODA = None  # 3-torsion rank of pi_n(S^2) by Toda (1962), n <= 22: see toda1962()


def toda1962():
    """{n: rank of the 3-torsion of pi_n(S^2)} from Toda's 1962 table, n <= 22 (data/s2_3torsion.csv)."""
    with open(HERE / "data" / "s2_3torsion.csv") as f:
        return {int(r["n"]): int(r["toda_rank"]) for r in csv.DictReader(f) if r["toda_rank"] != ""}


def load_e2(fn):
    E = collections.Counter()
    for r in csv.DictReader(open(fn)):
        n, s, c, h = int(r["n"]), int(r["s"]), int(r["colour"]), int(r["homology"])
        if h and n > 3:
            E[(n, s, c)] += h
    return E


def run(E2, delta, fill, nmax, extra=()):
    """extra: additional (r, colour change) allowed besides delta on every page.
    Since colour = stem + s (mod 4), a differential d_r can change the colour only by
    dc = r - 1 (mod 4), so on one page at most one of the allowed shifts ever applies."""
    E = collections.Counter(E2)
    diffs = []
    rmax = max(s for _, s, _ in E) + 1
    for r in range(2, rmax + 1):
        succ = {}
        shifts = [delta] + [dc for rr, dc in extra if rr == r]
        for (n, s, c) in list(E):
            for dc in shifts:
                t = (n - 1, s + r, c + dc)
                if E[(n, s, c)] and E.get(t):
                    assert (n, s, c) not in succ, "two targets on one page"
                    succ[(n, s, c)] = t
        if not succ:
            continue
        targets = set(succ.values())
        starts = [v for v in succ if v not in targets]
        flows = []
        for v in starts:
            chain = [v]
            while chain[-1] in succ:
                chain.append(succ[chain[-1]])
            order = range(len(chain) - 1) if fill == "high" else range(len(chain) - 2, -1, -1)
            used = collections.Counter()
            for i in order:
                a, b = chain[i], chain[i + 1]
                f = min(E[a] - used[a], E[b] - used[b])
                if f > 0:
                    used[a] += f
                    used[b] += f
                    flows.append((r, a, b, f))
        for r_, a, b, f in flows:
            E[a] -= f
            E[b] -= f
            diffs.append({"r": r_, "from": a, "to": b, "rank": f})
    left = collections.Counter()
    for (n, s, c), v in E.items():
        if v:
            left[n] += v
    return E, left, diffs


def judge(E, left, nmax):
    bad = []
    for n in range(4, min(22, nmax) + 1):
        if left[n] != TODA.get(n, 0):
            bad.append(f"π{n}: {left[n]} ≠ Toda {TODA.get(n, 0)}")
    for n in range(6, nmax):
        if n % 4 in (1, 2) and n >= 6 and not (n % 4 == 1 and n < 9) and left[n] == 0:
            bad.append(f"π{n}: family element killed")
    if nmax > 44 and left[44]:
        bad.append(f"π44: {left[44]} ≠ 0 (lecture)")
    if nmax > 71 and left[71] != 2:
        bad.append(f"π71: {left[71]} ≠ 2 (lecture)")
    for n in range(49, nmax):
        if left[n] == 0:
            bad.append(f"π{n}: 0, lecture conjectures 3-torsion")
    return bad


def main():
    global TODA
    fn = next((a for a in sys.argv[1:] if a.endswith(".csv")), str(HERE / "data" / "e2_metalib.csv"))
    E2 = load_e2(fn)
    nmax = max(n for n, _, _ in E2)
    TODA = toda1962()
    out = {}
    for delta in (+1, -1):
        for fill in ("high", "low"):
            E, left, diffs = run(E2, delta, fill, nmax)
            bad = judge(E, left, nmax)
            key = f"delta={delta:+d} fill={fill}"
            out[key] = (left, bad, diffs)
            print(f"\n== {key}: {len(diffs)} differentials, {len(bad)} disagreements")
            print("   left over π_n:", " ".join(f"{n}:{left[n]}" for n in range(4, nmax + 1)))
            for b in bad[:12]:
                print("   ", b)
    # Toda 2003 (toda2003.py): the full table up to pi_82
    import toda2003
    t3 = toda2003.by_n()
    e2tot = collections.Counter()
    for (n, s, c), v in E2.items():
        e2tot[n] += v
    over = [n for n in t3 if n <= nmax and t3[n] > e2tot[n]]
    print(f"\nsanity: Toda 2003 <= E^2 for every n <= {nmax}:", "ok" if not over else f"FAILS at {over}")
    for key, (left, _, _) in out.items():
        dis = [(n, left[n], t3[n]) for n in range(4, nmax) if n in t3 and left[n] != t3[n]]
        print(f"vs Toda 2003, {key}: n <= {nmax - 1}, {len(dis)} disagreements (n, rapacious, Toda): {dis}")

    # not Mikhailov's rule: also the colour-preserving d_5 (= d_{2p-1}, the length of Toda's
    # differential), which Toda's 2003 table seems to need beyond pi_48
    for fill in ("high", "low"):
        E, left, diffs = run(E2, +1, fill, nmax, extra=((5, 0),))
        dis = [(n, left[n], t3[n]) for n in range(4, nmax) if n in t3 and left[n] != t3[n]]
        key = f"delta=+1 & d5 colour-preserving, fill={fill}"
        out[key] = (left, judge(E, left, nmax), diffs)
        print(f"vs Toda 2003, {key}: {len(dis)} disagreements: {dis}")

    a, b = out["delta=+1 fill=high"][0], out["delta=+1 fill=low"][0]
    print("\nfill high vs low (delta=+1) differ at:", [n for n in range(4, nmax + 1) if a[n] != b[n]])
    if "--save" in sys.argv:
        res = {"source": fn, "nmax": nmax, "note": "n = nmax is not final: d_r from pi_{nmax+1} not computed",
               "variants": {}}
        for key, (left, bad, diffs) in out.items():
            res["variants"][key] = {
                "left": {n: left[n] for n in range(4, nmax + 1)},
                "disagreements": bad,
                "differentials": [{"r": x["r"], "from": list(x["from"]), "to": list(x["to"]), "rank": x["rank"]}
                                  for x in diffs]}
        (HERE / "data" / "rapacious.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
        print("wrote data/rapacious.json")
    if "--survivors" in sys.argv:
        E, _, _ = run(E2, +1, "low", nmax)
        print("\nsurvivors (delta=+1, fill=low) as (s, colour), with Toda 2003's rank:")
        for n in range(23, nmax + 1):
            cl = sorted((s, c) for (m, s, c), v in E.items() if m == n for _ in range(v))
            mark = "" if t3.get(n) == len(cl) else f"   <-- Toda {t3.get(n)}"
            print(f"  π{n}: {cl}{mark}")
    if "--list" in sys.argv:
        for fill in ("high", "low"):
            print(f"\ndifferentials, delta=+1 fill={fill}:")
            for x in out[f"delta=+1 fill={fill}"][2]:
                (n, s, c), (m, t, e) = x["from"], x["to"]
                print(f"  d{x['r']}: π{n} (s{s},c{c}) -> π{m} (s{t},c{e})  rank {x['rank']}")
    return out


if __name__ == "__main__":
    main()
