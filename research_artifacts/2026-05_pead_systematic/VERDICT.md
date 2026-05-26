# VERDICT — PEAD Systematic

Date : 2026-05-25
Status : KILL (vanilla) / DÉFERRED (variante ML)
Sharpe net retail attendu : 0.45–0.65 (ML 12-Q SUE elastic-net uniquement)
Capital minimum requis : $20K+ (ETF/futures sur indices sectoriels) + $50/mo data
Décorrélation portfolio existant : faible (corr positive avec Strategy C, +0.15–0.35)
Propfirm-fit : non (faible fréquence trades, événements post-earnings)

## Verdict tranché

KILL pour le PEAD vanilla. Martineau 2022 ("Rest in Peace PEAD") documente la
disparition complète de l'effet sur les 5 dernières années sur actions US.
La seule variante crédible — ML 12-Q SUE avec elastic-net (Kaczmarek-Zaremba
2025) — affiche un Sharpe net 0.45-0.65, mais présente une corrélation positive
avec Strategy C (+0.15-0.35) qui en fait un mauvais décorrélateur pour le
portfolio existant. Déféré jusqu'à obtention du dataset Tier 2 (FMP ou WRDS).

## Pourquoi cette conclusion

- **Martineau 2022 "Rest in Peace PEAD"** : méta-étude sur 1975-2021 montrant
  que l'effet PEAD vanilla est entièrement arbitragé depuis 2014-2016. Les
  hedge funds et market makers ont absorbé l'anomalie. Continuation post-earnings
  sur 3-5 jours → rendement espéré ≈ 0 net de bid-ask.
- **Ball-Brown 1968 → horizon décroissant** : l'edge original documentait une
  dérive sur 60 jours post-annonce. Sur données récentes, la dérive se concentre
  sur le jour J+1 uniquement (microstructure efficiente). Coûts RT > edge résiduel.
- **Corrélation positive avec C (+0.15-0.35)** : les deux stratégies réagissent
  favorablement aux tendances momentum intraday (NQ ORB et PEAD convergent sur
  les earnings de grandes caps tech). Mauvais diversificateur pour un portfolio
  où C représente déjà 22% ERC.
- **Données Tier 2 requises** : SUE (Standardized Unexpected Earnings) sur 12
  trimestres glissants nécessite accès FMP ($50/mo) ou WRDS académique. Absent
  des sources gratuites disponibles.

## Valeur pour CV / Interview

Démontre la veille littérature récente : citer Martineau 2022 pour clore la
question PEAD vanilla, puis pivoter vers Kaczmarek-Zaremba 2025 pour la variante
ML moderne, est exactement le niveau d'actualité attendu pour un poste quant M2.
La capacité à rejeter une anomalie historique (Ball-Brown 1968) sur la base
d'une méta-étude récente signal une posture empirique et non doctrinaire.

## Conditions de réactivation

- Accès dataset FMP (~$50/mo) ou WRDS via université pour construire SUE 12-Q.
- Validation que corr(PEAD_signal, Strategy_C_signal) < 0.10 sur données récentes
  2020-2025 avant de consommer le budget n_tests.

## Lien vers deep research

[deep_research.md](deep_research.md)
