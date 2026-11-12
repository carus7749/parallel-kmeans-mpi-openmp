# Reproduce the academic report

The maintained typesetting source is `report.tex`. It uses the unmodified
IEEEtran 1.8b class with `conference,a4paper,10pt`. See TEMPLATE_SOURCE.md and
IEEEtran-README.txt for provenance and licensing. The document represents a
DSA5208 course submission, not a published conference paper.

From the project root:

```sh
sh scripts/build_report_latex.sh
```

Install either Tectonic (tested with 0.17.0) or a TeX Live/MacTeX distribution
with pdfLaTeX. Tectonic downloads missing TeX packages on first use. Required
packages: fontenc, amsmath, amssymb, graphicx, cite, xurl, hyperref, microtype,
flushend, needspace, and ragged2e. The IEEEtran class is supplied here; it is not modified.

Direct commands from this directory:

```sh
tectonic --keep-logs report.tex
# Or use pdfLaTeX twice for citations and figure references:
pdflatex -interaction=nonstopmode -halt-on-error report.tex
pdflatex -interaction=nonstopmode -halt-on-error report.tex
```

Direct compilation produces report.pdf here. The shell wrapper also copies it
to report/DSA5208_Report.pdf. No BibTeX invocation is needed:
the two existing references use thebibliography and numbered citations.

All five figures are included from ../../figures/. Existing PNG and SVG assets
are retained; no experimental data are altered by document compilation.
The .tex source is authoritative. The public copy omits the student ID and internal node hostname; the private Canvas report retains its original assessment metadata. Technical content is unchanged.
