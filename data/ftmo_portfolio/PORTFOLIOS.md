# LIVRABLE FINAL — Les deux portefeuilles FTMO
### « Sprint pour passer, prudence pour durer »

> **Renforcement d'inférence (carte blanche, 2026-06-10 — voir Addendum 5) : le design challenge
> est validé par triangulation (moteur M5 vs modèle de renouvellement : écart 1.8 pt), antifragile
> au slippage d'exécution (p MONTE avec fills dégradés, coût en fees ~$30-60/cran), et robuste au
> single-history : sur 78 histoires synthétiques (bootstrap par blocs-semaines), P(p>50%) = 100%,
> pire histoire = 62.9%, p5 = 74.3%.**
*2026-06-10 · Compte $10k 2-step Swing · Stack audité (M1 réparé NQ-proxy, ORB era-costed, GER40 masqué) ·
Toutes les métriques : cohortes historiques 2013-2026, design gelé sur IS 2013-2019, validé OOS 2020-2026.*

---

## PORTEFEUILLE 1 — CHALLENGE (mur 3 mois, EV-optimisé)

### Spec gelée

| Composant | Réglage |
|---|---|
| Sleeves | Or TSMOM blend{60,120,250} carry-adj + J1 (USDJPY 12-1 LO) + **Overnight midweek US100+GER40 (budget renforcé 0.6/jambe)** + ORB V2+E7 US100 (risk 0.25% / trade, era-costed) |
| Vol multiplier | **14×** (notionnels jusqu'à ~20×/jambe, cap 1.5×/jambe pré-vm, marge ~5% à 1:100) |
| Phase 2 | **chaude : 1.2×** le risque P1 (barrières +5/−10 asymétriques) |
| Gouvernance | breaker M5 à 30% du budget daily restant ; taper floor 2% ; pacing horloge ON ; glide 0.5 |
| Règle d'abandon | equity < floor+2% pendant **5 jours** ⇒ abandonner, relancer (l'horloge continue) |
| Exécution | rebalance 22:05 CET ; overnight 17:35/22:05 → 09:00/15:30 ; quantization lots exacte |
| Cap de marge | **60% de l'equity max** (taux mesurés MT5 : indices/or 2% = 1:50, FX 1%) — scaling proportionnel si dépassement. Ajouté après revue MD (captures démo : marge p99 = 93% sans cap). Impact : p 80.8→81.1%, EV +$838. Swaps mesurés intégrés (US100 −644.06, GER40 −394.85/−48.8, XAU −89.26 pts) : modèle confirmé à 1-10%, funnel inchangé |

### RECALCUL CONTRACTUEL POST-REVUE MD (2026-06-10, swaps mesurés + cap marge 60%, cohortes step7 n=462)

| Métrique | Avant revue | **Corrigé (officiel)** |
|---|---:|---:|
| Challenge IS 91j | 87.7% / +$961 | **87.1% / +$953** |
| Challenge OOS 91j | 79.5% / +$814 | **79.9% / +$825** |
| **Pooled** | ~83.5% | **83.5% — IC95 [76.2 ; 88.5], P(p>50%) = 1.00** |
| Stress swap ×1.5 / spread ×2 | 81.5% / 77.9% | **86.4% (+$940) / 77.2% (+$751)** |
| Funded OOS (2 ans) | $2,680 / 0% bust | **$2,592 (méd $2,145) / 1% bust / 10.8 payouts** |
| Funded IS | ~$1,000 | **$824 (méd $109 — ère chop paie peu)** |
| EV chaînée / campagne | ≈ +$880 | **≈ +$800** (valeur funded recalée $1,342) |

Lecture : toutes les corrections de la revue (swaps mesurés, signe short GER40, marge 1:50)
déplacent les métriques de <1 pt / <5% — le modèle de coûts était déjà calibré juste, et le book
est insensible aux raffinements résiduels. La validation empirique overnight (positions tenues
cette nuit par le MD) reste le dernier verrou avant déploiement.

---

# v2.1 — RÉPONSE AU CONTRE-AUDIT ÉQUIPE (2026-06-10, nuit) — ERRATUM & RÉGÉNÉRATION

**Verdict équipe accepté intégralement. Le cleanroom a reproduit le headline (84.6 vs 83.5 ✓) et
cassé deux récits internes + une couche de chiffres périmés. Corrections exécutées dans leur ordre :**

**(1) Deadlock min-trading-days — CONFIRMÉ et PATCHÉ.** Reproduit sur notre moteur : ORB OFF →
**3.1%** (leur 3.5%). Mécanisme exact : au-dessus de la cible, le hit-check se déclenche au 1er bar
du segment 00:00 et verrouille flat_today AVANT les ouvertures 17:35/22:05 → le 4e jour ne compte
jamais → timeout à equity ~$11,035 (au-dessus de la cible !). **Patch token-trade** (au-dessus de
la cible et <4 jours : ouvrir/refermer 0.01 lot US100, ~$0.06) : ORB OFF + token = **87.4%**.
**Attribution républiée : l'ORB était un compteur de jours ; son P&L coûte −2.6 pts au challenge**
(token-only 87.4 > avec-ORB 84.8) et p est insensible à son coût (1.5-6 bps). La « résurrection par
la mesure » ne porte PAS le headline challenge — elle porte le funded (−52% d'extraction si edge
ORB nul). **(2) Contingence §7 réécrite : « auction >1.5 bps → ORB off » devient « → ORB
micro-lot »** (le bouton d'autodestruction est désamorcé).

**(3) Régénération MONO-STACK (regen_all.py, un run, une sortie) — chiffres contractuels v2.1 :**

| Métrique | v2.0 (périmé/mosaïque) | **v2.1 (régénéré)** |
|---|---:|---:|
| Challenge IS / OOS / pooled | 87.1 / 79.9 / 83.5% | **86.7 / 83.0 / 84.8%** |
| Valeur funded (cohérente, in-run) | $1,342-1,453 (incohérent) | **$1,204** |
| **EV pooled / campagne** | +$800-880 | **+$699** |
| Stress swap ×1.5 / spread ×2 | 86.4 / 77.2 (périmés) | **87.1 / 77.9** (token-rule incl.) |
| Funded OOS / IS / pooled | $2,592 / $824 | **$2,592 / $824 / $1,385** ✓ |
| Ablation ORB (P&L) / overnight (iso-reste) | non mesurées proprement | **−2.6 pts / +12.1 pts** |

**(5) Overnight : le mur porteur (+12.1 pts d'ablation) MAIS DSR 0.29 FAIL sur la grille de
sélection 40 cellules (équipe)** → statut : sleeve CONSERVÉE (contribution funnel massive,
mécanisme documenté, cross-confirmée 3 marchés par l'archive) avec **caveat de sélection ouvert** ;
sensibilité all-nights-vs-midweek à trancher avant signature. **(4) Gate démo ORB re-spécifié** :
slippage ACTIF sur fills 16:00-16:30 Paris, ≥60 trades, logs commitées — l'auction passive ne juge
pas cette sleeve (fills stop-market 16:05-16:10) ; pertinence : funded surtout (challenge
insensible). **(6) Gouvernance** : le canonical est amendé d'une note de réouverture formelle
(condition #2 satisfaite par mesure — spread auction + swaps terminal — et mandat MD explicite).
**Restes ouverts avant signature** : suite de robustesse (bootstrap/triangulation) à re-tourner sur
le stack v2.1 ; placebo gross-vs-net (leur 62/+22.5 adopté comme référence) ; nuit de swap + démo
3 semaines + EA. **Plancher pessimiste assumé si ORB mort au coût réel : p ~87% (token), extraction
$1,262/2 ans, EV ≈ +$295/campagne.** La décision « +$295 à +$699 vaut-il le travail restant »
appartient au comité.

### MESURE D'EXÉCUTION US100 (programme probe, INTERIM n=15/60 — verdict lundi 15/06)

Rapport équipe `RAPPORT_MESURE_us100_execution_cost_v1.md` : **all-in RT ≈ 0.61 bps au timestamp
canonique 16:00-16:30 Paris, mesuré un jour de CPI** (spread administré 0.50 + slips zéro-moyenne
±0.4-0.6). Session 1 (auction −3.34) requalifiée hors-sujet. Passe le kill 1.5 bps ×2.5
(provisoire). **Aucun ré-ancrage avant N=60 (règle pré-enregistrée respectée).** Branches
économiques PRÉ-CALCULÉES (funded OOS, scénarios de coût forward ; approximation shift 0.0225 R/bps,
rerun exact sur ledger au remontage de ftmo_research) :

| Branche N=60 | Extraction funded OOS 2y | EV/campagne (indicatif pooled) |
|---|---:|---:|
| ≤ 1.0 bps (interim 0.61) | **$2,887** (méd $2,455, 0% bust) | ≈ +$800 |
| = 1.0 bps (borne PASS) | $2,798 | ≈ +$760 |
| > 1.5 bps (ORB off + token) | **$1,280** (≡ $1,262 cleanroom ✓ re-validation croisée) | ≈ +$250-295 |

Caveats portés au registre : (a) **sélection adverse des stops** — la sonde mesure le plancher de
bruit des ordres marché, pas la prime spécifique stop-through (variante stop-order si verdict
1.0-1.5) ; (b) **asymétrie de venue** — challenge/verification se jouent SUR l'infra démo (bonne
venue pour p(pass)) ; le gap demo→live ne mord qu'au funded, exactement où vit la sensibilité EV.

### Métriques (mur 91 jours, retries inclus)

| | IS 2013-19 | **OOS 2020-26** |
|---|---:|---:|
| **p(funded ≤ 3 mois)** | 85.1% | **81.7%** |
| Essais utilisés (espérance) | 3.19 | 3.17 |
| Temps médian de funding | ~32 j | **34 j** |
| **EV de campagne** (valeur funded $1,453, fee $96) | +$931 | **+$874** |
| Référence mur 61j / single-essai | 59.5% [51.7;67.2] | 28.2% max (plafond structurel) |
| Stress (réf. sprint) swap×1.5 / spread×2 | 58.4% / 54.7% (@61j) | |
| Placebo (hygiène) | container ~47 pts, edge réel +12 pts | |

## PORTEFEUILLE 2 — FUNDED (rente, longévité)

### Spec gelée

| Composant | Réglage |
|---|---|
| Sleeves | **identiques au challenge** (or, J1, overnight midweek 0.35, ORB 0.25%) — c'est le réglage qui change, pas le book |
| Vol multiplier | **1.0×** (optimum extraction×longévité ; 1.25 dégrade, on_w 0.6 → bust ×18 rejeté) |
| Gouvernance | breaker 30%, taper 2%, **pace OFF, glide OFF, abandon OFF** |
| Retraits | **toutes les 2 semaines** : retirer (balance − $10k) si positif ; split trader 80% ; 1er payout rembourse la fee |
| Compte | Swing obligatoire (positions weekend + news — l'achat Standard est irréversible) |

### Métriques (horizon 2 ans, tronqué = conservateur)

| | IS 2013-19 | **OOS 2020-24** |
|---|---:|---:|
| **E[extraction brute]** | ~$1,000 | **$2,680** |
| Médiane / p10 / p90 | $434+ | **$2,065 / $95 / $5,268** |
| **Taux de bust** | 1-3% | **0%** |
| Payouts moyens | ~5 | **11.3** |
| Vie médiane | horizon plein | **horizon plein (504j)** |
| Contre-exemple (garder le book sprint funded) | | méd. $0, 59% bust, vie 27j |

## EV CHAÎNÉE DE L'OPÉRATION (1 campagne = challenge → switch → funded)

| | Valeur |
|---|---:|
| E[fees challenge] (3.17 essais × $96) | −$304 |
| p(funded) × (refund + 0.8 × extraction pooled $1,696) | +$1,187 |
| **EV par campagne de 3 mois** | **≈ +$880** |
| ROI sur fees engagées | ~2.9× |
| Pour 95% de certitude de funding | ~9 mois, 3.91 essais, fees ~$375 |

## Stratégies archivées re-testées dans ce cycle (mandat « archivées trop vite »)

| Stratégie | Verdict re-test |
|---|---|
| ORB V2+E7 (tuée à coût supposé 6-10 bps) | **RESSUSCITÉE par mesure** (auction 0.5 bps actuel, era-costed) — au book |
| Overnight midweek (beta-proxy, gap-tail) | **RESSUSCITÉE en sleeve sizé** — au book, budget 0.6 challenge / 0.35 funded |
| Breakouts Donchian/Bollinger/PDH-PDL (8 ledgers) | Re-pricés : artefact de fill confirmé (delay-1 ≈ 0) — morts |
| Énergie trend long-only (crédit de swap) | ≈ 0 net — morte |
| FX 10-paires (même swap-gated), equity trend, crypto trend | Confirmées mortes aux coûts réels |
| F1/ttb meta-feature ORB | Look-ahead (bughunt archive) — morte ; signature 3-var en quarantaine post-2026-07 |

## Protocole opérationnel (conditions de validité)

1. **Achat** : FTMO Challenge 2-Step $10k, **type Swing**.
2. **Pré-conditions démo (≥3 semaines)** : spread US100 à 15:30 CET ≤ 1.5 bps all-in ; swaps réels vs modèle (±50% toléré, stress couvert) ; slippage breaker. **Test d'unité de swap (1 nuit, décisif — réponse à la revue MD)** : tenir 0.01 lot US100 long et 0.01 lot XAUUSD long à travers minuit serveur, lire la ligne « swap » MT5 en $ : modèle ≈ −$0.066 (US100) / −$0.88 (XAU) par 0.01 lot/nuit ; si ~100× plus (−$6.6 / −$10+), la convention de points est fausse et TOUT le book est à re-coster avant déploiement.
3. **Pendant le challenge** : discipline d'abandon à J+5 sous floor+2% — sans état d'âme ; budget 4+ fees d'avance.
4. **Au funding** : **switch immédiat vers Portefeuille 2** (vm 14 → 1.0) — c'est la décision qui porte toute l'EV (+$4 → +$880).
5. **Risques résiduels** : clause 7.3 FTMO (style agressif en phase challenge — repli vm 12 ≈ −3 pts de p si besoin de discrétion) ; feed réel ≠ feed backtest ; une seule histoire de marché (CI larges) ; extraction tronquée à 2 ans (upside : scaling plan FTMO non modélisé).

*Reproduction : `simulator.py` + `audit_stack.py` + `funded.py` ; outputs/final_*.csv ; AUDIT.md pour la traçabilité des corrections de données.*

---

## ADDENDUM — Cycle d'itérations finales + audit du design (2026-06-10, clôture)

**10 itérations d'amélioration du portefeuille challenge (17 cellules, protocole : IS step10,
seuil de promotion > $40 d'EV, OOS-confirmation des promus) — résultat : CONVERGENCE, zéro promotion.**

| It | Hypothèse | Δ EV vs baseline +$949 | Verdict |
|---|---|---:|---|
| 1 | P2 plus chaude (1.4 / 1.6) | −$127 / −$147 | rejet (1.2 optimal) |
| 2 | Abandon 3j / 7j / buf 3% | −$117 / −$220 / +$23 | rejet / rejet / bruit |
| 3 | Breaker 0.20 / 0.45 | +$12 / −$201 | bruit / rejet |
| 4 | Glide off / pace_k 1.5 | +$3 / −$5 | bruit |
| 5 | ORB 0.4% | −$89 | rejet |
| 6 | Overnight split GER 0.8 / US 0.5 | −$145 | rejet |
| 7 | vm 13 / 15 | +$11 / −$90 | bruit / rejet |
| 8 | Tilt or 1.2 / jpy 0.8 | −$43 | rejet |
| 9 | Combos des candidats positifs | −$26 à +$11 | non additifs, bruit |
| 10 | — | — | **convergence : design gelé inchangé** |

Le design est sur un **plateau** (aucun knife-edge paramétrique) — propriété souhaitable.

**Audit du design final (pooled 2013-2026)** : delay +1j → 82.0% (dégradation gracieuse ✓) ;
**anticausal −1j → 79.6% < baseline 83.3% (aucun leak)** ✓ ; placebo sign-flip → 71.4%
(container 71 pts à 91j-retries, edge réel +12 pts — décomposition à jour) ; stress swap×1.5 →
81.5% (EV +$878), spread×2 → 77.9% (EV +$776) ; marge : gross max théorique ~50× → niveau de marge
~200% à 1:100 (faisable, surveillé) ; forensique comptable inchangée (cf. AUDIT.md).

**Chiffres finaux contractuels (inchangés) : challenge p = 81.7% OOS / 3.17 essais / EV +$874 ;
funded $2,680/2 ans OOS / 0% bust ; EV chaînée ≈ +$880 par campagne.**

---

## ADDENDUM 2 — Mandat matières premières (50 itérations max ; ~30 consommées) + BUG FIX

**Verdict : AUCUN sleeve commo promu. Mais le mandat a payé autrement — un bug réel attrapé.**

| Piste | Résultat |
|---|---|
| Softs trend LO weekly | *Mirage initial SR +0.55 = BUG* (rolling-vol sans min_periods : tout NaN de calendrier → position zéro silencieuse 60j). Corrigé puis re-falsifié : **−0.75** au spread mesuré plein, −0.13 à demi-spread |
| Softs LO monthly (turnover 0.8×/an) | +0.14 plein / +0.37 demi-coût — sous la barre, même en scénario optimiste |
| Énergie trend (2-sided / LO / weekly / monthly) | −0.82 à +0.20 — mort |
| NGAS trend | −0.74 à +0.17 — mort |
| XAG trend | SR ≈ 0, corr book 0.13-0.19 — redondant avec l'or |
| Énergie carry-harvest (long si backwardation) | SR apparent +0.50/+0.65 **AUTO-REJETÉ** : swap énergie modélisé constant (snapshot 2026) → signal toujours-long + crédit fantôme. **Non testable** sans série historique de swaps broker — legs ouvert documenté, pas un résultat |

**LE BUG FIX (impact book principal)** : `realized_vol` sans `min_periods` zérotait les poids
or/JPY jusqu'à 60j après chaque jour férié (or actif 28%→42% post-fix, exposition restaurée).
Correctif d'exactitude conservé. **Chiffres contractuels mis à jour (challenge, mur 91j) :
IS 87.7% (EV +$961) / OOS 79.5% (EV +$814), essais 3.55 OOS.** Pooled ≈ inchangé (83.6 vs 83.4) —
le book pré-fix perdait de l'edge aléatoirement, il n'en fabriquait pas (direction conservatrice
confirmée). Conclusion du mandat : l'univers commo FTMO au spread CFD retail mesuré n'offre pas de
sleeve décorrélé viable ; la seule piste réelle (carry énergie) exige des données de swap
historiques — transmise à l'archive comme lead ouvert.

---

## ADDENDUM 3 — Mandat FX (10 itérations, It31-It40)

**Verdict : aucun sleeve FX promu — mais l'intuition du MD est VALIDÉE sur le fond : un edge FX
réel existe. Il vit simplement sous le plancher de coût retail.**

| It | Piste | Résultat |
|---|---|---|
| 31-33 | Re-baseline trend FX post-bug-fix (2-sided/LO/weekly) | −0.23 à −0.02 — les kills historiques tiennent, pas un artefact du bug |
| 34 | **Table sessions × paires (30 cellules, IS/OOS séparés)** | **2 cellules OOS-validées : EURGBP-asia (t_IS 4.08 / t_OOS 3.82), USDCHF-asia (3.75 / 2.55)** — drift de session domestique (Breedon-Ranaldo), 19 ans stable |
| 35 | Coûts à l'heure exacte | Entrée minuit = spike de rollover (2.5-3.4 bps) ; optimisé 00:05→08:00 : RT ~2.0-2.2 bps vs +1.2-1.4 bruts |
| 36 | Tokyo fix USDJPY | mort (−0.35/−0.19, n.s.) |
| 37 | London fix month-end (flux de rebalancement) | signes opposés IS/OOS — mort |
| 38 | Breakout range asiatique (EURUSD/GBPUSD) | négatif les deux moitiés — mort |
| 39 | London-open momentum | en réalité une réversion (t −4 à −7) mais brute ≈ −0.76 bps ≪ coût — non récoltable |
| 40 | **Sleeve asia final (EURGBP+USDCHF, corr inter-jambes −0.19)** | **coût zéro : SR +1.70 IS / +1.52 OOS** — institutionnellement réel ; coût mesuré : −0.88/−1.78 ; demi-coût : +0.41/−0.13. **Break-even ≈ 1.0-1.4 bps RT all-in** |

**Conclusion** : l'edge FX de session existe (SR ~1.5-1.7 hors coûts, stable OOS, deux jambes
décorrélées entre elles) mais son seuil de viabilité (~1 bps RT all-in aux heures 00:05/08:00) est
sous le spread CFD retail mesuré. C'est un edge de banque/prime-broker, pas de compte FTMO.
**Test démo falsifiable transmis** : si une mesure live FTMO donne ≤1.0 bps all-in sur
EURGBP+USDCHF à ces heures précises, le sleeve devient viable (SR ~0.5-0.8 net attendu) — sinon
clos définitivement. J1 reste l'unique survivant FX du book. Itérations totales des deux mandats
(commo+FX) : ~40, deux bugs/limites de modèle attrapés (rolling-vol NaN, swap énergie constant),
zéro faux positif promu.

---

## ADDENDUM 4 — Mandat BTC (9/10 itérations, gate DSR Bailey-LdP)

**Verdict : DSR PASS sur full-sample, mais NON PROMU — zéro valeur marginale OOS dans le funnel.**

| It | Test | Résultat |
|---|---|---|
| 1-4 | 4 familles LO aux coûts FTMO pleins (swap −30%/an + 18.5 bps RT) : TSMOM28-hebdo (spec Strategy-A), blend{14,28,56}, Donchian55, 200dMA | SR full 0.85-**1.24** ; mais **2022+ = 0.26-0.42 sur les 4 familles** — décay de régime confirmé au niveau stratégie, pas spec |
| 5 | Corrélation au book | **0.00** — décorrélation parfaite (l'attrait du mandat) |
| 6 | Signal funding-rate HL (2023+) | LO-si-funding-bas : SR +0.70 (expo 24%) ; funding-haut → forward négatif (−0.62) — cohérent crowding. n=3 ans : trop court, **lead ouvert** (revisiter à ≥5 ans d'historique) |
| 8 | **DSR Bailey-LdP du meilleur (blend LO, full 2015-2026, n=4165, skew +1.4)** | **0.989 à N=25 essais, 0.976 à N=50 — PASS du gate** ; mais DSR fenêtre 2022+ = 0.07 |
| 9 | Injection funnel IS (budget 0.15, canal synthétique) | p 87.7→89.0, EV +$39 — sous le seuil de promotion ($40) |
| 10 | **Injection funnel OOS 2020-2026** | **p 79.5→78.6, EV −$6 — aucune valeur ajoutée** ; 2020-21 fort neutralisé par 2022+ mort |

**Lecture** : l'edge BTC trend LO *a été* réel (le DSR full-sample le certifie, même à compte
d'essais punitif) ; il est *aujourd'hui* décayé — quatre familles de signaux indépendantes le
disent ensemble, et le test de déploiement (funnel OOS) est négatif. Le séparer ainsi — « réel
historiquement, sans valeur marginale forward » — est exactement ce que le couple DSR + OOS-funnel
permet, là où l'un sans l'autre aurait conclu trop vite dans un sens ou l'autre. Le book
contractuel reste inchangé. Lead transmis : le filtre funding-rate est le seul mécanisme qui
adresse la CAUSE du décay (crowding) — spec falsifiable consignée pour ré-examen avec plus
d'historique.

---

## ADDENDUM 5 — Renforcement d'inférence (carte blanche du researcher)

Trois faiblesses structurelles du projet identifiées et traitées :

**1. Réalisme d'exécution du breaker (le mode de défaillance live n°1).** Fill pessimiste
close ± k×range-du-bar adverse : k=0.5 → p 80.8→82.7%, EV −$31 ; k=1.0 → p 85.2%, EV −$60.
**Le funnel est antifragile au slippage** : des fills dégradés créent plus de busts donc plus de
retries — p monte, le coût se paie en fees. Borné et quantifié ; pas de falaise d'exécution.

**2. Triangulation du moteur (un seul simulateur = une seule vérité possible).** Modèle de
renouvellement indépendant (distributions empiriques par essai : P1 pass 41.8% méd. 4j,
abandon 28%/8j, busts 30%/2-4j ; P2|P1 58.7%) → p(≤91j) = **79.0% vs moteur 80.8%** — deux chemins
de calcul disjoints concordent à 1.8 pt. Corollaire : la corrélation de régime entre essais est
quasi nulle à ce design — la machine de variance est near-memoryless, d'où la composition
efficace des retries.

**3. Le single-history (la vraie incertitude statistique).** Bootstrap de CHEMINS par blocs-
semaines (blocs géométriques ~13 sem., semaines entières → structure hebdo/swap/ON préservée),
78 histoires synthétiques de ~2.3 ans : **p moyen 84.8%, p5 = 74.3%, pire histoire = 62.9%,
P(p>50%) = 100%.** Le succès du design n'est pas un artefact de la séquence 2013-2026 particulière.
*Caveats : le bootstrap recombine des semaines observées (ne crée pas de régimes inédits) ; les
signaux gardent leur contexte d'origine aux coutures de blocs.*

**Reste au backlog du researcher** (par ordre de valeur) : harnais de réconciliation live
(EA MT5 + comparateur quotidien fills/swaps/spreads vs modèle avec kill-criteria automatiques) ;
gel des specs en config exécutable (YAML) ; ré-examen du filtre funding-rate BTC à ≥5 ans de
données ; test démo du sleeve FX sessions à spread raw (seuil 1.0 bps).
