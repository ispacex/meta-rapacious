#!/usr/bin/env bash
# Long computations of this repository on a remote Linux box, as background jobs.
#
# What runs is *this working tree as it is now*, not a pushed branch. The jobs take hours, so
# instead of one call that waits for a verdict there are five commands:
#
#   remote/mr-remote.sh submit [--name N] [--untracked] [--cpus 0-3] [--mem 8G] [--progress 'out/*.json:858'] -- COMMAND...
#   remote/mr-remote.sh status [ID]          # all jobs, or one
#   remote/mr-remote.sh log ID [LINES]       # tail of the job's log
#   remote/mr-remote.sh fetch ID [DEST]      # copy $JOB_OUT, log and metadata back
#   remote/mr-remote.sh cancel ID
#
# What travels: every file git tracks, with its uncommitted edits (git ls-files, submodules
# included), packed with tar. A file outside the index does not travel; the script names such
# files before sending, and --untracked sends them too. The job records the commit and whether
# the tree was dirty. Run it from the top of the repository whose files should travel.
#
# On the box every job gets $MR_REMOTE_ROOT/<ID>/ with tree/ (the files), out/ ($JOB_OUT),
# log, cmd.sh, meta, exit. It runs as an unprivileged user inside a transient systemd unit
# mr-<ID> (see MR_REMOTE_UNIT), optionally limited to the given CPUs and memory, at nice 15 and idle I/O priority,
# so that a shared box stays usable. Jobs see JOB_OUT, JOB_ROOT and JOB_CACHE (shared between
# jobs: uv, venvs, the Rust target directory). TMPDIR is $JOB_ROOT/tmp.
#
# Progress: either --progress GLOB[:TOTAL] -- the number of files matching GLOB in the job
# directory, out of TOTAL -- or the job itself writes "DONE/TOTAL" into $JOB_ROOT/progress as it
# goes; both end up in the job directory for whatever monitor reads it.
#
# Configuration (environment). The ssh login must be able to run systemd-run (root, as a rule).
#   MR_REMOTE_HOST  ssh destination, e.g. root@runner.example.org   (required, no default)
#   MR_REMOTE_USER  unprivileged user the jobs run as                (required, no default)
#   MR_REMOTE_ROOT  job directory on the box     (default /home/$MR_REMOTE_USER/mr-jobs)
#   MR_REMOTE_SSH   ssh command                  (default: ssh -o BatchMode=yes ...)
#   MR_REMOTE_UNIT  prefix of the systemd unit names (default mr-)
#
# Exit codes: 0 fine; 1 the job failed (or is not finished, for fetch);
# 2 nothing ran (no connection, bad arguments, submission failed).
set -u
not_run() { echo "NOT RUN: $*"; exit 2; }
[ -n "${MR_REMOTE_HOST:-}" ] || { [ $# -eq 0 ] || not_run "set MR_REMOTE_HOST (ssh destination of the runner)"; }
[ -n "${MR_REMOTE_USER:-}" ] || { [ $# -eq 0 ] || not_run "set MR_REMOTE_USER (the user jobs run as)"; }
HOST=${MR_REMOTE_HOST:-}
SSH=${MR_REMOTE_SSH:-ssh -o BatchMode=yes -o ConnectTimeout=20 -o LogLevel=ERROR}
RUSER=${MR_REMOTE_USER:-}
ROOT=${MR_REMOTE_ROOT:-/home/$RUSER/mr-jobs}
UNIT=${MR_REMOTE_UNIT:-mr-}
[[ "$UNIT" =~ ^[A-Za-z0-9_-]*$ ]] || not_run "MR_REMOTE_UNIT may contain letters, digits, - and _ only"

rsh() { $SSH "$HOST" "$@"; }
valid_id() { [[ "$1" =~ ^[A-Za-z0-9._-]+$ ]] || not_run "bad job id '$1'"; }

cmd_submit() {
  local name=job untracked=0 cpus="" mem="" progress=""
  while [ $# -gt 0 ]; do
    case $1 in
      --name) name=$2; shift 2 ;;
      --untracked) untracked=1; shift ;;
      --cpus) cpus=$2; shift 2 ;;
      --mem) mem=$2; shift 2 ;;
      --progress) progress=$2; shift 2 ;;
      --) shift; break ;;
      *) not_run "unknown option $1 (the command goes after --)" ;;
    esac
  done
  [ $# -gt 0 ] || not_run "no command after --"
  [[ "$name" =~ ^[A-Za-z0-9_-]+$ ]] || not_run "--name may contain letters, digits, - and _ only"
  local pglob="" ptotal=""
  if [ -n "$progress" ]; then
    pglob=${progress%%:*}; [ "$pglob" != "$progress" ] && ptotal=${progress##*:}
    [[ "$pglob" =~ ^[A-Za-z0-9._*?/-]+$ && "$pglob" != /* && "$pglob" != *..* ]] || not_run "--progress: a glob relative to the job directory, e.g. 'out/*.json:858'"
    [[ -z "$ptotal" || "$ptotal" =~ ^[0-9]+$ ]] || not_run "--progress: the total after ':' must be a number"
  fi
  local top; top=$(git rev-parse --show-toplevel 2>/dev/null) || not_run "not in a git repository"
  cd "$top" || not_run "cannot cd to $top"
  local sha dirty id
  sha=$(git rev-parse --short HEAD)
  dirty=$([ -n "$(git status --porcelain --untracked-files=no)" ] && echo dirty || echo clean)
  id="$(date +%Y%m%d-%H%M%S)-$name-$sha"
  local others; others=$(git ls-files --others --exclude-standard)
  if [ -n "$others" ] && [ $untracked = 0 ]; then
    echo "$(echo "$others" | wc -l | tr -d ' ') file(s) outside the index — NOT sent (git add them, or pass --untracked):"
    echo "$others" | sed 's/^/  /'
  fi
  local list; list=$(mktemp)
  git ls-files -z --recurse-submodules > "$list"
  [ $untracked = 1 ] && git ls-files -z --others --exclude-standard >> "$list"
  local cmd_b64; cmd_b64=$(printf '%s ' "$@" | base64 | tr -d '\n')
  echo "submitting $id: $* (cpus ${cpus:-all}, mem ${mem:-unlimited}, $sha $dirty)"
  # shellcheck disable=SC2016
  tar --null -czf - -T "$list" | rsh "set -e
    J=$ROOT/$id; mkdir -p \$J/tree \$J/out $ROOT/cache
    tar -xzf - -C \$J/tree
    echo '$cmd_b64' | base64 -d > \$J/cmd.sh
    printf 'id=%s\nsha=%s\ntree=%s\nsubmitted=%s\ncpus=%s\nmem=%s\nprogress_glob=%s\nprogress_total=%s\ncmd=%s\n' '$id' '$sha' '$dirty' \"\$(date -Is)\" '$cpus' '$mem' '$pglob' '$ptotal' \"\$(cat \$J/cmd.sh)\" > \$J/meta
    cat > \$J/run.sh <<'RUN'
cd \"\$JOB_ROOT/tree\"
# temp files on the job's disk, not in /tmp: on the box /tmp is a small tmpfs with a per-user quota,
# and a large job can write gigabytes of temporary files; they go with the job
export TMPDIR=\"\$JOB_ROOT/tmp\"; mkdir -p \"\$TMPDIR\"
echo \"started \$(date -Is) on \$(hostname), cpus \$(cat /sys/fs/cgroup\$(cut -d: -f3 /proc/self/cgroup)/cpuset.cpus.effective 2>/dev/null)\"
bash \"\$JOB_ROOT/cmd.sh\"
rc=\$?
echo \"finished \$(date -Is), exit \$rc\"
echo \$rc > \"\$JOB_ROOT/exit\"
exit \$rc
RUN
    chown -R $RUSER: \$J $ROOT/cache
    systemd-run --quiet --unit=$UNIT$id --uid=$RUSER --gid=$RUSER \
      ${cpus:+-p AllowedCPUs=$cpus} ${mem:+-p MemoryMax=$mem} -p Nice=15 -p IOSchedulingClass=idle \
      -p StandardOutput=append:\$J/log -p StandardError=append:\$J/log \
      --setenv=JOB_ROOT=\$J --setenv=JOB_OUT=\$J/out --setenv=JOB_CACHE=$ROOT/cache \
      --setenv=HOME=/home/$RUSER --setenv=PATH=$ROOT/cache/bin:/usr/local/bin:/usr/bin:/bin \
      bash \$J/run.sh" || { rm -f "$list"; not_run "submission of $id failed"; }
  rm -f "$list"
  echo "SUBMITTED: $id"
}

cmd_status() {
  local filter=${1:-}
  [ -n "$filter" ] && valid_id "$filter"
  rsh "cd $ROOT 2>/dev/null || { echo 'no jobs'; exit 0; }
    for J in \$(ls -d */ 2>/dev/null | tr -d / | grep -v '^cache\$' | sort); do
      case '$filter' in ''|\$J) ;; *) continue ;; esac
      st=\$(systemctl is-active $UNIT\$J 2>/dev/null)
      if [ -f \$J/exit ]; then rc=\$(cat \$J/exit); [ \"\$rc\" = 0 ] && v='DONE' || v=\"FAILED (exit \$rc)\"
      elif [ \"\$st\" = active ] || [ \"\$st\" = activating ]; then v=RUNNING
      else v=\"LOST (unit \$st, no exit file)\"; fi
      echo \"\$J  \$v  \$(grep -E '^(submitted|cmd)=' \$J/meta | tr '\n' ' ')\"
      [ -n '$filter' ] && { echo '--- log tail:'; tail -n 5 \$J/log 2>/dev/null; }
    done" || not_run "no connection to $HOST"
}

cmd_log() {
  [ $# -ge 1 ] || not_run "log needs a job id"
  valid_id "$1"
  rsh "tail -n ${2:-40} $ROOT/$1/log" || not_run "no log for $1"
}

cmd_fetch() {
  [ $# -ge 1 ] || not_run "fetch needs a job id"
  valid_id "$1"
  local top; top=$(git rev-parse --show-toplevel)
  local dest=${2:-$top/remote-results/$1}
  mkdir -p "$dest"
  rsh "cd $ROOT/$1 && tar -czf - out log meta \$(ls exit 2>/dev/null)" | tar -xzf - -C "$dest" \
    || not_run "could not fetch $1"
  if [ -f "$dest/exit" ]; then
    local rc; rc=$(cat "$dest/exit")
    if [ "$rc" = 0 ]; then echo "DONE: $1 → $dest"; exit 0; fi
    echo "FAILED (exit $rc): $1 → $dest (see $dest/log)"; exit 1
  fi
  echo "NOT FINISHED: $1 — partial results in $dest"; exit 1
}

cmd_cancel() {
  [ $# -ge 1 ] || not_run "cancel needs a job id"
  valid_id "$1"
  rsh "systemctl stop $UNIT$1 2>/dev/null; [ -f $ROOT/$1/exit ] || echo cancelled > $ROOT/$1/exit; cat $ROOT/$1/exit" \
    || not_run "no connection to $HOST"
}

case ${1:-} in
  submit) shift; cmd_submit "$@" ;;
  status) shift; cmd_status "$@" ;;
  log) shift; cmd_log "$@" ;;
  fetch) shift; cmd_fetch "$@" ;;
  cancel) shift; cmd_cancel "$@" ;;
  *) sed -n '2,36p' "$0"; exit 2 ;;
esac
