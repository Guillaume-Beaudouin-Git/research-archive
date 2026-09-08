# Plan de nettoyage du dépôt — consolidé

**2026-09-08.** Synthèse de quatre audits indépendants (`PLAN_01` narratif, `PLAN_02` Multi_Asset,
`PLAN_03` classes d'actifs, `PLAN_04` opérationnel). **Rien n'a été modifié.**

**Critère unique** : la lisibilité par un recruteur quant. Un fichier qui raconte une histoire
périmée est pire qu'un fichier absent — il fait douter de tout le reste.

## ⚠ Une contrainte que j'avais annoncée est FAUSSE

J'avais dit aux quatre agents que supprimer un fichier cité casserait `check_register_integrity.py`.
Vérifié : **le script ne valide qu'UN fichier** (`PropFirms/ftmo/program_2026-06/positive_dsr_register/REGISTER.md`)
et **seulement 16 chemins** y sont cités. Deux agents ont vérifié plutôt que de me croire.

Le vrai enjeu de citations est `_meta/research_active.md` (47 des 72 dossiers) et les citations
croisées intra-grappe — du travail de mise à jour, **pas un bloqueur**. Le plan est donc bien moins
risqué que je ne l'avais annoncé.

---

# NIVEAU 1 — Les contradictions. À faire en premier, elles coûtent la crédibilité.

Un lecteur qui en trouve **une** cesse de faire confiance au reste. Toutes se règlent par un bandeau
daté en tête de fichier, pas par une réécriture.

| # | fichier | ce qu'il dit | la réalité | geste |
|---|---|---|---|---|
| **1** | `PropFirms/ftmo/program_2026-06/PROGRAM_DECISION_MEMO.md` | **« do-not-fund »** | compte **funded depuis le 2026-08-17** | bandeau : décision renversée, pointer vers le compte réel |
| **2** | `Multi_Asset/.../orb_cost_funded_2026-08` | conclut **KILL** | la sleeve ORB **tourne en production** | bandeau : coût re-mesuré à 2,11 bps, décision reportée à octobre |
| **3** | `STRATEGY_RESEARCH_LOG.md` (racine, 32 Ko) | « A: LIVE on testnet, C: RESEARCH ONGOING » | **A gelée, C annulée** | bandeau SUPERSEDED + déplacer hors racine |
| **4** | `README.md` | renvoie au roadmap comme référence | roadmap périmé (voir #5) | corriger le renvoi |
| **5** | `_meta/roadmap_ftmo_2026.md` | « solde 10 013,88 », objectif $200k | solde 9 927, plan sans calendrier | **réécrire ou supprimer** |
| **6** | `swapkilled_futures_2026-07/DEPLOYMENT_PLAN.md` | recommande un book | son propre `ROLL_AUDIT.md` l'invalide | bandeau ou fusion des deux |
| **7** | `_meta/current_focus.md` | « Last updated: 2026-06-10 » | 90 jours ; signalé périmé **7 semaines de suite** par ton propre pipeline | réécrire, ou supprimer et laisser `TODO.md` seul |

**Effort : une demi-journée. Impact : maximal.**

---

# NIVEAU 2 — La structure. C'est ce qui fait conclure à la dispersion.

| # | action | détail | effort |
|---|---|---|---|
| **8** | **Archiver 51 des 72 dossiers Multi_Asset** | 10 grappes cohérentes ; garder **4 vivants** (`desk_orb`, `desk_overnight`, `macro_context`, `regime_diagnostic` — la décision desk d'octobre) | 2 h |
| **9** | **Regrouper le programme macro de septembre** sous un parent unique | 13 dossiers = **une** investigation en 7 étapes + 6 tests. Groupée, c'est la meilleure démonstration de méthode du dépôt ; éparpillée, c'est de la dispersion | 1 h |
| **10** | **Archiver les 6 dossiers `Crypto/research/active/`** | morts depuis 3+ mois ; l'un affiche « Status: ARCHIVED » **en résidant dans `active/`** | 20 min |
| **11** | Même geste isolé : `Forex/fix_reversal`, `Equities/sr2_hunt`, `Futures/voie_b_ftmo` | tous se déclarent clos ou ont perdu leur véhicule | 15 min |
| **12** | **Sortir les 4 orphelins de la racine** | `N_ledger.md` (doublon de `_meta/n_tests_ledger.md`), `SLEEVE_month_end_bounce.md`, `STUDY_BREAKOUT_CONTAINER_*`, `STUDY_REGIME_DIAGNOSTIC_*` — 2 citations à corriger | 30 min |
| **13** | `audit_reconcile_2026-08` → hors de `research/` | c'est un incident opérationnel, pas de la recherche | 5 min |

---

# NIVEAU 3 — Hygiène. Risque nul, gain immédiat.

| # | action | gain | risque |
|---|---|---|---|
| **14** | **Supprimer les 11 worktrees** `.worktrees/*` | **1,6 Go disque** | **nul** — j'ai vérifié au MD5 que les 2 commits « non mergés » portent un contenu **byte-identique** à `main` |
| **15** | Supprimer `Claude Vault/` | coffre Obsidian jamais initialisé, texte d'accueil par défaut | nul |
| **16** | Nettoyer `Algorithm_Brieuc/` | 5 raccourcis `.lnk` dupliqués, et un fichier nommé **`Abruti.mq5`** | nul — l'audit de fond est bon, c'est la vitrine qui gêne |
| **17** | Dé-tracker **63 Mo de parquet EURUSD** + 4 CSV `data/panels/ftmo_*.csv` | ~67 Mo | faible, régénérables |

---

# NIVEAU 4 — Chantiers plus lourds, à traiter séparément.

| # | sujet | pourquoi c'est à part |
|---|---|---|
| **18** | **Divergence de signal Strategy A** : `run_tsmom.sh` exécute `tsmom_live.py` (`VOL_TARGET=0.15` en dur) et non `signal.py` (documenté 0.18) — **deux implémentations parallèles du même signal live** | touche du code d'exécution ; A est gelée donc pas urgent, mais à trancher avant toute réactivation |
| **19** | **Purge de l'historique `.git`** : 293 Mo aujourd'hui contre 65 annoncés, cause isolée = ~2 Go de blobs XML de scraping. Le patch de juin a arrêté l'hémorragie sans purger l'existant | destructif : `filter-repo`, force-push, resync VPS. **Jamais pendant un déploiement live** — donc pas le 12 septembre |
| **20** | `PropFirms/ftmo/program_2026-06/ftmo_research/audit/` : 281 scripts et CSV à plat | curation longue, faible urgence |

---

# Ce qui doit être MIS EN AVANT

Le nettoyage ne suffit pas — il faut aussi diriger le regard.

- **`yt_strategy_replications/`** (156 fichiers, 4 Mo) — jugée **meilleure vitrine du dépôt**
- **Le programme macro de septembre**, une fois regroupé — 7 étapes, 21 essais, une auto-correction
  en temps réel où le round 2 découvre que son propre axe prioritaire était déjà mort
- **`growth_engine_2026-07`** — le book personnel réellement construit
- La chaîne `cost_denominator → edge_inventory → reaudit_vehicule → month_end_vehicle`
- **`Futures/research/active/nq_intraday/`** — le seul chantier vivant relié à une sleeve funded

---

# Question ouverte, à trancher par toi

`_meta/cv/contexte_pour_claude_cv_2026-09.md` apparaît **supprimé et non commité** depuis le début
de la session. Le contenu est en sécurité dans git (`9e8ab5ff`). Suppression volontaire après copie,
ou accident ? Je n'ai pas tranché seul.

---

# Ordre recommandé

**Niveau 1 d'abord** — sept bandeaux, une demi-journée, et le dépôt cesse de se contredire.
**Puis niveau 3** — risque nul, 1,7 Go, une heure.
**Puis niveau 2** — le rangement de fond, une demi-journée.
**Niveau 4 séparément**, et surtout pas le 12 septembre, jour de déploiement du filtre FOMC.
