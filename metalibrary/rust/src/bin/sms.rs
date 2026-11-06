//! A block of the differential as a sparse matrix over F_3 in SMS format (SpaSM, LinBox), for
//! benchmarking other elimination programs against `lowmem` (MATH-106):
//!
//!     sms N S C [THREADS] [--flip] > block.sms        # or: sms N S C | spasm/rank
//!
//! The block is d: (n,s,c) -> (n-1,s+1,c). Row i (1-based) is d of the (i-1)-th source word in the
//! lexicographic order of `lowmem`, column j is the (j-1)-th target word; entries are 1 or 2.
//! With --flip the columns are reversed (column j is target word T-j), so that the leftmost entry
//! of a row -- the pivot SpaSM's structural search prefers -- is lowmem's pivot, the largest word.
//! Rows are computed in parallel a chunk at a time, as in `lowmem`, and streamed in order, so the
//! matrix is never held in memory. stderr: the size, the number of nonzeros and the time.

#[path = "../algebra.rs"]
mod algebra;
#[path = "../numbering.rs"]
mod numbering;

use numbering::*;
use rayon::prelude::*;
use std::io::Write;
use std::time::Instant;

fn main() {
    let mut a: Vec<String> = std::env::args().collect();
    let flip = a.iter().any(|x| x == "--flip");
    a.retain(|x| x != "--flip");
    if a.len() < 4 {
        eprintln!("usage: sms N S C [THREADS] [--flip] > block.sms");
        std::process::exit(2);
    }
    let (n, s, c): (i64, usize, usize) = (a[1].parse().unwrap(), a[2].parse().unwrap(), a[3].parse().unwrap());
    if let Some(t) = a.get(4) {
        rayon::ThreadPoolBuilder::new().num_threads(t.parse().unwrap()).build_global().unwrap();
    }
    let t0 = Instant::now();
    let stem = n - 3;
    let cs = Counts::new(stem, s, c);
    let ct = Counts::new(stem - 1, s + 1, c);
    let nsrc = cs.get(START, stem as usize, s, c);
    let ntgt = ct.get(START, (stem - 1) as usize, s + 1, c);
    assert!(nsrc < i32::MAX as u64 && ntgt < i32::MAX as u64, "block too large for SMS (32-bit indices)");
    let mut out = std::io::BufWriter::with_capacity(1 << 22, std::io::stdout().lock());
    writeln!(out, "{} {} M", nsrc, ntgt).unwrap();
    const CHUNK: u64 = 1 << 16;
    let (mut start, mut nnz) = (0u64, 0u64);
    while start < nsrc {
        let end = (start + CHUNK).min(nsrc);
        let text: Vec<(usize, Vec<u8>)> = (start..end)
            .into_par_iter()
            .map(|i| {
                let row = block_row(&cs, &ct, stem, s, c, i);
                let mut b = Vec::with_capacity(row.len() * 16);
                for (j, v) in &row {
                    let col = if flip { ntgt - *j as u64 } else { *j as u64 + 1 };
                    writeln!(b, "{} {} {}", i + 1, col, v).unwrap();
                }
                (row.len(), b)
            })
            .collect();
        for (k, b) in text {
            nnz += k as u64;
            out.write_all(&b).unwrap();
        }
        start = end;
    }
    writeln!(out, "0 0 0").unwrap();
    out.flush().unwrap();
    eprintln!("sms n={} s={} c={}: {} x {}, {} nonzeros, {:.1}s", n, s, c, nsrc, ntgt, nnz, t0.elapsed().as_secs_f64());
}
