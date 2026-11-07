# SpaSM against lowmem on blocks of the differential (MATH-106)

**Question.** Is SpaSM (sparse rank over $\mathbb F_p$, OpenMP; https://github.com/cbouilla/spasm)
faster than `lowmem` on the blocks of the differential? `lowmem` computes rows in parallel and
eliminates in one thread. If SpaSM were faster, it would be used for the large open blocks.

**Answer: no.** On every block SpaSM gives the same rank where it finishes, but it is 60–80 times
slower than `lowmem` on a block of $3\cdot10^5$ words (60–84×), and does not finish in 10–20 minutes on blocks of
$10^6$–$3\cdot10^7$ words (stopped after 10–20 min), where `lowmem` takes 4 s, 33–41 s and 2.5–4.6 min.
`lowmem`'s elimination is not the bottleneck: it needs 0.01–1.8 GB, and most of its time goes into
computing the rows. The same rows streamed to `/dev/null` as text (`sms`) take 67–80% of `lowmem`'s time on the large blocks.

## Setup

- SpaSM at commit `09c40943f1d4b754f89fb97fc9ddf2b8e53e967e` (master, 2024-11-04, v1.3), built by
  `build.sh` with Givaro and FFLAS-FFPACK from conda-forge. There is one local change: the `-Werror` of
  `src/CMakeLists.txt` is removed, because newer GCC warns about format truncation.
- `../rust/src/bin/sms.rs` writes a block as an SMS matrix. Rows are source words and columns are
  target words, both in `lowmem`'s lexicographic order. The matrix is streamed into `rank --modulus 3`
  and never written to disk. `--flip` reverses the columns, so that SpaSM's structural pivot (the
  leftmost entry) is `lowmem`'s pivot (the largest word). SpaSM's `rank` transposes a matrix with fewer
  rows than columns (it has `--no-transpose`, not used here), so 72 13 6 and 81 15 9 were eliminated
  as their transposes; flip was only tried on 61 12 6.
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
  echelonization time; the rest is generating, streaming and parsing the matrix (the generator `sms`
  and SpaSM run at the same time, each with THREADS threads).

## Results

| block $(n,s,c)$ | rows × cols | nonzeros | rank (lowmem) | lowmem | certlow | sms alone | SpaSM |
|---|---|---|---|---|---|---|---|
| 61 12 6 | 308 910 × 269 346 | 2.23 M | 162 238 | 1.5 s, 133 MB | 1.7 s, 138 MB | 1.2 s | plain: 90.7 s, 103 MB (echelon 88.8 s), rank 162 238 ✓; flip: 125.5 s, 515 MB, rank 162 238 ✓ |
| 66 13 4 | 1 002 000 × 780 175 | 6.83 M | 476 508 | 4.4 s, 296 MB | — | 3.7 s | plain: > 1200 s (stopped), 234 MB |
| 84 20 13 | 4 992 288 × 1 550 400 | 22.8 M | 1 346 910 | 32.9 s, 648 MB | 37.1 s, 684 MB | 29.7 s | plain: > 600 s (stopped), 520 MB |
| 72 13 6 | 5 033 070 × 5 750 250 | 47.3 M | 2 899 325 | 40.5 s, 969 MB | 47.1 s, 1068 MB | 27.2 s | plain: > 600 s (stopped), 998 MB |
| 76 17 6 | 20 940 920 × 9 731 904 | 134.7 M | 7 256 976 | 158.8 s, 1.24 GB (61 s on a quieter run) | 92.1 s, 1.35 GB | 106.4 s | plain: > 900 s (stopped), 2.9 GB; still in the first pivot search (4.4 M of 20.9 M rows) |
| 81 15 9 | 29 718 040 × 37 455 704 | 335.5 M | 18 069 830 | 276.5 s, 2.67 GB | 478.5 s, 2.96 GB | 193.6 s | plain: > 900 s (stopped), 7.0 GB |

The `lowmem` ranks of 61 12 6, 66 13 4 and 84 20 13 equal those of `../data/ranks_part1.csv`. SpaSM's rank
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
Nothing here is a dense $\mathbb F_3$ matrix with tens of thousands of columns. This is an inference
from one SpaSM log and from `lowmem`'s memory, not a measurement on every block.

## What to use instead

- **Ranks.** `lowmem`, with independent blocks in parallel (`par_blocks.sh BLOCKS PAR THREADS`,
  step 2 of the plan).
- **Certificates.** `certlow` (`../rust/src/bin/certlow.rs`). It writes the same file as `cert`,
  which `../cert/check.py` and the Lean project check: byte-identical on 61 12 6 and 81 19 1, and
  `check.py` accepts 81 19 1. Its memory is that of `lowmem`, and its time within about 1–1.7 times `lowmem`'s.

  The certificate files are large: about 45–58 bytes per source word uncompressed (16 MB for
  61 12 6, 239 MB for 84 20 13, 294 MB for 72 13 6, 944 MB for 76 17 6).

**The limit is the checker, not the generator.** `check.py` lists every word of a block as Python
tuples and caches normal forms; its total memory is about 2 KB per word: 431 MB on the $2\cdot10^5$-word block 81 19 1. A block of $10^6$ words
needs about 2 GB, $5\cdot10^6$ about 10 GB, and $3\cdot10^7$ about 60 GB. The Lean check (which uses 7.7 GB on π₅₉–π₆₀ already) would likely need more.
Certificates of the large blocks can be written now, but checking them needs either a checker that
does not list the words, or that much RAM.

## The open blocks of `open_blocks_part2.txt` (step 2: blocks in parallel)

These are 84 blocks, $1.07\cdot10^9$ words in all, the largest of $3.0\cdot10^7$. They were computed by
`par_blocks.sh data/open_blocks_part2.txt 2 2 lowmem` on ax42 in 1 h 39 min: two blocks at a time,
2 threads each, 4 cores. The largest block took 7.5 min and at most 1.85 GB of pivot rows. The ranks
are in `../data/ranks_part2.csv`.

`merge_ranks.py data/ranks_part1.csv data/ranks_part2.csv` gives the exact dimension of 656 cells,
76 more than before (`../data/e2_known.csv`). Of the 76 new cells, 21 were open in `e2_colours.csv`;
the new ranks settle 9 of them as nonzero and 12 as zero. The other 55 were already determined
(11 nonzero, 44 zero), and the ranks agree with them.
**All 656 agree with the $E^2$ recovered from the $Q$-weight (`../data/e2_qgrade.csv`), 0 disagreements**.
Only 230 of these cells have a row in `e2_qgrade.csv` (the rest are zero there and here), so the check
has substance on the 21 open cells and on the nonzero ones. These ranks have no
certificates yet (see the checker limit above).


## The rest of `open_blocks.txt`

The 65 blocks of `open_blocks.txt` that are neither in part1 nor in part2 have $5.54\cdot10^9$ words.
Each has more than $3\cdot10^7$ words, and the largest has $3.0\cdot10^8$. Their ranks are in
`../data/ranks_part3.csv`. They were computed in two jobs:
- the 19 blocks over $10^8$ words on ax42, one at a time with 8 threads, in 3 h 6 min
  (ax42/tm/20261106-185100-m106-rest-big-0afb999);
- the 46 blocks of $3\cdot10^7$–$10^8$ words on kimmy, two at a time with 3 threads, in 3 h 55 min
  (kimmy/tm/20261106-185101-m106-rest-mid-0afb999).

With this, all 846 blocks of `open_blocks.txt` have ranks.

`merge_ranks.py` on part1, part2 and part3 gives 714 cells, 58 of them new. 28 of the new cells were
open in `e2_colours.csv`: 13 are nonzero and 15 are zero. The other 4 new cells that have a row in
`e2_colours.csv` were already determined (all nonzero), and 26 had no row there (already known to be
zero; all 26 come out zero). **No open cell of `e2_colours.csv` is left. All 714 cells agree with
`e2_qgrade.csv`.** Like part2, these ranks have no certificates: every block is far above the size
the current `check.py` can hold in memory.

## Certificates: what is certified and what is not

**Decision.** The certificate files themselves are not stored: they are 45–58 bytes per word (17.8 GB
for part1 alone). For each block, `cert_hashes.sh` has `certlow` write the certificate, the unchanged
trusted `../cert/check.py` check it (through `check_block.py`), and keeps only the certificate's sha256
and the rank `check.py` accepted. `certlow` is deterministic, so a certificate can be rebuilt and
compared with its hash. Only blocks whose check fits in 14 GB get a certificate. The trusted checkers
(`check.py`, Lean) are not changed.

**part1 (`../data/open_blocks_part1.txt`, 697 blocks, $3.05\cdot10^8$ words): 696 certified, 1 not.**
- `../data/cert_hashes_part1.csv` (n, s, colour, words, rank, bytes, sha256, check) lists 696 blocks
  of up to $4.99\cdot10^6$ words. Each rank there is the one `check.py` accepted, and each equals the
  rank in `../data/ranks_part1.csv`. As above, a block certificate proves rank ≥ that number; the exact
  rank also needs an upper bound, which `cert/` gets from cell certificates.
- `../data/cert_uncertified_part1.txt` lists the one block without a certificate: **83 12 8**
  ($4.94\cdot10^6$ words). Its `check.py` run needed more than 14 GB (`CHECK_MEM_GB=14`).
- `check.py` took 2–6 KB per word, not the 2 KB estimated above, because its caches grow with the length
  of the words. So the limit is not a word count. 84 12 9 and 83 17 13 ($1.8\cdot10^6$ words) failed
  with 6 GB and passed with 14 GB, while 84 20 13 ($5.0\cdot10^6$ words, short words) passed with 12 GB.
- `python3 spasm/check_cert_hashes.py` checks the bookkeeping: every part1 block is in exactly one of
  the two files, and words and ranks agree with `open_blocks_part1.txt` and `ranks_part1.csv`.

**How the CSV was made.** It is the union of the per-block results (`logs/*.csv`) of these jobs:
- kimmy: `kimmy/tm/20261106-185305-m106-cert-small-54dcf31` (blocks up to $10^6$ words),
  `kimmy/tm/20261106-230743-m106-cert-K1-a8073fd`, `kimmy/tm/20261107-002108-m106-cert-S1-709ad7b`,
  `kimmy/tm/20261107-002110-m106-cert-S2-709ad7b`, `kimmy/tm/20261107-022236-m106-cert-R1-c94a7ba`,
  `kimmy/tm/20261107-022238-m106-cert-RK-c94a7ba`;
- ax42: `ax42/tm/20261106-230740-m106-cert-A1-a8073fd`, `ax42/tm/20261107-021850-m106-cert-RA-c94a7ba`,
  `ax42/tm/20261107-083210-m106-cert-R14-f389ab3`;
- blocks that were also finished in stopped or probe jobs (`m106-cert-1e6`, `m106-cert-2e6`,
  `m106-speedprobe-*`) are duplicates of rows above.

The first four kimmy jobs were killed for memory partway, before `cert_hashes.sh` capped each check
(`c94a7ba`), and the blocks they had not finished were rerun. 7 blocks were checked twice (81 19 1 on
both machines), always with the same hash and rank. A tm job on each runner compared the CSV with every
`logs/*.csv` there. It found 0 differences, and the two runners together account for all 696 rows
(`kimmy/tm/20261107-095822-m106-verify-csv-887cfe4`, `ax42/tm/20261107-095823-m106-verify-csv-887cfe4`).

**part2 and the rest (`../data/ranks_part2.csv`, `../data/ranks_part3.csv`): not certified.** These are
149 blocks, $6.61\cdot10^9$ words, from $5.0\cdot10^6$ to $3.0\cdot10^8$ words per block. At 2–6 KB per
word, `check.py` would need from about 10 GB to over 600 GB per block. Their ranks come from `lowmem`
alone, so the cells of `../data/e2_known.csv` that depend on them are not certified, although they agree
with the $Q$-weight. Certifying them needs a checker that does not list the words, which would be a
change to trusted code.

## Reproducing

```bash
cd metalibrary
spasm/bench.sh spasm/blocks_small.txt 3            # SPASM_TIMEOUT=1200 SPASM_VARIANTS="plain flip"
spasm/bench.sh spasm/blocks_large.txt 4
spasm/par_blocks.sh data/open_blocks_part2.txt 2 2 lowmem
CHECK_MEM_GB=14 spasm/cert_hashes.sh BLOCKS 1          # sha256 + check.py rank per block -> $JOB_OUT/cert_hashes.csv
python3 spasm/check_cert_hashes.py
```
