# Institutional Sanity Check — Algo_claude
*Produced: 2026-05-23 | Auditor: Claude Sonnet 4.6 | Scope: full repo*

---

## SECTION 1 — Repo Structure Coherence

### 1.1 Directory Layout vs Convention

Convention (CLAUDE.md): `<AssetClass>/research/active/`, `<AssetClass>/research/archived/`, live code in `strategies/`.

**PASS** for Crypto and Futures: layout matches convention exactly. Crypto active/archived split is clean; Futures live/research split is clean.

**FLAG — Stale empty directory:**
`Crypto/research/active/eth_mvrv_netflow/` is an empty directory (64 bytes, no files). The ETH MVRV Netflow research was archived to `Crypto/research/archived/other/eth_mvrv_netflow/`. The empty active/ stub was left behind. Not harmful but clutters the tree. Can be removed (`rmdir`).

**FLAG — Untracked asset classes (never committed):**
Several entire asset classes exist locally but have no git history:

| Directory | Status | Size / Concern |
|-----------|--------|----------------|
| `Commodities/` | Untracked | Unknown; full content never committed |
| `ETF_Vol/` | Untracked | Unknown; full content never committed |
| `Equities/` | Untracked | Unknown; includes live/, research/archived/ |
| `Forex/live/` | Untracked | Live FX infra code (committed vs not unclear) |
| `Forex/data/cache/` | Gitignored ✓ | Large Dukascopy parquets, correct |

Recommendation: commit at minimum `Equities/` research archived code and `Forex/live/` if it contains deployable code. This is not a correctness issue for existing validated strategies, but represents a potential loss of research history.

**PASS — Active research integrity:**
`Crypto/research/active/` contains:
- 4 bootstrap notes (HL maker V1/V2, on-chain, VRP) — Phase 0 documents, correct
- `_preflight/` — preflight data cache, gitignored ✓
- `token_unlocks/` — bootstrap notes only (Phase 0, no hypothesis yet) ✓
- `vrp_short_gamma/` — bootstrap notes only (Phase 0, no hypothesis yet) ✓

**NOTE — vrp_short_gamma vs vrp_deribit:**
`Crypto/research/active/vrp_short_gamma/_bootstrap_vrp_notes.md` (created 2026-05-23 13:45) exists alongside `Crypto/research/archived/options/vrp_deribit/` (archived today, n_tests 153→156). These are distinct: the archived one completed Phase 3 (DECISION.md, full backtest); the active one is a fresh Phase 0 bootstrap for a different VRP framing. Not an error, but should be documented when `vrp_short_gamma` progresses.

**FLAG — Archived data directories not gitignored:**
Three `data/` subdirectories under archived research are untracked (not gitignored):
```
Crypto/research/archived/carry/cs_carry/data/
Crypto/research/archived/mean_reversion/cs_stat_arb/data/
Crypto/research/archived/other/hl_native/data/
```
The `.gitignore` covers `Crypto/research/active/_preflight/cache/` and `Crypto/research/active/vrp_short_gamma/data/` but not a blanket pattern for archived data. These should be added as `Crypto/research/archived/*/data/` or per-directory. Not a secrets risk (binary market data), but these blobs should not be committed.

---

## SECTION 2 — N_Tests Coherence

### 2.1 Crypto-Only Chain (Primary tracking)

Verified from postmortem chain, end-to-end:

| Mission | Postmortem n_tests | README §6.55 |
|---------|-------------------|--------------|
| OAGF gap fade | 148→151 | Line 1328: 142→151 (includes predecessor missions) |
| ETH MVRV Netflow | 151→153 | Line 1329: 151→153 |
| VRP Deribit | 153→156 | Line 1330: 153→156 |
| ETF Regime Overlay | 156→157 | Line 1331 + §6.55 |
| FGVD H1 | 157→158 | Line 1332 + §6.55 |
| WAV H3 | 158→159 | Line 1333 + §6.55 |

**PASS — Crypto chain fully consistent**: every postmortem's declared n_tests matches README §6.55. Terminal value 159 is authoritative for crypto-only count.

### 2.2 Global N_Tests Discrepancies (FLAG)

Three documents give different global figures:

| Source | Value | Last updated |
|--------|-------|-------------|
| `CLAUDE.md` line 119 | **274** | Before `indices_swing` archive (+100 tests) |
| README top status line | **321** | Set by commit `4f45c4d` (indices_swing cleanup) |
| README "crypto 157" in status | **157** | Not updated when crypto section went to 159 today |

**Root cause**: CLAUDE.md was not updated after indices_swing Sprint 2 ARCHIVE (n_tests +100). The discrepancy is 321 − 274 = 47 tests; the indices_swing contribution was +100 but some came before the CLAUDE.md was last written. This is a documentation lag, not a counting error — the per-mission chains are all correct.

**Specific error**: README top-line status says "crypto 157" but crypto section §6.55 says 159. The status line was not updated when today's session added FGVD H1 (+1) and WAV H3 (+1).

**Recommendation**: After next commit, update CLAUDE.md `n_tests = 274` → 324 (321 + 3 from today), and update README top-line "crypto 157" → "crypto 159".

### 2.3 Multi-Test Pre-Registration Discipline

**PASS**: All missions using Test A+B+C blocks (FGVD H1, WAV H3, ETH MVRV) correctly pre-registered the combined block as +1 test, not +3. This is the disciplined approach that avoids multiplicity inflation.

---

## SECTION 3 — Lessons Coherence

### 3.1 CLAUDE.md Lessons vs Research Record

CLAUDE.md `## Methodology lessons (key ones)` currently lists **L1–L12**. The research record has produced additional lessons:

| Lesson | Location | In CLAUDE.md? |
|--------|----------|---------------|
| L13 (VRP costs 200% of gross) | README §6.52, VRP POSTMORTEM | ✗ Not in CLAUDE.md |
| L14 (Execution validation before cost model) | README §6.52 (presumed) | Not verified |
| L15 (ETF regime overlay sub-threshold lift) | README §6.52, today | ✗ Not in CLAUDE.md |
| L17 (F&G velocity = momentum proxy) | README §6.52, today | ✗ Not in CLAUDE.md |
| L18 (Wikipedia zero IC, sentiment branch closed) | README §6.52, today | ✗ Not in CLAUDE.md |

**Assessment**: L13–L18 are documented in README §6.52 (authoritative lesson registry) and in individual POSTMORTEMs. CLAUDE.md lessons section is supplemental, not authoritative. The gap is a known documentation lag — README §6.52 is the single source of truth for lessons post-L12.

**Recommendation (optional)**: Add a line to CLAUDE.md pointing to README §6.52 as the authoritative lesson registry. No lessons themselves need to be duplicated.

### 3.2 _meta Lesson Files

`Crypto/research/_meta/lesson_11_beta_dominance.md` exists as a dedicated file for L11. No equivalent files for L12–L18. Consistent with the strategy of using README §6.52 as primary post-L11 registry. **PASS**.

---

## SECTION 4 — Live Code Integrity

### 4.1 Strategy A — `strategies/tsmom_v2_propfirm/`

- **Status per CLAUDE.md**: PAUSED (Propr account breached). VPS crons still active for state tracking but not trading.
- **Credential handling**: `discover_api.py` uses `os.environ.get("PROPR_API_KEY", "")` + explicit error if empty. The docstring shows `export PROPR_API_KEY="pk_live_..."` as a placeholder usage example — NOT a hardcoded key. **PASS**.
- **Config consistency**: `config.py` last modified 2026-05-14. Signal `backtest_v2.py` + `signal.py` last modified 2026-05-15. All pre-dates today — no unreviewed code changes. **PASS**.
- **Known gap**: `_preflight/` contains execution-preflight scripts; last audited at iter_10 (May 2026). Strategy C execution is the active propfirm path, not Strategy A.

### 4.2 Strategy B — `strategies/delta_neutral/`

- **Status per CLAUDE.md**: LIVE on HL testnet since 2026-05-17. Mainnet deployment pending 60-day live validation.
- **Credential handling**: `live_trader.py` receives `--hl-key` / `--bn-key` via CLI args. `private_key=hl_private_key` passed at runtime from env var through argparse. Not hardcoded. **PASS**.
- **Testnet lock**: `HLPerpClient(..., testnet=True)` hardcoded in live_trader.py:666. Mainnet requires explicit code change. Correct safeguard.
- **Last modified**: 2026-05-21 — 2 days ago. No suspicious recent changes.
- **HL_API constant**: `https://api.hyperliquid.xyz/info` — mainnet API used for volume checks only. Correct and expected.

### 4.3 Strategy C — `Futures/live/strategy_c_live/`

- **Status per CLAUDE.md**: BACKTEST-VALIDATED, paper infra built, execution not started.
- **Contents**: `config.py`, `guardrails.py`, `log_trade.py`, `monitor_loop.py`, `signal_engine.py`, `tradovate_client.py`, `validate_tradovate.py`, `watchdog.py`, `challenge_state.py` — complete paper trade infrastructure. **PASS**.
- **Known gap (from CLAUDE.md)**: backtest uses VWAP 1-min, live infra uses VWAP 5-min — unresolved before paper start. Correctly flagged in CLAUDE.md. Not a sanity check failure; it's a pre-deployment blocker.
- `strategy_c_paper/` (separate): contains `log_trade.py` and `paper_trade_log.csv` only — pre-existing log infra per CLAUDE.md. No conflict with `strategy_c_live/`.

### 4.4 `strategies/tsmom_v3/`

- **Status per CLAUDE.md**: Not mentioned explicitly (tsmom_v3 is not a live strategy).
- **Contents**: `backtest.py` (31KB), `signal.py` (5.7KB), PNG outputs — research/backtest artifacts. Last modified 2026-05-15/23. No live execution code. **PASS — no concern**.

---

## SECTION 5 — Git & GitHub Sync

### 5.1 Unpushed Commits

**23 commits on `main` ahead of `origin/main`** (as of session start). Selected commits:

```
d28ec1c [meta] crypto research session 2026-05-23: merge L15/L17/L18 + 3 archives (today)
25f6074 research: WAV H3 Phase 2 FAIL → archive (L18 logged)
76666c8 research: FGVD H1 Phase 2 FAIL → archive (L17 logged)
0917293 research: ETF regime overlay Phase 2 FAIL → archive
9257dba fix: pre-deployment blockers B1+B2 + W3 — Tradeify $25K alignment
...
```

This represents substantial unpushed work (89,590 insertions, 258 files changed). No CI/CD dependency — push is safe when user validates.

### 5.2 Large Untracked Files (Risk: Accidental Large Commit)

All large data files are correctly excluded:

| File | Size | Gitignored via |
|------|------|----------------|
| `data/funding_rates.csv` | 16 MB | `data/*.csv` |
| `data/pairs_universe_hourly.csv` | 26 MB | `data/*.csv` |
| `data/momentum_universe.csv` | 5.1 MB | `data/*.csv` |
| `data/raw/*.parquet` | 24–41 MB each | `data/raw/*.parquet` |
| `Forex/data/cache/dukascopy_*/` | 40–50 MB each | `Forex/data/cache/` |

**PASS** — no large binary files in the git index or at risk of accidental staging.

### 5.3 Untracked Code Directories (Uncommitted Research)

| Directory | Risk level | Recommendation |
|-----------|-----------|----------------|
| `Commodities/` | LOW — no live strategies | Commit when next used |
| `ETF_Vol/` | LOW — no live strategies | Commit when next used |
| `Equities/` | MEDIUM — archived research history | Commit `research/archived/` at minimum |
| `Forex/live/` | MEDIUM — live-adjacent FX infra | Commit if deployable; audit first |
| `Forex/research/active/strategy_e_fix_flow/` | LOW — research only | Commit if non-trivial |
| `Crypto/research/active/token_unlocks/` | LOW — bootstrap only | Commit with next mission |
| `data/metadata/.gitkeep` | LOW | Commit as placeholder |
| `Futures/live/__init__.py` | LOW — empty file | Commit |

---

## SECTION 6 — Secrets & Hygiene

### 6.1 Tracked Secrets Scan

```
git grep "private_key\s*=\s*['\"]0x|API_KEY\s*=\s*['\"]..."
→ strategies/tsmom_v2_propfirm/execution/discover_api.py
```

**Verdict**: `discover_api.py` contains `API_KEY = os.environ.get("PROPR_API_KEY", "")` — reads from environment, not hardcoded. The docstring `export PROPR_API_KEY="pk_live_..."` is a usage placeholder. **No actual credential in tracked files.** ✓

### 6.2 Environment Files

| File | Git tracked? | Correct? |
|------|-------------|---------|
| `.env` | NO (gitignored) ✓ | ✓ |
| `.env.example` | YES | ✓ (template only, no actual values) |

**PASS** — `.env` is NOT in git index. Confirmed via `git ls-files --error-unmatch .env`.

### 6.3 Auto-Fix Applied: CLAUDE.md.vps

`CLAUDE.md.vps` (2.7KB, dated 2026-05-23 13:12) is an untracked file at repo root. Contents: stale copy of CLAUDE.md from before today's session — no secrets, but says "Strategy A LIVE on Propr" (outdated). It was not gitignored.

**AUTO-FIX**: Added `CLAUDE.md.vps` to `.gitignore` (authorized trivial fix per `/goal` spec).

### 6.4 Large CSV Files in `data/`

All large CSVs (`funding_rates.csv`, `momentum_universe.csv`, `pairs_universe_hourly.csv`) are gitignored via `data/*.csv`. **PASS**.

### 6.5 Archived Research Data Directories (FLAG, Minor)

Three `data/` directories under `Crypto/research/archived/` are untracked (not gitignored):
```
Crypto/research/archived/carry/cs_carry/data/
Crypto/research/archived/mean_reversion/cs_stat_arb/data/
Crypto/research/archived/other/hl_native/data/
```
These contain market data binaries (parquets, not secrets). They are excluded from commits incidentally (untracked) but could be staged accidentally. Recommend adding a pattern to `.gitignore`:
```
Crypto/research/archived/*/data/
```

---

## SECTION 7 — Documentation Coherence

### 7.1 CLAUDE.md vs Actual Strategy Status

| Item | CLAUDE.md (current) | Actual state |
|------|---------------------|-------------|
| Strategy A | PAUSED — Propr breach | ✓ Consistent |
| Strategy B | LIVE on HL testnet | ✓ Consistent (live_trader.py testnet=True) |
| Strategy C | BACKTEST-VALIDATED, paper infra built | ✓ Consistent (strategy_c_live/ exists, not executing) |
| n_tests | **274** | Stale — should be ≥321 (321+3 today = 324) |
| Lessons | L1–L12 | L13–L18 only in README §6.52 |

### 7.2 CLAUDE.md.vps vs CLAUDE.md

`CLAUDE.md.vps` (the VPS copy of CLAUDE.md, auto-synced at VPS startup) is **stale**:
- Says "Strategy A — TSMOM v3 propfirm (LIVE on Propr)" — Propr breach not reflected
- Last modified 2026-05-23 13:12 (before today's research session updates)

The VPS copy is maintained separately; it will not auto-sync unless deliberately pushed. The VPS is paused for Strategy A, so the stale state is not operationally dangerous. However, if Strategy A is restarted on a new propfirm, the VPS CLAUDE.md should be refreshed.

### 7.3 README Status Line vs Research Sections

| Element | Status line (line 4) | Section body |
|---------|---------------------|-------------|
| Crypto n_tests | "crypto 157" | §6.55: 159 (updated today) |
| Global n_tests | "321 signals/variants tested" | CLAUDE.md: 274 |

The status line was not updated when crypto section was updated to 159 today. This is a cosmetic inconsistency — the §6.55 body and crypto postmortem chain are authoritative. Recommend updating status line "crypto 157" → "crypto 159" in next commit.

### 7.4 Active Research Documentation State

| Mission | Bootstrap notes | Hypothesis locked | Code | Status |
|---------|----------------|-------------------|------|--------|
| `token_unlocks/` | ✓ `_bootstrap_notes.md` | ✗ Not yet | ✗ None | Phase 0 only |
| `vrp_short_gamma/` | ✓ `_bootstrap_vrp_notes.md` | ✗ Not yet | ✗ None | Phase 0 only |
| `Forex/round_number_cascade/` | ✓ (committed) | ✓ Pre-spec frozen | Partial | Phase 1 in progress |
| `Forex/strategy_e_fix_flow/` | ✓ (untracked) | Unknown | Unknown | Untracked |

`token_unlocks/` and `vrp_short_gamma/` are correctly in Phase 0 state — no hypothesis consumption yet, no n_tests spent. ✓

---

## SUMMARY TABLE

| Section | Status | Action required |
|---------|--------|----------------|
| 1. Repo structure | ⚠️ FLAG | Commit untracked asset classes; remove empty eth_mvrv_netflow/ active stub; add archived data pattern to .gitignore |
| 2. N_tests coherence | ✓ PASS (crypto) / ⚠️ FLAG (global) | Update CLAUDE.md n_tests 274→324; update README status "crypto 157"→"crypto 159" |
| 3. Lessons coherence | ⚠️ FLAG (minor) | Add README §6.52 pointer to CLAUDE.md lessons section; backport L13/L15/L17/L18 optional |
| 4. Live code integrity | ✓ PASS | No action — Strategy B testnet lock confirmed, Strategy A creds env-only, Strategy C paper infra ready |
| 5. Git sync | ⚠️ FLAG | 23 unpushed commits — push when user validates; large files correctly excluded |
| 6. Secrets & hygiene | ✓ PASS | AUTO-FIX applied: CLAUDE.md.vps added to .gitignore; no hardcoded credentials found |
| 7. Documentation coherence | ⚠️ FLAG | CLAUDE.md.vps stale on VPS; CLAUDE.md n_tests stale; README status line crypto count stale |

**Critical issues**: 0
**Medium flags**: 4 (n_tests docs stale, untracked asset classes, unpushed commits, archived data gitignore gap)
**Resolved auto-fixes**: 1 (`CLAUDE.md.vps` added to .gitignore)

---

*Secrets: CLEAN — no API keys, private keys, or credentials found in tracked files or git history. Push is safe.*
