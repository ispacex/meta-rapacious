//! Homology of Mikhailov's coloured metalibrary: the same computation as
//! metalibrary/metalib.py (and lambda3.py), rewritten for speed. Conventions are those of
//! Ivanov-Mikhailov-Wu, arXiv:1506.00952, section 2, with p = 3; see lambda3.py.
//!
//!     metalib NMAX [THREADS]   > e2_metalib.csv
//!
//! Words: admissible, letters lambda_i, mu_i with i >= 1, first letter lambda_1 or mu_1,
//! last letter a lambda. The differential is the lambda-algebra one with words containing
//! mu_0 dropped (they span the subcomplex Lambda(1) mu_0); the result is checked to stay
//! inside the span of such words. Output lines: n,s,colour,words,rank_out,homology, where the
//! word lives over pi_n(S^3), n = stem + 3, and rank_out is the rank of d on the block.
//! Every block (n, s, colour) is independent: d goes to (n-1, s+1, colour).


mod algebra;

use algebra::*;
use rayon::prelude::*;
use rustc_hash::FxHashMap;


/// Rank over F_3 of the rows, consumed one at a time (rows are never all held in memory).
fn rank<I: IntoIterator<Item = Vec<(u32, u8)>>>(rows: I) -> usize {
    let mut piv: FxHashMap<u32, Vec<(u32, u8)>> = FxHashMap::default();
    for mut r in rows {
        r.sort_unstable_by_key(|t| t.0);
        loop {
            let Some(&(lead, lc)) = r.last() else { break };
            if let Some(p) = piv.get(&lead) {
                // r := r - lc * p   (p normalised, lead coefficient 1)
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
                let r2: Vec<(u32, u8)> = r.iter().map(|&(i, v)| (i, v * inv % 3)).collect();
                piv.insert(lead, r2);
                break;
            }
        }
    }
    piv.len()
}

/// Number of words and rank of d on the block (n, s, c); d goes to (n-1, s+1, c).
fn block_rank(n: i64, s: usize, c: usize) -> (usize, usize) {
    let src = words(n - 3, s, c);
    if src.is_empty() { return (0, 0); }
    let tgt = words(n - 4, s + 1, c);
    let id: FxHashMap<&Word, u32> = tgt.iter().enumerate().map(|(i, w)| (w, i as u32)).collect();
    let rows = src.iter().map(|w| {
        d_word(w)
            .into_iter()
            .map(|(v, c)| (*id.get(&v).unwrap_or_else(|| panic!("d leaves the metalibrary: {:?} -> {:?}", w, v)), c))
            .collect::<Vec<_>>()
    });
    (src.len(), rank(rows))
}

/// metalib --blocks FILE [THREADS]: ranks of the listed blocks (lines "n s c [words]"), printed as
/// "n,s,colour,words,rank" as soon as each block is done (so a stopped run keeps what it has).
fn blocks_mode(path: &str) {
    use std::io::Write;
    let text = std::fs::read_to_string(path).expect("cannot read the block list");
    let list: Vec<(i64, usize, usize)> = text
        .lines()
        .filter(|l| !l.trim().is_empty() && !l.starts_with('#'))
        .map(|l| {
            let f: Vec<&str> = l.split_whitespace().collect();
            (f[0].parse().unwrap(), f[1].parse().unwrap(), f[2].parse().unwrap())
        })
        .collect();
    let out = std::sync::Mutex::new(std::io::stdout());
    println!("n,s,colour,words,rank");
    list.par_iter().for_each(|&(n, s, c)| {
        let t = std::time::Instant::now();
        let (w, r) = block_rank(n, s, c);
        let mut o = out.lock().unwrap();
        writeln!(o, "{},{},{},{},{}", n, s, c, w, r).unwrap();
        o.flush().unwrap();
        eprintln!("block n={} s={} c={}: {} words, rank {}, {:.1}s", n, s, c, w, r, t.elapsed().as_secs_f64());
    });
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let threads = if args[1] == "--blocks" { args.get(3) } else { args.get(2) };
    if let Some(t) = threads {
        rayon::ThreadPoolBuilder::new().num_threads(t.parse().unwrap()).build_global().unwrap();
    }
    if args[1] == "--blocks" {
        return blocks_mode(&args[2]);
    }
    let nmax: i64 = args[1].parse().unwrap();
    // all blocks (n, s, c) with n <= nmax + 1
    let mut blocks = vec![];
    for n in 4..=nmax + 1 {
        let st = n - 3;
        for s in 1..=(st / 3) as usize {
            for c in 0..s {
                blocks.push((n, s, c));
            }
        }
    }
    // biggest first, for load balance
    blocks.sort_by_key(|b| std::cmp::Reverse((b.0, b.1)));
    let res: Vec<((i64, usize, usize), usize, usize)> = blocks
        .par_iter()
        .map(|&(n, s, c)| {
            let (w, r) = block_rank(n, s, c);
            if w > 0 { eprintln!("block n={} s={} c={}: {} words, rank {}", n, s, c, w, r); }
            ((n, s, c), w, r)
        })
        .collect();
    let mut dim: FxHashMap<(i64, usize, usize), (usize, usize)> = FxHashMap::default();
    for (k, w, r) in res { dim.insert(k, (w, r)); }
    println!("n,s,colour,words,rank_out,homology");
    let mut keys: Vec<_> = dim.keys().cloned().filter(|k| k.0 <= nmax).collect();
    keys.sort();
    for (n, s, c) in keys {
        let (w, r) = dim[&(n, s, c)];
        if w == 0 { continue; }
        let rin = if s >= 2 { dim.get(&(n + 1, s - 1, c)).map(|x| x.1).unwrap_or(0) } else { 0 };
        println!("{},{},{},{},{},{}", n, s, c, w, r, w - r - rin);
    }
}
