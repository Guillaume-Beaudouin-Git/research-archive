# Rapport stratégie 34/109 — Friday Momentum / "One Night Stand" (Filter)

**Statut :** ❌ **DISCARD (2/4)** — *effet week-end ; le « bat le beta » apparent est un ARTEFACT de fill (délai+1 inverse).* · **Source :** https://oxfordstrat.com/trading-strategies/short-term-trading-friday-momentum/ (Krutsinger, rating **D**). · **Registre :** #34. · 2026-06-07.

## Spec & archétype
**Saisonnalité (effet week-end)** : entrée **uniquement le vendredi**, buy stop au-dessus du plus-haut 4 j (en tendance MA haussière, Fast10>Slow40), **tenu sur le week-end, sortie au close/open du lundi** (« One Night Stand »). Sweep `Slow_MA × Long_Entry_LB`. `ftmo_lab`+`beta_bench` inchangés. Point Slow=40, Long_LB=4.

## Résultats + chiffres décisifs (réf. Slow=40, Long_LB=4)
**6 695 trades · win 53,3 % · expR +0,0089 · PF 1,208 · Sharpe 1,03 · MaxDD −28,2 %.** Grille 100 % positive.

> **DÉLAI+1 (DÉCISIF) :** natif(stop) Sharpe **+1,03** → fill réaliste open[i+1] **−0,21** (expR +0,009 → −0,002). **→ INVERSION = artefact de fill intrabar** (le buy-stop du vendredi se remplit dans la barre).
> **TWO-SIDED :** long +0,0085 / short +0,0098 → PASS (les deux côtés positifs).
> **BETA-MATCHED :** strat rec **+1,65** vs buy&hold **+1,01** → « bat le beta »… **mais sur les chiffres NATIFS (artefact)**. Au fill réaliste, l'edge disparaît.

## Gates — `results/s034_gates.csv` (2/4 FAIL)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | +1,03 → **−0,21** | ❌ **artefact de fill** |
| 2 | Two-sided | long +0,009 / short +0,010 | ✅ PASS |
| 3 | DSR | 1,27 < 1,52 | ❌ FAIL |
| 4 | OOS | +0,009 → +0,009 | ✅ PASS |

## Verdict
❌ **DISCARD (2/4).** Cas d'école : un effet week-end **two-sided + OOS-positif** qui semble même **battre le beta** — mais le **délai+1 révèle l'artefact de fill** (buy-stop intrabar). Au fill réaliste, −0,21. La fiche confirme : *« a cessé de fonctionner depuis 1993 une fois les coûts réalistes appliqués ».* **Démontre que le 5ᵉ test (beta-apparié) ne suffit pas seul — il faut le combiner au délai+1**, sinon un artefact de fill passe pour de l'alpha. 34ᵉ traitée, **34ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s034_friday_momentum.py` (dépend de `beta_bench`). `ftmo_lab.py` inchangé.
