#!/bin/bash
# Common body called by PBS scripts. No submission or remote transfer here.
set -euo pipefail
mode=${1:?build, correctness, pilot, calibration or full suite required}
: "${PBS_JOBID:?Run through PBS only}" "${PBS_O_WORKDIR:?}" "${PBS_NODEFILE:?}"
[[ "$mode" == build || "$mode" == correctness || "$mode" == pilot || "$mode" == calibration || "$mode" == full_strong || "$mode" == full_weak || "$mode" == full_characteristics ]] || exit 2
# Guard before any compilation/workload; only a single allocated compute host.
mapfile -t nodes < <(sort -u "$PBS_NODEFILE")
[[ ${#nodes[@]} == 1 && ${nodes[0]%%.*} == $(hostname -s) ]] || { echo 'Not on single allocated compute host'; exit 2; }
cd "$PBS_O_WORKDIR"
[[ -f src/main.cpp && -f Makefile ]] || { echo 'Submit from project root'; exit 2; }
mkdir -p results/atlas
ATLAS_RUN_DIR=$(mktemp -d "$PWD/results/atlas/${mode}.${PBS_JOBID}.XXXXXX")
export ATLAS_RUN_DIR
exec > >(tee "$ATLAS_RUN_DIR/job.log") 2>&1
finish() {
    rc=$?;trap - EXIT
    /opt/pbs/bin/qstat -f "$PBS_JOBID" > "$ATLAS_RUN_DIR/qstat-exit.txt" 2>&1 || true
    date -u +%FT%TZ > "$ATLAS_RUN_DIR/finished-utc.txt"
    printf '%s\n' "$rc" > "$ATLAS_RUN_DIR/exit-code.txt"
    exit "$rc"
}
trap finish EXIT
printf 'Run directory: %s\n' "$ATLAS_RUN_DIR"
date -u +%FT%TZ > "$ATLAS_RUN_DIR/started-utc.txt"
cp "$PBS_NODEFILE" "$ATLAS_RUN_DIR/nodefile.txt"
/opt/pbs/bin/qstat -f "$PBS_JOBID" > "$ATLAS_RUN_DIR/qstat-start.txt" 2>&1
/opt/pbs/bin/qstat -Qf parallel > "$ATLAS_RUN_DIR/queue-parallel.txt" 2>&1 || true
/opt/pbs/bin/qstat -Qf serial > "$ATLAS_RUN_DIR/queue-serial.txt" 2>&1 || true
hostname > "$ATLAS_RUN_DIR/hostname.txt"
uname -a > "$ATLAS_RUN_DIR/uname.txt"
lscpu > "$ATLAS_RUN_DIR/lscpu.txt"
grep Cpus_allowed_list /proc/self/status > "$ATLAS_RUN_DIR/job-affinity.txt"
env | sort | grep -E '^(PBS_|OMP_|OMPI_|LOADEDMODULES=|MODULEPATH=|PATH=|LD_LIBRARY_PATH=)' > "$ATLAS_RUN_DIR/selected-environment.txt" || true
# Snapshot only sources: exclude local Mac binaries, previous results and data.
mkdir "$ATLAS_RUN_DIR/source"
cp -R src include tests scripts Makefile "$ATLAS_RUN_DIR/source/"
cd "$ATLAS_RUN_DIR/source"
find src include tests scripts -type f ! -path '*/__pycache__/*' -exec sha256sum {} + > "$ATLAS_RUN_DIR/source-sha256.txt"
sha256sum Makefile >> "$ATLAS_RUN_DIR/source-sha256.txt"
source scripts/atlas/environment.sh > "$ATLAS_RUN_DIR/environment.log" 2>&1
export ATLAS_ALLOCATED_CORES=12 ATLAS_CORE_BUDGET=4
if [[ "$mode" == build ]]; then
    export ATLAS_ALLOCATED_CORES=1 ATLAS_CORE_BUDGET=1
fi
if [[ "$mode" == full_* ]]; then export ATLAS_CORE_BUDGET=12; fi
printf 'allocated_cores=%s\nactive_core_cap=%s\n' "$ATLAS_ALLOCATED_CORES" "$ATLAS_CORE_BUDGET" > "$ATLAS_RUN_DIR/resources.txt"
[[ $(wc -l < "$PBS_NODEFILE") -ge $ATLAS_ALLOCATED_CORES ]] || { echo 'Insufficient PBS MPI slots'; exit 2; }
# Never reuse Mac binaries or change an active job's binaries. Sequential build.
make -j1 CXX="$ATLAS_GXX" MPICXX="$ATLAS_MPI/bin/mpicxx" \
 CPPFLAGS='-DOMPI_SKIP_MPICXX=1' \
 CXXFLAGS='-O3 -std=c++17 -Wall -Wextra -Wpedantic' OMPFLAGS=-fopenmp \
 > "$ATLAS_RUN_DIR/build.log" 2>&1
"$ATLAS_MPI/bin/mpicxx" -DOMPI_SKIP_MPICXX=1 -O2 -std=c++17 -fopenmp \
 scripts/atlas/affinity.cpp -o bin/affinity >> "$ATLAS_RUN_DIR/build.log" 2>&1
for exe in bin/*; do
    sha256sum "$exe" >> "$ATLAS_RUN_DIR/binary-sha256.txt"
    ldd "$exe" >> "$ATLAS_RUN_DIR/ldd.txt" 2>&1
done
if [[ "$mode" == build ]]; then exit 0; fi
if [[ "$mode" == full_* ]]; then
    "$ATLAS_PYTHON" scripts/atlas/full_suite.py "$mode"
    exit 0
fi
for cfg in '1 1' '2 1' '3 1' '4 1' '1 4' '2 2'; do
    read -r p t <<< "$cfg"
    "$ATLAS_PYTHON" scripts/atlas/launch.py -n "$p" "$PWD/bin/affinity" --threads "$t" \
      > "$ATLAS_RUN_DIR/affinity-p${p}-t${t}.stdout" 2> "$ATLAS_RUN_DIR/affinity-p${p}-t${t}.stderr"
done
if [[ "$mode" == correctness ]]; then
    export MPIEXEC="$ATLAS_PYTHON $PWD/scripts/atlas/launch.py"
    # Instrument only the snapshot to retain every subprocess command/stdout/stderr.
    "$ATLAS_PYTHON" scripts/atlas/archive_tests.py
    sha256sum tests/test_correctness.py > "$ATLAS_RUN_DIR/instrumented-test-sha256.txt"
    "$ATLAS_PYTHON" tests/test_correctness.py > "$ATLAS_RUN_DIR/correctness.log" 2>&1
else
    export ATLAS_EXPERIMENT_MODE="$mode"
    "$ATLAS_PYTHON" scripts/atlas/run_suite.py
fi
