# -*- coding: utf-8 -*-
"""
Compare two rank files ("n,s,colour,words,rank"): every block present in both must agree.

    python3 compare_ranks.py REFERENCE.csv NEW.csv [MAXWORDS] [--list OUT]

With --list, writes the blocks of REFERENCE with at most MAXWORDS words as a block list
("n s c words") instead of comparing; that list is what the new program is run on.
"""
import csv
import sys


def load(fn):
    return {(r["n"], r["s"], r["colour"]): (int(r["words"]), int(r["rank"])) for r in csv.DictReader(open(fn))}


def main():
    ref = load(sys.argv[1])
    if "--list" in sys.argv:
        maxw = float(sys.argv[2])
        out = sys.argv[sys.argv.index("--list") + 1]
        rows = sorted((w, k) for k, (w, _) in ref.items() if w <= maxw)
        open(out, "w").write("".join(f"{k[0]} {k[1]} {k[2]} {w}\n" for w, k in rows))
        print(f"{len(rows)} blocks, {sum(w for w, _ in rows)} words -> {out}")
        return
    new = load(sys.argv[2])
    both = sorted(set(ref) & set(new), key=lambda k: ref[k][0])
    bad = [(k, ref[k], new[k]) for k in both if ref[k] != new[k]]
    print(f"{len(both)} blocks in both, largest {max(ref[k][0] for k in both)} words: "
          + ("all words and ranks agree" if not bad else f"{len(bad)} DIFFER, e.g. {bad[:5]}"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
