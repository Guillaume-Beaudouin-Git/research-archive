# Mémo de synthèse — Stratégie propfirm ORB Nasdaq (fusion des deux travaux)
### Document maître · Desk systématique · 2026-06-02 · v1.0

> **🛑 SUPERSÉDÉ — gouverné par `_FTMO_ETAT_CANONIQUE.md` (2026-06-03).** Ce mémo a été écrit AVANT l'état canonique et plusieurs de ses chiffres sont des cherry-picks de fenêtre favorable. Corrections obligatoires :
> - **Les « ~66-69 % single-attempt » (§1, §3, §5) sont REJETÉS** : ils combinent régime 2022-26 + règles 1-step 5 %/static (NON-FTMO) + coût 2 bps. **Chiffre honnête full-sample = ~33 %, plat selon le sizing** (cf. canonique §3).
> - **Le coût décide tout (canonique §4, L33) :** le mean_R **bascule négatif dès 3 bps** (futures direct) et franchement à 6 bps (CFD US100). Mon édifice p(pass) suppose 2 bps non mesuré → côté optimiste d'une falaise. **Au coût réel, le cœur est mort.**
> - **Le 1-step n'est PAS plus facile sur FTMO** (3 % daily + trailing + Best-Day 50 % punissent le skew = l'edge). **Raisonner 2-step.** Mes §3/§5/§6 « 1-step container = levier » ne valent QUE pour une firme non-FTMO à 5 %/static.
> - **Apport GER40+lundi = +1-3 pp sous DP → moot sur un cœur mort au coût réel.**
> - **Verdict gouvernant : FTMO = CONFIRMÉ-CLOS.** Ne pas allouer de cycles. Voir `_FTMO_ETAT_CANONIQUE.md`.
>
> *Ce qui reste valide ici : la structure du raisonnement (container, DP=plafond, décorrélations mesurées, protocole anti-faux-positif) — pas les niveaux de p(pass).*

> **Statut : backtest + Monte-Carlo, 0 jour live. Estimations, pas garanties.** Fusionne le rapport `STRATEGY_FINAL.md` (DP sizing + GER40) et notre arc de recherche (ORB, sleeve lundi, p(pass), corrections). Tous les chiffres ont été re-validés cette session.

---

## 1. BLUF — la stratégie retenue et les vrais leviers

> **Véhicule : ORB Nasdaq long-biaisé (US100/NQ), intraday pur, dans un container 1-step à DD large statique, sizé par DP. p(pass) ~66 % single-attempt en régime 2022-26.** Les **deux** leviers qui comptent sont (1) le **container 1-step** (une barrière au lieu de deux) et (2) le **sizing DP-optimal**. Empiler des sleeves décorrélés (GER40, lundi) est propre mais n'ajoute que **+1-3 pp** sous sizing optimal. **⚠ Le 1-step à 5 %/static n'est PAS le 1-step FTMO (3 %/trailing) → viser une firme type Funded Trading Plus, pas le 1-step FTMO.** Le **2-step plafonne à ~49 %** quelle que soit la combinaison.

---

## 2. Ce sur quoi les deux travaux convergent (robustesse par réplication indépendante)

Deux analyses séparées, mêmes conclusions — le meilleur signe possible :
- **Le cœur tradable = ORB Nasdaq long-biaisé** = beta long intraday (up-days). Pas d'alpha market-neutral.
- **1-step ≫ 2-step** pour un essai unique (une barrière vs deux en série).
- **Le 2-step single-attempt est plafonné** (~44-49 %, optimum DP) → hors d'atteinte de 50 % sans un Sharpe nettement plus haut, inexistant dans cet univers.
- **L'espace intraday liquide retail est efficient** : seul edge utilisable = beta long ; la contrainte qui borne tout = cap DD-jour + double barrière 2-step.
- **Rigueur partagée** : leur leak ML (Sharpe 11→0,68) et notre erreur d'annualisation (√252→√52 sur le lundi) attrapés des deux côtés.

---

## 3. Les vrais leviers (chiffres re-validés cette session)

### 3.1 Container 1-step + DP sizing (le moteur)
p(pass) **DP-optimal**, <2 mois, régime 2022-26, règles 5 %/static :

| série | 1-step | 2-step |
|---|---:|---:|
| NQ seul | **66 %** | 48 % |
| NQ+GER40+Lundi | 69 % | 49 % |

→ Notre repro du DP **valide leurs chiffres** (eux : 1-step 64 % régime / 53 % full-history ; 2-step 44 %).

### 3.2 Le sizing DP-optimal
État = (équité, jours restants, phase) ; action ρ ≤ 4,5 % ; Bellman backward. Forme : **risque max quand loin de la cible avec peu de jours, réduit en approchant la cible ET le floor**. **Proxy déployable : floor-taper c≈0,2 plafonné à 4,5 %.** C'est LE gain (améliore pass ET réduit bust vs sizing fixe).

---

## 4. Ce qui n'aide PAS beaucoup — l'empilement de sleeves

Les 3 sleeves sont **tous décorrélés** (vraies données 2022-26) :

| paire | corr |
|---|---:|
| NQ ↔ GER40 | −0,05 |
| NQ ↔ Lundi | −0,04 |
| GER40 ↔ Lundi | +0,06 |

Sharpe du book (vol-norm, 2022-26) : NQ **1,12** → +GER40 1,16 → +Lundi **1,64**.

**MAIS sous sizing DP-optimal, l'apport en p(pass) s'effondre à +1-3 pp** (vs +9-10 pp à sizing fixe sous-optimal). Raison : le DP extrait déjà presque toute la proba passable du NQ seul ; la diversification compense un mauvais sizing, pas un bon. **Conclusion : empiler GER40+lundi = robustesse, pas game-changer.** (Cohérent avec leur « multi-sleeve dilue, seul GER40 aide un peu ».)

---

## 5. Le menu p(pass) honnête (single attempt)

| Container / règles | p(pass) | Note |
|---|---:|---|
| **1-step 5 %/static (Funded Trading Plus-type) + DP** | **~66 % (2022-26) / ~53 % full-history** | ✅ la voie retenue |
| 1-step FTMO **réel** (3 % daily + trailing) | ~46 % parfait / **~27 % slippage** | ⚠ piège — ne pas utiliser |
| 2-step FTMO (DP-optimal) | ~48-49 % (2022-26) / ~44 % | mur, < 50 % |
| 2-step, sizing bas 1-1,5 % + grind 9-18 mois | 54-65 % | autre voie >50 %, mais lente |

**Pour >50 % :** soit (a) **1-step favorable + DP** (~66 %, rapide), soit (b) **2-step en grind lent** (1-1,5 % sizing, 9-18 mois → 54-65 %), soit (c) **essais multiples** (1−(1−p)ⁿ ; 2 essais à ~50 % → ~75 %).

---

## 6. La stratégie retenue (spec actionnable)

1. **Instrument** : US100 (Nasdaq-100), intraday pur (flat overnight → 0 swap).
2. **Signal** : ORB 30 min (open cash US 09:30-10:00 ET), **long-only** sur 1ᵉʳ break OR-high après 10:00, **filtre up-day** (OR-close > clôture veille), largeur OR ≥ 8 bps, fill next-bar-open. Stop = OR-low (−1R). Sortie : **hold-to-close** (PAS de trail-BE — couper la queue droite est contre-productif sur barrière asymétrique).
3. **Container** : **1-step, cible +10 %, daily ≥5 %, DD total ≥10 % STATIQUE (pas trailing), sans limite de temps.** ⚠ PAS le 1-step FTMO. Viser Funded Trading Plus 1-Phase ou équivalent.
4. **Sizing** : DP-optimal (proxy floor-taper c≈0,2, plafond ρ ≤ 4,5 %).
5. **Sleeves optionnels** (robustesse, +1-3 pp) : GER40 ORB (session Francfort, long-only up-day, hold-to-close) ; lundi intraday long (décorrélé, ~0,6-0,9 Sharpe corrigé). Vol-targeter, kill-switch régime.
6. **Budget** : petit compte ; ~31 % bust/essai au sizing agressif → prévoir 2 essais (→ ~78 %) si la contrainte 1-essai se relâche.

---

## 7. Registre de risques (à acter avant capital)

| # | Risque | Détail | Mitigation |
|---|---|---|---|
| R1 | **Mauvais container** | Le 1-step FTMO (3 %/trail) ≠ le 1-step modélisé (5 %/static) → 66 % devient ~27-46 % | **Vérifier les specs firme** ; viser 5 %/static |
| R2 | **Régime** | Les ~66 % / Sharpe 1,64 sont 2022-26 (favorable) ; full-history ~53 % | Borne robuste = full-history ; kill-switch |
| R3 | **Beta-long** | Perd en marché baissier ; tous les sleeves net-longs | Sizing modéré ; pas d'empilement de longs en bear |
| R4 | **Exécution** | GER40 fill same-bar (optimiste) ; stop gap-through non modélisé partout | Paper, mesurer slippage réel |
| R5 | **0 jour live** | Tout est backtest | **Paper ≥3 mois** avant capital |
| R6 | **Sur-ajustement DP** | Politique fittée sur la distribution réalisée | Validée en block-bootstrap, mais in-sample ; OOS live requis |

---

## 8. Corrections & leçons méthodologiques (le vrai livrable durable)

Le protocole qui a tenu — et a attrapé **4 faux positifs** cette session :
- **gap-fade** (CI bootstrap incluait 0) ; **shorts du scan** (bug signe-coût) ; **lundi** (annualisation √252→√52, gonflé ×2,2) ; **leur leak ML** (Sharpe 11→0,68).
- Outils : **réplication cross-asset** (a sauvé le lundi en signe), **CV années paires/impaires**, **FDR vs multiple-testing**, **bootstrap CI**, **annualisation correcte** (√(obs/an)), **block-bootstrap vol-clustering**, **DP comme borne supérieure du sizing**.

**Lessons à graver (proposées pour CLAUDE.md) :**
- **L33** — Annualisation : un edge « 1×/semaine » s'annualise en √52, pas √252 (sinon ×2,2 de gonflage). Toujours annualiser par √(observations/an).
- **L34** — L'apport d'un sleeve décorrélé doit être mesuré **sous sizing optimal** (DP), pas fixe : à sizing fixe la diversification compense le mauvais sizing (apport surévalué).
- **L35** — Vérifier les **règles exactes du container** (FTMO 1-step = 3 %/trailing ≠ 2-step 5 %/static) avant tout chiffre de p(pass).

---

## 9. Artefacts & reproductibilité

| Artefact | Chemin |
|---|---|
| Sleeve NQ ORB V2+E7 | `outputs/orb_v2e7.parquet` |
| Sleeve GER40 ORB (long-only up-day, E0) | `outputs/ger40_orb_LO.parquet` |
| Sleeve lundi + script | `code/monday_sleeve.py` (ANN=√52 corrigé) |
| Leur DP sizing | `dp_sizing.py` (reproduit & validé) |
| Stress-test lundi | `RAPPORT_monday_sleeve_stresstest.md` (erratum v1.1) |
| Décision FTMO/ORB | `RAPPORT_institutionnel_FTMO_ORB.md` |
| Recherche intraday | `INTRADAY_decorrelated_search_NQ.md` |

**Paramètres** : block-bootstrap blocs 10-21 j ; DP grille équité $50, ρ pas 0,5 % ; coûts 1-2 bps RT ; régime 2022-26 sauf mention full-history. 0 jour live.

---
*Mémo compilé 2026-06-02. Fusion STRATEGY_FINAL (DP+GER40) × arc desk (ORB, lundi, p(pass), corrections). Pour délibération — pas un conseil en investissement. Tous chiffres backtest.*
