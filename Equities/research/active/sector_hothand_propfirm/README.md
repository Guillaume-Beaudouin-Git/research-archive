# Sector Hot-Hand Momentum — Propfirm Challenge (FTMO 2-Step)

## Mandat

Reproduire et auditer un rapport LLM proposant une stratégie momentum sectoriel
cross-sectionnel « hot-hand » pour passer le challenge FTMO 2-Step.

**Prior bayésien : FAIBLE** — rapport non auditable, chiffres potentiellement fabriqués.
Protocole : audit données → baseline sans overlay → enrichissement progressif → décision.

Session Claude.ai : `claude/sector-hothand-phase0` (branch origin, 2026-05-28)

---

## Univers & spec stratégie (du rapport — NE PAS MODIFIER)

| Paramètre | Valeur |
|---|---|
| Actifs | QQQ, XLK, XLE, XLP, XLU, XLV, XLF, XLI, XLB, XLY (10 tickers) |
| Signal | Momentum 20j cross-sectionnel (close-to-close log-ret) |
| Action | Long unique actif au plus fort momentum si > 0, sinon cash |
| Vol scaling | Target 0.15 ann / realized 40j, cap 3× |
| Stop journalier | 1.2% sur rendement non-levered |
| Gap fill | Si open < entry × (1 − 0.012), exécuté à open |
| Coûts | 8 bp/trade × levier (modèle rapport — challangé Phase 4) |
| Signal timing | T-1 close → T open (L1 conforme) |
| Capital | 100 000 $ (standard FTMO) |
| Période backtest | 2002-01-01 → 2026-05-27 (burn-in 2000-2001) |

---

## Phases avec gates stop-loss

### Phase 0 — Audit données (current)
- Fetch OHLCV (Open, Close, AdjClose) via `data/cache.py`
- Vérifier : shape, missing %, premier/dernier jour, tail gaps, autocorrélation
- **Gate** : >5% missing OU start > 2001-01-01 → STOP, reporter avant de continuer
- Output : `results/data_audit.md`

### Phase 1 — Baseline sans overlay
- Engine idempotent (seed fixé) : daily returns nets, equity, DD, levier
- Full sample 2002-2026 + WF 5 folds (expanding train, test 2 ans)
- Bootstrap stationnaire 10 000 iter pour CI Sharpe
- AMTP sur 6 combos lookback × vol_target
- Simulation P(pass) FTMO 2-Step (10 000 paths MC)
- **Gate** : sharpe_deflated < 0.7 → ARCHIVE | p_pass_ci95[0] < 0.50 → ARCHIVE
- Output : `results/phase1_baseline.{json,png,md}`

### Phase 2 — Overlay HMM (conditionnel Phase 1 pass)
- Regime filter VIX ou HMM 2-états
- Re-simulation P(pass) FTMO
- **Gate** : lift Sharpe < 5% → inutile (L15 validé)

### Phase 3 — Timer / drawdown guardrails (conditionnel Phase 2 pass)
- Overlay trailing DD FTMO-aware
- Stress test gap open 3× baseline slippage

### Phase 4 — Réalisme coûts
- Challenger le modèle 8bp/jour × levier avec market-impact ETFs
- ETF liquidity check : spread + ADV

---

## Constitutional checks (appliqués à chaque phase)

| Règle | Description |
|---|---|
| **L1** | Signal T-1 close, trade T open. NO EXCEPTIONS. |
| **L2** | Walk-forward ≥ 5 folds + AMTP si n_tests > 1 |
| **L8** | Excess returns vs DTB3, HAC Newey-West lag-6, vol target 63j, AMTP/DSR |
| **L10** | Max 3 modifications post-baseline (overfitting guard) |
| **L15** | Overlay sur SR > 1.0 : lift < 5%/an — ne valide Phase 2 que si MaxDD > 20% |
| **L19** | Ablation vs baseline rescalé avant tout overlay |
| **L20** | DSR Bailey-LdP mandatory si N_mod ≥ 2 |
| **L21** | Sharpe reality check : single-instrument day-trade SR ∈ [0.8, 2.0] sustainable |

---

## Décision finale

```
sharpe_deflated_DSR ≥ 0.7  AND  p_pass_2step_ci95[0] ≥ 0.50
→ RESEARCH_PASS (continuer Phase 2)
→ sinon ARCHIVE (ne pas acheter challenge FTMO)
```
