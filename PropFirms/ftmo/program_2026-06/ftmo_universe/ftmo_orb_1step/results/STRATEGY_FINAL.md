# STRATÉGIE FINALE — ORB Nasdaq + sizing optimal (vraies règles FTMO)

Document maître **corrigé** après vérification des règles FTMO réelles (2026). Une version
antérieure modélisait le 1-step avec les règles du 2-step (erreur) — les chiffres ci-dessous sont
les bons.

> **CONTRAINTE : 1 SEUL ESSAI.** Sous les vraies règles, **aucune config ne passe >50 % en <2 mois.**
> Le meilleur véhicule single-attempt est le **2-step** (pas le 1-step) : **44 %** (book, régime
> récent) / **30 %** (full-history robuste) en <2 mois, **52 %** à <3 mois pour le book.

---

## 0. Les vraies règles FTMO (vérifiées, sources en bas)
| | **2-Step Challenge** | **1-Step Challenge** (lancé fév. 2026) |
|---|---|---|
| Cible profit | +10 % (P1) puis +5 % (P2) | +10 % |
| **Max daily loss** | **5 %** de l'initial (fixe) | **3 %** de l'initial (recalc. chaque jour) |
| **Max loss total** | **10 % STATIQUE** (floor $9 000) | **10 % TRAILING end-of-day** (floor = plus-haut-EOD − $1 000, ne baisse jamais) |
| Best Day Rule | non | **oui** : aucun jour > 50 % du profit total |
| Limite de temps | non (min 4 jours/phase) | non (min 4 jours) |

→ Les 3 contraintes du 1-step sont **plus serrées** → il est **plus dur** que le 2-step.

## 1. p(pass) — essai unique, Monte-Carlo block-bootstrap, fills réalistes, sizing honnête fixe
| | 2-step <2mo | 2-step <3mo | 1-step <2mo | 1-step <3mo |
|---|---:|---:|---:|---:|
| **Nasdaq full 16y (robuste)** | **30 %** (bust 42 %) | 39 % | 23 % (bust 28 %) | 33 % |
| **US100+GER40 book (régime 2022+)** | **44 %** (bust 49 %) | **52 %** | 29 % (bust 23 %) | 41 % |

**Aucun >50 % en <2 mois.** Le 2-step book frôle 50 % seulement à 3 mois (52 %).

## 2. Pourquoi le 1-step est plus dur (et pénalise CETTE stratégie)
1. **3 % daily** (vs 5 %) → cap de sizing ρ ≤ ~1,4 % (book) / 2,7 % (single) au lieu de 4,5 % → plus lent.
2. **Floor trailing** (vs statique) → l'avantage « la distance au floor grandit quand on gagne »
   (cœur du sizing DP) **disparaît** : le floor suit l'équité 1 000 $ en dessous du plus-haut EOD.
3. **Best Day Rule (50 %)** → coûte **~−13 pp** à elle seule, parce qu'elle **pénalise le skew**
   (+1,2 à +2,0) qui était l'atout de l'ORB. Sous cette règle, le profil idéal est **lisse et
   consistant** (beaucoup de petits gains), pas à grosses journées. *Reframe important pour la suite.*

## 3. La stratégie (règles actionnables — inchangé)
Nasdaq-100 (US100.cash), variante book + GER40.cash. **ORB long-only** : range d'ouverture 30 min
(09:30–10:00 ET), entrée sur cassure de l'OR-high après 10:00 **si** prix fin-d'OR > clôture veille,
stop OR-low (−1R), trailing breakeven après +1R sinon clôture RTH, **flat overnight**. Largeur OR
≥ 8 bps. ~40 % des jours tradés. Sizing fixe honnête (ρ selon le challenge & la limite daily).

## 4. Métriques du signal (inchangées — indépendantes des règles)
| | Nasdaq full 16y | book |
|---|---:|---:|
| Trades/an · hit · skew | ~100 · 49 % · +1,23 | ~155 · 42 % · +1,98 |
| Sharpe quot. (ann) · Sortino | 0,77 · 1,12 | 1,21 · 2,55 |
| Pire jour réalisé | −3,9 % | −4,3 % |

## 5. Ce qui a été testé et rejeté (rigueur)
MR/momentum (−EV) ; diversification equal-risk (dilue ; seul GER40 +EV décorrélé) ; ML walk-forward
(Sharpe 0,68, leak attrapé) ; HMM/macro-VIX (régime réel mais gating ralentit le timed) ; event/news
(pire les jours high-impact) ; cross-sectional indices (Sharpe +0,03) ; crypto BTC (−EV). **Edge
unique = beta long intraday ; contrainte = caps daily + barrières.**

## 6. Verdict honnête
- **Aucun single-attempt ne passe >50 % en <2 mois** sous les vraies règles. Meilleur = **2-step book
  44 %** (régime) / **30 %** (robuste). Le 2-step > 1-step (mes « 53-64 % 1-step » étaient faux).
- **Beta long**, pas d'alpha ; le 44 % est régime-récent, le **30 % full-history est la borne robuste**.
- Améliorer sans overfit → viser un signal **lisse +EV** (bon pour 1-step/best-day) ou monter le
  Sharpe — leviers épuisés dans cet univers liquide gratuit.

Sources règles : ftmo.com/en/blog/introducing-the-1-step-ftmo-challenge, ftmo.com/en/2-step-challenge,
ftmo.com/en/trading-objectives. Code : `dp_sizing.py` (2-step DP), `ftmo_1step_real.py` (1-step réel),
`engine.py`, `live_signals.py`.
