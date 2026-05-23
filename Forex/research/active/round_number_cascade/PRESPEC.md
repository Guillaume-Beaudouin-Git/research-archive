# PRE-SPEC — Round Number Stop-Loss Cascade (Phase 1.5 IC)

**Frozen:** 2026-05-23  
**N_tests baseline at freeze:** 170  
**Status:** FROZEN — toute modification après commit = nouveau n_test

Ce document fige exhaustivement la définition du signal, le mécanisme hypothétique, les horizons testés, et la comptabilité n_tests. Aucune décision n'est prise après avoir vu les données.

---

## 1. Définition "round number" — CHOIX : 50-pips (.XX00 + .XX50)

**Choix retenu :** niveaux espacés de 50 pips, soit `.XX00` et `.XX50` dans la convention 4 décimales EUR/USD (ex: 1.0800, 1.0850, 1.0900, 1.0950...).

**Justification Osler :**

Osler (2003, JF) documente le clustering des ordres stop-loss dans les données propriétaires Citibank. Les "psychologically significant exchange rate values" sont définies comme :
- **Big figures** (`.XX00`) : clustering le plus fort. Exemple : 1.08, 1.09, 1.10. Ce sont les niveaux où le clustering est statistiquement le plus significatif dans les données Osler.
- **Half-figures** (`.XX50`) : clustering secondaire documenté, moins intense que les big figures, mais statistiquement significatif. Exemple : 1.0850, 1.0950.

Les niveaux à 25 pips (`.XX25`, `.XX75`) ne sont **pas documentés** dans Osler (2003) ou Osler (2005) comme points de clustering — les inclure serait une hypothèse non pré-enregistrée.

Le choix `.XX00` uniquement (100-pip) est plus conservateur mais réduit N d'environ 50% (voir Section 5). Le choix `.XX00 + .XX50` maximise N tout en restant strictement dans le périmètre Osler.

**Implémentation :**
```python
# EUR/USD 5-decimal Dukascopy → round à 4ème décimale pour identifier les niveaux
# Niveaux : [round(p / 0.0050) * 0.0050 for p in price_range]
# Ex: 1.08000, 1.08500, 1.09000, 1.09500, ...
LEVEL_SPACING = 0.0050  # 50 pips en convention 5-décimales Dukascopy
```

**Niveaux actifs EUR/USD 2020–2024 :** range ≈ 1.0340 → 1.2350 → 40 niveaux actifs à 50 pips.

---

## 2. Définition "breach event" — CHOIX : close-through (option a)

**Choix retenu :** `close[t] > level AND close[t-1] < level` (upside breach) ou l'inverse (downside breach). Pas de buffer additionnel.

**Justification :**

Trois options candidates :
- **(a) close-through** : close[t] dépasse le niveau, close[t-1] ne le dépassait pas. Aucun paramètre libre.
- **(b) high/low breach + buffer X pips** : introduit un paramètre X non documenté par Osler.
- **(c) ATR-normalized** : introduit un paramètre Y%, modélisation de variance non spécifiée dans la littérature.

**Options b et c sont rejetées** car elles introduisent des paramètres libres qui consommeraient des n_tests supplémentaires. Option a est la seule sans paramètre libre.

**Limitation reconnue :** dans le mécanisme Osler, les stops sont déclenchés dès que le prix *touche* le niveau intrabar (high/low), pas nécessairement en close. Le close-through est un **proxy plus strict** : il exige que le prix reste au-delà du niveau à la fin du bar de 1min. Cela filtre les wicks qui touchent le niveau et reviennent immédiatement (faux signaux). Si le mécanisme cascade est réel, le close-through capturera la phase initiale de la cascade dans les bars suivants.

**Définition formelle :**
```python
# Upside breach (signal LONG):
signal_long[t] = 1 if (close[t] > level) and (close[t-1] <= level)

# Downside breach (signal SHORT):  
signal_short[t] = -1 if (close[t] < level) and (close[t-1] >= level)

# Les deux conditions sont mutuellement exclusives pour un niveau donné.
# Un bar peut déclencher un signal sur plusieurs niveaux si price traverse plusieurs
# niveaux en un seul bar (cas rare, traité : prendre le niveau le plus proche de close[t-1]).
```

**Règle de résolution collision :** si un seul bar traverse plusieurs niveaux consécutifs (ex: range du bar > 50 pips), on retient le **premier niveau traversé** (le plus proche de close[t-1]). Un seul signal par bar par paire.

---

## 3. Direction du signal — PRÉ-ENREGISTRÉE : MOMENTUM

**Hypothèse pré-enregistrée :**
- Breach upside (close[t] > level) → signal **LONG** (+1)
- Breach downside (close[t] < level) → signal **SHORT** (−1)
- Forward return attendu : **positif** (cascade continue dans la direction du breach)

**Mécanisme Osler :**  
Osler (2005) : "exchange rate trends are unusually rapid when rates reach levels where stop-loss orders cluster." Stop-loss BUY orders clustered just above round numbers → quand le niveau est franchi à la hausse, ces ordres s'exécutent → pression d'achat supplémentaire → momentum haussier.

**Règle de failsafe pré-enregistrée :**  
Si IC Spearman est **négatif** et t_HAC est significativement négatif sur l'horizon principal → c'est un **FAIL de l'hypothèse momentum**, pas un signal pour tester la direction inverse (fade-the-cascade). Hypothèse fade-the-cascade = nouvel n_test distinct, non testé ici.

---

## 4. Forward horizons — TOUS REPORTÉS, PAS DE CHERRY-PICKING

**Horizons pré-enregistrés :** 1min, 5min, 15min, 30min, 60min.

Tous les 5 sont calculés et reportés dans le résultat JSON. La gate IC ne s'applique qu'à l'**ensemble** — un seul horizon significatif sur 5 est insuffisant pour déclarer GO sans correction multiple.

**Gate IC :**  
- **PASS :** IC_spearman > 0 ET t_HAC > 1.65 sur **≥ 2 des 5 horizons** ET IC > 0 sur les 2 mêmes horizons
- **WEAK :** IC > 0 ET t_HAC ∈ [1.0, 1.65] sur ≥ 2 horizons → INCONCLUSIVE, pas de GO direct
- **FAIL :** t_HAC < 1.0 sur tous horizons, ou IC < 0 majoritairement → STOP

**Pourquoi 2/5 et non 1/5 :** 5 horizons testés simultanément, seuil de 1.65 suppose α = 5% — si on cherry-pick le meilleur, le vrai α est ~23% (1 − 0.95^5). Exiger 2/5 horizons cohérents réduit ce risque.

**Attribution HFT pré-enregistrée :**
- Si IC fort à 1min et décroît à 5-60min → cascade instantanée (HFT), signal exploitable seulement sub-minute → FAIL pour nos données 1-min
- Si IC faible à 1min mais positif et croissant à 5-30min → cascade lente, exploitable → signal viable
- Si IC positif à 15-60min mais négatif à 1-5min → mean reversion initiale puis momentum → mécanisme composite, documenter sans exploiter

---

## 5. Density check (pré-IC obligatoire)

**Gate pré-IC :** N ≥ 200 breach events sur EUR/USD 2020–2024 pour le produit final. Si N < 200, signal structurellement sparse → signaler avant IC.

**Estimation ex-ante (pre-data):**
- EUR/USD range 2020–2024 : 1.0340 → 1.2350 → ~40 niveaux actifs à 50 pips
- Traversées nettes directionnelles par niveau : ~4–8 (baisse 2021, rebond 2023, repli 2024)
- Traversées aller-retour (noise) : multiplicateur ×3–5 sur les traversées nettes
- Estimation totale : 40 niveaux × 6 traversées nettes × 2 directions = **~480 breach events bruts**
- Après filtre close-through (élimine les wicks) : ~60–70% retention → **~290–340 qualifying events**

Estimation passe le gate N ≥ 200. Le script confirmera avant de lancer IC.

**Reporting densité :**
```
Density check output (pre-IC):
  EUR/USD: N_breach_total = ?, N_breach_.XX00 = ?, N_breach_.XX50 = ?
  Distribution par année: 2020/2021/2022/2023/2024
  Gate N >= 200: [PASS/FAIL]
```

---

## 6. Paires et pooling

**Ordre de test :**
1. **EUR/USD** en premier (Osler 2003 primary pair, plus large des deux, données de meilleure qualité)
2. **GBP/USD** uniquement si EUR/USD IC > 0 (pas nécessairement significatif, mais direction positive)

**Pas de pooling** EUR/USD + GBP/USD jusqu'à confirmation de direction sur EUR/USD. Le pooling serait une décision post-data si EUR/USD passe — consomme un n_test supplémentaire.

**Justification :** pooler les deux paires sans confirmation EUR/USD préalable masquerait une situation où le signal est négatif sur EUR/USD mais positif sur GBP/USD — résultat contradictoire avec le mécanisme Osler qui est supposé universel sur les paires majeures.

---

## 7. Comptabilité n_tests

| Étape | Tests | Cumul |
|---|---|---|
| Baseline (ORB v1 archivé) | — | **170** |
| EUR/USD density check | 0 (pre-check, pas IC) | 170 |
| EUR/USD IC : 1 définition × 5 horizons | **+5** | **175** |
| GBP/USD IC (si EUR/USD IC > 0) : 5 horizons | **+5** | **180** |
| **Maximum engagé par ce pre-spec** | | **180** |

**Ce pre-spec interdit :**
- Tester une deuxième définition (ex: 100-pip uniquement) → +5 tests supplémentaires non pré-enregistrés
- Tester la direction inverse (fade-the-cascade) si IC négatif → nouveau n_test
- Pool EUR/USD + GBP/USD sans confirmation EUR/USD → nouveau n_test
- Ajouter un horizon (ex: 2h, session) non listé ici → nouveau n_test

Si l'une de ces extensions est jugée nécessaire après les résultats : documenter comme nouveau test, incrémenter n_tests, ne pas modifier ce fichier.

---

## Résumé des choix figés

| Paramètre | Choix | Raison |
|---|---|---|
| Définition niveau | .XX00 + .XX50 (50-pip) | Osler (2003) : clustering big + half figures documentés |
| Définition breach | Close-through (aucun paramètre libre) | Seule option sans free parameter |
| Direction signal | Momentum (suite du breach) | Osler (2005) : cascade dans la direction du breach |
| Horizons | 1, 5, 15, 30, 60 min | 5 horizons, tous reportés |
| Gate IC | IC > 0 + t_HAC > 1.65 sur ≥ 2/5 horizons | Correction implicite multi-horizons |
| Paire principale | EUR/USD | Osler primary pair |
| Pooling | Interdit avant confirmation EUR/USD IC > 0 | Évite masquage signal contradictoire |
| n_tests max | +10 (170 → 180) | 5 EUR/USD + 5 GBP/USD |

---

## Références sources (vérifiées web 2026-05-23)

- **Osler (2003)** — "Currency Orders and Exchange Rate Dynamics" — *Journal of Finance*, 58(4), 1791–1819
- **Osler (2005)** — "Stop-Loss Orders and Price Cascades in Currency Markets" — *Journal of International Money and Finance*, 24(2), 219–241

Ces deux papiers sont les **seules** sources justifiant les choix ci-dessus. Toute décision d'implémentation non déductible directement de ces papiers = hypothèse additionelle → documenter comme telle.
