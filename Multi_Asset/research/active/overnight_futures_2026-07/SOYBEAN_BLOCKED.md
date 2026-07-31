# Soja reopen-drift — BLOQUÉ SUR DONNÉES (pas rejeté)

**Statut : UNDERPOWERED, non certifiable avec les données gratuites disponibles. 2026-07-31.**
Ne pas re-tenter sans avoir d'abord résolu le problème de données ci-dessous — le test a déjà été
fait avec **tout** ce qui existe gratuitement.

## Pourquoi ce dossier reste ouvert
Le kill d'origine (`soybean_ftmo_feasibility_2026-06`, breakeven ~2 bps RT) est **nul et non avenu** :
il a été calculé sur **la mauvaise heure**. Le CFD SOYBEAN **ne cote jamais la réouverture CBOT**,
donc l'étude archivée mesurait une fenêtre où l'edge n'est pas (L56 : un drift de session est ancré
à l'horloge de l'ÉCHANGE, pas à UTC).

Sur le **vrai ZS=F**, la vraie fenêtre de réouverture donne :
**+9.65 bps/jour, t_HAC 2.84, N=463**, avec un gap de réouverture **NÉGATIF** — signature opposée à
celle de l'argent, donc **pas** un artefact de gap de halt. C'est encourageant, et insuffisant.

## Ce qui bloque : il n'existe pas d'intraday ZS long en gratuit

| Source | Couverture | Utilisable ? |
|---|---|---|
| `data/GLBX-20260601-FP4HWRA58K/` (Databento GLBX 1-min, 2010-2026) | **`NQ.FUT` uniquement** (`metadata.json` → `query.symbols`) | **non** — ZS absent du batch acheté |
| `yfinance ZS=F` 1 h | 2024-07 → 2026-07 (**~2 ans**) | **déjà utilisé** — c'est la source des N=463 |
| `data/deep_history_utc/SOYBEAN_M1.csv` (CFD, 2017-12 → 2026) | M1 complet | **non** — le CFD ne cote pas la réouverture CBOT |
| `data/deep_history_m1/_cache_duka/SOYBEAN_*.parquet` (Dukascopy CFD) | partiel | **non** — même défaut de session que le CFD |

⇒ **Le test a déjà consommé toutes les données gratuites existantes.** Relancer produirait le même
N=463 et le même verdict. Ce n'est pas un manque d'effort, c'est un mur de données.

## Le test décisif, le jour où le levier data s'ouvre
1. **≥10 ans d'intraday ZS** (Databento GLBX `ZS.FUT`, même batch que NQ — payant) ;
2. une **lecture réelle du spread MZS à 20:00-21:00 ET** (la fenêtre est juste après la réouverture,
   c'est l'heure la moins liquide — le spread y décide de tout, cf. L57 : le coût **fixe** domine en
   bps sur un petit notionnel, et MZS est un petit contrat) ;
3. reprendre la spec **exacte** de `overnight_futures_2026-07/PREREGISTRATION.md`, sans ré-optimiser.

**Avertissement matériel (L57)** : MZS ≈ $11 k de notionnel. La commission fixe (~$1.70 RT) y pèse
~1.5 bps à elle seule, contre 0.66 bps sur MGC. Un edge de ~9.65 bps garde de la marge, mais le
budget est bien plus serré que sur l'or — le spread mesuré à la réouverture peut le refermer seul.

## Ce que ce dossier ne dit PAS
Il ne dit pas que l'edge existe. Il dit que **le kill précédent était faux** et que la mesure de
remplacement est **sous-puissante**. Vocabulaire à trois valeurs : **UNDERPOWERED**, ni PASS ni
REJECTED — et un UNDERPOWERED **ne consomme pas** le budget de modifications de la famille.
