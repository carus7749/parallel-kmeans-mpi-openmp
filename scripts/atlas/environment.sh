#!/bin/bash
# Source in a PBS compute job; never run benchmarks on a login node.
set -euo pipefail
if ! type module >/dev/null 2>&1; then
    if [[ -r /etc/profile.d/modules.sh ]]; then source /etc/profile.d/modules.sh; fi
fi
if ! type module >/dev/null 2>&1; then
    echo 'Module initialization unavailable: obtain the Atlas initialization command.' >&2; return 1
fi
module purge
# Explicit Atlas module search paths.
printf 'Initial MODULEPATH=%s\n' "${MODULEPATH:-<unset>}"
for atlas_module_dir in /app1/modules/centos6.3 /app1/modules/centos7; do
    if [[ ! -d "$atlas_module_dir" || ! -r "$atlas_module_dir" || ! -x "$atlas_module_dir" ]]; then
        printf 'Atlas module directory inaccessible: %s\n' "$atlas_module_dir" >&2
        return 1
    fi
    module use "$atlas_module_dir" || return 1
done
unset atlas_module_dir
printf 'Effective MODULEPATH=%s\n' "${MODULEPATH:-<unset>}"
# Let OpenMPI load its own gcc/7.3.0 dependency. Do not load gcc/9.2.0.
module load openmpi/4.1.2
module load gmp/4.3.2
module load mpfr/2.4.2
export ATLAS_GXX=/app1/centos7/gnu/gcc-7.3.0_install/bin/g++
export ATLAS_MPI=/app1/centos7/gnu/openmpi-4.1.2_install
export OMPI_CXX="$ATLAS_GXX"
export PATH="$ATLAS_MPI/bin:$(dirname "$ATLAS_GXX"):$PATH"
[[ "$($ATLAS_GXX -dumpfullversion -dumpversion)" == 7.3.0 ]] || { echo 'GCC mismatch'; return 1; }
"$ATLAS_MPI/bin/mpirun" --version | grep -E '^mpirun \(Open MPI\) 4\.1\.2$' >/dev/null
[[ "$("$ATLAS_MPI/bin/mpicxx" --showme:command)" == "$ATLAS_GXX" ]] || { echo 'MPI backend mismatch'; return 1; }
# Use the verified interpreter directly; never load the Miniconda module.
export ATLAS_PYTHON=/app1/bioinfo/miniconda/4.9/bin/python
"$ATLAS_PYTHON" -c 'import sys; assert sys.version_info[:3] == (3,8,5), "Expected verified Python 3.8.5"'
export OMP_DYNAMIC=FALSE OMP_PLACES=cores OMP_PROC_BIND=close
unset OMP_THREAD_LIMIT GOMP_CPU_AFFINITY KMP_AFFINITY || true
module list 2>&1
"$ATLAS_GXX" --version
"$ATLAS_MPI/bin/mpicxx" --showme
"$ATLAS_MPI/bin/mpicxx" --showme:compile
"$ATLAS_MPI/bin/mpicxx" --showme:link
"$ATLAS_MPI/bin/ompi_info" --version
"$ATLAS_PYTHON" --version
