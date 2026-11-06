//! Ranks of metalibrary blocks with little memory. Same answers as `metalib --blocks`,
//! but for blocks of 1e8+ words:
//!
//!     lowmem --blocks FILE [THREADS] > ranks.csv        # FILE: lines "n s c [words]"
//!
//! * Words are never stored. A table of completion counts (last letter, stem left, length left,
//!   colour left) gives the lexicographic number of any word and the word with a given number,
//!   so source words are made from their numbers on the fly and target words are turned into
//!   their numbers without an index. The order is the same lexicographic order the old program
//!   sorted words in, so the elimination (pivot = largest target word) is the same.
//! * Rows of the differential are computed in parallel, a chunk at a time, and fed in order to
//!   one elimination.
//! * Pivot rows live in one arena (u32 column numbers, u8 coefficients, u64 offsets); the column
//!   -> pivot map is a dense u32 array over the target block.
//! Memory: 4 bytes per target word plus the pivot rows; stderr reports both per block.

#[path = "../algebra.rs"]
mod algebra;
#[path = "../numbering.rs"]
mod numbering;

use numbering::*;
use rayon::prelude::*;
use std::io::Write;
use std::time::Instant;

const NONE: u32 = u32::MAX;

/// Elimination over F_3 with pivot = largest column; pivot rows in one arena.
struct Elim {
    pivot_of: Vec<u32>,
    off: Vec<u64>,
    ids: Vec<u32>,
    cf: Vec<u8>,
}

impl Elim {
    fn new(ncols: usize) -> Elim {
        Elim { pivot_of: vec![NONE; ncols], off: vec![0], ids: vec![], cf: vec![] }
    }
    fn rank(&self) -> usize { self.off.len() - 1 }
    fn add(&mut self, mut r: Vec<(u32, u8)>) {
        loop {
            let Some(&(lead, lc)) = r.last() else { return };
            let p = self.pivot_of[lead as usize];
            if p == NONE {
                let inv = if lc == 1 { 1 } else { 2 };
                for &(i, v) in &r {
                    self.ids.push(i);
                    self.cf.push(v * inv % 3);
                }
                self.off.push(self.ids.len() as u64);
                self.pivot_of[lead as usize] = (self.off.len() - 2) as u32;
                return;
            }
            let (a, b) = (self.off[p as usize] as usize, self.off[p as usize + 1] as usize);
            let (pi, pc) = (&self.ids[a..b], &self.cf[a..b]);
            let f = (3 - lc) % 3;
            let mut o = Vec::with_capacity(r.len() + pi.len());
            let (mut i, mut j) = (0, 0);
            while i < r.len() || j < pi.len() {
                if j == pi.len() || (i < r.len() && r[i].0 < pi[j]) { o.push(r[i]); i += 1; }
                else if i == r.len() || pi[j] < r[i].0 { o.push((pi[j], f * pc[j] % 3)); j += 1; }
                else { let v = (r[i].1 + f * pc[j]) % 3; if v != 0 { o.push((r[i].0, v)); } i += 1; j += 1; }
            }
            r = o;
        }
    }
}

fn block_rank(n: i64, s: usize, c: usize) -> (u64, usize, u64, usize) {
    let stem = n - 3;
    let cs = Counts::new(stem, s, c);
    let ct = Counts::new(stem - 1, s + 1, c);
    let nsrc = cs.get(START, stem as usize, s, c);
    let ntgt = ct.get(START, (stem - 1) as usize, s + 1, c);
    if nsrc == 0 { return (0, 0, 0, 0); }
    assert!(ntgt < NONE as u64, "target block too large for u32 numbers");
    let mut el = Elim::new(ntgt as usize);
    const CHUNK: u64 = 1 << 16;
    let mut start = 0u64;
    while start < nsrc {
        let end = (start + CHUNK).min(nsrc);
        let rows: Vec<Vec<(u32, u8)>> = (start..end)
            .into_par_iter()
            .map(|i| block_row(&cs, &ct, stem, s, c, i))
            .collect();
        for r in rows { el.add(r); }
        start = end;
    }
    let bytes = el.pivot_of.len() * 4 + el.ids.len() * 5 + el.off.len() * 8;
    (nsrc, el.rank(), ntgt, bytes)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 3 || args[1] != "--blocks" {
        eprintln!("usage: lowmem --blocks FILE [THREADS]");
        std::process::exit(2);
    }
    if let Some(t) = args.get(3) {
        rayon::ThreadPoolBuilder::new().num_threads(t.parse().unwrap()).build_global().unwrap();
    }
    let text = std::fs::read_to_string(&args[2]).expect("cannot read the block list");
    let mut out = std::io::stdout();
    writeln!(out, "n,s,colour,words,rank").unwrap();
    for l in text.lines().filter(|l| !l.trim().is_empty() && !l.starts_with('#')) {
        let f: Vec<&str> = l.split_whitespace().collect();
        let (n, s, c): (i64, usize, usize) = (f[0].parse().unwrap(), f[1].parse().unwrap(), f[2].parse().unwrap());
        let t = Instant::now();
        let (w, r, nt, bytes) = block_rank(n, s, c);
        writeln!(out, "{},{},{},{},{}", n, s, c, w, r).unwrap();
        out.flush().unwrap();
        eprintln!("block n={} s={} c={}: {} words -> {} targets, rank {}, {:.1}s, elimination {:.2} GB",
                  n, s, c, w, nt, r, t.elapsed().as_secs_f64(), bytes as f64 / 1e9);
    }
}
