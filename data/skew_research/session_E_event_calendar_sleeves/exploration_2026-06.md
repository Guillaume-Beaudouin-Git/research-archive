# Skew research — session_E_event_calendar_sleeves (event-premia & flux à contrainte mécanique)
### Exploration 2026-06. Objectif : sleeves skew+/décorrélés TSMOM, FTMO-tradeables, **NET-CFD-survivants** (L7).
*Loi structurelle de l'arc : sur instruments FTMO, seuls survivent les EVENT-PREMIA et FLUX À CONTRAINTE MÉCANIQUE PERSISTANTE. session_B a sorti la pièce or-seasonal ; on chasse d'AUTRES sleeves de la même famille.*
*Règle : mécanisme PRESPEC, 1 spec canonique (L10), excess vs DTB3 + HAC lag-6, two-sided (L25), OOS (L31), corr-TSMOM, **DSR déflaté incluant la sélection**, **verdict binaire NET CFD t>1,5 ou meurt**.*

---

## Modèle de swap CFD (conservateur, documenté — swaps FTMO non publiés en table, in-platform only)
Recherche : FTMO publie les swaps dans le terminal (Market Watch), pas en table web (FAQ FTMO « account specifications » + mécanique financing CFD). J'applique donc un **modèle conservateur basé sur la mécanique de financing**, ère taux-hauts 2024-26 (USD ~5%) + markup courtier ~2,5% :

| classe | swap long (bps/nuit) | spread (bps/side) | nuits tenues |
|---|---:|---:|---|
| Indices (US500/US100/US30/GER40/UK100/JP225) | −2,5 | 1,5 | #1 ~1 · #3 ~1/j |
| Métaux Ag/Pt/Pd (non-or, plus lourds) | −3,5 | 4,0 | #2 ~21 (mois plein) |
| Énergie WTI (curve roll) | −4,0 | 4,0 | #4 ~1 |

*Conservateur = du côté lourd. La saisonnalité métaux (#2) porte donc ~−81,5 bps/mois de drag (21×3,5 + 8 spread) — le killer attendu. Verdict robuste si l'edge survit à CE swap.*

## Tableau de verdict (gross excess HAC · NET-CFD HAC · corr-TSMOM · survit/meurt)

| # | sleeve | gross (HAC t) | **NET-CFD (HAC t)** | corr-TSMOM | skew | **verdict t>1,5** |
|---|---|---|---|---:|---:|---|
| 1 | Pré-CB drift ECB→DAX | −28bp (−0,81) | −34bp (−0,97) | −0,01 | — | ❌ **MEURT** |
| 1 | Pré-CB BOJ→NIKKEI | +16bp (+0,82) | +11bp (+0,54) | +0,01 | — | ❌ MEURT |
| 1 | Pré-CB FOMC→SP500 | +15bp (+0,82) | +10bp (+0,53) | +0,01 | — | ❌ MEURT (decay) |
| 2 | **Silver January** | +468bp (+3,72) | **+387bp (+3,07)** | +0,056 | +0,12 | ✅ **SURVIT** (≈gold) |
| 2 | **Platinum January** | +415bp (+3,74) | **+334bp (+3,00)** | +0,055 | +0,16 | ✅ **SURVIT** |
| 2 | Palladium January | +294bp (+2,72) | +213bp (+1,97) | +0,036 | +0,44 | ⚠ survit faible |
| 2 | **Ag+Pt combiné** | +360bp (+3,13) | **+279bp (+2,42)** | +0,060 | **+0,35** | ✅ **SURVIT** |
| 3 | Turn-of-month US500/100/30 | +4-8bp/j (≤0,81) | +3-6bp/j (≤1,24) | — | — | ❌ MEURT (beta) |
| 4 | EIA drift WTI | Wed −28bp (−1,44) | −1bp (−0,13) | — | — | ❌ MEURT |
| 5 | Reconstitution indice | — | — | — | — | ❌ **KILL archive** |

## #2 — Le find, avec la nuance décisive (additionnalité)
Les 4 précieux ont un **vrai seasonal janvier** (mécanisme Q1 : demande physique festival/mariage/restock, **identique au gold de session_B**), et silver/platinum **survivent au net-CFD à t~3,0** même avec 21 nuits de swap métal lourd. **Robuste au swap** : même à 2× l'hypothèse (−7bp/nuit), silver net resterait ~+313bp (t~2,5).

**MAIS additionnalité — ce ne sont PAS 4 briques indépendantes :**
- **corr(silver-Jan, gold-Jan) = +0,86** → silver = gold-seasonal en plus volatil, redondant.
- corr(platinum-Jan, gold-Jan) = +0,42 (moyennement distinct) ; corr(palladium, gold) = +0,09 (indépendant) **mais palladium est le plus faible** (net t=1,97, et son best-month est Février → fragile au mining).
- **DSR×12 (sélection du mois) silver = 0,864 → FAIL** si janvier traité comme mined-best-of-12 ; **PASS** si janvier est pré-spécifié par le mécanisme or (ce qu'il est : transfert de mécanisme validé, pas mine fraîche). Honnêteté : la cellule silver seule n'est pas robuste au test multiple ; c'est le **faisceau** (4 métaux, même signe, même mécanisme, gold déjà keeper) qui en fait un effet de famille réel, pas une cellule isolée.

→ **Conclusion #2 : la famille survivante s'élargit de l'or à un panier « précieux-Q1 » (Ag+Pt+Pd+Au).** C'est **un sleeve plus robuste/large** (skew combiné +0,35 > gold seul −0,26 ; capacité ↑), **pas 4 sleeves décorrélés neufs.** Palladium = le seul ajout quasi-indépendant (corr 0,09) mais le plus faible. OOS : combiné pre-2014 +601 → post-2014 +212 (decay L31 net, reste fortement positif).

## #1 — pré-CB : meurt (et un artefact d'échantillon attrapé)
Premier run faux-positif : DTB3 s'arrête avant 2026 → l'excess (drop-NaN) tournait sur le sous-échantillon ancien favorable (ECB « +38bp t=2,70 »). **Corrigé sur full sample** : ECB→DAX = **−28bp t=−0,81** (pré-2023 −96bp : selloffs ECB hawkish 2022), BOJ +16bp t=0,82, **FOMC +15bp t=0,82 mais post-2023 +2bp = decay** (exactement le risque pré-spécifié). Aucun ne survit au net (t≤0,54). Le drift pré-résolution daily n'est pas harvestable net-CFD sur ECB/BOE/BOJ ; N≈48 mais le signal est absent, pas juste sous-puissant.

## #3/#4/#5 — meurent
- **#3 ToM** : le premium ToM (+2,4 à +4,4 bps/j vs non-ToM) n'est **pas distinct du beta long** (HAC t≤0,81 gross, net t≤1,24) → c'est de la concentration de beta sur quelques jours, pas un edge. Le test two-sided/distinctness tranche : MEURT.
- **#4 EIA** : V-shape Tue−28/Wed−28/Thu+32 mais aucun t>1,5 et signes opposés (pas de drift systématique indépendant de la surprise) ; net Wed −1bp. MEURT (prior faible confirmé).
- **#5 reconstitution** : KILL d'office — non-tradeable sur les 23 CFD large-cap (adds/deletes single-name), effet indice ≈0 déjà mesuré (`session_3 B2`, `session_structural_dislocations #1`). Non re-testé (discipline familles-mortes).

## VERDICT FINAL (session_E)
**1 famille survivante élargie, 0 brique neuve pleinement indépendante.**
- ✅ **Précieux-Q1 (Ag+Pt+Pd+Au) survit net-CFD** (silver/platinum net t~3,0 ; combiné Ag+Pt t=2,42, skew +0,35, corr-TSMOM 0,06). **Élargit la pièce or de session_B** en un panier plus robuste — à verser au sleeve metals-seasonal existant, pas comme 4 sleeves séparés (silver corr 0,86 à gold). Palladium = seul ajout quasi-indépendant mais faible.
- ❌ **Pré-CB drift, ToM, EIA, reconstitution = meurent** (net <1,5 / beta / decay / non-tradeable).

→ **Confirme la loi structurelle ET la raffine** : les flux à **contrainte mécanique persistante** (demande physique Q1 précieux) survivent net-CFD ; les **event-premia de résolution** (pré-CB) **décayent et meurent net** — tous les event-premia ne se valent pas. Le seul terrain qui produit du net-survivant reste la saisonnalité physique précieux.

## Candidats-leçons (NOMMÉS)
- **« La saisonnalité précieux-Q1 survit au net-CFD ; les non-or sont surtout du beta-or »** — silver/platinum Jan net t~3,0 (robuste à 2× swap) MAIS corr 0,86/0,42 à gold-Jan → élargissent le sleeve or, ne le décorrèlent pas. Palladium (corr 0,09) indépendant mais faible (t=1,97, best-month Feb).
- **« Event-premium de résolution ≠ flux mécanique persistant : le premier décaye, le second tient »** — pré-CB (ECB/BOE/BOJ/FOMC) meurt net (FOMC post-2023 +2bp), la demande physique Q1 tient. Distinguer dans la « loi event-premia » les deux sous-familles.
- **« Sample-consistency : un RF à couverture partielle fabrique un faux-positif »** — DTB3 finissant avant 2026 a sorti ECB « +38bp t=2,70 » (sous-échantillon ancien) vs −28bp full-sample. Toujours aligner l'échantillon gross/net (ffill RF ou restreindre les deux). 4e faux-positif attrapé de l'arc.
- **« Net-CFD décide, et il faut le mécanisme du swap »** — la saisonnalité métaux porte ~−81 bps/mois (21 nuits) ; seul un gross >+400bps survit. Le swap-mois est le filtre, pas le spread. Mesurer nuits×swap, pas un coût RT unique (L33).
- **« DSR×12 sur sélection-de-mois : une cellule isolée ne passe pas, le faisceau-mécanisme oui »** — silver seul DSR×12=0,864 (fail) ; c'est la cohérence des 4 métaux + le keeper gold qui valide la famille, pas la cellule.

---
*session_E_event_calendar_sleeves, 5 candidats. Données : xs_universe + commod_daily (Ag/Pt/Pd/oil) daily 2005-2026, DTB3 (RF), news_events 2020-2025 (ECB/BOE/BOJ/FOMC), book_JG/TSMOM (corr). Swap modèle conservateur documenté (non publié FTMO). HAC lag-6, DSR déflaté Bailey-LdP. Tout backtest, 0 jour live. Réconcilié archive (session_B or-seasonal, session_3 B2, session_structural #1 — pas de re-preuve). Rien figé, rien mergé. Écrit uniquement dans ce périmètre ; non touché aux autres sessions ni overnight_research/.*

Sources (swap research) : [FTMO account specifications FAQ](https://ftmo.com/en/faq/what-are-the-account-specifications/), [FTMO trading updates](https://ftmo.com/en/trading-updates/), [CFD swap/overnight financing mechanics — ActivTrades](https://www.activtrades.com/en/news/what-are-swap-rates-overnight-financing-for-cfd-positions).
