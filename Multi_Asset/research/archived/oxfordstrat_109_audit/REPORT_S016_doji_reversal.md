# Rapport stratégie 16/109 — Doji Pattern Reversal / Counter-Trend (Setup & Filter)

**Pipeline :** `ftmo_lab v2-gates`. **Statut :** ❌ **DISCARD (4/4)** — *2ᵉ archétype mean-reversion testé à fond ; échec net (ne marche pas).* · **Source :** https://oxfordstrat.com/trading-strategies/doji-countertrend-1/ (rating **D**). · **Registre :** #16. · 2026-06-05.

---

## 0. LES 4 CHIFFRES DÉCISIFS (réf. Body_Index=0,10, Trend_Index=10)

> 1. **DÉLAI+1 :** natif `stop` **Sharpe −0,60** (expR −0,0161) → `open[s+2]` **Sharpe −0,93** (expR −0,0232) ; `close[s+1]` Sharpe −1,05. → **négatif même au fill optimiste**, pire au réaliste. ❌
> 2. **TWO-SIDED :** long expR **+0,0115** (n=1981) | short expR **−0,0393** (n=2361). → short saigne, long à peine positif. ❌
> 3. **ALPHA-vs-BETA :** long doji +0,0115 vs candle **normale +0,0211** → **alpha −0,0096** ; short doji −0,0393 vs normale −0,0247 → **alpha −0,0145**. → **le Doji a un alpha NÉGATIF** (pire qu'une bougie quelconque dans le même contexte contre-tendance). ❌
> 4. **WALK-FORWARD (Sharpe) :** **−1,07 → +0,10 → −1,18 → −0,61** ; short/bloc tous négatifs. → n'a **jamais** marché. ❌

| Gate | Résultat | Verdict |
|---|---|---|
| 1 Délai+1 | −0,60 → −0,93 (open s+2) | ❌ FAIL |
| 2 Two-sided | long +0,012 / short −0,039 | ❌ FAIL |
| 3 DSR (N=20) | best Sharpe **−0,271** ≪ 1,871 | ❌ FAIL |
| 4 OOS | train −0,0156 → test −0,0165 | ❌ FAIL |

**VERDICT : DISCARD (4/4, `edge_pos=False`).** Pooled : 4 342 trades, **win 17,7 %**, expR −0,0161, PF 0,867, Sharpe −0,60, MaxDD −38,2 %, 8/30 positifs. **Grille de sensibilité 100 % négative.**

---

## 0bis. Réponse à la question clé (Doji = MR moins décayé que Bollinger ?)

**NON.** Le Doji counter-trend **ne marche pas du tout** — c'est un **échec net**, bien plus franc que le Bollinger (qui, lui, avait un alpha MR réel mais décayé). Trois constats décisifs :
1. **Edge négatif même au fill optimiste** (Sharpe −0,60) : ce n'est pas un edge décayé, c'est une stratégie **perdante** dès l'origine.
2. **Le pattern Doji a un alpha NÉGATIF** (−0,010 long, −0,015 short) : la bougie d'indécision est un **moins bon** signal d'entrée contre-tendance qu'une bougie normale. Le candlestick **soustrait** de la valeur.
3. **N'a jamais fonctionné** (walk-forward négatif sur 3 blocs / 4 ; short négatif à toutes les cellules et en régime récent).

⇒ **L'hypothèse « le candlestick pourrait être un MR moins arbitragé » est rejetée pour cet archétype.** Le **Bollinger %b reste le seul alpha MR réel** trouvé (décayé). 

**Mécanisme (négatif rigoureux) :** l'entrée est un **buy stop au-dessus du Doji** *après une baisse* (contre-tendance). On parie donc sur un rebond en achetant sa **cassure haussière** — mais ces cassures contre-tendance **échouent ~5 fois sur 6** (win 17,7 %). Le Doji combine trois handicaps : (a) pattern bruité (indécision), (b) **entrée sur stop intrabar** (artefact + slippage), (c) **timing contre-tendance** sur breakout. Les trois se cumulent en une stratégie perdante.

---

## 1. Spécification (reproduite fidèlement)
**Pattern recognition (candlesticks), counter-trend.** Setup **Doji** : `|Close[s]−Open[s]| / (High[s]−Low[s]) ≤ Body_Index`. Filtre **contre-tendance** : Long si `Close[s] < Close[s−Trend_Index]` (Doji après baisse) ; Short si `Close[s] > Close[s−Trend_Index]`. **Entrée STOP** : buy stop 1 tick au-dessus du High du Doji (long) / sell stop sous le Low (short). **Sorties :** Time(20) | Quick stop (extrême 2 barres autour de l'entrée) | ATR(20)×6. Sweep `Body_Index [0,0.3] × Trend_Index [1,40]`. Écarts vs site idem S001-S015.

## 2-5. Univers / données / coûts / archétype
Identiques. **Archétype = mean-reversion contre-tendance à ENTRÉE STOP** (mécaniquement distinct du Bollinger : chandelier vs écart à une moyenne). Sim `simulate_doji` dédiée. Réutilise `ftmo_lab` v2-gates. Mapping fills (stop-entry) : `'stop'`=niveau Doji (optimiste), `'next_open'`=open[s+2], `'close'`=close[s+1] — le **Gate 1 teste précisément l'artefact de fill** du reversal court terme.

## 6. Paramètres
`Body_Index` {0,05 ; 0,10 ; 0,20 ; 0,30} (réf. 0,10) × `Trend_Index` {1,5,10,20,40} (réf. 10) = **20 cellules**. `Time_Index=20`, `ATR` 20/6, `RISK_FRAC` 0,5 %.

## 7. Résultats
Réf. : 4 342 trades, **win 17,7 %**, expR −0,0161, Sharpe −0,60, MaxDD −38,2 %. **Sensibilité : toutes les cellules négatives** (−0,005 à −0,026). **Par instrument :** seuls quelques commodities/indices marginalement positifs (XPTUSD +0,11, AUS200 +0,06) ; majorité négative (8/30 positifs) — pas de poche exploitable.

## 8. Gates
**4/4 FAIL** ; `edge_pos=False` → DISCARD direct. Gate 1 (artefact fill) **et** Gate 2 (asymétrie) **et** DSR **et** OOS échouent — la stratégie est perdante sous tous les angles.

## 9. Verdict & suite
❌ **DISCARD net (4/4).** Le Doji counter-trend est une **stratégie perdante** (pas un edge décayé). Conséquences :
- **#17 (Doji Reversal — Filter & Exit)** est une variante du **même** counter-trend Doji → très probablement **héritage** (rapport court) sauf divergence.
- **Doji – Trend (#18/#19)** est un usage **DIFFÉRENT** (Doji dans le sens de la tendance, pas contre) → archétype distinct, à tester séparément (probablement trend/héritage).
- **Bilan mean-reversion (3 testés) :** Bollinger %b = alpha réel mais décayé (watchlist) ; Doji counter-trend = échec net. **Le seul candidat MR reste le Bollinger long-biais indices.**

## 10. Reproduction
`cd oxfordstrat_109/code && python strat_s016_doji_reversal.py` (les 4 chiffres décisifs + robustesse short + walk-forward s'affichent en tête). Env : Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3 ; matplotlib 3.10.8. Moteur `ftmo_lab.py` partagé/inchangé. Code faisant foi : `code/strat_s016_doji_reversal.py`.
