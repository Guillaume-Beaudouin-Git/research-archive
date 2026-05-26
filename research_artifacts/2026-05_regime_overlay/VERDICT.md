# VERDICT — Regime Overlay

Date : 2026-05-25
Status : NO-GO (portfolio complet) / CONDITIONAL GO (Strategy A standalone)
Sharpe net retail attendu : ΔSharpe +0.04 sur portfolio A+B+C (marginal)
Capital minimum requis : $0 (overlay, pas de capital additionnel)
Décorrélation portfolio existant : N/A (overlay, pas une stratégie)
Propfirm-fit : oui (regime filter Strategy C via VIX/VVIX possible)

## Verdict tranché

NO-GO pour le portfolio complet A+B+C. Le lift attendu (+0.04 sur Sharpe 2.24)
est inférieur au bruit d'estimation — indétectable sur une durée de vie raisonnable.
CONDITIONAL GO pour Strategy A standalone : le regime overlay HMM/JM peut réduire
les drawdowns extrêmes (-6.9% → potentiellement -5%) mais Asness 2016 et AQR
confirment que sur un Sharpe déjà > 1.0, le lift marginal ne justifie pas la
complexité ajoutée.

## Pourquoi cette conclusion

- **L15 confirmée empiriquement** : les regime overlays sur stratégies hauts-Sharpe
  (SR > 1.0) produisent un lift sub-threshold (≈1.7%/an, Δ = +0.022%/jour).
  Asness-Frazzini-Israel 2016 (AQR) : value+momentum overlays ne survivent pas
  aux transactions costs dans un portefeuille déjà diversifié.
- **Shu-Mulvey 2024** : regime conditioning améliore les portefeuilles à MaxDD >
  20% mais n'apporte rien de significatif pour MaxDD < 10% (notre cas A+B+C).
- **Bruit d'estimation dominant** : ΔSharpe +0.04 sur une période de 3 ans
  implique un t-stat ≈ 0.6 — indétectable statistiquement. Nécessite 40+ ans de
  données pour un test de puissance adéquat.
- **Complexité non justifiée** : ajout HMM/JM = 3-5 paramètres supplémentaires,
  risque d'overfitting sur 3 ans de données A (L10 : 3 modifications max).

## Valeur pour CV / Interview

Exercice méthodologique de haut niveau : HMM (Hamilton 1989), Kalman filter,
CPCV, DSR. Démontre la capacité à coupler une technique ML (régimes cachés) avec
une validation statistique rigoureuse et à conclure "non" malgré un résultat
techniquement positif (+0.04). Les desks buy-side (CFM, AQR Paris) valorisent
explicitement la capacité à ne pas sur-optimiser.

## Conditions de réactivation

- Strategy A MaxDD dépasse -15% sur un drawdown live réel → réévaluer l'overlay
  comme protection tail risk (objectif différent : réduction DD, pas lift SR).
- Nouvelles données live ≥ 3 ans supplémentaires pour atteindre puissance
  statistique suffisante (t > 1.65).

## Lien vers deep research

[deep_research.md](deep_research.md)
