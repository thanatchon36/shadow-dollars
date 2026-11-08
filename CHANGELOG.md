# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Zenodo archive: release 0.1.0 is [10.5281/zenodo.24050718](https://doi.org/10.5281/zenodo.24050718), and the
  concept DOI for all versions is [10.5281/zenodo.24050717](https://doi.org/10.5281/zenodo.24050717); DOI badge in the
  README, `doi` in `CITATION.cff`, and the archive linked from the web reader and the Hugging Face dataset.

## [0.1.0] - 2026-11-08

### Added
- Public-data evidence (paper §6): USDT supply and clienteles by chain, the USDC exit from Tron, the macro motive
  (inflation and exchange-rate volatility across 23 comparators), address formats on the OFAC SDN list, and event
  studies with placebo-calibrated inference over 149 random dates.
- Detectors (`shadowdollars.detectors`): difference-in-bunching at the 50,000-baht face-verification threshold,
  dwell-time mixtures, direction-aware graph exposure, anomaly scoring, synthetic control and event studies.
- Agent-based simulator of an exchange-year with planted mule accounts and a Monte Carlo in resumable chunks
  (`run_mc.sh`), with every number quoted in the paper written to `data/processed/facts_*.json`.
- Raw data as retrieved on 8 November 2026 with `data/raw/MANIFEST.json` (URL, retrieval time, size, SHA-256).
- The preprint in arXiv layout (`paper/`, `paper/paper.pdf`) and the upload bundle (`arxiv/make_arxiv_zip.sh`).
- Web reader for the paper, served by GitHub Pages from `docs/paper/` at
  <https://thanatchon36.github.io/shadow-dollars/paper/> and built by `make web` (`scripts/build_web.py`): pandoc
  renders the LaTeX source, and figure, table, equation and cross-reference numbers come from the LaTeX run so they
  match the PDF.
- `Makefile` with targets for every pipeline step (replaces `run_all.sh`); `make paper` falls back to tectonic when
  `pdflatex` is not installed.
- Dataset on Hugging Face, [`thanatchon36/shadow-dollars`](https://huggingface.co/datasets/thanatchon36/shadow-dollars): the raw public data with its manifest
  and checksums, the derived tables behind the public-data results, and the Monte Carlo results (simulated);
  Coin Metrics files and their derivatives under CC BY-NC 4.0, the rest as listed in its `LICENSE`.
- README banner from real data (`make banner`, `docs/assets/banner.png`), logo, `docs/data_sources.md`,
  `.zenodo.json` and this changelog.

### Fixed
- `pytest` collected the copy of the tests under `arxiv/submission/anc/` and stopped on a module-name clash;
  `testpaths` now limits collection to `tests/`.
