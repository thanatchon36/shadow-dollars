#!/usr/bin/env bash
# Full pipeline: data -> real-data figures -> Monte Carlo -> simulation figures -> tests -> paper.
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH=src
python -m shadowdollars.collectors.public      # downloads only files that are missing
python scripts/figures_real.py
bash run_mc.sh                                  # about 10 minutes on one core
python scripts/figures_sim.py
pytest -q
cp figures/fig_*.pdf paper/figures/
cd paper && pdflatex -interaction=nonstopmode main && bibtex main \
  && pdflatex -interaction=nonstopmode main && pdflatex -interaction=nonstopmode main
cp main.pdf paper.pdf
