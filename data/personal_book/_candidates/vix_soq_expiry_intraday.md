# Candidat — VIX expiry Wednesday SOQ (long-vol day-after)

> **Statut** : Near-miss daily (t=1,76 sur instrument tradeable < gate 2). Bon profil (skew+1,43, décorrélé) MAIS edge réel suspecté en intraday non mesurable sans data SOQ intraday.
> **Source canonique** : `data/skew_research/session_structural_dislocations/exploration_2026-06.md` (#2).

## Mécanisme

VIX se règle par auction **SOQ** (Special Opening Quotation) le mercredi 30 jours avant le 3e vendredi du mois suivant. La vol-réalisée est *artificiellement supprimée* dans la fenêtre auction (couverture forcée), puis **rebond après** la fin du print → effet structurel mensuel.

## Métriques mesurées

| Signal nu | n | mean | t | skew_horizon | corrEQ | Verdict |
|---|---:|---:|---:|---:|---:|---|
| **Spot ^VIX day-after-expiry** | — | +120 bp | **2,02** | — | — | effet réel sur l'indice |
| **VIXY day-after-expiry (tradeable)** | 182 | +54,9 bp | **1,76** | **+1,43** | ~0 | profil idéal mais t<2 |
| V-shape (after−before) | — | +90 bp | 1,16 | — | — | NS |

→ Dampening futures + contango ronge **~55 %** du signal (120 bp ^VIX → 55 bp VIXY). L23b confirmé : *mesurer l'instrument tradeable, pas l'indice.*

## Gate-0 FTMO

- ❌ **VIXY est un ETF** → exclu (« no access to ETFs »).
- ❌ Pas de VIX futures sur FTMO.
- ❌ Pas de proxy fidèle.

→ Hors-FTMO. Réservé compte courtier.

## Pourquoi pas en sleeves/

- **t=1,76 < 2 sur instrument tradeable** → ne passe pas le gate strict du livrable.
- **Daily ne capture pas l'auction intraday** : le vrai edge est le print SOQ et la fenêtre post-auction (~30 min), pas le close-to-close. La data intraday VIX/VIXY mensuelle n'est pas disponible dans ce repo.
- **N=182 events** sur ~15 ans → puissance modeste pour creuser conditionnels.

## Conditions de promotion

1. **Acquérir data intraday VIXY** (Polygon/IQFeed, ~$50-100/mo) sur ≥10 ans pour caractériser la fenêtre post-print en minute-bars.
2. **Re-mesurer** : signal long-VIXY au print SOQ + 5/15/30 min, holding 1-3 jours. Cible t>2 sur la fenêtre conditionnelle.
3. Si t passe, vérifier robustesse délai+1 et coût VIXY/VIX futures (typiquement 1-3 bps RT). L'edge à 55 bp/évt dwarfe ces coûts confortablement.

## Profil portefeuille (si promu)

- **skew +1,43** événementiel → profil L7 idéal (le tail paie quand on en a besoin).
- ~12 events/an → série quasi-zéro le reste du temps, corr daily ~0 par construction.
- Long-vol par nature → corr equity ≤ 0 attendue (vs −0,748 pour VXX naïf).
- **Distinct de VXX naïf** : VXX = long-vol permanent (theta bleed) ; SOQ = long-vol événementiel (pas de bleed permanent).

## Réconciliation archive

- Lesson candidate : *« VIX non-tradeable ≠ VIXY tradeable »* — day-after-expiry +120 bp t=2,02 sur ^VIX mais +55 bp t=1,76 sur VIXY. L23b.
- Lesson candidate : *« dislocations à data propriétaire = mur récurrent »* — comme reconstitution, basis CIP, dividend futures : edge structurel observable sur indice mais pas en granularité tradeable sans data payante.
