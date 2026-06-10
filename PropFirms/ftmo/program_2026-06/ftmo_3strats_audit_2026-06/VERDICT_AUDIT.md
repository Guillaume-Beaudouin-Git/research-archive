# Audit — Rapport "FTMO 3 stratégies" (S1/S2/S3 intraday indices)

**Date** : 2026-06-04 · **Source** : `data/ftmo_universe/FTMO_3_strategies_rapport.pdf`
**Périmètre** : audit indépendant des claims du rapport, re-implémentation depuis specs PDF,
NQ databento 1-min 2010-2026 + MT5 indices. Rien figé / mergé.

---

## TL;DR — Verdict global : **NO-GO**

Le portefeuille "3 moteurs décorrélés Sharpe 0,99" du rapport est en réalité :
**long-Nasdaq (S1) + 1 jambe morte-au-coût (S2) + beta-PM long-equity (S3)**, dont la
corrélation in-sample ≈ 0 est un artefact de fenêtre 2021-2026 dominée par le bull post-Covid.

- **S1** : reproduction Sharpe 0.70 sur 2021-2026 (rapport 0.73 ✓). Mais sur 16 ans
  (NQ databento 2010-2026) Sharpe = **0.14**, α non significatif (t_HAC = 0.69),
  jambe SHORT cumulée **négative −1.18 R**, **86 % du P&L vient de 2023-2026**, perdant
  en up-regime 2010-2022. Décomposition jambe-par-jambe : LONG β = +1.44 (t = 9.6) α ≈ 0 ;
  SHORT β = −1.76 (t = −10.9) α ≈ 0 — **pur beta-NQ sur les deux côtés, alpha absent**.
  DSR du 0.73 à N=105 trials = **20 %** (FAIL 95 % gate).

- **S2** : signal cross-sectionnel sur **N = 4 indices** (US500/100/30/2000, corrélations
  0.85-0.95 entre eux) → **viole L_methodology N ≥ 30** ; le rapport admet "edge mince,
  négatif dès 2× coûts, à n'utiliser que combiné" — non viable autonome, et la diversification
  apportée au combiné est elle-même un artefact d'une fenêtre courte (voir intégrité S2 ci-dessous).

- **S3** : **long-seul 3 indices** PM 12:30→16:00 = beta long-equity pur par construction.
  Le rapport admet "directionnelle long → dépend du régime actions (négative en 2022)" et
  "tient jusqu'à ~2× coûts". Décorrélation in-sample vs S1 = artefact temporel (S1 = matin,
  S3 = après-midi) et non d'edge orthogonal — la décomposition beta donnerait β ≈ 1 sur l'horizon
  PM, redondant avec S1 long-leg.

- **Intégrité données** : confirmation MT5 "intraday déguisé" pré-2021 (1 bar/jour). Le
  timestamp MT5 `utc` est en réalité **GMT+3 server-time** (confirmé par alignement volume
  peak MT5 17h "UTC" = 14h UTC réel = 09:00 ET cash open). Une fois corrigé :
  corr signal MT5 US100 vs NQ databento = **0.76-0.87** par année, corr full-session 0.93-0.96.
  **Le rapport n'a vraisemblablement pas ce bug** : ses chiffres S3 reproduisent quasi-identique
  (Sharpe ×1/×2/×3 = 0.35/0.10/−0.16 chez moi vs 0.40/0.09/−0.22 rapport). Le spread US100 à
  11:00 ET réel = 0.95 bp RT médian, **cohérent avec le modèle de coût du rapport**.

**Conclusion** : le rapport est honnête sur sa reproductibilité (specs claires, Sharpe
0.73 reproduit) mais le **3-moteurs combiné est un regime-fit du bull 2023-2026**. Le
verdict "porte tout le rendement" sur S1 dans le rapport (88 % du P&L combiné) cache
qu'il s'agit de **beta long-NQ avec un drag d'auto-cancelling sur la jambe short**, et
que les 2 autres briques sont admises non viables hors combiné.

---

## Phase 1 — S1 (décisive)

### Re-implémentation indépendante depuis specs PDF

Code : `code/01_s1_backtest.py` (depuis page 5 du PDF, sans regarder le code du rapport).

| Élément | Valeur retenue |
|---|---|
| Univers | NQ futures (databento GLBX 1-min, front-month roll par volume max/jour) |
| RTH | 09:30 → 16:00 ET (391 bars/jour médiane) |
| Signal | sign(open(11:00 ET) − open(09:30 ET)) |
| Filtre | \|move\| > 0.3 × ATR(14) daily (ATR à t-1, Wilder) |
| Entrée | open(11:00 ET) |
| Stop | entry ∓ 3 × ATR(14) (intrabar low/high check) |
| Sortie | close du dernier bar RTH (16:00) ou stop |
| Unité de P&L | R-multiple = pnl_pts / (3 × ATR) |
| Fenêtre | 2010-06-06 → 2026-05-31 (4 089 sessions) |

**Cross-check spec OK** : sur fenêtre exacte 2021-2026 du rapport, je reproduis
Sharpe = **0.70** vs rapport **0.73**. L'écart résiduel (≈ 4 %) s'explique par :
NQ futures roll-ajusté vs US100 CFD spot (le rapport utilise US100 MT5), ATR sur
prix différents, sizing en R-multiples vs %-equity.

### Métriques globales — full sample 2010-2026 (16 ans)

| | Sharpe | sum_R | Long sum_R | Short sum_R | n_trades | win_rate | DD R |
|---|---|---|---|---|---|---|---|
| **Full 2010-2026** | **0.14** | +3.72 | +4.90 | **−1.18** | 1 645 | 51.1 % | −6.55 |
| Pré-2021 (2010-2020) | **−0.13** | −2.35 | +0.92 | **−3.28** | 1 065 | 48.6 % | −6.36 |
| Fenêtre rapport 2021-2026 | +0.70 | +6.08 | +3.98 | +2.10 | 580 | 56.6 % | −2.42 |

### L25 split-direction — verdict

| Période | Long mean R/trade | Short mean R/trade | Short win_rate |
|---|---|---|---|
| Full 2010-2026 | +0.0059 | **−0.0014** | 45.8 % |
| 2010-2020 | +0.0017 | **−0.0062** | (négatif persistant) |
| 2021-2026 | +0.0067 | +0.0040 | (positif fenêtre récente uniquement) |

**Jambe SHORT cumulée −1.18 R sur 16 ans** et −3.28 R sur 2010-2020. La condition
"L25 split-par-direction" demandée → résultat : la jambe short ne contribue pas à
un edge sur l'historique long ; elle ajoute du beta dans le sens d'un short-NQ
sans alpha. Ce n'est **pas un edge two-sided** au sens du goal.

### Régression beta HAC NW lag-6

| Régression | n | α (annualisé R) | t(α)_HAC | β | t(β)_HAC | R² |
|---|---|---|---|---|---|---|
| Full S1 vs NQ daily | 4 089 | +0.293 | **0.69** | −0.32 | −1.67 | 0.15 % |
| Long-jours uniquement | 4 089 | +0.023 | **0.09** | **+1.44** | **+9.61** | 7.2 % |
| Short-jours uniquement | 4 089 | +0.270 | **0.85** | **−1.76** | **−10.91** | 7.6 % |

Lecture : **α non significatif partout** (max t = 0.85). Les jambes prises séparément
sont **β ≈ ±1.5 sans alpha** : exactement la signature "pure exposure NQ pendant la
fenêtre où le signal est actif", soit une exposition directionnelle conditionnelle, pas
un edge.

### Split par régime (rolling 60-day NQ return : up > +5 %, down < −5 %, chop)

| Période × régime | n_sess | sum_R | sum_R_long | sum_R_short | Sharpe |
|---|---|---|---|---|---|
| Pre-2015 × up | 551 | −0.28 | +0.52 | **−0.80** | −0.08 |
| Pre-2015 × down | 81 | +1.09 | +0.96 | +0.13 | +2.02 |
| 2015-19 × up | 560 | **−3.45** | −0.50 | **−2.95** | **−0.83** |
| 2015-19 × chop | 603 | +3.81 | +1.69 | +2.13 | +0.88 |
| 2020-22 × up | 367 | **−2.37** | −1.29 | −1.09 | **−0.95** |
| 2020-22 × down | 200 | +0.93 | +1.47 | −0.54 | +0.77 |
| 2023-26 × up | 501 | **+3.23** | +1.50 | +1.73 | **+1.00** |
| 2023-26 × down | 71 | +0.68 | +0.62 | +0.06 | +1.44 |

**Arbitre du goal** : "S1 marche-t-il en up ET tient-il en chop/down (edge), ou marche-t-il
en up et saigne en down (beta) ?". Réponse :
- Avant 2023, S1 **PERD en up-regime** (Sharpe −0.08, −0.83, −0.95 pour les 3 sous-périodes) —
  fait exactement l'inverse de ce que prédirait un edge "intraday Nasdaq drift". 
- Seul **2023-2026 × up** donne Sharpe +1.00. C'est la fenêtre du rapport ; ce n'est pas un edge,
  c'est un **fit sur le bull récent**.
- En down-regime, S1 est positif (cohérent avec une jambe short qui marche occasionnellement en
  marché baissier), mais N petit (477 sessions sur 4 089) et résultat porté par 2010-2014 +
  2023-2026.

**STOP-POINT 1 : verdict S1 = beta long-Nasdaq + regime-fit, NO-GO.**

---

## Phase 2 — DSR & coût (partielle, conduite par rigueur malgré STOP-POINT 1)

### Deflated Sharpe Ratio (Bailey-LdP 2014)

| SR_hat | T_obs | skew | kurt_excess | t_SR brute | N=50 DSR | N=105 DSR | N=120 DSR | N=200 DSR |
|---|---|---|---|---|---|---|---|---|
| Rapport 0.73 (2021-2026) | 1 394 | +0.26 | +15.94 | 1.72 | 0.29 | **0.20** | 0.19 | 0.15 |
| Mon 0.70 (2021-2026) | 1 394 | +0.26 | +15.94 | 1.65 | 0.27 | 0.18 | 0.17 | 0.13 |
| Mon 0.14 (2010-2026) | 4 089 | −0.12 | +11.64 | 0.56 | 0.04 | **0.02** | 0.02 | 0.01 |

**Le 0.73 du rapport ne survit pas à la déflation** (DSR 20 % à N=105, bien sous 95 %).
Même en supposant N=50 (seulement les survivants principaux) : DSR = 29 %, FAIL.

### Coût FTMO réaliste (post-correction MT5 GMT+3)

MT5 US100 spread à 11:00 ET (vrai cash session, post-correction) :
- médiane **80 points = 0.95 bp RT**, p95 145 pts = 1.72 bp RT (1 pt = 0.01 USD, US100 ≈ 19 000)

→ **Le modèle de coût du rapport est validé** sur la fenêtre 2021-2026. Les sensibilités
×1/×2/×3 du rapport (Sharpe S1 0.78 → 0.53 → 0.29) sont cohérentes.

**Conséquence pour le verdict S1** : le 0.73 brut survit techniquement au coût réel (descend
à 0.53 à 2×, 0.29 à 3×). Mais la déflation multi-test (DSR 0.20) + le full-sample 16 ans
(Sharpe 0.14) restent les arbitres. **Le coût ne sauve pas un regime-fit beta.**

---

## Phase 3 — S2 / S3 / Intégrité

### Intégrité MT5 vs databento (overlap 2021-2026)

**Résolution timezone** : les timestamps MT5 sont labellés `utc` mais sont en réalité
**GMT+3 server-time** (typical FTMO MT5 broker setting où NY 17:00 close = serveur 24:00).
Diagnostic : volume MT5 peak à hour 17 "UTC" = 14:00 UTC réel = 09:00 ET cash open (cohérent
avec winter, et confirmé par alignement serveur GMT+3 winter / GMT+2 summer + US DST).
La transformation correcte : `real_UTC = mt5_timestamp - 3h`, puis tz_convert ET classique.
**Ce n'est probablement PAS un bug du rapport** mais un piège de nommage du dump CSV.

Une fois la correction appliquée :

| Année | n_jours | corr signal (09:30→11:00 ET) | corr full session (09:30→16:00 ET) |
|---|---|---|---|
| 2021 | 256 | **0.80** ✓ | 0.94 |
| 2022 | 258 | **0.87** ✓ | 0.96 |
| 2023 | 257 | **0.81** ✓ | 0.93 |
| 2024 | 259 | **0.83** ✓ | 0.93 |
| 2025 | 257 | **0.76** ✓ | 0.96 |
| 2026 | 104 | **0.62** | 0.84 |

Corrélation signal_ret 0.76-0.87 = cohérent avec US100 spot ≠ NQ futures (cash dividends,
roll yield, fair value), pas un défaut. **MT5 indices données utilisables post-correction.**

**Spread US100 RTH ET (post-correction, 2021+)** :
- À 11:00 ET (S1 entry) : médiane 80 pts = **0.95 bp RT** (1 pt = 0.01 USD)
- p95 145 pts = 1.72 bp RT
- À 09:30 ET (US100 cash open) : médiane 90 pts = 1.06 bp RT
- À 15:30-15:59 ET (PM/close) : médiane 90 pts, p95 220 pts

→ **Le modèle de coût du rapport (∼1 bp RT US100 à 11:00 hors-auction) est validé.**
La sensibilité ×1/×2/×3 du rapport reflète bien des seuils réalistes.

### S2 — Reversion cross-sectionnelle (reproduit MT5 4 indices 2021-2026)

Re-implémentation : à 10:30 ET, rdt depuis 09:30 par index → z-score cross-sec → poids
w = −z normalisés Σ|w|=1 → hold jusqu'à 16:00 ET. 1 208 sessions effectives.

| Cost mult | Sharpe brut | Sharpe net | Rdt cumulé |
|---|---|---|---|
| Gross (×0) | +0.05 | — | +0.75 % |
| ×1 (~1 bp/index turnover) | — | **−0.71** | −11.3 % |
| ×2 | — | −1.46 | −23.4 % |
| ×3 | — | −2.21 | −35.5 % |

**Reproduction plus pessimiste que le rapport** (rapport : Sharpe brut 0.44, négatif dès 2×).
Différences possibles : sizing rapport "levier 0.76" vs mien Σ|w|=1, slippage non modélisé,
détail spec. Mais la **direction est confirmée** : S2 **mort au 1× coût réel** dans ma repro,
au mieux marginal en gross.

**Verdict S2 confirmé** : non viable autonome ; le "diversifiant market-neutral" du combiné
ne tient même pas au 1× cost réel dans ma reproduction. Viole aussi L_methodology N ≥ 30
(N = 4 indices US 0.85-0.95 corrélés entre eux = signal de variance quasi-nulle).

### S3 — Dérive PM long-equity (reproduit MT5 3 indices 2021-2026)

Re-implémentation : à 12:30 ET, LONG equal-weight US500/US100/US30 → hold 16:00 ET. 1 190
sessions effectives.

| Cost mult | Sharpe net |
|---|---|
| Gross (×0) | +0.60 |
| ×1 (~1 bp RT par index) | **+0.35** |
| ×2 | +0.10 |
| ×3 | −0.16 |

| Métrique rapport | Mon estim. |
|---|---|
| Sharpe brut 0.40 (rapport) vs +0.60 (mien — plus optimiste) | écart ~0.20 |
| Sharpe ×2 : 0.09 (rapport) vs +0.10 (mien) | ≈ identique ✓ |
| Sharpe ×3 : −0.22 (rapport) vs −0.16 (mien) | très proche ✓ |

**Reproduction quasi-identique au rapport sur la sensibilité coût** (les multipliers ×2/×3
collent à 0.01-0.06 près). Le brut un peu plus haut chez moi vient probablement d'un
sizing/calibration mineur.

**Verdict S3 confirmé** : long-equity PM intraday-drift, edge réel mais marginal :
- Sharpe net 1× = +0.35 → **bien en dessous du gate PROPFIRM_PASS (1.0)** et RESEARCH_PASS (0.7).
- Casse dès 2-3× cost.
- **β long-equity par construction** (le signal n'est pas adaptatif — toujours long), donc
  redondant avec une exposition S&P pendant heures de bureau.
- La décorrélation in-sample vs S1 est un **artefact temporel** : S1 entre à 11:00, S3 entre
  à 12:30 — différents segments du même biais long-equity post-bull 2023+.

---

## Portefeuille combiné — verdict final

Le rapport combine S1 + S2 + S3 à parts de risque égales → Sharpe 0.99, Calmar 0.97,
DD 7.5 %, 0 % breach historique 2021-2026.

**Décomposition réelle du combiné** :
- **S1 porte le rendement** (rapport page 9 : "S1 porte 2023-2026", combiné 27.6 %
  passage 1 an, S1 seul 45.9 %).
- **S2 contribue principalement une variance basse** (Sharpe 0.44, Calmar 0.22, rdt 1.7 %/an,
  edge mince).
- **S3 contribue +1.5 %/an de premium long-equity PM**.

Sur la fenêtre 2021-2026, S2 + S3 ont des décennies de **survie statistique fragile**
(régime 2022 : tous les trois négatifs, sauf S1 marginalement −1.9 %). Le combiné gagne
parce que les drawdowns ne se chevauchent pas exactement en 2021-2023 — mais cette
non-chevauchement est **non garantie hors fenêtre**. Aucune Phase 3 OOS possible (la consigne
le note explicitement : "PAS d'OOS possible faute de données autres indices").

**Verdict combiné** :
- Le portefeuille n'est PAS "3 moteurs décorrélés". Recomposition réelle :
  - **S1** = long-NQ 11:00→16:00 ET, regime-fit 2023-2026, β long-leg = +1.44, α non sig sur 16 ans.
  - **S2** = cross-sec 4-indices, **mort au coût réel** dans ma repro (Sharpe net 1× = −0.71),
    viole N≥30.
  - **S3** = long-equity 12:30→16:00 ET, Sharpe net 1× = +0.35 ≪ 1.0 gate, casse à 2× cost.
- La décorrélation observée est dominée par les **fenêtres d'entrée/sortie distinctes**, pas par
  des sources d'alpha orthogonales (S1 et S3 sont les deux long-equity bull conditionnel).
- Le combiné Sharpe 0.99 sur 2021-2026 est porté à >85 % par S1 dans la fenêtre bull, et **S1
  lui-même est un regime-fit**.
- DSR du combiné non calculé par le rapport ; appliqué aux mêmes prémices (N ≥ 105 trials),
  pas de raison de penser qu'il survive à la déflation.

---

## Réponse explicite à la question du goal

> "Le portefeuille '3 moteurs décorrélés' tient-il, ou est-ce long-Nasdaq + 1 jambe morte-au-coût
> + du beta PM dont la corrélation in-sample est un artefact ?"

**Réponse : ce dernier.** Le rapport est techniquement honnête sur ses chiffres et reproductible
sur sa fenêtre, mais il **sur-vend la décorrélation** comme "3 moteurs orthogonaux" alors que :
- S1 est un long-NQ regime-fit beta (démontré full-sample 2010-2026 : Sharpe 0.14, jambe short
  cumulée négative, alpha non sig, DSR 0.20).
- S2 est admis non viable hors combiné par le rapport lui-même + N=4 viole les règles cross-sec.
- S3 est par construction du beta long-equity intraday PM.

**Recommandation** : NO-GO sur déploiement FTMO de ce portefeuille tel quel. Si l'utilisateur
souhaite un futur passage S1 standalone, il faudrait : (a) clarifier la timezone MT5 et
re-tourner les chiffres avec spread réel à 11:00 ET vrai, (b) appliquer un DSR sur la
vraie famille de trials, (c) tester sur un échantillon OOS post-2026 d'au moins 1 an avant
toute conviction.

---

## Artefacts

- `code/00_load_databento_nq.py` — décompression dbn.zst + panel 1-min RTH + daily
- `code/01_s1_backtest.py` — S1 indépendant sur NQ 2010-2026
- `code/02_s1_beta_regime.py` — beta-regression + tag régime
- `code/03_s1_window_crosscheck.py` — slice fenêtre 2021-2026
- `code/04_dsr.py` — DSR Bailey-LdP
- `code/05_mt5_databento_integrity.py` — intégrité initiale (timezone non-corrigé)
- `code/06_mt5_tz_resolve.py` — résolution timezone MT5 → GMT+3 server
- `code/07_mt5_corrected_integrity_s2_s3.py` — repro S2/S3 + spread bucket ET réel
- `results/s1_*.{parquet,json,csv}` — outputs S1
- `results/s2_reproduction.parquet`, `s3_reproduction.parquet`, `s2_s3_reproduction.json`
- `results/mt5_*.{csv,json}` — intégrité MT5

**Rien figé / mergé.** Branche locale uniquement.
