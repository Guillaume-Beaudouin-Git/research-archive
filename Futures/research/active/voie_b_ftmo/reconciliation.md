# Voie B — Audit & Réconciliation EA ↔ Python

**Date :** 2026-05-28  
**Branch :** `claude/voie-b-reconciliation`  
**Statut :** 4 bugs EA confirmés — corrections dans `Voie_B_EA_fixed.mq5`

---

## 1. Audit Python (`ftmo_voie_b.py`)

### 1a. Cushion-ratchet implémenté ?

**NON.** Le backtest Python utilise du **vol-targeting pur**, pas de ratchet.

```python
# ftmo_voie_b.py, lignes 103-104
rv = net.rolling(60).std() * np.sqrt(DAYS)   # vol réalisée 60j, annualisée
rs = (net * (TARGET_VOL / rv).shift(1).clip(0, 5)).dropna()
```

- `TARGET_VOL = 0.10` (10% ann)
- Levier = `0.10 / rv`, cappé à 5×
- Aucune dépendance à l'equity du compte
- Référence capital : N/A — le vol-targeting est stationnaire, pas function du PnL accumulé

**Conséquence :** l'EA implémente un cushion-ratchet (`BaseLeverage + Ratchet × pct_gain`) que le backtest Python n'a jamais testé. Les deux modules produisent des tailles de position structurellement différentes. → Bug 4.

---

### 1b. Vol-target ou notional 1/4 égal ?

**Vol-target.** Voir ci-dessus (1a). Levier = `TARGET_VOL / rv_60d`, clip 5×.  
Pas de notional égal pondéré par symbole — la taille par symbole est `per_symbol = total_notional / 4` après scaling vol global.

---

### 1c. Heures de session

**Python :** données issues de CSVs uploadés (`ftmo_open.csv`, `ftmo_close.csv`). La définition de session (Open/Close) est **encodée dans les données sources**, pas dans le code.  
Le commentaire en tête de fichier indique :

```
US500/US100/US30/US2000 : 14:30 - 21:00 (NYSE/NASDAQ cash)
```

Ces heures correspondent au **fuseau EST (UTC-5, hiver)**. Le backtest ne contient pas de logique DST — la correction dépend de la qualité des CSVs sources.

**EA :** heures UTC hardcodées dans les inputs :

```mql5
input int EntryHourUTC   = 14;   // 14:31 UTC
input int ExitHourUTC    = 20;   // 20:58 UTC
```

→ Correct en **EST (hiver)**, décalé d'1h en **EDT (été)**. → Bug 1 confirmé.

**Validation mai 2026 (EDT, UTC-4) :**

| Événement | ET | UTC attendu | UTC actuel EA | Statut |
|---|---|---|---|---|
| US Open + 1min | 09:31 | **13:31** | 14:31 | ❌ +1h |
| US Close − 2min | 15:58 | **19:58** | 20:58 | ❌ +1h |
| prev_close (EOD) | 16:00 | **20:00** | 21:00 | ❌ +1h |

---

### 1d. Best Day Rule / consistency_ratio

**Non modélisés** dans le backtest Python.  

Note : la règle de cohérence FTMO ("best single day ≤ 50% of profit target") s'applique aux **comptes financés** (vérification mensuelle), pas à la phase de challenge. Elle est donc hors-scope pour la simulation actuelle mais devra être intégrée si la stratégie vise le compte financé (phase funded).

---

## 2. Bugs EA — Inventaire

### Bug 1 — DST (critique, déploiement bloqué)

**Localisation :** `OnTimer()`, entrée et sortie ; `GetPrevCloseAt21UTC()`.

**Problème :** heures UTC fixées pour EST uniquement. En EDT (mi-mars → début novembre), toute la session est décalée d'1h — l'EA entre 1h après l'open, sort 1h après la clôture réelle (hors session CFD).

**Fix :** calculer dynamiquement l'offset ET (4h EDT ou 5h EST) à chaque tick, et en dériver les bornes UTC. Voir `Voie_B_EA_fixed.mq5`, fonction `GetETOffsetHours()`.

---

### Bug 2 — Référence equity ratchet (critique)

**Localisation :** `OnTimer()`, bloc entry, ligne ~207.

```mql5
// AVANT (buggé)
double pct = equity / AccountInfoDouble(ACCOUNT_BALANCE) - 1.0;
```

`ACCOUNT_BALANCE` est le **solde réalisé courant**, qui croît avec les profits fermés. Diviser par lui sous-estime le gain par rapport au début du challenge.

**Fix :** stocker `challenge_start_balance` en `GlobalVariable` MT5 à la première initialisation, et utiliser ce montant fixe comme référence.

```mql5
// APRÈS (corrigé)
double start_bal = GlobalVariableGet("VoieB_StartBalance");
if(start_bal <= 0) { start_bal = equity; GlobalVariableSet("VoieB_StartBalance", equity); }
double pct = equity / start_bal - 1.0;
```

---

### Bug 3 — prev_close hardcodé 21:00 UTC

**Localisation :** `GetPrevCloseAt21UTC()`.

**Problème :** la fonction cherche toujours le bar M1 à 21:00 UTC. En EDT, le marché ferme à 20:00 UTC (16:00 ET). La barre à 21:00 UTC ne correspond plus à la clôture réelle.

**Fix :** rendre la cible DST-aware en appelant `GetETOffsetHours()` pour dériver l'heure de close (16:00 ET → UTC).

---

### Bug 4 — `VolTargetAnnual` mort / désalignement avec Python (structurel)

**Localisation :** paramètre `VolTargetAnnual = 0.10`, jamais utilisé. `EffectiveLeverage()` ignore ce paramètre.

**Décision (suite à 1b) :** aligner sur Python = **vol-targeting**, supprimer le ratchet ou le rendre optionnel.  
Fix : implémenter `ComputeVolTargetLeverage()` dans l'EA — calcul de vol réalisée 60j sur US500 Daily comme proxy de portefeuille, levier = `VolTargetAnnual / ann_vol`, cap `MaxLeverage`.  
Le paramètre `Ratchet` est conservé comme input mais ignoré si `UseVolTarget = true` (mode par défaut).

---

## 3. Parité EA ↔ Python

**Pré-requis** : EA compilé sans erreurs, Strategy Tester MT5 sur 2024-01-01 → 2025-12-31.

### Procédure

1. Dans MT5 Strategy Tester : `Voie_B_EA_fixed.mq5`, symbole `US500.cash`, TF `M1`, 2024-2026.
2. Exporter les trades : clic droit dans Results → *Save As CSV*.
3. Charger dans `parity_check.py` (fourni) avec le chemin du CSV.
4. Le script compare signal-par-signal (direction, date, taille) avec `ftmo_voie_b_returns.csv`.

### Gates

| Gate | Seuil | Statut |
|---|---|---|
| Concordance direction | ≥ 95% des jours actifs | ⏳ à mesurer |
| Concordance sizing | ≥ 90% (ratio lots) | ⏳ à mesurer |
| Déploiement VPS | **BLOQUÉ** tant que gates non atteints | ❌ |

---

## 4. corr(C, B) — Strategy C ↔ Voie B

Voir `results/corr_c_b.md` (généré par `corr_c_b.py`).

**Résultat préliminaire :** à run sur overlap 2022-2025 (limité par dataset NQ 1-min).

---

## Checklist déploiement

- [x] Audit Python complété
- [x] Bugs EA inventoriés (4 bugs)
- [x] EA corrigé (`Voie_B_EA_fixed.mq5`)
- [ ] Parity test MT5 Strategy Tester (manuel)
- [ ] Gate concordance ≥ 95% direction atteint
- [ ] Gate concordance ≥ 90% sizing atteint
- [ ] corr(C, B) calculé sur overlap commun
- [ ] Déploiement VPS approuvé
