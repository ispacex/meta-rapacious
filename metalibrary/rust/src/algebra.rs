//! The mod-3 lambda algebra for the metalibrary: letters, the relations of
//! Ivanov-Mikhailov-Wu (arXiv:1506.00952, section 2), normal forms, the differential, and the
//! enumeration of metalibrary words. Shared by main.rs (metalib) and bin/lowmem.rs.

use rustc_hash::FxHashMap;
use std::cell::RefCell;
use std::rc::Rc;

pub const P: i64 = 3;
pub type Word = Vec<u8>;
pub type Elem = Vec<(Word, u8)>;

pub fn is_mu(c: u8) -> bool { c & 1 == 1 }
pub fn idx(c: u8) -> i64 { (c >> 1) as i64 }
pub fn lam(i: i64) -> u8 { (2 * i) as u8 }
pub fn mu(i: i64) -> u8 { (2 * i + 1) as u8 }
pub fn deg(c: u8) -> i64 { 4 * idx(c) - if is_mu(c) { 0 } else { 1 } }
pub fn top(c: u8) -> i64 { P * idx(c) - if is_mu(c) { 0 } else { 1 } }
pub fn adm(a: u8, b: u8) -> bool { idx(b) <= top(a) }

pub fn binom3(n: i64, k: i64) -> i64 {
    if k < 0 || n < 0 || k > n { return 0; }
    // Lucas' theorem
    let (mut n, mut k, mut r) = (n, k, 1i64);
    while n > 0 || k > 0 {
        let (a, b) = (n % 3, k % 3);
        if b > a { return 0; }
        r = r * [1, 0, 0, 1, 1, 0, 1, 2, 1][(a * 3 + b) as usize] % 3; // C(a,b) mod 3, a,b < 3
        n /= 3;
        k /= 3;
    }
    r
}
pub fn md(x: i64) -> u8 { (((x % P) + P) % P) as u8 }
pub fn coef_a(k: i64, j: i64) -> u8 { md(if j % 2 == 0 { -1 } else { 1 } * binom3((P - 1) * (k - j) - 1, j)) }
pub fn coef_b(k: i64, j: i64) -> u8 { md(if j % 2 == 0 { 1 } else { -1 } * binom3((P - 1) * (k - j), j)) }
pub fn n_(k: i64) -> i64 { k - (k + 1 + P - 1) / P }
pub fn n1(k: i64) -> i64 { k - (k + P - 1) / P }

pub fn rewrite(a: u8, b: u8) -> Vec<(u8, u8, u8)> {
    let (i, m) = (idx(a), idx(b));
    let mut out = vec![];
    match (is_mu(a), is_mu(b)) {
        (false, false) => {
            let k = m - P * i;
            for j in 0..=n_(k) { out.push((coef_a(k, j), lam(i + k - j), lam(P * i + j))); }
        }
        (false, true) => {
            let k = m - P * i;
            for j in 0..=n_(k) { out.push((coef_a(k, j), lam(i + k - j), mu(P * i + j))); }
            for j in 0..=n1(k) { out.push((coef_b(k, j), mu(i + k - j), lam(P * i + j))); }
        }
        (true, false) => {
            let k = m - P * i - 1;
            for j in 0..=n_(k) { out.push((coef_a(k, j), mu(i + k - j), lam(P * i + j + 1))); }
        }
        (true, true) => {
            let k = m - P * i - 1;
            for j in 0..=n_(k) { out.push((coef_a(k, j), mu(i + k - j), mu(P * i + j + 1))); }
        }
    }
    out.retain(|t| t.0 != 0);
    out
}

pub fn d_letter(c: u8) -> Vec<(u8, u8, u8)> {
    let k = idx(c);
    let mut out = vec![];
    if !is_mu(c) {
        for j in 1..=n_(k) { out.push((coef_a(k, j), lam(k - j), lam(j))); }
    } else {
        for j in 0..=n_(k) { out.push((coef_a(k, j), lam(k - j), mu(j))); }
        for j in 1..=n1(k) { out.push((coef_b(k, j), mu(k - j), lam(j))); }
    }
    out.retain(|t| t.0 != 0);
    out
}

pub fn addto(acc: &mut FxHashMap<Word, u8>, w: Word, c: u8) {
    let e = acc.entry(w).or_insert(0);
    *e = (*e + c) % 3;
}

thread_local! {
    pub static MEMO: RefCell<FxHashMap<(Word, u8), Rc<Elem>>> = RefCell::new(FxHashMap::default());
    static REW: RefCell<FxHashMap<(u8, u8), Rc<Vec<(u8, u8, u8)>>>> = RefCell::new(FxHashMap::default());
}

pub fn rew(a: u8, b: u8) -> Rc<Vec<(u8, u8, u8)>> {
    REW.with(|m| m.borrow_mut().entry((a, b)).or_insert_with(|| Rc::new(rewrite(a, b))).clone())
}

/// Normal form of (admissible w) * x.
pub fn append(w: &[u8], x: u8) -> Rc<Elem> {
    if w.is_empty() || adm(*w.last().unwrap(), x) {
        let mut v = w.to_vec();
        v.push(x);
        return Rc::new(vec![(v, 1)]);
    }
    let key = (w.to_vec(), x);
    if let Some(r) = MEMO.with(|m| m.borrow().get(&key).cloned()) { return r; }
    let mut acc: FxHashMap<Word, u8> = FxHashMap::default();
    let last = *w.last().unwrap();
    for &(c, y, z) in rew(last, x).iter() {
        for (w2, c2) in append(&w[..w.len() - 1], y).iter() {
            for (w3, c3) in append(w2, z).iter() {
                addto(&mut acc, w3.clone(), c * c2 * c3 % 3);
            }
        }
    }
    let r: Rc<Elem> = Rc::new(acc.into_iter().filter(|t| t.1 != 0).collect());
    MEMO.with(|m| {
        let mut m = m.borrow_mut();
        if m.len() > 1_000_000 { m.clear(); }
        m.insert(key, r.clone());
    });
    r
}

/// d(w) for an admissible word, words containing mu_0 dropped.
pub fn d_word(w: &[u8]) -> Vec<(Word, u8)> {
    let mut acc: FxHashMap<Word, u8> = FxHashMap::default();
    let mut sign: i64 = 1;
    for pos in 0..w.len() {
        for (c, y, z) in d_letter(w[pos]) {
            let mut cur: FxHashMap<Word, u8> = FxHashMap::default();
            cur.insert(w[..pos].to_vec(), 1);
            let tail: Vec<u8> = [y, z].iter().cloned().chain(w[pos + 1..].iter().cloned()).collect();
            for x in tail {
                let mut nxt: FxHashMap<Word, u8> = FxHashMap::default();
                for (u, cu) in cur.iter() {
                    // mu_0 inside a product can disappear (mu_0 lambda_3 = -mu_2 lambda_1 + mu_1 lambda_2),
                    // so words are dropped only once the product is in normal form
                    for (u2, c2) in append(u, x).iter() {
                        addto(&mut nxt, u2.clone(), cu * c2 % 3);
                    }
                }
                cur = nxt;
            }
            for (u, cu) in cur {
                if cu != 0 && !u.contains(&mu(0)) {
                    addto(&mut acc, u, md(sign * (c as i64) * (cu as i64)));
                }
            }
        }
        if !is_mu(w[pos]) { sign = -sign; }
    }
    acc.into_iter().filter(|t| t.1 != 0).collect()
}

/// All metalibrary words with given stem, length and colour, in lexicographic order.
pub fn words(stem: i64, len: usize, col: usize) -> Vec<Word> {
    let mut out = vec![];
    fn rec(w: &mut Word, rem: i64, len: usize, col: usize, out: &mut Vec<Word>) {
        let used_mu = w.iter().filter(|c| is_mu(**c)).count();
        if w.len() == len {
            if rem == 0 && used_mu == col && !is_mu(*w.last().unwrap()) { out.push(w.clone()); }
            return;
        }
        let left = (len - w.len()) as i64;
        // every letter has degree >= 3; the last letter is a lambda, so at most left-1 more mu's
        if rem < 3 * left || used_mu > col || col - used_mu > len - w.len() - 1 { return; }
        let t = if w.is_empty() { 1 } else { top(*w.last().unwrap()) };
        for j in 1..=t {
            for x in [lam(j), mu(j)] {
                let dx = deg(x);
                if dx <= rem - 3 * (left - 1) {
                    w.push(x);
                    rec(w, rem - dx, len, col, out);
                    w.pop();
                }
            }
        }
    }
    rec(&mut vec![], stem, len, col, &mut out);
    out.sort();
    out
}
