# -*- coding: utf-8 -*-
"""
Checks of our reading of Toda's 2003 tables (toda2003.py, transcriptions in this directory),
MATH-442. Every check is run on every cell it applies to; the result is a list of lines
"check: cell: what", printed and written as JSON for the site.

    python3 -I toda03/check.py [E2_DIR] [--json OUT]       # from metalibrary/

  A. our S^3 column (toda2003.OLD / NEW_MOD_A, read 2026-10-15 and checked then) = the S^3
     column of the new transcription;
  B. the stable range: in the 3-local double-suspension range k <= 2n-1 (the fibre of
     E^2: S^{2m-1} -> Omega^2 S^{2m+1} has its bottom cell in dimension 2pm-3, so with n = 2m-1
     E^2 is an isomorphism for k <= 2n-1 and onto at k = 2n), and
     in the column "stable", the group is the stable stem: im J (Z/3^{v_3(r)+1} in k = 4r-1)
     plus Ravenel's Table A3.2 (green book, 3rd digital ed., "3-Primary Stable Homotopy Excluding
     im J"); section 6.5 is mod A, so there only A3.2;
  C. Toda 1962 (Ravenel's Table A3.4, n <= 21, k <= 19, as read for ggs_map.json of
     ispacex/visual, checked there against the PKU copy): the 3-part, summand by summand;
  D. the unstable Adams E_2 (sseq/ext and H(Lambda(m)), e2_job.sh): log_3 |pi| <= dim E_2 in
     every cell; for section 5.6 (whole groups) moreover the differentials must balance: with
     D_k = dim E_2 - log_3 |pi| in stem k, the ranks r_k of the differentials from stem k+1 to
     stem k are r_k = D_k - r_{k-1} (r_0 = 0) and must all be >= 0; and the two E_2 programs
     must agree where both ran;
  E. Toda against Toda: the groups mod A of the computing diagrams of sections 5.2-5.5
     (Theorems 5.1-5.4) against the table of section 5.6 (whole groups): the difference must be
     the alpha families, i.e. zero in the stems k = 0, 1 mod 4 (an assumption on what A holds:
     alpha_t, alpha'_3s, alpha''_9t lie in the stems 4t-1, their unstable companions and the
     products of alpha elements in stems = 2 mod 4; section 5 does not define A explicitly); and the spheres of origin
     u(.) of (5.4.2)-(5.4.3) against the chains of the table.
"""
import collections
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import toda2003 as T  # noqa: E402

# Ravenel, Table A3.2 (stems <= 79): element, order. "All elements have order 3 unless
# otherwise indicated"; 3 x45 = alpha_1 beta_3 and 3 x75 = alpha_1 beta_1^2 beta_2^2.
RAVENEL_A32 = {
    10: [("β1", 3)], 13: [("α1β1", 3)], 20: [("β1²", 3)], 23: [("α1β1²", 3)], 26: [("β2", 3)],
    29: [("α1β2", 3)], 30: [("β1³", 3)], 36: [("β1β2", 3)], 37: [("⟨α1,α1,β1³⟩", 3)],
    38: [("β3/2", 3)], 39: [("α1β1β2", 3)], 40: [("β1⁴", 3)], 42: [("β3", 3)],
    45: [("x45", 9)], 46: [("β1²β2", 3)], 47: [("⟨α1,α1,β1⁴⟩", 3)], 49: [("α1β1²β2", 3)],
    50: [("β1⁵", 3)], 52: [("β2²", 3)], 55: [("α1β2²", 3)], 62: [("β1β2²", 3)],
    65: [("α1β1β2²", 3)], 68: [("x68", 3)], 72: [("β1²β2²", 3)], 74: [("β5", 3)],
    75: [("x75", 9)], 78: [("β2³", 3)],
}


def im_j(k):
    """3-primary im J in the stem k: Z/3^{v_3(r)+1} for k = 4r - 1, r >= 1."""
    if k % 4 != 3:
        return []
    r, v = (k + 1) // 4, 0
    while r % 3 == 0:
        r, v = r // 3, v + 1
    return [3 ** (v + 1)]


def stable(k, mod_a):
    return sorted([o for _, o in RAVENEL_A32.get(k, [])] + ([] if mod_a else im_j(k)))


def toda1962():
    """{(k, n): orders of the 3-part} from ggs_map.json (Toda 1962 via Ravenel A3.4), n <= 21."""
    p = HERE / "toda1962_p3.csv"
    out = {}
    for line in p.read_text().splitlines()[1:]:
        n, k, p3 = line.split(",")
        orders = []
        for part in p3.split("."):
            if part in ("0", "1", ""):
                continue
            base, _, e = part.partition("^")
            orders += [int(base)] * (int(e) if e else 1)
        out[(int(k), int(n))] = sorted(orders)
    return out


def e2_dims(e2_dir):
    """{(n, k): total dim} of sseq and of H(Lambda(m)), with the stems each went up to, from
    E2_DIR/e2_packed.txt (e2_pack.py of the output of e2_job.sh)."""
    sseq, lam = collections.Counter(), collections.Counter()
    sseq_kmax, lam_kmax = {}, {}
    for line in (pathlib.Path(e2_dir) / "e2_packed.txt").read_text().splitlines():
        f = line.split()
        if f[0] == "#S":
            sseq_kmax[int(f[1])] = int(f[3])
        elif f[0] == "#L":
            lam_kmax[int(f[1])] = int(f[3])
        elif f[0] in ("L", "S"):
            n, k = int(f[1]), int(f[2])
            tot = sum(int(x.split(":")[1]) for x in f[3].split(","))
            (lam if f[0] == "L" else sseq)[(n, k)] += tot
    return sseq, sseq_kmax, lam, lam_kmax


def diagram_mod_a():
    """{(k, n): orders} mod A from the computing diagrams of sections 5.2-5.5: Theorem 5.1
    (k <= 27, complete) and the three parts of Theorems 5.2-5.4; plus the simple elements."""
    g = collections.defaultdict(list)
    files = ["d_thm51.txt", "d_thm52b.txt", "d_thm52c.txt", "d_thm53b.txt", "d_thm53c.txt",
             "d_thm54b.txt", "d_thm54c.txt"]
    # (d_p58, the case k = 49 once more, repeats rows of d_thm54b/c and the simple (3,49))
    rows = []
    for f in files:
        rows += T.load("s5/" + f)
    gg, _ = T.groups(rows, T.T56_NMAX)
    for key, v in gg.items():
        g[key] += v
    simple = {  # (1) Removable simple unstable elements, Theorems 5.2-5.4 (one Z/3 each)
        (28, 9), (29, 9), (32, 3), (33, 3),
        (36, 3), (37, 3), (38, 9), (39, 9), (40, 15), (41, 15), (42, 3), (43, 3),
        (43, 3, "b"), (44, 3), (44, 9), (45, 9),
        (49, 3), (50, 15), (51, 15), (52, 3), (53, 3), (52, 21), (53, 21),
        (53, 3, "b"), (54, 3), (54, 9), (55, 9), (55, 9, "b"),
    }
    for s in simple:
        g[(s[0], s[1])].append(3)
    # (3,16), (3,17), (3,26), (3,27) of section 5.2 (1) are in the diagram of Theorem 5.1
    return {k: sorted(v) for k, v in g.items()}


def run(e2_dir=None):
    """{check: {"checked": n, "problems": [...]}}, and the ranks r_k of check D by sphere."""
    g56, st56 = T.table56()
    g65, st65 = T.table65()
    res = collections.OrderedDict((c, {"checked": 0, "problems": []}) for c in "ABCDE")

    def note(c, ok, msg):
        res[c]["checked"] += 1
        if not ok:
            res[c]["problems"].append(msg)

    # A
    for k in range(1, 56):
        note("A", T.log3(g56.get((k, 3), [])) == T.OLD.get(k, 0), f"5.6 k={k} n=3")
    for k in range(56, 80):
        note("A", T.log3(g65.get((k, 3), [])) == T.NEW_MOD_A.get(k, 0), f"6.5 k={k} n=3")

    # B
    for k in range(1, 56):
        want = stable(k, mod_a=False)
        got = sorted(o for o, _ in st56.get(k, []))
        note("B", got == want, f"5.6 k={k} stable: table {got}, stable stem {want}")
        for n in range(3, T.T56_NMAX + 1, 2):
            if k <= 2 * n - 1:
                note("B", g56.get((k, n), []) == want, f"5.6 k={k} n={n}: {g56.get((k, n), [])} vs {want}")
    for k in range(56, 80):
        want = stable(k, mod_a=True)
        got = sorted(o for o, _ in st65.get(k, []))
        note("B", got == want, f"6.5 k={k} stable: table {got}, A3.2 {want}")
        for n in range(3, T.T65_NMAX + 1, 2):
            if k <= 2 * n - 1:
                note("B", g65.get((k, n), []) == want, f"6.5 k={k} n={n}: {g65.get((k, n), [])} vs {want}")

    # C
    t62 = toda1962()
    for (k, n), want in sorted(t62.items()):
        if n % 2 == 1 and n >= 3 and k >= 1:
            note("C", g56.get((k, n), []) == want, f"k={k} n={n}: 2003 {g56.get((k, n), [])}, 1962 {want}")

    # D
    balance = {}
    if e2_dir:
        sseq, skmax, lam, lkmax = e2_dims(e2_dir)
        for n in sorted(set(skmax) & set(lkmax)):
            for k in range(1, min(skmax[n], lkmax[n]) + 1):
                note("D", sseq[(n, k)] == lam[(n, k)],
                     f"E2 programs disagree at S^{n} k={k}: sseq {sseq[(n, k)]}, lambda {lam[(n, k)]}")
        for (tab, ks, nmax) in ((g56, range(1, 56), T.T56_NMAX), (g65, range(56, 80), T.T65_NMAX)):
            for n in range(3, nmax + 1, 2):
                for k in ks:
                    if k > skmax.get(n, -1):
                        continue
                    e2 = sseq[(n, k)]
                    note("D", T.log3(tab.get((k, n), [])) <= e2,
                         f"k={k} n={n}: log3|pi| = {T.log3(tab.get((k, n), []))} > dim E2 = {e2}")
        for n in range(3, T.T56_NMAX + 1, 2):
            if skmax.get(n, 0) < 56:
                continue
            r, rs = 0, []
            for k in range(1, 56):
                dk = sseq[(n, k)] - T.log3(g56.get((k, n), []))
                r = dk - r
                rs.append(r)
                note("D", r >= 0, f"S^{n}: the differentials into stem {k} would have rank {r} < 0")
            balance[n] = rs

    # E
    dm = diagram_mod_a()
    for k in range(1, 56):
        for n in range(3, T.T56_NMAX + 1, 2):
            full, moda = T.log3(g56.get((k, n), [])), T.log3(dm.get((k, n), []))
            if k % 4 in (0, 1):
                note("E", full == moda, f"k={k} n={n}: 5.6 has log3 {full}, the diagrams mod A {moda}")
            else:
                note("E", full >= moda, f"k={k} n={n}: 5.6 has log3 {full} < diagrams mod A {moda}")
    born = {r"\epsilon'": 7, r"\epsilon_1": 15, r"\epsilon_2": 11, r"\varphi": 9,
            r"\beta_1\beta_2": 5, r"\alpha_1\beta_1\beta_2": 3, r"\beta_1^4": 3}
    for r in T.load("t56.txt"):
        for ch in r.get("chains", []):
            if ch["tail"] in born:
                # the sphere where the generator itself is born: the start of the last run of
                # summands joined by '=' (phi: 3 phi is born on S^7, phi on S^9)
                it = ch["items"]
                j = len(it) - 1
                while j >= 2 and it[j - 1][2] == "=":
                    j -= 2
                note("E", it[j][0] == born[ch["tail"]],
                     f"u({ch['tail']}) = {born[ch['tail']]} (5.4.2-3), the generator of k={r['k']} is born on S^{it[j][0]}")
                if ch["tail"] == r"\varphi":
                    note("E", ch["start"] == 7, f"u(3 phi) = 7 (5.4.3), the chain of phi starts on S^{ch['start']}")
    return res, balance


def main():
    args = sys.argv[1:]
    out_json = None
    if "--json" in args:
        i = args.index("--json")
        out_json = args[i + 1]
        del args[i:i + 2]
    res, balance = run(args[0] if args else None)
    for c, v in res.items():
        print(f"{c}: {v['checked']} checks, {len(v['problems'])} problems")
        for p in v["problems"]:
            print("   ", p)
    if out_json:
        json.dump({"checks": res, "balance": balance}, open(out_json, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
