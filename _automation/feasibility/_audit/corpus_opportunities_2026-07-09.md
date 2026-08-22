# Corpus Opportunities Map — 2026-07-09

**Nature**: audit lecture-seule du corpus (routines alpha_hunt + feasibility + stratégies
existantes + travaux FTMO/propfirm). **Aucun backtest lancé, rien gravé.** Objectif : une
carte routée par usage, avec un **flag de fiabilité sur chaque source**.

## Préambule — pourquoi un verdict de rapport n'est PAS une vérité (4 caveats)
1. **77 faux FAIL_A purgés** (bug données vides, PR #387). Tout FAIL_A/verdict Level-A
   antérieur au 2026-07-09 peut être faux.
2. **Loader univers-7** jusqu'au 2026-07-09 : tous les verdicts crypto pré-fix sont sur un
   univers amputé (baseline 0.666 sur 7 vs 0.7635 sur 14) → **non-fiables pour go/no-go**.
3. **n_tests=321 non réconcilié** → aucun DSR historique n'est gravé.
4. **⚠ Caveat que j'ajoute (structurel)** : le `GenericHandler` de feasibility teste chaque
   idée scrapée contre une **baseline générique 28j TSMOM crypto**, PAS contre son vrai
   mécanisme (il l'écrit lui-même : « Specific hypothesis variant not implemented »). Donc
   la **majorité des ~150 verdicts feasibility ne testent pas l'hypothèse réelle** — ils
   mesurent juste si un momentum générique marche sur crypto. Re-tester les 77 purgés sur
   univers-14 **ne teste toujours pas leur mécanisme** → valeur d'information quasi-nulle
   sans handler dédié. C'est le point le plus important de cet audit.

---

## PHASE 1 — Inventaire par source (sans jugement)

### (a) Stratégies existantes A/B/C/D — statut réel
| Strat | Statut réel (CLAUDE.md + memory) | Chiffre affiché | Fiabilité du chiffre |
|---|---|---|---|
| **A** TSMOM crypto | **FROZEN** (Propr breach 2026-05-11) ; HL testnet daily place encore des fills | SR 1.33 OOS, MaxDD −6.9% | ⚠ suspect — 3 actifs, source docstring, results.json formel INTROUVABLE |
| **B** Delta-neutral carry | HL **testnet LIVE** depuis 2026-05-17 ; mainnet ~2026-07-17 | SR 4.10 backtest / 2.0 proxy | ⚠ testnet **inadmissible L14** (N<250) ; funding testnet artificiel |
| **C** NQ opening momentum | **ANNULÉ** (Tradeify annulé 06-10, FTMO ne prend pas CME) | re-baseline SR 0.41 ($29 RT) | fiable-mais-mort : sous gate, pas de véhicule |
| **D** D3+D5 NQ intraday | **pré-reg**, budget 3 mods 0 consommé | sleeves solo SR −1.08/−1.32 | fiable (échec solo mesuré) — portfolio+régime non testé |
| **FTMO live book** | **LIVE** (challenge/funded), breach <ACCOUNT_ID> le 2026-07-02 (flash USDJPY) | **p(pass) 69.7 %, EV +$678** | ✅ **le plus fiable du corpus** (sim calibrée sur le book live réel) |

### (b) REQUIRES_HUMAN en attente (137 dans l'index)
- **75 déjà triés** (`triage/REQUIRES_HUMAN_triage_2026-06-02.md`) : 72 % REJECT (méta/RSS/
  familles archivées), 23 % BACKLOG (data payante / classe hors-infra / parent FROZEN),
  5 % CANDIDATE (3 idées : C1 trailing-SL C, C2 HMM régime D, C3 FINRA→NQ overnight).
- **~62 accrus depuis** le triage : non re-triés individuellement, **même distribution**
  attendue (bruit méthodo majoritaire). Répartition catégories actuelle : REGIME_FILTER 68,
  COMPLEX 33, NON_TESTABLE 32, EXIT_RULE 4. Fiabilité : **REQUIRES_HUMAN = pas un verdict**,
  juste « le pipeline ne sait pas tester ça ».

### (c) promising/ non triées
- **421 fichiers** scrapés (arxiv q-fin, quantocracy, quantpedia, HN, github). Après triage,
  ~72 % sont du bruit reject. Fiabilité : **non-vérifié** (idées brutes).

### (d) Rapports FTMO / propfirm (autre session)
- `data/ftmo_portfolio/` : moteur first-passage MC + `trailing_dd_simulator` (L22/L24),
  audits v2 indépendants, attribution/timing, j1_suspend_study, v22, cache. **Fiable** (le
  corpus le plus rigoureux du repo — self-audité, memory ×20 fichiers).
- `PropFirms/{ftmo,apex,topstep,tradeify,mffu,phidias}/` : règles + programmes clos.
- `ftmo_live/` : EA MT5 déployé VPS, J1 gate LIVE, supervisor/reconcile/watchdog. **Live.**
- **decorrelated_sleeves_2026-07** (le plus récent, 2026-07-08) : 3 pistes (stat-arb / range /
  MR daily) **toutes FALSIFIÉES proprement** + correction bug swap-sign. ✅ **fiable** (post-fix,
  self-vérifié). → ne PAS re-proposer.

### (e) Ressources data fetchées → voir Phase 4.2.

---

## PHASE 2 — Tri par CONFIANCE (pas par performance)

### ÉTABLI (verdict fiable : live, post-fix, ou re-vérifiable immédiatement)
| Item | Verdict établi | Note |
|---|---|---|
| FTMO live book p(pass) 69.7 % / EV +$678 | **edge opérationnel réel** | seul « edge » live mesuré proprement ; c'est de la **gestion de risque**, pas une alpha neuve |
| decorrelated_sleeves 2026-07 (stat-arb/range/MR) | **FALSIFIÉS** ×3 | mécanismes nommés ; beta-trap / look-ahead / two-sided fail |
| **B1 FINRA→NQ overnight** | **FAIL Gate 4** | IC null (clean) / sous-seuil+survivorship (agrégat) ; **la thèse coût était juste** (NQ overnight swap-free monétiserait un vrai IC) mais le signal est absent → **CLÔT C3/P3 du triage** |
| Familles closes L11–L50 (crypto CS, FX intraday, commodity carry, fix-reversal, unlock-drift, funding-contrarian) | **fermées** | memory + POSTMORTEMs ; ne PAS re-vanter |
| Strategy A SR 1.33 | validé historiquement mais **FROZEN** + 3 actifs | pas actionnable tant que gelé |

### À-RE-TESTER (thèse plausible, verdict non-fiable OU incomplet)
| Item | Pourquoi non-fiable / incomplet | Ce qu'il faut |
|---|---|---|
| **Commodities XS basis+TSMOM** | Phase A **faite** (2026-05-23, 24 contrats 2005-26) mais **basis coverage 13 %** (proxy roll-gap sparse) ; leg TSMOM non backtesté | fetch front/second (`fetch_front_second.py`) pour vrai basis ; WF S_TSMOM sur continu |
| **Strategy D — D3+D5 + C2 HMM régime** | sleeves solo SR négatifs ; portfolio+régime **jamais testé** | protocole pré-reg P1 (triage) sur NQ |
| **ZN Baltussen** (bond momentum) | « en cours », verdict inconnu | finir le test ; caveat décroissance post-2015 rates |
| **sector_hothand_propfirm** | **t_HAC=10.38 = red flag** ; audit obligatoire | résoudre `_audit/sector_hothand_audit` avant tout |
| 77 faux FAIL_A purgés | verdict faux (données vides) MAIS **generic-handler ne teste pas le vrai mécanisme** | **valeur quasi-nulle** sans handler dédié — ne PAS prioriser en bloc |
| 12 FAIL_B + 2 SkipMonth FAIL_A (2026-05-24) | **pré-fix univers-7** ET tests generic-baseline | idem : re-test ≠ information tant que generic |

### SPÉCULATIF (idée brute, mécanisme non vérifié)
- ~62 REQUIRES_HUMAN non triés depuis 06-02 (bruit méthodo probable).
- `token_unlocks/`, `vrp_short_gamma/` : bootstraps **vides**.
- 421 promising/ en masse (~72 % reject-noise).

---

## PHASE 3 — Routage par usage

| Item (ÉTABLI/À-RE-TESTER crédible) | BOOK PERSO | PROPFIRM | INVEST LONG | AMÉLIO EXISTANT |
|---|:--:|:--:|:--:|:--:|
| **Strategy B mainnet** | ✅ seule alpha proche-live ; crypto delta-neutral hors-propfirm | — | — | — |
| **FTMO live risk-mgmt (J1/vm)** | — | ✅ protège p(pass) 69.7 % post-breach | — | ✅ overlay sur le book FTMO live |
| **Commodities XS TSMOM** | ✅ diversifie (orthogonal 100 % au crypto A+B) | ✗ mensuel = pas le profil propfirm (barrière symétrique) | ✅ **meilleur fit** : lent, low-turnover, coût négligeable | — |
| **Strategy D (D3+D5+HMM)** | ~ (NQ intraday perso possible) | ✅ décorrélé de C (mort) mais cible propfirm | ✗ | ✅ C2 = overlay régime sur D |
| **ZN Baltussen** | ✅ diversifie | ✗ (trend lumpy L24) | ✅ bond momentum mensuel | — |
| **A v4 mods (5 backlog)** | — | — | — | ✅ si A dégèle (L10 3-mod budget) |
| **B entry-criteria funding** | — | — | — | ✅ tuning du filtre carry de B |

**REJECT sans usage clair** : les 77 purgés + 12 FAIL_B + promising/ en masse (generic-handler
= pas de mécanisme testé) ; token_unlocks/vrp vides ; toutes familles L11-L50.

---

## PHASE 4 — Shortlist priorisée + ressources

### 4.1 TOP 5 (fiabilité × orthogonalité × faisabilité-infra × marge-coût) — p(succès) BRUTAL

**1. Strategy B — validation mainnet** · usage **BOOK PERSO**
→ Action : mesurer funding/swap **réels** sur 60 j live mainnet (~2026-07-17), comparer au
proxy SR 2.0. Effort : **faible** (déjà déployé testnet). Risque #1 : funding testnet
artificiel (L14) → l'edge peut s'effondrer en réel. **p ≈ 50 %.** *Ce n'est pas une alpha
neuve — c'est dé-risquer la chose la plus proche du live.* **Priorité #1 car ROI/effort max.**

**2. Commodities XS basis+TSMOM (leg TSMOM d'abord)** · usage **INVEST LONG + diversifier perso**
→ Action : `fetch_front_second.py` pour un vrai basis, puis WF S_TSMOM sur 24 continus
(univers propre, pas crypto → aucun impact du bug loader). Effort : **moyen**. Risque #1 :
régime post-2015 QE tue le XS commodités (documenté) ; leg basis data-faible (13 %).
**p ≈ 25 %.** Seul candidat vraiment orthogonal + coût-safe (L11 drag négligeable).

**3. FTMO live — gestion de risque (J1 gate / sizing vm)** · usage **PROPFIRM**
→ Action : surveiller l'efficacité du J1 suspension-gate post-breach 02/07 ; étudier vm0.85
(funded_anatomy : convertit 55/58 busts, Pareto +EV). Effort : **ops continu**. Risque #1 :
tail intra-barre ungateable (breach = flash 16.8× levier). **p(améliorer p(pass)) : modérée.**
*Capital-protection, pas alpha.* Priorité haute car protège un book LIVE.

**4. Strategy D — D3+D5 + overlay HMM régime (C2)** · usage **PROPFIRM / perso**
→ Action : protocole pré-reg P1 (HMM régime sur D3+D5, NQ). Effort : **3-4 j**. Risque #1 :
les deux sleeves sont SR négatifs en solo → portfolio+régime = **tentative de sauvetage**,
structurellement faible. **p ≈ 15 %.**

**5. ZN Baltussen — bond momentum** · usage **INVEST LONG**
→ Action : finir le test en cours (`Futures/research/active/zn_baltussen/`). Effort : inconnu
(en cours). Risque #1 : momentum obligataire décayé post-2015 (régime taux). **p ≈ 20 %.**

> **Honnêteté globale** : aucune de ces 5 n'est une alpha neuve à forte conviction. La vraie
> valeur du corpus est (a) les **systèmes LIVE** (A gelé, B mainnet-imminent, FTMO book) qui
> demandent de l'**attention opérationnelle**, pas de la recherche ; (b) 2-3 angles orthogonaux
> non-testés (commodités, D) à **p modeste**. Le corpus d'idées scrapées (promising/ +
> feasibility) a une alpha extractible **quasi-nulle** car le generic-handler n'a jamais testé
> les vrais mécanismes. La plupart ne mèneront à rien — c'est normal et attendu.

### 4.2 Ressources réutilisables (déjà fetchées)
| Ressource | Contenu | Permet |
|---|---|---|
| `data/deep_history_utc/` | M1 **true-UTC** FX majors + indices + commodités, 2007-2026, spread calibré, trous réparés, MANIFEST | tout intraday/daily FX/indices/commo, seams validés |
| `data/raw/NQ_1min_databento_2010-2026.parquet` (+ Kaggle) | NQ 1-min canonique | Strategy C/D, ORB, overnight NQ |
| `_automation/feasibility/data/cache/strategy_a_universe.parquet` | **NEW** crypto daily 14 actifs 2018-2026 (cache fixé) | baseline crypto propre, feasibility pipeline |
| `data/funding_carry/` + `data/delta_neutral/` | HL 8h funding + Binance spot | Strategy B, carry crypto |
| `data/ftmo_portfolio/` + `Portfolio/risk/trailing_dd_simulator.py` | moteur first-passage MC + sim p(pass) (L22/L24) + caches | toute éval propfirm (avant achat challenge) |
| `PropFirms/ftmo/program_2026-06/b1_feasibility/` | FINRA short-vol universe.parquet + `fetch_finra.py` + IC test | (signal FAIL, mais **infra FINRA réutilisable**) |
| `Commodities/research/active/xs_basis_tsmom/` | 24 continus 2005-26 + `fetch_front_second.py` + roll detection | commodités XS (leg TSMOM prêt, basis à compléter) |
| Downloaders | `dukascopy_downloader_m5.py`, `binance_klines_downloader.py`, `vrp/code/fetch_dvol.py` (Deribit), `fetch_continuous.py` | FX M5 / crypto klines / vol implicite / commo continu |
| `data/deep_history_m1/calendar` + `fomc_events.csv` (2004-2026) | calendriers macro | études event-driven (FOMC, ToM) |

---
*Audit lecture-seule, 2026-07-09. Rien gravé dans CLAUDE.md ; n_tests/_state/_index intouchés.*
