# SpaSM against lowmem on blocks of the differential (MATH-106)

**Question.** Is SpaSM (sparse rank over $\mathbb F_p$, OpenMP; https://github.com/cbouilla/spasm)
faster than `lowmem` on the blocks of the differential? `lowmem` computes rows in parallel and
eliminates in one thread. If SpaSM were faster, it would be used for the large open blocks.

**Answer: no.** On every block SpaSM gives the same rank where it finishes, but it is 60–80 times
slower than `lowmem` on a block of $3\cdot10^5$ words, and does not finish in 10–20 minutes on blocks of
$10^6$–$3\cdot10^7$ words (stopped after 10–20 min), where `lowmem` takes 4 s, 33–41 s and 2.5–4.6 min.
`lowmem`'s elimination is not the bottleneck: it needs 0.01–1.8 GB, and most of its time goes into
computing the rows. The same rows streamed to `/dev/null` (`sms`) take almost as long as `lowmem`.

## Setup

- SpaSM at commit `09c40943f1d4b754f89fb97fc9ddf2b8e53e967e` (master, 2024-11-04, v1.3), built by
  `build.sh` with Givaro and FFLAS-FFPACK from conda-forge. There is one local change: the `-Werror` of
  `src/CMakeLists.txt` is removed, because newer GCC warns about format truncation.
- `../rust/src/bin/sms.rs` writes a block as an SMS matrix. Rows are source words and columns are
  target words, both in `lowmem`'s lexicographic order. The matrix is streamed into `rank --modulus 3`
  and never written to disk. `--flip` reverses the columns, so that SpaSM's structural pivot (the
  leftmost entry) is `lowmem`'s pivot (the largest word).
- `bench.sh BLOCKS THREADS` runs the following on each block:
  - `lowmem`;
  - `sms > /dev/null`;
  - `sms [--flip] | rank` (`spasm-plain`, `spasm-flip`), stopped after `SPASM_TIMEOUT` seconds;
  - `certlow`.
- The machines:
  - kimmy: 3 threads, the blocks up to $5\cdot10^6$ words;
  - ax42: 4 threads, the blocks of $2\cdot10^7$–$3\cdot10^7$ words.

  ax42 was shared with other load, so its times are only rough; on a quiet run `lowmem` took 61 s on
  76 17 6.
- Time is wall clock, memory is maximum RSS (GNU time). For SpaSM, the last column is SpaSM's own
  echelonization time; the rest is reading the matrix.

## Results

| block $(n,s,c)$ | rows × cols | nonzeros | rank (lowmem) | lowmem | certlow | sms alone | SpaSM |
|---|---|---|---|---|---|---|---|
| 61 12 6 | 308 910 × 269 346 | 2.23 M | 162 238 | 1.5 s, 133 MB | 1.7 s, 138 MB | 1.2 s | plain: 90.7 s, 103 MB (echelon 88.8 s), rank 162 238 ✓; flip: 125.5 s, 515 MB, rank 162 238 ✓ |
| 66 13 4 | 1 002 000 × 780 175 | 6.83 M | 476 508 | 4.4 s, 296 MB | — | 3.7 s | plain: > 1200 s (stopped), 234 MB |
| 84 20 13 | 4 992 288 × 1 550 400 | 22.8 M | 1 346 910 | 32.9 s, 648 MB | 37.1 s, 684 MB | 29.7 s | plain: > 600 s (stopped), 520 MB |
| 72 13 6 | 5 033 070 × 5 750 250 | 47.3 M | 2 899 325 | 40.5 s, 969 MB | 47.1 s, 1068 MB | 27.2 s | plain: > 600 s (stopped), 998 MB |
| 76 17 6 | 20 940 920 × 9 731 904 | 134.7 M | 7 256 976 | 158.8 s, 1.24 GB (61 s on a quieter run) | 92.1 s, 1.35 GB | 106.4 s | plain: > 900 s (stopped), 2.9 GB; still in the first pivot search (4.4 M of 20.9 M rows) |
| 81 15 9 | 29 718 040 × 37 455 704 | 335.5 M | 18 069 830 | 276.5 s, 2.67 GB | 478.5 s, 2.96 GB | 193.6 s | plain: > 900 s (stopped), 7.0 GB |

The `lowmem` ranks of 61 12 6 and 66 13 4 equal those of `../data/ranks_part1.csv`. SpaSM's rank
equals `lowmem`'s wherever SpaSM finished.

**Why SpaSM loses here.** Here is SpaSM's log on 61 12 6.
- The first round finds structural pivots for about half of the rows.
- It then computes a sparse Schur complement for the other 146 714 rows. This step takes 77 of the
  79 s, and almost all of these rows are dependent (rank 0 after them).
- The second round finds 42 pivots, and the dense tail is $81\times107\,108$ of rank 0.

`lowmem` takes the largest word as pivot, in lexicographic order, on a matrix whose rows are already
nearly echelon in that order. A dependent row then reduces to zero in a few steps, with almost no
fill (0.01–1.8 GB of pivot rows). Flipping the columns for SpaSM does not help: it took 125 s instead of 90 s.

**GPU (step 3 of the plan): not needed.** There is no dense tail. SpaSM's dense remainder on
61 12 6 has rank 0, and `lowmem`'s pivot rows stay sparse: 1.78 GB on the block of $3\cdot10^7$ words.
Nothing here is a dense $\mathbb F_3$ matrix with tens of thousands of columns.

## What to use instead

- **Ranks.** `lowmem`, with independent blocks in parallel (`par_blocks.sh BLOCKS PAR THREADS`,
  step 2 of the plan).
- **Certificates.** `certlow` (`../rust/src/bin/certlow.rs`). It writes the same file as `cert`,
  which `../cert/check.py` and the Lean project check: byte-identical on 61 12 6 and 81 19 1, and
  `check.py` accepts 81 19 1. Its memory is that of `lowmem`, and its time is about the same.

  The certificate files are large: about 45–54 bytes per source word uncompressed (16 MB for
  61 12 6, 239 MB for 84 20 13, 294 MB for 72 13 6, 944 MB for 76 17 6).

**The limit is the checker, not the generator.** `check.py` lists every word of a block as Python
tuples, about 2 KB per word: 431 MB on the $2\cdot10^5$-word block 81 19 1. A block of $10^6$ words
needs about 2 GB, $5\cdot10^6$ about 10 GB, and $3\cdot10^7$ about 60 GB. The Lean check needs more.
Certificates of the large blocks can be written now, but checking them needs either a checker that
does not list the words, or that much RAM.

## Reproducing

```bash
cd metalibrary
spasm/bench.sh spasm/blocks_small.txt 3            # SPASM_TIMEOUT=1200 SPASM_VARIANTS="plain flip"
spasm/bench.sh spasm/blocks_large.txt 4
spasm/par_blocks.sh data/open_blocks_part2.txt 2 2 lowmem
```
