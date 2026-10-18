Русская версия: [README.ru.md](README.ru.md).

# cert/ — a verifiable proof of the rapacious rule's disagreement with Toda

**Claim.** If the rapacious rule (arrows $d_r\colon(n,s,c)\to(n-1,s+r,c+1)$, $r\ge2$, maximal rank
on every page) is applied to the actual $E^2$ page of the metalibrary, then over $\pi_n(S^2)$ there
remain

| $n$ | the rule (both filling orders) | Toda 2003 |
|---|---|---|
| 49 | 2 | 1 |
| 50 | 3 | 1 |
| 51 | 1 | 0 |
| 59 | 2 | 1 |
| 60 | 1 | 0 |

Toda's values are quoted, not proved (`../toda2003.py`). Only the left column is proved, and in
such a way that the check does not depend on our code that computed $E^2$ (`lambda3.py`, `rust/`).

## How it works

1. **Locality** (`plan.py`). The rule draws arrows only between nonzero cells of $E^2$, so it runs
   separately on each connected component of the graph of possible arrows. For the columns $N$ it
   suffices to know the exact dimensions of the cells of the components that meet these columns,
   and that all neighbouring cells (one possible arrow away) and all other cells of the columns are
   zero.
   π₄₉–π₅₁: 89 cells (20 nonzero), 100 blocks of the differential, n = 48…54.
   π₅₉–π₆₀: 86 cells (17 nonzero), 111 blocks, n = 58…62; the largest block is 308,910 × 269,346.
2. **Certificates** (`../rust/src/bin/cert.rs`; the program is not trusted, it only writes files).
   - *The rank of a block* $d\colon(n,s,c)\to(n-1,s+1,c)$ is at least $r$: $r$ lines `y t w:k …`,
     a vector $y=\sum k\,w$ of source words and a target word $t$. Each $d(y_i)$ contains its own
     $t_i$ and none of the $t_j$ with $j>i$; the matrix of coefficients is triangular with a nonzero
     diagonal, so the $d(y_i)$ are independent. Checking needs no Gaussian elimination, only
     computing $d$. On average $y$ has one and a half words.
   - *A nonzero cell* of dimension $h$: $h$ cycles $z$ ($dz=0$) and $h$ cocycles $\varphi$
     ($\varphi\circ d=0$ on the cell above) with an invertible matrix $\varphi_j(z_i)$; hence $\dim\ge h$.
   - From the lower bounds on the ranks: $`\dim\le\#\text{words}-\mathrm{rk}_\text{out}-\mathrm{rk}_\text{in}`$.
     Together this is the exact dimension.
3. **The checker** `check.py` is written from scratch following [arXiv:1506.00952](https://arxiv.org/abs/1506.00952), §2 (relations,
   $\partial$, admissibility, enumeration of words) and imports nothing from `metalibrary/`. Its
   normal form rewrites the leftmost inadmissible pair (the Rust code recurses on the last letter).
   It checks the certificates, the exactness of all claimed dimensions, that the set of cells is
   closed under the arrows of the rule, that the columns are complete, and runs the rule itself.
   `selftest.py` corrupts a certificate in four ways, and each corruption is rejected.
4. **Lean 4** (`lean/`): a third implementation of the algebra and of the same checks; the theorem
   `rule_survivors : checkAll … = some […]` is proved by `native_decide`
   (this trusts the Lean compiler, as noted).

## Results

| | generator | checker (Python) | Lean |
|---|---|---|---|
| π₄₉–π₅₁ | 3 s, 0.1 GB | 34 s, 1.1 GB | 4.6 min, 1.6 GB |
| π₅₉–π₆₀ | 72 s, 0.85 GB | 8 min, 4.3 GB | 3 h 28 min, 7.7 GB |

A remote machine, 3 cores (`../../remote/`). Lean rejects a wrong expected value (a run with
π₂₂ = 2 fails), so `native_decide` really computes.

The certificates are not in git (they would travel to the remote machine with every job). They are
published as the release https://github.com/ispacex/metalibrary/releases/tag/certificates-2026-10-15
(with a `SHA256SUMS` file); the generator is deterministic and recreates them in a minute.

| archive | size | sha256 |
|---|---|---|
| `cert_49_50_51.tar.gz` | 1.5 MB | `9a9820c8e7bca9de4e145b77eb1fe509f31ef3b2018accf357791a21e1b99ff1` |
| `cert_59_60.tar.gz` | 19 MB | `76eb8a4803e2e04698490aef37210980f2675fa5f3c28c644bf0eb55925d1cd0` |

The checker's reports are `data/check_*.txt`.

## Reproducing

Locally, on the small set ($\pi_{22}$, $\pi_{23}$, seconds; needs `cargo` and `python3`):

```bash
cd metalibrary
(cd rust && cargo build --release --bin cert)
rust/target/release/cert cert/blocks_22_23.txt cert/cells_22_23.txt /tmp/cert_22_23 1
python3 cert/check.py cert/cells_22_23.txt /tmp/cert_22_23 22 23
python3 cert/selftest.py cert/cells_22_23.txt /tmp/cert_22_23 22 23
```

The published certificates, with the same `check.py` and no generator:

```bash
curl -LO https://github.com/ispacex/metalibrary/releases/download/certificates-2026-10-15/cert_49_50_51.tar.gz
tar -xzf cert_49_50_51.tar.gz
python3 cert/check.py cert/cells_49_50_51.txt cert_49_50_51 49 50 51
```

Full runs go to a remote machine (`../../remote/`, from the top of the repository):

```bash
python3 metalibrary/cert/plan.py 49 50 51     # cells_49_50_51.txt, blocks_49_50_51.txt
remote/mr-remote.sh submit --name cert -- 'cd metalibrary && cert/run.sh 49 50 51'
remote/mr-remote.sh submit --name lean -- 'cd metalibrary/cert/lean && ./run.sh 49_50_51 49:2:2 50:3:3 51:1:1'
```

`lean/run.sh` takes the archive from the directory `$CERT_ARCHIVE`, or downloads it from the
release and checks it against `SHA256SUMS`; `gen_stage.py` writes `MetalibCert/Stage_<TAG>.lean`
with the theorem `rule_survivors`, and `lake build` checks it. The Lean project has no Mathlib:
only the Lean core and `Std`.

## What is not covered

- Toda's values are not checked.
- That the $E^2$ page of this complex is the $E^2$ of the spectral sequence of the paper, and that
  the formulas of §2 define the lambda algebra correctly, is the mathematics of the paper. The
  checkers verify $d^2=0$ on all words of small cells as a test of the conventions (in particular,
  of $N(k)$ with the ceiling).
- The rule itself is our reading of the lecture (`../rapacious.py`).
