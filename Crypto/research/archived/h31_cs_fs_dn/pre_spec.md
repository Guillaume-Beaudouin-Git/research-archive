# Pre-Specification — H31 CS-FS Delta-Neutral Carry
## Test #160 | Statut : OPTION C — univers dynamique, démarrage 2024-01-01

*Branche : `claude/h31-cs-fs-dn-test-160` | Date : 2026-05-28*
*Investigateur : Claude Sonnet 4.6*

---

## 1. Identité de l'hypothèse

**Famille** : H31 — Cross-Sectional Funding Spread Delta-Neutral Carry  
**Référence** : Schmeling, Schrimpf & Todorov (2023) BIS WP 1087 "Crypto Carry" — extension
delta-neutral. Koijen et al. (2018) carry cross-asset.  
**n_tests cumulé** : 159 (réalisations brutes) → 160 avec ce test.  
**n_hypothèses économiques** : 40 (restructure audit 2026-05-28) → 41 avec ce test.  
**AMTP method** : HLZ avec n=41 → t_required ≈ √(log 41) × Φ⁻¹(1 − 0.025/41) ≈ **3.18**  
**DSR** : T ≈ 504 trading days (2024-01-01 → 2026-05-05), N_mod = 0, SR_* = 1.0

---

## 2. Signal pre-registered (figé)

```
Pour chaque date t (daily), pour chaque asset i éligible à t :
  funding_rate_8h[i,t] = moyenne des 3 payments 8h du jour t
  funding_rate_7d_mean[i,t] = moyenne 7j glissante de funding_rate_8h
  funding_z[i,t] = (funding_rate_7d_mean[i,t] − mean_cross_section) / std_cross_section
                   où mean/std calculés uniquement sur l'univers éligible à t

Long quintile  : 20% assets par funding_z LE PLUS BAS (funding le plus négatif → shorts paient longs)
Short quintile : 20% assets par funding_z LE PLUS HAUT (funding le plus positif → longs paient shorts)
Sizing         : equal-weight intra-quintile, dollar-neutral (long $ = short $)
Signal date    : T-1, position prise à T (pas de look-ahead)
```

---

## 3. Paramètres pre-registered (non modifiables)

| Paramètre | Valeur figée |
|-----------|-------------|
| Lookback funding | 7 jours (canonique) |
| Z-score window | 60 jours rolling (intra-asset time-series) |
| Cross-section normalisation | Sur l'univers éligible à t uniquement |
| Rebalance | Daily 00:00 UTC |
| Quintile method | Bottom 20% (long) / top 20% (short) par funding_z |
| Long/short sizing | Equal-weight, dollar-neutral |
| Coût RT taker | HL 0.035% par leg |
| Slippage additionnelle | 1 bp par leg |
| Funding accrual | 3 payments/jour × funding_rate_8h × $-notional |
| **Univers** | **Dynamique point-in-time : first_date[i] ≤ t − 180 jours** |
| **Période backtest** | **2024-01-01 → 2026-05-05** |
| N minimum par date | N ≥ 10 assets éligibles pour générer un signal (sinon skip) |

---

## 4. Universe dynamics (Option C — figée)

À chaque date t, un asset i est éligible si et seulement si :
- `first_date[i] ≤ t − 180 jours` (6 mois d'historique HL)
- L'asset dispose de données de funding pour les 7 jours précédant t

Évolution attendue de l'univers :
- 2024-01-01 : N ≈ 22 (assets listés avant 2023-07-05)
- 2024-04-01 : N ≈ 36
- 2024-07-01 : N ≈ 69
- 2025-01-01 : N > 100

La perte de la période 2023 est acceptée comme trade-off pour un univers CS statistiquement viable.
Une éventuelle extension à 2023 fera l'objet d'un test séparé (test #161 ou ultérieur).

---

## 5. Gates pre-registered

| Gate | Critère | Verdict si FAIL |
|------|---------|-----------------|
| RESEARCH_PASS | Sharpe net > 0.7 ET MaxDD > −25% ET WF% > 50% ET t_HAC > 1.5 | FAIL |
| PROPFIRM_PASS | Sharpe net > 1.0 ET MaxDD > −10% ET WF% > 60% ET t_HAC > 2.0 | FAIL |
| AMTP (HLZ n=41) | t_HAC observé vs t_required ≈ 3.18 | À mesurer |

---

## 6. Contexte du STOP initial (résolu)

La spec originale supposait "29 perps HL au 2023-05". Le data prep a confirmé que HL
n'avait que 20 perps en mai 2023 (N < 22 minimum). Résolution choisie par l'investigateur
principal : **Option C — univers dynamique point-in-time** avec éligibilité ≥ 6 mois
d'historique, backtest démarrant au 2024-01-01 quand N ≥ 22 est garanti.

---

## 7. État du code

- `pre_spec.md` : présent (ce fichier — Option C finalisée)
- `data_prep.py` : À créer
- `signal.py` : À créer
- `backtest.py` : À créer
- `validation.py` : À créer
- `postmortem.md` : À créer (après backtest)
- `results/` : répertoire créé, vide

---

*Branche : `claude/h31-cs-fs-dn-test-160` | Paramètres figés — aucun amendement permis*
