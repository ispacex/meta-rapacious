# meta-rapacious

A recomputation of the "rapacious spectral sequence" from R. Mikhailov's lecture
*Coloured metalibraries. The mind of space* (2 September 2016,
[video](https://www.youtube.com/watch?v=yE49kR_RA7o), in Russian).

The lecture describes the 3-torsion of $\pi_n(S^2)$ as what is left of the $E^2$ page of a
"coloured metalibrary" — admissible words in letters $\lambda_i,\mu_i$, coloured by the number of
$\mu$'s — when the spectral sequence eats itself as fast as possible, constrained only by the
colour. This repository

* computes that $E^2$ page from scratch: the mod-3 lambda algebra for $S^3$ in the conventions of
  S. O. Ivanov, R. Mikhailov, J. Wu, *On nontriviality of homotopy groups of spheres*,
  [arXiv:1506.00952](https://arxiv.org/abs/1506.00952), §2, with the colour as an extra grading,
  checked against the unstable Ext of $S^3$ from the independent program
  [sseq/ext](https://github.com/JoeyBF/sseq);
* runs the rapacious rule on it — $d_r\colon(n,s,c)\to(n-1,s+r,c+1)$, maximal rank on every page —
  and compares what survives with Toda's tables: the 1962 table up to $\pi_{22}$ and the 2003 table
  of unstable 3-primary groups up to $\pi_{82}$. The rule agrees with Toda for all $n\le48$ and
  leaves extra classes from $\pi_{49}$ on;
* proves the first disagreements — over $\pi_{49}$, $\pi_{50}$, $\pi_{51}$, $\pi_{59}$, $\pi_{60}$ the rule
  leaves 2, 3, 1, 2, 1 classes where Toda has 1, 1, 0, 1, 0 — by certificates that are checked
  independently of the code that computed $E^2$: a checker in Python written from the paper alone,
  and a Lean 4 project;
* builds the site with the results, https://ispacex.github.io/metalibrary/ (English and Russian).

All numbers are 3-primary: the rank of the 3-torsion, every summand $\mathbb Z/3$.

## Layout

| Path | What |
|---|---|
| [`metalibrary/`](metalibrary/README.md) | the lambda algebra (`lambda3.py`), the homology of the metalibrary by colour (`metalib.py`, and `rust/` for speed), the colour solver, the rapacious rule (`rapacious.py`), Toda's 2003 table (`toda2003.py`), the picture (`plot_e2.py`), the computed data (`data/`) |
| [`metalibrary/cert/`](metalibrary/cert/README.md) | the certificates for $\pi_{49}$–$\pi_{51}$, $\pi_{59}$, $\pi_{60}$: the plan (`plan.py`), the untrusted generator (`../rust/src/bin/cert.rs`), the independent checker (`check.py`, `selftest.py`), the Lean project (`lean/`) |
| `site/` | the generator of the site (`build_site.py`) and of its search index (`two_tier.sh`) |
| [`remote/`](remote/README.md) | running long jobs on a remote Linux box (`mr-remote.sh`; the host comes from the environment) |

The READMEs of the subdirectories also exist in Russian (`*.ru.md`), the language the work was done in.

## Reproducing

Python 3.12 or later. The checker and the site need only the standard library; the computations
need NumPy, the colour solver SciPy, the picture matplotlib (`requirements.txt`). The Rust code
needs a stable toolchain, the Lean project [elan](https://github.com/leanprover/elan) (the
toolchain is pinned in `metalibrary/cert/lean/lean-toolchain`; no Mathlib).

```bash
git clone https://github.com/ispacex/meta-rapacious.git && cd meta-rapacious
python3 -m venv venv && venv/bin/pip install -r requirements.txt && . venv/bin/activate
cd metalibrary

# the lambda algebra: relations homogeneous, d^2 = 0, H(Lambda(1)) = the Ext of sseq, up to stem 20
python3 check_lambda.py 20 data/sseq_S3_p3.csv

# E^2 of the metalibrary by colour, up to pi_40 (Rust; up to pi_64 takes about 2 minutes and 2 GB)
(cd rust && cargo build --release) && rust/target/release/metalib 40 > /tmp/e2_40.csv

# the rapacious rule on the coloured E^2 up to pi_150, compared with Toda
python3 rapacious.py data/e2_qgrade.csv

# the certificates on the small set pi_22, pi_23 (seconds)
rust/target/release/cert cert/blocks_22_23.txt cert/cells_22_23.txt /tmp/cert_22_23 1
python3 cert/check.py cert/cells_22_23.txt /tmp/cert_22_23 22 23
python3 cert/selftest.py cert/cells_22_23.txt /tmp/cert_22_23 22 23

# the published certificates for pi_49-pi_51 (about half a minute, 1 GB)
curl -LO https://github.com/ispacex/metalibrary/releases/download/certificates-2026-10-15/cert_49_50_51.tar.gz
tar -xzf cert_49_50_51.tar.gz && python3 cert/check.py cert/cells_49_50_51.txt cert_49_50_51 49 50 51

# Lean on the small set (Linux: the script reports time and memory through GNU time)
cd cert/lean && ./run.sh 22_23 22:1:1 23:0:0
```

The Lean check of $\pi_{49}$–$\pi_{51}$ takes about 5 minutes and 1.6 GB, that of $\pi_{59}$–$\pi_{60}$
three and a half hours and 8 GB; such runs, and the larger enumerations, go to a remote machine
through [`remote/`](remote/README.md). See [`metalibrary/cert/README.md`](metalibrary/cert/README.md).

### The site

```bash
(cd metalibrary && PLOT_NMAX=100 python3 plot_e2.py data/e2_qgrade.csv ru en)   # the two pictures
python3 site/build_site.py /tmp/metalibrary-site
site/two_tier.sh /tmp/metalibrary-site     # the search index (needs git, node and network access)
```

The output is the content of [ispacex/metalibrary](https://github.com/ispacex/metalibrary), which
GitHub Pages serves at https://ispacex.github.io/metalibrary/. The pages are not edited by hand.

## Links

* The site: https://ispacex.github.io/metalibrary/ (in Russian: https://ispacex.github.io/metalibrary/ru/).
* The certificates: the release
  [certificates-2026-10-15](https://github.com/ispacex/metalibrary/releases/tag/certificates-2026-10-15)
  of ispacex/metalibrary, with `SHA256SUMS`.
* S. O. Ivanov, R. Mikhailov, J. Wu, *On nontriviality of homotopy groups of spheres*,
  [arXiv:1506.00952](https://arxiv.org/abs/1506.00952) (2015).
* sseq/ext, an independent computation of the unstable Ext: https://github.com/JoeyBF/sseq. The
  $Q$-weight (the colour) comes from the example `qgrade_dims` in the fork
  [ispacex/sseq](https://github.com/ispacex/sseq/tree/math-54-qgrade), branch `math-54-qgrade`.
* H. Toda, *Unstable 3-primary homotopy groups of spheres*, Econoinformatics (Himeji Dokkyo
  University) 29 (2003), 1–77; a [scan](https://www.sas.rochester.edu/mth/sites/doug-ravenel/otherpapers/Toda03-ocr.pdf)
  on D. Ravenel's site.
* H. Toda, *Composition methods in homotopy groups of spheres*, Annals of Mathematics Studies 49,
  Princeton University Press, 1962†; used through two reprints of its table: D. Ravenel, *Complex
  cobordism and stable homotopy groups of spheres*, Table A3.4, and the
  [PKU table](https://math.pku.edu.cn/teachers/zhaoxa/_web_resource/_math_table/sphere_homotopy.htm).
* R. Mikhailov, *Coloured metalibraries. The mind of space*, lecture, 2 September 2016:
  https://www.youtube.com/watch?v=yE49kR_RA7o.

† not checked against the original.

## License

[MIT](LICENSE).
