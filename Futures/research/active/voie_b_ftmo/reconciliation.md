# Voie B — Audit & Réconciliation EA ↔ Python

**Date :** 2026-05-28  
**Branch :** `claude/voie-b-reconciliation`  
**Statut :** 4 bugs EA confirmés — 2 fixes critiques vérifiés ✅ — parity check en attente

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

## 3. Confirmation des 2 fixes critiques (`confirm_fixes.py`)

Script : `confirm_fixes.py` — miroir Python exact du code MQL5.  
Run : `/usr/bin/python3 confirm_fixes.py`

---

### Fix 1 — DST ✅ PASS

**Code corrigé (`Voie_B_EA_fixed.mq5`) :**

```mql5
int NthSunday(int year, int month, int n) {
   // …calcule le n-ième dimanche du mois
   int first_sun = (tmp.day_of_week == 0) ? 1 : 8 - tmp.day_of_week;
   return first_sun + (n - 1) * 7;
}

int GetETOffsetHours() {
   datetime utc_now = TimeGMT();
   // EDT: 2nd Sun March 07:00 UTC → 1st Sun November 06:00 UTC
   edt_start.day = NthSunday(y, 3, 2);  edt_start.hour = 7;
   edt_end.day   = NthSunday(y, 11, 1); edt_end.hour   = 6;
   return (utc_now >= edt_start && utc_now < edt_end) ? 4 : 5;
}

void GetSessionBoundsUTC(int &entry_h, int &entry_m,
                          int &exit_h,  int &exit_m, int &eod_h) {
   int off  = GetETOffsetHours();
   entry_h  = 9  + off;  entry_m = 31;   // 09:31 ET
   exit_h   = 15 + off;  exit_m  = 58;   // 15:58 ET
   eod_h    = 16 + off;                   // 16:00 ET
}
```

**Résultats du test :**

| Date test | Saison | Offset ET | entry UTC | exit UTC | Statut |
|-----------|--------|-----------|-----------|----------|--------|
| 2026-05-15 12:00 UTC | ÉTÉ (EDT) | 4h | **13:31** | **19:58** | ✅ PASS |
| 2026-01-15 12:00 UTC | HIVER (EST) | 5h | **14:31** | **20:58** | ✅ PASS |

---

### Fix 1b — DST transitions (off-by-one) ✅ PASS

| Date test | Moment | Offset | entry UTC | exit UTC |
|-----------|--------|--------|-----------|----------|
| 2026-03-08 06:59 UTC | last EST minute | 5h | 14:31 | 20:58 | ✅ |
| 2026-03-08 07:00 UTC | first EDT minute | 4h | 13:31 | 19:58 | ✅ |
| 2026-11-01 05:59 UTC | last EDT minute | 4h | 13:31 | 19:58 | ✅ |
| 2026-11-01 06:00 UTC | first EST minute | 5h | 14:31 | 20:58 | ✅ |

`NthSunday(2026,3,2) = 8` ✅ `NthSunday(2026,11,1) = 1` ✅ — pas d'off-by-one quand le mois commence un dimanche.

---

### Fix 2 — Ratchet (référence start_balance) ✅ PASS

**Code corrigé (`Voie_B_EA_fixed.mq5`) :**

```mql5
#define GV_START_BAL "VoieB_StartBalance"

// OnInit — persiste le solde de départ une seule fois
if(!GlobalVariableCheck(GV_START_BAL) || GlobalVariableGet(GV_START_BAL) <= 0)
   GlobalVariableSet(GV_START_BAL, AccountInfoDouble(ACCOUNT_BALANCE));

double EffectiveLeverageRatchet(double cur_equity) {
   double start_bal = GlobalVariableGet(GV_START_BAL);
   if(start_bal <= 0) start_bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double pct = cur_equity / start_bal - 1.0;   // NOT ACCOUNT_BALANCE (croît avec profits)
   double lev = BaseLeverage + Ratchet * pct;
   return MathMax(MathMin(lev, MaxLeverage), 0.0);
}
// Inputs : BaseLeverage=2.5, Ratchet=25.0, MaxLeverage=5.0
```

**Résultats du test (start_balance = 100 000) :**

| Equity | pct | Levier attendu | Levier calculé | Statut |
|--------|-----|----------------|----------------|--------|
| start × 1.05 | +5% | **3.75** | 3.7500 | ✅ PASS |
| start × 1.00 | 0% | **2.50** | 2.5000 | ✅ PASS |
| start × 0.95 | −5% | 1.25 | 1.2500 | ✅ PASS |

> Note : `UseVolTarget = true` (défaut) → EffectiveLeverageRatchet n'est PAS appelé en
> production. Le mode ratchet est réservé à `UseVolTarget = false` (legacy / test only).

### Kill-switch + entry/exit timing ✅ PASS

| Test | Résultat |
|------|----------|
| Kill-switch lev=2.5 → threshold 97 000 (-3%) | ✅ |
| Kill-switch lev=5.0 → threshold 94 000 (-6%) | ✅ |
| Entry EDT 13:30 UTC — ne fire pas | ✅ |
| Entry EDT 13:31 UTC — fire | ✅ |
| Exit EDT 19:57 UTC — ne fire pas | ✅ |
| Exit EDT 19:58 UTC — fire | ✅ |

### Gap isolation (secondaires figés) ✅ PASS

Si les 3 secondaires sont figés en tester (BID=0), `DetermineDirection` retourne 0 (pas de
signal) car `n_up < MinConfirmation=2`. La confirmation multi-instruments **n'est vérifiable
qu'en live** — le tester ne peut pas valider cette logique.

CSV log `VoieB_decisions.csv` : gaps non-zéro = confirmation que les flux prix sont vivants.

---

## 4. Parité EA ↔ Python

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

## 5. corr(C, B) — Strategy C ↔ Voie B

Voir `results/corr_c_b.md` (généré par `corr_c_b.py`).

**Résultat :** corr(C, B) Pearson = **0.036**, Spearman = 0.002 → décorrélés.  
Overlap 2022-12-28 → 2025-12-11, N = 281 jours actifs simultanément.

---

## Checklist déploiement

- [x] Audit Python complété
- [x] Bugs EA inventoriés (4 bugs)
- [x] EA corrigé (`Voie_B_EA_fixed.mq5` v1.10 + CSV logging)
- [x] Fix DST confirmé — été/hiver + bascules 2026-03-08 / 2026-11-01 ✅
- [x] Fix Ratchet confirmé — equity×1.05→3.75, equity×1.00→2.50 ✅
- [x] Kill-switch + entry/exit timing confirmés ✅
- [x] Gap isolation (secondaires figés) — comportement documenté ✅
- [x] corr(C, B) = 0.036 — décorrélés ✅
- [ ] **Déploiement VPS Wine/MT5 demo FTMO** (→ `vps_deploy.md`)
- [ ] J1 : vérifier gaps non-zéro sur 4 instruments (VoieB_decisions.csv)
- [ ] J1 : vérifier DST offset correct (4 ou 5 selon date)
- [ ] Parity check live après 4-6 sem (`parity_check.py --mt5_csv decisions.csv`)
- [ ] Gate ≥ 95% direction atteint
- [ ] Gate ≥ 90% sizing atteint
- [ ] **Go/no-go challenge FTMO €99** (7 critères — voir `vps_deploy.md` §10)
