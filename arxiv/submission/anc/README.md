# Ancillary files: replication code for "Shadow Dollars" (Thanatchon Chongmankhong, arXiv preprint, 2026)

* `src/shadowdollars/` - collectors, detectors (bunching, dwell mixtures, graph exposure, scoring, synthetic control, event study), simulator, Monte Carlo
* `scripts/` - `figures_real.py` (public data), `figures_sim.py` (simulation), `run_mc.py` (Monte Carlo chunks)
* `tests/` - unit tests (`pytest -q`)
* `data/raw/MANIFEST.json` - URL, retrieval time (8 Nov 2026), size and SHA-256 of every raw file used in the paper
* `data/processed/` - derived series, Monte Carlo results and `facts_*.json` with every number quoted in the paper

Reproduce: `pip install -e ".[dev]"`, then `python -m shadowdollars.collectors.public`, `python scripts/figures_real.py`,
`bash run_mc.sh`, `python scripts/figures_sim.py`. Raw data are public and re-downloaded by the collectors; some sources
update daily, so a fresh download is a later vintage than the one recorded in the manifest.
Simulated results validate methods only and are not evidence about real markets.
