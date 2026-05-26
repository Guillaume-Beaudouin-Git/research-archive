# VERDICT — Sector Rotation Macro

Date : 2026-05-25
Status : KILL
Sharpe net retail attendu : N/A (edge absent post-costs avec N=11)
Capital minimum requis : N/A
Décorrélation portfolio existant : élevée (macro orthogonal à TSMOM)
Propfirm-fit : non

## Verdict tranché

KILL standalone. L'edge académique (Chava-Hsu-Zeng 2020) est documenté sur un
univers FF-48 (N=48 industries), pas sur 11 SPDR ETFs. Le produit live XLSR
(State Street macro rotation ETF) sous-performe SPY de -249 bps/an depuis 2019,
dégradation accélérée à -507 bps sur le 3Y rolling. Le Fundamental Law of
Active Management rend l'alpha mathématiquement insuffisant à N=11.

## Pourquoi cette conclusion

- **Breadth fatal N=11** : Fundamental Law (Grinold 1989) — expected gross alpha
  ≈ IC × √N × σ_target. À IC=0.05 et N=11 : gross_alpha ≈ 0.05 × √11 × 16%
  ≈ 2.65%/an. Costs ETF (0.10% RT × 12 rebal/an) = 1.2%/an. Net ≈ 1.45%/an,
  Sharpe ≈ 0.15. Non-investissable.
- **Chava-Hsu-Zeng 2020 sur FF-48, pas N=11** : les 14% alpha documentés
  s'appliquent à un univers de 48 industries avec rebalancement mensuel.
  La transposition mécanique à 11 SPDR ETFs détruit le breadth et sur-concentre
  les positions dans des ETFs corrélés (XLF/XLK r=0.62 sur cycle macro).
- **XLSR live falsification** : la performance réelle d'un produit institutionnel
  (AUM $2B+) utilisant exactement cette approche sous-performe l'indice de
  -249 bps/an (2019-2025) et -507 bps sur 3Y rolling. Si les institutions avec
  données alternatives ne peuvent pas extraire l'edge, le retail ne peut pas.
- **Absence de propfirm-fit** : stratégie mensuelle à faible fréquence → trop
  peu de trades pour atteindre le profit target Tradeify en 180 jours.

## Valeur pour CV / Interview

Exemple de falsification rigoureuse d'un edge publié (Chava et al. 2020) sous
contraintes retail réalistes. Démontre la capacité à séparer l'alpha académique
(documenté sur univers propre) de la transposabilité pratique (ETFs retail).
L'utilisation du Fundamental Law comme filtre de breadth avant backtest est
exactement le type de raisonnement recherché par les desks CS de Qube/CFM.

## Conditions de réactivation

- Accès à un univers N ≥ 30 (MSCI secteurs globaux, déclinaison internationale)
  pour restaurer suffisamment de breadth.
- Dataset alternatif (NLP earnings calls, satellite) permettant IC > 0.08 sur
  N=11 — non justifié par la littérature existante.

## Lien vers deep research

[deep_research.md](deep_research.md)
