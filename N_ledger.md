# N_ledger — programme btc_intraday_ftmo

**Convention (héritée fx_intraday_deepdive)** : chaque SPEC backtestée incrémente N. Validation
data pure (qualité, coût, moteur) = +0. Baseline programme = **0** (cellule neuve, cf. pré-reg §1).

| Step | Spec | ΔN | N | Verdict |
|---|---|--:|--:|---|
| Phase 1 | qualité data + modèle coût | 0 | 0 | data-only |
| Phase 2 | moteur barrière (validation synthétique) | 0 | 0 | engine-only |
| F1a | ORB continuation, ancre 00:00 UTC (OR 30min, stop OR-low, target 1×OR) | +1 | 1 | **FAIL** net −19,1 bps, HAC t −9,63 ; gross −2,5 bps (négatif) |
| F1b | ORB continuation, ancre 13:30 UTC (US open) | +1 | 2 | **FAIL** net −18,7 bps, HAC t −10,04 ; gross −1,5 bps |
| F2 | US-session long 13:30→20:00, stop −1,2% | +1 | 3 | **FAIL** net −15,7 bps ; gross +1,35 bps ≪ coût ; récent t −2,15 |
| F3 | pré-drift event (FOMC+CPI US HIGH, long −2h→event, stop −1%) | +1 | 4 | **FAIL/underpowered** net −5,8 bps, t −0,67 ; gross +4,7 bps ; récent +4,7 bps t +0,48 (N=168, power collapse L12) |
| V-ctrl | momentum intraday, long rest-of-day, unconditionnel [contrôle] | +1 | 5 | **FAIL** net −19,5 bps, t −2,75 |
| V-hv | momentum intraday **vol-conditionnel** (haute-vol), no-stop [primary] | +1 | 6 | ambigu preflight : net −9 bps t −0,41, mais récent 2022+ **gross +27 / net +16 bps** |
| V-hv-stop | idem + stop −1,5% [barrière] | +1 | 7 | **FAIL** net −29,5 bps (stop whipsaw sur hold 19h) |

**N = 7. STOP.** Validation décisive du survivant (V-hv récent) : gross positif survit au spread (net +28 @25 bps)
MAIS **HAC t ≤ 1,9** (< 2,5), **WF 3/6 folds** avec sign-flip (< 60%, L31), **DSR 0,03-0,04** (< 0,95, tué par
multiple-testing), **p(pass) 5,75%**, et point estimate sensible au seuil de vol (N=266→+16 ; N=105→+49 = degré de
liberté). Verdict : **BTC intraday long-only edge/cost-dead pour FTMO.** POSTMORTEM.md.

## Lecture
- **F1 (continuation) est significativement NÉGATIF** (t −9 à −10) : le breakout intraday BTC ne
  continue pas, il **fade**. Signal réel, mais magnitude (~2,5 bps) < coût live (~8 bps).
- **F2 (drift directionnel de session)** : gross +1,35 bps, sub-cost — même mur que L43 (FX) mais ici
  c'est faible, pas inversé ; **négatif significatif en récent** (t −2,15).
- **F3 (pré-event drift)** : seul gross positif robuste (+4,7 bps, +4,7 récent) et cohérent L42, mais
  **sous-coût + underpowered** (N=168 ≈ 20/an, L12 power collapse) → t non significatif.

## Null pré-engagé (pré-reg §9)
Les 3 familles pré-enregistrées échouent → soit (a) UN shot pré-enregistré sur la direction fade
(mean-reversion long-only), soit (b) STOP + POSTMORTEM « BTC intraday long-only edge/cost-dead ».
Décision à trancher AVANT toute nouvelle spec (chaque test déflate le DSR de tout candidat futur).

## À réconcilier
`data/crypto_intraday/axis1_events.csv` — étude crypto CPI/FOMC préexistante (continuation 30/60/120m).
Vérifier si un verdict/POSTMORTEM existe avant tout nouveau test event (L48).

## Pre-reg #2 — #1 MR oversold + #2 gamma/expiry (exécuté + audité 2026-07-12)
| Spec | ΔN | N | Verdict |
|---|--:|--:|---|
| #1 MR oversold (RSI2/IBS/VWAP × seuils, 6 cellules) | +6 | 13 | **STOP cost-dead** : RSI(2)<5 gross +0,34 bps (2022+) vs coût taker ~10,5 bps ; net −9 bps ; DSR 0 ; two-sided sign OK mais ~1 bp ≈ 10× sous coût (L43) |
| #2 gamma/expiry (type × horizon, 6 cellules) | +6 | 19 | **Mixte** : daily/weekly = momentum (V-shape falsifié) ; **MONTHLY récent = rebond RÉEL** |

**Audit indépendant #2 monthly (recompute from scratch, session principale)** : 2022+ N=37 WR 0,76 w/l 1,09 net +39,4 t +2,48 ; 2023+ N=28 WR 0,79 w/l 1,37 net +48,1 t +2,60 ; full-sample t +0,45 (récent-only). **Profil L24-idéal** (WR haut, w/l>1, survit au coût) MAIS underpowered standalone (~6-9/an, DSR 0,02, sign-flip pré-2022).
Extension proposée : **cross-asset pooling** (ETH/SOL/BNB monthly expiries, gratuit) → N≥30 + fréquence + test généralité mécanisme (L44) ; GEX conditioning = payant.

## Extension cross-asset #2 (exécuté + audité 2026-07-12) — MÉCANISME FALSIFIÉ
Pooled 2023+ : LIQUIDE BTC+ETH+SOL net +46,7 bps t+2,85 (N=75) ; PLACEBO DOGE+XRP+BNB net +48,8 bps **t+3,86** (N=67) ; DOGE seul +70,7 t+3,18.
**Contraste L44 : placebo ≥ liquide → gamma-hedging FALSIFIÉ.** L'effet n'est PAS options-spécifique : c'est un rebond intraday de FIN DE MOIS (dernier vendredi) market-wide, présent sur toute la crypto (co-mouvement).
Conséquence breadth : les 6 actifs = ~1 pari corrélé (beta crypto), PAS 6 indépendants → N effectif ≈ ~20-25 fins-de-mois qualifiantes, pas 75 ; t pooled 2,85 GONFLÉ. Cross-asset n'ajoute PAS de breadth réelle sur des actifs corrélés.
Résiduel : vrai rebond de fin de mois (récent, WR~0,75, ~12/an market) MAIS probablement long-beta timé (L25) → test alpha-vs-beta requis avant de le garder.

## Test alpha-vs-beta rebond fin-de-mois (2026-07-12) — EDGE RÉEL confirmé
BTC 2023+ : dip-buying jour ordinaire [placebo temporel] net −8,9 bps (t−2,98, N=594) ; LAST-FRIDAY +47,1 bps (t+2,55, WR 0,75, N=28). ETH idem (placebo −10,0 ; last-Fri +42,5). UP-morning = momentum (+6,4 bps).
→ Prior "beta" FALSIFIÉ : acheter un dip un jour ordinaire PERD ; seul le dernier vendredi rebondit. + placebo cross-asset (tous coins bougent) = effet CALENDAIRE market-wide fin de mois (rebalancing), ni gamma ni beta générique. Récent-only (pré-2022 last-Fri −26 bps). PREMIER edge survivant. Caveats : N~28, ~12/an, régime-dépendant. Prochaine étape : DSR + p(pass) barrière + sizing + plan de déploiement (sleeve).

## Sizing fin-de-mois + overnight 21-23h (2026-07-12)
Month-end BTC 2023+ (N=28) : bounce moy +0,59% (max +3,30%), MAE intraday moy −0,36% (min −3,37%) = queue gauche minuscule.
Claim "1 trade passe P1" : à levier max 1:3.33, E[return]/trade = +1,57% (pas +10%) ; P(1 trade≥+10%)=P(bounce≥3%)=4% ; P(breach)=4%. → loterie 4%, PAS "il suffit de sizer" (plafond levier bloque). MAIS MAE minuscule → sizable agressivement sans bust (breach 4% à max lev). Bonne façon = compound ~6-7 fins-de-mois. Micro-positions 4 jours = valide.
Overnight 21:00→23:00 UTC BTC 2023+ : +7,2 bps/jour, t+3,64, WR 0,53, N=1248 (haute freq) MAIS < coût FTMO ~9 bps RT + swap → probablement cost-dead (L43). Swap FTMO à mesurer pour confirmer.

## Rotation régime (étapes 1-3, 2026-07-12)
Étape 1 (contenu prédictif régime, no look-ahead) : vol-régime prédit la vol forward (fiable, sizing) ; direction robuste SEULEMENT en up-lo (bull-calme) +32/+40 bps/j. down-hi = rebond post-crash (dangereux).
Étape 2 (long en up-lo, net frais FTMO réels : comm 6,5 + spread ~4 + swap 8,2bps/nuit ×3 ven ; levier 3.33) : multi-jours Sharpe 0,80 MaxDD −37% ; intraday-flat 0,75 −29% ; buy-hold 0,68 −77% ; MA-naïf 0,64 −62%. Le filtre BAT les benchmarks risk-adjusted + divise le DD par 2 (valeur défensive). Multi-jours > intraday (swap survécu) → horizon = swing.
Étape 3 (+ filtre MA200) : Sharpe 0,89 MaxDD −33% (coupe 2022/2018) mais 2021 négatif. **DSR ÉCHEC 0,001-0,066** (Sharpe 0,79 < E[maxSR] 1,3-1,9). **Sizing FTMO : MaxDD −33% → levier 0,30× → +5%/an → +10% en ~22 mois.**
VERDICT : vrai beta BTC risk-improved (Sharpe 0,89, ½ DD du buy-hold) = candidat sleeve book/perso, PAS un passeur de challenge FTMO (barrière −10%/−33% + DSR). Méta : pas de stratégie challenge rapide dans l'espace prix/régime BTC.

---

## RÉCONCILIATION D'AUDIT (auditeur ≠ auteur, 2026-07-13) — voir outputs/btc_intraday_ftmo/POSTMORTEM_process.md
**n_trials réel de l'ESPACE prix/régime BTC ≈ 50** (19 déclarés + 6 cross-asset + 3 alpha-vs-beta + 2 sizing/overnight + matrice régime 6×4 recouvrante + 4 vol-est + 4 combos book + MA200/horizons). Le « 15-40 » du rapport #2 sous-compte. → **E[maxSR] ≈ 1,8-2,3** (Bailey-LdP, sd(SR) 0,8-1,0). Meilleur book atteint 1,13 ≈ **la moitié**.

**DSR des deux specs promues, au n_trials honnête (confirmé, pas infirmé) :**
- **Month-end bounce = 0,02-0,07** (par-trade T=28 ; dispersion calendaire sd 0,367 ; survivant rang 1/25 cellules). **DSR-MORT.** Le 0,02 est dans ce ledger (l.46) mais **omis de la table §5.1 du rapport DOCX**, euphémisé « DSR marginal » dans la fiche, promu « candidate validée ». Mécanisme « rebalancing fin-de-mois » **falsifié** (jours de fin-de-mois adjacents Mon/Wed/Thu-last tous négatifs ; seul Fri paie ⇒ signature expiry). « HAC t 2,55 » = t **brut** ; vrai HAC(6)=2,29 < 2,5.
- **Regime-rotation 2-sleeve = 0,00** (Sharpe 1,13 ⋘ E[maxSR], T≈3066 j). Rapport #2 : 3 erreurs arithmétiques (§7 EV @p=0,40 sleeve-solo vs book 0,46 → +$325 ; §5.5 MaxDD −17 % sous barrière −10 % = sizing réduit ~0,59× non déclaré ; EV par-attempt ≠ par-campagne).

**Budget multiple-testing de l'espace BTC = ÉPUISÉ.** Tout candidat prix/régime BTC naît mort (y c. expiry-hebdo — NON testé, délibérément).

## VERDICT FINAL BTC — CLOS (voir outputs/audit_btc_sleeve/VERDICT.md)
BTCUSD 5e actif du pipeline `engine` (1 essai, 0 DOF, vm14) = **NO-GO** : corr(BTC, book) 0,10 (décorrélé, réfute l'overload) MAIS swap Swing éteint l'edge en régime opérant (2023+ net Sharpe **+0,05**) → sleeve net-nul **dilue** le book vol-targeté (ΔEV ≤ 0 < +$150) ; granularité lot 0,01 BTC casse le vol-target sur $10k ; BTCUSD hors univers EA armé ; DSR épuisé. Déploiement version-future (EA gelé). **BTC clos définitivement — pas de 3e itération.**

## ACTIF EXTRAIT (le seul de valeur, indépendant de toute stratégie BTC) — voir outputs/audit_barrier/BOOK_pathaware.md
Le moteur du triplet book acté est **M5-close-only** (vérifié source). Le « low-check » realmetrics EST le fix close→low (floor sur low adverse continu / breaker sur close M5 discret). Delta path-aware sur le triplet challenge = **−1,3 pt** [CI90 ⊃ 0, NS], (71,4 %/+740)→(69,7 %/3,29/+678) — **PAS les « 34-49 pts » du rapport #1** (qui mécaractérise le moteur M5-grid comme EOD-approx). **vm14 tient au challenge.** Tail intra-barre réel = stade FUNDED (14-30 % vs 3 %, porté OR, $-borné) ; « 57 % funded bust/an » du rapport #2 = **non sourcé**, contredit par le sim projet (14-30 %). Chantier funded séparé, déjà ouvert.

---

## Programme idx_spreadMR (indices) — #7 spread-MR × #5 gate Hurst (exécuté 2026-07-13, fil neuf)
Pré-reg GELÉE : `PRE_REG_indices_spreadMR.md`. Script gelé `spread_mr_hurst.py` (seul le mount corrigé). Univers US30/US100/US500/GER40/US2000 (M1 true-UTC, daily = preuve de mécanisme). Coût pré-enregistré 4 bps/changement (2 jambes). Signal T-1 → trade T (positions laggées z & Hurst, vérifié source). Reproduction fidèle : net poolé k=2,0/Hurst-ON = **−0,08 bps/j** (identique au run gelé → pipeline validé).

| Spec | ΔN | N | Verdict |
|---|--:|--:|---|
| #7+#5 spread-MR poolé, grille {k=1,5;2,0}×{Hurst off/on} (4 cellules) | +4 | 4 | **STOP mécanisme-absent** |
| #7 index-vs-panier (pré-enregistré, k=2,0 Hurst ON) | +1 | 5 | **STOP** gross ≈ 0,00 bps/j (Sh −0,00) |

**Chiffres décisifs — GROSS (coût=0, c'est le mécanisme lui-même) :**
- Poolé 10 paires : gross +0,08 bps/j, t +0,2, Sharpe +0,02. EW-portefeuille gross Sharpe +0,08, **bootstrap-bloc 95% CI [−0,39 ; +0,56] ⊃ 0** (P[Sh>0]=0,64) → indiscernable de zéro (IC, pas le t seul).
- Index-vs-panier : gross **0,00** bps/j (Sh −0,00), net* −0,16 (coût sous-estimé, 5 jambes chargées comme 2).
- Gate Hurst (#5, le régime « fait proprement ») : effet marginal (net poolé −0,15 → −0,08). N'exhume aucun mécanisme.
- Meilleure paire US30-GER40 : gross t +1,4 (best-of-10, < 2,5 ; ~0 après multiple-testing) ; **5/10 paires gross-négatives**.

**Kill rule pré-engagée DÉCLENCHÉE.** Spread-MR poolé (gate Hurst) gross statistiquement nul (CI ⊃ 0) + index-vs-panier gross nul → mécanisme absent dans cette forme → STOP. **DSR hors sujet** (aucun Sharpe positif à défler ; échec au gate mécanisme, EN AMONT du DSR). Net ≤ 0 partout → Phase-2 (intraday-flat, coût maker < 1 bp) NE PEUT PAS sauver un gross ≈ 0.

**Périmètre (garde anti-faux-négatif)** : STOP = MR *relative* (spread cross-sectionnel) daily entre ces 5 indices — PAS « la MR est morte ». Espace pré-enregistré NON pêché (fishing interdit post-échec, pré-reg §kill) : hedge-ratio OLS {60,120}, z-lookback 20, k=2,5, Hurst window {60,120}, VR Lo-MacKinlay, half-life sizing. Roadmap pré-enregistrée : **#4 (OU half-life)** ou **#1 (vrai VWAP + bandes)**.
Artefacts (author≠auditor, recompute possible) : `outputs/idx_spreadMR/confirm_stop.py` (bootstrap+basket), `outputs/idx_spreadMR/gross_check.py` (décompo gross/net), `outputs/idx_spreadMR/{run,gross}.log` + `confirm_stop_results.txt`. Cache daily régénérable via gross_check.py. Script gelé : `outputs/idx_spreadMR/spread_mr_hurst.py` (mount corrigé).

---

## RÉCONCILIATION L48 (fil neuf 2026-07-13) — #4 (OU half-life) + #5 (Hurst/VR) DÉJÀ EXÉCUTÉS AU DEPTH
Sweep L48 AVANT de minter #4 → collision avec un deep-dive FTMO MR préexistant **non loggé dans ce ledger** :
`PropFirms/ftmo/program_2026-06/ftmo_research/MR_deepdive_ftmo.md` (+ `mr_deepdive_grid.csv` 284 cellules, `mr_deepdive_halflife.csv`, `code/mr_deepdive.py`).

**Ce deep-dive teste EXACTEMENT #4+#5 :** half-life AR(1) estimée ET matchée (≈8-9 barres 5m/15m sur US30/US500/US100/GER40) = **#4** ; conditionnement variance-ratio / régime (range vs trend) = **#5** (Hurst<0,5 ⟺ VR<1) ; logics {SMA20-z, EMA20-z, VWAP-dev (=**#1**), RSI14 (=**#9**), range-fade} × TF {5m,15m,30m} × θ {mod,extreme} × exit {mean-touch, half-life-ts} ; non-overlap + coût 1,5 bps/trade indices + **délai-1-barre** + **test two-sided** + DSR sur l'espace total (**~344 trials**).

**Recompute grid sur les 4 indices ciblés par #4 (2026-07-13) :**
| instr | cellules | net>0 | two-sided net>0 | meilleur net (bps) | meilleur t |
|---|--:|--:|--:|--:|--:|
| US30 | 44 | 0 | 0 | −0,26 | −0,26 |
| US500 | 44 | 0 | 0 | −0,73 | −0,87 |
| US100 | 44 | 0 | 0 | −0,89 | −0,53 |
| GER40 | 48 | 0 | 0 | −0,70 | −0,25 |

→ **0/176 cellules indices net-positives** (toutes négatives), **0 two-sided**. Grid entier 0/284 two-sided net>0 ; regime steelman 4/60 two-sided mais **best t 1,44 < chance-max 2,94**. OU half-life « **did not manufacture EV** » (confirme **L29**). Meilleurs blips : US100 high-vol VWAP-dev t 1,43 (2022-concentré, ~35 tr/an, +0,2%/an) ; EURUSD-midday knife-edge (OOS-train t 0,54, +1,3%/an) — infaisables FTMO (levier DD-breaking).

**VERDICT #4 = STOP par prior-art (0 nouvel essai lancé).** OU half-life + gate Hurst sur MR intraday indices = famille close AU DEPTH. Ré-tester (US2000, sizing ∝ dev/half-life, entrée OU « pure ») ne peut pas produire un survivant (0/344 two-sided ; le two-sided ne se retourne pas par sizing) et **déflate le DSR** de tout candidat futur.

**Réconciliation n_trials de l'ESPACE indices-MR ≈ 350** : deep-dive FTMO ~344 + batch #7 idx_spreadMR (5) + specs absolues (OR-fade/session-MR, harnais intraday perdu — non commité). E[maxSR] (Bailey-LdP) élevé en conséquence → tout candidat indices-MR **naît DSR-mort**. Le roadmap MR (handoff §6) recouvre largement ce deep-dive : #1/#4/#5/#9/#10 déjà couverts ; restent formellement non-testés #2 (Bollinger/Keltner mTF), #3 (pivots/prior-day), #6 (Kalman), #8 (vélocité) — MÊME famille 0/344, prior très fort.

**Méta :** MR intraday indices FTMO = épuisé en **breadth** (ALPHA_hunt) + **depth** (MR_deepdive ~344) + **daily relative-value** (#7, ce jour). Filtre décisif partout = le **two-sided** (la « réversion » = drift directionnel de la période = beta). Pistes hors-MR (deep-dive §guidance + handoff §8) : breakout au-delà d'ORB-30min, momentum intraday high-hit-rate two-sided-first, GEX/order-flow (data payante = seule info neuve), chantier funded-tail (14-30% vs 3%), book crypto systématique hors-FTMO.

---

## Programme btc_semivar_reversal (crypto daily, hors-FTMO) — Arm 0 gate (exécuté 2026-07-13)
Pré-reg GELÉE : `outputs/btc_semivar_reversal/PRE_REG_btc_semivar_reversal.md`. Origine : survey BTC intraday 2026-07-13 candidat #3 (Liu, Lu, Li & Wang 2023, signed-semivariance timing). Univers 10 majors Binance 1m (2018→2026), daily, **RSJ=(RS⁺−RS⁻)/RV** depuis barres 5-min ; signal T-1→trade T. Coût pré-enregistré 0,17% RT (Phase 2, non atteinte). N_days pooled = 27 573.

| Spec | ΔN | N | Verdict |
|---|--:|--:|---|
| Arm 0 gate : RSJ_t→ret_{t+1} pooled HAC (brut + contrôle momentum) | +2 | 2 | **STOP** |
| Arm 1 preview : sleeve reversal GROSS pos=−sign(RSJ) | +1 | 3 | **STOP** (confirme beta) |

**Kill rule DÉCLENCHÉE sur les 4 critères pré-enregistrés :**
- **(a) MAUVAIS SIGNE** : coef RSJ→ret_{t+1} poolé = **+0,00038 (positif)** ; pré-reg attendait NÉGATIF (reversal). HAC t +0,25.
- **(b) NON two-sided** : quartiles RSJ → Q1_low (downside-dom) +12,9 bps t+2,09 ; **Q4_high (upside-dom) +8,3 bps t+1,34 → positif, PAS de reversal**. Sleeve gross : **SHORT leg (RSJ>0) −5,8 bps t−1,29 (PERD)** ; LONG leg +4,5 bps t+1,04. → seule la jambe dip-buy paie = **beta long**, pas un reversal symétrique.
- **(c)** |HAC t|=0,25 ≪ 2,5 gross.
- **(d)** RSJ ne survit pas au contrôle momentum (t+0,30 ; cum5 t−0,10, tous deux non-signif).
Sleeve reversal gross poolé **Sharpe −0,02** (mean −0,5 bps, t−0,15). Per-actif dispersé (LTC +0,58 … AVAX −1,00) = pas de mécanisme généralisable (in-sample selection).

**Verdict : mécanisme signed-semivariance-reversal ABSENT sur crypto daily.** La seule structure (Q1_low, long-leg +4,5) = **dip-buy long-beta** (L45/L11) — exactement le risque #1 pré-flaggé dans la pré-reg. **STOP loggé.** Reste pré-enregistré NON pêché (Arm 2 TSMOM-timing, L∈{1,5}, seuils) — kill rule interdit le fishing post-échec. DSR hors sujet (échec au gate mécanisme, gross ≈ 0). Restent du survey : #1 gamma-expiry reversal (data taker-flow Deribit), #2 seesaw cross-sectionnel (free-data). Artefacts : `outputs/btc_semivar_reversal/` (phase1_arm0.py, daily_*.pkl, run_tmp.log).
