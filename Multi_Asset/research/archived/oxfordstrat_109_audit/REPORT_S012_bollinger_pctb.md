# Rapport stratégie 12/109 — Bollinger Bands %b (Test : Setup) — **1ᵉʳ mean-reversion**

**Pipeline :** `ftmo_lab v2-gates`. **Statut :** ❌ **DISCARD (1/4)** — *mais cas le plus intéressant du pipeline : 1ʳᵉ à passer Gate 1 ET Gate 2.* · **Source :** https://oxfordstrat.com/trading-strategies/bollinger-bands-reversal/ (Connors, rating **D**). · **Registre :** #12. · 2026-06-05.

---

## 0. LES DEUX CHIFFRES DÉCISIFS (en tête, comme demandé)

> **DÉLAI+1 (L26) :** natif `open[s+1]` **Sharpe +0,74** (expR +0,0153) → réaliste `open[s+2]` **Sharpe +0,42** (expR +0,0081) ; `close[s+1]` Sharpe +0,50. **→ survit (Gate 1 PASS).**
> **TWO-SIDED (L25) :** long expR **+0,0242** (n=2628) | short expR **+0,0038** (n=2035). **→ les deux côtés positifs (Gate 2 PASS — une première).**

| Gate | Résultat | Verdict |
|---|---|---|
| 1 — Délai+1 | +0,74 → +0,42 (survit) | ✅ **PASS** |
| 2 — Two-sided | long +0,0242 / short **+0,0038** | ✅ **PASS** (1ʳᵉ fois) |
| 3 — DSR (N=20) | best Sharpe **0,967** ≪ E[max] 1,871 ; z −29,6 | ❌ **FAIL** |
| 4 — OOS | train +0,0267 (Sh +1,18) → test +0,0054 (Sh +0,29) | ✅ **PASS** |

**VERDICT automatique : DISCARD (1/4, échoue seulement le DSR).**

---

## 0bis. Lecture honnête (double-check effectué)

C'est la **première stratégie qui n'est ni un artefact de fill (Gate 1) ni du beta long déguisé (Gate 2)** : un vrai mean-reversion. Win rate **68,6 %** (signature MR). Et — fait notable — **signature inverse du cluster trend** : les **indices et le FX portent** (US500 +0,06, GBPUSD +0,06, US100 +0,06, EURUSD +0,04), la **crypto perd** (ETH −0,02, BTC −0,03). Le dip-buy mean-revert marche là où ça range (indices/FX), pas là où ça trend (crypto). Cohérent.

**MAIS le double-check tempère fortement :**
1. **Bootstrap par blocs (config canonique MA5/SD1) :** expR +0,0153, **IC 95 % [+0,0073 ; +0,0232] → significatif** (ne traverse pas zéro). Donc le **DSR (qui déflate sur 20 cellules) et le bootstrap (config unique) sont en désaccord** : au réglage canonique de Connors (non grid-searché), l'edge est réel ; sur la grille, il est noyé. Le DSR est ici **conservateur** (cellules corrélées → N effectif ≪ 20).
2. **La symétrie Gate 2 est FRAGILE :** le short n'est positif (**+0,0038**, PF 1,04) **qu'à la cellule canonique** MA5/SD1. À MA20/40/60, le short **perd** (−0,04 à −0,06, PF 0,80-0,96). En **OOS** (≥2016), le short **flippe négatif** (long +0,016 / short **−0,008**). ⇒ Le Gate 2 passe *de justesse et localement* ; la partie robuste est le **long dip-buy** (qui est en partie du beta long).

**Synthèse :** un **vrai edge MR mais mince et asymétriquement fragile** — le long dip-buy (indices/FX) est solide, le short rip-sell est marginal et décroît OOS. Le DSR le rejette (multiplicité) ; le bootstrap le valide au canonique. **C'est le premier vrai candidat-limite du pipeline.**

---

## 1. Spécification (reproduite fidèlement)
**Connors %b mean-reversion.** Bandes : `MA=SMA(close, MA_Length)`, `Upper/Lower = MA ± St_Dev·std`, `%b=(Close−Lower)/(Upper−Lower)`. Filtre de tendance `MA_Trend=SMA(close,200)`.
- **Setup Long :** `Close[i−1]>MA200[i−1]` ET `%b<0,2` sur i−1,i−2,i−3 (creux survendu en uptrend).
- **Setup Short :** `Close[i−1]<MA200[i−1]` ET `%b>0,8` sur i−1,i−2,i−3 (sommet suracheté en downtrend).
- **Entrée :** market-on-open à `i`. **Sortie :** *Trend Exit* (long : %b>0,8 au close ; short : %b<0,2 au close) **ou** stop ATR(20)×6.
- **Sensibilité :** `MA_Length [5,60] × St_Dev [0,5 ; 3,0]`. Défauts Connors : MA_Length=5, St_Dev=1.

Écarts vs site idem S001-S011 (univers FTMO 30, R-multiples, coûts FTMO).

## 2-4. Univers / données / coûts / look-ahead (partagés)
Identiques. Setup sur `i−1`, entrée `open[i]`, `risk0=ATR[i−1]×6`. Sans look-ahead. %b/MA200 cachés par `(instrument, MA_Length, St_Dev)`.

## 5. Archétype & moteur
> **🔑 Archétype = MEAN-REVERSION trend-alignée, entrée MARKET-ON-OPEN.** Ni stop intrabar (≠ S001/S006), ni fill-on-close (≠ piège close-print) : l'entrée à `open[i]` est déjà décalée d'une barre du signal `i−1`. **Gate 1** teste `open[s+1]` vs `open[s+2]` (+ `close[s+1]`). **Gate 2** est LE juge : dip-buy (long) vs rip-sell (short) doivent marcher **tous deux**.

Sim **`simulate_meanrev`** dédiée (sortie sur retour de %b au close + stop ATR ; une position à la fois). Réutilise `ftmo_lab` v2-gates (coûts, `trade_metrics`, 4 gates, `atr`, `RISK_FRAC`). Mapping fills : `'stop'`=open[s+1] natif, `'next_open'`=open[s+2], `'close'`=close[s+1].

## 6. Paramètres
`MA_Trend=200` · `MA_Length` {5,10,20,40,60} (réf. **5**) × `St_Dev` {0,5 ; 1,0 ; 1,5 ; 2,5} (réf. **1,0**) = **20 cellules** · `ATR` 20/6 · `RISK_FRAC` 0,5 %.

## 7. Résultats
**Réf. (MA5/SD1) :** 4 663 trades · **win 68,6 %** · expR +0,0153 · PF 1,172 · Sharpe 0,74 · MaxDD −34,5 % · 16/30 positifs.
**Par instrument (`results/s012_per_instrument.csv`) :** **top = indices + FX** (US500, GBPUSD, US100, US2000, EURUSD, US30) ; **bas = crypto + qq FX** (USDJPY, ETHUSD, NZDUSD, BTCUSD, USDCHF). **Signature MR inverse du trend.**
**Sensibilité (`results/s012_sensitivity.png`) :** 100 % positif, mais **les cellules à grand expR (MA60/SD2.5 +0,17) sont sparse ET long-dominées** (short négatif) ; la cellule canonique (MA5/SD1) est la plus symétrique mais à expR modeste. Tous Sharpe ≤ 0,97 → DSR.

## 8. Gates — détail (`results/s012_gates.csv`)
- **Gate 1 PASS** : +0,74 → +0,42 (open s+2) / +0,50 (close s+1). Le MR ne dépend pas d'une exécution intra-jour irréaliste.
- **Gate 2 PASS (fragile)** : long +0,0242 / short +0,0038 au canonique ; **mais short négatif aux autres cellules et en OOS** (cf. §0bis).
- **Gate 3 DSR FAIL** : best Sharpe 0,967 < E[max] 1,871 (N=20), z −29,6. *Caveat : conservateur (cellules corrélées) ; le bootstrap de la config canonique est, lui, significatif (IC [+0,007 ; +0,023]).* 
- **Gate 4 OOS PASS** : test +0,0054 (Sh +0,29), positif, pas de flip global — mais porté par les longs (short OOS −0,008).

## 9. Verdict & disposition
**DISCARD (1/4, DSR)** au sens strict du pipeline. **Mais c'est le candidat-limite le plus sérieux jusqu'ici :** 1ʳᵉ à passer Gate 1+Gate 2, bootstrap-significatif au canonique. Ce qui le retient : **DSR (multiplicité)** + **short MR mince et qui décroît OOS** (la robustesse vient surtout du long dip-buy, partiellement beta).
**Pistes (si on approfondit) :** (a) isoler le **long dip-buy sur indices/FX** comme sleeve MR et le comparer à un buy&hold timé ; (b) voir si la **#13 (Bollinger %b Setup & Filter)** — variante avec filtre — renforce/assainit le short ; (c) vol-targeting (MaxDD −34 %).

## 10. Reproduction
`cd oxfordstrat_109/code && python strat_s012_bollinger_pctb.py` (Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3 ; matplotlib 3.10.8 ; pyarrow 24.0.0). Le bloc « deux chiffres décisifs » s'affiche en tête de la console. Moteur `ftmo_lab.py` partagé/inchangé. Code faisant foi : `code/strat_s012_bollinger_pctb.py`.
