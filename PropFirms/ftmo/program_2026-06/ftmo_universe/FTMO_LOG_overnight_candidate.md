# FTMO — Overnight equity premium : entrée de log (CANDIDAT À MERGER)
*Corrections équipe appliquées (2026-06-03). Ne pas renuméroter. Périmètre = equity-overnight uniquement.
Ne touche pas `data/trend_research/` ni la section trend du log.*

## Verdict (accepté par l'équipe)
**L'edge EXISTE net de coûts** (swap + spread) — positif la plupart des années (cf. table §risque ;
seul 2022 négatif). Ce **n'est PAS un « edge mort net de coûts »**. Il est **non-déployable** pour
**DEUX raisons distinctes**, à ne pas confondre avec le coût :

- **(a) beta-proxy** — β ≈ 0,33, corr ≈ 0,57 vs l'indice : exposition beta déguisée, **dilutive sous
  le gate SR 0,70** (SR standalone 0,68 < 0,70).
- **(b) gap-tail** — queue gauche de type cluster semaine-COVID (≈ **−12 % cumulé** sur 3 nuits) →
  **breach potentiel du floor total 10 %**.

Swap **résolu proprement** (unité 0,01 cross-validée EURUSD/XAUUSD ; US100.cash swap_long −662,4 pts
= **−3,08 bps/nuit**, triple-swap = **vendredi**).

## Risque de queue — REFORMULÉ [correction #1]
Ce **n'est pas un « carry-crash »** : il n'y a pas de carry ici. L'effet est l'**equity overnight
premium**, et son risque de queue est un **GAP overnight (queue gauche)** — pas un dénouement de carry.
- Pire nuit du book cross-régional : **−5,1 %** (gap COVID, 2020-03-09). Cluster semaine-COVID
  (2020-03-09/12/16) ≈ **−12 % cumulé → breach du floor total 10 %**. Risque = **gap-tail**, pas carry.

**Année-par-année, MESURÉ** (NQ overnight, all-nights, bps/nuit) :

| Année | GROSS | NET swap | NET swap+spread |
|---|---:|---:|---:|
| 2016 | −0,6 | −3,6 | −5,6 |
| 2020 | +12,0 | +8,9 | +6,9 |
| **2022** | **−8,9** | **−12,0** | **−14,0** |
| 2023 | +4,4 | +1,3 | −0,7 |
| 2024 | +10,3 | +7,2 | +5,2 |
| 2025 | +6,1 | +3,0 | +1,0 |

→ **Correction du claim** : le « 2023-2024 net négatif » était une **impression non mesurée**. Mesuré,
**2023-2024 net-de-swap = +4,3 bps (POSITIF)**, net swap+spread = **+2,3 bps**. L'année réellement
négative est **2022** (−12 net / −14 net+spread : régime bear + hausses de taux), avec 2016 et 2011
secondairement négatives. La fragilité de régime est **concentrée sur les bear/chocs-de-taux soutenus
(2022)**, pas sur 2023-2024. → claim « 2023-2024 négatif » **retiré**, remplacé par le chiffré ci-dessus.

## Leçon [correction #2 — CANDIDAT NOMMÉ, non numéroté]
> **LESSON-CANDIDATE: overnight-equity-premium = beta-proxy** — n'admettre qu'en **long-short** ou avec
> **β-hedge explicite** (sinon = exposition beta déguisée, dilutive sous gate SR 0,70).

*NB : ne pas réutiliser « L36 » — collision avec le L36 existant de CLAUDE.md (« edge hebdo s'annualise
en √52 »). Numérotation tranchée au merge.*

## Périmètre [correction #3]
**Finding EQUITY-overnight-SPÉCIFIQUE.** À ne PAS lire comme une affirmation générale sur l'overnight.
L'overnight **FX / Gold** peut se comporter différemment (un finding opposé d'une autre session est
valide — **instruments différents, les deux coexistent**). Le gap-tail + le verdict beta-proxy ci-dessus
ne portent que sur les **indices actions**.

## Non touché
`data/trend_research/` et la **section trend du log** : intacts (par consigne).
