# Candidat — Mean-Reversion 1j SPX (reversal)

> **Statut** : Phase-2 partielle. Skew+ confirmé mais **délai+1 effondre l'edge** → exécution close-print non capturable sans validation open→close. Non-déployable en l'état.
> **Source canonique** : `data/skew_research/session_vol_tail/exploration_2026-06.md` (#5-MR).

## Mécanisme

Reversal court-terme : −sign(rendement SPX veille) joué sur le jour suivant. Hypothèse littérature : autocorrélation négative 1j de l'indice (cohérent avec McLean-Pontiff 2016, dip-buying intraday).

## Métriques mesurées

| Métrique | Valeur |
|---|---:|
| n (daily SPX, 2000-2026) | 8097 |
| Mean daily | +5,4 bp |
| Hit rate | 52 % |
| **Skew daily** | **+0,59** (+0,71 sur fenêtre commune 2018-2026) |
| t (raw) | **+3,61** |
| SR (raw) | 0,70 |
| corrEQ | +0,15 |

### Barrières (phase 2)

| Barrière | Verdict |
|---|---|
| **Coût (L33)** | OK : SR 0,70 → 0,57 → 0,43 → 0,29 à 0/1/2/3 bp. ES futures (~0,5-1 bp) → SR ~0,57-0,43. |
| **Délai+1 (L26)** | ❌ **EFFONDRE** : SR 0,57 → **0,08**. Signal ultra-court ; load-bearing = exécution **immédiate au close**. Risque artefact bid-ask bounce close-to-close non capturable. |
| **Two-sided (L25)** | Long-après-baisse SR **+1,11** vs short-après-hausse SR +0,28 → asymétrique, dominé par dip-buying. Pas pur beta mais déséquilibré. |
| **OOS (L31)** | 2000-12 SR 0,76 / **2013-26 SR 0,33** → décay confirmé (McLean-Pontiff). |

## Verdict actuel

> **NON-DÉPLOYABLE, probablement artefact δ+1 (kill).** Le délai+1 collapse SR 0,57 → 0,08 est le signe classique d'un edge porté par le bid-ask bounce sur le close-print — pratiquement impossible à capturer en compte courtier retail. La re-mesure open→close est dans la liste de choses à faire pour confirmer, **mais le prior est que ça confirme le kill** (le même mécanisme bid-ask bounce qui crée l'edge daily-close serait absent open→close → SR proche de zéro, edge mort). La promotion en `sleeves/` exige une preuve, pas une espérance ; sans preuve, ce candidat est en pratique mort.

## Gate-0 FTMO

- ⚠ SPY (ETF) **non tradeable FTMO**. Mais **US500.cash CFD ou ES futures** seraient des proxies valides… SI le sleeve était déployable. Comme il ne l'est pas, ce point est moot.
- En pratique : FTMO interdit ETF, donc une variante US500.cash CFD serait à re-mesurer (spread CFD typiquement 6-10 bps RT → mange l'essentiel de l'edge à 5,4 bp/j).

## Pourquoi quand même intéressant

- Skew daily **+0,59** = profil L7 (tail-loser absent ; les gains rares dominent les pertes rares).
- corr ~0 avec tous les autres sleeves du merge (LONGVOL_VXX, VIXTERM, PREFOMC, TSMOM_PROXY).
- Spec ultra-simple (1 jour de mémoire, daily) → robuste si l'edge survit l'exécution.

## Conditions de promotion (prior = ne se réalisera pas)

1. **Mesurer open→close** sur 2000-2026 même définition. Si t>2 et SR>0,3 net coût (peu probable), promouvoir en `sleeves/`.
2. **Si open→close meurt aussi** (résultat attendu) → marquer la lesson candidate finale : *« reversal SPX 1j = artefact close-print bid-ask bounce, edge non capturable retail »* et archiver définitivement.

Note : la re-mesure n'est pas urgente. Le candidat est traité comme suspendu/quasi-mort tant qu'aucune mesure open→close positive n'est produite. Ne PAS le déployer sur prior optimiste.

## Réconciliation archive

- Distinct du **VRP / short-vol VIX** (skew −1,70, side opposé du book vol).
- L'archive listait short-term reversal indices comme « décaye (L31) » → confirmé empiriquement (0,76 → 0,33 OOS).
- **Angle neuf** : le profil skew+ (+0,71 fenêtre commune) n'avait pas été caractérisé. L'archive jugeait sur Sharpe/décay.

## Leçons (candidates)

- *« reversal court-terme : skew+ mais load-bearing = exécution au close »* — le délai+1 le tue, drapeau exécution.
- *« skew = dimension de sélection distincte du Sharpe »* — un edge décayé en SR peut conserver un skew+ exploitable structurellement (si l'exécution suit).
