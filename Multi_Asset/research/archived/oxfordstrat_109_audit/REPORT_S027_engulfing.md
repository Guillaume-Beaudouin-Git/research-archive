# Rapport stratégie 27/109 — Bearish Engulfing Candlestick (Exits) + archétype du cluster Engulfing

**Statut :** ❌ **DISCARD net (4/4)** — *short perdant d'origine ; le pattern n'a pas d'alpha de reversal. Établit l'archétype du cluster Engulfing (#27-#30).* · **Source :** https://oxfordstrat.com/trading-strategies/pattern-bearish-engulfing/ (rating **D**). · **Registre :** #27. · 2026-06-06.

> **Découverte clé :** les « engulfing candlestick » d'oxfordstrat **ne sont PAS des mean-reversion à l'entrée close** — l'entrée est l'**ORB-stop de Crabel** (`Open ∓ Stretch`, Stretch = SMA(noise,10)×2), juste filtrée par un pattern d'absorption. Même famille que S001/S002/GSV. J'ai donc testé : (1) la jambe short fidèle, (2) le système **bilatéral combiné**, (3) une **décomposition pure-pattern** (le pattern prédit-il un reversal, sans ORB ?).

## LES 2 CHIFFRES DÉCISIFS (en tête)

> **DÉLAI+1 (combiné) :** natif Sharpe **−0,55** (expR −0,073) → fill réaliste **−0,08** (expR −0,012). **→ négatif des deux côtés (pas d'edge à fiabiliser).**
> **TWO-SIDED (combiné) :** long **−0,0031** (n=2083) / short **−0,1500** (n=1882). **→ les DEUX côtés perdent ; le short est catastrophique.**

## Décomposition décisive — le pattern a-t-il un alpha de reversal ?
**Rendement forward 10 j du *pur pattern* (entrée au close, sans ORB, net de coûts) :**
- **Bullish engulfing → long : +0,37 %** (n=4383) — ≈ la simple dérive haussière du marché sur 10 j (du **beta**, pas de l'alpha de reversal).
- **Bearish engulfing → short : −0,44 %** (n=3782) — **négatif** : après un bearish engulfing le prix tend à *monter*, donc shorter perd.

→ **Le pattern engulfing ne prédit aucun reversal exploitable** sur cet univers. Le bullish ne capte que le beta ; le bearish est à contre-sens de la dérive.

## Résultats (réf. Target=3, Time=10)
Jambe **short (#27)** : **1 882 trades · win 24,1 % · expR −0,1500 · PF 0,806 · Sharpe −0,80 · MaxDD −77,8 %.** Perdant dès le fill optimiste.
Jambe **long (#28)** : expR −0,003 (quasi nul). **Combiné** : expR −0,073, Sharpe −0,55.

## Gates — système bilatéral combiné — `results/s027_gates.csv` (4/4 FAIL)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | −0,55 → −0,08 | ❌ FAIL (négatif) |
| 2 | Two-sided | long −0,003 / short −0,150 | ❌ FAIL — deux côtés perdants |
| 3 | DSR | best Sharpe 0,12 ≪ 1,52 | ❌ FAIL |
| 4 | OOS | train −0,069 → test −0,075 | ❌ FAIL |

`edge_pos=False` → **DISCARD net.**

## Verdict
❌ **DISCARD net (4/4).** Le bearish engulfing short est **perdant d'origine** (−0,15 R, win 24 %) : il combine l'absence d'alpha de reversal du pattern **et** le combat à contre-sens de la dérive haussière. La décomposition prouve que le pattern engulfing **n'a pas d'edge de reversal** (le bullish ≈ beta, le bearish perd). 27ᵉ traitée, **27ᵉ DISCARD**. **3ᵉ archétype de bougie testé (après Doji) — les patterns de bougie ne portent pas d'edge exploitable ici.**

## Suite
**#28** (bullish, jambe long), **#29** (Type A, pattern plus strict), **#30** (Type A + filtre dip = contre-tendance) — tous héritage de cet archétype.

## Repro
`cd oxfordstrat_109/code && python strat_s027_engulfing.py` (module partagé du cluster). Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3. `ftmo_lab.py` inchangé. Code : `code/strat_s027_engulfing.py`.
