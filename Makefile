PY ?= .venv/bin/python

.PHONY: setup data figures mc sim test paper web banner poster arxiv all clean

setup:          ## create venv and install the package (needs uv)
	uv venv .venv --python 3.12
	uv pip install --python .venv/bin/python -e ".[dev]"

data:           ## download the public data into data/raw/ (only files that are missing) + MANIFEST.json
	$(PY) -m shadowdollars.collectors.public

figures:        ## figures and tables from public data -> figures/, paper/tables/, data/processed/facts_real.json
	$(PY) scripts/figures_real.py

mc:             ## Monte Carlo in resumable chunks (about 10 minutes on one core) -> data/processed/mc_*.csv
	PY=$(PY) bash run_mc.sh

sim:            ## figures and tables from the simulation -> figures/, paper/tables/, data/processed/facts_sim.json
	$(PY) scripts/figures_sim.py

test:
	$(PY) -m pytest -q

paper:          ## compile paper/paper.pdf (pdflatex + bibtex when installed, otherwise tectonic in paper/.build/)
	cp figures/fig_*.pdf paper/figures/
	@if command -v pdflatex >/dev/null 2>&1; then \
	  cd paper && pdflatex -interaction=nonstopmode main && bibtex main \
	    && pdflatex -interaction=nonstopmode main && pdflatex -interaction=nonstopmode main \
	    && cp main.pdf paper.pdf; \
	else \
	  rm -rf paper/.build && mkdir paper/.build \
	    && cp -R paper/*.tex paper/*.sty paper/*.bib paper/tables paper/figures paper/.build/ \
	    && sed -i.bak '1{/pdfoutput/d;}' paper/.build/main.tex \
	    && tectonic --keep-intermediates --chatter=minimal paper/.build/main.tex \
	    && cp paper/.build/main.pdf paper/paper.pdf && cp paper/.build/main.bbl paper/main.bbl; \
	fi

web:            ## web reader -> docs/paper/index.html (pandoc, tectonic, pdftoppm; copies paper/paper.pdf)
	$(PY) scripts/build_web.py

banner:         ## README banner -> docs/assets/banner.png (real data)
	$(PY) scripts/make_banner.py

poster:         ## LinkedIn launch poster -> docs/assets/linkedin_poster.png (1440 x 1800; headless Chrome)
	$(PY) scripts/make_poster.py

arxiv:          ## arXiv upload -> arxiv/arxiv_submission.zip (paper source + replication code as anc/)
	bash arxiv/make_arxiv_zip.sh

all: data figures mc sim test paper web

clean:
	rm -rf data/processed/mc paper/.build
	rm -f paper/*.aux paper/*.log paper/*.out paper/*.blg paper/main.pdf arxiv/arxiv_submission.zip
