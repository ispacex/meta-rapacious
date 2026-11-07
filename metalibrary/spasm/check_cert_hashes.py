# -*- coding: utf-8 -*-
"""
Consistency check of data/cert_hashes_part1.csv and data/cert_uncertified_part1.txt (MATH-106):

- every block of data/open_blocks_part1.txt is in exactly one of the two files;
- the word count of each certified block is the one in open_blocks_part1.txt;
- the rank check.py accepted equals the rank in data/ranks_part1.csv;
- every sha256 is 64 hex digits, every status is "ok".

This checks the bookkeeping, not the certificates: those are rebuilt by certlow and checked by
cert/check.py (spasm/cert_hashes.sh), and the sha256 says which file was checked.

    cd metalibrary && python3 spasm/check_cert_hashes.py
"""
import csv
import pathlib
import re
import sys

data = pathlib.Path(__file__).resolve().parent.parent / "data"


def key(n, s, c):
    return (int(n), int(s), int(c))


part1 = {}
for line in open(data / "open_blocks_part1.txt"):
    if line.strip() and not line.startswith("#"):
        n, s, c, w = line.split()
        part1[key(n, s, c)] = int(w)
ranks = {key(r["n"], r["s"], r["colour"]): (int(r["words"]), int(r["rank"]))
         for r in csv.DictReader(open(data / "ranks_part1.csv"))}

errors = []
certified = {}
for r in csv.DictReader(open(data / "cert_hashes_part1.csv")):
    b = key(r["n"], r["s"], r["colour"])
    if b in certified:
        errors.append(f"{b}: listed twice")
    certified[b] = r
    if b not in part1:
        errors.append(f"{b}: not a block of open_blocks_part1.txt")
        continue
    if int(r["words"]) != part1[b]:
        errors.append(f"{b}: {r['words']} words, open_blocks_part1.txt says {part1[b]}")
    if (int(r["words"]), int(r["rank"])) != ranks.get(b):
        errors.append(f"{b}: rank {r['rank']}, ranks_part1.csv says {ranks.get(b)}")
    if not re.fullmatch(r"[0-9a-f]{64}", r["sha256"]):
        errors.append(f"{b}: bad sha256 {r['sha256']!r}")
    if r["check"] != "ok":
        errors.append(f"{b}: status {r['check']!r}")

uncertified = {}
for line in open(data / "cert_uncertified_part1.txt"):
    if line.strip() and not line.startswith("#"):
        n, s, c, w, why = line.split()[:5]
        b = key(n, s, c)
        if b in uncertified or b in certified:
            errors.append(f"{b}: listed twice")
        uncertified[b] = why
        if part1.get(b) != int(w):
            errors.append(f"{b}: {w} words, open_blocks_part1.txt says {part1.get(b)}")

missing = set(part1) - set(certified) - set(uncertified)
errors += [f"{b}: in neither file" for b in sorted(missing)]
print(f"{len(certified)} certified, {len(uncertified)} uncertified, of {len(part1)} part1 blocks; "
      f"{len(errors)} errors")
for e in errors:
    print(" ", e)
sys.exit(1 if errors else 0)
