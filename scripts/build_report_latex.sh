#!/bin/sh
# Local document compilation only; does not run benchmarks or contact Atlas.
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_root/report/latex"
if command -v tectonic >/dev/null 2>&1; then
    tectonic --keep-logs report.tex
elif command -v pdflatex >/dev/null 2>&1; then
    pdflatex -interaction=nonstopmode -halt-on-error report.tex
    pdflatex -interaction=nonstopmode -halt-on-error report.tex
else
    printf '%s\n' 'Install Tectonic or a TeX Live/MacTeX distribution with pdflatex.' >&2
    exit 1
fi
cp report.pdf ../DSA5208_Report.pdf
printf '%s\n' "$project_root/report/DSA5208_Report.pdf"
