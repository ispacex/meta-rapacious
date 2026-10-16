# -*- coding: utf-8 -*-
"""
Independent checker of the certificates: the rapacious rule leaves classes in the given
columns pi_N. Written from scratch from Ivanov-Mikhailov-Wu, arXiv:1506.00952, section 2; it does
not import lambda3.py, metalib.py or the Rust code, and trusts nothing in the certificate files.

    python3 cert/check.py CELLS CERTDIR N [N ...]

CELLS: lines "n s c dim" -- the claim: dim E^2(n,s,c) for these cells. CERTDIR: the files written
by `cert` (block_n_s_c.txt, cell_n_s_c.txt). N: the columns pi_N whose survivors are computed.

The algebra (p = 3). Generators lambda_i (i >= 1, degree 4i-1) and mu_j (j >= 0, degree 4j);
a(k,j) = (-1)^{j+1} C(2(k-j)-1, j), b(k,j) = (-1)^j C(2(k-j), j); N(k) = k - ceil((k+1)/3),
N'(k) = k - ceil(k/3). The paper writes [ (k+1)/p ]; with the floor the relation for k = 1 would
contain its own left-hand side, and d^2 = 0 fails -- the checker tests d^2 = 0 on small blocks.
Relations (rewriting an inadmissible pair):
  lambda_i lambda_{pi+k} = sum_{j<=N(k)} a(k,j) lambda_{i+k-j} lambda_{pi+j}
  lambda_i mu_{pi+k}     = sum_{j<=N(k)} a(k,j) lambda_{i+k-j} mu_{pi+j} + sum_{j<=N'(k)} b(k,j) mu_{i+k-j} lambda_{pi+j}
  mu_i lambda_{pi+k+1}   = sum_{j<=N(k)} a(k,j) mu_{i+k-j} lambda_{pi+j+1}
  mu_i mu_{pi+k+1}       = sum_{j<=N(k)} a(k,j) mu_{i+k-j} mu_{pi+j+1}
Differential (a derivation, sign (-1)^{degree of what stands to the left}):
  d lambda_k = sum_{j=1}^{N(k)} a(k,j) lambda_{k-j} lambda_j
  d mu_k     = sum_{j=0}^{N(k)} a(k,j) lambda_{k-j} mu_j + sum_{j=1}^{N'(k)} b(k,j) mu_{k-j} lambda_j
Admissible: after lambda_i the next index is <= pi-1, after mu_i it is <= pi.
The complex: admissible words in Lambda(1) (first index <= 1) ending in a lambda = the basis of
Lambda-lambda(1), the E^1 of the paper's spectral sequence for S^3. A cell (n,s,c) = words of
degree n-3, length s, with c mu's (the colour); d: (n,s,c) -> (n-1,s+1,c).

What is checked:
 1. every block certificate: lines "y t w:k ...", y = sum k w over source words, t a target word;
    d(y_i) contains t_i and none of t_{i+1}, t_{i+2}, ...: the matrix (coefficient of t_j in
    d y_i) is triangular with a nonzero diagonal, so rank d >= the number of lines;
 2. every cell certificate: d z = 0, phi vanishes on d(cell above), det(phi_j(z_i)) != 0,
    so dim >= claimed;
 3. every claimed cell: words - rank_out - rank_in (lower bounds from 1) = claimed, so with 2 the
    dimension is exactly the claimed one;
 4. closure: every cell that a rule arrow (n,s,c) -> (n-1,s+r,c+1), r >= 2, joins to a claimed
    nonzero cell, and every cell of the columns N, is claimed (or has no words);
 5. the rule, run on the claimed nonzero cells (both fills): survivors per column N.
By 4, the claimed nonzero cells form a union of connected components of the graph of possible
arrows on E^2, and the rule never draws an arrow between components; so 5 is what the rule run on
the whole E^2 gives in the columns N.
"""
import collections
import functools
import pathlib
import sys
import time

P = 3


# ---------------------------------------------------------------- the algebra
# a letter is (kind, index), kind 0 = lambda, 1 = mu

def deg(x):
    return 4 * x[1] - (1 if x[0] == 0 else 0)


def binom_mod3(n, k):
    if k < 0 or n < 0 or k > n:
        return 0
    r = 1
    while n or k:
        a, b = n % 3, k % 3
        if b > a:
            return 0
        r = r * (1 if b == 0 or b == a else 2) % 3  # C(2,1) = 2
        n //= 3
        k //= 3
    return r


def a_(k, j):
    return (-1) ** (j + 1) * binom_mod3((P - 1) * (k - j) - 1, j) % 3


def b_(k, j):
    return (-1) ** j * binom_mod3((P - 1) * (k - j), j) % 3


def N(k):
    return k - -(-(k + 1) // P)


def N1(k):
    return k - -(-k // P)


def admissible_pair(x, y):
    return y[1] <= P * x[1] - (1 if x[0] == 0 else 0)


def relation(x, y):
    """x y for an inadmissible pair, as {(letter, letter): coefficient}."""
    out = collections.Counter()
    i, m = x[1], y[1]
    if x[0] == 0:
        k = m - P * i
        assert k >= 0
        if y[0] == 0:
            for j in range(N(k) + 1):
                out[((0, i + k - j), (0, P * i + j))] += a_(k, j)
        else:
            for j in range(N(k) + 1):
                out[((0, i + k - j), (1, P * i + j))] += a_(k, j)
            for j in range(N1(k) + 1):
                out[((1, i + k - j), (0, P * i + j))] += b_(k, j)
    else:
        k = m - P * i - 1
        assert k >= 0
        for j in range(N(k) + 1):
            out[((1, i + k - j), (y[0], P * i + j + 1))] += a_(k, j)
    return {t: c % 3 for t, c in out.items() if c % 3}


@functools.lru_cache(maxsize=1 << 21)
def normal(w):
    """Normal form of the monomial w (a tuple of letters): rewrite the leftmost inadmissible pair."""
    for p in range(len(w) - 1):
        if not admissible_pair(w[p], w[p + 1]):
            out = collections.Counter()
            for (y, z), c in relation(w[p], w[p + 1]).items():
                for u, cu in normal(w[:p] + (y, z) + w[p + 2:]).items():
                    out[u] += c * cu
            return {u: c % 3 for u, c in out.items() if c % 3}
    return {w: 1}


def d_letter(x):
    k = x[1]
    out = []
    if x[0] == 0:
        for j in range(1, N(k) + 1):
            out.append((a_(k, j), (0, k - j), (0, j)))
    else:
        for j in range(0, N(k) + 1):
            out.append((a_(k, j), (0, k - j), (1, j)))
        for j in range(1, N1(k) + 1):
            out.append((b_(k, j), (1, k - j), (0, j)))
    return [t for t in out if t[0] % 3]


@functools.lru_cache(maxsize=1 << 16)
def d(w):
    out = collections.Counter()
    sign = 1
    for p, x in enumerate(w):
        for c, y, z in d_letter(x):
            for u, cu in normal(w[:p] + (y, z) + w[p + 1:]).items():
                out[u] += sign * c * cu
        if deg(x) % 2:
            sign = -sign
    return {u: c % 3 for u, c in out.items() if c % 3}


@functools.lru_cache(maxsize=None)
def words(n, s, c):
    """Basis of the cell (n, s, c): admissible, first index <= 1, last letter a lambda,
    degree n-3, length s, c mu's; sorted."""
    out = []

    def rec(w, rem, mus):
        if len(w) == s:
            if rem == 0 and mus == c and w[-1][0] == 0:
                out.append(tuple(w))
            return
        left = s - len(w)
        if rem < 3 * left or mus > c:
            return
        # mu_0 can only be followed by mu_0, so it never occurs in a word ending in a lambda
        hi = 1 if not w else P * w[-1][1] - (1 if w[-1][0] == 0 else 0)
        for i in range(1, hi + 1):
            for kind in (0, 1):
                x = (kind, i)
                if deg(x) <= rem:
                    w.append(x)
                    rec(w, rem - deg(x), mus + kind)
                    w.pop()

    if s >= 1:
        rec([], n - 3, 0)
    return tuple(sorted(out))


def parse_word(t):
    return tuple((0 if x[0] == "l" else 1, int(x[1:])) for x in t.split("."))


# ---------------------------------------------------------------- linear algebra over F_3

def rank(rows):
    """rank of sparse rows {col: coef}."""
    piv = {}
    r_ = 0
    for row in rows:
        row = dict(row)
        while row:
            lead = max(row)
            if lead not in piv:
                inv = 1 if row[lead] == 1 else 2
                piv[lead] = {k: v * inv % 3 for k, v in row.items()}
                r_ += 1
                break
            f = (3 - row[lead]) % 3
            for k, v in piv[lead].items():
                nv = (row.get(k, 0) + f * v) % 3
                if nv:
                    row[k] = nv
                else:
                    row.pop(k, None)
    return r_


def det_nonzero(m):
    return rank([{j: v for j, v in enumerate(row) if v % 3} for row in m]) == len(m)


# ---------------------------------------------------------------- the checks

def d_into(w, tgt_index, where):
    """d(w) as {index in the target cell: coef}; fails if a term is not a basis word of the cell."""
    out = {}
    for u, c in d(w).items():
        if u not in tgt_index:
            raise AssertionError(f"{where}: d({w}) has the term {u} outside the target cell")
        out[tgt_index[u]] = c
    return out


def check_block(path):
    lines = path.read_text().split("\n")
    h = lines[0].split()
    n, s, c = int(h[1]), int(h[2]), int(h[3])
    src, tgt = words(n, s, c), words(n - 1, s + 1, c)
    assert int(h[5]) == len(src) and int(h[7]) == len(tgt), f"{path.name}: word counts {len(src)}, {len(tgt)}"
    ys = [l.split() for l in lines if l.startswith("y ")]
    assert len(ys) == int(h[9]) and lines[-2 if lines[-1] == "" else -1] == "end"
    srcset = set(src)
    tix = {u: i for i, u in enumerate(tgt)}
    T = [parse_word(y[1]) for y in ys]
    assert all(t in tix for t in T) and len(set(T)) == len(T), f"{path.name}: pivots not distinct target words"
    pos = {tix[t]: i for i, t in enumerate(T)}
    for i, y in enumerate(ys):
        acc = collections.Counter()
        for term in y[2:]:
            w, k = term.split(":")
            w = parse_word(w)
            assert w in srcset, f"{path.name}: {w} is not a source word"
            for j, v in d_into(w, tix, path.name).items():
                acc[j] += int(k) * v
        dy = {j for j, v in acc.items() if v % 3}
        # triangular: d(y_i) has its own pivot and none of the pivots after it
        assert tix[T[i]] in dy, f"{path.name}: d(y_{i}) misses its pivot"
        assert all(pos[j] <= i for j in dy if j in pos), f"{path.name}: d(y_{i}) has a later pivot"
    return (n, s, c), len(ys)


def check_cell(path):
    lines = [l for l in path.read_text().split("\n") if l]
    h = lines[0].split()
    n, s, c, dim = int(h[1]), int(h[2]), int(h[3]), int(h[7])
    x = words(n, s, c)
    xset = set(x)
    vec = lambda l: {parse_word(t.split(":")[0]): int(t.split(":")[1]) % 3 for t in l.split()[1:]}
    Z = [vec(l) for l in lines if l.startswith("z ")]
    F = [vec(l) for l in lines if l.startswith("phi ")]
    assert len(Z) == len(F) == dim and lines[-1] == "end"
    for v in Z + F:
        assert set(v) <= xset, f"{path.name}: a vector has a word outside the cell"
    below = {u: i for i, u in enumerate(words(n - 1, s + 1, c))}
    for z in Z:  # d z = 0
        acc = collections.Counter()
        for w, k in z.items():
            for j, v in d_into(w, below, path.name).items():
                acc[j] += k * v
        assert all(v % 3 == 0 for v in acc.values()), f"{path.name}: d z != 0"
    xi = {u: i for i, u in enumerate(x)}
    for u in words(n + 1, s - 1, c) if s >= 2 else ():  # phi(d u) = 0
        du = d_into(u, xi, path.name)
        for f in F:
            assert sum(f.get(x[j], 0) * v for j, v in du.items()) % 3 == 0, f"{path.name}: phi(d {u}) != 0"
    assert det_nonzero([[sum(f.get(w, 0) * k for w, k in z.items()) % 3 for f in F] for z in Z]), \
        f"{path.name}: the pairing is degenerate"
    return (n, s, c), dim


def check_d2(n, s, c):
    """d^2 = 0 on every word of the cell (a test of the conventions, N(k) above all)."""
    for w in words(n, s, c):
        acc = collections.Counter()
        for u, k in d(w).items():
            for v, kk in d(u).items():
                acc[v] += k * kk
        assert all(v % 3 == 0 for v in acc.values()), f"d^2 != 0 on {w}"


def rule(E, fill):
    """The rapacious rule: on pages r = 2, 3, ... arrows (n,s,c) -> (n-1,s+r,c+1) of maximal total
    rank; the arrows of a page form chains, filled from the high-n end ("high") or the low-n end."""
    E = dict(E)
    rmax = max(s for _, s, _ in E) + 1
    for r in range(2, rmax + 1):
        nxt = {v: (v[0] - 1, v[1] + r, v[2] + 1) for v in E if E[v] and E.get((v[0] - 1, v[1] + r, v[2] + 1))}
        hit = set(nxt.values())
        flows = []
        for v in nxt:
            if v in hit:
                continue
            chain = [v]
            while chain[-1] in nxt:
                chain.append(nxt[chain[-1]])
            used = collections.Counter()
            steps = range(len(chain) - 1) if fill == "high" else range(len(chain) - 2, -1, -1)
            for i in steps:
                a, b = chain[i], chain[i + 1]
                f = min(E[a] - used[a], E[b] - used[b])
                if f > 0:
                    used[a] += f
                    used[b] += f
                    flows.append((a, b, f))
        for a, b, f in flows:
            E[a] -= f
            E[b] -= f
    left = collections.Counter()
    for (n, s, c), v in E.items():
        left[n] += v
    return left


def main():
    cells_file, certdir, cols = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), [int(a) for a in sys.argv[3:]]
    t0 = time.time()
    claim = {}
    for l in cells_file.read_text().split("\n"):
        if l.strip() and not l.startswith("#"):
            n, s, c, dim = map(int, l.split())
            claim[(n, s, c)] = dim
    # sanity of the conventions: d^2 = 0 on all words of the small claimed cells
    small = [k for k in claim if len(words(*k)) <= 300]
    for k in small:
        check_d2(*k)
    print(f"d^2 = 0 on all words of {len(small)} claimed cells with <= 300 words")
    rk = {}
    for f in sorted(certdir.glob("block_*.txt")):
        k, r = check_block(f)
        rk[k] = r
        print(f"  block {k}: rank >= {r}  ({time.time() - t0:.0f}s)", flush=True)
    lower = {}
    for f in sorted(certdir.glob("cell_*.txt")):
        k, dim = check_cell(f)
        lower[k] = dim
        print(f"  cell {k}: dim >= {dim}  ({time.time() - t0:.0f}s)", flush=True)
    for (n, s, c), dim in claim.items():
        w = len(words(n, s, c))
        out_ = rk.get((n, s, c), 0) if words(n - 1, s + 1, c) else 0
        in_ = rk.get((n + 1, s - 1, c), 0) if s >= 2 else 0
        assert w - out_ - in_ == dim, f"cell {(n, s, c)}: words {w} - ranks {out_} - {in_} != {dim}"
        assert dim == 0 or lower.get((n, s, c)) == dim, f"cell {(n, s, c)}: no lower bound {dim}"
    print(f"3. all {len(claim)} claimed dimensions are exact ({sum(1 for v in claim.values() if v)} nonzero)")
    smax = max(s for _, s, _ in claim) + 30
    for (n, s, c), dim in claim.items():
        if not dim:
            continue
        for r in range(2, smax):
            for v in ((n - 1, s + r, c + 1), (n + 1, s - r, c - 1)):
                if v[1] >= 1 and v[2] >= 0 and words(*v):
                    assert v in claim, f"closure: {v} (next to {(n, s, c)}) has words and is not claimed"
    for N_ in cols:
        for s in range(1, N_):
            for c in range(s):
                if words(N_, s, c):
                    assert (N_, s, c) in claim, f"column {N_}: cell {(N_, s, c)} is not claimed"
    print("4. closure: every neighbour of a nonzero claimed cell and every cell of the columns is claimed")
    E = {k: v for k, v in claim.items() if v}
    for fill in ("high", "low"):
        left = rule(E, fill)
        print(f"5. rule, fill {fill}: survivors " + ", ".join(f"pi_{N_}: {left[N_]}" for N_ in cols))
    print(f"OK ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
