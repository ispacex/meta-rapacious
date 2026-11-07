# -*- coding: utf-8 -*-
"""
Consistency check of data/cert_hashes_part1.csv and data/cert_uncertified_part1.txt (MATH-106):

- every block of data/open_blocks_part1.txt is in exactly one of the two files;
- the word count of each block is the one in open_blocks_part1.txt;
- the rank check.py accepted equals the rank in data/ranks_part1.csv;
- every sha256 is 64 lowercase hex digits and no two blocks share one; bytes is a positive integer;
  every status is "ok"; every uncertified block has a known reason;
- no block is listed twice in any of the four files.

This checks the bookkeeping, not the certificates: those are rebuilt by certlow and checked by
cert/check.py (spasm/cert_hashes.sh), and the sha256 says which file was checked.

    cd metalibrary && python3 spasm/check_cert_hashes.py            # the data
    cd metalibrary && python3 spasm/check_cert_hashes.py --selftest # negative controls
"""
import csv
import pathlib
import re
import shutil
import sys
import tempfile

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
FILES = ("open_blocks_part1.txt", "ranks_part1.csv", "cert_hashes_part1.csv",
         "cert_uncertified_part1.txt")
REASONS = {"memory"}


def key(n, s, c):
    return (int(n), int(s), int(c))


def lines(path):
    for i, line in enumerate(open(path), 1):
        if line.strip() and not line.startswith("#"):
            yield i, line.split()


def check(data):
    errors = []

    def put(d, b, v, where):
        if b in d:
            errors.append(f"{where}: {b} listed twice")
        d[b] = v

    part1, ranks, certified, uncertified, hashes = {}, {}, {}, {}, {}
    for i, f in lines(data / "open_blocks_part1.txt"):
        if len(f) != 4:
            errors.append(f"open_blocks_part1.txt:{i}: malformed line")
            continue
        put(part1, key(*f[:3]), int(f[3]), "open_blocks_part1.txt")
    for r in csv.DictReader(open(data / "ranks_part1.csv")):
        put(ranks, key(r["n"], r["s"], r["colour"]), (int(r["words"]), int(r["rank"])),
            "ranks_part1.csv")

    for r in csv.DictReader(open(data / "cert_hashes_part1.csv")):
        b = key(r["n"], r["s"], r["colour"])
        put(certified, b, r, "cert_hashes_part1.csv")
        if b not in part1:
            errors.append(f"{b}: not a block of open_blocks_part1.txt")
            continue
        if int(r["words"]) != part1[b]:
            errors.append(f"{b}: {r['words']} words, open_blocks_part1.txt says {part1[b]}")
        if (int(r["words"]), int(r["rank"])) != ranks.get(b):
            errors.append(f"{b}: rank {r['rank']}, ranks_part1.csv says {ranks.get(b)}")
        if not re.fullmatch(r"[0-9a-f]{64}", r["sha256"]):
            errors.append(f"{b}: bad sha256 {r['sha256']!r}")
        elif r["sha256"] in hashes:
            errors.append(f"{b}: same sha256 as {hashes[r['sha256']]}")
        hashes[r["sha256"]] = b
        if not re.fullmatch(r"[1-9][0-9]*", r["bytes"]):
            errors.append(f"{b}: bad bytes {r['bytes']!r}")
        if r["check"] != "ok":
            errors.append(f"{b}: status {r['check']!r}")

    for i, f in lines(data / "cert_uncertified_part1.txt"):
        if len(f) != 5:
            errors.append(f"cert_uncertified_part1.txt:{i}: malformed line")
            continue
        b = key(*f[:3])
        put(uncertified, b, f[4], "cert_uncertified_part1.txt")
        if b in certified:
            errors.append(f"{b}: both certified and uncertified")
        if part1.get(b) != int(f[3]):
            errors.append(f"{b}: {f[3]} words, open_blocks_part1.txt says {part1.get(b)}")
        if f[4] not in REASONS:
            errors.append(f"{b}: unknown reason {f[4]!r}")

    errors += [f"{b}: in neither file" for b in sorted(set(part1) - set(certified) - set(uncertified))]
    return len(certified), len(uncertified), len(part1), errors


def selftest():
    """Each mutation of a copy of the data must be reported; the unmodified copy must pass."""
    def edit(name, fn):
        def run(d):
            p = d / name
            p.write_text(fn(p.read_text().splitlines(keepends=True)))
        return run

    def cert_row(fn):  # change one field of the first data row of the CSV
        def g(ls):
            f = ls[1].rstrip("\n").split(",")
            fn(f)
            return "".join([ls[0], ",".join(f) + "\n"] + ls[2:])
        return edit("cert_hashes_part1.csv", g)

    def same_sha(ls):  # give the second row the first row's sha256
        f1, f2 = ls[1].rstrip("\n").split(","), ls[2].rstrip("\n").split(",")
        f2[6] = f1[6]
        return "".join(ls[:2] + [",".join(f2) + "\n"] + ls[3:])

    first_cert = (DATA / "cert_hashes_part1.csv").read_text().splitlines()[1].split(",")
    data_lines = lambda ls: [l for l in ls if l.strip() and not l.startswith("#")]
    cases = {
        "rank changed": cert_row(lambda f: f.__setitem__(4, str(int(f[4]) + 1))),
        "words changed": cert_row(lambda f: f.__setitem__(3, str(int(f[3]) + 1))),
        "sha256 bad char": cert_row(lambda f: f.__setitem__(6, "g" + f[6][1:])),
        "sha256 short": cert_row(lambda f: f.__setitem__(6, f[6][:-1])),
        "sha256 upper": cert_row(lambda f: f.__setitem__(6, f[6].upper())),
        "bytes negative": cert_row(lambda f: f.__setitem__(5, "-" + f[5])),
        "status": cert_row(lambda f: f.__setitem__(7, "fail")),
        "block dropped": edit("cert_hashes_part1.csv", lambda ls: "".join(ls[:1] + ls[2:])),
        "block twice": edit("cert_hashes_part1.csv", lambda ls: "".join(ls + ls[1:2])),
        "same sha256": edit("cert_hashes_part1.csv", same_sha),
        "both files": edit("cert_uncertified_part1.txt", lambda ls: "".join(
            ls + [" ".join(first_cert[:4]) + " memory\n"])),
        "uncertified emptied": edit("cert_uncertified_part1.txt",
                                    lambda ls: "".join(l for l in ls if l.startswith("#"))),
        "uncertified twice": edit("cert_uncertified_part1.txt",
                                  lambda ls: "".join(ls + data_lines(ls))),
        "uncertified words": edit("cert_uncertified_part1.txt", lambda ls: "".join(
            re.sub(r"^(\d+ \d+ \d+ )(\d+)", lambda m: m[1] + str(int(m[2]) + 1), l) for l in ls)),
        "uncertified reason": edit("cert_uncertified_part1.txt", lambda ls: "".join(
            l if l.startswith("#") else l.replace("memory", "banana") for l in ls)),
        "uncertified short line": edit("cert_uncertified_part1.txt", lambda ls: "".join(ls + ["1 2 3\n"])),
        "ranks row twice": edit("ranks_part1.csv", lambda ls: "".join(ls + ls[1:2])),
        "ranks changed": edit("ranks_part1.csv", lambda ls: "".join(
            [l if i == 0 else re.sub(r"(\d+)$", lambda m: str(int(m[1]) + 1), l.rstrip("\n")) + "\n"
             for i, l in enumerate(ls)])),
        "open_blocks line twice": edit("open_blocks_part1.txt", lambda ls: "".join(ls + data_lines(ls)[:1])),
        "open_blocks extra block": edit("open_blocks_part1.txt", lambda ls: "".join(ls + ["99 9 9 9\n"])),
    }
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        for name, mutate in [("unmodified", None)] + list(cases.items()):
            d = pathlib.Path(tmp) / re.sub(r"\W", "_", name)
            d.mkdir()
            for f in FILES:
                shutil.copy(DATA / f, d / f)
            if mutate:
                mutate(d)
            try:
                errs = check(d)[3]
            except Exception as e:  # a crash is not a report
                errs = None
                print(f"  {name}: crashed: {e!r}")
            ok = errs == [] if mutate is None else bool(errs)
            bad += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name}: {'passes' if errs == [] else 'reported'}")
    print(f"selftest: {len(cases) + 1 - bad} of {len(cases) + 1} as expected")
    return bad == 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if selftest() else 1)
    nc, nu, np1, errors = check(DATA)
    print(f"{nc} certified, {nu} uncertified, of {np1} part1 blocks; {len(errors)} errors")
    for e in errors:
        print(" ", e)
    sys.exit(1 if errors else 0)
