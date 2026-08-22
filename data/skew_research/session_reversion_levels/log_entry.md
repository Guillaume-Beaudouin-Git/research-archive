# Entrée de log — session_reversion_levels (CANDIDAT, à merger par le mainteneur)
*Candidat de section, périmètre session_reversion_levels uniquement. Numérotation/intégration tranchées au merge. Ne PAS écrire dans le log partagé (collision sessions parallèles). Rien figé. Dédup vs `MR_deepdive_ftmo.md` + `mr_reversal_1d_spx.md` (#5-MR) au merge.*

---

## [2026-06] Skew research — session_reversion_levels (setups réversion discrétionnaires basiques)

**Objectif** : briques skew+ OU anti-trend pour portefeuille L7. Détail : `data/skew_research/session_reversion_levels/exploration_2026-06.md`.

**Résultat : 0 brique retenue.** 5 setups (RSI/Bollinger/MA-rev/Donchian-fade/gap-fill) × 6 instruments daily. Aucun edge (t<2 sauf USDJPY-BB t=2,42 = outlier skew+8,18). Le rejet n'est PAS « skew− » (prior trop fort) mais : (1) pas d'edge, (2) corr-trend ≈0 (décorrélé pas anti-corrélé).

**Trois constats (cœur) :**
- **Signe du skew = fixé par l'EXIT, pas l'entrée** : take-profit→skew−, hold-fixe→neutre/+ (4/4 SP500/GOLD × RSI/BB ; ex. GOLD-BB +0,11→−0,49). Le prior « MR=skew− » ne vaut que pour le style discrétionnaire take-profit.
- **MR daily = décorrélé (~0) au trend, PAS anti-corrélé** (corrTrend médian −0,02). Hypothèse « skew− utile si anti-trend » non matérialisée. Seul gold-MR négatif (−0,25) = mécanique (book_JG contient gold-trend).
- **Two-sided = beta** : jambe longue (dip-buying) porte tout, short ~0 (SP500-BB +1,15/+0,04). Confirme `MR_deepdive` intraday, reproduit au daily.

**Par setup** : RSI skewM −0,12 / BB +0,31 / MA-rev +0,01 / Donchian +0,56 / gap-fill mort (gaps ne mean-revert pas intraday, corr −0,04). Bollinger & Donchian = skew+ léger mais t<1,3 → forme sans alpha.

**Réconciliation** : `MR_deepdive` (intraday, ~350 trials, KILL) ; `mr_reversal_1d_spx` (#5-MR, seule MR à edge+skew+, horizon 1j spécifique, execution-fragile, non reproduit à 5j) ; `IDEA_5B` xsec reversal KILL.

**Candidats-leçons (nommés, à numéroter au merge) :**
- « Le signe du skew d'un setup MR est fixé par l'EXIT, pas l'entrée » (take-profit→−, hold-fixe→neutre/+ ; 4/4).
- « MR daily = décorrélé au trend (~0), PAS anti-corrélé » (décorrélation ≠ anti-corrélation ; le skew− MR ne diversifie pas le trend).
- « Two-sided au daily confirme l'intraday : jambe longue dip-buying = beta, short ~0 ».
- « Les gaps ne mean-revert pas intraday (NQ corr −0,04) » (prémisse gap-fill fausse ; construction open→close propre).
- « Skew+ sans edge ≠ brique » (Bollinger/Donchian skew+ mais t<1,3).

**Statut** : 0 jour live, tout backtest. Réconcilié archive (pas de re-preuve). Coordination : écrit uniquement dans `session_reversion_levels/`, non touché aux autres sessions ni `overnight_research/`. Ne pas merger sans revue mainteneur.
