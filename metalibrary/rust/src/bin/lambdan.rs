//! Unstable Adams E_2 of the odd spheres S^{2m+1} at p = 3 from the lambda algebra Lambda(m),
//! for the check of Toda's 2003 table (toda2003/, MATH-442).
//!
//!     lambdan M KMAX [THREADS]  > e2_lambda_m.csv      # lines m,k,s,dim  (k = stem, 1 <= k <= KMAX)
//!
//! Lambda(m): admissible words whose first index is <= m (lambda3.py). As in main.rs (Lambda(1),
//! the metalibrary) the complex is the reduced one: words without mu_0 that end with a lambda.
//! For m = 1 its homology equals H(Lambda(1)) and the Ext of sseq except the tower over pi_3
//! (README, items 3-4); for m > 1 the same is not assumed but checked: the program panics if d
//! leaves the reduced words, and toda2003/check.py compares the result with sseq/ext cell by cell.
//! Blocks (stem, s, colour) are independent (d keeps the colour = number of mu's).

#[path = "../algebra.rs"]
mod algebra;

use algebra::*;
use rayon::prelude::*;
use rustc_hash::FxHashMap;

/// Reduced words of Lambda(m) with given stem, length and colour, in lexicographic order.
fn words_m(m: i64, stem: i64, len: usize, col: usize) -> Vec<Word> {
    let mut out = vec![];
    fn rec(m: i64, w: &mut Word, rem: i64, len: usize, col: usize, out: &mut Vec<Word>) {
        let used_mu = w.iter().filter(|c| is_mu(**c)).count();
        if w.len() == len {
            if rem == 0 && used_mu == col && !is_mu(*w.last().unwrap()) { out.push(w.clone()); }
            return;
        }
        let left = (len - w.len()) as i64;
        if rem < 3 * left || used_mu > col || col - used_mu > len - w.len() - 1 { return; }
        let t = if w.is_empty() { m } else { top(*w.last().unwrap()) };
        for j in 1..=t {
            for x in [lam(j), mu(j)] {
                let dx = deg(x);
                if dx <= rem - 3 * (left - 1) {
                    w.push(x);
                    rec(m, w, rem - dx, len, col, out);
                    w.pop();
                }
            }
        }
    }
    rec(m, &mut vec![], stem, len, col, &mut out);
    out.sort();
    out
}

fn rank(rows: Vec<Vec<(u32, u8)>>) -> usize {
    let mut piv: FxHashMap<u32, Vec<(u32, u8)>> = FxHashMap::default();
    for mut r in rows {
        r.sort_unstable_by_key(|t| t.0);
        loop {
            let Some(&(lead, lc)) = r.last() else { break };
            if let Some(p) = piv.get(&lead) {
                let f = (3 - lc) % 3;
                let mut o = Vec::with_capacity(r.len() + p.len());
                let (mut i, mut j) = (0, 0);
                while i < r.len() || j < p.len() {
                    if j == p.len() || (i < r.len() && r[i].0 < p[j].0) { o.push(r[i]); i += 1; }
                    else if i == r.len() || p[j].0 < r[i].0 { o.push((p[j].0, f * p[j].1 % 3)); j += 1; }
                    else { let v = (r[i].1 + f * p[j].1) % 3; if v != 0 { o.push((r[i].0, v)); } i += 1; j += 1; }
                }
                r = o;
            } else {
                let inv = if lc == 1 { 1 } else { 2 };
                piv.insert(lead, r.iter().map(|&(i, v)| (i, v * inv % 3)).collect());
                break;
            }
        }
    }
    piv.len()
}

/// Number of words and rank of d on the block (stem, s, c) of Lambda(m); d goes to (stem-1, s+1, c).
fn block_rank(m: i64, stem: i64, s: usize, c: usize) -> (usize, usize) {
    let src = words_m(m, stem, s, c);
    if src.is_empty() { return (0, 0); }
    let tgt = words_m(m, stem - 1, s + 1, c);
    let id: FxHashMap<&Word, u32> = tgt.iter().enumerate().map(|(i, w)| (w, i as u32)).collect();
    let rows = src.iter().map(|w| {
        d_word(w)
            .into_iter()
            .map(|(v, x)| (*id.get(&v).unwrap_or_else(|| panic!("d leaves reduced Lambda({}): {:?} -> {:?}", m, w, v)), x))
            .collect::<Vec<_>>()
    }).collect();
    (src.len(), rank(rows))
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let m: i64 = args[1].parse().unwrap();
    let kmax: i64 = args[2].parse().unwrap();
    if let Some(t) = args.get(3) {
        rayon::ThreadPoolBuilder::new().num_threads(t.parse().unwrap()).build_global().unwrap();
    }
    let mut blocks = vec![];
    for st in 1..=kmax + 1 {
        for s in 1..=(st / 3) as usize {
            for c in 0..s {
                blocks.push((st, s, c));
            }
        }
    }
    blocks.sort_by_key(|b| std::cmp::Reverse((b.0, b.1)));
    let res: Vec<((i64, usize, usize), usize, usize)> = blocks
        .par_iter()
        .map(|&(st, s, c)| {
            let (w, r) = block_rank(m, st, s, c);
            ((st, s, c), w, r)
        })
        .collect();
    let dim: FxHashMap<(i64, usize, usize), (usize, usize)> = res.into_iter().map(|(k, w, r)| (k, (w, r))).collect();
    let mut h: std::collections::BTreeMap<(i64, usize), usize> = Default::default();
    for (&(st, s, c), &(w, r)) in dim.iter() {
        if st > kmax || w == 0 { continue; }
        let rin = if s >= 2 { dim.get(&(st + 1, s - 1, c)).map(|x| x.1).unwrap_or(0) } else { 0 };
        let hh = w - r - rin;
        if hh > 0 { *h.entry((st, s)).or_insert(0) += hh; }
    }
    println!("m,k,s,dim");
    for ((st, s), d) in h { println!("{},{},{},{}", m, st, s, d); }
}
