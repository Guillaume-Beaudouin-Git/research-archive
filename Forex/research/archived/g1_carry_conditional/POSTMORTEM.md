# POSTMORTEM — G1 Carry G10 conditionnel par régime macro

**Date archived:** 2026-05-26
**Status:** ARCHIVED — ne pas re-proposer sans evidence forte nouvelle
**Stage reached:** Literature scan + audit constitutionnel. Aucun backtest exécuté.
**n_tests consommés:** 0 (tué à l'audit, avant tout IC test ou backtest)
**Decision:** Unilatérale post-audit constitutionnel — verdict analytique, pas validation empirique requise.

---

## 1. Verdict final

G1 rejeté sur la base du gate analytique 3× (Israel-Jiang-Ross 2017) et de trois deal-breakers
procéduraux identifiés lors de l'audit constitutionnel. Le verdict du rapport v1 (tuer G1) résiste
à l'audit sans modification. Plusieurs lignes de preuve indépendantes convergent vers
l'impossibilité retail 2026 — la conclusion n'est pas fragile.

Hypothèse : **carry G10 conditionné par régime de volatilité macro** (filtre VXY proxy < médiane
rolling 24M et/ou pause carry FOMC ±5j), 7 paires vs USD, long top-3 / short bottom-3,
vol-target 10%, rebalance mensuel, Dukascopy ECN ou OANDA.

Verdict : **NON viable net de coûts**. Kill au premier gate analytique (L11 / 3× gate) et
trois deal-breakers procéduraux non réparables avant toute exécution du protocole.

---

## 2. Deal-breakers — verbatim audit_v1.md

### F9 — AMTP + n_tests budget absents [Deal-breaker]

> AMTP + n_tests budget absents — constitution : "Excess returns, HAC lag-6, AMTP if n_tests > 1"
> (hard rule). Le protocole 3 étapes du rapport v1 consomme au minimum 4 sous-hypothèses
> (carry baseline + filtre VXY + filtre Fed + combinaison). n_tests global = 321 → 325+.
> La constitution exige AMTP à partir de n_tests > 1. Le protocole ne mentionne ni n_tests
> ni p-value AMTP corrigée. Pour n_tests = 4 (Bonferroni simple), le seuil α effectif par
> test = 0.05/4 = 0.0125 → t critique ≈ 2.50. L'absence totale de discussion AMTP est une
> violation formelle.
>
> — audit_v1.md, table sévérité + section Recommendations

### F12 — Seuil HAC 1.96 vs constitution 2.5 [Deal-breaker]

> Seuil HAC 1.96 vs constitution 2.5 — Protocol Step 2 utilise t > 1.96 ; constitution
> (CLAUDE.md Methodology Toolkit) fixe t > 2.5 pour IC feasibility. Un résultat qui passe
> 1.96 mais échoue 2.5 serait archivé selon les standards constitutionnels. Pour n_tests > 1,
> AMTP élève encore le seuil effectif. Le protocole est sous-exigeant sur le critère critique
> de significativité.
>
> — audit_v1.md, table sévérité + section "Fragilités additionnelles F12"

### F3b — Budget FX-1→FX-4 + 3-mod limit non vérifié [Deal-breaker]

> Budget FX-1→FX-4 + 3-mod limit non vérifié — FX-1→FX-4 déjà dépensé sur carry G10
> (research history) ; le limit de 3 modifications par hypothèse n'est pas vérifié avant G1.
> Action requise : vérifier avant toute ouverture G1.
>
> — audit_v1.md, table sévérité

### F14 — FX n_tests budget et 3-mod limit non audités [Deal-breaker]

> FX n_tests budget et 3-mod limit non audités — Constitution : "Max 3 modifications per
> strategy hypothesis." Research history : "G10 carry (FX-1 to FX-4): dead post-GFC."
>
> Les stratégies FX-1 à FX-4 ont consommé 4 tests sur la famille carry G10. Selon
> l'hypothèse que FX-1 = carry inconditionnel de base, les modifications FX-2, FX-3, FX-4
> représentent déjà 3 modifications. G1 (carry conditionnel) serait une **4ème modification**,
> au-delà du budget constitutionnel de 3.
>
> Ce point n'est ni adressé ni même mentionné dans le rapport. Si FX-1→FX-4 sont des
> hypothèses indépendantes (pas des modifications de la même hypothèse), le budget est intact.
> Mais si FX-1 = plain carry et FX-2/FX-3/FX-4 = variations du carry, le budget est épuisé.
>
> — audit_v1.md, section "Fragilités additionnelles F14"

**Note F3b/F14 :** ces deux entrées décrivent le même enjeu constitutionnel (budget Lesson 10
sur la famille carry G10) sous deux angles — F3b identifie le risque dans la table générale,
F14 l'instrumente et conclut que G1 serait la 4ème modification si FX-2/FX-3 sont comptées
comme modifications du carry. Les deux sont reproduits verbatim car ils apparaissent
séparément dans audit_v1.md.

---

## 3. Magnitude vs coûts (gate analytique décisif)

**Gate Methodology Toolkit : gross_alpha > 3 × cost_drag.**

Au scénario le plus favorable possible (Dupuy 2021 G10 vol-conditioned, coûts Dukascopy ECN
best case, swap asymmetry lower bound) :

```
gross_alpha = SR_gross_optimal × σ_target
            = 0.53 × 10%
            = 530 bps/an

cost_drag = 180-320 bps/an
  80 bps  (spread, rotation mensuelle 6 paires G10, Dukascopy)
+100 bps  (swap broker asymmetry, lower bound OANDA fév. 2026)
= 180 bps/an (best case)

3 × cost_drag = 540-960 bps/an
ratio = 530/540 à 530/960 = 0.98 à 0.55
Gate 3× : FAIL dans tous les cas (sous 1.0 même pour coûts minimaux)
```

— audit_v1.md, section "Key Finding 5", lignes verbatim

Scénarios moins favorables :
- OANDA spread-only + swap asymmetry full : cost drag ≈ 450-600 bps → ratio 0.53-0.88
- Sharpe gross réel G10-only post-2010 non conditionnel ≈ 0.25 → gross 250 bps → ratio 0.42

**Aucun scénario retail accessible ne passe le gate 3×.**

Note additionnel : le Sharpe gross 0.53 de Dupuy 2021 est lui-même qualifié "small, insignificant
increase" par l'auteur (baseline 0.45 → 0.53 non significatif). Le gate est calculé sur le
meilleur chiffre disponible — il échoue.

---

## 4. Références académiques décisives

| Référence | Finding décisif |
|-----------|----------------|
| Accominotti, Cen, Chambers & Marsh (2021, *IRFA*) | SR carry G10 pre-GFC 1.08 → post-GFC 0.25 |
| **Dupuy (2021, *JBF*)** | Vol-conditioned G10 : 0.45 → **0.53, gain "small, insignificant"** |
| Macrosynergy *How to use FX carry* (2000-2024) | Vol-adjustment "delivered a slightly **lower** Sharpe ratio over the past 20 years" |
| Macrosynergy *Advanced FX carry valuation-adjusted* | SR 0.67-0.78 sur **24 devises** (dont EM) — non transférable G10-only |
| Yoldas (Fed FEDS Note, mai 2024) | Canal UIP partiellement rompu 2021-2022 ; coefficient pente négatif et non-significatif |
| BIS Bulletin No. 90 (Aquilina et al., août 2024) | 5 août 2024 : carry unwind cause le spike vol — endogénéité fatale au filtre VXY |
| JPMorgan (Delair, Chandan & Padh, 8 août 2024) | "75% of carry trades removed" — le conditionnement vol n'a PAS évité le crash |
| DBV (Invesco DB G10 Currency Harvest Fund) | Liquidé 10 mars 2023 ; return 10-ans **−0.29%** — même institutionnel a abandonné |

---

## 5. Root cause unique

**Le carry G10 conditionnel échoue le gate constitutionnel 3× au scénario le plus favorable**
(ratio 0.98), et le conditionnement par vol est endogène au phénomène qu'il vise à éviter.

Décomposition :

1. **Dégradation post-2010** : ~80% de la valeur du carry G10 générée dans les années 2000
   (Macrosynergy). Edge épuisé post-publication Brunnermeier-Nagel-Pedersen 2008.

2. **Conditionnement vol insuffisant** : Dupuy 2021 mesure un gain "small, insignificant"
   (0.45→0.53) ; Macrosynergy mesure un gain négatif sur 24 ans. L'amélioration conditionnelle
   documentée ne compense pas le delta coût retail.

3. **Endogénéité structurelle** : le filtre VXY est endogène — l'unwind carry *cause* le spike
   de vol. Le filtre ne peut pas anticiper l'évènement qu'il vise à éviter. Aucun proxy
   non-endogène accessible retail identifié en 2026 (CFTC COT, credit spread, 3M-OIS ne
   résolvent pas l'endogénéité simultanée).

4. **Coût retail asymétrique** : swap broker asymmetry retail (OANDA fév. 2026 : NZD/USD
   long −2.42%/short +0.31%, USD/CHF long +2.82%/short −4.92%) absent des backtests académiques
   (Burnside et al. : bid-ask spot uniquement). Cost drag réel = 1.5-2× le modèle académique.

---

## 6. Lessons confirmées

| Lesson | Citation | Confirmation G1 |
|--------|----------|-----------------|
| L11 (3× gate) | "require gross > 3×cost_drag" | Ratio 0.98 best case → FAIL |
| L11 (β-dominance FX) | Research history : "CS momentum, TSMOM G10: dead post-Menkhoff" | G2A invalide sans IC gate préalable |
| Hard rule AMTP | "Excess returns, HAC lag-6, AMTP if n_tests > 1" | F9 : absent du protocole |
| Hard rule t > 2.5 | "HAC NW lag-6, threshold t > 2.5 for IC feasibility" | F12 : protocole utilisait 1.96 |
| Lesson 10 | "3 modifications maximum per strategy" | F3b/F14 : budget FX-1→FX-4 potentiellement épuisé |

**Nouvelle observation (non lesson formelle) :** Endogénéité des filtres régime sur carry —
le mécanisme de protection (filtre vol, filtre sentiment) est endogène au crash qu'il cible.
Cohérent avec BIS Bulletin No. 90 août 2024 : crash causé par l'unwind, pas l'inverse.

---

## 7. Ce qui est CONSERVÉ vs SUPPRIMÉ

### CONSERVÉ — snapshots immutables (audit pipeline)
- `report_v1.md` — rapport de faisabilité complet, snapshot immutable
- `audit_v1.md` — audit constitutionnel complet, snapshot immutable
- `archive_reasons.md` — résumé du kill analytique
- `audit_summary.md` — grille complète F1-F14 (voir fichier séparé)

### RÉUTILISABLE — infrastructure FX existante
- Données FRED G10 3M (`IR3TIB01[CC]M156N`) : directement utilisables pour G2D carry
  cross-asset (Koijen 2018) si ce pivot est développé
- `Forex/data/cache/dukascopy_m5/` : données M5 G10 téléchargées, in-place, non déplacées
- `data_setup.py` Strategy E : download Dukascopy réutilisable

### NON CONCERNÉ
- `Forex/data/` : infrastructure data partagée, intact
- n_tests global : inchangé à **321** (G1 tué avant tout IC test ou backtest)
- Aucun crontab VPS (G1 jamais déployé)

---

## 8. Conditions pour reconsidération future

Ne pas re-proposer G1 sauf si TOUTES les conditions suivantes sont réunies simultanément :

1. Access JPMaQS (Macrosynergy) ou prime brokerage Bloomberg JPMVXYG7:US — signal
   valuation-adjusted instrumentable
2. Coût d'exécution < 30 bps RT all-in panier G10 (Saxo Pro tier ou prime brokerage) —
   condition nécessaire pour que le ratio gross/3×cost dépasse 1.0
3. Proxy non-endogène au crash carry identifié et accessible retail (CFTC COT, credit spread
   HY-IG, 3M-OIS basis FRED H.15) — avec vérification empirique de la non-endogénéité
4. Sharpe gross G10-only conditionnel > 0.70 documenté sur paper post-2018 avec t_HAC > 2.5
5. Budget Lesson 10 re-ouvert explicitement (résolution ambiguïté FX-2/FX-3)

---

## 9. Liens

- Rapport v1 : `report_v1.md` (snapshot immutable)
- Audit v1 : `audit_v1.md` (snapshot immutable, grille complète F1-F14 dans `audit_summary.md`)
- Strategy E (architecture similaire, closé au même stade) : `Forex/research/archived/strategy_e_fix_flow/POSTMORTEM.md`
- FX-1→FX-4 archived : `Forex/research/archived/fx_carry_fred/`, `fx_momentum_monthly/`, `fx_carry_em/`
- G2D pivot (Koijen 2018 carry cross-asset) : à instrumenter, infra Tradovate réutilisable
