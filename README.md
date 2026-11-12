# Scalable K-means Clustering Using Hybrid MPI and OpenMP

Repository: [https://github.com/carus7749/parallel-kmeans-mpi-openmp](https://github.com/carus7749/parallel-kmeans-mpi-openmp)

DSA5208 Project 3 — Lai Xining — 5 November 2026.

C++17 Lloyd K-means with serial, MPI-only and MPI+OpenMP executables.
Atlas single-node experiments and automated evidence checks are complete.

## Motivation and measured results

K-means combines independent distance calculations with globally dependent centroid updates, making it a useful study of computation, communication and thread coordination in data science.

All reported performance measurements came from actual NUS Atlas jobs; no timings are generated estimates.

| Measurement | Result | Baseline |
|---|---:|---|
| Strong loop speedup, MPI 12 ranks | 10.85x (90.41% efficiency) | Serial, same input |
| Strong loop speedup, hybrid 6 ranks x 2 threads | 9.16x (76.33%) | Serial, same input |
| Weak loop efficiency, MPI 12 cores | 91.12% | MPI 1 core |
| Weak loop efficiency, hybrid 12 cores | 93.51% | Hybrid 2 cores |

These are single-node CPU results, not inter-node or GPU results. See timing definitions below and the report for qualifications.

## Public data and private evidence

The public JSONL files omit command arrays (which contained personal absolute paths) and scheduler job IDs. All measurements and remaining JSON values are unchanged. Each provenance file distinguishes original private hashes from public derivative hashes. Full logs, environment dumps, source snapshots and job records remain in the private evidence archive; they are not published here. The public report source omits the student ID and internal node name. The Canvas report is retained separately.

Atlas-specific software installation paths in the PBS environment script are configuration, not portable defaults. Adapt them with your cluster administrator; the generic local build does not depend on Atlas.

## Implementations and numerical policies

All executables use the same row-major double data, nearest-center calculation,
seeded distinct-sample initialization and centroid update rules. Exact ties select
the lowest cluster index; empty clusters retain their preceding center. Normal
execution stops on maximum Euclidean centroid displacement <= tolerance or the
iteration cap. `--fixed` disables early stopping. Final labels/SSE are recomputed
against returned centers, including when the iteration cap is reached.

- Serial: single process, no MPI/OpenMP calls.
- MPI: contiguous row partitions (sizes differ by at most one), replicated centers,
  one initial broadcast, two MPI_Allreduce calls per iteration for double sums
  and integer counts. Zero-row ranks still participate in collectives.
- Hybrid: static OpenMP row worksharing, thread-private sums/counts and serial
  local merging. MPI_THREAD_FUNNELED; MPI calls occur outside parallel regions.

Synthetic data have ten latent groups independent of K, centers in [0,12) and
bounded noise in [-0.5,0.5). Global row/feature/seed indexing makes generation
partition-independent. This is not k-means++ and no global optimum is promised.
Floating-point reduction order changes with rank/thread counts; tolerance-based
agreement is expected, not bitwise identity or identical convergence iterations.

## Dependencies and local/Linux build

C++17 compiler, MPI headers/runtime, OpenMP runtime, Make. The tested Atlas stack
is GCC 7.3.0 and OpenMPI 4.1.2. Python 3.8+ standard library runs tests and benchmark
scripts; plotting requires matplotlib/numpy and PDF compilation requires Tectonic or a TeX Live/MacTeX distribution.
The plotting/PDF tools run locally and are not required to compile K-means.

```sh
make CXX=g++ MPICXX=mpicxx CPPFLAGS=-DOMPI_SKIP_MPICXX=1 OMPFLAGS=-fopenmp
```

Run `make clean` before changing compiler/flags; this removes only generated bin/.
A machine-specific Apple Silicon recipe is supplied in scripts/build_local_macos.sh
and assumes installed MPI/OpenMP libraries under /opt/anaconda3. Linux/Atlas
reproduction does not require that recipe.

Examples below are for a local workstation or an appropriately allocated compute
session, NEVER an Atlas login node. Generic mpirun binding is implementation-specific;
use the supplied PBS workflow on Atlas.

```sh
bin/kmeans_serial --n 10000 --d 8 --k 5 --iterations 20 --seed 42 --fixed
mpirun -n 2 bin/kmeans_mpi --n 10000 --d 8 --k 5 --iterations 20 --seed 42 --fixed
OMP_PLACES=cores OMP_PROC_BIND=close mpirun -n 2 bin/kmeans_hybrid \
  --n 10000 --d 8 --k 5 --iterations 20 --seed 42 --fixed --threads 2
```

| Option | Default | Meaning |
|---|---:|---|
| --n | 10000 | Positive number of samples |
| --d | 8 | Positive number of features |
| --k | 5 | Number of centers, 1 <= K <= N |
| --seed | 42 | Unsigned 64-bit seed |
| --iterations | 100 | Maximum iterations, exact with --fixed |
| --tol | 1e-6 | Maximum centroid displacement stopping threshold |
| --threads | 1 | OpenMP threads per rank; non-hybrid requires 1 |
| --fixed | off | Disable tolerance stopping |
| --details | off | Initial/final centers and labels; small tests only |
| --input FILE | none | Exactly N*d whitespace-separated finite numbers |
| --init FILE | none | Exactly K*d initial center coordinates |
| --help | | Use alone to display usage |

Files have no header. Values must have absolute value <= 1e100; no implicit CSV
conversion, standardization or missing-value handling. N*d <= INT_MAX is a
conservative portable MPI-count bound. Root reads input files and scatters rows;
synthetic generation is distributed.

## Atlas module initialization and allocation

scripts/atlas/environment.sh is sourced by each PBS job and uses:

```sh
module purge
module use /app1/modules/centos6.3
module use /app1/modules/centos7
module load openmpi/4.1.2
module load gmp/4.3.2
module load mpfr/2.4.2
```

It checks directory access, effective GCC 7.3.0, OpenMPI 4.1.2 and Python 3.8.5.
OpenMPI loads GCC 7.3.0; do not load GCC 9.2.0. Compiler and MPI paths are pinned
under /app1/centos7/gnu/. Python is /app1/bioinfo/miniconda/4.9/bin/python; do not
load the Miniconda module because it can change library paths.

The launcher requires PBS and one allocated compute host. It uses
`--map-by slot:PE=T --bind-to core --nooversubscribe --report-bindings` with
OMP_DYNAMIC=FALSE, OMP_PLACES=cores and OMP_PROC_BIND=close. P*T must not exceed
the active cap or allocation. Preflights check distinct guest-visible core
bindings. PBS scripts deliberately set mpiprocs=ncpus: nodefile line counts are
not generally equivalent to allocated CPU counts for arbitrary hybrid requests.

## PBS workflow and correctness tests

From the extracted project root on Atlas, submit ONE stage at a time, inspect
its completion and exit status, then continue. These commands create new jobs;
they are for reproduction, not needed to inspect the supplied measurements.

```sh
mkdir -p results/submissions
JOB=$(/opt/pbs/bin/qsub scripts/atlas/build.pbs) &&
  printf '%s\n' "$JOB" > "results/submissions/build-${JOB}.jobid"
/opt/pbs/bin/qstat -f "$JOB"
# Once finished:
/opt/pbs/bin/qstat -xf "$JOB"
# After successful build, submit correctness separately:
/opt/pbs/bin/qsub scripts/atlas/correctness.pbs
```

Build requests serial queue, 1 CPU, 2 GB, 10 minutes. Correctness requests parallel
queue, 12 CPUs, 2 GB, 10 minutes, using at most four active cores. A fresh source
snapshot is compiled within each PBS allocation. No existing Mac binary is reused.

On a local workstation with MPI configured, `python3 tests/test_correctness.py`
runs a separately implemented Python reference plus executable checks. MPIEXEC
can override the launcher and must accept `-n P`. Atlas correctness.pbs adds
raw per-invocation evidence capture to its snapshot of the test script.
Fixtures include empty clusters, ties, K=1/K=N, uneven and empty partitions,
initialization, convergence, and invalid input. Invalid-input subprocesses are
expected to fail; the overall test job must pass. Successful Atlas job 1033975
records 54 checks passing. Tests are evidence, not proof for all possible inputs.

## Benchmark reproduction

After inspecting correctness results, submit and inspect each suite sequentially:

```sh
/opt/pbs/bin/qsub scripts/atlas/full_strong.pbs
# Wait and inspect before the next submission:
/opt/pbs/bin/qsub scripts/atlas/full_weak.pbs
# Wait and inspect before the next submission:
/opt/pbs/bin/qsub scripts/atlas/full_characteristics.pbs
```

Each requests parallel queue, 12 CPUs, 4 GB, 30 minutes: maximum 6 allocated
core-hours each, 18 for all three. Active cores vary per configuration; input
characteristics uses at most four active cores. Required modules and binding
are applied by job.sh, environment.sh and launch.py, not by the login shell.

All suites use seed 42, 50 fixed iterations, one warmup and five measured repeats,
with reproducibly shuffled sweeps (seed 5208). Strong scaling: 15 configurations,
N=1M,d=16,K=8, 90 invocations. Weak: 9 configurations, 250k rows/active core,
54 invocations. Characteristics: 7 input shapes x 3 implementations, 126 invocations.
full_suite.py specifies exact matrices; each invocation has a 120-second timeout
and errors stop the suite. Pilot/calibration PBS scripts are also included.

## Expected outputs and supplied data

Each executable emits one JSON object on stdout; errors go to stderr. It includes
input dimensions, rank/thread counts, iterations, SSE and timing fields.
`--details` adds center and label arrays. Atlas jobs create unique directories
`results/atlas/<mode>.<jobid>.<suffix>/`, containing source/binary hashes, source
snapshot, compiler/environment/topology logs, PBS metadata, individual stdout,
stderr and command records, plus exit-code.txt. Formal suites produce
preflight-status.txt, suite-status.txt and `<mode>.jsonl`.

Expected success: exit-code 0, preflight PASS and suite PASS with 90/54/126 records.
A PBS job ID indicates acceptance, not success. Final qstat Exit_status must be
checked. Preserve failed runs rather than overwriting them.

The three results/atlas-*-analysis directories contain privacy-redacted formal JSONL,
summary CSV and provenance. Warmup records are preserved but excluded from
medians. Timing ranges are min/max of five measured runs, not confidence intervals.
Strong speedup uses matching serial loop medians; efficiency divides by active
P*T, not 12 reserved cores. Weak efficiency uses its own family baseline: MPI
one core, hybrid two cores. Do not compare SSE across different input sizes.

loop_s is the maximum iteration-loop time over ranks. end_to_end_s is an
application timer after MPI initialization and before diagnostics/finalization.
external_wall_s includes invocation/launcher overhead. These are different
boundaries. Component rank maxima are not additive; collective time includes
waiting. MPI is faster in the reported loop comparison, while hybrid 6x2 beats
MPI 12x1 under external invocation timing in this strong-scaling sample.

## Reproduce figures and report (local analysis only)

```sh
python3 scripts/make_report_figures.py
sh scripts/build_report_latex.sh
```

Outputs: five PNG/SVG figure pairs in figures/ and
report/DSA5208_Report.pdf from report/latex/report.tex.
See report/latex/BUILD.md for LaTeX dependencies and direct compilation commands.
No experimental records are modified by these commands. Raw full logs are in a
separate evidence ZIP, not required to regenerate the figures from supplied JSONL.
To validate that archive after extracting it:

```sh
python3 scripts/audit_archive.py /path/to/evidence/full-archive
```

The audit checks source/binary hashes, instrumented test hash, formal JSONL against
individual stdout, repetition coverage and final scheduler exit statuses.

## Limitations

Only single-node CPU scaling is measured (up to 12 guest-visible active cores
under KVM); no inter-node, GPU, hardware-counter or real-data claims. One seed,
fixed iterations and a limited input range were tested. Simple initialization,
O(T*K*d) thread buffers, serial merging, replicated centers and root file loading
limit generality. The module patch succeeded on the measured node; the earlier failing node was not retested.

## AI Usage Disclosure

OpenAI Codex was used extensively as an assistant throughout this project, including implementation, testing, debugging, performance analysis, visualization, and report preparation. The HPC experiments were conducted on NUS Atlas, and all reported performance results are based on actual measurements rather than generated estimates.
