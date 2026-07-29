# Pre-FOMC drift US30 / GER40 — ré-ouverture sur échantillon étendu

**Verdict : REJECTED.** Non pas sur une statistique, mais sur le **split de régime** (L31).
Date : 2026-07-29. Spec **non modifiée** — celle du batch `top10_test` appliquée telle quelle.

## Pourquoi la ré-ouverture était justifiée

`summary_batch_142.csv` : `ed_fomc_US30_LO` → SR_excess 0.96, MaxDD −6.8 %, WF 5/5,
cost gate 6.4, `ftmo_p_pass_p1_p2` **0.6385**, **HAC_t_excess 2.4058 contre un gate à 2.50**.
Raté pour **0.09**. `ed_fomc_GER40_LO` → HAC_t 1.96.

**Finding n°1 — l'échantillon n'était pas limité par les données, mais par le fichier
d'événements.** Le batch lit `Forex/data/news_events_2020_2025.csv`, qui ne contient que
**49 FOMC (2020-01-29 → 2025-12-10)**, alors que
`data/personal_book/post_fomc_drift/data_cache/fomc_events.csv` en contient **182 (2004-2026)**,
dont **102 depuis le début des données US30** (2013-09-30). La troncature était accidentelle.

## Spec répliquée (inchangée)

`batch_strategies.py::family_event_drift` : entrée au **close daily T-1**, sortie au **prix de
19:00 UTC le jour de l'événement**, long-only, coûts `FTMO_COST_BPS_RT[indices] = 4.6 bps` +
**1 nuit de swap −3.0 bps**. L'heure 19:00 UTC est celle du fichier source (48 cas sur 49 ; pas
d'ajustement DST) — reprise à l'identique.

## Résultats

| Série | n | gross bps | net bps | t_HAC |
|---|--:|--:|--:|--:|
| **US30 total 2013-2026** | 97 | +20.69 | **+13.09** | **2.12** |
| US30 pré-2020 *(hors échantillon)* | 47 | +15.84 | +8.24 | 1.25 |
| US30 2020+ *(l'échantillon d'origine)* | 50 | +25.25 | +17.65 | 1.70 |
| **GER40 total 2013-2026** | 99 | +20.95 | **+13.35** | **1.40** |
| **GER40 pré-2020** | 49 | +7.73 | **+0.13** | **0.01** |
| GER40 2020+ | 50 | +33.91 | +26.31 | 1.85 |
| **Pool US30+GER40** | 101 | — | **+11.75** | **1.65** |
| pool pré-2020 | 46 | — | +6.15 | 1.14 |
| pool 2020+ | 49 | — | +22.89 | 1.89 |

Placebo US30 (3000 tirages de 97 jours non-FOMC, même fenêtre close→19:00) : observé
**+20.69** vs médiane +3.77, p95 +18.60 → **96.8ᵉ percentile** (franchi, de justesse).

## Ce qui tue le candidat

1. **GER40 est NUL hors échantillon** : +0.13 bps net, **t = 0.01** sur 49 événements pré-2020.
2. **Le profil est le même sur les deux instruments** : l'effet est 1.6× (US30) à 4.4× (GER40)
   plus fort après 2020 qu'avant. C'est la signature d'un **effet de régime**, pas d'un edge
   structurel — et 2020-2025 est précisément la fenêtre COVID + QE illimité + hausses de 75 bps,
   où chaque FOMC portait un enjeu exceptionnel.
3. **Doubler l'échantillon ne renforce pas le t, il l'affaiblit.** Attendu si l'effet était
   stable : `2.41 × √(97/49) ≈ 3.39`. Obtenu : **2.12**. Le gate de 2.50 n'est franchi par
   aucune série.
4. **Le pooling n'aide pas** : t 1.65 pour le pool contre 2.12 pour US30 seul. La corrélation
   entre les deux jambes sur événements communs est **0.544** — elles ne sont pas indépendantes,
   donc le gain de puissance théorique est faible et la jambe faible (GER40) dilue.

## Finding n°2 — le « SS » du batch n'est PAS un test two-sided

`batch_strategies.py` instancie la jambe short par `side = -side_long` : c'est l'inverse
**mécanique** exact du long (`mean_bps_per_trade_gross` +29.407 / −29.407 dans le CSV).
**L25 n'a donc jamais été réellement appliqué à cette famille**, contrairement à ce que la
présence d'une ligne `_SS` laissait croire. Vrai pour toute la famille `event_drift` du batch.

## Finding n°3 — colonne spread

GER40 à 19:00 UTC : **22 % des barres ont un spread nul** dans `deep_history_utc`. Cohérent
avec le finding du même jour sur le FX (EURUSD 66-69 % de barres nulles en 2021-2023, et
sous-estimation d'environ 2.4× du RT FTMO réel même quand la colonne est peuplée). Ici sans
conséquence — le batch utilise un coût forfaitaire, pas la colonne — mais à retenir.

## Réserves

- `t_HAC` calculé ici sur les **trades** (n≈100) ; le batch le calculait sur une série
  **quotidienne** de 1531 jours. Le « 2.41 → 2.12 » est une tendance, pas une mesure appariée.
- Le test `Δp(pass)` marginal sur le book n'a pas été lancé : inutile sur un candidat rejeté
  au split de régime.

## Conséquence pour le registre

Le candidat était présenté comme « raté de 0.09 sur le t ». Il est en réalité mort d'un
**effet de régime post-2020**, ce que l'échantillon tronqué ne pouvait pas révéler. La leçon
n'est pas « le gate était trop strict » mais **« l'échantillon était tronqué par un fichier
d'entrée, et personne ne l'avait vérifié »**.
