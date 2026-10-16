Русская версия: [README.ru.md](README.ru.md).

# metalibrary/ — the E² page of the coloured metalibrary and the "rapacious" spectral sequence

In his lecture of 2 September 2016, R. Mikhailov states that the 3-torsion of $\pi_n(S^2)$ is
obtained from the $E^2$ page of the "coloured metalibrary" if the spectral sequence eats itself
as fast as possible, constrained only by the colour. Here $E^2$ is computed from scratch and the
rule is run on it.

The section "Results" below is the state at $\pi_{64}$, from the direct enumeration. The current
results — colours up to $\pi_{150}$ from the $Q$-weight, the rule final up to $\pi_{149}$ — are on
the site, https://ispacex.github.io/metalibrary/, which `../site/build_site.py` builds from `data/`.

## What is computed

1. **The mod-3 lambda algebra** (`lambda3.py`): relations, differential and admissibility
   following Ivanov–Mikhailov–Wu (arXiv:1506.00952, §2), rewriting into the admissible basis.
   The paper has $N(k)=k-[\tfrac{k+1}{p}]$; the brackets are taken here as the ceiling: with the
   floor, the relation for $k=1$ would contain its own left-hand side.
2. **Checks** (`check_lambda.py`): $\partial^2=0$ and $\partial\Lambda(1)\subseteq\Lambda(1)$
   on all 2.2 million words up to stem 43; $H(\Lambda(1))$ agrees with the unstable Ext of the
   sphere $S^3$ at $p=3$ computed by the independent program sseq/ext (`resolve_unstable`, module
   `S_3[3]`, https://github.com/JoeyBF/sseq) in every cell (stem, $s$).
3. **The metalibrary** in Mikhailov's definition: admissible words in $\lambda_i,\mu_i$
   ($i\ge1$) that start with $\lambda_1$ or $\mu_1$ and end with a $\lambda$. These are exactly
   the words of $\Lambda(1)$ without $\mu_0$ that end with a $\lambda$. They form a subcomplex of
   $\Lambda(1)/\Lambda(1)\mu_0$, which is checked on every word. Homology by
   $(n,s,\text{colour})$: `metalib.py` (Python, up to $\pi_{56}$) and `rust/` (the same in Rust,
   more than 20 times faster, byte-for-byte equal to the Python output up to $\pi_{56}$).
4. **Comparison**: for $n>3$ the homology of the metalibrary equals $H(\Lambda(1))$ cell by cell
   in $(n,s,\text{colour})$ (checked up to $\pi_{46}$) and equals the Ext from sseq in $(n,s)$
   (`compare_sseq.py`, up to the last computed $n$). So dropping $\mu_0$ and the words ending in
   $\mu$ removes only the tower over $\pi_3=\mathbb Z$.
5. **The rapacious rule** (`rapacious.py`): $d_r\colon (n,s,c)\to(n-1,s+r,c\pm1)$, maximal rank
   on every page, pages in order.

## Results (data up to $\pi_{64}$)

The Rust enumeration of the metalibrary is complete up to $n=64$ (141 s, 1.9 GB). A run up to
$n=72$ was stopped half-way; beyond that the computation went to a remote machine (`../remote/`).

- **The metalibrary is $E^2$ for $S^3$.** The $E^2$ of the metalibrary agrees with the Ext from
  sseq in all 188 classes for $4\le n\le64$.
- **The colours of the sandwiches and of the Toda elements** run 3 4 4 5 5 6 …, as the lecture says.
- **The rapacious rule, colour $+1$** (`data/rapacious.json`), compared with Toda's 2003 table
  (`toda2003.py`):
  - it agrees for all $n\le48$, that is, in the stems $k<46$ that Toda determined in 1967.
    The forks at $\pi_{41},\pi_{43}$ are decided in favour of the "low" filling;
  - $\pi_{44}=0$ and $\pi_{48}=0$;
  - beyond that the rule leaves extra classes: in $\pi_{49},\pi_{50},\pi_{51},\pi_{59},\pi_{60},\pi_{63}$
    (1–2 more than Toda). In $\pi_{49}$–$\pi_{60}$ they are removed by colour-preserving $d_5$:
    $\pi_{50}(5,0)\to\pi_{49}(10,0)$, $\pi_{51}(5,1)\to\pi_{50}(10,1)$, $\pi_{60}(7,0)\to\pi_{59}(12,0)$.
    Allowing all such $d_5$ breaks $\pi_{57},\pi_{58}$;
  - colour $-1$ gives no differential at all: $\pi_{44}$ stays equal to 4.

## Colours without enumeration

`colour_solver.py` recovers the colours of the $E^2$ classes from the Ext of sseq
(`data/sseq_S3_p3_150.csv`, $n\le150$) and three constraints:
- $c \equiv m-3 \pmod 4$ on the antidiagonal $m=n+s$;
- $0 \le c \le s-1$;
- the Euler characteristic $\chi(m,c)$, computed from the numbers of words, with no linear algebra.

For every cell an integer LP gives the least and the greatest number of classes of each colour.

A run on the remote machine (`../remote/`, 9 s):
- for $n\le64$ all answers agree with the enumeration; 99 cells are determined exactly;
- up to $n=84$, 146 classes out of 394 are determined uniquely, among them 47 cells with $64<n\le84$;
- the other 248 classes need the enumeration.

The result is `data/e2_colours.csv`: `status = determined` or `range lo..hi`.

## Colour modulo 4

The stem of a word is $4\sum(\text{indices})-\#\lambda$, so
$\text{colour}\equiv\text{stem}+s \pmod 4$. Hence an arrow "colour $+1$" is possible only for
$r\equiv2\pmod4$, that is, for $d_2, d_6, d_{10},\dots$. The colour itself is a separate grading:
the number of Bocksteins, the $Q$-degree in Ext. The Ext of sseq does not see it, which is why the
metalibrary had to be computed here.

## Files

- `lambda3.py`, `check_lambda.py`: the algebra and its checks.
- `metalib.py`: homology of the metalibrary or of $\Lambda(1)$ by colour (Python).
- `rust/`: `cargo build --release && target/release/metalib NMAX [THREADS] > data/e2_metalib.csv`.
- `compare_sseq.py`: the comparison with sseq/ext.
- `rapacious.py`: the rapacious rule, its variants and checks; `--list` prints the differentials.
- `plot_e2.py`: the picture `out/7_e2_rapacious_{ru,en}.png`.
- `data/e2_metalib.csv`: $n,s,\text{colour},\#\text{words},\operatorname{rank}\partial,\dim E^2$;
  `data/e2_lambda1.csv`: the same for $\Lambda(1)$ up to $\pi_{46}$;
  `data/sseq_S3_p3.csv`: the Ext from sseq up to $n=86$; `data/rapacious.json`: the outcome of the rule.
- `colour_solver.py`, `colours_to_e2.py`: colours without enumeration (above); `data/e2_colours.csv`, `data/e2_full.csv`.
- `open_blocks.py`, `needed_blocks.py`, `select_blocks.py`, `split_blocks.py`, `pick_blocks.py`,
  `merge_ranks.py`, `compare_ranks.py`: which blocks of the differential remain to be enumerated
  (`rust/src/bin/lowmem.rs`), and exact dimensions from their ranks: `data/e2_known.csv`, `data/*blocks*.txt`.
- `qgrade_to_e2.py`, `check_qgrade.py`: the colour as the $Q$-weight of Ext from a fork of sseq
  (https://github.com/ispacex/sseq, branch `math-54-qgrade`, example `qgrade_dims`) and its check
  against the lambda algebra: `data/sseq_qgrade_S3_p3_150.csv`, `data/e2_qgrade.csv` ($E^2$ with colours up to $\pi_{150}$).
- `toda2003.py`: Toda's 2003 table (3-primary $\pi_{3+k}(S^3)$, $k\le79$), read from the scan.
- `data/s2_3torsion.csv`: the 3-torsion of $\pi_n(S^2)$ by Toda's 1962 table ($n\le22$, column
  `toda_rank`), the Toda elements and sandwiches (Ivanov–Mikhailov–Wu) and the statements of the
  lecture; checked against two reprints of Toda's table (Ravenel, Table A3.4, and the PKU table).
- `cert/`: verifiable certificates of the rule's disagreement with Toda in $\pi_{49}$–$\pi_{51}$,
  $\pi_{59}$, $\pi_{60}$ ([`cert/README.md`](cert/README.md)).

## Reproducing the sseq data

```bash
git clone https://github.com/JoeyBF/sseq && cd sseq/ext
# the example unstable_dims.rs: resolve_unstable printing n,s,dim (kept in metalibrary/sseq_unstable_dims.rs)
cp .../metalibrary/sseq_unstable_dims.rs examples/unstable_dims.rs
cargo build --release --example unstable_dims
printf 'S_3[3]\n\n86\n40\n' | target/release/examples/unstable_dims > sseq_S3_p3.csv
```
