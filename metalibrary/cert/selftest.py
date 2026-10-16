# -*- coding: utf-8 -*-
"""
The checker must reject broken certificates:

    python3 cert/selftest.py CELLS CERTDIR N [N ...]

On a copy of a good certificate: change a cycle coefficient, swap two pivots of a rank certificate, claim a wrong
dimension, drop a cell from the claim. Each must make check.py fail; the original must pass.
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent


def run(cells, certdir, cols):
    r = subprocess.run([sys.executable, str(HERE / "check.py"), str(cells), str(certdir)] + cols,
                       capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-1]


def main():
    cells, certdir, cols = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3:]
    ok, last = run(cells, certdir, cols)
    print("original:", "passes" if ok else "FAILS", "|", last)
    assert ok
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        cases = []

        def case(name, edit_cert=None, edit_cells=None):
            d = tmp / name
            shutil.copytree(certdir, d)
            c = tmp / (name + ".cells")
            c.write_text(cells.read_text())
            if edit_cert:
                edit_cert(d)
            if edit_cells:
                edit_cells(c)
            cases.append((name, c, d))

        def bump_z(d):
            # a cycle with several words (a one-word cycle times 2 is still a cycle)
            f, i = next((f, k) for f in sorted(d.glob("cell_*.txt"))
                        for k, l in enumerate(f.read_text().splitlines()) if l.startswith("z ") and len(l.split()) > 2)
            lines = f.read_text().splitlines()
            t = lines[i].split()
            w, k = t[1].split(":")
            t[1] = f"{w}:{3 - int(k)}"
            lines[i] = " ".join(t)
            f.write_text("\n".join(lines) + "\n")

        def swap_pivots(d):
            # two lines of the rank certificate exchange their pivots: no longer triangular
            f = max(d.glob("block_*.txt"), key=lambda p: p.stat().st_size)
            lines = f.read_text().splitlines()
            i, j = [k for k, l in enumerate(lines) if l.startswith("y ")][:2]
            a, b = lines[i].split(), lines[j].split()
            a[1], b[1] = b[1], a[1]
            lines[i], lines[j] = " ".join(a), " ".join(b)
            f.write_text("\n".join(lines) + "\n")

        def wrong_dim(c):
            lines = c.read_text().splitlines()
            i = next(k for k, l in enumerate(lines) if l and not l.startswith("#") and l.split()[3] != "0")
            t = lines[i].split()
            t[3] = str(int(t[3]) + 1)
            lines[i] = " ".join(t)
            c.write_text("\n".join(lines) + "\n")

        def drop_cell(c):
            lines = c.read_text().splitlines()
            i = next(k for k, l in enumerate(lines) if l and not l.startswith("#") and l.split()[3] == "0")
            del lines[i]
            c.write_text("\n".join(lines) + "\n")

        case("cycle coefficient changed", edit_cert=bump_z)
        case("two pivots swapped", edit_cert=swap_pivots)
        case("dimension claimed one too big", edit_cells=wrong_dim)
        case("a zero cell left out of the claim", edit_cells=drop_cell)
        bad = 0
        for name, c, d in cases:
            ok, last = run(c, d, cols)
            print(f"{name}: {'ACCEPTED (bad!)' if ok else 'rejected'} | {last}")
            bad += ok
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
