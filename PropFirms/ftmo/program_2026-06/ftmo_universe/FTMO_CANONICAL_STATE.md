# FTMO — ÉTAT CANONIQUE (source unique de vérité)
*MAJ 2026-06-03. À coller en tête de toute session travaillant sur FTMO. Si une session produit un chiffre qui contredit ce document, c'est la session qui a tort — réconcilier avant de continuer.*

---

## VERDICT (une ligne)
**FTMO = CONFIRMÉ-CLOS.** Pas par manque d'effort (~1100 hypothèses testées), mais parce que l'arène n'a pas d'alpha retail accessible. C'est un résultat négatif propre et falsifié — un asset CV, pas un échec. **Ne pas rouvrir sans preuve dure** (voir §6).

---

## 1. LE MEILLEUR ALGO POUR FTMO
**ORB sur NQ / US100 — spec V2+E7.** Opening Range Breakout 30 min, stop = côté opposé de l'OR (1R), exit E7 = trail-to-breakeven après +1R sinon close RTH, filtre V2 = OR ≥ 10 bps, flat overnight, ~1 trade/jour.

> **"Seul survivant" ≠ "bon".** En standalone : Sharpe 0,27, MaxDD −56% à −89%. Deflated Sharpe ~0,70 (échoue le bar 1,0). Ce n'est PAS une stratégie investable. C'est un exploit de barrière : on passe vite ou on buste vite.

Deux causes distinctes de la médiocrité, à ne jamais confondre :
- **Fragilité de régime → mauvais Sharpe.** 6 années sur 16 négatives (2013-16, 2020), edge concentré sur les années qui trendent (2022, 2024). Vrai à n'importe quel coût.
- **Coût → bascule du signe de l'edge.** mean_R si fin que 2 bps de coût le font passer positif→négatif (voir §4). C'est ça qui tue le déploiement réel.

---

## 2. QUEL CHALLENGE : 2-STEP
Le **1-step est PLUS DUR, pas plus facile.** Son daily 3% + DD trailing + règle Best-Day 50% punissent directement le skew positif qui *est* l'edge de l'ORB (~−13 pts de p(pass) rien que par Best-Day). Toujours raisonner 2-step pour l'ORB.

**Règles FTMO 2-step (SETTLED — NE JAMAIS RE-VÉRIFIER) :**
- Cible : +10% Phase 1, +5% Phase 2
- Daily DD : 5% (fixe, du solde initial)
- Total DD : 10% **statique** (floor $9 000)
- Min 4 jours/phase, **AUCUNE limite de temps**

---

## 3. p(pass) ET DURÉE — chiffres honnêtes
**FTMO 2-step, ORB V2+E7, full sample 2010-2026, coût idéalisé 2 bps :**

| Risk/trade | p(funded) | bust | médiane si financé |
|---|---|---|---|
| 1,0% | 34% | 60% | 132 j |
| 1,5% | 33% | 64% | 58 j |
| 2,5% | 32% | 67% | 25 j |

**Lecture critique :** p(pass) PLAT à ~33% quel que soit le sizing. Le résultat est déterminé par le **régime de marché au démarrage** (non chronométrable), pas par la taille. Monter le risque ne change pas la proba — seulement la vitesse de résolution (running → bust plus vite).

**Décomposition placebo :** ~80% de ce 33% = pure math de container (no-bust + temps illimité). L'ORB n'ajoute que ~15-20 pts. **Le levier est la règle, pas le signal.**

**Plafond DP :** le sizing DP-optimal est l'optimum sur TOUTES les politiques → le gap résiduel à 50% est une propriété de l'edge, pas du money-management. Mieux sizer ne remonte pas le plafond.

**Mur Sharpe :** >60% en 1 essai exigerait Sharpe ~1,4 tenu ~6 mois. Meilleur edge robuste de tout le programme = 0,34. Écart facteur ~4, non comblable en price-pattern retail.

**Chiffres flatteurs à rejeter :** 44-52% (régime 2022+ in-sample), "50,9%" (2022-25), "93%" (2026) = tous cherry-pick de fenêtre favorable. Les deux dossiers l'admettent.

---

## 4. LE COÛT — le paramètre qui décide tout (L33)
Le sign-flip entre les 4 anciens rapports n'était PAS un bug : hypothèses de coût différentes sur le même ledger. Grille canonique (`nq_v2_trades.parquet`) :

| Coût RT | mean_R baseline | mean_R E7 | Statut |
|---|---|---|---|
| 2 bps (abstrait) | +0,004 | +0,020 | hypothèse dossiers — non mesurée |
| **3 bps (réel futures direct)** | **−0,018** | **−0,003** | **mort arithmétique** |
| 6 bps (FTMO CFD US100) | −0,085 | −0,070 | mort franc |

**Bascule du signe entre 2 et 3 bps RT.** mean_R<0 ⇒ pas de "durée pour passer" : drift négatif sur barrière symétrique ne converge jamais, il dérive vers le bust.

---

## 5. ITEM OUVERT — le seul (mesure spread US100.cash)
Le coût "2 bps" des dossiers était une **hypothèse, jamais une mesure.** Specs FTMO US100.cash confirmées par capture broker :
- **Commission = 0%** → 100% du coût = **spread flottant** (non mesuré)
- Swap long −662,4 / court +28,58 (asymétrique, L30) → **non pertinent ORB** (flat overnight)

**Protocole de mesure (compte démo, ~5 sessions, 20 min/jour) :**
- Ouverture cash US = **16:30 EET** (broker) = **~15:30 Paris (CEST)**. Vérifier le décalage sur l'horloge MT5.
- Logger le spread **en points** à : 15:30:00 (auction, pire cas), 15:33, 15:35, + réf 16:30 (calme).
- Conversion : bps_RT = (spread_points / 21500) × 10000 × 2. Ajouter le slippage market order à l'open.
- **Seuil de mort : ~3 points cumulés (spread+slippage) RT ⇒ mean_R<0 ⇒ FTMO US100 mort par mesure.**

Cette mesure ne valide PAS la stratégie — elle transforme une estimation en mesure et boucle le NO-GO définitivement. Statut attendu : confirme le NO-GO (commission 0 + spread flottant CFD = profil 6-10 bps estimé).

---

## 6. CONDITIONS DE RÉ-OUVERTURE (≈ 0)
Rouvrir FTMO/ORB SEULEMENT si TOUTES réunies :
1. Firme 1-step futures-direct + DD static + cible≤DD + no daily + no consistency → **n'existe pas 2026-06**
2. Coût all-in ≤ 2 bps **confirmé sur 60+ trades démo**
3. Edge OOS **post-2026** (pas 2022-24 in-sample post-hoc)
4. DSR > 1,0 avec mod-count L10-compliant (actuel : 0,70 / 8 mods — **à re-vérifier contre le journal**)

---

## 7. CE QU'ON BANQUE (CV / journal)
- **L33** — l'instrument réel (sa structure de coût), pas le signal, décide si un exploit de barrière vit. Backtest 2 bps ne transfère pas à un CFD 6-10 bps.
- **L34 (proposé)** — checklist d'honnêteté prop-firm : 1 ledger canonique + coût réel + spec gelée + full-sample regime. Quand les 4 sont réunis, plus de sign-flip.
- **L35 (proposé)** — DP-optimal = ceiling, pas heuristique. Money-management n'est pas le levier.
- **Placebo** — ~80% du p(pass) = math no-bust × temps illimité, pas signal.

---

## 8. DÉCISION / ALLOCATION
- **Ne pas allouer de cycles à FTMO.** Confirmé-clos.
- **Cycles → A→BreakoutProp** (vrai edge +EV, Sharpe ~1,33) + personal book (A crypto, B delta-neutral mainnet pending).
- Make-or-break BreakoutProp (inchangé) : est-ce que son daily DD encaisse la DD intra-semaine naturelle de A (le facteur exact qui a breaché Propr à 3%) ?

---
*Ne pas mélanger les chiffres de specs différentes (V2+E7 two-sided vs long-only filtré doc3). Honnêteté > optimisme. Réconciliation > régénération. Si doute sur un chiffre : retour à ce document.*

---

## RÉCONCILIATION 2026-06-10 — Mission "portefeuille 6 mois" (`data/ftmo_portfolio/REPORT.md`)

**Ce qui change (par MESURE, pas par opinion) :**

1. **§5 ITEM OUVERT : CLOS PAR MESURE — dans le sens INVERSE de l'attendu.** Spread US100.cash à
   l'auction 15:30 CET mesuré sur 518 jours (M1 calibré 2024-2026) : **0.47-0.55 bps médian, p95
   0.64** — pas 6-10 bps. Coût ORB all-in ≈ 1.5-1.6 bps RT ⇒ mean_R(V2+E7) = **+0.0305** (n=4013),
   encore positif à 2.5 bps. La condition de réouverture #2 est remplie par mesure (caveat : feed
   FTMO à confirmer en démo avant capital). L'ORB redevient un sleeve d'appoint légitime (SR ~0.40
   full), PAS un véhicule standalone.
2. **§3 p(pass) : le mur a bougé mais tient à 6 mois.** Portefeuille 4 sleeves (or trend, J1,
   overnight midweek, ORB) + governor (cap notionnel 1.5×, breaker M5, taper incl. ORB, pacing) +
   coûts réels + règles exactes + quantization $10k :
   **38.1% [IC95 25-49] à 6 mois (retries incl.)** ; 24% (2013-19) / 53% (2020-25, design-OOS) ;
   **56% à 18 mois**. Le plafond mono-stratégie ~33% (sans horloge) est dépassé par le portefeuille
   sous une contrainte PLUS dure — mais **>50% à 6 mois reste falsifié** (borne IC95 < 50%).
3. **J1 : le swap modélisé (^IRX, +0.175 SR) était optimiste** — aux swaps broker réels (calibrés
   sur specs juin 2026, variables avec les taux), le swap J1 est un léger COÛT net cumulé. J1 tient
   à SR ~0.43 full / 0.42 récent quand même (le timing porte l'edge, pas le carry).
4. **Négatifs re-confirmés aux coûts réels** : FX multi-paires (même swap-gated), equity trend,
   énergie long-only-avec-crédit, crypto trend (décayé 2019+ ≈ 0 cumulé), softs (spreads 144-1190 bps).
5. **Leçons nouvelles** : buffer flottant (ne PAS réaliser quotidiennement sous daily ancrée
   balance : bust 11→17.5% sinon) ; cap notionnel obligatoire sous vol-targeting cascadé (p95
   2.85×/max 9.6× sinon) ; retry-paradox (minimiser les busts tue l'optionalité des retries) ;
   l'horloge externe coûte plus que la barrière (38%→56% en relâchant 6→18 mois).

**Verdict canonique mis à jour : FTMO 2-step reste CLOS pour un mandat "p>50% en ≤6 mois, 1 compte".
Il est OUVERT pour un mandat patient (~56% à 18 mois, retries) ou comme pari à ~38% par fenêtre de
6 mois, aux pré-conditions de mesure démo près. Toute itération supplémentaire exigerait du mining
frais (interdit par la charte) ou un autre container.**

### Amendement itération 2 (2026-06-10 soir, mandat ML — REPORT.md §9)

- **Règle d'abandon** (zombie ≥8j sous floor+2% ⇒ relancer) : les "timeouts" étaient pour moitié des
  zombies policy-induits (médiane −8.9%, épinglés par le taper). Fix structurel : **+12 pts**.
- **p(funded ≤6mo) = 50.2% IC95 [35.6 ; 63.1]** (IS 35.7 / OOS-design 65.5 ; stress 46-47% ;
  12 mois : 69.5%). **La barre des 50% est atteinte au point estimate, pas avec confiance (P=0.46).**
- ML : 4 falsifications propres (meta-label ORB foreclos par le bughunt F1 hérité ; ledgers breakout
  = artefact de fill ; vol-governor < baseline naïf ET overlay négatif ; start-gate ≈ bruit ;
  VIX-skip incohérent). **Le gain est venu du diagnostic, pas de la prédiction.**
- Leçon candidate : **L-zombie** — sous barrière statique + horloge, tout taper protecteur doit être
  couplé à une règle d'abandon, sinon il convertit des busts retry-ables en morts lentes.

### Amendement AUDIT (2026-06-10, nuit — AUDIT.md)

- **Le 50.2% est RÉTRACTÉ.** Audit risk-quant : (F1 CRITIQUE) US100 M1 = 1 bar/jour sur 2018-2020
  (GER40 : mi-2019→2021) → breaker/règle daily aveugles intraday 3 ans → IS gonflé de +9.2 pts ;
  corrigé par proxy NQ databento + masquage GER40. (F2) Coût ORB d'époque (auction 4.3 bps en 2013
  vs 0.5 en 2024) → mean_R ORB 2013-19 réel = −0.057 ; corrigé. **Headline audité : 45.8%
  [30.6 ; 58.9], IS 25.5 / OOS 67.1.** Causalité (delay-test funnel, anticausal plat), comptabilité
  (forensique swaps/avg-price), et sélection de composition (contrefactuel crypto OOS-neutre) : PASS.
- Leçons : **L-data-blind-rules** — un trou de granularité ne biaise pas que les signaux : il rend
  les règles de risque invisibles en sim (busts non détectés = pass fictifs). Auditer la COUVERTURE
  INTRADAY par année avant tout claim de barrière. **L-era-costs** — tout coût mesuré "récent"
  appliqué uniformément à l'histoire fabrique de l'edge dans les ères chères.

### Amendement SPRINT 2 MOIS (2026-06-10, nuit — REPORT.md §10) — LE MUR EST TOMBÉ

- Mandat p>50% en 61 jours → **design de variance séquencée** (vm 14, P2 ×1.2 chaude, abandon 5j,
  breaker M5, retries) sur stack audité : **59.5% IC95 [51.7 ; 67.2], P(p>50%)=0.99**, IS 59.1 /
  OOS 60.0 (zéro décay), stress 54.7-58.4%. Parallèle 2 comptes (corr mesurée 0.08) : **80.6%**.
- **Le même design sous 6 mois : 90.9%** — l'ancien plafond ~33-46% était un artefact du PARADIGME
  (grind de drift + protection anti-bust). Sous barrière symétrique + cible asymétrique P2 + retries
  bon marché + horloge, **l'optimum est fail-fast à haute variance** : le container porte ~47 pts
  (placebo anti-edge mesuré), l'edge réel +12 pts.
- **MISE À JOUR DU VERDICT CANONIQUE : FTMO 2-step est OUVERT** — pas par découverte d'alpha, mais
  par ingénierie de barrière mesurée honnêtement. Réserves de déploiement : clause 7.3 (style
  agressif), slippage à ~20× à mesurer en démo, brutalité psychologique (~65% des essais meurent).
- Leçons : **L-variance-vs-drift** — sous (barrière, horloge, retries), maximiser p(franchir) ≠
  maximiser SR : à edge faible, la politique optimale est la variance maximale contrôlée par les
  règles, pas le drift. **L-mandate-shapes-design** — le mur des 6 mois n'est jamais tombé tant que
  le mandat n'a pas FORCÉ l'abandon du paradigme prudent ; re-deriver la policy depuis la fonction
  objectif à chaque changement de mandat.


### NOTE DE RÉOUVERTURE FORMELLE v2.1 (2026-06-10 — appliquée depuis CANONICAL_AMENDMENT_PENDING.md, bloquée à l'origine par dossier non monté ; exigée par le contre-audit équipe v2.1, point 6)

Le verdict « CONFIRMÉ-CLOS, ne pas rouvrir sans preuve dure (§6) » a été levé dans ce cycle sous :
(a) **mandat MD explicite** (portefeuille multi-sleeves, horloges 6→3 mois, ML autorisé) ;
(b) **condition de réouverture #2 partiellement satisfaite PAR MESURE** : spread US100 à l'auction
mesuré 0.5 bps (518 jours M1), puis swaps/marges validés au terminal MT5 démo (modèle ±10%) —
le démo-60-trades reste un gate de déploiement, re-spécifié v2.1 : slippage ACTIF sur fills
16:00-16:30 Paris, ≥60 trades, logs commitées ;
(c) **changement d'objet** : v2.1 établit que le headline challenge ne repose PAS sur l'ORB
(compteur de jours ; P&L = −2.6 pts ; deadlock min-trading-days patché par token-trade) mais sur
l'overnight (+12.1 pts d'ablation iso-reste) + le séquencement variance/retries.

Les conditions #3 (OOS post-2026) et #4 (DSR>1 au niveau challenge) restent NON satisfaites au
sens strict — statut canonique : **« OUVERT SOUS CONDITIONS, v2.1 »**, pas « prouvé ».
Chiffres contractuels v2.1 (mono-stack, regen_all.py) : challenge pooled **84.8%** (IS 86.7 /
OOS 83.0), valeur funded **$1,204**, **EV +$699/campagne** ; plancher pessimiste si ORB mort au
coût réel : ~87% (token) / extraction $1,262 / **EV +$295**. Caveat ouvert : DSR 0.29 de la
sélection midweek overnight (grille 40 cellules) — sensibilité all-nights à trancher avant
signature. Conforme : réconciliation > régénération.

### Amendement v2.2 (2026-06-10, soir) — RÉOUVERTURE DOCUMENTÉE : audit BLOCKED + re-run contractuel

- **Audit indépendant clean-room du rapport v2.0** (`data/ftmo_portfolio/audit_v2_independent/`,
  claims C01-C40) : verdict **BLOCKED** — le cœur computationnel reproduit (pooled 84.6 vs 83.5,
  funded $2,632, replay avril exact) mais (F-A1) **deadlock simulateur côté cible** : balance>+10%
  avec <4 jours ouvrés ⇒ aucun trade ne s'ouvre plus ⇒ timeout AU-DESSUS de la cible ; le posting
  ORB quotidien non-gaté était l'unique échappatoire (« ORB off » → p 3.5%) ; (F-A2) le P&L de
  l'ORB COÛTE ~3.7 pts au challenge (flag-only 87.7 > 83.5) et l'échelle de coûts 1.5→6 bps laisse
  p à 84-87% — la « résurrection par mesure de spread » ne porte PAS le headline challenge ;
  (F-A3) l'EV funded dépend de l'ORB à coût moderne non vérifié (extraction −52% si mort) ;
  (F-A4) chiffres secondaires v2.0 périmés (182j/270j/swap×1.5/médianes/SR ORB full/EV $1,342-vs-$1,453).
- **v2.2 = re-run contractuel à UN changement gelé** (`data/ftmo_portfolio/v22/`) : challenge
  ORB-OFF + **MICRO-ORB** compteur de jours (0.01 lot, entrée canonique 16:05-16:10, P&L modélisé,
  posé si rien d'ouvert à 21:30) ; funded inchangé, coût ORB **paramétré** (`ORB_RT_BPS`).
  **Chiffres contractuels : challenge IS 90.6 / OOS 83.4 / pooled 87.0 [82.3;91.6] (N_eff 174) ;
  CDF 41.6/70.3/87.0/98.9/100.0 monotone ; funded IS $684 / OOS $2,632 ; VAL re-dérivée $1,422 ;
  EV +$926/campagne ; placebo edge +15.8 pts ; anticausal −3.9 (pas de leak) ; pathboot 78
  histoires min 71.4 P(>50%)=100%.**
- **Réconciliation des conditions de réouverture (§6)** : telles qu'écrites, elles gataient
  l'ORB-comme-edge. v2.2 retire l'edge ORB du challenge → le claim challenge ne repose plus sur
  AUCUNE des 4 conditions ; il repose sur l'ingénierie de container (retries + abandon + variance,
  placebo 71 pts) + le book 3 jambes, audités en clean-room. La condition #2 (coût ≤2 bps confirmé
  sur 60+ trades démo, fills ACTIFS 16:00-16:30) reste VIVE mais gate uniquement le sleeve ORB
  FUNDED via `ORB_RT_BPS` (EV +$926 → ≈ +$745 @3bps / ≈ +$310 si mort — jamais négative).
  Les conditions #1/#3/#4 sont sans objet pour le book challenge v2.2.
- Gates live inchangés (audit) : test swap overnight EN COURS ; démo 3 semaines ; EA MT5 +
  réconciliation ; budget 4+ fees ; clause 7.3. **Le statut opérationnel reste : OUVERT
  conditionnel aux gates live — aucun lancement avant leur passage.**

### Amendement v2.2-résidus (2026-06-10, clôture) — §9 RAPPORT_MESURE re-scopé + branches exactes

- **§9 du RAPPORT_MESURE_us100_execution_cost_v1 AMENDÉ** (fichier hôte hors repo — amendement
  canonique : `data/ftmo_portfolio/v22/AMENDEMENT_RAPPORT_MESURE_s9.md`, à insérer verbatim à la
  synchro) : **branche kill (>1.5 bps → ORB off) RETIRÉE**, re-scopée par 605f4a4 — l'ORB ne peut
  plus tuer le challenge (insensible par construction, ancres non-régression en garde). Le verdict
  N=60 = valeur d'`ORB_RT_BPS` + re-run section funded ; EV rapportée à la valeur mesurée. Aucun
  ré-ancrage avant N=60 (règle pré-enregistrée maintenue, era = défaut jusqu'au 15/06).
- **Branches N=60 re-calculées EXACTES sur ledger** (ftmo_research/ monté — le rerun pendant de
  PORTFOLIOS.md est fait ; approximation équipe validée à +0.3%) : 0.61 bps → funded OOS $2,897,
  EV +$1,125 ; 1.0 → $2,807, +$1,063 ; 1.5 → $2,578, +$965 ; era → $2,632, +$926 ; ORB-mort →
  $1,262, ≈ +$295-310. **L'EV est positive sur tout le domaine de mesure.**
- vm sweep v2.2 vérifié (résidu #1 du contre-audit) : provenance fraîche confirmée (colonne micro,
  n=462) ; granularité complétée vm13 86.2 / vm15 87.7 → **plateau lisse autour de vm14 (87.0)**,
  voisins ±2-4 vm à −2.4/−3.2 pts, TOUS les deltas appariés CI95 ⊃ 0 — pas de knife-edge, pas de
  chiffre hérité.
