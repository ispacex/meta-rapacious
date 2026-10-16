//! Experiment: how much of the rank of a block do triangular minors made of single
//! words give? A set of words whose d's have pairwise different leading terms (in some order of
//! the target words) is independent with a triangular minor -- a certificate that needs no
//! elimination to check. Prints, per block: rank, and the number of distinct leading terms for
//! the lexicographic order, its reverse, and a greedy acyclic matching.
//!
//!     leads BLOCKS

#[path = "../algebra.rs"]
mod algebra;

use algebra::*;
use rustc_hash::{FxHashMap, FxHashSet};

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let text = std::fs::read_to_string(&a[1]).unwrap();
    let (mut tr, mut tl, mut th, mut tg, mut tys) = (0, 0, 0, 0, 0);
    for l in text.lines().filter(|l| !l.trim().is_empty() && !l.starts_with('#')) {
        let f: Vec<i64> = l.split_whitespace().map(|x| x.parse().unwrap()).collect();
        let (n, s, c) = (f[0], f[1] as usize, f[2] as usize);
        let src = words(n - 3, s, c);
        let tgt = words(n - 4, s + 1, c);
        if src.is_empty() || tgt.is_empty() { continue; }
        let id: FxHashMap<&Word, u32> = tgt.iter().enumerate().map(|(i, w)| (w, i as u32)).collect();
        let rows: Vec<Vec<u32>> = src.iter().map(|w| {
            let mut r: Vec<u32> = d_word(w).into_iter().map(|(v, _)| id[&v]).collect();
            r.sort_unstable();
            r
        }).collect();
        // rank, tracking each pivot row as a combination y of source words; |y| summed
        fn axpy(a: &[(u32, u8)], f: u8, b: &[(u32, u8)]) -> Vec<(u32, u8)> {
            let mut m: std::collections::BTreeMap<u32, u8> = a.iter().cloned().collect();
            for &(j, v) in b { let e = m.entry(j).or_insert(0); *e = (*e + f * v) % 3; }
            m.into_iter().filter(|t| t.1 != 0).collect()
        }
        let mut piv: FxHashMap<u32, (Vec<(u32, u8)>, Vec<(u32, u8)>)> = FxHashMap::default();
        let mut ysum = 0usize;
        let mut ymax = 0usize;
        for (wi, w) in src.iter().enumerate() {
            let mut r: Vec<(u32, u8)> = d_word(w).into_iter().map(|(v, k)| (id[&v], k)).collect();
            r.sort_unstable_by_key(|t| t.0);
            let mut y: Vec<(u32, u8)> = vec![(wi as u32, 1)];
            loop {
                let Some(&(lead, lc)) = r.last() else { break };
                if let Some((p, py)) = piv.get(&lead) {
                    let f = (3 - lc) % 3;
                    r = axpy(&r, f, p);
                    y = axpy(&y, f, py);
                } else {
                    let inv = if lc == 1 { 1 } else { 2 };
                    ysum += y.len();
                    ymax = ymax.max(y.len());
                    piv.insert(lead, (r.iter().map(|&(j, v)| (j, v * inv % 3)).collect(), y.iter().map(|&(j, v)| (j, v * inv % 3)).collect()));
                    break;
                }
            }
        }
        let rank = piv.len();
        let hi: FxHashSet<u32> = rows.iter().filter_map(|r| r.last().cloned()).collect();
        let lo: FxHashSet<u32> = rows.iter().filter_map(|r| r.first().cloned()).collect();
        // greedy acyclic matching: repeatedly take a column hit by exactly one remaining row,
        // match them and drop that row; dropped rows' other columns stay usable (they are
        // "below" the matched pair in the order), so the result is triangular.
        let mut colrows: Vec<Vec<u32>> = vec![vec![]; tgt.len()];
        for (i, r) in rows.iter().enumerate() { for &j in r { colrows[j as usize].push(i as u32); } }
        let mut alive = vec![true; rows.len()];
        let mut deg: Vec<usize> = colrows.iter().map(|v| v.len()).collect();
        let mut used = vec![false; tgt.len()];
        let mut stack: Vec<u32> = (0..tgt.len() as u32).filter(|&j| deg[j as usize] == 1).collect();
        let mut g = 0;
        while let Some(j) = stack.pop() {
            if used[j as usize] || deg[j as usize] != 1 { continue; }
            let i = *colrows[j as usize].iter().find(|&&i| alive[i as usize]).unwrap();
            alive[i as usize] = false;
            used[j as usize] = true;
            g += 1;
            for &k in &rows[i as usize] {
                deg[k as usize] -= 1;
                if deg[k as usize] == 1 && !used[k as usize] { stack.push(k); }
            }
        }
        println!("{} {} {}: {} x {}, rank {}, leads hi {} lo {}, greedy {}, |y| sum {} max {}", n, s, c, src.len(), tgt.len(), rank, hi.len(), lo.len(), g, ysum, ymax);
        tys += ysum;
        tr += rank; th += hi.len(); tl += lo.len(); tg += g;
    }
    println!("total: rank {}, leads hi {}, lo {}, greedy {}, |y| sum {}", tr, th, tl, tg, tys);
}
