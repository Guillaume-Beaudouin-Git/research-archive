# FTMO-suitability inventory screen — 2026-05-30

**Trigger** : L24 (added this commit to CLAUDE.md, registre Propfirm) — propfirm
pass-probability is driven by distribution SHAPE, not by account size. Strategy
C plateau 44% empirically confirms (sweep 2026-05-30). Inventory needs to be
re-screened by shape, not by Sharpe alone.

**Method** : every results.json / metrics_*.json / *_baseline.json under
`Crypto/`, `Forex/`, `Equities/`, `Futures/`, `Multi_Asset/`, `Options_Vol/`
(excluding `_frozen/`, `_audit/`) parsed for available shape metrics. NO metric
is fabricated — missing fields stay `N/A`. Strategy C iter_10 anchored from the
daily-PnL moments in `_audit/strategy_c_ftmo10k_sim_results.json` (no engine
re-run).

**Scoring** : 5 components in `[0,1]` averaged on the available subset.

| Component | Floor (s=0) | Target (s=1) |
|---|---|---|
| s_winrate | WR ≤ 30% | WR ≥ 65% |
| s_winloss | win/loss ratio ≥ 2.0 | win/loss ratio ≤ 1.0 |
| s_dsharpe | daily Sharpe ≤ 0 | daily Sharpe ≥ 0.10 |
| s_freq | freq ≤ 0/day | freq ≥ 1 trade/day |
| s_kurt | excess kurt ≥ 6 | excess kurt ≤ 0 |

**Verdict tiers** :
- **FTMO-CANDIDATE** : score ≥ 0.65 AND WR ≥ 55% AND win/loss ≤ 1.5
- **MARGINAL** : score ≥ 0.45
- **LUMPY-UNFIT** : score < 0.45
- **DATA-INSUFFISANT** : fewer than 3 of 5 components available, OR
  n_trades < 100, OR n_days < 250 (L14 sample-floor)

Threshold rationale: strict — a "candidate" must meet ALL of (decent edge per
day, regular grind, ratio ≈ 1). Any laxer threshold lets through lumpy
strategies that we've already empirically shown plateau at ~44% p(pass).

---

## §1. Inventory tableau (verdict tier puis score décroissant)

### Tier MARGINAL (1 entry)

| # | Strategy | Class | N | WR | WL | dSh | freq | kurt | Score | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | nq_intraday/iter_05_D_trail | Futures | 622 | 44% | 1.36 | 0.03 | 0.81 | N/A | **0.526** | MARGINAL |

### Tier LUMPY-UNFIT (43 entries, top 10 shown)

| # | Strategy | Class | N | WR | WL | dSh | freq | kurt | Score | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | nq_intraday/iter_1c | Futures | 747 | 37% | 1.94 | 0.05 | 0.97 | N/A | 0.429 | LUMPY-UNFIT |
| 3 | voie_b_ftmo | Futures | 1885 | 26% | 1.37 | 0.17 | 0.44 | **11.3** | 0.415 | LUMPY-UNFIT |
| 4 | nq_intraday/iter_05_A+C+D | Futures | 622 | 39% | 1.73 | 0.03 | 0.81 | N/A | 0.401 | LUMPY-UNFIT |
| 5 | nq_intraday/iter_05_A$400 | Futures | 622 | 26% | 3.70 | 0.07 | 0.81 | N/A | 0.389 | LUMPY-UNFIT |
| ... | (38 more iterations of nq_intraday family) | ... | ... | ... | ... | ... | ... | ... | ... | ... |
| 35 | **nq_intraday/iter_10 (Strategy C anchor)** | Futures | 346 | **28%** | **3.73** | 0.10 | 0.45 | **44.1** | **0.281** | **LUMPY-UNFIT** ✓ |
| ... | D1, D2, D3 (NQ Strategy D candidates) | ... | ... | ... | ... | ... | ... | ... | ... | LUMPY-UNFIT |

**Sanity check anchor** : Strategy C iter_10 ranks #35 with score 0.281,
verdict LUMPY-UNFIT. Cohérent avec L24 et le plateau 44% mesuré dans
`strategy_c_ftmo_account_sweep_2026-05-30.md` — la calibration est saine.

### Tier DATA-INSUFFISANT (24 entries)

| Strategy | Class | Missing | Note |
|---|---|---|---|
| sector_hothand_propfirm | Equities | WR, WL, freq, kurt | Only sharpe_net + max_dd exposed in baseline JSON. Plus look-ahead audited (engine.py:120). |
| nq_intraday/iter_07_val_YM | Futures | WL, kurt + N=46 | Cross-instrument YM validation, 46 trades in 70 days — viole L14 (N<250 inadmissible). |
| nq_intraday/iter_07_val_ES | Futures | WL, kurt + N=47 | Idem ES, 47 trades en 71 jours. Inadmissible. |
| f2_asian_breakout (FX) | FX | WL, dSh, freq, kurt | "0 backtests" — archived at L11 preflight. |
| nq_intraday/iter_3c | Futures | WL, kurt + N=25 | 25 trades insufficient. |
| multi_asset_tsmom | Equities | WR, WL, freq, kurt | Only sharpe + alpha t in results.json (HAC + excess returns post-correction). |
| nq_intraday/iter_3a, 3b | Futures | kurt + N<100 | Insufficient samples. |
| nq_intraday/D5 | Futures | WL, kurt + N=52 | Strategy D candidate, 52 trades insufficient. |
| etf_regime_overlay, h31_cs_fs_dn, vrp_deribit, fgvd_h1, pmr_basis, wav_h3 | Crypto | tous | results.json contiennent IC/feasibility stats mais pas WR/winloss/freq trade-level. |
| jt_momentum_cs (Equities) | Equities | WR, WL, freq, kurt | Monthly CS portfolio — pas de trades discrets. |
| fx_carry_em, fx_carry_fred, fx_carry_trend, fx_momentum_monthly | FX | WR, WL, freq, kurt | Cross-sectional portfolio metrics, pas de trades discrets. |
| fx_strategy_d_modified_carry, _v2 | FX | tous | Variantes carry. |
| vrp_spx_angle_c | Options | WR, WL, freq, kurt | IC scan stats only. |
| nq_intraday_vwap/iter_01 | Futures | tous + N=19 + look-ahead | INSUFFICIENT SAMPLE flaggé par auteur + bug d'engine audité. |

### Inventaire sans aucune métrique (mentionné mais non scoré)

| Strategy | Class | Statut |
|---|---|---|
| strategy_d (pré-reg) | Futures | Pre-registration document only, no backtest. |
| strategy_d_nq (infra) | Futures | Infra scripts only. |
| cip_eoq | FX | sigma_estimation/ only, no backtest. |
| zn_baltussen | Futures | tests/ + sigma_estimation/, no metrics emitted. |
| token_unlocks | Crypto | Bootstrap notes only. |
| vrp_short_gamma | Crypto | Bootstrap notes only. |
| network_momentum (archived) | Multi-Asset | feasibility_summary.md FAIL E3 SR=0.293 only. |

---

## §2. Synthèse franche

### Y a-t-il AU MOINS UNE candidate crédible ?

**NON.**

- **Tier FTMO-CANDIDATE : 0 stratégie.** Le seuil est strict (WR ≥ 55%,
  win/loss ≤ 1.5, score ≥ 0.65 ; ce sont les minimums dérivés de L24 pour
  ne pas plafonner ~44%).
- **Tier MARGINAL : 1 stratégie** (`iter_05_D_trail`) — mais elle a un
  MaxDD de **-71%** (`max_dd_pct=-0.7076` dans results.json), ce qui
  signifie qu'elle déclencherait le breach max-DD FTMO sur quasiment
  toute fenêtre. Le score 0.526 ignore MaxDD car ce n'est pas dans les 5
  composantes shape ; c'est un faux positif structural.
- Aucune autre stratégie n'a un WR ≥ 55% **avec** ≥ 100 trades **et**
  ≥ 250 jours **et** une distribution non-lumpy. Les variantes
  iter_07_val_YM/ES exhibent WR 76%/64% **mais** sur 46-47 trades en
  70 jours — sample insuffisant (viole L14, donc filtrées en
  DATA-INSUFFISANT).

### Cas spéciaux demandés explicitement

- **voie_b_ftmo** : audit clean (cf. `_audit/engine_contamination_2026-05-30.md`),
  nom contient "ftmo" → présomption de cible FTMO. **Verdict : LUMPY-UNFIT**
  (score 0.415, rang #3 du LUMPY-UNFIT). Profil : WR seulement **26%**,
  win/loss 1.37, daily Sharpe **0.17 (bon !)**, freq 0.44, excess kurtosis
  **11.3 (très lumpy)**. Le bon daily Sharpe est obtenu via un edge concentré
  dans la queue (les big up-gap days US dominent). FTMO 5%/10% pénalise
  exactement ce profil. **Le nom est trompeur** : voie_b_ftmo a été développée
  pour FTMO mais ne respecte pas le profil L24. Probabilité de pass FTMO
  reste à simuler mais structurellement (kurt 11, WR 26) c'est sans appel.

- **Strategy C / iter_10** : rang #35 (score 0.281, LUMPY-UNFIT). **Sanity
  check OK** — la calibration du score reproduit le verdict empirique du
  sweep account-size (plateau 44%, jamais > 50%). C'est le point d'ancrage
  négatif que le user demandait.

- **strategy_d** : pré-registration sans run → DATA-INSUFFISANT.
  `Futures/research/active/strategy_d/hypotheses_preregistered.md` est un
  document de spec, aucun backtest exécuté. Verdict reporté.

- **strategy_d_nq** : infra (manual_signal.sh + plist) → DATA-INSUFFISANT.

- **cip_eoq** : sigma_estimation/ seul → DATA-INSUFFISANT. La phase A
  (CIP dislocation EOQ) n'a pas produit de backtest, juste une étude de
  variance de basis.

- **zn_baltussen** : tests/ + sigma_estimation/ → DATA-INSUFFISANT.

- **nq_intraday_vwap/iter_01** : DATA-INSUFFISANT (N=19 sur 3 ans
  insuffisant + engine look-ahead audité).

### Verdict global

L'inventaire est **vide de candidates FTMO**. Aucune stratégie existante n'a
le profil de distribution requis pour une barrière symétrique 5%/10%.

**Une phase de recherche dédiée est nécessaire pour développer une stratégie
au profil "grind régulier".**

Caractéristiques cibles d'une recherche L24-compatible (ordre de priorité) :
1. **Win-rate ≥ 55%** (idéal 60-65%)
2. **Win/loss ratio ≤ 1.5** (idéal ≈ 1.0)
3. **Daily Sharpe ≥ 0.07** (annualisé ≥ 1.1)
4. **Frequency ≥ 0.5 trade/day** (idéal ≥ 1)
5. **Excess kurtosis ≤ 3** (limite la queue de breach)
6. **MaxDD historique ≤ 6%** (laisse de la marge sous le 10% FTMO floor)

Familles **fines à explorer** :
- Mean-reversion intraday avec exit serré (faible kurt, freq haute)
- Spread/pair trading market-neutral (faible vol, MaxDD contenu)
- Options short straddle delta-hedged avec gap-risk caps (régime-conditional)
- Mais attention aux contraintes L11/L12 (cost-ceiling) — la fee structure
  des futures CME (~$2/MNQ RT) tolère 5-10 trades/jr ; au-delà le cost-drag
  dévore l'edge.

Familles **à éviter** (déjà connues lumpy) :
- TSMOM, breakout-momentum (dont C iter_10), trend-following pure
- Event-driven / earnings-momentum (queue très haute)
- Mean-reversion avec stops larges (drawdown trail)

### Recommandation prochaine étape

**Pas de sim FTMO complète recommandée** sur les top du tableau :

- `iter_05_D_trail` (score MARGINAL 0.526) est disqualifiée par MaxDD -71%.
- `voie_b_ftmo` (LUMPY-UNFIT 0.415) plafonnerait probablement < 30% p(pass)
  vu le kurt 11.3 — simulation possible mais inutile, le profil est
  structurellement inadapté.

**Recommandation forte : ouvrir une recherche dédiée** "L24-compatible
strategy hunt". Pré-spec :
- Universe et timeframe à fixer (intraday liquide : MNQ, MES, MCL, ZN ; ou
  multi-instrument mean-reversion)
- Pré-registration des seuils L24 (WR ≥ 55%, etc.) comme gates avant tout
  développement
- Réutiliser `_audit/strategy_c_ftmo10k_sim.py` puis
  `strategy_c_ftmo_account_sweep.py` (généralisable au nouveau trade log)
  pour valider en amont avant toute décision propfirm

Le pipeline existant (engine, sim, sweep) est mature et réutilisable. Il
manque la **stratégie au bon profil distribution**.

---

## §3. Reproductibilité et fichiers

| Fichier | Rôle |
|---|---|
| `_audit/ftmo_suitability_screen.py` | Script transparent, formule de score documentée |
| `_audit/ftmo_suitability_screen_results.json` | Sortie chiffrée |
| `_audit/ftmo_suitability_screen_2026-05-30.md` | Ce rapport |

Reproduction :
```bash
"<HOME>/Desktop/Unholy returns/Python3.12.9/myenv/bin/python3" \
  _audit/ftmo_suitability_screen.py
```
~5 secondes (lecture seule de fichiers JSON / CSV ; aucune sim).

Note sur calibration : Strategy C iter_10 ressort à score 0.281 / LUMPY-UNFIT,
en cohérence avec la mesure empirique (plateau 44% p(pass) toutes tailles).
Si le score de C remontait au-dessus de 0.45 (MARGINAL), le scoring serait
mal calibré et il faudrait durcir les pondérations (s_winrate ou s_winloss).
Pour l'instant le scoring tient.

L24 (CLAUDE.md `Methodology lessons` → registre Propfirm) ajoutée comme
constitutionnel. Numérotée L24 et non L19 (collision avec NQ market impact
existant) ; note de numérotation incluse dans le texte de la leçon.
