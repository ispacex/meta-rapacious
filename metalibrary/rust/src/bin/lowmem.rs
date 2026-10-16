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

use algebra::*;
use rayon::prelude::*;
use std::io::Write;
use std::time::Instant;

const START: usize = 0; // state before the first letter (only lambda_1, mu_1 may follow)
const NONE: u32 = u32::MAX;

/// Completion counts: cnt[state][stem][len][col] = number of ways to continue a word whose last
/// letter is `state` by `len` letters of total degree `stem` containing `col` mu's, ending with a
/// lambda and admissible throughout. State 0 is the start; state x >= 2 is the letter code x.
struct Counts {
    ns: usize,
    st: usize,
    ln: usize,
    cl: usize,
    t: Vec<u64>,
}

impl Counts {
    fn new(stem: i64, len: usize, col: usize) -> Counts {
        let imax = ((stem + 1) / 4 + 1) as usize;
        let ns = 2 * imax + 2;
        let (st, ln, cl) = (stem as usize + 1, len + 1, col + 1);
        let mut c = Counts { ns, st, ln, cl, t: vec![0; ns * st * ln * cl] };
        for l in 0..ln {
            for state in 0..ns {
                if state == 1 { continue; } // code 1 is mu_0: not a metalibrary letter
                for s in 0..st {
                    for k in 0..cl {
                        let v = if l == 0 {
                            (s == 0 && k == 0 && state != START && !is_mu(state as u8)) as u64
                        } else {
                            let top = if state == START { 1 } else { top(state as u8) };
                            let mut v = 0u64;
                            for j in 1..=top.min(imax as i64) {
                                for x in [lam(j), mu(j)] {
                                    let d = deg(x) as usize;
                                    let m = is_mu(x) as usize;
                                    if d <= s && m <= k && (x as usize) < ns {
                                        v += c.get(x as usize, s - d, l - 1, k - m);
                                    }
                                }
                            }
                            v
                        };
                        let i = c.at(state, s, l, k);
                        c.t[i] = v;
                    }
                }
            }
        }
        c
    }
    fn at(&self, state: usize, s: usize, l: usize, k: usize) -> usize {
        ((state * self.st + s) * self.ln + l) * self.cl + k
    }
    fn get(&self, state: usize, s: usize, l: usize, k: usize) -> u64 {
        if state >= self.ns || s >= self.st || l >= self.ln || k >= self.cl { return 0; }
        self.t[self.at(state, s, l, k)]
    }
    /// The word with lexicographic number r among words of (stem, len, col).
    fn unrank(&self, stem: i64, len: usize, col: usize, mut r: u64) -> Word {
        let (mut s, mut k, mut state) = (stem as usize, col, START);
        let mut w = Vec::with_capacity(len);
        for p in 0..len {
            let top = if state == START { 1 } else { top(state as u8) };
            let mut chosen = None;
            'choose: for j in 1..=top {
                for x in [lam(j), mu(j)] {
                    let (d, m) = (deg(x) as usize, is_mu(x) as usize);
                    if d > s || m > k { continue; }
                    let n = self.get(x as usize, s - d, len - p - 1, k - m);
                    if r < n { chosen = Some(x); break 'choose; }
                    r -= n;
                }
            }
            let x = chosen.expect("unrank out of range");
            w.push(x);
            s -= deg(x) as usize;
            k -= is_mu(x) as usize;
            state = x as usize;
        }
        w
    }
    /// Lexicographic number of a word of (stem, len, col); None if it is not such a word.
    fn rank(&self, w: &[u8], stem: i64, col: usize) -> Option<u64> {
        let len = w.len();
        let (mut s, mut k, mut state, mut r) = (stem as usize, col, START, 0u64);
        for (p, &x) in w.iter().enumerate() {
            let top = if state == START { 1 } else { top(state as u8) };
            if idx(x) < 1 || idx(x) > top { return None; }
            for j in 1..=idx(x) {
                for y in [lam(j), mu(j)] {
                    if y >= x { break; }
                    let (d, m) = (deg(y) as usize, is_mu(y) as usize);
                    if d <= s && m <= k { r += self.get(y as usize, s - d, len - p - 1, k - m); }
                }
            }
            let (d, m) = (deg(x) as usize, is_mu(x) as usize);
            if d > s || m > k { return None; }
            s -= d;
            k -= m;
            state = x as usize;
        }
        if s == 0 && k == 0 && !is_mu(*w.last()?) { Some(r) } else { None }
    }
}

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
            .map(|i| {
                let w = cs.unrank(stem, s, c, i);
                let mut row: Vec<(u32, u8)> = d_word(&w)
                    .into_iter()
                    .map(|(v, x)| {
                        let id = ct.rank(&v, stem - 1, c)
                            .unwrap_or_else(|| panic!("d leaves the metalibrary: {:?} -> {:?}", w, v));
                        (id as u32, x)
                    })
                    .collect();
                row.sort_unstable_by_key(|t| t.0);
                row
            })
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
