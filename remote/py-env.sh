# Python environment for jobs on the box (sourced by a job command):
#
#     source remote/py-env.sh && cd metalibrary && python colour_solver.py ...
#
# The box has python3 without ensurepip, so the venv is made with uv, which remote/setup-box.sh
# puts into $JOB_CACHE/bin. The venv is shared between jobs and keyed by the requirements file,
# so a changed pin makes a new one instead of mutating the old.
set -e
: "${JOB_CACHE:?JOB_CACHE is not set (are we inside a mr-remote job?)}"
_req="$(dirname "${BASH_SOURCE[0]}")/requirements-py.txt"
_key=$(sha1sum "$_req" | cut -c1-10)
_venv="$JOB_CACHE/venv-$_key"
if [ ! -x "$_venv/bin/python" ]; then
  uv venv -q -p /usr/bin/python3 "$_venv"
  uv pip install -q --python "$_venv/bin/python" -r "$_req"
fi
export PATH="$_venv/bin:$PATH"
set +e
