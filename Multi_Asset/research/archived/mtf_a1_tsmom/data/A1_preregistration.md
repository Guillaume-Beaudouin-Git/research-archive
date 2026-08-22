# A1 — Diversified Multi-Horizon Time-Series Momentum — Pre-registration

**Horodatage de gel** : 2026-06-05T22:57:54Z (UTC) — avant toute donnée téléchargée pour cet archétype.
**Auteur** : Claude (Opus 4.7), mission utilisateur "MISSION — Falsifier l'archétype A1".
**Survey** : MTF, archétype #1.
**Statut** : FROZEN. Toute analyse confirmatoire ajoutée APRÈS l'exécution sera rejetée.

---

## 1. Référence académique
- Moskowitz, Ooi, Pedersen (2012), "Time Series Momentum", JFE 104.
- Hurst, Ooi, Pedersen (2017), "A Century of Evidence on Trend-Following Investing", JPM.
- Sanity réelle live : SG Trend Index Sharpe live ≈ 0.42 sur 2000-2023, à comparer à ≈ 1.0 backtest. Tout résultat backtest >> 1.0 net est suspect.

## 2. Univers (4 classes, ~25 contrats) — yfinance continuous futures, tier feasibility
- **Equity index** : `ES=F`, `NQ=F`, `YM=F`, `RTY=F`
- **Bonds / rates** : `ZT=F`, `ZF=F`, `ZN=F`, `ZB=F`
- **FX** : `6E=F`, `6J=F`, `6B=F`, `6A=F`, `6C=F`, `6S=F`
- **Commodities** : `CL=F`, `NG=F`, `GC=F`, `SI=F`, `HG=F`, `ZC=F`, `ZW=F`, `ZS=F`, `KC=F`, `SB=F`

Règle d'inclusion : `historique propre >= 8 ans`. Tout instrument retiré est listé dans le rapport.
Flag rapport : yfinance roll opaque → caveat explicite, **tier feasibility**, pas production.

## 3. Spec figée du signal (aucun tuning)
- Vol ex-ante par instrument : `σ_i = rolling_std(r_i_daily, 63) × √252`, **laguée 1 jour**.
- Horizons : k ∈ {21, 63, 252} jours (≈ 1, 3, 12 mois).
- Sub-signal : `s_k_i = sign(prod(1+r_i_{t−k+1..t−1}) − 1)` (i.e. signe du return cumulé sur k jours, **arrêté à t−1**).
- Signal combiné : `S_i = mean(s_21, s_63, s_252) ∈ {−1, −1/3, +1/3, +1}`.
- Position instrument : `pos_i = S_i × σ_target_inst / σ_i` (σ_target_inst égal pour tous, fixé pour viser ~10 %/an si toutes les positions étaient orthogonales — calibration fixée a priori).
- Vol-targeting portefeuille (2e étage) : scale tous les poids pour viser **10 % vol annualisé ex-ante** (vol réalisée trailing 63 j du portefeuille, laguée 1 j).
- Rebalance **mensuelle** : signal au dernier jour de bourse du mois t−1, position tenue tout le mois t. Garantit L1 (signal à T-1, trade à T) au niveau mensuel.

## 4. Coûts & métriques
- Coût RT futures : **1.5 bps** par unité de turnover notionnel (futures ~1 bp L9 + slippage 0.5 bp). Coût de BASE, pas stress.
- Pas de stop, pas de cap MAE.
- Returns : returns de prix directement (futures collatéralisés ≈ excess returns).
- Métriques nettes : Sharpe ann., MaxDD, vol réalisée, skew, kurtosis, pire mois, turnover annuel moyen, hit-rate.
- Significativité : alpha avec t HAC Newey-West lag-6 ; PSR(0.5) ; DSR avec n_tests survey.

## 5. Tableau des hypothèses (figé)

| # | Hypothèse | Test | Seuil PASS |
|---|---|---|---|
| **H2 (DÉCISIVE)** | Le trend ajoute du Sharpe au-delà du long vol-managé | OLS `r_TSMOM ~ α + β·r_BH`, t HAC lag-6 | **alpha > 0 ET t_HAC > 1.5** |
| H1 | Signal trend existe (pas un artefact de t-stat de panel) | Régression panel poolée `r_{i,t} ~ sign(mom_{i,t-1})`, block-bootstrap stationnaire bloc ≈ 12 m, 5000 tirages sur le coef | **t_empirique > p95 de la null bootstrap** (Huang-Li-Wang-Zhou 2020 JFE 135) |
| H3 | Sharpe net > 0.5 crédible | PSR(SR\*=0.5) sur returns NETS du portefeuille, ajusté skew/kurtosis | **PSR > 0.95** |
| H4 | Edge bilatéral (L25) | Split mois par direction du signal (long vs short), mean return net par jambe | **les DEUX jambes mean > 0** net coûts |
| H5 | Survie post-décay (drought 2010+) | Sous-échantillon 2010-01-01 → fin, Sharpe net | **Sharpe net > 0.3** (sinon : décay confirmé, à rapporter, pas un fail bloquant) |

**Verdict global** : A1 DÉFENDABLE ssi `H1 ∧ H2 ∧ H3`. H4/H5 qualifient la robustesse.

## 6. Cross-check obligatoire
Corrélation portefeuille TSMOM répliqué vs facteur AQR "Time Series Momentum" mensuel (téléchargé). Reporté en en-tête de rapport.
**Si corr < 0.6 → build invalide. Stopper et débugger avant de publier les autres tests.**

## 7. Ablations (toutes mêmes coûts, même vol-targeting, même univers)
1. **TSMOM** : signal {1/3/12} ci-dessus.
2. **BuyHold (BH)** : `S_i ≡ +1`, sinon identique → benchmark H2.
3. **RandomSign (RS)** : `S_i ∈ {−1, +1}` iid, identique sinon. 500 seeds → distribution Sharpe. TSMOM positionné dans cette distribution → percentile rapporté.

Hidden-factor : OLS `r_TSMOM ~ α + β_eq·r_ES + β_BH·r_BH` (HAC lag-6).

## 8. Stabilité régime
- ≥5 segments consécutifs de la timeline, Sharpe net par segment.
- Sous-échantillon post-2010 explicite (H5).
- Spec FIGÉE → c'est un test de stabilité régime, pas un walk-forward de tuning.

## 9. Garde-fous
- Aucun fill same-bar (rebal mensuel laguée).
- Pas de cap MAE.
- Slippage en coût de base.
- Pas de stop.
- Vérifie hidden-factor leak (étape 3 du test).
- Spec figée : un résultat décevant se rapporte tel quel, ne se "fix" pas.

## 10. Livrables
1. `code/mtf/a1_tsmom_multihorizon.py` (engine, seed fixée).
2. `outputs/mtf/a1_returns.parquet` (returns mensuels nets des 3 portefeuilles).
3. `outputs/mtf/a1_per_market_stats.parquet` (Sharpe / t-stat par instrument, pour H1).
4. `data/mtf_survey/A1_diversified_tsmom_report.md` (rapport structuré).

## 11. n_tests survey
Tracker dans `data/mtf_survey/_n_tests.json`. A1 = test #1.

— EOF —
