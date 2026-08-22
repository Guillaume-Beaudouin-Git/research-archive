# Cartographie des pistes rouvrables — PARTIE 2 (les trous nommés par la Partie 1)

**2026-08-21.** Poursuite de `CARTOGRAPHIE.md` (non modifiée). Aucun test exécuté sur données de
marché — uniquement lecture de résultats déjà calculés, vérification de chiffres cités, lecture
de code, et deux requêtes littérature datées. Un diagnostic ne consomme pas de DSR.

---

## SYNTHÈSE (≤12 lignes)

**~15 dossiers diagnostiqués en profondeur** (3 postmortems FX, 1 famille NQ intraday + ses 2
dérivés, 2 constructions de littérature vérifiées, ~13 lignes crypto de l'inventaire véhicule,
164 du funnel FTMO via l'artefact déjà produit). **Résultat net : 2 candidats de plus qu'en
Partie 1**, tous deux déjà repérés par le Programme 2 (véhicule) mais jamais montés en priorité —
**R023** (combo D3+D5, budget 3-mods intact, NOUVEL ESSAI) et **S035 Gap Pattern** (le plus
propre near-miss du corpus 109, mais watch-list, pas priorité). **Les trois postmortems FX
tiennent** : E (cost-tier institutionnel, déjà re-testé sur futures 6E et mort quand même), G1
(ratio 3× gate 0.98 même au meilleur cas, source elle-même qualifie le gain "insignificant"), F2
(le gate corrigé L11b **a déjà été appliqué dans le postmortem lui-même** — ratio 2.565 < 3.0,
rien à refaire). **Le gross NQ MR/afternoon n'existe nulle part** dans le dépôt en forme
récupérable — et pire, sa vraie cause de mort documentée est la **PUISSANCE** (N=19 trades/3 ans,
AMTP=1.000), pas le coût : **le candidat n°2 de la Partie 1 est donc RETIRÉ**, mal caractérisé par
le résumé d'une ligne. **Crypto (159) et funnel FTMO (164) : confirmés épuisés**, aucune exception
mécanique trouvée dans les artefacts déjà produits. **Constat principal** : le programme de
contraste littérature ne trouve **aucune** construction erronée nouvelle (Koijen carry = écart de
breadth déjà nommé en Partie 1 ; VRP Deribit = construction retail-standard, correctement
implémentée). **Ce qui n'est PAS recommandé de rouvrir** : les 3 postmortems FX, tout le corpus
crypto (159), les 162 du funnel FTMO, et l'ancien candidat n°2 NQ — voir §6.

---

## 1. Les trois postmortems FX — verdict tranché

### 1.1 Strategy E — WMR Fix + EOM USD Flow — **KILL TIENT, fermé**

[V] `Forex/research/archived/strategy_e_fix_flow/POSTMORTEM.md:36-43` : E1 intra-mois 1-4bp gross
vs 6-7bp coût retail Dukascopy → net <0 ; E1 EOM ~15bp gross, ~12 événements/an, net Sharpe
0.3-0.5 mais N trop petit pour être fiable ; E2 conditionnel t_HAC≈1.2, N_eff 35-45.

Le raisonnement n'est **pas** un gate mal calibré : c'est une comparaison directe gross-vs-coût
avec sources datées (Benenchia-Galati-Lepone 2024, Krohn-Mueller-Whelan 2024 [LIT, cités dans le
postmortem]) documentant la décroissance post-réforme BIS 2015. Krohn et al. 2024 est explicitement
le papier qui "ferme la branche conditionnelle" (E2) — ce n'est pas notre biais, c'est la
littérature elle-même qui révise à la baisse le signal EOM conditionnel post-2015.

**Déjà re-testé depuis, sur véhicule futures, et mort quand même** [V]
`Multi_Asset/research/active/reaudit_vehicule_2026-08/vehicule/RAPPORT.md:108,147,164-166` : le
même mécanisme apparaît dans l'inventaire véhicule comme **R015 "fix WMR (Ranaldo)"** — gross
2.07 bps/j two-sided, t 3.55 (le seul vrai t two-sided de la matrice). Re-gaté au coût futures
6E : ratio **2.11, PASS** — mais notionnel **10.49× le compte de €12k, infaisable** ; sur le micro
M6E, granulaire, le ratio retombe à **0.71, FAIL**. Le coût qui tuait la famille au tier retail la
retue au tier micro-futures (piège de ciseaux, §6.1 du rapport véhicule). **Conclusion : E est
fermé sur DEUX tiers de coût indépendants** (Dukascopy retail ET futures micro), avec un
mécanisme dont le t-stat véritable (3.55) est le meilleur de tout le corpus FX du dépôt — et il
meurt quand même. **Ne pas rouvrir sans un compte ≥ €120k (6E plein) ou un broker prime
<1.5bp.**

### 1.2 G1 — Carry G10 conditionnel — **KILL TIENT, fermé**

[V] `Forex/research/archived/g1_carry_conditional/POSTMORTEM.md:83-116` : gate 3× au **meilleur
cas** donne ratio **0.98** (gross 530bps vs 3×cost_drag 540bps) — **sous 1.0 même au scénario le
plus favorable**. Et le papier source lui-même (Dupuy 2021 [LIT]) qualifie son propre gain de
conditionnement vol de **"small, insignificant"** (SR 0.45→0.53). Macrosynergy (2000-2024 [LIT])
mesure un gain **négatif** sur 24 ans de vol-adjustment. Trois sources indépendantes convergent
vers la même conclusion : le conditionnement n'ajoute rien d'exploitable.

Les 4 "deal-breakers" procéduraux cités (AMTP absent, seuil HAC 1.96 vs 2.5, budget 3-mods non
vérifié) sont **secondaires** — le kill substantif (gate 3×, ratio <1 même best-case) est
indépendant d'eux et suffit seul. Ce n'est **pas** un cas de gate IJR mal appliqué à un
instrument binaire (contrairement à F2, §1.3) : G1 est un portefeuille long-short continu sur 6-7
paires, rebalancé mensuellement — c'est exactement la structure cross-sectionnelle pour laquelle
Grinold-Kahn/IJR est valide. **Aucune signature S1-S8 objective ici** — l'endogénéité du filtre
vol (BIS Bulletin 90, août 2024 [LIT] : l'unwind carry CAUSE le spike de vol) est un argument
économique, pas une erreur d'implémentation. **Kill mécanique-économique, reste fermé.**

Le pivot que le postmortem nomme lui-même — Koijen et al. 2018 carry cross-asset — est **différent**
de G1 (G1 = carry FX seul conditionné ; Koijen = carry multi-classe) et déjà correctement identifié
en Partie 1 §4 comme nouvel essai, pas une correction de G1.

### 1.3 F2 — Asian Range Breakout — **KILL TIENT, déjà corrigé par lui-même**

C'est le cas signalé par la mission comme le plus probable d'un raisonnement trop rapide. Il ne
l'est pas : [V] `Forex/research/archived/strategy_f2_asian_breakout/POSTMORTEM.md:54-70` montre
que le postmortem **a déjà calculé le gate L11b corrigé, dans le document lui-même**, daté
2026-05-26 — avant même que L11b soit gravée dans le registre :

> "L11 Alt — Binary TP/SL Gate ... gate_ratio **2.565** ... Verdict **FAIL** (< 3.0) ... Alt gate
> passes at IC ≥ 0.107 (win_rate ≥ 55.3%) ... **Bumping IC post-failure without data is post-hoc
> adjustment; refused.**" (lignes 54-70)

Autrement dit : F2 n'a pas été tué par le mauvais gate IJR seul — le postmortem calcule **les
deux gates**, IJR (ratio 0.478-0.751, FAIL) et le gate corrigé E[gross/trade] > 3×cost (ratio
**2.565**, FAIL aussi) à l'IC pré-enregistré de 0.05. Le seul chemin de réouverture serait un IC
≥ 0.107 (win rate ≥ 55.3%) **documenté numériquement par la littérature AVANT de regarder les
données** — le postmortem le dit explicitement et refuse de le faire post-hoc. Aucune source de ce
niveau n'a été trouvée depuis (Tzimopoulos 2025, cité dans le postmortem, ne publie pas de
win-rate numérique par régime).

**Verdict : F2 est le cas d'école inverse de ce que la mission anticipait** — la correction
méthodologique existe déjà dans l'archive, datée du jour même de l'archivage, et le kill résiste
au bon gate. Rouvrir exigerait une **hypothèse nouvelle** (un IC justifié par une source non encore
trouvée) — ce serait un NOUVEL ESSAI, pas une correction, et rien ne le justifie aujourd'hui.

---

## 2. Contraste littérature — deux constructions vérifiées, une confirmation externe

### 2.1 Hurst-Ooi-Pedersen 2017 — confirmation externe du diagnostic de la Partie 1

[LIT, WebSearch 2026-08-21] AQR / *Journal of Portfolio Management* 44(1):15-29 — "time series
momentum has been profitable... for nearly all **equity index futures, fixed income futures,
commodity futures and currency forwards**", données depuis 1880. Ceci **confirme** le diagnostic
S1 de la Partie 1 (§2.1) : le papier teste des **futures/forwards**, jamais des ETF, sur un
univers documenté ailleurs par la même équipe à ~58-67 contrats. Le repo a testé 12 ETF dont
USO/UNG. Rien à ajouter — la Partie 1 avait raison, et c'est maintenant sourcé de façon externe et
datée plutôt que déduit du seul résumé interne.

### 2.2 Koijen-Moskowitz-Pedersen-Vrugt 2018 ("Carry") — l'écart de breadth, chiffré

[LIT, WebSearch 2026-08-21] *Journal of Financial Economics* 127(2):197-225 : le carry y est
testé sur **actions globales, obligations globales, commodités, Treasuries US, crédit, ET
options** — six classes d'actifs, la construction est explicitement présentée comme
**multi-classe** (le carry FX n'est qu'une sixième du cadre du papier).

Confronté au corpus du dépôt : `research_history.md:16` liste "G10 carry (FX-1 to FX-4)" et
`Forex/research/archived/g1_carry_conditional/POSTMORTEM.md` (G1) — **les deux ne testent QUE le
carry FX**, jamais les cinq autres classes. C'est une signature **S2 (breadth insuffisante)**
objective : le dépôt a testé **1/6 de la construction du papier cité comme pivot**. Ce n'est pas
un vice caché — le postmortem G1 le nomme lui-même comme pivot non exploré
(`report_v1.md`/`POSTMORTEM.md:217` "G2D pivot") — et la Partie 1 l'a déjà correctement classé
comme **NOUVEL ESSAI** (pas une correction de G1, un mécanisme différent). Rien de nouveau à
corriger ici ; la vérification externe confirme juste l'ampleur du trou (6 classes testables,
1 testée) et que l'infrastructure FRED G10 3M citée comme réutilisable ne couvre que la
composante FX du nouveau test — les obligations/commodités/actions/crédit demanderaient une
collecte de données neuve, pas seulement un nouveau signal sur des données existantes.

### 2.3 VRP Deribit BTC — construction vérifiée, **AUCUNE violation S5 trouvée**

Hypothèse à vérifier : le VRP académique se construit par réplication de swap de variance
(pondération 1/K² sur un continuum de strikes, Carr-Wu 2009-style) — la construction utilisée
au repo (straddle ATM simple, delta-hedgé, roulé) pourrait être un indicateur ad hoc (S5).

[V] `Crypto/research/archived/options/vrp_deribit/engine.py:1-14`, `HYPOTHESIS_VRP.md:17-24` :
le signal ex-ante utilise **DVOL** (l'indice de volatilité Deribit, lui-même construit
model-free façon VIX sur un continuum de strikes) moins RV30 réalisé — **c'est la bonne
construction du signal**, pas un proxy dégradé. Le P&L est réalisé via straddle ATM
delta-hedgé, l'approximation B-S standard pour un praticien retail qui ne peut pas trader un
swap de variance directement — **c'est la pratique retail normale**, pas un raccourci qui
invalide le test (les swaps de variance ne sont pas cotés sur Deribit ; aucune option
retail-accessible ne réplique un swap de variance sans cette approximation).

**Verdict : pas de signature S1-S8.** Le kill (`DECISION.md:8-17` [V]) est un vrai kill
mécanique-économique : coûts 8.89%/an (fees 49% + spread 49%, symétriquement) contre gross
4.44%/an, ratio coût/gross **200%**, **0/13 plis WF positifs**, stress LUNA/FTX confirmant la
queue. Reste fermé — **confirme** l'entrée "à laisser fermé" de la Partie 1, avec vérification de
construction en plus (ce que la Partie 1 n'avait pas fait).

### 2.4 Funding-extremes crypto (L50) — pas d'écart trouvé

Non creusé en détail (hors budget de cette passe) : L50 documente déjà une réplication
inter-exchange (HL puis Binance, 2,195 événements) confirmant la continuation — c'est déjà une
comparaison-littérature interne robuste (deux jeux de données indépendants). Aucun signal de
mauvaise construction relevé dans le registre. Non retenu comme piste de contraste supplémentaire.

---

## 3. Chantier NQ intraday — le gross retrouvé, et le candidat n°2 de la Partie 1 est RETIRÉ

**Source identifiée** [V] `Futures/research/archived/nq_intraday_vwap/iter_01.py` +
`iter_01_summary.md` — "Strategy D iter_01: VWAP Mean Reversion NQ Afternoon", n_tests 126→130,
c'est la seule famille du dépôt correspondant au libellé `research_history.md:34` ("NQ VWAP MR /
afternoon momentum: all FAIL ($19 RT cost kills any edge)").

### 3.1 Le vrai kill documenté n'est PAS le coût — c'est la PUISSANCE

[V] `iter_01_summary.md:20,45,53-56,61` : meilleure variante (1d, touch exit) — **N=19 trades sur
3 ans** (~6/an), **AMTP = 1.000** ("certain false positive given n_tests=130"), et le document
conclut lui-même : **"Effective verdict: FAIL — 19 trades is the binding constraint. Any Sharpe
estimate with N<50 is unreliable."** Le filtre (z>2σ ET 3 barres consécutives, fenêtre
12:30-15:00) ne tire que 19 fois sur 23 400 créneaux disponibles (0.08%). Pire : le document
lui-même avance une explication économique **contraire à l'hypothèse** — "NQ (Nasdaq 100) is a
momentum-dominated instrument... This is the opposite of the mean-reversion hypothesis"
(ligne 61), cohérent avec Baltussen-Da-Lammers-Martens 2021 [LIT, cité indépendamment dans
`Futures/research/active/strategy_d/hypotheses_preregistered.md:92-95`] qui documente la
**continuation** (pas la réversion) intraday sur futures indiciels l'après-midi.

Donc la ligne de `research_history.md` **mécarcatérise son propre test** : ce n'est pas
"$19 RT cost kills any edge", c'est "N=19 trades tue toute inférence, et l'hypothèse pourrait
être économiquement inversée de toute façon". Le coût est même objectivement petit ici : `iter_01.py:42-45,260-261` [V] — `COST_RT=$19` s'applique à un nombre de contrats
`clip(DOLLAR_RISK/(sl_dist×POINT_VALUE), 0.1, 2.0)`, donc le coût réel par aller-retour va de
**$1.90 à $38.00** selon le sizing, jamais un "$19 RT" constant — ce n'est même pas la bonne
lecture du chiffre cité.

### 3.2 Le gross bps/trade — NON RETROUVABLE sans ré-exécution

Aucun fichier de trades (`pnl_pts`, `contracts` par trade) n'a été persisté — `iter_01.py`
calcule et jette ces champs en mémoire ; seules les statistiques agrégées **nettes** de
`iter_01_summary.md` survivent (avg winner net $278.68, avg loser net -$90.09, N=19). Reconstruire
le gross exigerait de re-exécuter le backtest sur données de marché — **hors périmètre de cette
mission (contrainte 1)**. **La réserve L33b ("faut > 3 bps de gross pour exister en
intraday-flat") reste NON LEVABLE pour cette famille précise**, et c'est un résultat honnête, pas
un échec de recherche.

### 3.3 Conséquence : le candidat n°2 de la Partie 1 est RETIRÉ

Le correctif proposé en Partie 1 ("tué à $19 RT, réel ~$2-4, Δn_tests=0") suppose que le coût
était le facteur liant. Ce n'est **pas** ce que documente le seul enregistrement retrouvable :
le facteur liant est **N=19** (puissance), pas le coût, et le mécanisme pourrait être
économiquement inversé. Changer de véhicule ne répare ni l'un ni l'autre — c'est exactement le
motif structurel identifié par `vehicule/RAPPORT.md:172-201` ("le changement de véhicule répare le
dénominateur, jamais le numérateur"). **Je retire ce candidat de la liste des réouvertures.**

### 3.4 Les vrais dérivés de cette famille (D1-D5) — déjà triés, un candidat authentique trouvé

L'inventaire véhicule (Programme 2) contient les VRAIS successeurs testés (`iter_d2_mr.py`, n_tests
153-160), déjà classés :

| id | famille | kill | reopenable |
|---|---|---|---|
| R022 (D2 VWAP touch fade) | signal directionnellement inversé, IC_t -0.86 | **NON — mécanique** [V] `vehicule/out/inventaire_annote.csv` |
| **R023 (D3 opening-range mid-fade + D5 afternoon BB squeeze)** | échouent individuellement (Sharpe -1.08/-1.32) mais **la combinaison portefeuille + filtre de régime n'a jamais été testée** | **OUI — budget 3-mods, 0 consommé** |

[V] même source, et confirmé par `Futures/research/active/strategy_d/hypotheses_preregistered.md`
Section 1 (D3, D5 pré-enregistrés avec spec gelée, coûts $4 RT / $62.50 RT sur MCL/ZN, corr gate
|ρ|<0.20 vs C). **C'est le seul candidat NQ intraday authentiquement rouvrable** trouvé dans ce
chantier — mais c'est un **NOUVEL ESSAI** (la combinaison portefeuille n'a jamais tourné), pas une
correction : Δn_tests = +1 si exécuté, dans le budget des 3 modifications déjà alloué à
l'hypothèse D.

---

## 4. Corpus crypto (159) et funnel FTMO (164) — passe rapide, confirmé épuisé

### 4.1 Crypto — confirmé, aucune exception mécanique trouvée

13 lignes crypto/perp dans `vehicule/out/inventaire_annote.csv` [V] : R001 (Strategy A, déjà live,
ne pas re-tester), R002 (Strategy B, variante hold≥10j = hypothèse vivante déjà connue), R003
(TSMOM two-sided CFD, mécanique à coût nul), R004 (unlock cliff, sous placebo), R005
(funding-extremes contrarian, mauvais signe — cohérent L50), **R006 (PMR basis, COÛT — plafond
L12 structurel, "non à ce tarif")**, R008 (VRP Deribit, mécanique + coût — vérifié §2.3 ci-dessus),
R025 (Network momentum, univers trop petit). **Aucune de ces 13 lignes ne porte une signature S1-S8
non déjà identifiée par le dépôt.** Le seul "coût" pur (R006) n'a pas de véhicule futures — le
plafond L12 (912 events/an pour 5%/an net à 0.17% RT) est **intrinsèque au tarif d'exchange perp**,
pas un artefact CFD. **Confirmé : β-dominance L11 et plafond L12 tiennent, rien à rouvrir.**

### 4.2 Funnel FTMO (164/162) — déjà ré-audité, ne pas refaire

[V] `funnel_reaudit/RAPPORT.md:8-17,283-303` : **0/162 survivants** sous P1-R1 même pile
entièrement réparée (fuseau EET, coûts, swap, DSR, plancher, type d'ordre). Le seul défaut qui
change des verdicts (fuseau horaire, 5 changements) est un **bruit d'appariement**, pas un filtre —
il tue autant qu'il crée. Le DSR cassé (`framework.py:118`, `std_sr_trials=1.0`) n'a éliminé
**personne qui aurait survécu au DSR sain** (meilleur SR du funnel 0.960 contre seuil sain
2.33/1.09). **Ce travail a déjà été fait rigoureusement — je ne le refais pas** (consigne
explicite de la mission), je le cite comme réponse au chantier D.

---

## 5. Table consolidée — candidats rouvrables, RÉVISÉE depuis la Partie 1

| # | candidat | nature du kill réel | correctif | Δn_tests | statut |
|---|---|---|---|---|---|
| 1 | Commodity TSMOM (Partie 1) | S1 (ETF/roll) + S2 (N=12) | futures, N≥30 | **0 — correction** | maintenu, priorité 1 |
| ~~2~~ | ~~NQ VWAP MR/afternoon~~ | ~~coût~~ **PUISSANCE (N=19), gross introuvable** | — | — | **RETIRÉ (§3.3)** |
| 3 | Equity indices_swing (Partie 1) | S1+S3, l'étude dit elle-même Sharpe 0.45 au coût futures | re-mesurer au coût futures exact | **0 — correction** | maintenu, priorité 3 (plafond sous 0.70) |
| **4** | **R023 — D3+D5 combo NQ (nouveau)** | jamais testé (combo + régime) | exécuter le protocole déjà pré-enregistré | **+1 — NOUVEL ESSAI, dans budget** | à traiter après 1 et 3 |
| **5** | **S035 Gap Pattern (nouveau, watch)** | PUISSANCE (DSR 1.39<1.52, de justesse) **+** decay vs beta récent (0.30<1.02) | vérifier corrélation des cellules de grille (DSR conservateur noté par le fichier source) ; sinon rester fermé | **incertain — priorité basse** | watch-list, pas priorité |
| 6 | Carry cross-asset Koijen 2018 (Partie 1 §4, confirmé §2.2) | jamais testé, S2 (1/6 classes) | nouvelle collecte multi-classe | **NOUVEL ESSAI** | après 1, 3, 4 |

---

## 6. Ce qui n'est PAS recommandé de rouvrir — protège le DSR de la suite

- **Les trois postmortems FX (E, G1, F2)** — chacun tient sur un raisonnement substantif
  indépendant du process qui l'a produit (§1). E a même déjà été re-testé sur véhicule futures et
  meurt une deuxième fois. F2 a déjà appliqué le bon gate dans son propre document.
- **Tout le corpus crypto (159 essais)** — β-dominance L11 et plafonds L12/L13 confirmés
  structurels sur les 13 lignes vérifiées, aucune exception mécanique.
- **Le funnel FTMO (162-164)** — déjà ré-audité intégralement par Programme 1, 0 survivant même
  pile réparée ; ne pas relancer un 3ᵉ passage sans angle vraiment nouveau.
- **VRP Deribit BTC** — construction vérifiée conforme à la pratique retail, kill
  mécanique-économique (ratio coût/gross 200%, 0/13 plis), confirmé fermé.
- **L'ancien candidat n°2 "NQ VWAP MR/afternoon"** — retiré : son kill documenté est la puissance
  (N=19) et une possible inversion de signe économique, pas le coût ; un changement de véhicule ne
  répare aucun des deux.
- **R022 (D2 VWAP touch fade)** — mécanique, signal inversé (IC_t -0.86), fermé.
- **Sector reversal, D4 Lunch RSI, jt_momentum_cs, h31_cs_fs_dn, Pairs/Gatev, Round Number
  Cascade, Momentum de clôture** — kills mécaniques confirmés en Partie 1, non ré-examinés ici
  (hors périmètre des 4 chantiers), rien ne les rouvre.

---

## 7. Limites de cette passe

- **Chantier A (contraste littérature) traité sur 2 mécanismes externes + 1 vérification de
  construction interne**, pas systématique sur les ~15 mécanismes majeurs du registre L11-L60.
  Priorisé sur les cas où la Partie 1 ou les postmortems nommaient déjà un pivot non vérifié
  (Koijen) ou une construction jamais auditée (VRP).
- **Le gross NQ MR/afternoon reste définitivement non retrouvable sans ré-exécution** — c'est une
  limite dure de la donnée persistée, pas un manque d'effort.
- **S035 Gap Pattern (§5, ligne 5)** : je n'ai pas vérifié si le gate DSR du pipeline
  oxfordstrat_109 (`PIPELINE_v2_gates.md`) porte le même bug `std_sr_trials=1.0` que
  `top10_test/framework.py` — le fichier source note lui-même que les essais de la grille ne sont
  "pas indépendants ⇒ DSR conservateur", ce qui pourrait ou non suffire à franchir 1.39→1.52.
  Non tranché ici ; watch-list, pas un chiffre publié.
- **Funding-extremes et autres mécanismes L45-L60** n'ont pas reçu de contraste littérature externe
  dédié dans cette passe (budget de recherche concentré sur A/B/C en premier, D traité par citation
  d'artefacts déjà produits).
