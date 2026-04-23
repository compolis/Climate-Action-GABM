# Build the Springer Nature paper.
# Default target produces sn-article.pdf via latexmk + pdflatex.

MAIN := sn-article
LATEXMK := latexmk
LATEXMK_FLAGS := -pdf -interaction=nonstopmode -halt-on-error -file-line-error -shell-escape

.PHONY: all pdf watch clean distclean

all: pdf

pdf:
	$(LATEXMK) $(LATEXMK_FLAGS) $(MAIN).tex

# Continuous build (re-runs on save). Requires latexmk -pvc support.
watch:
	$(LATEXMK) $(LATEXMK_FLAGS) -pvc $(MAIN).tex

# Remove build artefacts, keep the PDF.
clean:
	$(LATEXMK) -c $(MAIN).tex

# Remove everything generated, including the PDF.
distclean:
	$(LATEXMK) -C $(MAIN).tex
