# Rapport stratégie 60/109 — Oops Pattern Bullish (Exits)

**Statut :** 🟡 **BORDERLINE — RÉTROGRADÉ de KEEP (Sharpe gonflé par artefact de méthode).** *Voir le dossier d'audit complet `AUDIT_DOSSIER_S060.md`.* — *gap-down-fade long-only ; edge par trade réel mais petit ; **Sharpe mark-to-market réel ~0,7 (pas ~3)**, alpha couvert-beta NON significatif sur données propres (indices, t=0,61).* · **Source :** https://oxfordstrat.com/trading-strategies/bull-oops-pattern/ (Larry Williams, rating **C**). · **Registre :** #60. · 2026-06-07.

> ⚠️ **CORRECTION (audit du 2026-06-07).** Le deep-dive précédent annonçait Sharpe 2,9–3,1 / beta≈0 / KEEP : **erreur de méthode** (PnL quotidien construit par R *étalé* sur la détention → vol écrasée 1,1 % vs 3,4 % réels → Sharpe ×3 et beta biaisé vers 0). Recalcul **mark-to-market** : **Sharpe 0,70 brut / 0,41 couvert-beta** (déployable, délai+1) ; **alpha non significatif sur indices (données propres)**. Ce qui tient : **edge par trade positif** (expR +0,031 R indices, IC95 [+0,014;+0,050]>0). **Validé sur données FTMO réelles** (`Algo_claude/data` : indices vrai OHLC + or M1 2007+ + crypto) : edge par trade confirmé MAIS **alpha couvert-beta NON significatif (t_NW=0,61 indices / 0,79 déployable)** ; le marginal venait de commodités proxy non validables. **Effet réel mais trop faible pour être exploité seul — ne satisfait pas KEEP.** Détail : `AUDIT_DOSSIER_S060.md` §11-12. *(Le `AUDIT_S060_deepdive.md` antérieur est conservé mais ses Sharpe 2,9–3,1 sont obsolètes.)*

## Spec & archétype
**Gap-down-fade (« Oops » de Larry Williams), long-only** : si Open[i] < Low[i−1] (gap baissier), buy stop au **reclaim de Low[i−1]** (le gap échoue → rebond). Sortie Time + stop ATR×ATR_Index. Réutilise `s058` (side='long'). Point ATR_Index=3, Time=10.

## Résultats + chiffres décisifs (réf. ATR_Index=3, Time=10)
**3 750 trades · win 55,5 % · expR +0,0568 · PF 1,392 · Sharpe 1,56 · MaxDD −65,6 %.**

> **DÉLAI+1 :** natif **+1,56** → fill réaliste open[i+1] **+1,10** (expR +0,057 → +0,040). **→ PASS : vrai edge, pas un artefact** (reclaim-stop à un niveau réel).
> **DSR :** SR **1,593 > 1,519** → **PASS** (grille significative).
> **OOS :** train +0,0525 → test **+0,0610** → **PASS** (s'améliore récemment).
> **BETA-MATCHED :** full Sh 1,56 vs BH 0,74 ; **rec Sh 1,64 vs BH 1,01 → BAT le beta.**

## Gates — `results/s060_gates.csv` (1/4 FAIL)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | +1,56 → **+1,10** | ✅ PASS — vrai edge |
| 2 | Two-sided | long +0,057 / short N/A | ❌ FAIL — **par construction (long-only)** |
| 3 | DSR (N=9) | **1,593 > 1,519** | ✅ **PASS** |
| 4 | OOS | +0,053 → **+0,061** | ✅ PASS |

## Verdict
🟡 **BORDERLINE / candidat fort.** Le gap-down-fade long capture une **réversion overnight réelle** : après un gap baissier sous le plus-bas de la veille, le reclaim de ce plus-bas précède un rebond. Il **survit au fill réaliste** (délai+1 +1,10), **passe la DSR** (1,59 — rare !), **s'améliore en OOS**, et **bat le buy&hold always-in** (rec 1,64 vs 1,01). Le seul gate échoué (two-sided) l'est **par construction** (pattern unidirectionnel).

**Réserves (anti-sur-crédit, leçon S012) avant tout KEEP :**
- **MaxDD −66 %** : le fade achète des gaps baissiers → *attrape des couteaux qui tombent* en krach. À vol-targeter / filtrer.
- **Long-only** : à confronter à un buy&hold **apparié en exposition** (pas seulement always-in) et à mesurer l'alpha-timing régime-apparié — exactement le test qui avait corrigé S012.
- DSR N=9 (grille modeste).

**→ Recommandation : DEEP-DIVE #60** (exposition/vol-apparié, walk-forward, par classe, alpha-vs-neutre, contrôle du −66 % DD) avant de trancher KEEP vs DISCARD. C'est le meilleur candidat du projet à ce stade.

## Repro
`cd oxfordstrat_109/code && python strat_s060_oops_bull.py` (dépend de s058 + beta_bench). `ftmo_lab.py` inchangé. Code : `code/strat_s060_oops_bull.py`.
