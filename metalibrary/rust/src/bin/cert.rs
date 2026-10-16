//! Certificates for the dimensions of metalibrary cells. This program is NOT trusted:
//! it only writes certificates; metalibrary/cert/check.py verifies them with its own lambda algebra.
//!
//!     cert BLOCKS CELLS OUTDIR [THREADS]
//!
//! BLOCKS: lines "n s c" -- for each, OUTDIR/block_n_s_c.txt certifies rank d >= r for the block
//!   d: (n,s,c) -> (n-1,s+1,c) by r lines "y t w:k w:k ...": a vector y = sum k w of source words
//!   and a target word t (its pivot), such that d(y) has t with a nonzero coefficient and none of
//!   the pivots of the lines after it. The matrix (coefficient of t_j in d y_i) is then triangular
//!   with a nonzero diagonal, so the d(y_i) are independent. No elimination is needed to check it.
//! CELLS: lines "n s c dim" -- for each cell with dim > 0, OUTDIR/cell_n_s_c.txt gives dim cycles z
//!   (d z = 0) and dim cocycles phi (phi vanishes on the image of d from (n+1,s-1,c)) whose pairing
//!   matrix phi_j(z_i) is invertible; that proves dim E^2(n,s,c) >= dim. Together with the ranks of
//!   the two blocks around the cell it fixes the dimension exactly.
//! Words are written as letters joined by '.', e.g. m1.l3.l2 = mu_1 lambda_3 lambda_2.

#[path = "../algebra.rs"]
mod algebra;

use algebra::*;
use rayon::prelude::*;
use rustc_hash::FxHashMap;
use std::io::Write;
use std::time::Instant;

type Vec3 = Vec<(u32, u8)>; // sparse vector over F_3, sorted by index

fn name(w: &[u8]) -> String {
    w.iter()
        .map(|&c| format!("{}{}", if is_mu(c) { 'm' } else { 'l' }, idx(c)))
        .collect::<Vec<_>>()
        .join(".")
}

/// a + f*b
fn axpy(a: &Vec3, f: u8, b: &Vec3) -> Vec3 {
    let mut o = Vec::with_capacity(a.len() + b.len());
    let (mut i, mut j) = (0, 0);
    while i < a.len() || j < b.len() {
        if j == b.len() || (i < a.len() && a[i].0 < b[j].0) {
            o.push(a[i]);
            i += 1;
        } else if i == a.len() || b[j].0 < a[i].0 {
            o.push((b[j].0, f * b[j].1 % 3));
            j += 1;
        } else {
            let v = (a[i].1 + f * b[j].1) % 3;
            if v != 0 { o.push((a[i].0, v)); }
            i += 1;
            j += 1;
        }
    }
    o
}

fn scale(a: &Vec3, f: u8) -> Vec3 { a.iter().map(|&(i, v)| (i, v * f % 3)).collect() }
fn inv(c: u8) -> u8 { if c == 1 { 1 } else { 2 } }

/// Rows of d from the words `src` into the words `tgt` (indices into tgt).
fn rows(src: &[Word], tgt: &[Word]) -> Vec<Vec3> {
    let id: FxHashMap<&Word, u32> = tgt.iter().enumerate().map(|(i, w)| (w, i as u32)).collect();
    src.par_iter()
        .map(|w| {
            let mut r: Vec3 = d_word(w)
                .into_iter()
                .map(|(v, c)| (*id.get(&v).unwrap_or_else(|| panic!("d leaves the block: {:?} -> {:?}", w, v)), c))
                .collect();
            r.sort_unstable_by_key(|t| t.0);
            r
        })
        .collect()
}

/// Echelon form: pivot (largest index) -> normalised row. Returns for each row whether it was
/// independent of the rows before it.
struct Echelon { piv: FxHashMap<u32, Vec3> }
impl Echelon {
    fn new() -> Self { Echelon { piv: FxHashMap::default() } }
    fn reduce(&self, mut r: Vec3) -> Vec3 {
        while let Some(&(lead, lc)) = r.last() {
            match self.piv.get(&lead) {
                Some(p) => r = axpy(&r, (3 - lc) % 3, p),
                None => break,
            }
        }
        r
    }
    /// Adds r if independent; returns its pivot.
    fn add(&mut self, r: Vec3) -> Option<u32> {
        let r = self.reduce(r);
        let &(lead, lc) = r.last()?;
        self.piv.insert(lead, scale(&r, inv(lc)));
        Some(lead)
    }
}

fn block(n: i64, s: usize, c: usize, out: &str) {
    let t = Instant::now();
    let src = words(n - 3, s, c);
    let tgt = words(n - 4, s + 1, c);
    let rs = rows(&src, &tgt);
    // elimination tracking every pivot row as a combination y of source words: d(y) has the
    // pivot as its largest target word, and pivots are distinct
    let mut piv: FxHashMap<u32, (Vec3, Vec3)> = FxHashMap::default();
    for (i, r0) in rs.into_iter().enumerate() {
        let mut r = r0;
        let mut y: Vec3 = vec![(i as u32, 1)];
        while let Some(&(lead, lc)) = r.last() {
            match piv.get(&lead) {
                Some((p, py)) => {
                    let k = (3 - lc) % 3;
                    r = axpy(&r, k, p);
                    y = axpy(&y, k, py);
                }
                None => {
                    let k = inv(lc);
                    piv.insert(lead, (scale(&r, k), scale(&y, k)));
                    break;
                }
            }
        }
    }
    let mut leads: Vec<u32> = piv.keys().cloned().collect();
    leads.sort_unstable();
    let mut f = std::io::BufWriter::new(std::fs::File::create(format!("{}/block_{}_{}_{}.txt", out, n, s, c)).unwrap());
    writeln!(f, "block {} {} {} words {} targets {} rank {}", n, s, c, src.len(), tgt.len(), leads.len()).unwrap();
    let mut ysum = 0;
    for t_ in &leads {
        let y = &piv[t_].1;
        ysum += y.len();
        let ys: Vec<String> = y.iter().map(|&(i, k)| format!("{}:{}", name(&src[i as usize]), k)).collect();
        writeln!(f, "y {} {}", name(&tgt[*t_ as usize]), ys.join(" ")).unwrap();
    }
    writeln!(f, "end").unwrap();
    eprintln!("block {} {} {}: {} x {}, rank {}, |y| {}, {:.1}s", n, s, c, src.len(), tgt.len(), leads.len(), ysum,
              t.elapsed().as_secs_f64());
}

/// Vectors over the domain X of f (f given by its rows, one per element of X) that span
/// ker f modulo the image of g (g given by its rows, vectors over X).
fn homology(f_rows: Vec<Vec3>, g_rows: Vec<Vec3>) -> Vec<Vec3> {
    let mut img = Echelon::new();
    for r in g_rows { img.add(r); }
    // elimination of f's rows, tracking each pivot row as a combination of elements of X
    let mut piv: FxHashMap<u32, (Vec3, Vec3)> = FxHashMap::default();
    let mut reps = vec![];
    for (x, r0) in f_rows.into_iter().enumerate() {
        let mut r = r0;
        let mut tr: Vec3 = vec![(x as u32, 1)];
        while let Some(&(lead, lc)) = r.last() {
            match piv.get(&lead) {
                Some((p, pt)) => {
                    let k = (3 - lc) % 3;
                    r = axpy(&r, k, p);
                    tr = axpy(&tr, k, pt);
                }
                None => break,
            }
        }
        match r.last() {
            Some(&(lead, lc)) => {
                let k = inv(lc);
                piv.insert(lead, (scale(&r, k), scale(&tr, k)));
            }
            None => {
                // tr is in ker f; keep it if it is new modulo the image of g and the cycles so far
                let z = img.reduce(tr);
                if let Some(&(lead, lc)) = z.last() {
                    let z = scale(&z, inv(lc));
                    img.piv.insert(lead, z.clone());
                    reps.push(z);
                }
            }
        }
    }
    reps
}

fn transpose(rows: &[Vec3], ncols: usize) -> Vec<Vec3> {
    let mut t: Vec<Vec3> = vec![vec![]; ncols];
    for (i, r) in rows.iter().enumerate() {
        for &(j, v) in r { t[j as usize].push((i as u32, v)); }
    }
    t
}

fn cell(n: i64, s: usize, c: usize, dim: usize, out: &str) {
    let t = Instant::now();
    let x = words(n - 3, s, c);
    let below = words(n - 4, s + 1, c); // d: x -> below
    let above = if s >= 2 { words(n - 2, s - 1, c) } else { vec![] }; // d: above -> x
    let f = rows(&x, &below);
    let g = rows(&above, &x);
    let ft = transpose(&f, below.len());
    let gt = transpose(&g, x.len());
    let z = homology(f, g);
    let phi = homology(gt, ft);
    assert_eq!(z.len(), dim, "cell {} {} {}: {} cycles, expected {}", n, s, c, z.len(), dim);
    assert_eq!(phi.len(), dim, "cell {} {} {}: {} cocycles, expected {}", n, s, c, phi.len(), dim);
    let mut o = std::io::BufWriter::new(std::fs::File::create(format!("{}/cell_{}_{}_{}.txt", out, n, s, c)).unwrap());
    writeln!(o, "cell {} {} {} words {} dim {}", n, s, c, x.len(), dim).unwrap();
    let pr = |v: &Vec3| v.iter().map(|&(i, k)| format!("{}:{}", name(&x[i as usize]), k)).collect::<Vec<_>>().join(" ");
    for v in &z { writeln!(o, "z {}", pr(v)).unwrap(); }
    for v in &phi { writeln!(o, "phi {}", pr(v)).unwrap(); }
    writeln!(o, "end").unwrap();
    eprintln!("cell {} {} {}: {} words, dim {}, |z| {:?}, |phi| {:?}, {:.1}s", n, s, c, x.len(), dim,
              z.iter().map(|v| v.len()).collect::<Vec<_>>(), phi.iter().map(|v| v.len()).collect::<Vec<_>>(),
              t.elapsed().as_secs_f64());
}

fn read(path: &str) -> Vec<Vec<i64>> {
    std::fs::read_to_string(path)
        .expect("cannot read the list")
        .lines()
        .filter(|l| !l.trim().is_empty() && !l.starts_with('#'))
        .map(|l| l.split_whitespace().map(|x| x.parse().unwrap()).collect())
        .collect()
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    if a.len() < 4 {
        eprintln!("usage: cert BLOCKS CELLS OUTDIR [THREADS]");
        std::process::exit(2);
    }
    if let Some(t) = a.get(4) {
        rayon::ThreadPoolBuilder::new().num_threads(t.parse().unwrap()).build_global().unwrap();
    }
    std::fs::create_dir_all(&a[3]).unwrap();
    let blocks = read(&a[1]);
    let cells: Vec<Vec<i64>> = read(&a[2]).into_iter().filter(|v| v[3] > 0).collect();
    blocks.iter().for_each(|b| block(b[0], b[1] as usize, b[2] as usize, &a[3]));
    cells.iter().for_each(|v| cell(v[0], v[1] as usize, v[2] as usize, v[3] as usize, &a[3]));
}
