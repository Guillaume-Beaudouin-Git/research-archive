# Ré-ouverture n°1 (segmentation Ranaldo) — l'arithmétique tranche en deux minutes

**2026-09-08.** Candidat n°1 de `REOUVERTURES.md`. Δn_tests = 0 — aucun backtest, seulement le
calcul de budget de coût à partir des chiffres déjà mesurés.

## Le point de départ, vérifié à la source

`Forex/research/active/fix_reversal/FIX_REVERSAL_TZ_MIGRATION.md` (version post-correction de fuseau,
2026-06-10) :

| jambe | brut vrai UTC (t) |
|---|---|
| vente 03-11 ET | 1,31 (**2,55**) |
| achat 11-16 ET | 0,76 (**2,62**) |
| **combiné** | **2,07 bps/jour (t 3,55)**, **SR brut 0,73** |

L'edge est **réellement bilatéral** — les deux jambes dépassent t = 2,5. L'asymétrie signalée dans
le rapport d'origine était un artefact de fuseau, corrigé depuis. Deux aller-retours par jour, coût
FTMO mesuré 2,48 bps/jambe ⇒ 4,96 bps, d'où le net SR de −1,02.

Le kill est donc bien de catégorie **coût**, explicitement rouvrable.

## L'arithmétique du budget de coût

| véhicule | coût/jambe | coût total | net | **SR net** | brut/coût |
|---|---|---|---|---|---|
| FTMO CFD *(mesuré)* | 2,48 | 4,96 | −2,89 | **−1,02** | 0,42 |
| Eightcap ECN *(annoncé, non mesuré)* | 0,75 | 1,50 | +0,57 | **0,20** | 1,38 |
| 6E futures pleine taille *(estimé)* | 0,40 | 0,80 | +1,27 | **0,45** | 2,59 |
| M6E micro *(estimé, commission fixe)* | 1,70 | 3,40 | −1,33 | **−0,47** | 0,61 |

## Ce que les seuils maison exigent

| seuil | coût total maximal | par jambe |
|---|---|---|
| **RESEARCH_PASS (SR > 0,70)** | **0,09 bps** | **0,04 bps** |
| L43 (brut/coût ≥ 1,5) | 1,38 | 0,69 |
| IJR (brut > 3× coût) | 0,69 | 0,34 |

**Voilà le fait décisif : le SR BRUT ne vaut que 0,73, contre un gate à 0,70.** Il n'y a donc
pratiquement **aucun budget de coût** — il faudrait exécuter à 0,04 bps par jambe, ce qu'aucun
véhicule accessible n'approche, ni retail ni même institutionnel.

Le changement de véhicule aide **beaucoup** (de −1,02 à +0,45 de SR) et **ne suffit pas**.

Et le contrat qui tiendrait confortablement dans 13 k€ — le micro — **le rend négatif**, par
domination de la commission fixe sur un petit notionnel : c'est L57 à la lettre.

## Verdict

**Ré-ouverture LÉGITIME, refermée sur l'arithmétique.** Le kill de coût était correctement
classé rouvrable ; l'exercice valait la peine ; le résultat est que le brut est trop mince pour
qu'un véhicule quelconque le sauve.

**Ce que ça épargne** : un cycle complet de recherche — mesure du coût réel chez Eightcap, ouverture
de compte, backtest, walk-forward — pour un plafond de SR de 0,45 connu d'avance.

## Attribution — l'énumération, avant d'archiver

**Ce qui meurt** : la segmentation Ranaldo **sur EURUSD seul, à la spécification de fenêtre testée,
en mono-paire**. Pas « la segmentation Ranaldo ».

| axe | varié ? | pourrait-il retourner le verdict ? |
|---|---|---|
| **Univers multi-paires** | ❌ non | **OUI — le seul axe sérieux.** Le SR de 0,73 est mono-paire. Si le même effet existe sur GBPUSD, USDJPY, AUDUSD, une version diversifiée aurait un SR **mécaniquement supérieur** (l'agrégation de N sources faiblement corrélées multiplie le SR par ~√N), donc un vrai budget de coût. C'est l'axe qui pourrait franchir le gate. |
| Fenêtres horaires | ❌ non | Peu probable — les bornes viennent de la littérature, les balayer serait du data-mining. |
| Vol-targeting / sizing | ❌ non | Non — le SR est invariant au levier. |
| Véhicule | ✅ 4 testés | Non — épuisé par le tableau ci-dessus. |
| Période | ✅ 2007-2026 | Non |

**Classification : kill PARTIEL**, catégorie **breadth/univers**, rouvrable **une fois** sur l'axe
multi-paires. Coût : le brut par paire doit être mesuré sur 4-6 paires avant tout backtest — si le
brut médian par paire est nettement sous 2 bps, l'agrégation ne sauvera rien et l'axe se ferme
définitivement. **C'est un pré-test bon marché et décisif.**

Priorité **moyenne-haute** : c'est le seul candidat de la session dont l'edge brut est bilatéral,
significatif et déjà mesuré sur données corrigées.
