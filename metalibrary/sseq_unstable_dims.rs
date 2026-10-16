//! Resolves an unstable module through (n, s) and prints `n,s,num_gens` for every bidegree.

use ext::chain_complex::{ChainComplex, FreeChainComplex};
use sseq::coordinates::Bidegree;

fn main() -> anyhow::Result<()> {
    ext::utils::init_logging()?;

    let res = ext::utils::query_unstable_module(false)?;

    let max = Bidegree::n_s(
        query::raw("Max n", str::parse),
        query::raw("Max s", str::parse),
    );

    res.compute_through_stem(max);

    for b in res.iter_stem() {
        println!("{},{},{}", b.n(), b.s(), res.number_of_gens_in_bidegree(b));
    }
    Ok(())
}
