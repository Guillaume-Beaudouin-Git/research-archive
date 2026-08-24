# STUDY — vm sweep du container FTMO Swing 2-step (2026-06-17)

**Lecture seule.** Aucun contact compte live / EA `book_executor` / FLAT / targets. Sim audité
réutilisé tel quel (`engine_v22` + cleanroom `engine`, helpers de mesure `run_swing_fit`) ; seul le
grid `vm` change. Pré-enregistrement : `PREREGISTRATION.md` (committé `aab58ae` AVANT le run).
Conditionnel à la marge Swing officielle 1:30/1:15/1:9 (`margin_rate_live` serveur PENDANTE).

## VERDICT — **GARDER vm14.**
vm14 est sur un **plateau d'EV plat [vm10–vm30]** (+$734 à +$762, tous dans le bruit block-bootstrap).
Le max NOMINAL est vm18 (+$762) mais il **ne bat PAS vm14 significativement** (ΔEV +$22.4, CI90
[−35.7;+81.9] ⊃ 0) et ajoute du bust-floor. **Aucun régime plus agressif ne bat vm14** ; le « full
port » littéral (vm=∞, épinglé au cap) est **strictement le pire** (p91 −2.6 pt, EV −$55). Le clip
dynamique capture déjà l'EV — vm ne fait que régler la fréquence de saturation du cap. Décision
identique à v2.2.2 (NULL), désormais étendue vers le HAUT : **null documenté, vm14 reste.**

## Gates de reproduction (preuve de réutilisation fidèle)
`policy 87.01 = 87.01` ✓ · `swing 71.43 = 71.43` ✓ · cross-checks `vm10 = 70.13`, `vm14 = 71.43`
**reproduits au centième** → le sim n'a pas dérivé, les chiffres ci-dessous sont comparables au
baseline `1947163`.

## Tableau complet (wall 91j ; M_swc re-cost ; MRATE Swing ; CI95 block-bootstrap ; VAL_swc $1,438 ; FEE $96)
| vm | p91 % (CI95) | n_tent | t_med (j cal) | P1/tent no-clock | bust_daily % | bust_floor % | abandon % | **EV91 $** | EV @comm | p45 % | p182 % | bind % | clip_depth |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 | 70.13 [61.2;78.8] | 2.69 | **34.0** | 43.61 | 7.68 | 4.89 | 35.43 | +750 | +711 | **45.67** | 88.96 | 42.8 | 0.420 |
| **14** | **71.43 [63.2;79.4]** | 2.99 | 38.5 | 41.69 | 9.82 | 5.24 | 36.01 | **+740** | +699 | 42.21 | 92.21 | 56.0 | 0.460 |
| 18 | 73.16 [64.9;81.2] | 3.02 | 39.5 | 41.69 | 9.06 | 6.01 | 35.54 | **+762** | +721 | 43.07 | 93.72 | 68.5 | 0.497 |
| 22 | 71.65 [63.4;79.7] | 3.08 | 40.0 | 41.20 | 8.96 | 6.20 | 36.32 | +734 | +694 | 42.21 | 94.59 | 71.5 | 0.564 |
| 26 | 72.73 [64.5;80.7] | 3.07 | 39.0 | 39.52 | 8.87 | 6.59 | 35.71 | +751 | +710 | 43.94 | 94.59 | 72.7 | 0.620 |
| 30 | 72.29 [64.3;79.9] | 3.06 | 39.0 | 40.00 | 9.29 | 6.04 | 36.16 | +746 | +704 | 41.56 | 94.16 | 72.9 | 0.664 |
| **∞** | 68.83 [60.6;76.6] | 3.18 | 39.0 | 39.28 | 10.40 | 5.73 | 37.61 | **+685** | +646 | 41.34 | 91.13 | 87.1 | **1.000** |

**Deltas appariés EV vs vm14 (CI90)** : vm10 +10.6 [−83.8;+107] · vm18 +22.4 [−35.7;+81.9] ·
vm22 −5.4 · vm26 +11.4 · vm30 +5.8 · vm∞ −55.0 [−143;+31]. **Tous ⊃ 0** → aucun ne bat vm14.
**Le cap fait converger les livres** : bind 42.8 %→87.1 %, clip_depth 0.42→1.00 ; pre-cap `need/eq`
médian explose (vm∞ : **×47 961**, p99 ×267 949) **mais le livre réalisé est borné à 60 % de marge**
→ le « full port » LITTÉRAL = le livre-à-60 %, et l'EV plafonne puis recule.

## Les trois points (a / b / c)
- **(a) EV max = vm18** : (p91 **73.16 %**, n_tent **3.02**, EV **+$762**). Mais +$22 vs vm14, **ns**.
- **(b) Pass médian le plus rapide = vm10** : t_med **34.0 j cal** (p91 70.13, n_tent 2.69, EV +$750).
- **(c) vm où EV<0 : AUCUN.** Le cap 60 % plancherise l'EV à **+$685** (vm=∞). *Cf. addendum cap.*

**(a) ≠ (b) — et l'agression n'achète PAS la vitesse.** L'optimum d'EV (vm18) est **+5.5 j cal plus
LENT** que le plus rapide (vm10) pour **+$11.8** d'EV (ns). En montant vm : t_med **monte** 34→40,
le pass P1/tentative (no-clock, gambler's ruin pur) **baisse** 43.6→39.3. Mécanisme : plus de taille
→ plus de busts daily → plus de retries → campagne plus lente ET plus chère. L'intuition « gros =
rapide » est **fausse** sous le cap.

## Profil SPRINT (DOCUMENTÉ, non adopté)
**Sous le cap 60 % (grille pré-enregistrée)** : le sprint (argmax p45) = **vm10**, le PLUS LÉGER
(p45 45.67 %, p30 28.79 %, bust/tent 12.6 %, EV +$750). Sprinter ≠ grossir : à cap fixe, alléger
passe plus vite ET busts moins.

**Le vrai levier d'agression = RELEVER LE CAP** (vm est borné par le cap — addendum exploratoire,
hors pré-enregistrement, `cap_cliff.py`) :
| margin_cap | p91 % | n_tent | t_med | bust_d/f % | EV91 $ |
|---|---|---|---|---|---|
| 0.60 (actuel) | 68.8 | 3.18 | 39 | 10.4 / 5.7 | +685 |
| 0.80 | 76.2 | 3.31 | 34 | 12.8 / 5.8 | +778 |
| 1.00 | 78.1 | 3.48 | **32** | 12.8 / 7.7 | **+789** |
| 1.30 | 75.8 | 3.92 | **29** | 19.1 / 6.7 | +713 |
| 1.60 | 81.8 | 4.06 | 32 | 21.0 / 9.5 | +786 |
| 2.50 | 79.7 | 5.25 | 30 | 31.8 / 12.6 | +641 |

Le sprint EXISTE (cap 1.0–1.6 : t_med **29–32 j**, p91 **78–82 %**) **mais** : (i) coût bust ×2–4 ;
(ii) **infaisable au-delà de ~100 % de marge** (margin call) ; (iii) le sim est **OPTIMISTE** à
haut cap (pas de liquidation forcée modélisée → réel pire) ; (iv) le cap 60 % gouverne AUSSI le
funded — le relâcher pour passer le challenge importe un livre 100 %-marge sur le compte financé.
**EV ne devient JAMAIS négatif** même à cap 2.5× : il faudrait ~15 tentatives/campagne (VAL/FEE≈15),
**physiquement impossible en 91 j**. La stratégie est **structurellement EV-positive** sur toute la
plage d'agression — l'agression échange le timing de p(funded) et la fréquence de bust, **jamais le
SIGNE de l'EV**.

## Décomposition bust — arm le plus agressif (vm=∞), Q4
Sur 2 058 tentatives, 302 events bust :
- **Daily −5 % : 10.40 %/tent · Floor −10 % : 5.73 %/tent** → des busts : **64.5 % daily / 35.5 % floor**.
- **Breaker M5 incapable d'agir à travers un gap — CONFIRMÉ** :
  - **20.86 %** des busts au **bar d'ouverture du jour** (`first_bar`, seg 0 bar 0) → aucun bar
    intra-day antérieur où le breaker aurait pu flatten.
  - **41.39 %** des busts sur **lundi/post-weekend** (≥3 j depuis la séance précédente) — ~2× le
    taux de base (~20 % des jours).
  - `first_bar ∩ gap` = **11.26 %** ; et **53.97 % des busts de jours-gap sont au bar d'ouverture**
    (le gap saute par-dessus breaker ET limite dure en un seul bar : `tb = tk = 0`).
  - **Stress gap ×1.5** (étiqueté, non canonique) : la part « open parmi busts-gap » monte
    **53.97 → 75.47 %**, floor bust 5.73 → 6.05 % → amplifier le gap **pousse encore plus** de busts
    sur le bar d'ouverture : le breaker reste structurellement hors-jeu dans le trou. ✓
- **Triple-swap (DOW mer/ven) : 22.85 %** des busts — **SOUS** le taux de base (40 % des jours) →
  le triple-swap **n'est PAS** un moteur de bust (swap posté en EOD, après les barrières intra-day ;
  il resserre la limite du LENDEMAIN, ne déclenche pas le bust du jour).

Le canonical (`wgap_stress=1.0`) ne modélise **aucune amplification** : les gaps = les vrais sauts
d'ouverture M5 historiques. vm30 ≈ vm∞ (first_bar 21.7 %, gap 45.3 %, open-parmi-gap 66.7 %).

## Single-sleeve vs diversifié, Q5
| Livre | p91 % | n_tent | t_med | bust_d/f % | abandon % | timeout % | EV91 $ |
|---|---|---|---|---|---|---|---|
| **Diversifié 4 sleeves @ vm14** | **71.43** | 2.99 | 38.5 | 9.82 / 5.24 | 36.0 | **0.0** | **+740** |
| J1-only @ vm14 | 53.68 | 2.44 | 34.0 | 4.43 / 2.38 | 39.4 | 7.58 | +537 |
| Overnight-only @ vm14 | 49.35 | 2.59 | 44.5 | 11.47 / 10.01 | 30.8 | 0.79 | +461 |
| Gold-only @ vm14 | 47.40 | 2.11 | 36.0 | 7.63 / 4.42 | 32.0 | 9.15 | +479 |
| J1-only FULL (vm=∞) | 54.55 | 2.70 | 36.0 | 7.20 / 3.74 | 37.9 | 7.02 | +525 |
| Gold-only FULL (vm=∞) | 49.78 | 2.15 | 36.0 | 8.0 / 4.3 | 31.8 | 8.0 | +510 |
| Overnight-only FULL (vm=∞) | 42.64 | 2.98 | 43.0 | **15.8 / 8.8** | 34.1 | 0.5 | +327 |

**La meilleure sleeve standalone est J1 (p91 53.68), PAS « nightly ».** La diversification écrase
toute concentration : **+16.9 pt de p(funded) et +$215 d'EV** vs la meilleure sleeve seule (J1-full
54.55 / +$525). Cranker la sleeve seule à fond n'aide pas (J1 +0.9 pt mais EV −$13 ; **overnight
EMPIRE** 49.35 → 42.64, bust 24.6 %/tent).

**Le paradoxe « mur porteur ».** Overnight = **plus gros contributeur marginal** du livre diversifié
(ablation +12.1 pt, registre) **mais PIRE en standalone** : concentré, son risque de gap overnight
Mon/Mar domine (bust_floor **10 %** seul = 2× le 5.24 % diversifié) ; ce n'est que MÉLANGÉ au gold/J1
continus — qui lissent le P&L journalier et offrent de la marge de récupération intra-day — que son
rendement overnight **décorrélé** devient un actif net plutôt qu'une machine à bust. **Valeur
marginale en portefeuille ≠ survivabilité standalone.** Le **DSR 0.29** (registre) flague justement
son edge standalone comme fragile — cohérent avec un actif « portefeuille-only ».

**Pourquoi la diversification gagne (mécanisme).** Chaque sleeve seule a un mode d'échec dominant —
overnight = bust/gap, gold = timeout/plat (8–9 %), J1 = abandon+timeout/drift lent (47 % cumulés).
Le mélange 4-sleeves les **annule** : timeout → **0 %** (toujours assez actif), bust contenu à 15 %,
et **3 flux à drift positif décorrélés atteignent +10 % en 91 j bien plus fiablement** (p91 71.4 vs
54.6 meilleure-seule). C'est de la diversification de **fiabilité de rendement**, plus que de
réduction de bust.

## Recommandation — triplets (p91, n_tent, EV)
| Option | p91 | n_tent | EV91 | Statut |
|---|---|---|---|---|
| **GARDER vm14** | **71.4 %** | **2.99** | **+$740** | ✅ **recommandé** — sur le plateau, = optimum au bruit près |
| vm18 (max nominal) | 73.2 % | 3.02 | +$762 | +$22 **ns** (CI90 ⊃ 0) + bust_floor ↑ → pas un changement de spec gelé v2.3 justifié |
| vm10 (rapide/sûr) | 70.1 % | 2.69 | +$750 | moins de busts, pass le + rapide (34 j), EV ≈ égale — alternative défendable si réduire la fréquence de bust prime |
| vm=∞ (full port) | 68.8 % | 3.18 | +$685 | **pire** — documente que « l'agression max » nuit |
| Sprint (cap↑, NON adopté) | 78 % @cap1.0 | 3.48 | +$789 | t_med 32 j MAIS infaisable >100 % marge, bust ×2, sim optimiste, casse le risk-control funded |

**Bouger de vm14 n'est pas justifié** : zéro gain significatif vers le haut, dégradation claire au
plein régime. Si un ajustement était un jour souhaité, **vm10** (pas vm18) est l'inflexion sensée
(bust ↓, vitesse ↑, EV ≈), mais reste dans le bruit → statu quo recommandé.

## Caveats
1. **Marge Swing** 1:30/1:15/1:9 **À CONFIRMER** serveur (`margin_rate_live`) — gate v2.2.1, comme v2.2.2.
2. **t_med = jours CALENDAIRES** (métrique du sim), pas jours de trading.
3. **FEE = $96** (sim, remboursé au 1er payout) ; à $99 : ΔEV ≈ −$9/campagne, **classement invariant**.
4. **EV haut-cap optimiste** : le sim n'a **pas** de liquidation forcée / margin call ; un broker réel
   refuse les ordres >100 % marge et liquide avant le floor à pire prix → le réel au-delà de cap 0.60
   est PIRE que montré (renforce « ne pas relâcher le cap »).
5. vm10/vm14 reproduisent SWING_FIT (70.13 / 71.43) au centième → réutilisation fidèle vérifiée.

## Artefacts
`PREREGISTRATION.md` (aab58ae) · `run_vm_sweep.py` · `cap_cliff.py` · `vm_sweep_run.log` ·
`cap_cliff_run.log` · `summary.json` · `tables/{vm_sweep_summary,paired_vs_vm14,bust_decomposition,
single_sleeve,cap_cliff,arm_*,bust_diag_*}.csv`. Baseline READ-ONLY `1947163` ; aucune édition de
spec, aucun contact prod.
