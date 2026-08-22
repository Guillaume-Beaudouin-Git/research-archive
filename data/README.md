# data — sources and caches

Full governance rules: `_meta/data_governance.md` (audit of 2026-06-10). This file is a short map
of what lives here; read the governance doc before adding or moving anything.

## Rule of thumb

One series, one canonical file. Research code **references** `data/`, it never copies a series
into a research folder. Regenerable caches are gitignored; raw/immutable sources and their
manifests are tracked. Never commit a data blob directly under a research folder.

## Contents

| Path | What it is |
|---|---|
| `deep_history_utc/` | Canonical FX/indices M1, true UTC, 2007 → 2026-06, spread calibrated. `MANIFEST.md` is machine-generated — regenerate it, don't hand-edit it. 2018-2021 gaps were backfilled from Dukascopy 2026-06-10 (`*_M1.csv.pre_repair_backup` kept for reproducibility of `announcement_premium`) |
| `deep_history_m1/` | The assembly/backfill code (`assemble.py`, `duka_m1_backfill.py`) and its reports — not the data itself |
| `ftmo_portfolio/` | The live book's research and deployment tree: `v22/` (current spec, engine, EA generation, recost studies), `audit_v2_independent/cleanroom/` (the tracked, canonical signal-engine library — imported by live code, see `docs/ARCHITECTURE.md` and the note on it in root `CLAUDE.md` §Worktree), `j1_suspend_study/`, `j1_lcap8_2026-07/`, `v23_j1_study/`, `v222_swing_fit/`. `CANONICAL_AMENDMENT_PENDING.md` tracks reconciliation still owed to a canonical doc |
| `personal_book/` | Registry of validated/candidate building blocks for the personal (non-propfirm) account. Has its own `README.md` — read that, not this, for how it's organized |
| `panels/` | Flat OHLC panels (`ftmo_open/high/low/close.csv`) consumed directly by research code |
| `metadata/` | Manifests for `data/raw/`-style immutable sources |
| `pairs_trading/`, `vrp/`, `skew_research/` | Per-study caches and small reports for closed or archived research lines — see the asset-class folder that owns the corresponding study for the verdict |
| `tools/` | `generate_manifest.py`, `validate_splice_seams.py`, `audit_bar_density.py` — the scripts that produced the audit/seam-validation reports checked into `deep_history_utc`/`deep_history_m1` |
| `cache.py` | Shared caching helper imported by research code across asset classes |

## What not to do here

- Do not commit a new data blob (parquet/csv of raw prices) outside `data/` — a research folder
  that needs a cached series references the canonical file in `data/`, it does not get its own copy.
- Do not delete a subset (a shorter date range, an old cache) without checking whether it is the
  sole recorded provenance of a validated strategy (e.g. the ex-Kaggle NQ parquet — kept even
  though it's superseded by Databento, because Strategy C's historical validation was run on it).
- Regenerable caches (`*/cache/`, `*_cache/`) are gitignored by design; if one shows up as
  trackable, that is more likely a `.gitignore` gap than an intentional addition.
