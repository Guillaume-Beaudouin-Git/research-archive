# PRÉ-ENREGISTREMENT — Ré-audit du funnel contaminé + question du véhicule

**Gelé le 2026-08-13, AVANT tout accès aux données.** Deux programmes indépendants, exécutés en
parallèle. Rédigé par le MD.

## 0. Pourquoi ce travail existe

Le book FTMO live se réduit à **une seule famille active** : deux jambes overnight indices
(lundi/mardi, LONG-only, **sans signal** — exposition calendaire pure). L'or est en dead-zone,
le J1 est suspendu par son gate à hystérésis, et l'ORB funded vient d'être tué
(`orb_cost_funded_2026-08/RESULTS.md`, règles R2 et R4).

La recherche de sleeves décorrélées sur FTMO a consommé **321 essais** et n'a produit **aucun
survivant déployable**. Les 7 derniers jours à eux seuls : carte de 8 695 cellules ⇒ shortlist
vide ; 241 prédicteurs exogènes ⇒ 0 ; axe du signe fermé ; dernier candidat (or veille de CPI)
rejeté le 12/08.

**Ce n'est donc PAS une chasse fraîche.** Une chasse fraîche déflate le DSR de tous les candidats
suivants pour un taux de base observé proche de zéro. Les deux programmes ci-dessous exploitent
au contraire des **erreurs d'instrument documentées** et la **politique de ré-ouverture** du repo
(kills sur COÛT / PUISSANCE / GÉOMÉTRIE = rouvrables ; kills MÉCANIQUES = restent fermés).

---

# PROGRAMME 1 — Ré-audit du funnel `top10_test` (164 tests)

## 1.1 Les défauts d'instrument, et le SENS de chaque biais

Le funnel `PropFirms/ftmo/program_2026-06/top10_test/` a filtré 164 hypothèses. Cinq défauts sont
établis, **tous documentés avant ce pré-enregistrement** :

| # | Défaut | Source | Sens du biais |
|---|---|---|---|
| 1 | **DSR cassé** — `std_sr_trials=1.0` ⇒ seuil exigé **2.57** au lieu de **1.27** | sprint 08-01 | **faux négatifs** (barre 2× trop haute) |
| 2 | **Fuseau EET étiqueté UTC** ⇒ **38.7 %** du RTH jamais testé | sprint 08-01 | fenêtres **jamais explorées** |
| 3 | **Table de coûts de catalogue** : or **3.50** vs **1.84** mesuré (**1.9×**) ; `Index_CFD_major` 1.5 et `minor` 2.5 vs **~0.9** mesuré au centre | `cost_denominator_2026-07/COST_AUDIT.md` | **faux négatifs** sur métaux + indices |
| 4 | **Plancher à CLIQUET** — `framework.py:56` `FTMO_MLL_PCT` documenté « trailing, EOD high-watermarked, never decreases » | contredit `rules.md` (statique en 2-step, cliquet = 1-step écarté), tranché **2×** | **faux négatifs sur les chemins GAGNANTS** |
| 5 | **Swap indices −3.1 bps/nuit** vs mesuré **US100 −2.13 / GER40 −1.56** | `spec_v22.yaml:cost_anchors` | **faux négatifs** sur les familles tenues |

⚠ **Une exception qui va dans l'AUTRE sens — à ne pas effacer.** Sur le **FX**, la colonne de
spread du cache est **zéro-inflée** (EURUSD **33.2 %** de jours à spread nul ⇒ médiane 0.093,
« ~13× trop bas » ; GBPUSD, USDJPY, USDCAD idem). Le `FX_major = 1.5` du funnel n'est donc
**pas** démontré trop sévère, et pourrait être **optimiste**. **La correction de coût est
favorable aux indices et aux métaux, PAS au FX.** Toute conclusion FX doit le dire.

⚠ **Différence d'échelle** : le funnel tourne sur `FTMO_CAPITAL = 100_000`, notre compte est à
**10 000**. Par L24 la p(pass) dépend de la FORME de la distribution, pas de la taille — mais
par **L57** la granularité de lot mord en **INTERDISANT le vol-targeting** (0.35 de Sharpe,
skew +0.99 → −0.49, queue −18.4 % sur une séance). Ce biais-là joue **contre** les candidats à
10k. Rapporter les deux échelles.

## 1.2 Un sixième défaut, découvert le 2026-08-13 et à intégrer

Le coût dépend du **TYPE D'ORDRE**, d'un ordre de grandeur, et le funnel facture tout pareil :

| type d'ordre | référence de `req_price` | coût mesuré | N |
|---|---|---:|---:|
| marché/limite en séance liquide | le bid/ask (spread déjà payé) | **~0.0-0.1 bps** au-delà | 32 |
| **stop au repos** (entrée ORB) | le **niveau théorique** | **+2.169 bps** | 12 |

⇒ Une famille qui entre **au marché à heure fixe** est structurellement **~2.5× moins chère**
qu'une famille à **déclenchement sur stop**. Classer les 164 candidats par type d'ordre est un
axe de re-tri **gratuit**.

## 1.3 Ce que le programme 1 doit produire

1. **Une pile d'instruments réparée** : DSR corrigé, plancher STATIQUE, table de coûts mesurée
   (indices ~0.9 centre / queue p95 2.3 / max 4.5 ; or 1.84 ; FX **inchangé**, motif ci-dessus),
   swaps mesurés, et le RTH complet.
2. **Le re-run des 164 tests** sur cette pile.
3. **La LISTE DES DELTAS** — le livrable principal : **quels candidats changent de verdict**, et
   **lequel des 6 défauts** en est responsable, un par un (contribution marginale, pas seulement
   l'effet joint).
4. Pour tout survivant : Sharpe, MaxDD, **walk-forward ≥5 folds**, DSR corrigé, t HAC lag-6,
   IC block-bootstrap, **et la corrélation à la sleeve overnight déployée** — c'est l'objet de la
   recherche : on cherche du **décorrélé**, pas du performant.

## 1.4 Règles de kill — GELÉES

- **P1-R1** — un candidat n'est **SURVIVANT** que s'il franchit RESEARCH_PASS (Sharpe > 0.7,
  MaxDD < −25 %, WF > 50 %) **sur la pile réparée**, avec DSR corrigé > 0 et IC bootstrap
  excluant 0.
- **P1-R2** — un survivant n'est **ADMISSIBLE au book** que si sa corrélation à la sleeve
  overnight est **|ρ| < 0.3** et que ΔSR_book > 0 au poids ERC, significatif au block-bootstrap.
- **P1-R3** — tout candidat dont le kill d'origine était **MÉCANIQUE** (gross ≈ 0, two-sided
  négatif à coût NUL, sous placebo) **reste fermé**, quelle que soit la réparation. Réparer un
  instrument ne ressuscite pas un gross de 0.00 bps.
- **P1-R4** — un candidat ressuscité **uniquement** par le passage du cliquet au plancher
  statique doit être signalé comme tel : c'est une correction de **géométrie**, pas un edge.

## 1.5 Comptage des essais — RÈGLE EXPLICITE

Re-passer une hypothèse **déjà pré-enregistrée et déjà comptée** avec des instruments réparés est
une **CORRECTION, pas un nouvel essai** : le ledger `n_tests` **n'est pas incrémenté**, et le DSR
des candidats futurs n'est pas déflaté. En revanche **toute hypothèse nouvelle** rencontrée en
chemin est **hors périmètre** : on la note, on ne la teste pas.

---

# PROGRAMME 2 — La question du véhicule

## 2.1 La question

Trois edges d'affilée ont eu **IBKR pour maison, pas FTMO** — le repo l'a noté comme un motif
structurel. Le compte perso €12k porte déjà un book validé (trend + bond month-end, ρ 0.01,
SR combiné 1.02), et le CLAUDE.md classe ce compte comme un véhicule de **PREMIÈRE CLASSE**,
pas un repli. Les futures y coûtent **~0.4 bps RT** contre 2-7 bps en CFD retail.

**Question** : parmi les familles tuées **SUR LE COÛT**, lesquelles vivent sur futures IBKR ?

C'est la catégorie explicitement **ROUVRABLE** de la politique du repo : *« le coût futures
(~0.4 bps RT sur MNQ) change le gate d'un ordre de grandeur »*. Précédent établi : month-end ZN,
rejeté **2×** sur le véhicule, **vivant** sur le compte perso (+17.6 %/an, SR 0.92 — L53).

## 2.2 Ce que le programme 2 doit produire

1. **L'inventaire des familles tuées SUR LE COÛT** (pas mécaniquement) — sources : registre L
   (L32b, L33b, L34, L43, L45), `research_history.md`, la carte des 8 695 cellules, les 241
   exogènes. Pour chacune : le gross mesuré, le coût qui l'a tuée, le véhicule supposé.
2. **La matrice de véhicule, AVANT tout backtest** (correctif du biais « véhicule en dernier »,
   L53) : pour chaque famille, existe-t-il un instrument futures liquide correspondant ? quelle
   marge au lot minimum ? **la marge du lot minimum tient-elle dans €12k ?** — si oui, un
   propfirm n'apporte rien (test de 5 minutes, L53).
3. **Le re-gate au coût futures** : `gross / cost` recalculé à ~0.4 bps RT au lieu de 2-7 bps,
   avec le gate pré-flight `gross_per_trade / cost_p95 ≥ 1.5`.
4. **Le verdict de granularité (L57)** : un micro-future n'est propre que si son notionnel dilue
   la commission fixe ($1.70 fixe = 2.3-2.8 bps sur $6-7k, mais 0.66 bps sur $40k). Et surtout :
   la granularité mord en **INTERDISANT le vol-targeting** — rapporter le **skew** et la **queue
   single-session** de toute sleeve à lot fixe.

## 2.3 Règles de kill — GELÉES

- **P2-R1** — une famille n'est **ROUVERTE** que si son kill d'origine est de nature **COÛT**,
  **VÉHICULE**, **PUISSANCE** ou **GÉOMÉTRIE**. Kill **MÉCANIQUE** ⇒ reste fermé, sans exception.
- **P2-R2** — une famille rouverte doit passer `gross_per_trade / cost_p95 ≥ 1.5` **au coût
  futures mesuré**, sinon elle se referme immédiatement.
- **P2-R3** — appliquer le **test L53 en PREMIER** : si la marge du lot minimum tient dans le
  capital perso, la route propfirm est **strictement dominée** et la famille se juge sur IBKR seul.
- **P2-R4** — aucune conclusion de performance sans **skew** et **queue single-session** au lot
  déployé (L57), et sans **placebo apparié** si le claim est calendaire (L49/L58).

---

# 3. Garde-fous communs (les deux programmes)

- Écriture **uniquement** dans le sous-dossier du programme :
  `reaudit_vehicule_2026-08/{funnel_reaudit,vehicule}/`.
- **Interdiction absolue** de modifier `ftmo_live/`, `Portfolio/`, `strategies/`, `data/`,
  `data/ftmo_portfolio/v22/`, `audit_v2_independent/cleanroom/`,
  `PropFirms/ftmo/program_2026-06/top10_test/` (à IMPORTER en lecture seule ; toute réparation se
  fait par **copie** dans le dossier du programme, jamais en éditant la source), ni le dossier de
  l'autre programme.
- **Aucune commande git.** Interpréteur `/usr/bin/python3`.
- **Block bootstrap** (Politis-Romano) pour toute incertitude — iid **interdit**. HAC lag-6.
  Walk-forward **≥5 folds** expanding, jamais un split simple. Toujours rapporter **N**.
- Annualiser en **√(observations par an)**, jamais √252 en dur (L47).
- La colonne `spread` de `data/deep_history_utc/` est **inutilisable seule** comme mesure de coût.
- **Vérifier le fuseau avant toute découpe horaire** (L52/L56) — c'est précisément le défaut n°2.
- **Un résultat défavorable se publie tel quel.** Les règles de kill ne se renégocient pas après
  avoir vu les chiffres.
