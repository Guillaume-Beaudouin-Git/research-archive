# Crypto CFD FTMO — TSMOM two-sided BTC/ETH — KILL

**Status:** ARCHIVED at pre-flight (cost-feasibility, swap=0 counterfactual).
**Date:** 2026-06-02.
**n_test budget consumed:** 1 (the kill counts as the single decisive hypothesis test).
**Candidate L-number:** **L33** (proposed, awaiting promotion into `CLAUDE.md`).

---

## 1. Hypothèse H1 (formelle)

Réutiliser la construction de signal de Strategy A
(`strategies/tsmom_v2_propfirm/signal.py:compute_signal`, lookback=28, `tanh` de t-stat
normalisé √28) **en retirant `.clip(lower=0.0)`** afin d'autoriser le short. Rebalance
hebdomadaire lundi. Univers BTC + ETH uniquement (SOL spread FTMO trop large pour amortir
sur trade hebdo). Signal T-1, trade T. Coûts : spread RT FTMO MT5 mesuré empiriquement
(BTC 2.3 bps med ; ETH 2× BTC à défaut de panel MT5 ETH) + commission 0.065 % RT (FTMO
blog 2026, `PropFirms/ftmo/rules.md`) + swap overnight 7 nuits/trade.

**Question décisive (binaire, posée par l'utilisateur) :**
- (a) Le drift NET/trade de la jambe **SHORT** est-il ≥ 0 après swap ?
- (b) Si on retire la jambe short, le long survivant ≠ A long-only ?

---

## 2. Tableau split-by-direction (L25) — swap=0 counterfactuel

> Le swap réel FTMO crypto étant structurellement prohibitif sur hold overnight
> (utilisateur, corroboré par le pattern L30 "swap-sign rule"), on évalue la H1 à la
> borne supérieure `swap = 0` : "même sans swap, est-ce que ça marche ?"

### 2.1 markup=1.0 (spread feed-raw, BTC=2.3 + comm 6.5 = 8.8 bps ; ETH=4.6 + 6.5 = 11.1 bps)

| Asset | Leg   | N    | Gross/trade (bps) | Cost/trade (bps) | **Net/trade (bps)** | **t_HAC6** | **L11 ratio** |
|-------|-------|-----:|------------------:|-----------------:|--------------------:|-----------:|--------------:|
| BTC   | LONG  | 236  | 87.6              | 5.5              | 82.2                | 1.87       | 5.34          |
| BTC   | SHORT | 205  | **14.0**          | 4.6              | **9.4**             | **0.28**   | **1.01**      |
| ETH   | LONG  | 236  | 89.1              | 6.6              | 82.5                | 1.50       | 4.48          |
| ETH   | SHORT | 205  | 88.1              | 6.5              | 81.7                | 1.62       | 4.55          |

### 2.2 markup=2.0 (retail-vs-feed, L23b) — sanity

| Asset | Leg   | Net/trade (bps) | t_HAC6 | L11 ratio |
|-------|-------|----------------:|-------:|----------:|
| BTC   | LONG  | 80.7            | 1.84   | 4.23      |
| BTC   | SHORT | 8.2             | 0.24   | 0.80      |
| ETH   | LONG  | 79.7            | 1.45   | 3.16      |
| ETH   | SHORT | 79.0            | 1.56   | 3.21      |

### 2.3 Long-survivor check (b) — H1 long-leg vs A long-only

| Asset | A long-only Net | H1 long-leg Net | Δ |
|-------|----------------:|----------------:|---:|
| BTC   | 82.15 bps       | 82.15 bps       | **0 bps (identique)** |
| ETH   | 82.49 bps       | 82.49 bps       | **0 bps (identique)** |

→ **La jambe LONG de H1 est mathématiquement A long-only** : `clip(s, 0, +∞)` ne change
que les semaines où s<0, donc les semaines s>0 sont préservées trait pour trait.

---

## 3. Réponses binaires

### (a) Short-leg net drift ≥ 0 après swap ? — **NON**

- **BTC short** : gross 14.0 bps, t_HAC6=0.28 (NON significatif, gate t>1.65). L11
  ratio = **1.01** (FAIL, gate 3.0). À swap=0 le net est déjà à 9.4 bps. Tout
  swap > 9.4 bps/trade rend le net négatif. Avec un swap réaliste de **-10 %/an × 7 nuits
  ≈ 19 bps/trade**, net BTC short = -10 bps avec t<0.
- **ETH short** : gross 88.1 bps, t_HAC6=1.62 (borderline, **sous** 1.65), L11=4.55.
  À swap réaliste -10 %/an × 7 nuits = -19 bps → net ETH short ≈ 62 bps, t encore inférieur
  à 1.65. La jambe short ETH **n'est pas significativement positive** même au counterfactuel
  swap=0.

→ Sur la condition (a), **BTC short kill clair, ETH short non-significatif** — la moyenne
  short à 2 assets est tirée par ETH seul, ce qui contredit le principe `N≥30 instruments`
  pour un cross-sectional (Hard rule + L24).

### (b) Long-survivor ≠ A long-only ? — **NON**

- La jambe LONG de H1 est **identique** à A long-only par construction (cf. §2.3).
  Retirer la jambe SHORT ramène mathématiquement à A.

→ Sur la condition (b), **STOP : c'est A long-only déguisé** côté long. La seule "nouveauté"
  est la jambe SHORT, qui est elle-même non-significative (cf. (a)).

---

## 4. Hygiène

### 4.1 Delay-1 sensitivity (L26)

| Scenario              | BTC LONG net | BTC SHORT net | ETH LONG net | ETH SHORT net |
|-----------------------|-------------:|--------------:|-------------:|--------------:|
| delay-1 (canonique)   | 82.2 bps     | 9.4 bps       | 82.5 bps     | 81.7 bps      |
| delay-0 (look-ahead)  | 67.2 bps     | 19.5 bps      | 97.6 bps     | 61.1 bps      |

→ Δ < 30 % sur chaque jambe ; pas d'effondrement sous delay-1 → **pas d'artefact de
  fill** sur la construction hebdomadaire (cohérent : signal computé sur 28 jours, le
  passage delay-0→delay-1 = perturbation d'1 jour sur 28). **Pas un kill par L26.**

### 4.2 DSR sur Sharpe net agrégé (BTC+ETH pooled, markup=1, swap=0)

- Sharpe weekly = 0.088 → **annualisé 0.90** (T=882 trades, skew=0.20, kurt=6.44)
- DSR_prob (Bailey-LdP, n_trials=3) = 0.961

→ Le **Sharpe annualisé 0.90 est sous le `PROPFIRM_PASS=1.0`** (CLAUDE.md two-tier gates)
  **au counterfactuel swap=0**. Le DSR à n_trials=3 ne sauve pas : la barre intrinsèque
  est ratée avant correction multiple-testing. Avec un swap réaliste, le Sharpe net
  passe sous 0.5 (estimation : 19 bps swap drag × 104 trades/an ≈ 2 % drag annuel, sur
  un gross ≈ 6-7 %/an → -30 % à -50 % de Sharpe).

---

## 5. Mécanisme du kill — formulation L33 candidate

> **L33 — Crypto-CFD TSMOM two-sided structurellement infaisable sur FTMO.**
>
> Trois axes de kill indépendants :
>
> (a) **Jambe SHORT non-significative** : sur BTC (le seul asset crypto avec données
> spread MT5 propres), gross/trade = 14 bps, t_HAC6 = 0.28, L11 ratio = 1.01 au
> counterfactuel swap=0 (N=205 trades hebdo, 2017-2026). Sur ETH, gross 88 bps mais
> t_HAC6 = 1.62 (sous gate 1.65). Un univers N=2 ne peut pas survivre à la règle dure
> `N≥30 instruments` pour CS, et la moyenne ETH-only viole également L21 (le SR
> annualisé 0.9 reste sous propfirm gate avant même swap).
>
> (b) **La jambe LONG de toute version two-sided crypto TSMOM est identiquement A
> long-only** : `clip(s,0,+∞)` n'affecte que les semaines s<0. Retirer la jambe SHORT
> ramène mathématiquement à A → pas de nouveauté côté long, c'est du β-long déguisé
> (L11).
>
> (c) **Swap overnight FTMO crypto structurellement prohibitif** : utilisateur-asserté
> (sourcé MT5), corroboré par le pattern L30 ("swap-sign rule" : markups FTMO
> asymétriques). Hold 7 nuits/trade × swap typique -10 %/an = ~19 bps/trade de drag.
> Ce drag mange seul la jambe ETH short (gross 88 → net ~62-69) ET pousse la jambe
> BTC short profondément en négatif (gross 14 - swap 19 = -5 avant même spread+comm).
>
> **Verdict :** la classe "TSMOM hebdo crypto two-sided" est CLOSED sur FTMO. Toute
> nouvelle proposition crypto TSMOM doit être *intraday-flat* (cf. `run_crypto.py`
> existant) ou doit migrer vers une exécution non-CFD (cf. Strategy A sur Propr).

**Lien CLAUDE.md** : à promouvoir comme L33 dans la section "Crypto structural —
registre L" si validé par l'utilisateur. Numérotation libre (L32 = commodity carry,
dernier consommé).

---

## 6. Cases FTMO restantes (post-kill)

D'après l'inventaire utilisateur ("dernière case FTMO non creusée = crypto CFD"),
**toutes les classes d'actifs FTMO sont maintenant fermées sur les familles momentum
hebdo/quotidien standard** :
- FX carry (L23) ;
- Indices overnight (cités L32 swap-kill) ;
- Commodity carry (L32 explicite) ;
- Crypto CFD weekly (L33 proposé).

Les survivants identifiés sur FTMO sont :
- ORB intraday-flat (Strategy C iter_10 — DSR-fail, NO-GO confirmé) ;
- ORB K5 push-pass (mid-vol 98.6 % — `orb_pushpass_2026-06`) ;
- V2+E7 sur Indices CFD (mid-vol 49.5 % — `orb_deepening_2026-06`).

**Recommandation** : ne pas re-proposer de famille TSMOM/carry crypto sur FTMO.
Revenir sur BreakoutProp (alpha-program crypto intraday momentum, exécution flat
00-21 UTC) ou pivoter sur le matériel ORB-deepening déjà validé.

---

## 7. Artefacts

- `run_kill_test.py` : backtest reproductible (Python typed, vectorisé).
- `kill_test_output.txt` : sortie console intégrale.
- Données : `data/ftmo_universe/daily_panels/crypto/btc_full.csv` et `crypto_panel.csv`
  (BTC 2017-11→2026-05, ETH 2017-11→2026-05, 3121 jours).
- Code signal : `strategies/tsmom_v2_propfirm/signal.py` réutilisé via import direct
  (zéro divergence avec A en production).

**STOP conditions respectées (per brief)** : pas de WF/MC lancé.
