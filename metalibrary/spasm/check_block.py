# -*- coding: utf-8 -*-
"""
Check one block certificate with the trusted checker cert/check.py (its check_block, unchanged),
and print "n,s,colour,rank" on success; any failure is an exception and a non-zero exit.

    python3 spasm/check_block.py CERTDIR/block_n_s_c.txt
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "cert"))
import check  # noqa: E402  -- metalibrary/cert/check.py

# check.py checks with assert: refuse to run with assertions off (python -O, PYTHONOPTIMIZE)
if not __debug__:
    sys.exit("check_block.py: assertions are disabled; run without -O / PYTHONOPTIMIZE")

(n, s, c), r = check.check_block(pathlib.Path(sys.argv[1]))
print(f"{n},{s},{c},{r}")
