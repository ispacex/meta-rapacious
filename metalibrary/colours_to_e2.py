# -*- coding: utf-8 -*-
"""
E^2 by (n, s, colour) in the format of rapacious.py from the colour solver's output.

    python3 colours_to_e2.py data/e2_colours.csv > data/e2_full.csv

Only n below the first n with an undetermined cell is written, so the file is complete
up to its last n. Columns: n,s,colour,words,rank_out,homology (words and rank_out empty).
"""
import csv
import sys


def main():
    rows = list(csv.DictReader(open(sys.argv[1])))
    first_open = min((int(r["n"]) for r in rows if r["status"] != "determined"), default=10 ** 9)
    w = csv.writer(sys.stdout, lineterminator="\n")
    w.writerow(["n", "s", "colour", "words", "rank_out", "homology"])
    for r in rows:
        if int(r["n"]) < first_open and r["status"] == "determined" and int(r["dim"]) > 0:
            w.writerow([r["n"], r["s"], r["colour"], "", "", r["dim"]])
    print(f"complete up to n = {first_open - 1}", file=sys.stderr)


if __name__ == "__main__":
    main()
