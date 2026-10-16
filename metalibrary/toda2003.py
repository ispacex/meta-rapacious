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
