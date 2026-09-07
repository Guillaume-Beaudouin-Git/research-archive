# Ré-ouvertures — audit d'attribution du kill (macro_round6, 2026-09-07)

Mission : appliquer la règle candidate « attribution-du-kill » (`_meta/lessons_registry.md`,
section CANDIDATES) aux archives de recherche du dépôt, et la politique de ré-ouverture
(`CLAUDE.md`) — trouver les familles tuées sur **une variante**, pas sur **le mécanisme**.
Déclencheur du round : ouverture cette semaine d'un compte IBKR (futures ~0,4 bps RT lot
entier) qui change le tarif de coût pour tout ce qui a été tué au tarif CFD retail (2-7 bps).

**Balayage** : disque complet (`find`/`grep`), pas seulement l'index git — `.worktrees/`
inclus (11 worktrees actifs vérifiés, tous sur des branches déjà committées, aucun dossier de
recherche non commité trouvé dedans). Répertoires couverts : `Crypto`, `Forex`, `Futures`,
`Equities`, `Commodities`, `ETF_Vol`, `Options_Vol`, `Multi_Asset` (`research/archived` +
`research/active`), `PropFirms/ftmo/program_2026-06/`.

**Dossiers examinés en profondeur (rapport lu, motif de mort cité) : 15.**
**Retenus pour ré-ouverture : 3. Écartés : 12** (détail §3).

---

## 1. Ré-ouverture #1 — FX segmentation Ranaldo/Breedon (jambe two-sided confirmée, tuée au coût)

**Dossier :** `Forex/research/active/fix_reversal/` — `FIX_REVERSAL_FTMO.md` (2026-06-02) +
`FIX_REVERSAL_TZ_MIGRATION.md` (correction et re-run 2026-06-10, **version faisant foi**).
**Statut actuel :** NO-GO, actif (non archivé) mais fermé opérationnellement, cité comme
fondation de L34.

### Ce qui a été testé exactement
- **Signal :** `short_leg = -log(P[11:00 ET]/P[03:00 ET])`, `long_leg = +log(P[16:00 ET]/P[11:00 ET])`
  (segmentation horaire Ranaldo-Breedon — vendre EUR heures euro, acheter EUR heures US).
- **Univers :** EURUSD seul.
- **Véhicule :** CFD FTMO MT5 (`data/deep_history_utc/EURUSD_M1.csv`, TRUE UTC, corrigé d'un
  bug de fuseau EET qui avait invalidé le premier run).
- **Capital :** compte FTMO (challenge/funded), pas de compte perso testé.
- **Fréquence :** 2 jambes/jour, intraday-flat.
- **Horizon échantillon :** 2007-2026 (19 ans, N=15 039 sur la version TRUE UTC).
- **Estimateur :** HAC lag-6, gross/net avec coût mesuré p95 réel (spread + commission + slippage).
- **Géométrie de sortie :** fermeture programmée en fin de fenêtre horaire, pas de stop/TP.
- **Régime :** pooled sur 19 ans, pas de walk-forward formel par folds (juste des splits
  temporels descriptifs).

### Motif du kill — cité verbatim
> « Pattern B : seul survivant gross (two-sided, t=3,55, SR gross 0,73) — **tué uniquement par
> le tier de coût retail** (besoin < ~1 bps RT/leg pour net positif). Cœur du candidate **L34
> (tier institutionnel uniquement) : CONFIRMÉ et renforcé** » (`FIX_REVERSAL_TZ_MIGRATION.md §4`).

Chiffres TRUE UTC (version faisant foi, remplace le premier rapport EET-era invalidé) :
short leg gross t=2,55 ; long leg gross t=2,62 ; **combiné gross t=3,55, SR gross 0,73, N
correspondant à ~19 ans de sessions quotidiennes** — un edge two-sided propre, les deux
jambes significatives au gross (contrairement au premier run, où l'asymétrie L25 était un
artefact de fuseau horaire, explicitement corrigé : « l'edge est two-sided propre »).
Coût FTMO MT5 mesuré p95 = **2,48 bps/jambe** (spread + commission + slippage réels, calibrés
sur `deep_history_utc`) → coût total 2 jambes/jour ≈ 4,96 bps vs gross combiné 2,07 bps →
net SR -1,02. **Le seuil de coût pour repasser positif est < ~1 bps RT/jambe.**

Le pattern A (fix-reversal Krohn-Mueller-Whelan, fade du fix) est en revanche un **vrai kill
mécanique** confirmé sur la version corrigée (« absence totale de signal au fix » — pooled
t=0,59 sur N=15 039, gross 0,07 bps) : **ne pas rouvrir ce volet.**

### Axes d'instanciation non variés — énumération
| Axe | Varié ? | Pourrait retourner le verdict ? |
|---|---|---|
| **Véhicule** | NON — seul le CFD FTMO MT5 (2,48 bps/jambe) a été testé | **OUI, plausible fort** — le rapport lui-même chiffre le seuil de bascule (<1 bps/jambe) ; Eightcap ECN (~0,75 bps, FX seul, déjà disponible dans le profil) et futures CME 6E via IBKR (~0,4 bps, ouverture cette semaine) sont tous deux SOUS ce seuil |
| Univers | NON — EURUSD seul | Oui mais secondaire — élargir à GBP/JPY/AUD/CHF augmente la breadth, ne change pas le verdict coût |
| Capital | NON — FTMO uniquement | Le compte perso IBKR n'a ni barrière ni horloge — cohérent avec le changement de véhicule |
| Fréquence | Fixe (2 jambes/jour) — c'est la construction du signal, non arbitraire | Non pertinent ici |
| Horizon | 19 ans pooled, pas de walk-forward par fold | Secondaire — le gross est stable two-sided sur tout l'échantillon corrigé (pas de mention de décroissance post-2015 au sens L23) |
| Estimateur | HAC lag-6, correct | Non pertinent |
| Géométrie de sortie | Fixe horaire, jamais testée avec stop/délai | Secondaire |
| Régime | Pooled seul | Secondaire — pas de raison structurelle de régime-dépendance identifiée dans le texte |

**Aucun signe de mort mécanique** (gross ≈ 0, signe contredit à coût nul) sur ce pattern : le
gross combiné est positif, two-sided, t=3,55 — **la mort est intégralement au coût.**

### Classification
**COÛT/VÉHICULE — ROUVRABLE.** Kill correctement isolé et même auto-diagnostiqué comme tel
par le rapport d'origine (« tué uniquement par le tier de coût retail »).

### Angle neuf et budget
**Angle en une phrase :** retester la segmentation Ranaldo/Breedon EURUSD (et élargir à
GBP/JPY/AUD/CHF pour la breadth) au coût Eightcap ECN (~0,75 bps/jambe) et/ou futures CME 6E
via IBKR (~0,4 bps/jambe) au lieu du coût FTMO MT5 (2,48 bps/jambe) — le gross mesuré (2,07 bps
combiné, t=3,55) survit confortablement aux deux tarifs (net ≈ +0,57 à +1,27 bps selon le
véhicule, contre -1,02 SR net au tarif FTMO).
**Breadth :** 2 jambes/jour, ~252 j/an sur EURUSD seul ≈ **504 paris/an** avant élargissement
univers — déjà largement > le plancher de breadth mensuel typique du dépôt ; élargir à 5 paires
majeures multiplierait par ~5 sans changer le mécanisme.
**Coût en essais :** 1 test confirmatoire (recharger le même script `step1_backtest.py` avec un
`step0_costs.json` recalibré sur les coûts Eightcap/IBKR-futures réels — aucune nouvelle
hypothèse, donc pas de nouvel essai HARK au sens strict, mais compter **1 essai déclaré** par
discipline).

---

## 2. Ré-ouverture #2 — Network Momentum (GMOM) : véhicule ETF + breadth sous-dimensionnée + estimateur non sparsifié

**Dossier :** `Multi_Asset/research/archived/network_momentum/feasibility_summary.md`
(généré 2026-05-21, déplacé de `active/` à `archived/` le 2026-05-30 — antérieur de plus de
trois mois à la discipline actuelle de rigueur des rounds macro 2026-08/09).

### Ce qui a été testé exactement
- **Signal :** graph-learning momentum (Laplacian regularization à la GMOM/Poh et al.),
  agrégation de features de momentum par proximité dans un graphe appris.
- **Univers :** 35 actifs (Bond=3, Commodity=7, Crypto=3, Equity=5, FX=9, Sector=8) —
  **tous en ETF/spot**, pas un seul futures.
- **Véhicule :** ETF (SPY, GLD, USO, TLT, IWM, XLE, etc.) + spot FX + spot crypto.
- **Capital :** non spécifié (feasibility research, pas de sizing propfirm).
- **Fréquence :** rebalance mensuel.
- **Horizon :** 2015-2026 (2 968 jours), walk-forward 5 fenêtres annuelles 2020-2025.
- **Estimateur :** régression Laplacian/Frobenius, pénalité de sparsité **absente** (pas de
  LASSO/seuil de corrélation).
- **Régime :** walk-forward 5 fenêtres, 4/5 positives (E3/E4).

### Motif du kill — cité verbatim
> « **ALL VARIANTS FAIL** — graph learning doesn't transfer to this universe at sufficient
> Sharpe. » Meilleur variant **E3 : Sharpe HAC 0,293** (gate >0,7 RESEARCH), MaxDD -11,6%
> (passe le gate research -20%), **WF% positive 80%** (4/5 fenêtres OOS positives), corr avec
> le book existant quasi nulle (corr_A=0,079, corr_C=-0,025).

Le rapport **énumère lui-même trois causes**, sans les avoir testées séparément :
> « **Issue 1 — Dense graph** (Laplacian formulation fails to sparsify) : ... edge density 1.0
> (toutes les 595 arêtes possibles actives) ... vs 0.25-0.55 dans l'article source. »
> « **Issue 2 — OLS cross-sectional regression underpowered at N=35** ... The paper used 64
> assets ... »
> « **Issue 3 — ETF proxies vs futures** : Our universe uses ETFs (SPY, GLD, USO) rather than
> futures. ETF returns include dividends, management fees, and tracking error that corrupt the
> momentum signal at the margin. The paper's futures universe has clean roll-adjusted momentum
> signals. »

### Axes d'instanciation non variés — énumération
| Axe | Varié ? | Pourrait retourner le verdict ? |
|---|---|---|
| **Véhicule** | NON — ETF/spot uniquement, jamais testé en futures roll-adjustés | **OUI** — cité explicitement par les auteurs (« corrupt the momentum signal at the margin ») ; 24 futures continus roll-validés existent déjà dans `Commodities/research/active/xs_basis_tsmom/` + FX/rates/indices futures disponibles ailleurs dans le dépôt |
| **Univers / breadth** | NON — N=35 vs N=64 dans l'article source, explicitement noté « borderline » | **OUI** — élargir à 50-64 instruments (commodities+FX+rates+indices futures) est directement actionnable avec l'infra déjà présente |
| **Estimateur** | NON — pas de sparsification (LASSO / seuil de corrélation) alors que le rapport identifie ceci comme cause n°1 | **OUI** — c'est un changement de géométrie d'estimation, pas de nouvelle hypothèse économique |
| Capital | Non pertinent (rebalance mensuel, coût quasi nul pour cette classe) | Non |
| Fréquence | Fixe mensuel | Secondaire |
| Régime | WF 4/5 positif — déjà un signe encourageant, pas un signe de mort | N/A, plutôt un argument POUR la réouverture |

Signal directionnellement cohérent (WF 80% positif) mais de magnitude insuffisante — **ce
n'est pas un gross ≈ 0 ni un signe contredit**, c'est un edge trop faible sur un univers trop
petit avec un estimateur mal calibré. Aucun des trois éléments cités par les auteurs eux-mêmes
n'a été testé isolément.

### Classification
**VÉHICULE + PUISSANCE + GÉOMÉTRIE (trois axes cumulés) — ROUVRABLE.** Kill non-mécanique :
signal directionnel réel (WF 80%), magnitude sous les gates, cause multi-axes documentée par
les auteurs d'origine mais jamais isolée.

### Angle neuf et budget
**Angle en une phrase :** rejouer GMOM sur ~50-64 futures continus roll-ajustés (commodities +
FX + rates + indices, déjà partiellement disponibles via `xs_basis_tsmom`), avec une
sparsification explicite (seuil de corrélation ou pénalité L1) pour viser la densité de graphe
0,25-0,55 de l'article source, au lieu de la densité 1,0 mesurée ici.
**Breadth :** rebalance mensuel sur 50-64 instruments cross-asset ≈ 12 paris de portefeuille/an
mais avec dispersion cross-sectionnelle sur N≥30 (satisfait la hard rule dès l'univers actuel).
**Coût en essais :** 1 essai pour la reconstruction univers+sparsification (nouvelle
pré-registration nécessaire — c'est un changement de construction, pas un simple recalibrage de
coût ; compter 1-2 essais selon que la sparsification est balayée en grille ou fixée a priori).

---

## 3. Ré-ouverture #3 (priorité plus faible) — Pairs cointegration C1 : dérive de frais ETF confondue avec non-stationnarité

**Dossier :** `Equities/research/archived/pairs_cointegration/` (généré 2026-05-20, archivé —
c'est un **screening pré-backtest**, aucun signal de trading n'a jamais été testé : 0 test IC
consommé selon la convention du dépôt).

### Ce qui a été testé exactement
- **Signal :** aucun — c'est un screening de cointégration (Engle-Granger, Johansen, half-life,
  Hurst) sur 19 paires, gate d'admission avant tout backtest.
- **Univers :** 19 paires en 4 catégories (C1 ETF même indice, C2 ETF sectoriels, C3
  commodity-vs-equity, C4 pairs actions).
- **Véhicule :** ETF et actions US (VOO/IVV/SPY, GLD/IAU, SLV/SIVR, etc.).
- **Capital / fréquence / horizon / estimateur / géométrie de sortie :** non atteints — le
  screening a éliminé 19/19 paires avant tout backtest.
- **Gate liant :** demi-vie ≤ 30 jours, choisi a priori.

### Motif du kill — cité verbatim
> « **STOP — 0/19 pairs pass all 4 cointegration tests.** » Root cause : « **Binding
> constraint: half-life > 30 days (14/19 pairs fail only this).** »
Et, spécifiquement pour la catégorie C1 (ETF du même indice) :
> « Root cause: **expense ratio drift**. VOO (0.03%), IVV (0.04%), SPY (0.0945%) have different
> annual cost drags. Over 15 years, this creates a cumulative drift of 0.1–0.9% in the log
> ratio. **The ADF test on OLS residuals detects this slow drift as a unit root** (can't reject
> I(1)) **even though short-run mean reversion is present.** »
La paire la plus proche d'un pass (V/MA) : « satisfies the Hurst test (genuinely mean-reverting
spread) ... but fails the HL constraint by 3.2× » — Hurst H=0,385 (PASS), EG p=0,075, HL=96j
(vs seuil 30j).

### Axes d'instanciation non variés — énumération
| Axe | Varié ? | Pourrait retourner le verdict ? |
|---|---|---|
| **Véhicule (spécifique C1)** | NON — la dérive de frais qui fait rejeter GLD/IAU et SLV/SIVR est un artefact de STRUCTURE DE PRODUIT (frais annuels différents), pas un signal économique absent | **OUI pour C1** — le rapport le démontre lui-même : la relation de prix EST mean-reverting à court terme (Hurst<0,5) mais le test ADF confond dérive de frais et non-stationnarité. Une paire sans dérive de frais différentielle (ex. futures indiciels vs cash, produits sans expense ratio) échapperait à cet artefact |
| **Seuil / géométrie du gate** | NON — demi-vie ≤ 30j posée a priori, jamais balayée | **OUI** — le rapport propose lui-même l'option de relâcher à 90j (V/MA qualifierait) ou de reformuler en spread-ratio à β=1 fixé (Option B) |
| **Construction de l'univers** | NON — paires ETF/actions US classiques uniquement | **OUI, l'option la plus propre** — le rapport propose explicitement (Option C) : paires structurellement liées et IMMUNES à la dérive de frais (actions à double cotation type Shell A/B ou Unilever PLC/NV, primes de closed-end funds vs NAV, ETF-vs-panier) |

**Ce n'est pas un kill mécanique** au sens strict (aucun signal n'a même été testé — c'est un
gate d'entrée), mais la cause dominante documentée (dérive de frais confondue avec
non-stationnarité) est un **artefact de véhicule identifié par les auteurs eux-mêmes**, qui ont
déjà écrit les trois options de correction sans les tester.

### Classification
**GÉOMÉTRIE (seuil de gate) + VÉHICULE (dérive de frais) — ROUVRABLE, priorité plus faible.**

### Angle neuf et budget
**Angle en une phrase :** re-screener les catégories C1 et C3 avec (a) la reformulation
spread-ratio à β=1 fixé (Option B du rapport, corrige l'estimation OLS) ET (b) un univers élargi
à des paires structurellement immunes à la dérive de frais (double cotation, CEF premium/NAV) —
sans toucher au reste de la méthodologie.
**Breadth :** faible et c'est la limite principale — même optimiste, 1 à 3 paires qualifieraient
(V/MA proche, + 1-2 paires structurelles nouvelles), très en dessous du plancher N≥30 pour une
stratégie cross-sectionnelle ; **seule une stratégie mono-paire ou multi-paire à N<10 en
sortirait**, ce qui limite fortement l'intérêt même en cas de PASS.
**Coût en essais :** 1 essai (screening seul, pas de backtest tant que le gate n'est pas
repassé) — très bon marché, mais **priorité basse** vu la breadth structurellement faible même
en cas de succès.

---

## 4. Dossiers examinés et écartés (12) — avec motif explicite

Pour chacun, le texte du rapport a été lu et le motif de mort a été jugé **soit mécanique
(gross ≈ 0 / signe contredit / IC négatif persistant), soit déjà correctement attribué et
adressé cette semaine, soit ambigu sans que l'axe non varié soit plausible.**

1. **`Multi_Asset/research/active/swapkilled_futures_2026-07/`** (9 hypothèses H1-H9) — **déjà
   la ré-ouverture systématique de familles tuées au swap, testée directement sur véhicule
   futures/personnel.** H1 (NQ overnight) et H5 (dispersion) FALSIFIED comme **beta slices**
   (« NQ overnight-only SR 0.80 < buy-&-hold 24h SR 0.95 ») — mécanique, pas véhicule. H6
   (month-end FX flow) FALSIFIED sur données propres (SR 0,05≈0, post-2015 -0,03) — mécanique.
   H7/H8 (grilles vol courte) FALSIFIED comme pièges de ruine structurels. H3 (month-end
   Treasury) et H9 (spreads crack) **déjà PASS et déployés/en cours de déploiement** (source du
   L51-L55 gravé). **Rien à rouvrir ici — le travail est déjà fait, dans les deux sens.**
2. **`Commodities/research/archived/commodity_tsmom/`** (TSMOM absolu sur 12 ETF commodities,
   Sharpe 0,391, dir. accuracy 51%, AMTP p=0,808) — le rapport d'origine **ne cite jamais le
   roll drag** comme cause explicite (contrairement à ce que suggère la lesson L5 générale) ;
   les contributions par actif (USO +4,1%, UNG +1,6%, positives) ne montrent pas de signature
   de roll drag évidente pour un système long/short adaptatif. Et le même mécanisme TS/XS a
   été **directement retesté sur 24 futures continus roll-ajustés** dans `xs_basis_tsmom`
   (momentum XS commodities = REVERSAL, IC t -2,6 à -3,4, mécanique). Écarté : attribution
   d'origine trop faible, terrain déjà substantiellement recouvert par un retest futures.
3. **`Multi_Asset/research/active/forced_flow_cooccurrence_2026-08/`** — verdict du rapport
   lui-même : « un kill MÉCANIQUE (gross ≈ 0 à coût nul, signe contredit) — donc NON rouvrable
   au sens de la politique de ré-ouverture ». Déjà correctement classé par le dossier source.
4. **`Multi_Asset/research/active/gold_cpi_eve_2026-08/`** — retest confirmatoire d'un
   candidat identifié la semaine dernière (`sleeve_search_2026-08-06`) ; **rejeté cette
   semaine** (t_HAC plein échantillon 1,53, OOS pur 2007-2019 vide, t=0,40, p=0,95) — déjà
   tranché, pas une découverte nouvelle pour ce round.
5. **`Multi_Asset/research/active/two_sided_axis_2026-08/`** — verdict explicite du rapport :
   « L'axe du SIGNE est FERMÉ, par un kill MÉCANIQUE » (jambe short positive au gross dans
   1/21 cellules seulement). Correctement fermé.
6. **`Multi_Asset/research/active/statarb_multivariate_2026-08/`** — la meilleure cellule
   (GER40→US30, h=60) a IC 0,086, t_HAC 4,70 mais **walk-forward 1-2 folds/5**, tout l'edge
   concentré dans le fold COVID (gross +31,5 bps contre -0,5 à -2,3 ailleurs). C'est
   précisément ce que le test walk-forward est censé détecter — limite floue avec un kill
   mécanique de persistance, jugé trop fragile pour être classé « régime rouvrable » sans
   nouvelle donnée post-échantillon.
7. **`Equities/research/archived/multi_asset_tsmom/`** — Sharpe 0,43-0,67 selon overlay, mais
   **DSR full-sample échoue systématiquement** (p=0,23 à 0,79) après ajustement du nombre
   d'essais (58-62) consommés dans CE thread. Le kill est un problème de multi-testing propre
   au thread, pas un artefact de véhicule (ETF implicite non cité comme cause) — changer de
   véhicule ne répare pas un DSR qui échoue à cause du nombre de variantes essayées.
8. **`ETF_Vol/research/archived/vix_term_carry/`** — argument véhicule plausible (VIXY vs
   futures VX directs) mais **secondaire face à l'AMTP** (p=0,674 sur n=71 essais du thread) :
   le kill dominant est un problème de multi-testing du thread de recherche, pas du coût ou du
   véhicule de l'instrument — changer d'instrument ne change rien à l'AMTP.
9. **`Forex/research/archived/strategy_d_modified_carry/`** — IC carry brut +0,022 (t=0,81),
   carry modifié REER -0,010 (t=-0,26). Rapport : « The full-period IC of +0.022 is entirely an
   artifact of 2005-2007 ... zero or negative predictive power ... since approximately 2011. »
   Rupture structurelle post-GFC documentée sur 15 ans — kill mécanique, et de toute façon dans
   le périmètre exclu (« carry FX conditionné »).
10. **`Forex/research/archived/cip_eoq/`** — cost gate L11 échoue ×5 (gross 5-10 bps vs coût
    4-jambes 6-12 bps), MAIS le rapport a **déjà explicitement testé et écarté** l'angle
    véhicule futures : « CME XEU futures launched Feb 2025 ... ADV effectively zero one year
    after launch » et pose des conditions de déclenchement chiffrées (ADV>500 contrats/j) non
    remplies. L'axe véhicule a été varié et fermé, pas laissé non testé — à ne PAS rouvrir sans
    que les conditions de déclenchement écrites par les auteurs soient remplies.
11. **`Multi_Asset/research/active/cross_conditioning_2026-08/`** — grille de verdicts mixtes
    déjà très instrumentée (gates GROSS d'abord, walk-forward, DSR, R² vs buy&hold) ; les
    cellules qui passent le gross ne survivent pas au réseau de contrôles internes déjà
    appliqué cette semaine — pas de nouvel angle à apporter sans re-belaboring un travail déjà
    fait avec la discipline recherchée par ce round.
12. **`Multi_Asset/research/active/regold_funnel_2026-08/`** — « Trois candidats atteignent un
    seuil au coût corrigé. **Aucun n'est un PASS.** » Audit de reproduction déjà fait au niveau
    de rigueur visé par cette mission ; rien à ajouter sur l'attribution.

---

## Résumé (≤20 lignes)

**15 dossiers examinés en profondeur, 12 écartés, 3 retenus.**

1. **FX segmentation Ranaldo/Breedon (EURUSD, `Forex/research/active/fix_reversal/`)** —
   priorité **haute**. Edge two-sided confirmé (t=3,55, gross 2,07 bps combiné) tué
   *uniquement* par le coût FTMO MT5 (2,48 bps/jambe) ; le rapport chiffre lui-même le seuil de
   bascule (<1 bps/jambe) — Eightcap ECN (0,75 bps, déjà disponible) et futures IBKR (~0,4 bps)
   passent tous deux ce seuil. Breadth ~504 paris/an sur EURUSD seul. Coût : 1 essai
   confirmatoire.
2. **Network Momentum GMOM (`Multi_Asset/research/archived/network_momentum/`)** — priorité
   **haute**. WF 80% positif, corrélation quasi nulle au book — magnitude insuffisante
   attribuée par les AUTEURS eux-mêmes à trois axes jamais isolés : véhicule ETF (« corrupt the
   momentum signal »), breadth N=35 vs 64 dans l'article source, estimateur non sparsifié
   (densité de graphe 1,0 vs 0,25-0,55 visé). Infra futures (24 continus + FX/rates) déjà dans
   le dépôt. Coût : 1-2 essais.
3. **Pairs cointegration C1 (`Equities/research/archived/pairs_cointegration/`)** — priorité
   **basse**. Dérive de frais ETF (VOO/IVV/SPY, GLD/IAU) confondue avec non-stationnarité par
   le test ADF, démontré par les auteurs ; mais breadth structurellement faible (1-3 paires
   même en cas de succès) — cher en effort relatif au gain espéré.

Le dossier `swapkilled_futures_2026-07` (9 hypothèses) montre que l'exercice de ré-ouverture
« véhicule futures » est **déjà largement fait** dans ce dépôt pour la classe la plus évidente
(overnight, month-end, crack spreads) — d'où l'intérêt de cibler ici la FX microstructure et le
cross-asset network momentum, deux familles hors de ce balayage antérieur.
