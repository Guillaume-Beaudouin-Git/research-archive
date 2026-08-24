# TODO — état au 2026-08-24

Consolidé après la session du 17-24 août. Le nettoyage du dépôt est **terminé** ; ce qui
reste est de la recherche, de la dette de méthode, et deux gestes opérateur. Chaque entrée porte : qui fait, quel effort, quel
critère de fin. Classé par urgence réelle, pas par facilité.

---

## 🔴 Bloquant — rien ne se décide sans ça

| # | tâche | qui | effort | fin |
|---|---|---|---|---|
| 1 | **Lire la *maximum capital allocation rule*** sur ftmo.com. Le scaling plan dit $2 M tous comptes confondus ; la règle d'allocation elle-même n'est pas citée en source primaire. Elle conditionne toute décision de taille. | **toi** | 10 min | gravée dans `PropFirms/ftmo/rules.md` |
| 2 | **Dérapage ORB, N=30 fills décomposés** — `(ask_au_déclenchement − niveau)` + `(fill − ask)`. Tranche **trois** décisions d'un coup : garder two-sided (<1.94 bps), passer long-only (1.94-2.5), désarmer (>2.5). | automatique | ~1 fill/jour ouvré | **~octobre 2026** |

---

## 🟠 Sous quinze jours

| # | tâche | qui | note |
|---|---|---|---|
| 3 | **Profil de spread à 2 semaines** — 22 500+ lignes déjà collectées. Confirme ou infirme le 1.045 bps RT sur un échantillon incluant heures creuses et ouvertures. | automatique | ~2 sept. |
| 4 | **Premier retrait** + remboursement des €89. Balance > 10 000 à la frontière des 14 jours de trading. | toi | ~début sept. |
| 5 | **Ré-ancrer les 4 swaps** (`spec_bounds_breach = 1` sur 4/4). Impact P&L négligeable (~$15/2 ans) mais **le swap de l'or est DANS le signal** (prix carry-ajusté). À grouper avec un autre ré-gel de spec. | moi (prépa) + toi (déploiement) | chaîne complète : config → yaml → sha → mqh → recompile → re-dépôt |
| 6 | **Suite des résurrections S037 / S061** — l'audit d'ambiguïté d'entrée les fait passer DISCARD → KEEP. S061 est fragile au contrôle L60 (Sharpe +0.32 → +0.09), S037 tient mieux. Décider : dossier complet ou classement. | moi | Δn_tests = 0 (correction) |

---

## 🟡 Dette de méthode — à solder pendant que c'est frais

| # | tâche | pourquoi |
|---|---|---|
| 7bis | ✅ **FAIT** — trou de réconciliation ORB (PR #435). Le sleeve funded n'était modélisé **nulle part** : `replay.py` ne simulait que le micro-ORB (`micro_orb: false` en FUNDED) et le filtre `reason.startswith("micro")` de `reconcile.py` excluait `funded_orb_*` par construction. **Les 4 jours du compte funded étaient aveugles** ; 3 « OK » étaient des faux négatifs passés sous tolérance par chance. Correctif + 3 tests. | — | — |
| 7 | **Graver L61-L63** dans le registre : (a) le sizing dépendant du chemin fabrique du t positif sur du bruit, invisible au HAC ; (b) un placebo bloc-bootstrap fabrique une géométrie de barres inexistante — 10× trop d'ambiguïté intra-barre ; (c) une mesure empruntée est acceptable si la marge au seuil dépasse l'erreur plausible de la source, sinon non. | trois artefacts mesurés cette semaine, aucun encore dans le registre |
| 8 | **Auditer la résolution des jours à double touche du ledger ORB** — 4 013 jours, 1 direction/jour, mais on ignore comment les journées où les deux niveaux étaient touchés ont été tranchées. Le corpus 109 les score « assume loser » (le pire cas) ; le ledger funded a `entry == level` 4013/4013 (le meilleur cas). Le verdict R2 et le point mort à 1.94 bps reposent dessus. | inconnue neuve, jamais auditée |
| 9 | **Mesure native du coût COPPER** — seul des 4 commodités dont la marge (×27) n'est pas hors d'atteinte d'une erreur de source. NGAS/USOIL/UKOIL sont à ×179-780, hors de portée. | ferme proprement le kill énergie |
| 10 | **Corriger `DOC_SIGNAL_PIPELINE.md:37`** (affirme « ≥2 des 3 lookbacks » alors que le code exige l'unanimité) et **documenter le duty cycle réel de l'or** (43.9 % des séances éteintes, jamais rapporté). | la doc affirme le contraire du code |
| 11 | **Ajouter `ftmo_live/` au regex hard-fail de `auto-merge.yml:57`** — aujourd'hui seul `*.mq5` bloque, alors que `ftmo_live/brain.py` est du Python **réellement déployé** par le pull. GARDE 2 le rattrape, mais la défense documentée n'existe pas. | 1 ligne, PR dédiée (`.github/` est lui-même hard-fail) |

---

## ✅ Nettoyage du dépôt — TERMINÉ (2026-08-22 → 24)

| | départ | final |
|---|---|---|
| branches distantes | 448 | **17** |
| branches locales | 99 | 22 |
| PR ouvertes | 7 | **0** |
| fichiers non suivis | 846 | **0** |

Fait : 460 branches supprimées avec preuve de contenu · 3 035 fichiers triés (1 899 commités,
1 001 gitignorés, 135 supprimés) · README racine réécrit (l'ancien, 138 Ko et périmé de trois
mois, archivé dans `docs/`) · `docs/ARCHITECTURE.md` + `docs/RESEARCH_METHOD.md` · 11 README de
dossier · **19 branches non mergées remontées** (PR #434), dont ZN Baltussen que `CLAUDE.md`
citait comme actif alors que `main` n'en contenait aucun fichier · **4 incohérences de vérité
corrigées** (PR #433).

**Reste, non bloquant :**

| # | tâche | risque |
|---|---|---|
| 12 | **Restructuration de la racine** (25+ dossiers) — ⚠ **DIFFÉRÉ**. Le VPS pull `main` toutes les 30 min et des pins référencent des chemins absolus : déplacer `ftmo_live/`, `data/ftmo_portfolio/v22/`, `Portfolio/` ou `strategies/` **casse la production**. Exige un plan de déploiement coordonné. | **ÉLEVÉ** |
| 13 | 3 worktrees encore montés (`_fixdoctruth`, `_rescue`, `_reconcile`) + un `stash@{0}` devenu redondant. Nettoyage cosmétique. | nul |

## 🔵 Projets futurs — par ordre d'espérance

### En attente explicite (hors session en cours)

| projet | pourquoi il attend |
|---|---|
| **Commodity TSMOM sur futures** | Le meilleur candidat de la cartographie : testé sur **12 ETF dont USO et UNG** alors que le papier cité (Hurst-Ooi-Pedersen) opère sur ~60 **futures**. Trois violations simultanées des règles maison (instrument, breadth 12 < 30, pénalité de multiple testing sur un test sous-puissant par construction). **Δn_tests = 0**. Pré-enregistrement déjà rédigé. |
| **Carry cross-asset (Koijen et al. 2018)** | Le repo a fermé le carry **FX** et le carry **commodités CFD**, mais jamais la construction **multi-classe** du papier — écart de breadth mesuré à **1/6**. Nouvel essai, donc déflate. |

Les deux sont sur **futures/IBKR**, exclus de la session FTMO en cours par décision explicite.

### Famille neuve, jamais ouverte

| projet | note |
|---|---|
| **Momentum intraday (Gao-Han-Li-Zhou)** — première et dernière demi-heure | Famille **différente** du retour à la moyenne (momentum, pas reversion). Identifiée pendant la revue de littérature et volontairement non repliée dans le kill MR. Mérite son propre pré-enregistrement. |

### Univers MR non couvert

**HK50, AUS200, UK100, FRA40, ESP35, EUSTX50, crypto CFD.** L'infrastructure de téléchargement est
en place, la reprise est peu coûteuse. ⚠ Espérance faible : l'invariance est déjà démontrée sur
indices, FX, métaux et 7 nouveaux crosses (t moyen −1.03 à −1.28 partout). À ne faire que pour
clore formellement.

### Le débat de fond, non tranché

**FTMO contre IBKR.** Sur 118 edges inventoriés, **11 nomment le compte personnel comme voie de
ré-ouverture, zéro ne nomme FTMO**. Le scaling plan FTMO est hors d'atteinte d'un facteur 4-6 par
construction (10 %/4 mois exigés contre ~1.7 % produits). Le compte perso porte déjà un book
validé (trend + bond month-end, ρ 0.01, SR 1.02), sans barrière, sans horloge, avec compounding
réel et 100 % du P&L.

Les deux ne sont pas exclusifs — instruments et horizons différents, corrélation faible. Mais si
l'effort marginal doit aller quelque part, **les chiffres disent IBKR**.
