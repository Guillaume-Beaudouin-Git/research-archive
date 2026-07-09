# A vs B — rendre le cache prix accessible à la routine feasibility

**Date**: 2026-07-09  
**Statut**: ANALYSE — aucune décision prise, aucune infra modifiée.  
**Problème**: le cache parquet est gitignoré → invisible pour la routine si elle tourne
dans le sandbox cloud Anthropic (pas de réseau là-bas). Deux façons de le rendre lisible.

---

## Fait mesuré (cache généré localement ce jour)
- `strategy_a_universe.parquet` : **194 130 octets (~190 K)**, 3111 lignes × **7 actifs**
  (BTC, ETH, LINK, DOGE, ADA, LTC, BCH), plage 2018-01-01 → 2026-07-08.
- ⚠️ **7 actifs, pas 14** : le loader écarte les actifs listés après 2018 (SOL/AVAX/DOT/
  UNI/MATIC/OP) via sa logique *late-listed drop* (voir §« Aparté »). Indépendant de A/B,
  mais le blob committé (option A) figerait ce périmètre à 7.

---

## Option A — retirer le parquet du `.gitignore` + le committer

**Mécanique** : le sandbox cloud lit le parquet versionné ; le refresh périodique
(build_price_cache.py, sur une machine avec réseau) réécrit le blob et re-commite.

| Cadence de refresh | Poids par commit | Croissance `.git`/an (blob binaire, mal deltifié) |
|--------------------|-----------------:|--------------------------------------------------:|
| Hebdomadaire       | ~190 K           | **~10.1 MB/an** |
| Mensuelle          | ~190 K           | **~2.3 MB/an** |

- Le **fichier** en lui-même ne grossit que de ~0.4 K/semaine (+7 lignes × 7 colonnes) ;
  c'est l'**historique git** qui accumule un blob de ~190 K par refresh.
- **Filet de sécurité déjà en place** : même si le cache committé dépasse 14 j, le loader
  tente le live (bloqué en cloud) puis **sert le cache périmé avec un WARNING** — il ne
  casse jamais. La fraîcheur n'est donc pas critique : un refresh **mensuel** suffit
  (→ ~2.3 MB/an), et pour une baseline TSMOM 2018→ les prix historiques ne bougent pas.

**Pour** : zéro changement d'infra ; la routine cloud actuelle continue telle quelle ;
Telegram (`notify-digest.yml`) inchangé ; déployable immédiatement.  
**Contre** : viole la règle de gouvernance « jamais de blobs data dans git » (CLAUDE.md) —
bien que petit et régénérable ; bloat d'historique (bornable par cadence).

---

## Option B — migrer la routine feasibility-digest sur le VPS

Là où le cache local suffit (réseau présent), plus besoin de committer le parquet.

**État VPS vérifié (<VPS_IP>, ~/projects/Algo_claude sur `main`)** :
- ✅ venv `~/venv` : pandas 3.0.3, yfinance 1.2.2, pyarrow 24.0.0
- ✅ réseau (yfinance OK) → `build_price_cache.py` tourne, cache local régénérable
- ✅ clé de déploiement SSH avec **push** (`git@github-algo-write:…`)
- ❌ **statsmodels ABSENT** du venv (requis par ic_check + ExitRuleHandler)
- ❌ **`gh` CLI absent**
- ℹ️ les crons existantes (`fetch_arxiv.sh`, `fetch_alpha_sources.sh`) **poussent
  directement sur `main`** (`git push origin main`), pas de PR ; verrou `.algo_git.lock` +
  `git pull --rebase --autostash` ; wrapper `scripts/run_with_env.sh`.
- ℹ️ **aucun script de génération de digest** n'existe dans le repo (`grep` : rien n'émet
  `tested_24h/queue_size/generated_at`) → le digest markdown est **rédigé par l'agent LLM
  cloud**, pas par un script déterministe.

**Ce qu'il faudrait construire (4 briques)** :
1. `~/venv/bin/pip install statsmodels` (sinon Level A/handlers échouent).
2. **`generate_digest.py`** déterministe : calcule le frontmatter (tested_24h, verdicts.*,
   queue_size) depuis `_state.json`/`_index.json` + corps markdown. C'est ce qui remplace
   la rédaction LLM de la routine cloud. (~1 fichier, tous les champs sont calculables.)
3. **Ouverture de PR** : `notify-digest.yml` ne se déclenche que sur *fin du workflow
   Auto-merge* + diff d'un digest sur `main`. Or les crons VPS poussent **direct sur main**
   → Auto-merge ne tourne pas → **Telegram ne partirait pas**. Il faut soit :
   - (b1) que le cron VPS **ouvre une PR** (installer `gh`, ou API GitHub via curl+token) →
     Auto-merge tourne → Telegram OK ; soit
   - (b2) ajouter un trigger `on: push` (paths `_automation/feasibility/digests/**`) à
     `notify-digest.yml` — un push par **clé de déploiement** (≠ GITHUB_TOKEN) **déclenche**
     bien les workflows `push`. Mais c'est une modif `.github/` (hard-fail path, hors
     `_automation/`, revue humaine obligatoire).
4. **Cron VPS** : p.ex. `0 5 * * *  run_with_env.sh python3 orchestrator.py` (batch) puis
   `generate_digest.py` puis commit/push (ou PR), sous le verrou `.algo_git.lock`.

**Pour** : pas de blob data dans git (cache local gitignoré = conforme gouvernance) ;
prix toujours frais ; cohérent avec l'automation déjà VPS (alpha_hunt/arxiv).  
**Contre** : 4 briques à livrer (statsmodels, generate_digest.py, PR/Telegram, cron) ;
plus de pièces mobiles ; le Level B lourd (2-4 h) tournerait sur un CX22 (2 vCPU) →
question de ressources/temps pour les gros batches.

---

## Recommandation (argumentée — je n'exécute pas)

**A maintenant, B comme cible durable.** Raisons :
- A débloque la routine **immédiatement** sans toucher à l'infra, et le filet de sécurité
  (service du cache périmé + WARNING) rend la cadence non critique → **refresh mensuel**,
  soit **~2.3 MB/an** de bloat, acceptable et bornable.
- Le seul vrai grief d'A (blob data en git) est mineur ici (190 K, régénérable) et
  réversible : si B est livré plus tard, on re-gitignore le parquet et on purge le blob.
- B est plus propre **mais** exige 4 briques dont une non triviale (`generate_digest.py`
  déterministe qui reproduit le digest aujourd'hui rédigé par LLM) et une modif `.github/`
  ou l'install de `gh` pour préserver Telegram. À faire, mais pas dans l'urgence.

Chemin hybride concret : (1) option A ce mois-ci pour re-tester les 76 hypothèses ; (2) en
parallèle, écrire `generate_digest.py` + `pip install statsmodels` VPS ; (3) basculer en B
et re-gitignorer le parquet une fois B validé de bout en bout (digest + Telegram).

**Décision laissée à Guillaume.**

---

## Aparté — 7 actifs au lieu de 14 (indépendant de A/B, à trancher séparément)
`_fetch_live_universe` construit un DataFrame indexé depuis 2018-01-01 ; sa règle
*late-listed drop* (`df.iloc[:90].isna().mean() > 0.5`) supprime toute colonne >50 % NaN
sur les 90 premières lignes → **SOL/AVAX/DOT/UNI/MATIC/OP sont éjectés** (ils n'existaient
pas début 2018), alors qu'ils **se téléchargent bien** (SOL 2281 lignes, etc. — vérifié).
- Ce comportement **préexiste** au fix réseau (règle héritée du loader d'origine) et
  **n'est PAS** causé par la PR #383.
- Il est **cohérent** avec le Sharpe baseline canonique : 7 actifs → **Sharpe 0.666**
  (n_days=3111), soit le fameux « ≈0.68 » (historique 0.678 = mêmes 7 actifs).
- À décider **hors** A/B : garder 7 (continuité historique du 0.678) **ou** corriger la
  règle drop pour inclure les actifs dès leur date de listing (→ 14 actifs, mais change la
  baseline et la sémantique n_tests de tous les tests futurs). Non touché ici.
