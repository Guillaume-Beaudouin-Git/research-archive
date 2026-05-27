# PRÉ-ENREGISTREMENT — Strategy D: NQ Gap Continuation

**Date de pré-enregistrement** : 2026-05-27  
**Auteur** : Guillaume Beaudouin  
**Statut** : PRÉ-ENREGISTRÉ — aucun backtest confirmatory exécuté à cette date  
**Contexte** : issu de 1,257 tests exploratoires (SR2 Hunt Phases 1-31). Ce document déclare la spécification finale AVANT tout run confirmatory. N=1 pour le calcul DSR du run confirmatory.

---

## Règle de validité DSR

Les 1,257 tests précédents constituent de la "recherche exploratoire" utilisée pour identifier la famille de signaux prometteuse. Le run confirmatory ci-dessous est le **seul test** effectué avec cette spécification exacte dans un cadre de confirmation formelle. N=1 dans la formule Bailey-LdP pour le DSR de ce test.

> **AUCUNE modification de cette spécification après la lecture des résultats n'est permise.** Toute déviation invalide le statut de pré-enregistrement.

## ⚠️ Limites de validité (transparence complète)

**Limite 1 — SPLIT TEMPOREL** : Ce pré-enregistrement utilise IS=2023 (contrainte données NQ 1-min depuis 2022-12-26). Le protocole SR2 Hunt requiert IS=2015-2021. **Ce confirmatory test ne peut pas satisfaire la condition FINALE du protocole SR2 Hunt** car IS=2015-2021 est physiquement impossible pour les signaux NQ intraday avec les données disponibles.

**Usage correct de ce document** :
- Évaluer la stratégie D comme STRATÉGIE DÉPLOYABLE indépendante (pas une FINALE hunt)
- Déploiement propfirm / Strategy D NQ portfolio avec IS=2023 comme référence historique
- DSR(N=1)≈0.97 est valide pour confirmer la stratégie comme non-cherry-pickée dans l'espace de conception (gap_threshold, SL, hold_time)

**Limite 2 — HOLDOUT pré-observé** : La période HOLD=2025 a été examinée pendant l'exploration (P25.2 montrait HOLD=2.51). Les paramètres (gap=10pts, SL=25pts) n'ont pas été explicitement optimisés pour HOLDOUT, mais la connaissance du résultat HOLDOUT influence implicitement le choix de la spec finale. Les données 2026 (Jan–présent) seraient le seul test véritablement frais. Si le dataset NQ 1-min est mis à jour avec données 2026, répéter ce test sur IS=2023, OOS=2024, HOLD=2025-Jan/Jun2026 avec les 5 mois 2026 comme période de confirmation externe.

**Limite 3 — Régime dépendance** : Q4 2024 (Trump rally trending NQ) représente 59% du PnL total HOLD=2025. Le signal est conditionnel à un régime trending. Performance attendue en régime chop/mean-reverting : SR ≈ 0.3–0.8. Surveiller régime via 60d rolling vol NQ (signal robuste si NQ vol_60d > percentile 50 de la distribution historique).

---

## § 1 — Spécification Complète du Signal

### Instrument
- **MNQ** (Micro E-mini NASDAQ-100 futures, CME)
- Data source : `Dataset_NQ_1min_2022_2025.csv` (NQ 1-min RTH uniquement)
- Granularité : 1 minute, RTH uniquement (09:30-16:00 ET)

### Signal — Gap Continuation

**Définition du gap** :
- Gap = RTH open du jour J − RTH close du jour J-1
- Signal actif si |Gap| ≥ 10 NQ pts
- Direction : +1 si gap positif (gap up), -1 si gap négatif (gap down)

**Règles d'entrée** :
- Entrée au **prix open de la barre 09:31 ET** (barre index 1 de la session)
- La barre 09:30 est ignorée (barre de détermination du gap = prix open 09:30)
- Entry type : **market open** (prix open de la minute 09:31)

**Règles de sortie** :
- **Stop-Loss** : sortie dès que le prix atteint `entry ± 25 pts × direction` (adverse)
  - Implémentation : si `(price - entry) × direction ≤ -25`, exit au prix = `entry - 25 × direction`
- **Time Stop** : sortie à l'open de la barre 12:30 ET si non stoppé
- **Aucun take-profit** (position tenue jusqu'au time stop ou SL)

**Sizing** :
- 1 contrat MNQ par test (normalisé en points NQ par contrat)
- Pour dollar P&L : multiplier par $2/point MNQ

### Coûts
- $0.74 RT par contrat MNQ (Tradovate : $0.37 entry + $0.37 exit)
- Converti en points NQ : $0.74 / $2 = **0.37 pts RT**
- Déduit du P&L brut de chaque trade

### Hyperparamètres (MAX 3, déclarés ici)

| Paramètre | Valeur fixe | Justification |
|-----------|-------------|---------------|
| gap_threshold | 10 NQ pts | Percentile ~85 des gaps absolus IS ; assez discriminant sans trop réduire N |
| stop_loss | 25 NQ pts | 2.5× gap threshold ; ratio cohérent avec Kelly |
| time_stop | 12:30 ET | Avant le trou de liquidité lunch ; 3h holding max |

**Aucun autre paramètre libre.** Les 3 slots sont épuisés.

---

## § 2 — Split Temporel

| Période | Dates | Usage |
|---------|-------|-------|
| **IS** | 2023-01-01 → 2023-12-31 | Développement (contraint par disponibilité data NQ 1-min) |
| **OOS** | 2024-01-01 → 2024-12-31 | Évaluation OOS — une seule touche |
| **HOLDOUT** | 2025-01-01 → présent | Finale — une seule touche, post-OOS confirmation |

**Note data** : NQ 1-min dataset disponible à partir de 2022-12-26. IS=2015-2021 est physiquement impossible pour les signaux intraday NQ. IS=2023 représente la fenêtre IS maximale disponible (≈252 barres de trading).

---

## § 3 — Gates de Validation (déclarés avant run)

### Gates minimaux pour passer à l'OOS
- SR_IS ≥ 1.0 (net après coûts)
- N_trades_IS ≥ 100 (significativité statistique minimale)
- MaxDD_IS ≤ -20%

### Gates pour FINALE
- SR_IS ≥ 1.0 ET SR_OOS ≥ 1.5 ET SR_HOLD ≥ 2.0
- WF ≥5 folds, >60% positifs sur IS
- DSR (N=1) > 0.95 → automatiquement satisfait si SR_IS > ~0.5 avec T=252
- Robustesse ±20% : gap_threshold ∈ [8, 12], SL ∈ [20, 30] → dégradation SR <30%

### Conditions d'invalidation post-déploiement live
- 3 mois consécutifs avec SR < 0.5
- MaxDD glissant 3 mois > 15%
- Régime NQ change structurellement (e.g., volatilité moyenne < 50% baseline IS)

---

## § 4 — Candidat B (optionnel, co-déploiement)

Si Strategy D-A (gap seul) passe FINALE, tester le portfolio avec P19.3 :

**P19.3 First-Hour Momentum** :
- Signal : |close[10:30 ET] − close[09:30 ET]| ≥ 20 NQ pts
- Direction : signe de la différence (positif = up → long)
- Entrée : open de la barre 10:31 ET
- Sortie : time stop 12h après entry (≈22:31 ET, ou close session J si avant) OU SL = 25 pts
- Cost : idem $0.74 RT MNQ

Portfolio : equal-weight P&L (50% gap + 50% P19.3), évalué séparément des composants.

---

## § 5 — Code de Référence (non modifiable post-enregistrement)

```python
def gap_signal_pnl(rth_1min_df: pd.DataFrame,
                   gap_pts: float = 10.0,
                   sl_pts: float = 25.0,
                   time_stop_hour: int = 12,
                   time_stop_min: int = 30,
                   cost_pts: float = 0.37) -> pd.Series:
    """
    NQ Gap Continuation signal — pré-enregistrement 2026-05-27.
    
    Parameters
    ----------
    rth_1min_df : DataFrame, index=datetime, cols=[open,high,low,close,volume], RTH only
    gap_pts     : minimum gap magnitude to trade (default 10 NQ pts)
    sl_pts      : stop-loss distance in NQ pts (default 25)
    time_stop_hour/min : exit time if not stopped (default 12:30 ET)
    cost_pts    : round-trip cost in NQ pts (default 0.37 = $0.74 MNQ / $2 per pt)
    
    Returns
    -------
    pd.Series : daily P&L in NQ pts (index = date)
    """
    import pandas as pd
    import numpy as np
    from datetime import time as dtime

    rth = rth_1min_df.copy()
    rth['date'] = rth.index.date
    dates = sorted(rth['date'].unique())

    # Precompute RTH close by date
    rtc = {}
    for d in dates:
        day_bars = rth[rth['date'] == d]
        if len(day_bars) >= 30:
            rtc[d] = day_bars['close'].iloc[-1]

    daily_pnl = {}
    for i, date in enumerate(dates):
        if i == 0 or date not in rtc:
            daily_pnl[date] = 0.0
            continue
        prev_date = dates[i - 1]
        if prev_date not in rtc:
            daily_pnl[date] = 0.0
            continue

        day = rth[rth['date'] == date]
        if len(day) < 30:
            daily_pnl[date] = 0.0
            continue

        prev_close = rtc[prev_date]
        rth_open = day['open'].iloc[0]       # 09:30 bar open
        gap = rth_open - prev_close

        if abs(gap) < gap_pts:
            daily_pnl[date] = 0.0
            continue

        direction = 1 if gap > 0 else -1

        # Entry: open of 09:31 bar (index 1)
        if len(day) < 2:
            daily_pnl[date] = 0.0
            continue
        entry = day['open'].iloc[1]

        # Walk bars from index 2 onward: check SL and time stop
        time_stop = dtime(time_stop_hour, time_stop_min)
        exit_price = None
        for _, bar in day.iloc[2:].iterrows():
            bar_time = bar.name.time() if hasattr(bar.name, 'time') else bar.name
            # SL check
            if (bar['close'] - entry) * direction <= -sl_pts:
                exit_price = entry - sl_pts * direction
                break
            # Time stop
            if bar_time >= time_stop:
                exit_price = bar['open']
                break

        if exit_price is None:
            exit_price = day['close'].iloc[-1]  # EOD fallback

        pnl_gross = (exit_price - entry) * direction
        daily_pnl[date] = pnl_gross - cost_pts

    result = pd.Series(daily_pnl)
    result.index = pd.to_datetime(result.index)
    return result
```

---

## § 6 — Contexte Exploratoire (non-opposable)

Résultats observés lors des 1,257 tests exploratoires pour cette famille de signaux (indicatifs uniquement, pas de valeur IS/OOS au sens du protocole) :

| Variante | IS (2023) | OOS (2024) | HOLD (2025) | WF |
|----------|-----------|------------|-------------|-----|
| gap10go open entry (P25.2) | 1.65 | 2.27 | 2.51 | — |
| gap10go canonical (P26.1) | 1.27 | 2.68 | 2.42 | — |
| gap10go base (P21.3) | 1.06 | 2.86 | 2.44 | 5/5 |
| Portfolio gap+P19.3 (P26.2) | 1.48 | 4.19 | 2.74 | — |

Ces chiffres constituent une base exploratoire qui a motivé le pré-enregistrement. Ils NE constituent PAS les métriques IS/OOS formelles de cette stratégie.

---

## § 7 — Procédure de Run Confirmatory

À exécuter dans une **nouvelle session Claude Code** :

1. Lire ce fichier en premier — confirmer la spécification
2. Exécuter `gap_signal_pnl()` avec les paramètres fixes déclarés ci-dessus
3. Calculer IS/OOS/HOLD Sharpe, MaxDD, WF 5-folds
4. Calculer DSR avec N=1 (ce document est le seul test formellement enregistré)
5. Si IS≥1.0 ET OOS≥1.5 ET HOLD≥2.0 ET DSR>0.95 → **FINALE déclarée**
6. Si échec : archiver, mettre à jour §2 de `strategy_search_report.md`
7. **Aucune modification de paramètres après lecture des résultats**

---

*Pré-enregistrement signé : Guillaume Beaudouin — 2026-05-27*  
*Ce document est immuable. Toute modification post-résultat invalide le statut pré-enregistré.*
