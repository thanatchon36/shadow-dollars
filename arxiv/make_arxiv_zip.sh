#!/usr/bin/env bash
# Rebuild arxiv/arxiv_submission.zip from paper/ (LaTeX source, compiled by arXiv with pdfLaTeX)
# and the replication code (uploaded as ancillary files under anc/).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d)
cp "$ROOT"/paper/main.tex "$ROOT"/paper/arxiv.sty "$ROOT"/paper/appendix.tex "$ROOT"/paper/refs.bib "$ROOT"/paper/main.bbl "$TMP"/
cp "$ROOT"/paper/sec*.tex "$TMP"/
cp -r "$ROOT"/paper/tables "$ROOT"/paper/figures "$TMP"/
mkdir -p "$TMP"/anc/data/raw "$TMP"/anc/data/processed
cp -r "$ROOT"/src "$ROOT"/scripts "$ROOT"/tests "$ROOT"/pyproject.toml "$ROOT"/run_mc.sh "$TMP"/anc/
cp "$ROOT"/arxiv/anc_README.md "$TMP"/anc/README.md
cp "$ROOT"/data/raw/MANIFEST.json "$TMP"/anc/data/raw/
cp "$ROOT"/data/processed/*.csv "$ROOT"/data/processed/*.json "$TMP"/anc/data/processed/
cp "$ROOT"/figures/qa_overlaps.json "$TMP"/anc/data/processed/figure_overlap_qa.json
find "$TMP" -name "__pycache__" -type d -prune -exec rm -rf {} +
rm -f "$ROOT"/arxiv/arxiv_submission.zip
(cd "$TMP" && zip -qr "$ROOT"/arxiv/arxiv_submission.zip .)
rm -rf "$TMP"
echo "wrote arxiv/arxiv_submission.zip"
