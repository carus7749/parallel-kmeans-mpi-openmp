#!/bin/sh
# Verified local installation only; use normal make overrides on the cluster.
set -eu
cd "$(dirname "$0")/.."
make CXX=clang++ MPICXX=clang++ CPPFLAGS='-I/opt/anaconda3/include' \
 OMPFLAGS='-Xpreprocessor -fopenmp' \
 LDLIBS='-L/opt/anaconda3/lib -Wl,-rpath,/opt/anaconda3/lib -lmpi -lomp' "$@"
