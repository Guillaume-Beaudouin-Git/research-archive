# AUDIT ADVERSARIAL — Bascule compte FTMO funded $10k + patch EA v2.9

**Date** : 2026-08-17 · **Auditeur** : session indépendante, lecture seule VPS
**Périmètre** : (A) opérations du jour sur l'infra live, (B) plan de bascule vers le compte funded réel
**Méthode** : lecture du code source, hachage des binaires, lecture de l'état runtime VPS. Aucune écriture.

Convention de ce rapport : **[V]** = vérifié par citation `fichier:ligne` ou sortie de commande reproduite ici · **[D]** = déduit d'un raisonnement sur du code vérifié · **[NV]** = non vérifiable depuis ce poste.

---

## 1. VERDICT

# GO SOUS CONDITIONS

Le patch v2.9 est propre et la chaîne de build est cohérente au hash près ; mais **trois conditions bloquantes** doivent être levées avant de toucher au VNC, et la « nuit de validation désarmée » telle que planifiée **ne valide rien et casse activement la chaîne targets** — ce point est prouvé empiriquement, pas supposé.

### Conditions bloquantes

1. **B1 — Le binaire v2.9 n'a JAMAIS tourné.** Sa première exécution de l'histoire serait sur le compte à argent réel. Le faire tourner d'abord sur le compte P2 (fermé, trading désactivé serveur) coûte 10 minutes et zéro risque. → §4.1
2. **B2 — `InpPhase` mal réglé = 16,8× la taille prévue, et RIEN dans la chaîne ne le détecte** (le cross-check brain↔EA est circulaire). Un `pkill -9` du watchdog peut ressusciter un profil `InpPhase=2` sur le compte funded. Exige une procédure de vérification explicite post-attachement + persistance du profil. → §2.1
3. ~~**B3 — Le mécanisme de Max Loss du compte FUNDED n'est cité en source primaire NULLE PART dans le repo.**~~ → **LEVÉ le 2026-08-17**, le jour même de l'audit. L'opérateur a vérifié sur son compte funded réel : le Max Loss funded est **STATIQUE** (10 % du capital initial, ancré au capital initial, ne monte jamais). **L'EA avait donc raison** avec son plancher fixe à $9 000 — aucune correction de code requise. Gravé en source primaire dans `PropFirms/ftmo/rules.md` §« Compte FUNDED (post-challenge) ». **Ne reste que 2 bloquants : B1 et B2.**

Non bloquant mais à intégrer **au plan** : la nuit désarmée casse `market_export → brain → targets` (§2.4), et il n'y a **aucune urgence calendaire** — armer mardi ne rapporte qu'un ORB à $25 de risque avant lundi 24 (§3.5).

---

## 2. BLOQUANTS

### 2.1 — B2 : `InpPhase=2` sur le compte funded = 16,8× la taille, non détecté

**Arithmétique, entièrement dans le code :**

| Grandeur | source | phase 2 | phase 3 |
|---|---|---|---|
| `VmEff()` | `book_executor.mq5:162-167`, `spec_v22.mqh:30,31,73` | `CH_VM × CH_P2_MULT` = 14 × 1.2 = **16.8** | `FU_VM` = **1** |
| `OnWEff()` | `book_executor.mq5:168`, `spec_v22.mqh:32,74` | `CH_ON_W` = **0.6** | `FU_ON_W` = **0.35** |
| `Glide()` | `book_executor.mq5:204-209` | 1.0 à eq=10 000 (prog=0) | 1.0 (OFF) |
| `Pace()` | `book_executor.mq5:210-217` | `InpAttemptStart=2026.08.06` → frac_t=12/91 → **1.132** | 1.0 (OFF) |

**Scénario** : l'opérateur se connecte au compte funded, ré-attache l'EA, mais `InpPhase` reste à 2 (valeur mémorisée dans le profil/template du graphe).

- `Scale(eq)` = 16.8 × 1 × 1 × 1.132 = **19.02** [D, à partir de `mq5:218`]
- Jambe GER40 à 17:35 = `OnWEff() × Scale × eq` = 0.6 × 19.02 × 10 000 = **$114 100** de notionnel [V, `mq5:1108`]
- Marge requise à 6.667 % (taux live vérifié) = $7 607 = 76 % de l'équité → le cap marge 60 % mord [V, `mq5:1001-1006`, `CH_MARGIN_CAP 0.6` mqh:42] → écrêté à **$90 000 de notionnel, soit 9× de levier sur un compte de $10 000**
- Budget quotidien = $500 [V, `mq5:174`]. **Un mouvement adverse de 0,55 % sur GER40 consomme tout le budget journalier.** σ quotidien GER40 ≈ 1 %.
- Configuration correcte (phase 3) : 0.35 × 1 × 10 000 = **$3 500**. **Rapport ≈ 26×.**

**Pourquoi rien ne l'attrape — le cross-check est CIRCULAIRE [V] :**

- `brain.py:170` : `phase = phase or (state or {}).get("phase") or "P1"`. La cron `50 19 * * 1-5` lance `brain.py` **sans `--phase`**. Donc brain lit la phase **dans `state.json`, que l'EA écrit lui-même** (`mq5:1510,1519`).
- `TargetsValidate()` compare ensuite `ea_vm`/`ea_on_w`/`ea_phase_hint` de `targets.json` à `VmEff()`/`OnWEff()`/`InpPhase` (`mq5:961-967`). Les deux côtés dérivent de la même source erronée → **`mode_mismatch` reste à 0**.
- Et même s'il passait à 1 : `mq5:961` dit explicitement « alarme seulement, mqh = autorité ». **Ça ne bloque aucun ordre.**

**Aggravant — le watchdog peut ressusciter le mauvais profil [V] :**
`watchdog_mt5.sh` fait `screen -S mt5 -X quit` → `pkill -f '[t]erminal64'` → `pkill -9 -f '[t]erminal64'` → `start_mt5.sh`. Un `pkill -9` ne laisse pas MT5 persister les inputs du graphe. `start_mt5.sh` relance le terminal, qui recharge **le dernier profil SAUVEGARDÉ** — potentiellement celui d'avant la bascule, avec `InpPhase=2`.

**Condition de levée** : après ré-attachement, vérifier dans `state.json` **avant toute autre action** que `"phase": "FUNDED"` ET `"governor": {..., "vm": 1.00}` ET `"micro_enabled": 0` ET `"target_equity": 0.00`. Puis **forcer la persistance du profil** (File → Profiles → Save, ou une sortie propre File → Exit plutôt qu'un kill) pour qu'un restart watchdog ne puisse pas ressusciter la phase 2.

### 2.2 — B1 : le binaire déployé n'a jamais été exécuté

**Preuve [V]** :
- `MQL5/Files/state.json` mtime = `Aug 17 13:15`, réécrit chaque minute → **un EA tourne**.
- Journal Experts `MQL5/logs/20260817.log` : `13:03:57.476 book_executor (US100.cash,H1) ERROR kill-file FLAT — EA désarmé` → l'EA est attaché sur le graphe US100.cash H1.
- **`ls MQL5/Files/ | grep -ci spread` → `0`.** Aucun `spread_log_202608.csv`.
- `SampleSpread()` s'exécute inconditionnellement en tête de `OnTimer()` (`mq5:1703`) et écrit dès la première minute où une cotation est fraîche. **L'absence du fichier prouve que le code en mémoire n'est pas le v2.9.**

Le `.ex5` a été remplacé sur disque à 13:03 pendant que MT5 tournait (démarré il y a 22 jours, pid 2928142). MT5 charge le `.ex5` à l'attachement ; l'instance en mémoire reste v2.8. **Le remplacement à chaud n'a pas posé de problème de verrou** (le fichier fait bien 90 922 octets et son sha correspond au build) [V] — mais le binaire est **staged, pas actif**.

**Conséquence** : premier run de v2.9 = sur le compte funded réel. C'est un défaut de processus, pas de code. **Correctif à coût nul** : ré-attacher l'EA v2.9 sur le compte P2 actuel (`<ACCOUNT_ID>`, dont le journal terminal dit `trading has been disabled - disabled on server`, donc aucun ordre n'est physiquement possible), `FLAT` en place, et vérifier en 2 minutes que (a) `spread_log_202608.csv` apparaît, (b) `state.json` continue de battre, (c) le journal Experts logue `SPEC OK v2.2.2 sha 3e7626f6d3fd…`. **Ensuite seulement** basculer de compte.

### 2.3 — B3 : ~~le mécanisme de Max Loss du compte FUNDED n'est pas documenté~~ → **RÉSOLU 2026-08-17**

> ## ✅ RÉSOLU LE JOUR MÊME — plancher **STATIQUE** confirmé
>
> L'opérateur a vérifié sur son compte funded réel le 2026-08-17 : le Max Loss funded est
> **STATIQUE**, 10 % du capital initial ancré au capital initial, il ne monte jamais.
>
> **L'EA avait raison.** `StaticFloor() = $9 000 fixe` est le bon modèle, `LimEff()` est correct,
> le breaker daily-only reste bien dimensionné. **Aucune correction de code.** Le scénario de
> « $600 de marge fantôme » décrit ci-dessous **ne se produira pas**.
>
> Le trou de documentation était réel et l'analyse ci-dessous reste valable comme *raisonnement* —
> elle est conservée pour mémoire. Le fait manquant est désormais gravé en source primaire :
> `PropFirms/ftmo/rules.md` §« Compte FUNDED (post-challenge) — plancher STATIQUE lui aussi ».
> Question tranchée **trois fois** (2026-07-20, 2026-08-01, 2026-08-17) : ne pas la rouvrir.

**Analyse d'origine, conservée pour mémoire (hypothèse depuis INFIRMÉE) :**

**Ce que fait l'EA [V]** : `double StaticFloor() { return ACCOUNT_SIZE_USD*(1.0-MAX_LOSS_FRAC); }` (`mq5:173`) = 10 000 × 0.90 = **$9 000 fixe, jamais recalculé**. `LimEff() = max(DailyFloor, StaticFloor)` (`mq5:176`). Le breaker est **daily-only par conception** (`mq5:177-190`, correctif v2.4 (A)).

**Ce que dit le repo** :
- `PropFirms/ftmo/rules.md:26` — plancher statique, sous le titre `## 2-Step Challenge — Trading Objectives` (`rules.md:20`).
- `rules.md:71-80` — la citation à cliquet est explicitement scopée « **QU'AU CHALLENGE 1-STEP** », tranchée deux fois, ne pas rouvrir.
- `rules.md:90-93` — « Variante 2-step (LA NÔTRE) — plancher statique ».

**Le trou** : ces trois passages portent tous sur le **produit CHALLENGE**. Le compte FUNDED (« FTMO Account ») est un produit distinct. J'ai relu `rules.md` en entier : **aucune ligne, verbatim ou dérivée, ne cite le mécanisme de Max Loss du compte funded.** Les seules lignes scopées funded portent sur le news-trading (`rules.md:131-132`) et le week-end (`rules.md:145-146`).

**Pourquoi c'est le sens dangereux** : si le funded est à cliquet sur le HWM du solde à 00:00 CET, alors à un solde de $10 600 le vrai plancher est $9 600 pendant que l'EA en croit un à $9 000 → **$600 de marge fantôme, soit 6 % du compte**, et le breaker daily ne couvre pas cet écart puisqu'il ne regarde que l'ancre du jour. Ce régime est atteint dès +6 % de performance. La décision « statique » a été prise pour un produit court où le solde dépasse à peine le capital initial ; le funded tourne des mois. **L'argument de non-réouverture de `rules.md:77` ne s'applique pas au produit funded** — ce n'est pas rouvrir un arbitrage tranché, c'est constater qu'il n'a jamais couvert ce produit.

**[NV]** — Je ne peux pas vérifier ceci depuis ce poste. Il faut lire la page « FTMO Account » de ftmo.com ou le tableau de bord du compte. **5 minutes, avant d'armer.**

### 2.4 — La « nuit de validation désarmée » ne valide rien et casse la chaîne targets

**Mécanisme [V]** : `OnTimer()` teste `FileIsExist("FLAT")` en `mq5:1705` et **`return` en `mq5:1715`**. Tout ce qui suit est court-circuité : le rollover (`mq5:1719`), `InvariantCheckM5`, `MicroManage`, et **toute la grille horaire `mq5:1737-1749`** — dont `Do2145Export()` (`mq5:1744`), seul producteur de `market_export.json` (`mq5:1318`).

**Chaînage [V]** : `brain.py:131` appelle `marketdata.load_export(files_dir / "market_export.json")`, et `lib/marketdata.py:48` lève `MarketDataError`.

**Preuve empirique, pas théorique** — extrait littéral de `/home/algo/logs/ftmo_brain.log` :
```
lib.marketdata.MarketDataError: export EA stale 24.1h > 6.0h (généré 2026-08-04 21:45:00)
  — pas de close T-1 fiable, brain refuse d'écrire targets
lib.marketdata.MarketDataError: export EA stale 48.1h > 6.0h (généré 2026-08-04 21:45:00)
  — pas de close T-1 fiable, brain refuse d'écrire targets
```
C'est **exactement la période de FLAT qui a suivi le passage de la Phase 1** (compte désarmé le 2026-08-05). Le mode de panne s'est déjà produit.

**Cascade** : pas d'export → brain refuse d'écrire → `targets.json` vieillit → `TargetsValidate()` renvoie `STALE` au-delà de 26 h (`mq5:958`) → `Do1735` (`mq5:1101-1102`) et `Do2205Rebalance` (`mq5:1163-1167`) **SKIP** en « gestion seule ».

**Donc** : une nuit sous FLAT ne teste ni l'export, ni brain, ni les targets, ni le sizing, ni un seul ordre. Elle teste le heartbeat et `SampleSpread`. Et elle garantit que le lendemain **rien ne peut s'armer avant le cycle export 21:45 → brain 21:50 → rebalance 22:05 du jour même**.

**Ce n'est pas rédhibitoire, mais le plan doit l'intégrer** : retirer `FLAT` **le matin** (bien avant 15:30 Paris, cf. §3.2), pour que la journée se déroule nativement et que la chaîne se ré-amorce le soir même.

**État courant chiffré** : `targets.json` généré `2026.08.17 15:00:02` Paris (par `monday_restamp.py`, cron `0 13 * * 1`). Âge à mardi 22:05 = **31,1 h > 26 h → STALE**. **Le rebalance de mardi soir sera skippé même compte armé**, sauf si brain tourne avec succès lundi 21:50 — ce que le FLAT de ce soir empêche.

---

## 3. RISQUES NON BLOQUANTS

### 3.1 — Le latch `g_flat_today` et la date de retrait de `FLAT`

Chaîne vérifiée :
1. `FlattenAll("kill_flat")` pose `g_flat_today=true` (`mq5:740`) puis `SaveState()` (`mq5:749`) — le latch est **persisté**.
2. Tant que `FLAT` existe, `OnTimer` sort avant `DayRollover()` (`mq5:1715` vs `1719`) → **aucun rollover ne se produit pendant le désarmement** ; `g_anchor_date` reste figé au jour de la pose.
3. Purge : uniquement dans `DayRollover()` (`mq5:1214`), donc **seulement au premier tick suivant le retrait de `FLAT`, ET seulement si le jour Paris a changé**.

**Piège** : retirer `FLAT` le **même jour Paris** que sa pose → pas de rollover → `g_flat_today` reste à 1 → **la journée entière est morte** (tous les créneaux testent `g_flat_today`). Détecté mais non corrigé par `supervisor.py:268-274` (« EA ARMÉ (kill=0) mais flat_today=1 COLLÉ »). Le plan (poser aujourd'hui, retirer demain) évite ce piège — le noter pour ne pas l'enfreindre par impatience.

### 3.2 — Piège horaire : ORB rétroactif entre 16:00 et 20:00 Paris

Au retrait de `FLAT`, `DayRollover()` remet tous les `g_done_*` à false (`mq5:1217-1218`), puis la grille rattrape immédiatement tous les créneaux déjà passés (`mq5:1737-1749`). Si l'heure est ≥ 16:00 : `DoBuildOR()` construit l'OR 15:30-16:00 depuis l'historique M5, puis `Do1600Arm()` — gardé par `hm<2000` (`mq5:1740`) — **arme l'ORB funded plusieurs heures après coup, sur un OR périmé**.

Cas favorable : le broker rejette les stops comme prix invalides (le marché a traversé le niveau) → `RawSend` échoue, alerte, `g_micro_state` reste 0. Cas défavorable : le prix est encore entre les deux bornes → entrée légitime mais hors spec temporelle.

→ **Retirer `FLAT` avant 15:30 Paris**, idéalement au réveil. Après 20:00 c'est également sûr (`hm<2000` bloque l'armement) mais on perd la journée.

### 3.3 — L'ORB funded contourne le cap de marge et tous les caps de jambe

**Sizing [V]** : `mq5:1058-1073`. `risk = FU_ORB_RISK × ACCOUNT_SIZE_USD × OrbTaper0()` = 0.0025 × 10 000 × 1 = **$25**.
- `ACCOUNT_SIZE_USD` = **10000** — vérifié `spec_v22.mqh:13`. **Ce n'est pas 100 000, le sizing n'est pas faux d'un facteur 10.**
- `OrbTaper0()` = clip((10 000 − 9 000)/10 000/0.02) = clip(5) = **1** à l'ouverture du compte (`mq5:219-223`).
- `upp = UsdPerUnit("US100.cash")` = `tick_value/tick_size` (`mq5:259-265`) = 0.010000/0.010000 = **1.0** [V, `state.json:symbol_specs`] → 1 lot = $1/point, notionnel = prix × lots, prix courant 30 127.

| largeur OR | lots | notionnel | % équité | marge (6.667 %) |
|---|---|---|---|---|
| 135 pts (ouverture US typique) | 0.18 | $5 423 | 54 % | $362 |
| 90 pts | 0.27 | $8 134 | 81 % | $542 |
| 40 pts (OR serré) | 0.62 | **$18 679** | **187 %** | $1 245 |

**Le contournement [V]** : la branche funded appelle `PlaceStopOrder` directement, **sans passer par `CapQuantizeTrade`** — laquelle n'est appelée que depuis `Do1735` (`mq5:1110`) et `Do2205Rebalance` (`mq5:1177`). Donc **ni le cap marge 60 %, ni `LegLotCap`, ni `LEG_LEV_CAP_*` ne s'appliquent à l'ORB**. De plus `LegLots(k)` filtre sur `magic == InpMagicBase+k` (`mq5:303`) : une position `MAGIC_FORB` (base+12) est **invisible** à la comptabilité de jambe et au calcul de `need` du cap marge.

Impact réel borné : l'ORB est fermé à 22:00 (`Do2200TimeStop`, `mq5:1140-1156`) **avant** le rebalance de 22:05 ; le seul recouvrement est GER40 17:35 → 22:00 les lundis/mardis, soit $3 500 + jusqu'à $18 700 → marge cumulée ≈ $1 478 = 15 % de l'équité, bien sous le cap de $6 000. **Non bloquant, mais à connaître : ce n'est pas gouverné.**

**Caveat L59** : le risque « $25 » suppose un fill au niveau exact du stop. La leçon L59 mesure que **25 % des barres de stop ouvrent au-delà**. Sur 0.62 lot, un décalage de 10 points coûte $6 supplémentaires ; un gap de 1 % coûte **$187 = 1,87 % du compte**. Le chiffre honnête à retenir n'est pas $25 mais « $25 en médiane, queue à ~$190 ».

### 3.4 — `spec_bounds_breach = 1` : informatif, **vérifié**, mais pas anodin économiquement

`g_spec_breach` est affecté en `mq5:406,427,433,457`, imprimé en `mq5:464`, émis dans `state.json` en `mq5:1543-1544`. **Grep exhaustif du fichier : il n'apparaît nulle part ailleurs. Il ne gate rien.** [V]

Écarts actuels, sur les **swaps uniquement** (les taux de marge collent au modèle à 1.5e-05, `targets.json:mrate_divergence_breach: false`) :

| jambe | live | ancre `spec_v22.mqh` | écart |
|---|---|---|---|
| XAUUSD swap_long | −93.35 | −65.68 (`mqh:97`) | **+42 %** |
| USDJPY swap_long | +2.61 | +0.96 (`mqh:103`) | +82 % (norme targets.json) |
| US100 swap_short | +14.23 | +27.49 (`mqh:110`) | **−48 %** |
| GER40 swap_short | −28.61 | −48.68 (`mqh:116`) | −41 % |

Deux réserves : (a) les ancres datent du **2026-06-10** et ont été mesurées sur **« FTMO-Demo Standard »** (`mqh:93-94`), pas sur un serveur funded Swing — la borne est donc déjà d'une pertinence douteuse ; (b) le livre funded **tient overnight** et L36/L55 établissent que le swap mange la prime : un swap or long 42 % pire que l'ancre de validation n'est pas du bruit cosmétique sur un compte réel. À la ré-init sur le compte funded, `ReadLiveSpecs()` (`mq5:1682`) relira contre les mêmes ancres de juin. **Ne pas classer un flag allumé en « bruit connu » par habitude.**

### 3.5 — Calendrier : aucune urgence à armer, et mardi soir ne tradera pas

- Aujourd'hui = lundi 2026-08-17, jour ON (`targets.json:ea_on_day: 1`). Nuits ON = lundi + mardi (`mq5:143`, `mqh:86`).
- Mardi 18 : dernière nuit ON de la semaine. **Mais son rebalance sera skippé pour cause de targets STALE** (§2.4, 31,1 h).
- Mercredi 19 → vendredi 21 : pas de jambes ON. Et `ea_w_xauusd = 0.0`, `ea_w_usdjpy = 0.0` (§3.6) → **le livre ne fait rien du tout, sauf l'ORB à $25 de risque**.
- Prochaine nuit ON exploitable : **lundi 2026-08-24**.

→ **Armer mardi rapporte un ORB et rien d'autre avant une semaine.** Il n'y a strictement aucun coût d'opportunité à passer 48 h sur B1/B2/B3. C'est le meilleur argument de ce rapport contre la précipitation.

### 3.6 — Le livre funded démarre plus que MONO : il démarre VIDE

Confirmé sur les données du jour, pas sur la mémoire projet [V] :
- `targets.json` : `ea_w_xauusd: 0.0`, `ea_w_usdjpy: 0.0`, `weights: {XAUUSD: 0.0, USDJPY: 0.0}`
- `j1_gate` : `{"enabled": true, "t_off": 160.0, "t_on": 155.0, "n_resume": 10, "suspend": true, "level": 159.505, "reason": "in_zone"}` → USDJPY à 159.505 est dans la zone morte d'hystérésis ; J1 reste OFF jusqu'à **10 clôtures consécutives ≤ 155**.
- Poids or = 0 également (dead-zone).
- `state.json` : `"positions": []`, `last_rebalance` du 2026.08.14 22:05 avec les **quatre** cibles à $0.00.

→ **Les seules sleeves vivantes sur le compte funded seront (a) les jambes ON US100/GER40 les lundis/mardis à `on_w` 0.35, (b) l'ORB funded.** La mémoire projet dit « MONO » ; la mesure dit « plus fin que mono ».

### 3.7 — Fenêtre d'interférence du watchdog pendant la bascule

`watchdog_mt5.sh` (cron `*/3`) ne redémarre que si **les trois** conditions tiennent : session ouverte **ET** âge(`state.json`) > 240 s **ET** `link_state ∈ {DEAD, DISCONNECTED}` (avec re-poll socket de 60 s). Le motif `pkill` est `'[t]erminal64'`, immunisé contre sa propre cmdline. [V]

- **Détacher l'EA seul ne déclenche rien** : `state.json` gèle, mais le terminal reste vivant et le socket broker établi → verdict `CONNECTED` → « trou de ticks normal — PAS de restart ». ✔
- **La fenêtre dangereuse** : pendant le changement de compte, le socket broker tombe. Si le socket reste absent > 60 s alors que `state.json` a déjà > 240 s → verdict `DISCONNECTED` → `quit` + `pkill -9` + relance **en pleine séquence de login**. Combiné à §2.1 (profil non persisté), c'est le chemin vers `InpPhase=2` sur le compte funded.
- Garde-fou existant : anti-boucle max 2 restarts/h, puis alerte critique et STOP.

→ Mitigation sans écriture VPS : garder `FLAT` en place sur toute la durée de la bascule (**le plan le fait déjà — c'est son meilleur choix**), et boucler le login en moins de 4 minutes après le gel de `state.json`.

### 3.8 — Fichiers d'état résiduels : inventaire

| fichier | contenu P2 ? | risque | action |
|---|---|---|---|
| `MQL5/Files/ea_state.json` | **OUI** — `login <ACCOUNT_ID>`, `anchor 10538.93`, `flat_today 1`, `open_days 4` | voir §4.2 | **supprimer** (le plan le prévoit) |
| `MQL5/Files/fills.csv` | **OUI** — l'« archivage » est une **COPIE**, l'original est toujours là (5 506 o, Aug 12 19:30, les deux) | l'EA **appendra** les fills funded à un fichier de fills P2 | séparable *a posteriori* par la colonne `phase` (2 vs 3) — contamine la mesure de coût que v2.9 existe précisément pour permettre |
| `MQL5/Files/swaps_billed.csv` | **OUI — pas archivé du tout** (569 o, Aug 11) | même contamination par append | à archiver aussi |
| `MQL5/Files/market_export.json`, `m5_today.json` | oui mais écrasés par `AtomicWrite` | aucun report, seulement staleness (§2.4) | — |
| `MQL5/Files/FLAT` | — | présent, 0 octet, Aug 17 13:03 | à retirer pour armer |
| `ftmo_live/runtime/{book_state,brain_status,snapshots,alerts_state}.json`, `reconcile_log.csv`, `eod/`, `sod/` | mélangés par date | **aucune de ces structures n'est clefée sur le login** (grep `login|account` dans `reconcile.py` : 0 hit) | hygiène, pas sécurité |

### 3.9 — Type de compte funded : Swing ou Standard ? [NV]

Toute la conception suppose un compte **Swing** :
- `rules.md:132` — Funded **Swing** : « ✓ **EXEMPT** — no news-trading restriction ». Funded **Standard** : fenêtre de 2 minutes avant ET après les news restreintes, **y compris déclenchements de SL/TP**.
- `rules.md:146` — Funded **Swing** : pas de restriction week-end. Funded **Standard** : clôture obligatoire avant le week-end.
- Les ancres de marge `MARGIN_SWING_*` (`mqh:101,107,113,119`) et `MRATE_*` (`mqh:43-46`) sont calibrées Swing.

Conséquence de sizing : **faible**, car à `vm=1` le cap marge 60 % ne mord pas ($3 500 de notionnel ≈ $233 de marge contre un cap de $6 000). Conséquence réglementaire : **binaire**. Le livre ne tient pas sur le week-end (jambes fermées à 09:00 et 15:30 le lendemain), donc la règle week-end ne mord pas ; **la règle news à 2 minutes, si**, sur un compte Standard.

→ **Vérifier le type du compte émis avant d'armer.** Je ne peux pas le lire d'ici.

### 3.10 — Divergence source repo ↔ binaire déployé

Le `.mq5` patché **n'est pas commité**. État vérifié :

| copie | sha256 | version |
|---|---|---|
| repo local `ftmo_live/mt5/book_executor.mq5` | `610c9ea6…6307ff` | **v2.9** (non commité) |
| VPS `~/.wine/drive_c/build/book_executor.mq5` | `610c9ea6…6307ff` | v2.9 ✔ |
| VPS `MQL5/Experts/ftmo_live/book_executor.mq5` | `610c9ea6…6307ff` | v2.9 ✔ |
| **VPS repo `~/projects/Algo_claude/ftmo_live/mt5/book_executor.mq5`** | `89c16d8c…b327f` | **v2.8 — source de vérité git DÉSYNCHRONISÉE du binaire live** |

Le VPS fait bien `git pull --rebase --autostash origin main` toutes les 30 min (`scripts/fetch_alpha_sources.sh:68`) et **push** aussi (`:149`). Mais l'arbre MT5 est **hors du repo** : le pull ne peut pas écraser le `.ex5` ni le `.mq5` déployés. **Aucun risque de déploiement surprise du côté EA.** [V]

En revanche, côté **Python**, `merger sur main EST un déploiement** (brain.py, watchdog, lib/, supervisor) dans les 30 minutes. À garder en tête pendant la fenêtre funded.

Risque résiduel du non-commit : si le VPS était reconstruit depuis git, il redéploierait un v2.8, silencieusement. Et le pin `v22_ea_build` de `targets.json` (`79c6912a…`) ne correspond plus à rien de traçable pour v2.9.

### 3.11 — Espace disque : non-problème, chiffré

`df -h /` → **38 G total, 21 G utilisés, 15 G disponibles, 59 %**. [V]
Croissance de `spread_log_YYYYMM.csv` : 4 jambes × 1 440 min/jour × ~85 o ≈ **490 Ko/jour ≈ 15 Mo/mois**, rotation mensuelle, **aucune purge**. Soit **0,1 % de l'espace libre par mois**. Non-problème. (Et l'échantillonnage ne tourne pas week-ends/marché fermé, cf. §4.3 — le chiffre réel sera ~30 % plus bas.)

---

## 4. ERREURS TROUVÉES DANS LE TRAVAIL D'AUJOURD'HUI

### 4.1 — Erreur de processus : déployer sans jamais exécuter

Voir §2.2. Le binaire est correct, hashé, cohérent, compilé sans erreur — et **n'a jamais tourné une seule fois**. `ls MQL5/Files/ | grep -ci spread` = `0` pendant que `state.json` bat à la minute. Annoncer un déploiement quand on a fait un *staging* est une erreur de qualification. Le correctif coûte 10 minutes sur un compte où le trading est désactivé côté serveur.

### 4.2 — Thèse « breach immédiat » sur `ea_state.json` : **INFIRMÉE**, dans les deux sens

C'est le point où le travail du jour est le plus étayé — et où sa justification est fausse.

**Le garde de bascule de compte existe déjà [V]**, `book_executor.mq5:1625-1637` :
```
long st_login=(long)JjsNum(txt, "account_login");
long cur_login=AccountInfoInteger(ACCOUNT_LOGIN);
if(st_login!=0 && cur_login!=0 && st_login!=cur_login)
  { Print("LoadState: ea_state.json d'un AUTRE compte …"); return; }
```
Le fichier courant contient bien `"account_login":<ACCOUNT_ID>` [V]. Sur le compte funded (login différent, non nul), **l'état est IGNORÉ et `OnInit` ré-ancre** sur `AccountInfoDouble(ACCOUNT_BALANCE)` (`mq5:1685-1690`).

**Et si le garde était contourné**, l'arithmétique ne donne **pas** un breach :
- `DailyFloor()` = 10 538.93 − 500 = **10 038.93** (`mq5:175`)
- `LimEff()` = max(10 038.93 ; 9 000) = **10 038.93** (`mq5:176`)
- `room_daily` = 10 000 − 10 038.93 = **−38.93** dès le premier tick
- `BreakerLine()` = 10 038.93 + 0.3 × 500 = **10 188.93** (`mq5:186-191`), soit **1,89 % AU-DESSUS** de l'équité de départ
- `InvariantCheckM5` (`mq5:1192`) ne déclenche que `if(eq<BreakerLine() && !g_flat_today && OurPositionsExist())` → **sans position, rien ne se passe** ; avec une position, **flatten immédiat**.

→ Le mode de défaillance est une **sur-protection paralysante** (le livre se met à plat dès qu'il ouvre quoi que ce soit), **pas un breach**. La thèse serait juste dans le cas *symétrique* — une ancre héritée **INFÉRIEURE** au solde du nouveau compte — qui abaisserait la ligne de breaker et supprimerait la protection. Ce n'est pas le cas ici : 10 538.93 > 10 000.

**La vraie fenêtre de risque, elle, est réelle et vaut d'être nommée** : le commentaire `mq5:1627-1631` documente que `ACCOUNT_LOGIN` peut lire **0** transitoirement à `OnInit` (avant autorisation serveur), auquel cas le garde login est sauté. Le second garde (`mq5:1638`, `anchor_date != ParisDate()`) ne sauve pas non plus, car l'`anchor_date` du fichier est **`2026-08-17`, c'est-à-dire AUJOURD'HUI**. **La seule journée de l'année où ce fichier peut être chargé à tort est aujourd'hui.** La suppression referme la fenêtre.

**Conclusion** : supprimer `ea_state.json` reste **obligatoire** — pour la justesse, et à cause de cette fenêtre du même jour. Mais il faut cesser de propager « breach immédiat au premier tick » : c'est faux pour cette ancre, et un motif de sécurité faux fait prendre les mauvaises décisions à la marge (ici : il ferait croire que la suppression est le risque n°1, alors que c'est `InpPhase`, §2.1, qui l'est de loin).

### 4.3 — Le patch v2.9 : revue ligne à ligne — aucun bug bloquant trouvé

Points contrôlés un par un, tous **[V]** sauf mention :

- **Fuite de handle : NON.** `FileOpen` unique en `mq5:1409` ; `FileClose(h)` en `mq5:1431` atteint sur tout chemin ayant obtenu un handle valide (les `continue` sont **à l'intérieur** de la boucle `for`, pas des sorties de fonction). Le seul `return` prématuré (`mq5:1410`) est sur `INVALID_HANDLE`, donc sans handle à fermer.
- **`FILE_TXT|FILE_ANSI` + `FileSize` + `FileSeek(END)` : idiome DÉJÀ éprouvé dans ce fichier**, identique à `LogSwapsBilled` (`mq5:1252-1258`) et `LogFill` (`mq5:1441-1447`). `swaps_billed.csv` et `fills.csv` existent sur le VPS avec un contenu valide et lisible → le pattern est validé empiriquement, pas seulement par lecture. Ce n'est pas un risque nouveau.
- **`static datetime last_min` au rechargement** : remis à 0 → un échantillon supplémentaire immédiatement après attachement. Sans effet.
- **`TimeCurrent()` ne progresse pas sans tick** → `m==last_min` reste vrai week-end/marché fermé → pas d'échantillonnage. Comportement souhaité ; corollaire à connaître : **le fichier ne peut pas servir de preuve de vie**.
- **Disque plein** : `FileOpen` renvoie `INVALID_HANDLE` → `return`, `FileWriteString` échoue silencieusement. Pas d'exception, pas de blocage, `OnTimer` poursuit.
- **Ré-entrance** : `OnTimer` n'est pas ré-entrant en MQL5 (mono-thread par EA). Sans objet.
- **Coût CPU** : un open/close fichier + 4 × 5 appels `SymbolInfo*` **par minute** (garde `if(m==last_min) return;`), pas par seconde. Négligeable.
- **État partagé / schéma existant** : `SampleSpread` n'appelle ni `SaveState`, ni `WriteState`, ni `AtomicWrite`, ne touche aucun global hors son propre `static`, et écrit un nom de fichier absent du répertoire (listing `MQL5/Files/` vérifié). **Aucune fonction de trading appelée.** Les garanties annoncées dans l'en-tête du patch sont **exactes**.
- **La chaîne de log du watchdog est préservée** : `watchdog_mt5.sh:init_count` grep littéralement `"book_executor v2.2 INIT"` ; le patch ne touche pas ce `Print` (`mq5:1692`). Correct — c'était un piège évitable, il a été évité.

**Deux défauts mineurs réels** :

1. **Rotation mensuelle sur le mois PARIS, première colonne en heure SERVEUR.** `mq5:1406` utilise `ParisStruct(pd)` pour `spread_log_%04d%02d.csv`, tandis que `mq5:1425` écrit `TsServer()` en première colonne. Autour de minuit le 1er du mois, la frontière de fichier et son propre horodatage divergent d'une heure. Cosmétique, mais c'est exactement la classe de bug que L52/L56 sanctionnent (« ne jamais faire confiance à l'horloge implicite d'un champ »). À corriger au prochain passage.
2. **Placement avant le test de `FLAT` : aucun changement fonctionnel démontré, mais gratuitement risqué.** J'ai tracé le chemin de kill : le bloc `mq5:1705-1716` est inchangé, `FlattenAll` (`mq5:726-750`) est intact, le latch `g_flat_today` (`mq5:740`) et sa persistance (`mq5:749`) sont intacts. **Je n'ai trouvé aucun scénario de défaillance concret.** `FileOpen` en MQL5 ne bloque pas ; un fichier verrouillé renvoie `INVALID_HANDLE` et `SampleSpread` rend la main. **Verdict : pas de bug.** Mais faire passer un chemin de code jamais exécuté **avant** le coupe-circuit, à chaque tick de timer, inverse la priorité pour un bénéfice nul — une alternative à couverture **strictement identique** existe : appeler `SampleSpread()` en première instruction **à l'intérieur** du bloc `FLAT`, et à nouveau juste après `g_killed=false;` (`mq5:1717`). Même échantillonnage désarmé, test de kill en premier. Gratuit.

### 4.4 — `fills.csv` et `swaps_billed.csv` : archivage incomplet

`fills.csv` et `fills.csv.p2_archive_20260817` font **tous deux 5 506 octets, mtime Aug 12 19:30** → c'est une **copie**, pas un déplacement. L'EA continuera d'appender les fills funded dans un fichier qui contient les fills P2. `swaps_billed.csv` (569 o, Aug 11) **n'a pas été archivé du tout**.

Ce n'est pas un risque de trading. Mais c'est un risque **pour l'objet même du patch v2.9** : le patch existe pour rendre le coût mesurable (`fills.csv` ne journalise ni bid ni ask, cf. l'en-tête du patch), et on démarre cette mesure sur un ledger déjà mélangé. La colonne `phase` (2 vs 3) permet la séparation *a posteriori* — c'est une chance, pas une conception.

---

## 5. AFFIRMATIONS QUE JE N'AI PAS PU VÉRIFIER

| # | Affirmation | Pourquoi non vérifiable ici | Ce qu'il faudrait |
|---|---|---|---|
| ~~NV1~~ | ~~**Le Max Loss du compte FUNDED est statique à −10 % de l'initial**~~ | **✅ VÉRIFIÉ ET CONFIRMÉ le 2026-08-17** par l'opérateur sur son compte funded réel : plancher **STATIQUE**, l'EA avait raison (`mq5:173`) | RIEN À FAIRE — gravé dans `rules.md` §« Compte FUNDED ». Bloquant **levé** |
| NV2 | Le compte funded émis est un **Swing** et non un **Standard** | pas d'accès au portail FTMO | tableau de bord du compte. Détermine l'applicabilité des règles news 2 min (`rules.md:131-132`) et week-end (`:145-146`) |
| NV3 | Le solde d'ouverture du compte funded est **exactement 10 000.00** | pas d'accès au compte | `ACCOUNT_SIZE_USD` est figé à 10000 (`mqh:13`) et n'est **pas** lu depuis le serveur. Un compte à un autre montant rendrait **tous** les planchers et le sizing ORB faux. À lire dans MT5 après login |
| NV4 | Le serveur funded est en **EET** (`InpServerTZOffsetMin=60` correct) | dépend du serveur du nouveau compte | vérifié sur le serveur actuel (`state.json` : `ts_server 16:10:57` vs `ts_paris 15:10:57` = +60). À re-vérifier après login, d'un coup d'œil |
| NV5 | Les symboles `XAUUSD`, `USDJPY`, `GER40.cash`, `US100.cash` existent avec ces noms exacts sur le serveur funded | idem | `OnInit` renvoie `INIT_FAILED` si un symbole manque (`mq5:1679-1680`) — fail-safe, mais il faut **lire le journal Experts** pour le voir |
| NV6 | Le comportement de `FileOpen`/`FileSeek` de v2.9 **sous Wine**, en conditions réelles | le binaire n'a jamais tourné (§2.2) | ré-attacher sur le compte P2 et constater l'apparition de `spread_log_202608.csv`. **C'est le blocant B1** |
| NV7 | MT5 restaure bien `InpPhase=3` après un `pkill -9` du watchdog | exigerait de tuer un process — **interdit par le mandat lecture seule** | à traiter par la procédure (sauvegarde explicite du profil, §6), pas par le test |
| NV8 | `reconcile.py` se comporte correctement à cheval sur deux comptes | grep `login|account` dans `reconcile.py` → 0 hit ; je n'ai pas lu ses 22 317 octets en entier | relecture ciblée de `reconcile.py` avant le premier EOD funded |
| NV9 | Le pin `v22_ea_build: 79c6912a…` de `targets.json` correspond à quoi | ce commit n'est pas rattachable au binaire v2.9 non commité (§3.10) | commiter le `.mq5` et régénérer le pin |

---

## 6. CHECKLIST OPÉRATEUR CORRIGÉE

### Phase 0 — AVANT de toucher au VNC (bloquants)

| # | Action | Critère de sortie |
|---|---|---|
| 0.1 | Lire sur ftmo.com / le tableau de bord : mécanisme de **Max Loss du compte FUNDED** (statique −10 % de l'initial, ou cliquet sur le HWM du solde EOD ?) | Réponse écrite et sourcée. **Si cliquet → NO-GO** jusqu'à correction de `StaticFloor()` (`mq5:173`) : l'EA serait sous-protecteur dès +6 % |
| 0.2 | Vérifier le **type** du compte funded (Swing / Standard) et son **solde d'ouverture exact** | Swing confirmé ; solde = 10 000.00 (sinon `ACCOUNT_SIZE_USD` `mqh:13` est faux → NO-GO) |
| 0.3 | **Faire tourner v2.9 une première fois** : ré-attacher l'EA sur le compte P2 **actuel** (`<ACCOUNT_ID>`, trading désactivé serveur), `FLAT` en place, `InpPhase` inchangé | `spread_log_202608.csv` apparaît dans `MQL5/Files/` **ET** `state.json` continue de battre à la minute **ET** le journal Experts logue `SPEC OK v2.2.2 sha 3e7626f6d3fd…` |
| 0.4 | Décider du sort de la recommandation **« funded vm 0.85 »** | **Elle est MORTE en l'état.** `FU_VM` est un `#define` (`spec_v22.mqh:73`) consommé par `VmEff()` (`mq5:164`) ; **il n'existe aucun input**. La changer impose d'éditer un `.mqh` **généré** (`mqh:2-3` : « NE PAS ÉDITER À LA MAIN »), donc de regénérer depuis `spec_v22.yaml`, ce qui casse `PIN_MQH_SHA256` (`ftmo_live/lib/__init__.py:35`) et impose un re-gel de spec + rebuild + redéploiement complet. **Décision : partir à `FU_VM=1`, ou repousser la bascule d'une fenêtre de re-gel (samedi).** Pas de troisième voie |
| 0.5 | Archiver **par déplacement** (pas copie) `fills.csv` et `swaps_billed.csv` | les deux originaux absents de `MQL5/Files/` |

### Phase 1 — Bascule VNC (garder `FLAT` en place du début à la fin)

| # | Action | Critère de sortie |
|---|---|---|
| 1.1 | Vérifier que `MQL5/Files/FLAT` **existe** avant de commencer | présent (il l'est : 0 o, Aug 17 13:03) |
| 1.2 | Noter l'heure. **À partir du détachement de l'EA, la fenêtre watchdog s'ouvre à T+4 min** (§3.7) | horaire noté |
| 1.3 | Détacher l'EA du graphe US100.cash H1 | EA retiré |
| 1.4 | **Se connecter au compte funded — objectif < 4 minutes** (identifiants prêts, copiés-collés à l'avance) | journal terminal : `authorized on <serveur>` avec le **nouveau login** |
| 1.5 | Relever et noter : **login**, **solde**, **nom du serveur**, **décalage horaire serveur** | solde = 10 000.00 ; serveur EET (sinon corriger `InpServerTZOffsetMin`) |
| 1.6 | **Supprimer `MQL5/Files/ea_state.json`** (l'archive `.p2_archive_20260817` reste) | fichier absent |
| 1.7 | Ré-attacher `book_executor` sur un graphe **US100.cash H1**, avec `InpPhase = 3` | dialogue d'inputs fermé sur `InpPhase=3` |
| 1.8 | **Ré-activer AlgoTrading** (le changement de compte le désactive silencieusement) | bouton vert dans MT5 |
| 1.9 | **Sauvegarder explicitement le profil** (File → Profiles → Save) — sinon un `pkill -9` du watchdog ressuscite `InpPhase=2` (§2.1, §3.7) | profil sauvegardé |

### Phase 2 — Vérification post-attachement (aucune est optionnelle)

Lire `MQL5/Files/state.json` et **exiger les six valeurs suivantes** :

| champ | valeur exigée | signification si faux |
|---|---|---|
| `"phase"` | `"FUNDED"` | **STOP** — `InpPhase` mal réglé, §2.1 |
| `"governor": {"vm": …}` | `1.00` | **STOP** — 16,8× la taille prévue |
| `"micro_enabled"` | `0` | `MicroEnabled()` (`mq5:170`) contredit la phase 3 |
| `"target_equity"` | `0.00` | `PhaseTarget()` (`mq5:169`) contredit la phase 3 |
| `"anchor_balance"` | = solde réel du compte funded (**pas 10538.93**) | **STOP** — `ea_state.json` mal purgé, §4.2 |
| `"static_floor"` | `9000.00` | incohérence `ACCOUNT_SIZE_USD` |

Puis dans le **journal Experts** : `SPEC OK v2.2.2 sha 3e7626f6d3fd…` et `book_executor v2.2 INIT — phase 3, serveur−Paris 60 min, vm_eff 1.0, micro OFF, magic 220500`.
Puis vérifier l'apparition de `spread_log_202608.csv` (confirme que c'est bien v2.9 qui tourne).
Enfin, noter `spec_bounds_breach` et son détail sur le **nouveau** serveur (§3.4) : le comparer aux écarts P2 ci-dessus, ne pas le classer « bruit connu » sans regarder.

### Phase 3 — Nuit désarmée, en connaissant sa vraie valeur

**Ce qu'elle valide** : que l'EA v2.9 tient, écrit `state.json` et `spread_log`, ne crashe pas, et ne passe aucun ordre.
**Ce qu'elle ne valide PAS** : l'export, brain, targets, le sizing, le moindre ordre — le `return` de `mq5:1715` court-circuite tout.
**Ce qu'elle CASSE** : `market_export.json` ne sera pas régénéré à 21:45 → `brain.py` lèvera `MarketDataError` à 21:50 → `targets.json` ne sera pas réécrit (§2.4, preuve dans `logs/ftmo_brain.log`).

→ L'accepter en connaissance de cause, et **ne pas s'étonner d'une alerte brain le lendemain matin : elle sera attendue, pas anormale.**

### Phase 4 — Armement

| # | Action | Critère de sortie |
|---|---|---|
| 4.1 | Retirer `MQL5/Files/FLAT` **le matin, avant 15:30 Paris** — impérativement un **jour Paris différent** de celui de la pose | §3.1 (latch collé si même jour) et §3.2 (ORB rétroactif si 16:00-20:00) |
| 4.2 | Vérifier dans les 2 minutes : `"kill": 0` **ET** `"flat_today": 0` | si `kill=0` mais `flat_today=1` → le rollover n'a pas eu lieu, la journée est morte ; `supervisor.py:268-274` alerte |
| 4.3 | Vérifier `"anchor_balance"` = solde à 00:00 Paris et `"daily_floor"` = ancre − 500 | rollover correct (`mq5:1212-1213`) |
| 4.4 | **Ne rien attendre de la première soirée avant 22:05** : le rebalance exige que l'export 21:45 **puis** brain 21:50 aient réussi ce jour-là | à 21:55, vérifier `"targets_status": "OK"` et `"targets_age_h" < 1` |
| 4.5 | À 22:06, vérifier `last_rebalance` dans `state.json` | cibles cohérentes avec `on_w 0.35 × vm 1 × equity` ≈ **$3 500** par jambe ON — **si vous lisez ~$90 000, coupez immédiatement (`FLAT`)** |

### Rappel de calendrier

Mardi 18 : les targets seront **STALE de 31,1 h** → **le rebalance sera skippé même armé** (§2.4). Mercredi 19 → vendredi 21 : aucune jambe ON, poids or et J1 à zéro → **le livre ne fait rien sauf l'ORB à $25 de risque**. Première nuit ON réellement exploitable : **lundi 2026-08-24**.

**Il n'y a aucun coût d'opportunité à consacrer les 48 prochaines heures à NV1, NV2, B1 et B2.**
