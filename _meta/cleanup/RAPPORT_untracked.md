# Rapport — tri des fichiers non suivis (2026-08-22)

Tri de l'ensemble des fichiers non suivis du dépôt (`git status --porcelain | grep '^??'`),
845 entrées de premier niveau / 3035 fichiers une fois les répertoires dépliés. Détail
exhaustif par entrée : `_meta/cleanup/inventaire_untracked.csv` (846 lignes, header compris).

## Chiffres

| Destination | Fichiers | Volume |
|---|---:|---:|
| COMMIT | 1899 | 44.08 Mo |
| IGNORE (gitignoré, laissé sur disque) | 1001 | 796.92 Mo |
| DELETE (supprimé du disque) | 135 | 4.76 Mo |
| **Total analysé** | **3035** | **845.76 Mo** |

Volume ajouté au dépôt par cette PR : **44.08 Mo** (1899 fichiers), sous le plafond de 50 Mo.
Répartition par lot de commit :

| Commit | Fichiers | Insertions |
|---|---:|---:|
| `.gitignore` (nouveau bloc daté) | 1 | 54 lignes |
| `Multi_Asset/` | 754 | 105 465 |
| `PropFirms/ftmo/program_2026-06/` | 652 | 182 709 |
| `data/` (hors ftmo_portfolio cache/node_modules) | 323 | 225 515 |
| `yt_strategy_replications/` | 139 | 10 307 |
| Racine + `_audit/` + `_meta/` + `ftmo_profile_study/` + `strategies/trend_futures/` | 31 | 6 270 |

Aucun chemin de production (`ftmo_live/`, `data/ftmo_portfolio/v22/`, `Portfolio/`,
`strategies/{tsmom_v2_propfirm,delta_neutral}`, `_automation/`, `scripts/`, `.github/`) n'a été
déplacé, renommé ou modifié — seuls des fichiers nouveaux ont été ajoutés (`strategies/trend_futures/`
est une sleeve nouvelle, pas une des deux sleeves live existantes).

## Méthode de tri

Un fichier est **COMMIT** s'il est un livrable qu'un lecteur externe au projet devrait pouvoir
lire pour comprendre la recherche (rapport, préregistration, code, résultat léger — CSV/JSON/PNG
de quelques dizaines à quelques centaines de Ko). Il est **IGNORE** s'il est régénérable
(cache, sortie de pipeline, blob binaire de données) — laissé intact sur disque, seulement retiré
de la vue git via `.gitignore`. Il est **DELETE** seulement s'il est un déchet sans fonction
(artefact d'éditeur, cache npm interne, symlink cassé, scratch de test).

Règles opérationnelles (appliquées de façon uniforme, cf. script de catégorisation) :
- **Tout `.parquet`, `.npy`, `.csv.gz`** → IGNORE (blob binaire ou export compressé, jamais commité
  par gouvernance du dépôt — cf. CLAUDE.md « jamais de blobs data dans git »), *sauf* les ~90
  parquets déjà trackés avant ce tri (legacy non rouvert).
- **Tout dossier littéralement nommé `cache/`, `_cache/`, `out/`, `node_modules/`** → IGNORE
  wholesale. Convention déjà établie dans le dépôt : 3 dossiers de recherche non suivis avaient
  déjà leur propre `.gitignore` local avec exactement ce motif (`decorrelated_sleeves_2026-07`,
  `mr_intraday_grille_2026-08`, `oxfordstrat_109_audit`) — le tri généralise ce motif au niveau
  racine plutôt que de multiplier les `.gitignore` locaux.
- **Symlinks absolus** : `PropFirms/ftmo/program_2026-06/ftmo_universe/` s'est révélé être une
  arborescence quasi entièrement construite en symlinks absolus (`<HOME>/…`)
  pointant vers `data/panels/` ailleurs dans le dépôt — un mécanisme de référence-sans-copie
  légitime, mais non portable en git (casse sur tout autre checkout, VPS inclus). 28 étaient déjà
  **cassés** (cible supprimée lors d'un cleanup antérieur, ex. le nettoyage `m5_indices` du
  2026-06-10) → DELETE, comportement inchangé pour tout consommateur (`os.path.exists` renvoie déjà
  `False` sur un symlink cassé, identique à son absence). 23 étaient **valides** → laissés sur
  disque tels quels (IGNORE), aucun changement fonctionnel local.
- **`data/ftmo_portfolio/audit_v2_independent/`** (hors `cleanroom/engine.py`, déjà tracké) → IGNORE
  en totalité. Décision déjà actée dans CLAUDE.md (« Worktree + artefacts locaux ») : seul
  `cleanroom/engine.py` est la librairie canonique trackée, les `run_phase*.py` sont qualifiés
  d'« importés par personne, restent locaux » — ce tri applique simplement cette décision existante
  aux résultats et scripts qui l'accompagnent.
- **4 fichiers individuels >1 Mo** ont été basculés en IGNORE uniquement pour respecter le budget
  de 50 Mo (voir section dédiée ci-dessous) — ce sont des résultats de recherche légitimes, pas du
  déchet.

## Ce qui a été supprimé (135 fichiers, 4.76 Mo) et pourquoi

| Catégorie | Nombre | Détail |
|---|---:|---|
| Cache npm interne (`_cacache`) | 101 | `data/deep_history_m1/_tool/.npmcache/` — cache HTTP interne de npm, aucune valeur, régénéré automatiquement au prochain `npm install`. |
| Symlinks absolus cassés | 28 | Cibles supprimées par un cleanup antérieur (2026-06-10, `m5_indices`) ou jamais réalisées (`data/ftmo_research/`). Comportement pour tout script consommateur : inchangé (déjà `FileNotFoundError` avant suppression). |
| Fichiers temporaires / lock LibreOffice | 4 | `.tmp` (autosave PDF) et `.~lock.*#` dans `data/ftmo_portfolio/` — doublons des PDF réels déjà présents. |
| `package.json` (racine) | 1 | Artefact `npm init` isolé, aucune référence dans le dépôt (grep vide), pas de `node_modules`/lock associé, description périmée (mentionne l'ancien total « 321 tests »). |
| `ftmo_live/_tmp_new4_plugin.py` | 1 | Plugin pytest de scratch (nom `_tmp_`, 5 lignes), zéro référence, jamais vu par le VPS (fichier non suivi, jamais synchronisé). Dans un chemin de production (`ftmo_live/`) — signalé explicitement par prudence, mais le fichier lui-même n'a jamais été un artefact de production (untracked de bout en bout). |

Avant chaque suppression, le nom du fichier a été recherché dans l'ensemble du dépôt
(`grep -rl`) ; aucun des 135 supprimés n'est cité ailleurs, à l'exception de deux répertoires
de symlinks cassés (`eurusd_extras/`, `specs/`) dont le *nom de dossier* apparaît dans des
rapports historiques — mais leur contenu (les symlinks eux-mêmes) n'est référencé nulle part
et était déjà non fonctionnel.

## Ce qui a été gitignoré (1001 fichiers, 796.92 Mo) — rien supprimé du disque

Tout reste accessible localement, seulement retiré de la vue git. Principaux postes :
- `data/ftmo_portfolio/cache/` (273 Mo), `Multi_Asset/.../mr_univers_complet_2026-08/_cache/`
  (331 Mo), `.../mr_intraday_grille_2026-08/_cache/` (656 Mo, déjà gitignoré localement) — caches
  de séries FX M1/M5 régénérables depuis Dukascopy/API.
- Parquets épars (prix bruts, résultats binaires intermédiaires) dans une trentaine de dossiers
  d'étude — régénérables en relançant le script de l'étude concernée contre les sources
  canoniques déjà gouvernées ailleurs (`data/deep_history_utc/`, `data/raw/`).
- `data/ftmo_portfolio/node_modules/` (10 Mo, 381 fichiers) — dépendances npm de
  `report_gen.js` (générateur de rapport `.docx`), `package.json`/`package-lock.json` commités,
  `node_modules/` régénérable par `npm install`.
- `data/panels/*.csv` (panels de marché bruts, ~20 Mo) — sources fetchées, gouvernance du dépôt :
  une série = un fichier canonique, jamais dupliqué dans git.
- `data/ftmo_portfolio/audit_v2_independent/` (hors `engine.py`, déjà tracké).
- 23 symlinks absolus valides dans `ftmo_universe/` (cf. section méthode).

## Décisions signalées (tranchées, mais à valider si besoin)

- **`package.json` racine → DELETE.** Grep vide sur tout le dépôt, pas de `node_modules`/lock
  associé au niveau racine. Si un usage futur était prévu (ex. tooling JS au niveau repo), il
  faudra le recréer — aucune perte de données réelle (fichier généré par `npm init`, aucun code).
- **4 CSV >1 Mo basculés en IGNORE pour tenir le budget <50 Mo** (`pooled_ambiguous_trades_all_strategies.csv`
  2.2 Mo, `drawdowns.csv` 1.8 Mo, `daily_raw.csv` 1.1 Mo, `setup_daily_series.csv` 1.0 Mo). Ce sont
  des résultats de recherche légitimes (pas du déchet) ; ils restent sur disque et peuvent être
  commités a posteriori (`git add -f`) si le budget de 50 Mo n'est pas une contrainte stricte pour
  ce lot précis.
- **`ftmo_universe/` (arborescence de symlinks absolus)** : mécanisme de référence-sans-copie
  fonctionnel mais fragile (chemin machine-spécifique, 28/51 symlinks déjà cassés). Une vraie
  correction (symlinks relatifs, commitables) sortirait du cadre d'un simple tri et n'a pas été
  tentée ici — signalé comme dette technique.
- **`strategies/trend_futures/`** : nouvelle sleeve (code + résultats légers commités, prix/résultats
  binaires gitignorés) distincte des deux sleeves live existantes (`tsmom_v2_propfirm`,
  `delta_neutral`) — aucun chemin live existant touché.

## Rien laissé en suspens

Le script de catégorisation n'a laissé aucune entrée en `REVIEW` après itération (2 fichiers
`.superseded_by_S037` initialement non catégorisés ont été rattachés à COMMIT — marqueurs de
statut négligeables dans un dossier `_parked_drafts/` déjà archivé). Toutes les 3035 entrées ont
une destination et un motif explicites dans `inventaire_untracked.csv`.

## Vérification

- `tools/check_register_integrity.py` exécuté dans le répertoire principal (jamais dans le
  worktree) après application des suppressions : voir résultat dans la description de la PR.
- Toutes les commandes destructrices ont été bornées aux 135 chemins de `delete_paths.txt`,
  vérifiés un par un (existence avant/absence après), aucune commande `rm -rf` générique.
