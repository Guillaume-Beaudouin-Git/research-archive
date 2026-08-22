# Skew research — session_reversion_levels (setups de réversion discrétionnaires basiques)
### Exploration 2026-06. Objectif : briques skew+ OU anti-corrélées au trend pour portefeuille L7.
*Analyste libre (univers/params/horizons choisis). Prior assumé : MR = skew− typiquement → mauvais profil. Mais (a) certaines implémentations donnent skew+, (b) un skew− fortement anti-trend serait utile. Ne pas tuer le skew− d'office — flaguer + regarder corr-trend.*

---

## Méthode (choix d'analyste)
- **Univers** : SP500, NAS100, DAX, GOLD, USDJPY, EURUSD (daily, xs_universe 2000-2026) — 6 instruments liquides, 3 classes d'actifs, pour robustesse cross-instrument (pas de cherry-pick mono-actif).
- **5 setups** : RSI(14) <30/>70 ; Bollinger(20,2) ; MA-rev z(SMA50)>1,5 ; S/R = Donchian20-fade (long au plus-bas 20j, short au plus-haut) ; Gap-fill (NQ open→close).
- **Signal T-1 → trade T**, hold-fixe 5j (version systématique des setups discrétionnaires).
- **Mesures** : skew à l'**horizon mensuel** (pas daily), t, SR, **corr au sleeve trend `book_JG`** (J=USDJPY-trend + G=gold-trend, equal-risk), two-sided (jambe long vs short).
- **Expérience-exit** : take-profit-au-MA vs hold-fixe, pour isoler l'effet de l'exit sur le signe du skew.
- **Réconciliation archive** (cite, pas re-prouve) : `MR_deepdive_ftmo.md` (~350 trials intraday), `mr_reversal_1d_spx.md` (#5-MR), `IDEA_5B_xsec_reversion.md`.

## Résultats — médiane cross-univers par setup

| setup | skewM (méd) | corrTrend (méd) | t (méd) | edge ? | profil |
|---|---:|---:|---:|---|---|
| RSI(14) | −0,12 | −0,03 | +0,32 | ✗ | skew~0, décorrélé |
| **Bollinger(20,2)** | **+0,31** | +0,01 | +1,22 | ✗ (t<2) | **skew+ léger**, décorrélé |
| MA-rev z(SMA50) | +0,01 | −0,02 | +0,32 | ✗ | neutre |
| **S/R Donchian20-fade** | **+0,56** | −0,01 | +0,87 | ✗ (t<2) | **skew+**, décorrélé |
| Gap-fill (NQ) | +0,58 | ~0 | +0,13 | ✗ | premise fausse (voir infra) |

**Cellule la moins pire** : USDJPY-BB t=2,42 SR 0,46 — mais skewM **+8,18** = outlier-driven (1-2 mois), non robuste. Écartée (skew aberrant + t modeste = quelques réversions chanceuses, pas un edge).

## Trois constats nets (le cœur du livrable)

**1. Le signe du skew d'un setup MR est fixé par l'EXIT, pas par l'entrée.** Expérience-exit (per-trade, SP500 & GOLD) :

| | HOLD-fixe 10j (skew) | TAKE-PROFIT au MA (skew) |
|---|---:|---:|
| SP500 RSI | −0,42 | **−1,00** |
| SP500 BB | +0,26 | +0,01 |
| GOLD RSI | +0,66 | +0,08 |
| GOLD BB | +0,11 | **−0,49** |

**4/4 : le take-profit rend le skew plus négatif que le hold-fixe.** Le prior « MR = skew− » est vrai pour le style **discrétionnaire take-profit** (gagne petit souvent, perd gros rarement) — mais la version **systématique hold-fixe** donne skew **neutre-à-positif** (capture la bounce occasionnelle = queue droite). Le profil de skew est donc un **artefact de la règle d'exit**, pas une propriété de l'entrée.

**2. Les MR daily sont DÉCORRÉLÉS du trend (~0), PAS anti-corrélés.** corrTrend médian −0,01 à −0,03, individuelles ∈ [−0,25 ; +0,03]. Le seul négatif notable (GOLD, −0,13/−0,25) est **mécanique** (book_JG contient G=gold-trend, donc gold-MR fade le gold-trend). → **L'hypothèse (b) ne se matérialise pas** : ces setups sont *indépendants* du trend, pas *opposés*. Un sleeve skew− MR ne fournit donc PAS l'autocorrélation négative recherchée — la décorrélation, on l'a déjà en abondance (cf. cross-asset) ; l'anti-corrélation, non.

**3. Two-sided = confirmation du diagnostic archive (beta déguisé).** La jambe longue porte tout, la jambe short ~0 : SP500-BB +1,15/+0,04 ; NAS100-BB +2,04/+0,07 ; SP500-Donchian +2,03/−0,94. C'est du **dip-buying dans une tendance haussière = beta**, exactement le verdict `MR_deepdive_ftmo.md` (« la jambe gagnante = drift directionnel de la période ») — **reproduit au daily** (l'archive était intraday).

## #5 Gap-fill — prémisse fausse
`corr(gap, r_rth open→close) = −0,036` → les gaps **ne mean-revert PAS** intraday sur NQ (la prémisse du gap-fill est quasi-nulle). gap-fade −sign(gap)·r_rth : mu +0,21bp, **t=0,13** (mort) ; conditionnel |gap|≥Q90 : t=0,30. **Look-ahead check propre** (corr gap/return = −0,04, pas de contamination) — distinct de l'artefact « gap-fade » intraday-timing attrapé plus tôt dans le projet ; ici la construction open→close est honnête et simplement sans edge.

## Réconciliation archive (cité, non re-prouvé)
- **`MR_deepdive_ftmo.md`** (~350 trials, RSI/SMA-z/EMA-z/VWAP/range-fade, intraday 5-30m) : pas d'alpha MR two-sided/delay/OOS/DSR-robuste sur FTMO ; filtre décisif = two-sided (jambe gagnante = beta). **Mon batch (daily + lentille skew/corr-trend) confirme le diagnostic two-sided au daily** ; angle neuf = profil skew + corr-trend, pas FTMO-pass.
- **`mr_reversal_1d_spx.md`** (#5-MR, personal_book) : reversal **1-jour** SPX = la SEULE MR à edge réel (t=3,61, skew+0,71) MAIS spécifique à l'horizon 1j et exécution-fragile (délai+1 effondre). **Non reproduit ici à 5j** : l'edge ultra-court décaye avant 5j → cohérent, pas contradictoire.
- **`IDEA_5B_xsec_reversion.md`** : reversal cross-sectionnel = KILL (signal faible, forme tradeable non-compliant, version long-only = beta cost-killed).

## VERDICT FINAL (session_reversion_levels)
**0 brique L7 retenue.** Mais le rejet n'est PAS « parce que skew− » (le prior est trop fort — hold-fixe donne skew neutre/+) ; il tient à deux raisons distinctes :
1. **Pas d'edge** : t<2 sur tous les setups robustes (USDJPY-BB = outlier) — confirme l'archive ~350-trials, au daily aussi.
2. **corr-trend ≈ 0, pas << 0** : décorrélés mais pas anti-corrélés → même un sleeve skew− ne diversifierait pas le trend comme espéré (hypothèse (b) non matérialisée).

→ La seule MR à edge réel + skew+ reste le **reversal 1-jour** (#5-MR, déjà au personal_book, execution-fragile). La famille « setups discrétionnaires basiques à 5j » n'ajoute rien : profil souvent correct (skew neutre/+, décorrélé) mais **forme sans alpha** — le même piège que credit-momentum (batch cross-asset).

## Candidats-leçons (NOMMÉS, pas numérotés — tranché au merge)
- **« Le signe du skew d'un setup MR est fixé par l'EXIT, pas l'entrée »** — take-profit→skew− (style discrétionnaire classique), hold-fixe→skew neutre/+ (4/4 SP500/GOLD × RSI/BB). Toujours spécifier l'exit avant de juger le profil de skew d'une MR.
- **« MR daily = décorrélé au trend (~0), PAS anti-corrélé »** — un sleeve skew− MR ne fournit pas l'autocorrélation négative au trend (corrTrend médian −0,02, indép. pas opposé). Décorrélation ≠ anti-corrélation (rappel cross-asset). Le seul négatif (gold-MR) est mécanique (même actif dans book_JG).
- **« Two-sided au daily confirme l'intraday : la jambe longue (dip-buying=beta) porte tout »** — short-leg ~0 sur tous les setups ; l'« edge MR » apparent est du beta de marché haussier. `MR_deepdive` reproduit au daily.
- **« Les gaps ne mean-revert pas intraday (NQ corr −0,04) »** — prémisse gap-fill fausse, edge nul ; construction open→close propre (≠ l'artefact gap-fade intraday-timing).
- **« Skew+ sans edge ≠ brique »** — Bollinger/Donchian skew+ médian (+0,31/+0,56) mais t<1,3 ; forme sans alpha non allouable (rappel credit-momentum #3).

---
*session_reversion_levels, 5 setups × 6 instruments (+ NQ gap). Données : xs_universe (daily 2000-2026), book_JG (trend benchmark), nq_intraday_panel (gap). Tout backtest, 0 jour live. Réconcilié archive (MR_deepdive intraday, mr_reversal_1d_spx #5-MR, IDEA_5B xsec — pas de re-preuve). Rien figé, rien mergé. Écrit uniquement dans ce périmètre ; non touché aux autres sessions ni overnight_research/. Dédup vs MR_deepdive + #5-MR au merge.*
