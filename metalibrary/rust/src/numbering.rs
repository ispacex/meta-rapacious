//! Numbering of metalibrary words without storing them: a table of completion counts gives the
//! lexicographic number of any word of a cell and the word with a given number. Shared by
//! bin/lowmem.rs and bin/sms.rs.

use crate::algebra::*;

pub const START: usize = 0; // state before the first letter (only lambda_1, mu_1 may follow)

/// Completion counts: cnt[state][stem][len][col] = number of ways to continue a word whose last
/// letter is `state` by `len` letters of total degree `stem` containing `col` mu's, ending with a
/// lambda and admissible throughout. State 0 is the start; state x >= 2 is the letter code x.
pub struct Counts {
    ns: usize,
    st: usize,
    ln: usize,
    cl: usize,
    t: Vec<u64>,
}

impl Counts {
    pub fn new(stem: i64, len: usize, col: usize) -> Counts {
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
    pub fn get(&self, state: usize, s: usize, l: usize, k: usize) -> u64 {
        if state >= self.ns || s >= self.st || l >= self.ln || k >= self.cl { return 0; }
        self.t[self.at(state, s, l, k)]
    }
    /// The word with lexicographic number r among words of (stem, len, col).
    pub fn unrank(&self, stem: i64, len: usize, col: usize, mut r: u64) -> Word {
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
    pub fn rank(&self, w: &[u8], stem: i64, col: usize) -> Option<u64> {
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

/// Row number `i` of the block d: (stem, s, c) -> (stem-1, s+1, c): d of the i-th source word, as
/// (target number, coefficient) sorted by target number.
pub fn block_row(cs: &Counts, ct: &Counts, stem: i64, s: usize, c: usize, i: u64) -> Vec<(u32, u8)> {
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
}
