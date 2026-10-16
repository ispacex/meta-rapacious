# -*- coding: utf-8 -*-
"""
The mod-3 lambda algebra and its unstable piece Lambda(1) for S^3.

Conventions are those of Ivanov-Mikhailov-Wu, "On nontriviality of homotopy groups of
spheres", arXiv:1506.00952, section 2, with p = 3:

  letters  lambda_i (i >= 1), degree 2(p-1)i - 1 = 4i - 1   (odd)
           mu_j     (j >= 0), degree 2(p-1)j     = 4j       (even)
  a(k,j) = (-1)^(j+1) C((p-1)(k-j)-1, j),  b(k,j) = (-1)^j C((p-1)(k-j), j)
  N(k) = k - ceil((k+1)/p),  N'(k) = k - ceil(k/p)
  (the paper writes [.]; with the floor, the relation for k = 1 would contain its own
  left-hand side, and beyond k - ceil(..) every binomial vanishes anyway)

  admissible: after lambda_i the next index is <= p*i - 1, after mu_i it is <= p*i.
  Lambda(n): admissible words whose first index is <= n; Lambda(1) computes the unstable
  Adams E_2 of S^3 (Bousfield-Curtis-Kan-Quillen-Rector-Schlesinger).

A word is a tuple of letter codes: lambda_i -> 2i, mu_i -> 2i + 1. Elements are dicts
{word: coefficient in {1, 2}}. The differential is a derivation with the Koszul sign:
d(xy) = d(x) y + (-1)^|x| x d(y).

Gradings of a word: stem = sum of degrees (= t - s; the word lives over pi_{stem+3}(S^3)),
length = s (Adams filtration), colour = number of mu's (Mikhailov). The differential
lowers the stem by 1, raises the length by 1 and keeps the colour.
"""
import functools
import math
import sys

P = 3
sys.setrecursionlimit(100000)


def lam(i):
    return 2 * i


def mu(i):
    return 2 * i + 1


def is_mu(c):
    return c & 1


def idx(c):
    return c >> 1


def deg(c):
    return 4 * idx(c) - (0 if is_mu(c) else 1)


def name(w):
    sub = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
    return "".join(("μ" if is_mu(c) else "λ") + str(idx(c)).translate(sub) for c in w) or "1"


def stem(w):
    return sum(deg(c) for c in w)


def colour(w):
    return sum(is_mu(c) for c in w)


def admissible_pair(a, b):
    return idx(b) <= P * idx(a) - (0 if is_mu(a) else 1)


def admissible(w):
    return all(admissible_pair(w[i], w[i + 1]) for i in range(len(w) - 1))


def binom3(n, k):
    if k < 0 or n < 0 or k > n:
        return 0
    return math.comb(n, k) % P


def A(k, j):
    return ((-1) ** (j + 1) * binom3((P - 1) * (k - j) - 1, j)) % P


def B(k, j):
    return ((-1) ** j * binom3((P - 1) * (k - j), j)) % P


def N(k):
    return k - -(-(k + 1) // P)


def N1(k):
    return k - -(-k // P)


@functools.lru_cache(maxsize=None)
def rewrite(a, b):
    """A non-admissible pair (a, b) as a combination of pairs: [(coef, (y, z)), ...]."""
    i, m = idx(a), idx(b)
    out = []
    if not is_mu(a) and not is_mu(b):              # lambda_i lambda_{pi+k}
        k = m - P * i
        out = [(A(k, j), (lam(i + k - j), lam(P * i + j))) for j in range(N(k) + 1)]
    elif not is_mu(a) and is_mu(b):                # lambda_i mu_{pi+k}
        k = m - P * i
        out = [(A(k, j), (lam(i + k - j), mu(P * i + j))) for j in range(N(k) + 1)]
        out += [(B(k, j), (mu(i + k - j), lam(P * i + j))) for j in range(N1(k) + 1)]
    elif is_mu(a) and not is_mu(b):                # mu_i lambda_{pi+k+1}
        k = m - P * i - 1
        out = [(A(k, j), (mu(i + k - j), lam(P * i + j + 1))) for j in range(N(k) + 1)]
    else:                                          # mu_i mu_{pi+k+1}
        k = m - P * i - 1
        out = [(A(k, j), (mu(i + k - j), mu(P * i + j + 1))) for j in range(N(k) + 1)]
    assert k >= 0, (a, b)
    return tuple((c, pr) for c, pr in out if c)


@functools.lru_cache(maxsize=None)
def d_letter(c):
    """The differential of one letter: [(coef, (y, z)), ...]."""
    k = idx(c)
    if not is_mu(c):
        out = [(A(k, j), (lam(k - j), lam(j))) for j in range(1, N(k) + 1)]
    else:
        out = [(A(k, j), (lam(k - j), mu(j))) for j in range(0, N(k) + 1)]
        out += [(B(k, j), (mu(k - j), lam(j))) for j in range(1, N1(k) + 1)]
    return tuple((x, pr) for x, pr in out if x and idx(pr[0]) >= (0 if is_mu(pr[0]) else 1)
                 and idx(pr[1]) >= (0 if is_mu(pr[1]) else 1))


def add(acc, w, c):
    v = (acc.get(w, 0) + c) % P
    if v:
        acc[w] = v
    else:
        acc.pop(w, None)


@functools.lru_cache(maxsize=None)
def append(w, x):
    """Normal form of (admissible word w) * (letter x), as a tuple of (word, coef)."""
    if not w or admissible_pair(w[-1], x):
        return ((w + (x,), 1),)
    acc = {}
    for c, (y, z) in rewrite(w[-1], x):
        for w2, c2 in append(w[:-1], y):
            for w3, c3 in append(w2, z):
                add(acc, w3, c * c2 * c3)
    return tuple(acc.items())


def times(elem, letters):
    """Normal form of elem * letters (elem a dict of admissible words)."""
    cur = elem
    for x in letters:
        nxt = {}
        for w, c in cur.items():
            for w2, c2 in append(w, x):
                add(nxt, w2, c * c2)
        cur = nxt
    return cur


def nf(word):
    return times({(): 1}, word)


@functools.lru_cache(maxsize=None)
def d(w):
    """Differential of an admissible word, in normal form: tuple of (word, coef)."""
    acc = {}
    sign = 1
    for pos, x in enumerate(w):
        for c, (y, z) in d_letter(x):
            part = times({w[:pos]: 1}, (y, z) + w[pos + 1:])
            for w2, c2 in part.items():
                add(acc, w2, sign * c * c2)
        if not is_mu(x):
            sign = -sign
    return tuple(acc.items())


def basis_lambda1(max_stem, max_len):
    """Admissible words of Lambda(1) (first index <= 1) by (length, stem, colour)."""
    out = {}

    def rec(w, st):
        key = (len(w), st, colour(w))
        out.setdefault(key, []).append(w)
        if len(w) == max_len:
            return
        last = w[-1]
        top = P * idx(last) - (0 if is_mu(last) else 1)
        for j in range(0, top + 1):
            for x in ((lam(j),) if j else ()) + (mu(j),):
                s2 = st + deg(x)
                if s2 <= max_stem:
                    rec(w + (x,), s2)

    for first in (lam(1), mu(0), mu(1)):
        if deg(first) <= max_stem:
            rec((first,), deg(first))
    return out


def rank_mod3(rows):
    """Rank of a list of sparse vectors {word: coef} over F_3 (Gaussian elimination,
    pivot on the largest word -- Curtis' algorithm in effect)."""
    piv = {}
    for r in rows:
        r = dict(r)
        while r:
            lead = max(r)
            if lead in piv:
                c = r[lead]
                for w, v in piv[lead].items():
                    add(r, w, -c * v)
            else:
                inv = 1 if r[lead] == 1 else 2
                piv[lead] = {w: (v * inv) % P for w, v in r.items()}
                break
    return len(piv)
