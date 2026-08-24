# AUDIT ADVERSARIAL — sleeve « month-end bounce » (BTC / FTMO)

**Auditeur ≠ auteur · session offline · 2026-07-12** · Pré-reg gelée : `design/PREREG_audit_month_end_20260712-1644.md`
(commit `062a1898`, **avant** tout résultat). Aucune action live, aucun merge, aucun déploiement.
Artefact audité : `Rapport_BTC_intraday_FTMO.docx` + `SLEEVE_month_end_bounce.md`.
**Code de repro (`alpha_vs_beta.py`, `ftmo_barrier.py`) + `N_ledger.md` ABSENTS** → audit par
**recomputation indépendante** depuis `data/panels/m5_indices/binance/BTCUSD_M1.csv` (2018→2026-06, UTC).
Interpréteur : venv `myenv` (pandas 3.0.2, statsmodels 0.14.6).

## Contrôle d'entrée (SSH lecture seule, `state.json` VPS 2026-07-12 16:44:04 Paris)
`kill=0` · `flat_today=0` · `positions=[]` · `FLAT`=ABSENT · phase P1, equity 9641.29, vm=14,
spec_sha `56fbdde78a2e…27928` (chaîne gelée). Préexistant hors périmètre : `targets MISSING` (dimanche).

## §2 — Chiffres de référence : CONFIRMÉS (la data & la règle sont fidèlement reproduites)
| Grandeur | Rapport | Recon indépendante | Verdict |
|---|---|---|---|
| N (last-Fri, pre<0, 2023+) | 28 | **28** | ✓ exact |
| net moyen / trade | +0,471 % | **+0,467 %** | ✓ |
| brut moyen | +0,59 % | **+0,586 %** | ✓ |
| σ net / trade | 0,977 % | **0,977 %** | ✓ exact |
| SR / trade | 0,482 | **0,478** | ✓ |
| WR | 0,75 | **0,750** | ✓ exact |
| MAE moy / pire | −0,36 % / −3,37 % | **−0,364 % / −3,368 %** | ✓ exact |
| best | +3,30 % | **+3,301 %** | ✓ exact |
| pré-2022 (contrôle régime) | ≈ −26 bps | **−27 bps** (N=22) | ✓ |
| W/L | 1,37 | 1,60 | ✗ mineur (déf. différente) |
| **HAC t** | **+2,55** | **plain 2,57 / HAC(6) = 2,29** | ✗ **voir F1** |

**F1 — Le « HAC t=2,55 » n'est PAS du HAC.** Le t simple (lag 0) = 2,57 ≈ leur 2,55 ; le vrai HAC
Newey-West (règle-maison obligatoire) tombe à **2,23–2,31 pour tout lag ≥ 1** (lag-6 = 2,29). C'est
**déjà sous le seuil 2,5 que le rapport se fixe lui-même** (§8), au coût de référence (11,9 bps) —
**avant** d'ajouter un seul bp. La « marge de coût 0,9 bp » du brief est donc **déjà négative** sous HAC honnête.

---

## TEST 1 — DSR du survivant — **KILL** (BLOQUANT)
Base par-trade (formule du brief). skew=**−0,449**, kurtosis=**8,55** (F2 : le rapport vend « low
kurtosis / tiny left tail » — l'empirie est **fat-tailed & negatively skewed**, l'opposé).

**DSR data-driven (dispersion mesurée du SR de la MÊME règle sur la grille calendaire, 2023+) :**
le survivant Fri-last (SR 0,478) est **rang 1/25** cellules, dispersion `sd(SR)=0,367`.

| N_trials | SR0 (max attendu par chance) | **DSR** |
|--:|--:|--:|
| 25 (DOF « quel jour », littéral) | 0,732 | **0,151** |
| 40 (+ régime/fenêtre/horizon) | 0,803 | **0,094** |
| 75 | 0,890 | 0,048 |

Sensibilité (liste de trials du rapport, t/√N) : sd=0,199 → DSR **0,57–0,66** (N 19-40) ; comptage le
plus indulgent (exclure les 2 positifs corrélés au survivant, N=19) → 0,88. **Jamais ≥ 0,95.**
Bootstrap 10k : net moyen CI95 **[+0,11 %, +0,82 %]**, P(mean>0)=0,993.

**F3 — mécanisme falsifié par les données.** Grid calendaire 2023+ (même règle, pre<0) :
| jour-rang | net moy | t | | jour-rang | net moy | t |
|---|--:|--:|---|---|--:|--:|
| **Fri-last (survivant)** | **+0,467 %** | **+2,53** | | Thu-4th | −0,449 % | **−2,44** |
| Fri-4th | +0,266 % | +1,28 | | Thu-last | −0,381 % | −1,88 |
| Fri-1st | +0,196 % | +1,40 | | Mon-last | −0,400 % | — |
| Wed-4th/last | +0,25 % | — | | Wed-last | −0,400 % | — |

Un « flux de rebalancing **market-wide de fin de mois** » (thèse §5 du rapport) toucherait aussi
lun/mar/mer/jeu de fin de mois. **Ils sont tous NÉGATIFS** ; seul **Friday**-last est positif, et il
existe une cellule de signe opposé **aussi significative** (Thu-4th t −2,44). Signature de sélection
sur bruit / effet spécifique-vendredi (expiry), **pas** de rebalancing month-end.

**KILL RULE (gelée) : DSR < 0,80 → sleeve morte, STOP, passage au TEST 4.** DSR = **0,05–0,15**
(data-driven) ; ≤ 0,66 sous tout comptage incluant les positifs corrélés ; 0,88 au mieux (< 0,95 →
« GO plein » déjà exclu). **→ SLEEVE MORTE.** Per pré-reg : aucune variante de sauvetage ; TESTS 2/3/5 non exécutés.

---

## TEST 2 — Coût réel FTMO — **NON EXÉCUTÉ** (TEST 1 kill) ; faits corroborants déjà en main
Non lancé (règle gelée + chaque essai supplémentaire dégrade le DSR). Éléments **déjà surfacés** qui vont tous dans le sens NO-GO :
- **BTCUSD absent du book live** : `state.json` `symbol_specs` = XAUUSD/USDJPY/US100/GER40 uniquement. Disponibilité crypto sur le compte à confirmer, non traitée live.
- **Levier Swing < Normal** : `spec_bounds_detail` → marge XAUUSD Swing **0,1111 (1:9)** vs Std 0,0333. Le rapport suppose crypto 1:3,33 (Normal) → le front de sizing (65 % @3,33) est probablement **inatteignable en Swing** (levier crypto vraisemblablement plus bas).
- **Marge de coût déjà négative** (F1) : au coût du rapport (11,9 bps) le HAC honnête est **2,29 < 2,5**. La kill rule TEST 2 (coût > 12,8 bps → t < 2,5) est **déjà franchie à 0 bp additionnel** sous HAC correct.
- Le backtest entre à `open(08:00)` (prix intouchable en market) → tout slippage réaliste ne fait qu'aggraver.

## TEST 3 — Effet d'expiration — **PRÉ-RÉPONDU par le grid calendaire du TEST 1** (pas de nouveau spec)
La grille du TEST 1 (byproduct, pas un test ajouté) montre déjà : (a) mécanisme « month-end
rebalancing » **falsifié** (jours de fin de mois adjacents tous négatifs) ; (b) gradient **vendredi**
(Fri-1st/2nd/4th faiblement positifs, Fri-last le plus fort) — cohérent avec des **vendredis d'expiry**
(options Deribit/Binance expirent le vendredi 08:00 UTC), pas avec un flux market-wide. **Implication :**
si un edge « expiry hebdo » existe (N~180), c'est une **hypothèse de recherche distincte** exigeant sa
**propre pré-registration** — ce n'est pas une résurrection de CE sleeve (le sleeve *tel que spécifié*,
last-Fri N=28, est mort au TEST 1). Le brief autorisait ce test comme « le seul monde où ça vaut le
coup » ; verdict : **à re-pré-enregistrer séparément si poursuivi**, hors périmètre de cet audit.

---

## TEST 4 — Portage path-aware sur le book — **FAIT (indépendant)** : la correction est PETITE, pas 34-49 pts
**Step 1 — moteur du triplet acté (vérifié sur SOURCE, pas deviné).** Le triplet (71,4 %/+740/vm14 ;
réel 69,7 %/+678) est produit par le cleanroom `engine_v22`
(`data/ftmo_portfolio/audit_v2_independent/cleanroom/engine.py`). `load_market` charge **un seul prix
par barre M5 par jambe = le close** (L50-87) ; `run_phase` marque l'équité sur ces closes et vérifie
floor −5 %/j + breaker sur la **grille M5, closes uniquement** (L258-275). → **M5-close-only** ; il ne
voit jamais le low intra-barre. **MAIS : c'est déjà de la grille M5, PAS de l'« EOD-approx ».**

**Step 2/3 — port path-aware + delta.** Un overlay path-aware existe et est **indépendamment audité**
(session `real-book-metrics-lowcheck`, `lowcheck_engine.py`, floor-sur-adverse / breaker-close-discret ;
AUDIT.md author≠auditor = **CONFIRM-WITH-CAVEATS**, tout re-dérivé du brut). Ancres reproduisant le
triplet cité **exactement** : SWING OFF/close **71,4286 % = 330/462**, EV **+$739,72**.

| triplet (p, attempts, EV) | valeur |
|---|---|
| **baseline close-only (cité)** | **(71,4 % , ~3,2 , +$740)** |
| **path-aware réel (compte 3 = low + gate J1)** | **(69,7 % , 3,29 , +$678)** |
| Δ low-check seul | **−1,30 pt** [CI90 −4,11 ; +1,52], McNemar p=0,327 (**NS**) |
| Δ combiné (gate+low) | −1,73 pt ; ΔEV −$62 |
| borne pessimiste (low_both) | −3,9 pt |

**F4 — le rapport surestime la correction path-aware du book d'un ordre de grandeur.** Le rapport (§3)
qualifie le sim du book d'« EOD-approx (net daily) » et en tire « surestime la survie de **34-49 pts** ».
Mais le moteur du book est **déjà M5-grid** (la grosse correction EOD→M5-grid est *déjà appliquée*). Le
résiduel réel (M5-close → low intra-M5) est **−1,3 pt** (challenge), offsets réels median 1,5-3,7 bps.
Les « 34-49 pts » sont la démo EOD-vs-path du *propre moteur du sleeve BTC* — **non transférable** au book.

**vm14 :** le brief dit « si delta significatif → ré-examiner vm14 ». Au **challenge**, Δ = −1,3 pt, CI⊃0,
**NON significatif → vm14 tient**. Le vrai siège du tail intra-barre est le stade **FUNDED** (14-30 %
busts vs 3 %, vm-sensible, porté par l'OR, dégât $ borné par le banking) — déjà **signalé, non tranché**
par la session realmetrics, chantier séparé. **L'ajout du sleeve BTC est sans rapport avec cette question.**

## TEST 5 — Intégration book — **NON EXÉCUTÉ** (conditionné à 1∧2∧3 PASS ; TEST 1 a kill)

---

## §3 — Contrainte d'exécution → **version-future** (voir `design/ARCHI_NOTE_month_end_executor.md`)
Créneaux sleeve (08:00/11:59 UTC) **absents de la grille EA** (Paris 09:00/15:30/16:00/17:35/21:30-22:05/22:58 ;
sortie ≈13-14:00 Paris = trou). Non déployable sans recompile EA (interdit) → **LCAP8 quoi qu'il arrive**.

## RECOMMANDATION FINALE (5 lignes)
1. **NO-GO** sur le sleeve month-end tel que spécifié. **DSR = 0,05–0,15** (data-driven ; ≤0,66 tout
   comptage sérieux ; jamais « GO »), sous la kill rule TEST 1 (< 0,80).
2. Le mécanisme « rebalancing market-wide de fin de mois » est **falsifié par ses propres données**
   (jours de fin de mois adjacents tous négatifs ; seul le vendredi paie ⇒ signature expiry, N=28, ~8/an).
3. Le **HAC honnête est déjà 2,29 < 2,5** au coût de référence : la « marge 0,9 bp » n'existe pas ;
   BTCUSD n'est pas au book live et le levier Swing est < 1:3,33 supposé.
4. **TEST 4 découplé — c'est la vraie valeur :** le moteur du book est M5-close-only ; le port
   path-aware ne coûte que **−1,3 pt (69,7 %/3,29/+$678 vs 71,4 %/+740)**, NS, **PAS 34-49 pts** →
   **vm14 tient au challenge** ; le tail intra-barre funded (déjà à l'étude) est le seul angle mort réel.
5. Le rapport n'est **pas** malhonnête sur la data (§2 reproduit exact) mais **survend** trois choses :
   la significativité (t brut étiqueté HAC), le profil de queue (fat-tailed, pas « low kurtosis »), et
   sa contribution path-aware au book (×25-35 trop grande). Non intégrable, non déployable → **classer version-future.**

## Contrôle de sortie (SSH lecture seule, `state.json` VPS 2026-07-12 17:08:20 Paris)
`kill=0` · `flat_today=0` · `positions=[]` · `breaker_fired_today=0` · `FLAT`=ABSENT ·
spec_sha `56fbdde78a2e…` (**inchangé** vs entrée) · heartbeat frais · `last_error=''`.
→ **Compte <ACCOUNT_ID> intouché, chaîne gelée intacte.** VNC non utilisé → bouton Algo Trading jamais
touché (re-check conditionnel N/A ; EA vivant + kill=0 + no error = opérationnel). Aucune action live,
aucun merge, aucun déploiement effectués durant la session.
