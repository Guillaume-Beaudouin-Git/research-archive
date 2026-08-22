# Rapport stratégie 100/109 — Wyckoff MR (Time Exits) — *court (variante #98)*

**Statut :** ❌ **DISCARD (3/4)** — *étude time-exit sur l'entrée Wyckoff ; ~zéro, ne bat pas le beta.* · **Source :** https://oxfordstrat.com/trading-strategies/richard-wyckoff-mean-reversion-3/ (rating **C**). · **Registre :** #100. · 2026-06-07.

## Résultats (reward désactivé, time/ATR gouverne)
**9 469 trades · win 25,5 % · expR +0,0021 · Sharpe 0,09.** BETA rec 0,17 < BH 1,01. **Gates 3/4 FAIL** (two-sided long-biais + DSR bruit + OOS flip). La sortie temporelle relève l'espérance à ~0 mais reste sous le beta. Cluster Wyckoff {#98,#99,#100} = 3/3 DISCARD ; **toute la famille fade de false-breakout** (False Breakout, Turtle Soup, Reversal Patterns, Wyckoff) = **0 edge** sur l'univers FTMO. 100ᵉ traitée, **100ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s100_wyckoff_time.py`. `ftmo_lab.py` inchangé.
