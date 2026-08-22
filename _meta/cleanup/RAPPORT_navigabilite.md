# Audit de navigabilité — 2026-08-22

Scope : fichiers markdown trackés par git, plus quelques fichiers de code cités comme faisant foi
(`.github/workflows/auto-merge.yml`, `ftmo_live/lib/`, `dsr.py`). Recherche effectuée : (1) tous
les liens markdown `[texte](chemin)` du dépôt, résolus contre le système de fichiers ; (2)
`tools/check_register_integrity.py`, exécuté dans le répertoire principal ; (3) comparaison
ciblée entre affirmations de `CLAUDE.md` / README des dossiers et l'état vérifiable (code, dates de
dernier commit, contenu réel). Ce rapport **liste et hiérarchise**, il ne corrige pas.

Constat de méthode d'abord : **zéro lien markdown `[texte](chemin)` mort** sur l'ensemble du dépôt
tracké — la convention de citation dominante ici est le chemin entre backticks en prose, pas le
lien cliquable, donc les problèmes trouvés ci-dessous viennent d'une lecture ciblée des documents
« source de vérité », pas d'un lien HTML cassé.

---

## Sévérité haute — contredit l'état courant, à corriger avant qu'un lecteur externe ne s'y fie

### 1. `CLAUDE.md` §CI décrit un mécanisme d'auto-merge qui ne correspond pas à `.github/workflows/auto-merge.yml`

Deux écarts vérifiés en lisant le workflow ligne à ligne :

- **`ftmo_live/` est absent des chemins hard-fail.** `CLAUDE.md:76` liste
  `Futures/live/`, `Portfolio/`, `strategies/`, `.github/`, `*.mq5`. Le fichier `SENSITIVE` réel
  (`auto-merge.yml:56`) matche exactement cette liste — `ftmo_live/` n'y figure pas, alors que
  c'est le chemin du code Python **réellement déployé** par le pull VPS toutes les 30 minutes (voir
  `docs/ARCHITECTURE.md` §4). Une PR qui ne touche que `ftmo_live/brain.py` n'est bloquée que par la
  restriction « tout sous `_automation/` », pas par un garde-fou nommé pour le live.
- **Le label `needs-human-review` n'est pas ce que `CLAUDE.md` décrit.** `CLAUDE.md:76` dit qu'un
  chemin hard-fail fait « étiqueter la PR `needs-human-review` au lieu d'auto-merger ». Lu dans le
  workflow : le hard-fail (`GARDE 1`, chemins sensibles / `*.mq5`) exécute `exit 1` et arrête le job
  — il n'y a **aucun appel `addLabels`** à cet endroit. Le seul endroit qui pose
  `needs-human-review` est `GARDE 3` (`auto-merge.yml:104-108`), déclenché par un critère différent
  (fichiers hors `_automation/`). Une PR qui trébuche sur `GARDE 1` échoue silencieusement côté
  labels — elle n'est pas marquée pour revue humaine, contrairement à ce que dit la constitution.

Trouvaille indépendante confirmée par `Multi_Asset/research/active/orb_cost_funded_2026-08/AUDIT_PR429_2026-08-18.md`
§F, qui avait déjà noté le premier écart lors d'un audit de PR réel.

### 2. `_meta/current_focus.md` cite un chiffre que `CLAUDE.md` déclare caduc

`_meta/current_focus.md:32` : « Book référence = A+B : SR analytique 2.31 ». Or `CLAUDE.md`
§Portfolio context est explicite : *« L'ancien 2.31 est CADUC (…) Fourchette défendable 0.57 (A
seul) → 1.85 (A + proxy B optimiste) »* (recalc 2026-07-29). Le fichier n'a pas été retouché depuis
**2026-06-10** (`git log`) — deux mois avant la dépréciation du chiffre qu'il cite — alors que son
propre en-tête dit *« Mettre à jour à chaque session »*. Un lecteur qui ouvre ce fichier avant
`CLAUDE.md` repart avec un chiffre que le dépôt a lui-même rétracté.

### 3. `PropFirms/README.md` décrit un état de véhicules antérieur à deux décisions majeures

Table §Scope : `Tradeify | ACTIVE (Strategy C candidate)`, `Topstep | EVALUATED (abandoned for C)`.
Deux faits la contredisent, tous deux dans `CLAUDE.md` :
- Strategy C / Tradeify est **ANNULÉ depuis 2026-06-10** (FTMO ne finance pas les futures CME —
  raison du pivot recherché à l'époque — mais le véhicule Tradeify lui-même est mort).
- Le gel « toutes les firmes futures sont daily-flat ⇒ écartées » a été **LEVÉ le 2026-07-30**
  (L51) : Apex/Topstep/MFFU repassent « évaluables au cas par cas », pas « EVALUATED (abandoned) ».

Fichier non modifié depuis **2026-05-25** (`git log`) — antérieur aux deux événements. Le dossier
`PropFirms/ftmo/program_2026-06/` documente correctement l'état FTMO ; c'est la table de synthèse
`PropFirms/README.md` qui n'a pas suivi.

### 4. `_meta/research_active.md` — et le pointeur correspondant dans `CLAUDE.md` — n'indexe pas le programme de recherche le plus actif du dépôt

`_meta/research_active.md` est vérifié 2026-05-30 (restructuré 2026-07-30 pour la limite de
caractères, sans mise à jour de fond). `CLAUDE.md` §Research history pointe dessus pour la liste des
« chantiers ouverts ». Or la totalité du programme `Multi_Asset/research/active/` daté 2026-07 et
2026-08 — une trentaine de dossiers, source des leçons L51 à L60, qui est *le* corps de recherche
qui a produit le livre actuellement en live — n'y figure pas. Un lecteur qui suit le pointeur
`CLAUDE.md → _meta/research_active.md` pour « voir ce qui est en cours » manque l'essentiel de ce
qui est réellement en cours. (Corrigé côté lecteur dans `Multi_Asset/README.md`, nouvellement
écrit par cet audit, qui signale explicitement le trou plutôt que de renvoyer vers le fichier
périmé.)

---

## Sévérité moyenne

### 5. Root `README.md` cite un fichier qui n'est pas suivi par git

`README.md` (§Reading this repository) : *« Then `_meta/roadmap_ftmo_2026.md` for where the work
is going »*. Ce fichier existe sur le disque de cette session (confirmé) mais apparaît en `??`
(non suivi) dans `git status` — il n'a jamais été commité. Sur un clone frais du dépôt, ce lien est
mort. Soit le fichier doit être ajouté à git, soit la citation doit être retirée ou remplacée ; les
deux sont hors du périmètre de cet audit (fichier non suivi = territoire d'une autre session selon
la consigne de cette tâche).

### 6. Scripts historiques à la racine, non documentés dans la carte du dépôt, datés avril-mai 2026

`tsmom_live.py`, `hyperliquid_client.py`, `monitor.py`, `notifier.py`, `run_tsmom.sh`,
`run_delta_neutral.sh`, `challenge_state.db` sont trackés à la racine, tous antérieurs au 22 mai
2026 (dernier commit les touchant), et absents de la carte du dépôt dans `README.md` (qui ne liste
que des dossiers). Ce sont les scripts d'exécution Hyperliquid-testnet d'origine des Strategies A/B
— **prédatent** `strategies/{tsmom_v2_propfirm,delta_neutral}/` et le système actuellement en live,
`ftmo_live/`. Un lecteur pressé peut confondre `tsmom_live.py` (racine) avec le code live actuel.
Aucune contradiction factuelle ici — juste une racine encombrée sans étiquette « historique ».

### 7. `Futures/live/orb_floor_ftmo/` — chemin « live » pour un vehicule REJETÉ

Vit sous `Futures/live/`, aux côtés du code live réel (`strategy_c_live/`), mais son propre
`DEPLOYMENT.md` conclut *« NO-GO au coût CFD US100 réaliste. KILL VÉHICULE FTMO 2-STEP »*
(2026-06-09). Le nom du dossier parent (`live/`) suggère à tort qu'il s'agit d'infrastructure
active. `Futures/README.md` (nouvellement écrit) signale ce statut explicitement.

---

## Sévérité basse — clutter, sans impact sur l'exactitude

### 8. `Claude Vault/` à la racine — vault Obsidian par défaut, jamais rempli

Quatre fichiers trackés : `Bienvenue.md` (note de bienvenue Obsidian par défaut, jamais supprimée —
elle invite explicitement à « supprimer cette note et faire ce coffre vôtre »), `Random thoughts.md`
et `To do's list.md` (vides), `Trading strategy ideas.md` (deux mots : « Momentum Crypto »). Aucun
contenu de valeur ; se présente comme un dossier de premier niveau dans tout listing de repo à côté
de `Portfolio/` ou `ftmo_live/`.

### 9. `outputs/`, `infra/`, `_downloads_logs/` — trackés, sans README, contenu hétérogène

`outputs/` : deux PNG de backtest orphelins. `infra/` : trois snapshots de crontab VPS
(`crontab_vps_2026-06-1{2,3,5}.txt`) — date, pas d'index de quel est le courant. `_downloads_logs/` :
logs et un script de téléchargement Dukascopy/Binance anciens. Aucun n'était dans la liste des
dossiers explicitement demandés pour cet audit ; signalés ici pour information, non traités.

### 10. Chaîne de supersession à deux niveaux, correctement étiquetée mais profonde

`STRATEGY_RESEARCH_LOG.md` (juin 2026) se dit superseded par l'ancien `README.md` racine (devenu
`docs/RESEARCH_JOURNAL_2026-05.md` lors de la réécriture de cette session, commit `fb61cb33`), qui
est lui-même désormais superseded par le nouveau `README.md`. Chaque maillon est correctement
étiqueté « superseded » dans le fichier suivant — ce n'est pas une contradiction, juste une pile de
trois documents historiques à traverser si quelqu'un cherche l'origine d'un chiffre ancien
(ex. le "SR 2.31" du point 2 ci-dessus vient précisément de cette chaîne).

---

## Vérifié sain

- **0 lien markdown `[texte](chemin)` mort** sur l'ensemble des `.md` trackés.
- `tools/check_register_integrity.py`, exécuté dans le répertoire principal (jamais un worktree,
  par consigne) : `REGISTER INTEGRITY: clean`, chaîne de ledger monotone `[108, 112, 115, 117]`.
- Les deux documents produits par cet audit (`docs/ARCHITECTURE.md`, `docs/RESEARCH_METHOD.md`) ne
  citent que des chiffres relus directement dans le code au moment de l'écriture : le mécanisme de
  scellement de spec (`ftmo_live/mt5/book_executor.mq5:955,1668`, `ftmo_live/lib/spec.py`), le bug
  de `rf` par défaut dans `dsr.py` (docstring du module, daté 2026-08-04), le bug `std_sr_trials=1.0`
  (`Multi_Asset/research/active/reaudit_vehicule_2026-08/PREREGISTRATION.md`), et le cycle complet
  pré-enregistrement → verdict de `Multi_Asset/research/active/gold_cpi_eve_2026-08/`.

## Priorité suggérée si quelqu'un traite cette liste

Corriger d'abord le point 1 (CI) et le point 3 (`PropFirms/README.md`) — ce sont les deux cas où un
document tracké affirme quelque chose de vérifiablement faux sur l'état présent, plutôt que
simplement périmé. Le point 2 et le point 4 sont des staleness ordinaires (fichier pas remis à jour)
plutôt que des erreurs actives. Les points 5 à 10 sont du confort de lecture, pas de l'exactitude.
