# Rapport stratégie 13/109 — Bollinger Bands %b (Test : Setup & Filter)

**Pipeline :** `ftmo_lab v2-gates`. **Statut :** ❌ **DISCARD-watchlist** (comme #12) — *hypothèse « le filtre assainit le short » **rejetée***. · **Source :** https://oxfordstrat.com/trading-strategies/bollinger-bands-reversal-2/ (Connors, rating **D**). · **Registre :** #13. · 2026-06-05.

---

## 0. LES 4 CHIFFRES DÉCISIFS (cellule canonique MA5 / MA_Trend200 = **identique au #12**)

> 1. **DÉLAI+1 :** natif `open[s+1]` **Sharpe +0,74** (expR +0,0153) → `open[s+2]` **Sharpe +0,42** (expR +0,0081). ✅ **PASS**
> 2. **TWO-SIDED :** long **+0,0242** (n=2628) | short **+0,0038** (n=2035). ✅ **PASS**
> 3. **ALPHA-vs-BETA :** long dip +0,0242 vs neutre +0,0053 → **alpha +0,0189** ; short pop +0,0038 vs neutre −0,0081 → **alpha +0,0119**. → vrai MR bilatéral.
> 4. **WALK-FORWARD (Sharpe) :** **1,52 → 1,63 → 0,51 → 0,21** (2000→2026) ; short par bloc **+0,022 / +0,040 / −0,019 / −0,006**. → décroissance + short mort post-2012.

| Gate (canonique) | Résultat | Verdict |
|---|---|---|
| 1 Délai+1 | +0,74 → +0,42 | ✅ PASS |
| 2 Two-sided | long +0,0242 / short +0,0038 | ✅ PASS |
| 3 DSR (N=20) | best Sharpe 0,858 ≪ 1,871 | ❌ FAIL |
| 4 OOS | train +0,0267 → test +0,0054 | ✅ PASS |

**VERDICT : DISCARD (1/4, DSR)** — strictement identique au #12 (la cellule canonique est la même).

---

## 0bis. LE TEST DE L'HYPOTHÈSE (la seule chose nouvelle vs #12)

**Question :** la #13 balaye `MA_Trend_Length` ([80,250], #12 le fixait à 200). **Un autre `MA_Trend` récupère-t-il le short fragile / ralentit-il le décay ?**

| `MA_Trend` | long | short (full) | **2018+ Sharpe** | **2018+ short** |
|---|---|---|---|---|
| 80 | +0,0266 | −0,0064 | −0,14 | −0,0166 |
| 120 | +0,0242 | −0,0040 | −0,01 | −0,0117 |
| 160 | +0,0274 | +0,0001 | +0,19 | −0,0107 |
| 200 (#12) | +0,0242 | +0,0038 | +0,21 | −0,0056 |
| 250 | +0,0256 | +0,0052 | **+0,33** | −0,0035 |

**Réponse : NON.** Le **short reste négatif en régime récent (2018+) à TOUTES les longueurs de filtre** (−0,017 à −0,0035). Un `MA_Trend` plus long (250) ralentit *un peu* le décay global (2018+ Sharpe 0,33 vs 0,21), **mais uniquement parce que le LONG dip-buy porte** — le short MR ne revient jamais. Le meilleur Sharpe récent (0,33) reste **< 0,5** et **non two-sided** (short récent négatif).

⇒ **Hypothèse rejetée.** Le filtre (longueur de tendance) n'assainit pas le short et ne sauve pas le régime récent. Cohérent avec le prior « les filtres ont dégradé 0/5 fois » : ici le filtre est **neutre** (légèrement utile au long, nul pour le short mort).

---

## 1. Spécification (vs #12)
**Mean-reversion %b de Connors, setup IDENTIQUE au #12** (`Close vs MA_Trend` + `%b<0,2`/`>0,8` ×3 jours, entrée open, sortie retour %b + ATR). **Seule différence :** sensibilité **`MA_Length × MA_Trend_Length`** (`St_Dev=1` fixe), au lieu de `MA_Length × St_Dev` (#12). `MA_Trend_Length ∈ [80,250]`. Voir `REPORT_S012 §1` pour le détail %b. Écarts vs site idem.

## 2-6. Univers / données / coûts / archétype / paramètres
Identiques au #12 (`REPORT_S012 §2-§6`). Réutilise `strat_s012.pctb`, `simulate_meanrev`, univers, coûts, et `ftmo_lab` v2-gates. Grille **MA_Length {5,10,20,40,60} × MA_Trend {80,150,200,250}** = 20 cellules (St_Dev=1). Réf. MA5/MA_Trend200.

## 7. Résultats & sensibilité
**Réf. (MA5/MT200) :** identique #12 — 4 663 trades, win 68,6 %, expR +0,0153, Sharpe 0,74, MaxDD −34,5 %.
**Sensibilité MA_Length × MA_Trend (`results/s013_sensitivity.png`) :** majoritairement positive ; expR croît avec MA_Length (cellules longues sparse, MA60/MT80 +0,12 = peu de trades). `MA_Trend` a un effet de second ordre (cf. §0bis). Tous Sharpe ≤ 0,86 → DSR FAIL.

## 8. Gates
Identiques au #12 (la cellule canonique est la même) : Gate 1 ✅, Gate 2 ✅, **Gate 3 DSR ❌** (best Sharpe 0,86 < 1,87 ; N=20), Gate 4 ✅. **DISCARD (1/4).** Le bootstrap de la config canonique reste significatif (cf. audit #12) ; le DSR (multiplicité) tranche DISCARD.

## 9. Verdict & disposition
❌ **DISCARD-watchlist**, **strictement comme le #12** : c'est le **même alpha MR réel mais décayé** ; le filtre (MA_Trend) testé ici **ne le répare pas**. Le short reste structurellement mort post-2012 quel que soit le filtre.
- **Conclusion sur l'archétype Bollinger %b :** confirmé **réel mais décayé et non réparable par le filtre de tendance**. Exploitable seulement en **long-biais indices, vol-targeté**, en combinaison — pas en solo (cf. `AUDIT_S012`).
- **Suite :** l'archétype Bollinger est clos (#12+#13). Le **Doji (#16/#17)** est un archétype MR **mécaniquement distinct** (chandelier de retournement, pas écart à une bande) — à tester **à fond et séparément** : il pourrait être un MR moins décayé.

## 10. Reproduction
`cd oxfordstrat_109/code && python strat_s013_bollinger_filter.py` (les 4 chiffres + le test du filtre s'affichent en tête). Env : Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3. Dépend de `strat_s012_bollinger_pctb.py` (même dossier). Moteur `ftmo_lab.py` partagé/inchangé. Code faisant foi : `code/strat_s013_bollinger_filter.py`.
