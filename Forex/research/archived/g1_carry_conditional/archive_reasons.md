# Archive — G1 Carry G10 conditionnel par régime macro

**Date archive :** 2026-05-26
**Status :** ARCHIVED — ne pas re-proposer sans evidence forte nouvelle
**Verdict audit :** REVISE → ARCHIVE confirmé
**Décision :** unilatérale post-audit constitutionnel, pas de validation empirique requise

---

## Hypothèse testée

Carry G10 (7 paires vs USD, long top-3 / short bottom-3, vol-target 10%, rebalance mensuel)
conditionné par régime macro : filtre VXY-proxy (vol réalisée 21j, pondérations BIS) < médiane
rolling 24M ET/OU pause carry sur fenêtre FOMC ±5j si |Bauer-Swanson orthogonalized surprise|
> 1.5σ. Exécution retail via Dukascopy ECN ou OANDA, horizon weekly à monthly, personal book
$25k et/ou propfirm Swing (FTMO/FundedNext). Verdict rapport v1 : NON viable net de coûts.

---

## Kill analytique principal (F1 — gate Israel-Jiang-Ross 2017)

Au scénario LE PLUS FAVORABLE possible (Dupuy 2021 G10 vol-conditioned meilleure spécification,
coûts Dukascopy ECN best case, swap asymmetry lower bound) :

```
Gross alpha = Sharpe_gross_optimal × σ_target
            = 0.53 × 10%
            = 530 bps/an

Cost drag minimal (Dukascopy ECN, best case) :
  80 bps  (spread, rotation mensuelle 6 paires G10)
+ 100 bps (swap broker asymmetry, lower bound OANDA février 2026)
= 180 bps/an

Gate Methodology Toolkit (CLAUDE.md) : gross_alpha > 3 × cost_drag
  530 bps > 3 × 180 = 540 bps ?
  530 < 540  →  FAIL  (ratio 0.98)
```

Scénarios moins favorables :
- OANDA spread-only + swap full asymmetry : cost drag ≈ 450-600 bps/an → ratio 0.53-0.88
- Sharpe gross réel post-2010 G10-only (non conditionnel) ≈ 0.25 → gross 250 bps → ratio 0.42

**Aucun scénario retail accessible ne passe le gate 3×.** Le ratio sub-1.0 dans le meilleur cas
signifie que même en l'absence de tout autre problème, la stratégie serait rejetée par le gate
constitutionnel avant tout backtest.

Note : le Sharpe gross 0.53 de Dupuy 2021 est lui-même qualifié "small, insignificant increase"
par l'auteur (base 0.45 → 0.53 non significatif). Le gate est calculé sur le meilleur chiffre
disponible ; il échoue.

---

## Deal-breakers procéduraux (audit constitutionnel)

### F9 — AMTP et n_tests global non provisionnés

n_tests global = 321 avant G1 (CLAUDE.md "Research history (n_tests = 321 global)"). Le protocole
3 étapes du rapport v1 consomme au minimum 4 sous-hypothèses (carry baseline + filtre VXY + filtre
Fed + combinaison). Hard rule CLAUDE.md : "Excess returns (vs cash rate), HAC lag-6, AMTP if
n_tests > 1." À n_tests = 321 + 4 = 325, le seuil Bonferroni α/325 ≈ 0.00015 → t critique ≈ 3.8,
très au-dessus du t_HAC observé pour carry G10 conditionnel (Dupuy 2021 : delta non significatif).
L'AMTP est absent du rapport v1 et du protocole proposé — violation de hard rule.

### F12 — Seuil t-stat sub-constitutionnel dans le protocole

Le protocole Step 2 du rapport v1 stipule "t-stat HAC > 1.96" comme critère pass. La constitution
(CLAUDE.md Methodology Toolkit) exige : "Significance: HAC Newey-West (lag-6) t-stat, threshold
t > 2.5 for IC feasibility." Utiliser 1.96 au lieu de 2.5 baise le bar d'exactement la zone où
les stratégies FX mortes peinent à passer (t_HAC G10 carry post-2010 ≈ 2.02 selon FX-1 README).
Tout protocole utilisant t > 1.96 sur un carry G10 est constitutionnellement invalide.

### F14 — Budget Lesson 10 : 3 modifications épuisé sur famille carry G10

Lesson 10 (CLAUDE.md Core) : "3 modifications maximum per strategy to avoid overfitting."
La famille G10 FX (listée CLAUDE.md Research History sous "G10 carry (FX-1 to FX-4)") a déjà
consommé 4 variantes :
- FX-1 : Carry FRED 3M G10, EW (base)
- FX-2 : CS Momentum 12M-1M G10 (mod 1 — signal différent)
- FX-3 : TSMOM tanh 12M G10 (mod 2 — scaling différent)
- FX-4 : Carry G10 + EM (mod 3 — univers étendu)

G1 carry conditionnel = 5e variation sur la famille G10 FX → dépasse le budget constitutionnel
de 3 modifications. Note : si FX-2/FX-3 sont comptés comme hypothèses indépendantes (momentum ≠
carry), alors seules FX-1 et FX-4 sont des modifications carry (2 mods consommées). Ambiguïté sur
la classification — mais per CLAUDE.md qui groupe FX-1 à FX-4 sous "G10 carry" comme une seule
entrée, la famille est épuisée. Trancher par prudence constitutionnelle : CLOSED.

---

## Standards constitutionnels invoqués

| Standard | Citation CLAUDE.md | Application |
|----------|-------------------|-------------|
| Lesson 10 | "3 modifications maximum per strategy to avoid overfitting." | Budget FX-1→FX-4 épuisé (F14) |
| Methodology Toolkit — IR gate | "IC → net Sharpe (Israel-Jiang-Ross 2017): expected_gross_alpha ≈ 0.40 × IC × √breadth × σ_target; require gross > 3×cost_drag." | Kill analytique F1 : ratio 0.98 au best case |
| Methodology Toolkit — HAC | "Significance: HAC Newey-West (lag-6) t-stat, threshold t > 2.5 for IC feasibility." | Protocole F12 : seuil 1.96 sub-constitutionnel |
| Hard rule | "Excess returns (vs cash rate), HAC lag-6, AMTP if n_tests > 1." | F9 : AMTP absent, n_tests non provisionné |
| Hard rule | "Walk-forward ≥5 folds — never single split." | F11 : WF absent du protocole proposé |
| RESEARCH_PASS | "Sharpe>0.7, MaxDD<-25%, WF>50%" | Sharpe net attendu 0.15-0.30 → sous le gate d'un facteur 2-5× |
| Research History | "CS momentum, TSMOM G10: dead post-Menkhoff (central bank anchoring)." | G2A (carry × momentum) invalide sans IC gate préalable |
| Research History | "BIS REER ≠ bilateral USD valuation: unsuitable as carry signal modifier." | G2B (valuation-adjusted) partiellement contrainte |

Note : L16 invoqué dans le template d'audit n'existe pas dans le registre constitutionnel
(CLAUDE.md saute de L15 à L17). Les findings "G10 momentum dead" et "BIS REER" sont bien présents
mais enregistrés sous Research History, pas comme L-lesson numérotée.

---

## Conditions pour reconsidération future

NE PAS re-proposer G1 sauf si TOUTES les conditions suivantes sont réunies simultanément :

1. **Access institutionnelle** : JPMaQS (Macrosynergy data) ou prime brokerage avec accès
   Bloomberg JPMVXYG7:US / EUBSC3 / JYBSC3, swap rates institutionnels ≤ 5 bps asymmetry.
2. **Coût d'exécution** : spread retail effondré à < 30 bps RT all-in panier G10 (Saxo Pro tier
   ou prime brokerage) — condition nécessaire pour que le ratio gross/3×cost dépasse 1.0.
3. **Proxy non-endogène au crash carry** : VXY est endogène par construction (unwind carry
   CAUSE le spike vol). Proxy alternatif requis : credit spread HY-IG, JPY-implied vol leadership,
   CFTC positioning (COT report), 3M-OIS basis (FRED H.15). Aucun disponible retail avec
   qualité suffisante en 2026.
4. **Sharpe gross G10-only conditionnel > 0.70** : documenté sur paper post-2018 avec t_HAC > 2.5
   sur données propres (pas extrapolé depuis Dupuy 2021 sur 1999-2018).
5. **Ouverture budget** : nouvelles hypothèses FX uniquement si budget Lesson 10 re-ouvert
   explicitement (ex. résolution de l'ambiguïté FX-2/FX-3 comme hypothèses indépendantes).

---

## Pivots issus de l'audit

### G2A — Carry × Momentum hybride AMP 2013 [conditionnellement valide]

Signal composite = 0.5 × rank(carry forward-implied) + 0.5 × rank(12-1 momentum spot), G10 8
devises, vol-target 10%, rebalance mensuel.
**Gate IC obligatoire avant tout développement** : tester IC(12-1 momentum spot, G10, 2010-2025)
avec HAC t > 2.5. Research History dit "CS momentum, TSMOM G10: dead post-Menkhoff" — si confirmé
(IC ≈ 0 ou wrong direction), G2A invalide, kill. Probabilité d'échec au gate IC estimée ~70%.
Sharpe net retail estimé si gate passé : 0.35-0.55 (Asness-Moskowitz-Pedersen 2013 cross-asset
argument, non encore instrumenté G10 FX post-2010).

### G2B — Carry valuation-adjusted Macrosynergy [dépriorisé]

Ajustement carry par gap PPP/REER via OECD REER monthly (gratuit). Sharpe gross Macrosynergy
0.67-0.78 sur 24 devises (dont ~6-8 EM). Dégradation G10-only non quantifiée mais estimée
−20-40% → Sharpe net retail G10-only ≈ 0.18-0.36, probablement sous RESEARCH_PASS (0.7).
À déprioriser vs G2A. Accès JPMaQS requis pour répliquer fidèlement le signal Macrosynergy.

### G2D — Carry cross-asset Koijen-Moskowitz-Pedersen-Vrugt 2018 [émergent, non instrumenté]

Carry across asset classes (equity index futures, bonds, commodities, FX), Sharpe in-sample
~1.2 (Koijen et al. 2018 *Journal of Financial Economics*). Robuste par diversification des
sources de risk premium là où carry FX pur est mort. Infrastructure Tradovate (Strategy C déjà
live) + spot FX IBKR. Brief recherche dédié à produire.

---

## Liens

- Rapport v1 : `report_v1.md` (snapshot immutable)
- Audit v1 : `audit_v1.md` (snapshot immutable)
- FX-1→FX-4 archived : `Forex/research/archived/fx_carry_fred/`, `fx_momentum_monthly/`, `fx_carry_em/`
- Strategy E (architecture similaire : closé à literature stage) : `Forex/research/archived/strategy_e_fix_flow/POSTMORTEM.md`
