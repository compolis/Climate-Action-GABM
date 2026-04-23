# Paper: GABM Tipping Point and Competing Persuasion

Single-source Springer Nature manuscript for the pol-sci quants seminar.

## Layout

- `sn-article.tex` — manuscript source (single file per SN policy).
- `references.bib` — bibliography (numbered style: `sn-mathphys-num`).
- `figures/` — figures referenced by the manuscript (PDF preferred).
- `sn-jnl.cls` and `sn-*.bst` — Springer Nature template files (vendored).
- `_template/` — original SN sample PDF and user manual for reference; not part of the build.
- `Makefile` — `make` builds `sn-article.pdf`; `make watch` for live rebuild; `make clean` / `make distclean`.

## Build

```sh
cd paper
make            # one-shot build
make watch      # live rebuild on save (latexmk -pvc)
make clean      # remove aux files, keep PDF
```

Requires a TeX distribution with `latexmk`, `pdflatex`, and `bibtex` (TeX Live or MacTeX).

## Overleaf sync

The Overleaf project is the source of truth for collaborators; this directory mirrors the same single-file structure so a one-shot zip export (Overleaf → Menu → Source) can be dropped in here, or a GitHub link configured the other way. Keep filenames identical (`sn-article.tex`, `references.bib`) to avoid having to reset Overleaf's main-document setting.
