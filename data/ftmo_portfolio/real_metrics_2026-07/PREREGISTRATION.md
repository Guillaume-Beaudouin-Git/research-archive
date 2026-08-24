# PRE-REGISTRATION — Métriques RÉELLES du book (compte 3, <ACCOUNT_ID>) : gate J1 + low-check

**Gelée AVANT résultats.** Author≠auditor. Read-only recherche, aucune action live. Worktree
`claude/real-book-metrics-lowcheck` (off origin/main 80f7e5d, gate #343 inclus). Moteur canonique
(`engine_v22`, chaîne v2.2.1) **NON muté** — le low-check est une couche d'évaluation à côté.

## 1. Question
p(pass) réelle du challenge FTMO 2-step pour le book **tel que configuré aujourd'hui** (compte 3),
en triplet :
1. **p(pass challenge)** — proba de passer P1+P2.
2. **Nombre moyen d'essais avant un pass** — E[#challenges achetés avant 1er funded] ; rapporter la
   DISTRIBUTION MC réelle, pas seulement 1/p.
3. **Temps moyen jusqu'au pass** — jours calendaires ; distinguer temps/tentative (médian) vs temps
   total espéré jusqu'au 1er pass (somme tentatives échouées + réussie).

Plus **p(funded 3 mois)** et **EV/campagne** (VAL·p_funded − FEE·attempts).

Les 2 comptes déjà fail (<ACCOUNT_ID>, <ACCOUNT_ID>) NE conditionnent PAS ce chiffre : tirages
indépendants, même config gate. Question = « p(pass) du book tel que configuré, mesurée honnêtement »,
PAS « proba après 2 échecs ».

## 2. Les deux corrections vs le baseline cité (71.4% / +$740)
Le baseline cité = **marge SWING + M5-close + SANS gate** (RECOST v2.2.1 : POLICY 87.01 → SWING 71.4,
Δ −15.58pt ; EV≈+$740). Le compte 3 réel diffère par :
- **(A) GATE J1 ACTIF** (déployé #343) : suspension USDJPY si close ≥ 160, reprise après 10 closes ≤ 155
  (causal T-1). Mécanisme = `wt[:,1] *= (1−flag)` (identique au live `weights["USDJPY"]=0`).
- **(B) LOW-CHECK au bid** : bust testé au LOW intra-barre M5 (long) / HIGH (short), pas au M5-close.
  Motivé par les 2 breachs réels 02-03/07 (audit cf48e80 : sim M5-close sous-compte les busts
  intra-barre ; **seul le Δ entre bras est robuste, p(pass) absolu M5-close optimiste**).

Config compte 3 = **SWING + GATE + LOW-CHECK**, données → horizon disponible.

## 3. Volet 0 — Données (GELÉ, résolu empiriquement)
- **Panel canonique** `cache/sim_m5_repaired.parquet` (4 legs XAUUSD/USDJPY/US100/GER40, M5-close),
  tz-naïf, **2013-09-25 → 2026-06-05 22:55**, pas 5min.
- **Alignement tz — RÉSOLU (probe_align.py)** : `sim_m5 == deep_history_utc localisé Europe/Paris`
  (CET/CEST : +1h hiver / +2h été), **median|Δ| = 0.00000 yen** (2024-02-14 ET 2024-08-14, 276/264
  barres). Barres **left-labeled** (label=left,closed=left : |Δ|=0 vs right : 0.016). CONSÉQUENCE
  FORTE : sim_m5 et deep_history sont la MÊME donnée sous-jacente → le low-check depuis deep_history
  M1 est un **overlay exact sur la même grille/source** ; **PAS de confusion source MT5↔Duka** (le
  résidu 3.6 pips craint par l'étude M1 ne s'applique PAS au panel historique). Le Δ(low−close) est
  pur (intra-barre), pas un artefact de source.
- **Spread** : colonne `spread` en points MT5 (10^−digits) ; USDJPY digits=3 (pt 0.001),
  XAU/US100/GER40 digits=2 (pt 0.01). Marquage bid (long) = low − ½·spread·pt ; ask (short) =
  high + ½·spread·pt. (Second ordre vs low−close pour un flash ; inclus par rigueur, réserve audit (a).)
- **Coûts/marge** : chaîne v2.2.1 gelée (config_v22 : swaps mesurés en option, `MARGIN_RATES_SWING`
  = {XAU 1/9, JPY 1/30, US100 1/15, GER40 1/15}, cap 0.60). Signal via `E.build_signals()`.
- **Horizon** : données → 2026-06-05. Cohorte complétable = besoin 91j de données ⇒ **dernier start
  complétable ≈ 2026-03-06** (data 06-05). L'extension → 07-06 (Volet 5) N'AJOUTE PAS de cohorte
  complétable (mur 91j + horizon data) → traitement HONNÊTE : MC sur data dispo ; les flashs 07-02/03
  traités par REPLAY ciblé (§7), là où ils sont décision-pertinents, pas dans le sweep cohortes.

## 4. Design expérimental (2×2 × marge), tout le reste identique
Grille cohortes canonique : `C22.WINDOWS` (IS 2013-10-01→2019-12-31, OOS 2020-01-02→2026-02-25),
step 7 → 462 cohortes (comparabilité exacte suspend study). Variante étendue (OOS_hi → dernier
complétable) rapportée en robustesse.

Cellules (marge SWING = primaire ; POLICY = ancre) :
| # | gate | eval | rôle |
|---|------|------|------|
| 1 | OFF | close | **baseline** → doit reproduire SWING 71.4 / POLICY 87.01 |
| 2 | ON  | close | baseline + gate → Δp_gate (doit confirmer +0.65 sur POLICY) |
| 3 | OFF | low   | baseline + low-check → correction d'optimisme SEULE |
| 4 | ON  | low   | **COMPTE 3 RÉEL** → triplet livrable |

Paires (vs baseline apparié par cohorte) + block-bootstrap circulaire (bloc=10, 3000 tirages,
**seed=23**), CI90 (décision) + CI95 (comparabilité). N_eff via autocorr (convention aggregate_suspend).

## 5. Spécification LOW-CHECK (exacte, gelée)
Clone instrumenté de `engine_v22.run_phase/run_funnel/run_funded` (`lowcheck_engine.py`). IDENTIQUE au
canonique SAUF la détection de breach :
- Panels additionnels `M["lo"]`, `M["hi"]` (même shape que `px_day`, bid/ask-ajustés), alignés grille sim_m5.
- Par barre : `adv_k = lo_k` si `pos_k>0`, `hi_k` si `pos_k<0`, sinon `close_k`.
  `pl_adv = Σ_k pos_k·(adv_k/avg_k − 1)` ; `eq_adv = bal + pl_adv − dip`.
- **Bust/breaker** (`hb`,`hk`) testés sur `eq_adv + gap_extra` (au lieu de `eq`).
- **Target** (`ht`) et **comptabilité** (trades, flat, swaps, pass) **INCHANGÉS** (close). Conservateur
  sur les pass (pas de pass fabriqué au high).
- `mode="close"` ⇒ `adv_k ≡ close_k` ⇒ **reproduit engine_v22 exactement** (EQUIV gate obligatoire).
- **Simultanéité (conservateur)** : primaire = tous les legs à leur extrême de barre (borne HAUTE de
  busts). Sensibilité rapportée = **dominant-leg-only** (seul le leg au pire move adverse utilise son
  extrême, autres au close) = borne BASSE. Δ vrai ∈ [dominant, all-legs]. Mesurer aussi le taux de
  bust low-check sur jours NON-flash (inflation « jour normal »).

## 6. Gates de validation (STOP si échec)
- **G-tz** : reconstruction M5-close depuis deep_history (Paris, left) == sim_m5 close, médian|Δ| ≈ 0
  sur l'overlap (modulo trous GER40/ffill). [Volet 0 : 0.00000 sur 2 jours → à confirmer full-history.]
- **G-EQUIV-close** : `lowcheck_engine(mode=close)` == `engine_v22.run_funnel` sur les 462 cohortes
  (funded/attempts/t identiques). Sinon STOP.
- **G-POLICY** : cellule 1 POLICY == 87.01 (repro déterministe) ; cellule 2 POLICY Δp == +0.65
  (repro suspend study). Sinon diagnostic avant d'interpréter SWING.
- **G-SWING** : cellule 1 SWING == 71.4 ± 0.5 (repro RECOST). Sinon diagnostic.
- **G-breach** : au replay (§7), low-check + gateOFF reproduit les 2 busts réels 02-03/07 ; gateON les
  évite (J1=0). Sinon la couche low-check est invalidée.

## 7. Volet 5 — Extension & flash replay (secondaire, non-bloquant)
- Fetch Dukascopy M1 4 legs 2026-06-06→07-06 (réutilise le pattern j1 : tick→M1, scale /1e3, UTC).
  Si flaky après 2-3 essais → fallback data flash USDJPY déjà fetchée (j1 studies).
- **Replay** : rejouer l'état book compte-3 à travers 07-02/03, close-check vs low-check, gate ON vs
  OFF. Attendu : low-check+OFF ⇒ bust (reproduit les breachs) ; gate ON ⇒ survit. Démontre que le gate
  neutralise le tail J1 EN zone ; identifie le tail RÉSIDUEL (nightly/or hors J1).

## 8. Livrable & règles de reporting
- Triplet compte-3 (cellule 4 SWING) : p(pass) / attempts (dist) / temps (médian tentative + total
  espéré) + p(funded) + EV.
- **Décomposition** : Δp_gate seul (cellule 2−1), Δp_lowcheck seul (cellule 3−1), combiné (4−1). « De
  combien l'optimisme se corrige » = |cellule 4 − 71.4| décomposé.
- **Risque résiduel par sleeve** : attribution des busts low-check (jpy/gold/on_us/on_ger) sous gate ON
  → quel sleeve porte le tail intra-barre non couvert.
- **vm14** : SIGNALER si le low-check déplace l'optimum de sizing (comparer EV vs vm voisins) ; NE PAS
  trancher (chantier séparé).
- Distinguer DONNÉE (rétrospectif MC) vs JUGEMENT (tail hors-modèle, prospectif).

## 9. Caveats GELÉS (déclarés d'avance)
1. Low-check DISCRET : flash sous-M1 rare (non modélisé).
2. Low-check **surestime la perte** (liq FTMO ≈ floor, pas le low) → détecte le bust correctement, pas
   la perte exacte ; pour p(pass) seul le bust/no-bust compte.
3. Simultanéité 4-legs = conservateur (borne haute) ; bracketé par dominant-leg (§5).
4. tz Duka↔MT5 : ICI non-problème (median|Δ|=0, même source) — mais niveaux absolus low-check restent
   « indicatifs », le **Δ** est la grandeur robuste.
5. Gate : gèle sur close T-1 (reproductible, matché backtest) ; le live lit USDJPY à 21:50.
6. Extension : n'ajoute pas de cohorte complétable (§3) ; le flash est décision-pertinent via replay,
   pas via p(pass).

## 10. Ordre d'exécution
V0 (fait, gelé) → build+valid panel (G-tz) → lowcheck_engine (G-EQUIV) → run 2×2×marge (G-POLICY,
G-SWING) → agrégation triplet+déltas → replay (G-breach) → résidu sleeve + vm14 flag → self-verify →
audit indépendant → REPORT + mémoire.
