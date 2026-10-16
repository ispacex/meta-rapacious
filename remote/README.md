Русская версия: [README.ru.md](README.ru.md).

# remote/ — long computations on a remote machine

The enumeration of the metalibrary, large resolutions and the Lean checks of the certificates take
hours. They can be sent as background jobs to any Linux box with systemd and ssh access (the
"runner"):

| File | What |
|---|---|
| `mr-remote.sh` | `submit`, `status`, `log`, `fetch`, `cancel` — the working tree as it is goes to the box and runs there as a systemd unit |
| `setup-box.sh` | one-time preparation of the box: `uv`; with `--rust` a Rust toolchain, with `--lean` elan, for the job user |
| `py-env.sh` | Python environment for a job (`source remote/py-env.sh`), a venv keyed by `requirements-py.txt` |

Configuration is by environment only; there is no default host:

```bash
export MR_REMOTE_HOST=root@runner.example.org   # ssh destination; must be able to run systemd-run
export MR_REMOTE_USER=jobs                      # unprivileged user the jobs run as
# optional: MR_REMOTE_ROOT (default /home/$MR_REMOTE_USER/mr-jobs), MR_REMOTE_SSH,
#           MR_REMOTE_UNIT (unit name prefix, default mr-)
```

A job runs at nice 15 with idle I/O priority; `--cpus` and `--mem` limit it further, which is
worth doing on a shared machine.

```bash
remote/setup-box.sh --rust --lean          # once: uv, Rust and elan for the job user

remote/mr-remote.sh submit --name colours84 --cpus 0-2 --mem 12G -- \
  'source remote/py-env.sh && cd metalibrary && python colour_solver.py data/sseq_S3_p3_150.csv 84 --out "$JOB_OUT"'
remote/mr-remote.sh status               # all jobs: RUNNING / DONE / FAILED (exit N) / LOST
remote/mr-remote.sh status ID            # one job and the tail of its log
remote/mr-remote.sh log ID 100
remote/mr-remote.sh fetch ID             # out/, log, meta, exit → remote-results/ID/
remote/mr-remote.sh cancel ID
```

- Every file git tracks travels, **with uncommitted edits**. A file outside the index does not:
  the script names such files before sending; `git add` them or pass `--untracked`.
- `meta` records the commit and whether the tree was dirty, so a result can always be matched
  with the code that computed it.
- On the box every job gets `$MR_REMOTE_ROOT/<ID>/`: `tree/` (the files, the job runs in them),
  `out/` (`$JOB_OUT`, what `fetch` brings back), `log` (stdout and stderr, starting with the CPUs
  the job actually runs on), `cmd.sh` and `meta`, and `exit` at the end. The job is a transient
  systemd unit `mr-<ID>`; `systemctl status mr-<ID>` on the box shows it as it is.
- A job sees `$JOB_OUT`, `$JOB_ROOT` and `$JOB_CACHE` (shared between jobs: `uv`, a venv per hash
  of `requirements-py.txt`, the Rust `target/`). `TMPDIR` is `$JOB_ROOT/tmp`.
- Python: `source remote/py-env.sh` (the venv is made by `uv`, so a system `python3` without
  `ensurepip` is enough; nothing is installed system-wide).
- Exit codes: `0` fine; `1` the job failed or (for `fetch`) has not finished yet; `2` nothing
  ran at all (no connection, bad arguments, submission failed). "The job failed" and "the job did
  not run" are different answers, and the script keeps them apart.
