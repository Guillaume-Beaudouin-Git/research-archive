# Déploiement — échantillonneur de spread natif FTMO (EA v2.9)

**Objet** : obtenir une mesure de coût **prise sur le compte FTMO lui-même**, et cesser d'importer
des coûts d'un autre broker. C'est la correction de l'erreur qui a produit un kill erroné de l'ORB
le 2026-08-13 (coût mesuré sur `deep_history_utc`, appliqué à une stratégie exécutée chez FTMO —
interdit par L33).

**Statut : PATCH ÉCRIT, NON COMPILÉ, NON TESTÉ.** Rien ne part en production sans les étapes 2
et 3 ci-dessous.

➡ **Procédure d'exécution pas à pas : `RUNBOOK_DEMO_SPREAD.md`** (compte démo, 7 phases).
Ce fichier-ci décrit le patch et ses garanties ; le runbook décrit les gestes.

⚠ **Correction 2026-08-14** : la compilation ne demande **pas** MetaEditor en GUI. Elle se fait
en headless sous wine **sur le VPS** (`wine MetaEditor64.exe /compile:C:\build\… /log`, chemin
sans espaces obligatoire — cf. `ftmo_live/RUNBOOK_BURNIN_SWING.md` §Recompilation future,
précédent `mt5/build_2026-07-26_v28.log` : 0 errors / 0 warnings).

---

## 1. Ce que le patch fait, et ce qu'il ne fait pas

`ftmo_live/mt5/book_executor.mq5` — **+53 lignes, 0 suppression**.

- Une fonction neuve `SampleSpread()`, appelée depuis `OnTimer()`.
- Écrit **un fichier NEUF** `spread_log_YYYYMM.csv` (rotation mensuelle) :
  `ts_server, ts_paris, symbol, bid, ask, spread_pts, spread_bps`
- Une salve par minute, une ligne par jambe cotée.
- Garde de fraîcheur : une cotation de plus de 120 s est ignorée (marché fermé ou flux coupé ⇒
  un prix figé n'est pas un prix — L60).

**Garanties de non-régression** *(vérifiées, pas supposées)* :

| | |
|---|---|
| appels de trading dans le bloc | **AUCUN** (`OrderSend`, `PositionClose`, `FlattenAll`, `SetError`, `SaveState`, `WriteState` — zéro occurrence) |
| schémas existants modifiés | **AUCUN** — `fills.csv`, `state.json`, `ea_state.json`, `swaps_billed.csv` intacts |
| `spec_v22.mqh` | **NON TOUCHÉ** ⇒ `PIN_MQH_SHA256 = d8d3dcb1…` reste valide, **pas de re-gel de spec** |
| `SPEC_SHA256` (contrôle de `targets.json`) | non affecté |
| équilibre des accolades | delta inchangé (−1 **pré-existant**, dû à des accolades dans des littéraux) |
| échec d'écriture | `FileOpen` raté ⇒ `return` silencieux, **jamais bloquant** |

**Placement délibéré** : l'appel est **AVANT** le test du kill-file `FLAT`. On veut la mesure
**même EA désarmé** — c'est tout l'intérêt : mesurer sans risquer un centime. Le compte est
actuellement flat-latché, donc sans ce placement le logger ne produirait rien.

---

## 2. Compilation et test — À FAIRE AVANT TOUT DÉPLOIEMENT

1. Compiler **en headless sur le VPS** (pas de GUI), exiger **0 erreur / 0 warning** :
   `scp` du `.mq5` + `.mqh` vers `~/.wine/drive_c/build/`, puis
   `wine ./MetaEditor64.exe /compile:C:\\build\\book_executor.mq5 /log`, puis
   `iconv -f UTF-16LE -t UTF-8 ~/.wine/drive_c/build/book_executor.log`.
2. Attacher l'`.ex5` compilé sur un **graphe DEMO** (jamais le compte funded en premier).
3. Laisser tourner **≥ 30 minutes en séance**, puis vérifier dans `MQL5/Files/` :
   - `spread_log_YYYYMM.csv` existe, en-tête correct ;
   - ~1 ligne par minute et par jambe cotée, pas de doublon de minute ;
   - `spread_bps` d'un ordre de grandeur plausible (**US100 ≈ 0.4-1.1 bps** hors ouverture) ;
   - **`fills.csv`, `state.json`, `ea_state.json` inchangés dans leur format.**
4. Vérifier que le heartbeat `state.json` continue de s'écrire à la seconde (le logger ne doit
   pas ralentir `OnTimer`).

**Si l'un de ces points échoue, on s'arrête.** Aucune de ces vérifications n'est optionnelle.

---

## 3. Déploiement

**Fenêtre : SAMEDI, marché fermé.** Ordre impératif — le binaire AVANT le merge.

1. Copier l'`.ex5` compilé vers le VPS (`MQL5/Experts/`), remplacer l'ancien.
2. Recharger l'EA sur le graphe (VNC). ⚠ **Vérifier que l'AlgoTrading est bien RALLUMÉ** — un
   rechargement ou un changement de compte le désactive silencieusement.
3. Contrôler `state.json` : `heartbeat_epoch` avance, `kill` et `mode_mismatch` inchangés.
4. **Ensuite seulement** : merger la PR. ⚠ Le VPS pull `main` toutes les 30 min, donc **merger EST
   un déploiement** du côté Python — ici le patch est MQL5-only, donc le merge ne déploie rien,
   mais l'ordre reste la règle.
5. Mettre à jour le pin `v22_ea_build` dans `ftmo_live/lib/__init__.py` avec le commit de merge.
6. **Ne jamais squash-merger** un lot touchant la chaîne de spec.

**CI** : `ftmo_live/` est un chemin **hard-fail** ⇒ la PR sera étiquetée `needs-human-review` et
**ne s'auto-mergera pas**. C'est le comportement attendu, pas une panne.

---

## 4. Récupération des données

```
ssh -o ControlMaster=auto -o ControlPath=/tmp/cc-ftmo-%r@%h:%p -o ControlPersist=300 \
    -i ~/.ssh/hetzner_algo_claude algo@<VPS_IP> \
    'cat "/home/algo/.wine/drive_c/Program Files/FTMO Global Markets MT5 Terminal/MQL5/Files/spread_log_202608.csv"'
```

**Ce fichier ne doit JAMAIS entrer dans git** (règle : pas de blobs data dans le dépôt). Volume :
~2 Mo/semaine, rotation mensuelle par construction. Purger les mois déjà tirés.

---

## 5. Ce que la mesure débloque, et en combien de temps

| question | ce qu'il faut | délai réaliste |
|---|---|---|
| **Spread FTMO natif à l'heure de l'ORB** | le logger seul | **~2 semaines** (≈450 min dans la fenêtre 16:00-16:10, plusieurs milliers d'observations sur la séance entière) |
| Profil horaire complet, 4 jambes | le logger seul | ~2 semaines |
| Vérification du swap contre facture | déjà possible | fait |
| **Dérapage d'un stop AU-DELÀ de l'ask** | logger **+ nouveaux fills** | **lent** — le micro-ORB produit ~6 fills/mois ⇒ ~10 mois pour 60 |

⚠ **Les 12 fills historiques ne seront pas décomposables** : le logger démarre au déploiement, il
n'y a pas de spread rétroactif. Seuls les fills **futurs** se décomposent en
`(ask_au_déclenchement − niveau)` + `(fill − ask)`.

**Conséquence honnête sur l'ORB** : dans ~2 semaines on saura si le coût de spread natif est
proche de 1.06 bps RT (auquel cas 2018-2026 passe R2 avec 63 % de marge) ou nettement au-dessus.
On ne saura **pas** encore trancher la part de dérapage, qui est la différence entre « 2018-2026
passe » et « seul 2022-2026 passe ». **Ne pas allumer l'ORB avant d'avoir les deux.**
`FU_ORB_RISK` reste à **0** à la bascule funded.

---

## 6. Ce que ce patch NE règle pas

- La **concentration de régime** du gross ORB (t 0.62 / 0.10 / 1.05 / **3.72** par période de
  4 ans, **avant tout coût**). Aucune mesure de frais ne répond à ça.
- Le choix de l'échantillon 2018-2026, **fait après avoir vu les résultats**. Il faut un test
  pré-enregistré vers l'avant, avec la date de départ justifiée sur un critère de **régime de
  coût** décidé indépendamment de la performance.
