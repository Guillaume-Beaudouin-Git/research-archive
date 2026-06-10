# Rapport stratégie 76/109 — Ross Hook Pattern (Setup) — **CANDIDAT FORT (flag)**

**Statut :** 🟢 **KEEP — PREMIER KEEP DU PROJET (promu après deep-dive complet).** *Voir le dossier `AUDIT_DOSSIER_S076.md`.* Passe les 4 gates ET le deep-dive niveau-S060 : **anti-look-ahead OK** (robuste au délai+2/+3/+5), **alpha significatif sur données FTMO réelles (t=4,0)** — le test que #60 échouait —, distinct du beta marché (β≈0) et du beta tendance (corr TSMOM 0,11), **persistant en récent**, robuste aux coûts (+10 bps). · **Source :** https://oxfordstrat.com/trading-strategies/ross-hook-1/ (Joe Ross, rating **C**). · **Registre :** #76. · 2026-06-07.

> ✅ **PREMIER KEEP (1/80).** Continuation de breakout court terme. Cadrage honnête : ~60 % = prime de breakout-momentum générique, ~40 % = sélectivité du hook. Réserves : forex faible (retirer), part commodités en données proxy (revalider), effet lent (hook précis non critique). Détail complet : `AUDIT_DOSSIER_S076.md`.

> 🔔🔔 **ON S'ARRÊTE ET ON SIGNALE FORT** (instruction permanente). Une continuation de tendance qui passe les 4 gates, **bat le beta**, **n'est pas du beta marché (β≈0), n'est pas du beta tendance (corr TSMOM 0,11), et survit en récent (2019-2026)**. C'est le candidat le plus solide des 76 stratégies.

## Spec & archétype
**Ross Hook (Joe Ross), continuation de tendance, deux côtés** : après la cassure d'un pattern 1-2-3 (jambe d'au moins `Min_Setup` barres), le prix forme une **première correction** (le « hook ») ; on place un **buy stop au-dessus du plus-haut du hook** (long) / sell stop sous le plus-bas (short). Reprise de la tendance = entrée. Sorties : quick-stop (plus-bas/haut du hook), stop ATR×6, sortie temporelle. Réf. Min_Setup=10, Max_Hook=20 barres, Time=10. Moteur `rosshook.simulate_rosshook`.

## Gates — `results/s076_gates.csv` (0/4 FAIL = KEEP)

| # | Gate | Résultat | Verdict |
|---|------|----------|---------|
| 1 | Délai+1 | Sh +1,78 → **+1,53** (open[i+1]) | ✅ PASS — survit au fill réaliste |
| 2 | Two-sided | long +0,066 / short **+0,021** | ✅ PASS — les deux côtés positifs |
| 3 | DSR | 2,63 > 1,78 | ✅ PASS |
| 4 | OOS | +0,043 → **+0,049** | ✅ PASS — s'améliore |

*(Sharpe ci-dessus = trade-séquentiel ; MaxDD séquentiel −79 % = artefact de la métrique, cf. ci-dessous le vrai DD.)*

## Test décisif — mark-to-market + facteur tendance (la leçon S060 + RSI2)
Série quotidienne **mark-to-market** (close-to-close, pas de R étalé), fill délai+1, régressée sur le marché **et** un facteur **time-series momentum 12 mois (CTA)** :

| Mesure | Valeur |
|---|---|
| **Sharpe MTM portefeuille** | **0,96** (vs trade-séq 1,53) |
| **MaxDD réel** | **−6,0 %** (pas −79 %) · skew **+2,32** |
| alpha ann. vs marché | +4,5 % · **β = −0,02** · **t_NW = +5,2** · Sharpe couvert 1,02 |
| **alpha vs marché + TSMOM** | **+4,6 % · t_NW = +5,4** · charge TSMOM 0,03 · **corr(TSMOM)=0,11** |
| Sous-période 2000-2009 | Sharpe couvert 1,06 (t 3,2) |
| Sous-période 2010-2018 | Sharpe couvert 0,93 (t 3,1) |
| **Sous-période 2019-2026** | **Sharpe couvert 1,05 (t 2,9) — TOUJOURS VIVANT** |

**Lecture :** β marché ≈ 0, **non spanné par la tendance** (corr 0,11 ; alpha t=5,4 *après* contrôle marché+TSMOM), **stable sur les 3 sous-périodes y compris récente**. C'est exactement ce qui a manqué à #60 (mort en MTM/réel) et à RSI2 (décayé post-2009). **Contrôle propre :** le SMA dual classique (#80) **ÉCHOUE** (beta long, DISCARD) sur le même univers → l'edge vient de la **sélectivité du hook**, pas de « la tendance marche ici ».

## Verdict
🟢 **CANDIDAT KEEP — flag fort.** Continuation de tendance sélective (achat de la reprise après la première correction d'une jambe), **alpha distinct** (β marché ≈0, β tendance ≈0, t_NW 5,4), **drawdown maîtrisé (−6 %)**, **skew positif (+2,3)**, **persistant en récent**. Survit au délai+1 et aux 4 gates.

**Réserves avant KEEP définitif (humilité S060) — à traiter en deep-dive :**
1. **Audit anti-look-ahead / ré-implémentation indépendante** : le moteur de détection du hook est non trivial → re-coder de zéro pour exclure tout biais.
2. **Par classe + données FTMO réelles** : vérifier que l'edge n'est pas concentré sur les commodités-proxy (yf) ; revalider sur OHLC réel (indices déjà réels).
3. **Côté short faible en MTM** (long-dominé) ; exposition/capacité/turnover/sensibilité aux coûts (gros gagnants à queue → coûts d'exécution).
4. **Plateau de la grille** : l'expR croît avec Max_Hook (fenêtre) → confirmer un plateau, pas un bord de grille.

**→ Recommandation : DEEP-DIVE complet (dossier niveau S060) avant KEEP définitif.** C'est le meilleur résultat du projet à ce stade.

## Repro
`cd oxfordstrat_109/code && python strat_s076_ross_hook.py` (gates) ; audit MTM/tendance = méthode `s060_audit.py` appliquée à `rosshook.simulate_rosshook(..., daily=True)`. `ftmo_lab.py` inchangé (9dea332).
