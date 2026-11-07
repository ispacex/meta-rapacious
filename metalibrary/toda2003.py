# -*- coding: utf-8 -*-
"""
3-primary pi_{3+k}(S^3) = pi_{3+k}(S^2) from H. Toda, "Unstable 3-primary homotopy groups of
spheres", Econoinformatics (Himeji Dokkyo University) 29 (2003), 1-77; NDL BibID 6899969,
CiNii crid 1523669554954337536. Scan with OCR on D. Ravenel's site:
https://www.sas.rochester.edu/mth/sites/doug-ravenel/otherpapers/Toda03-ocr.pdf
(PDF pages 67-68: section 5.6, k <= 55; pages 80-81: section 6.5, 56 <= k <= 79).

Read by eye from the n = 3 column (2026-10-15). Every summand is Z/3 on S^3
(a filled dot; Cohen-Moore-Neisendorfer). A row of the table that starts to the right of
n = 3 does not count.

  OLD[k]  section 5.6, k <= 55: the whole group, alpha families included
          (they are printed, e.g. <alpha_2>, <alpha'_12>). Toda: k < 46 is from his 1967 work,
          46 <= k <= 55 from an announcement of K. Maruyama and M. Mimura (1998).
  NEW[k]  section 6.5, 56 <= k <= 79: the group mod A, i.e. without the unstable alpha
          families. On S^3 the family A contributes one Z/3 in the stems rq-2 and rq-1
          (q = 4), i.e. k = 2, 3 mod 4 (section 4.3, diagram for the case v(r) = 1): the
          sandwiches and the Toda elements alpha_r(3). TOTAL adds them back.
          Toda: "the results for k = 76 and k = 77 are not yet fixed".
"""

OLD = {
    3: 1, 4: 0, 5: 0, 6: 1, 7: 1, 8: 0, 9: 0, 10: 1, 11: 1, 12: 0, 13: 1, 14: 1, 15: 1, 16: 1,
    17: 1, 18: 1, 19: 1, 20: 0, 21: 0, 22: 1, 23: 2, 24: 1, 25: 0, 26: 2, 27: 2, 28: 0, 29: 0,
    30: 1, 31: 1, 32: 1, 33: 2, 34: 2, 35: 1, 36: 1, 37: 1, 38: 1, 39: 2, 40: 1, 41: 0, 42: 2,
    43: 3, 44: 1, 45: 0, 46: 1, 47: 1, 48: 0, 49: 2, 50: 3, 51: 2, 52: 1, 53: 2, 54: 2, 55: 2,
}

NEW_MOD_A = {
    56: 1, 57: 0, 58: 1, 59: 2, 60: 2, 61: 1, 62: 1, 63: 1, 64: 0, 65: 1, 66: 1, 67: 0,
    68: 1, 69: 1, 70: 0, 71: 0, 72: 0, 73: 0, 74: 0, 75: 1, 76: 1, 77: 0, 78: 1, 79: 2,
}
NOT_FIXED = {76, 77}


def alpha_on_s3(k):
    """Number of Z/3 the unstable alpha families give in pi_{3+k}(S^3)."""
    return 1 if k % 4 in (2, 3) and k >= 3 else 0


TOTAL = dict(OLD)
TOTAL.update({k: v + alpha_on_s3(k) for k, v in NEW_MOD_A.items()})


def by_n():
    """{n: rank of 3-torsion of pi_n(S^2)}, n = k + 3, 6 <= n <= 82."""
    return {k + 3: v for k, v in TOTAL.items()}


if __name__ == "__main__":
    print(" ".join(f"π{n}:{v}" for n, v in sorted(by_n().items())))


# ---------------------------------------------------------------------------------------------
# All columns (MATH-442). The tables of sections 5.6 and 6.5 and the computing diagrams of
# section 5 are transcribed in toda03/ in a small line format, read from the page images:
#
#     k | m | 3:*=*->o=<\alpha_1>  | 9:*      one printed row; chains at their first column
#     k | u | 4:a | 6!:b                      labels written above the row (H-images)
#     k | l | 6:B                             labels written below the row (P-preimages)
#     k | r | text                            a note at the right margin
#
# Columns: an odd number n is the sphere S^n; an even number is the place between n-1 and n+1
# (where the source writes E^2, and where a label of Q^{n-1} stands). In a chain, '*' 'o' '>'
# '(*)' are the summands Z/3, Z/9, Z/27 and Toda's parenthesised dot; '=' '->' '<~' are the
# connecting E^2 (bijective, non-trivial not bijective, and the hook of section 5.2); a final
# '=<...>' is the stable name, the chain then goes on unchanged to every larger n. A label
# 'c:x' has the arrow of the source (to/from the dot), 'c!:x' is printed without it.

import pathlib as _pl

DIR = _pl.Path(__file__).resolve().parent / "toda03"
ORDER = {"*": 3, "o": 9, ">": 27, "(*)": 3}


def parse_chain(col, s):
    """'3:*=*->o=<x>' -> (items, tail): items [(col, kind, token)] with kind 'sym' or 'con'."""
    items, i, c, tail, want_sym = [], 0, col, None, True
    while i < len(s):
        if want_sym:
            tok = "(*)" if s.startswith("(*)", i) else s[i]
            if tok not in ORDER:
                raise ValueError(f"bad symbol at {s[i:]!r} in {s!r}")
            items.append((c, "sym", tok))
            i += len(tok)
            c += 1
        else:
            if s.startswith("=<", i):
                tail = s[i + 2:].rstrip()
                if not tail.endswith(">"):
                    raise ValueError(f"bad tail in {s!r}")
                tail = tail[:-1]
                break
            tok = next((t for t in ("->", "<~", "=") if s.startswith(t, i)), None)
            if tok is None:
                raise ValueError(f"bad connector at {s[i:]!r} in {s!r}")
            items.append((c, "con", tok))
            i += len(tok)
            c += 1
        want_sym = not want_sym
    if want_sym:
        raise ValueError(f"chain ends with a connector: {s!r}")
    return items, tail


def load(name):
    """Rows of a transcription file: dicts k, kind, and chains / labels / note."""
    rows = []
    for line in (DIR / name).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        f = [x.strip() for x in line.split("|")]
        k, kind, rest = int(f[0]), f[1], [x for x in f[2:] if x]
        row = {"k": k, "kind": kind}
        if kind == "m":
            row["chains"] = []
            for x in rest:
                c, s = x.split(":", 1)
                items, tail = parse_chain(int(c), s)
                row["chains"].append({"start": int(c), "items": items, "tail": tail})
        elif kind in ("u", "l"):
            row["labels"] = []
            for x in rest:
                c, t = x.split(":", 1)
                row["labels"].append((int(c.rstrip("!")), t, not c.endswith("!")))
        elif kind == "r":
            row["note"] = " | ".join(rest)
        else:
            raise ValueError(line)
        rows.append(row)
    return rows


def groups(rows, nmax):
    """{(k, n): sorted orders of the cyclic summands} for odd n <= nmax, read off the chains; a
    chain with a stable name goes on with its last summand. Also {k: stable orders}."""
    g, stable = {}, {}
    for r in rows:
        if r["kind"] != "m":
            continue
        for ch in r["chains"]:
            syms = [(c, t) for c, kind, t in ch["items"] if kind == "sym"]
            for c, t in syms:
                if c % 2 == 0:
                    raise ValueError(f"symbol on an even column, k={r['k']}")
                g.setdefault((r["k"], c), []).append(ORDER[t])
            if ch["tail"] is not None:
                last_c, last_t = syms[-1]
                for n in range(last_c + 2, nmax + 1, 2):
                    g.setdefault((r["k"], n), []).append(ORDER[last_t])
                stable.setdefault(r["k"], []).append((ORDER[last_t], ch["tail"]))
    return {key: sorted(v) for key, v in g.items()}, stable


def log3(orders):
    return sum({3: 1, 9: 2, 27: 3}[o] for o in orders)


T56_NMAX, T65_NMAX = 29, 37


# Cells where the printed table of section 5.6 omits a summand that Toda's own text gives,
# {(k, n): orders of the omitted cyclic summands}; t56.txt stays as printed.
#   (45, 9): Theorem 5.3 (1) (p. 53, PDF 60) has the removable simple element P(B_2) at
#   (n, k) = (9, 45), H P(B_2) = AB_2; the table shows only the Z/9 of phi. The EHP sequence
#   (2.1.3) decides it: pi_51(S^7) = 0, so H maps pi_54(S^9) onto pi_51(Q_2^7) = (Z/3)^2
#   (Lemma 2.2, Proposition 2.1: pi^S_30 = <beta_1^3>, pi^S_29 = <alpha_1 beta_2>), and the
#   kernel E^2 pi_52(S^7) is Z/3, so the group is Z/9 + Z/3 (tracker D5-48).
CORRECTIONS_56 = {(45, 9): [3]}


def table56(printed=False):
    """Section 5.6: whole 3-primary groups (alpha families included), k <= 55, n = 3..29;
    with CORRECTIONS_56 applied unless printed=True."""
    g, st = groups(load("t56.txt"), T56_NMAX)
    if not printed:
        for key, extra in CORRECTIONS_56.items():
            g[key] = sorted(g.get(key, []) + extra)
    return g, st


def table65():
    """Section 6.5: groups mod A, 56 <= k <= 79, n = 3..37 (k = 76, 77 'not yet fixed')."""
    return groups(load("t65.txt"), T65_NMAX)
