//! Rank certificates for large blocks, in the format of `cert` (checked by cert/check.py and the
//! Lean project), with the memory of `lowmem` (MATH-106). This program is NOT trusted.
//!
//!     certlow BLOCKS OUTDIR [THREADS]          # BLOCKS: lines "n s c [words]"
//!
//! For each block d: (n,s,c) -> (n-1,s+1,c) it writes OUTDIR/block_n_s_c.txt: the header
//! "block n s c words W targets T rank R", R lines "y t w:k w:k ..." sorted by the pivot t, "end".
//! It is the elimination of `cert` (pivot = largest target word, rows in lexicographic order,
//! each pivot row carried with its combination y of source words), so for the same block it writes
//! the same file; but words are numbered with the completion counts of `lowmem` instead of being
//! stored, rows are computed in parallel a chunk at a time, and pivot rows and their y live in
//! arenas. Memory: 4 bytes per target word plus 5 bytes per stored entry of the pivot rows and y.

#[path = "../algebra.rs"]
mod algebra;
#[path = "../numbering.rs"]
mod numbering;

use numbering::*;
use rayon::prelude::*;
use std::io::Write;
use std::time::Instant;

const NONE: u32 = u32::MAX;
type Vec3 = Vec<(u32, u8)>;

fn name(w: &[u8]) -> String {
    w.iter()
        .map(|&c| format!("{}{}", if algebra::is_mu(c) { 'm' } else { 'l' }, algebra::idx(c)))
        .collect::<Vec<_>>()
        .join(".")
}

/// a + f*b for sorted sparse vectors over F_3.
fn axpy(a: &[(u32, u8)], f: u8, bi: &[u32], bc: &[u8]) -> Vec3 {
    let mut o = Vec::with_capacity(a.len() + bi.len());
    let (mut i, mut j) = (0, 0);
    while i < a.len() || j < bi.len() {
        if j == bi.len() || (i < a.len() && a[i].0 < bi[j]) { o.push(a[i]); i += 1; }
        else if i == a.len() || bi[j] < a[i].0 { o.push((bi[j], f * bc[j] % 3)); j += 1; }
        else { let v = (a[i].1 + f * bc[j]) % 3; if v != 0 { o.push((a[i].0, v)); } i += 1; j += 1; }
    }
    o
}

struct Arena { off: Vec<u64>, ids: Vec<u32>, cf: Vec<u8> }
impl Arena {
    fn new() -> Self { Arena { off: vec![0], ids: vec![], cf: vec![] } }
    fn push(&mut self, v: &[(u32, u8)], k: u8) {
        for &(i, c) in v { self.ids.push(i); self.cf.push(c * k % 3); }
        self.off.push(self.ids.len() as u64);
    }
    fn get(&self, p: u32) -> (&[u32], &[u8]) {
        let (a, b) = (self.off[p as usize] as usize, self.off[p as usize + 1] as usize);
        (&self.ids[a..b], &self.cf[a..b])
    }
    fn bytes(&self) -> usize { self.ids.len() * 5 + self.off.len() * 8 }
}

fn block(n: i64, s: usize, c: usize, out: &str) {
    let t0 = Instant::now();
    let stem = n - 3;
    let cs = Counts::new(stem, s, c);
    let ct = Counts::new(stem - 1, s + 1, c);
    let nsrc = cs.get(START, stem as usize, s, c);
    let ntgt = ct.get(START, (stem - 1) as usize, s + 1, c);
    assert!(nsrc < NONE as u64 && ntgt < NONE as u64, "block too large for u32 numbers");
    let mut pivot_of = vec![NONE; ntgt as usize];
    let (mut rows, mut ys) = (Arena::new(), Arena::new());
    const CHUNK: u64 = 1 << 16;
    let mut start = 0u64;
    while start < nsrc {
        let end = (start + CHUNK).min(nsrc);
        let chunk: Vec<Vec3> = (start..end).into_par_iter().map(|i| block_row(&cs, &ct, stem, s, c, i)).collect();
        for (k, r0) in chunk.into_iter().enumerate() {
            let (mut r, mut y): (Vec3, Vec3) = (r0, vec![((start + k as u64) as u32, 1)]);
            while let Some(&(lead, lc)) = r.last() {
                let p = pivot_of[lead as usize];
                if p == NONE {
                    let inv = if lc == 1 { 1 } else { 2 };
                    pivot_of[lead as usize] = (rows.off.len() - 1) as u32;
                    rows.push(&r, inv);
                    ys.push(&y, inv);
                    break;
                }
                let f = (3 - lc) % 3;
                let (pi, pc) = rows.get(p);
                r = axpy(&r, f, pi, pc);
                let (yi, yc) = ys.get(p);
                y = axpy(&y, f, yi, yc);
            }
        }
        start = end;
    }
    let rank = rows.off.len() - 1;
    let t_elim = t0.elapsed().as_secs_f64();
    let mem = pivot_of.len() * 4 + rows.bytes() + ys.bytes();
    drop(rows);
    // pivots in increasing order: walk the target words; write the lines in parallel chunks
    let path = format!("{}/block_{}_{}_{}.txt", out, n, s, c);
    let mut f = std::io::BufWriter::with_capacity(1 << 22, std::fs::File::create(&path).unwrap());
    writeln!(f, "block {} {} {} words {} targets {} rank {}", n, s, c, nsrc, ntgt, rank).unwrap();
    let mut ysum = 0usize;
    for lo in (0..ntgt).step_by(CHUNK as usize) {
        let hi = (lo + CHUNK).min(ntgt);
        let text: Vec<(usize, String)> = (lo..hi)
            .into_par_iter()
            .filter(|&t| pivot_of[t as usize] != NONE)
            .map(|t| {
                let (yi, yc) = ys.get(pivot_of[t as usize]);
                let mut l = format!("y {}", name(&ct.unrank(stem - 1, s + 1, c, t)));
                for (&i, &k) in yi.iter().zip(yc) {
                    l.push(' ');
                    l.push_str(&name(&cs.unrank(stem, s, c, i as u64)));
                    l.push(':');
                    l.push_str(&k.to_string());
                }
                l.push('\n');
                (yi.len(), l)
            })
            .collect();
        for (k, l) in text { ysum += k; f.write_all(l.as_bytes()).unwrap(); }
    }
    writeln!(f, "end").unwrap();
    f.flush().unwrap();
    eprintln!("block {} {} {}: {} x {}, rank {}, |y| {}, elimination {:.1}s {:.2} GB, total {:.1}s",
              n, s, c, nsrc, ntgt, rank, ysum, t_elim, mem as f64 / 1e9, t0.elapsed().as_secs_f64());
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    if a.len() < 3 {
        eprintln!("usage: certlow BLOCKS OUTDIR [THREADS]");
        std::process::exit(2);
    }
    if let Some(t) = a.get(3) {
        rayon::ThreadPoolBuilder::new().num_threads(t.parse().unwrap()).build_global().unwrap();
    }
    std::fs::create_dir_all(&a[2]).unwrap();
    let text = std::fs::read_to_string(&a[1]).expect("cannot read the block list");
    for l in text.lines().filter(|l| !l.trim().is_empty() && !l.starts_with('#')) {
        let v: Vec<i64> = l.split_whitespace().map(|x| x.parse().unwrap()).collect();
        block(v[0], v[1] as usize, v[2] as usize, &a[2]);
    }
}
