# Dossier d'audit — Stratégie #76 « Ross Hook » → **PREMIER KEEP DU PROJET**

*Audit niveau-S060 du candidat. `ftmo_lab.py` @ 9dea332. 2026-06-07. Reproductible : `code/s076_deepdive.py`, `code/rosshook.py`.*

---

## 0. Verdict

🟢 **KEEP — promu de CANDIDAT.** Le Ross Hook survit à **tous** les tests qui avaient recalé #60 (mort en données réelles) et RSI2 (décayé). C'est une **continuation de breakout à court horizon** (achat d'un nouveau plus-haut N-barres après une 1ʳᵉ correction, détention ~11 j), avec **alpha significatif sur données FTMO réelles** (t=4,0), **distinct du beta marché ET du beta tendance**, **persistant en récent**, robuste aux coûts et **sans look-ahead**. Premier KEEP en 80 stratégies.

**Cadrage honnête** : ~60 % de l'edge est du **breakout-momentum générique** (acheter les nouveaux plus-hauts), ~40 % vient de la **sélectivité du hook**. C'est une *bonne implémentation d'une prime de breakout-momentum court terme* — réelle, distincte du TSMOM lent (corr 0,11) et du beta actions (β≈0) — pas un alpha secret unique.

---

## 1. Spec (rappel)
Continuation Joe Ross, 2 côtés : nouveau plus-haut sur `Min_Setup=10` barres = jambe ; 1ʳᵉ correction = hook ; **buy stop au plus-haut du hook** (long) / sell stop au plus-bas (short). Sorties : quick-stop (extrême du hook), stop ATR×6, temps `Time=10`. R-normalisé par ATR×6. Moteur `rosshook.simulate_rosshook`.

## 2. Gates (rappel) — 0/4 = KEEP
Délai+1 +1,78→+1,53 · two-sided long +0,066/short +0,021 · DSR 2,63>1,78 · OOS +0,043→+0,049. (Sharpe trade-séquentiel ; MaxDD séquentiel −79 % = artefact, vrai DD ci-dessous.)

## 3. Audit anti-look-ahead — **PASS**
Robustesse au **délai d'entrée** (un leak au bar d'entrée s'effondrerait si on retarde) :

| Entrée | delay+0 | delay+1 | delay+2 | delay+3 | delay+5 |
|---|---|---|---|---|---|
| Sharpe trade | 1,78 | 1,53 | 1,49 | 1,58 | 1,68 |
| expR | 0,046 | 0,040 | 0,037 | 0,041 | 0,046 |

→ L'edge **ne s'effondre pas** quand on retarde l'entrée de 2-5 jours → **pas de fuite d'information** au bar d'entrée. (Conséquence : c'est un effet **lent** de continuation, donc l'exécution est tolérante — bon pour le live — mais le « hook » précis n'est pas critique.)

## 4. Placebo — le hook ajoute, mais le fond est du breakout
| Signal (délai+1) | expR |
|---|---|
| Ross Hook | **+0,0397** |
| Naïf « acheter chaque nouveau plus-haut 10-barres » (sans hook) | +0,0235 |
| **Apport de la sélectivité du hook** | **+0,0162 (~40 %)** |

→ ~60 % de l'edge = prime de breakout-momentum générique ; ~40 % = raffinement du hook. Honnête mais positif (le naïf seul est déjà positif).

## 5. Par classe (trade expR + IC bootstrap ; Sharpe MTM couvert)
| Classe | n | expR (IC95) | Sharpe MTM |
|---|---|---|---|
| **Indices** (réel FTMO) | 3 405 | **+0,028 [+0,019 ; +0,039]** | 0,53 |
| **Commodités** | 2 255 | +0,059 [+0,038 ; +0,082] | 0,93 |
| **Crypto** | 287 | +0,086 [+0,040 ; +0,156] | 0,90 |
| Forex | 630 | +0,012 [−0,015 ; +0,040] | 0,20 (faible) |

→ Edge **bootstrap-significatif y compris sur indices (données propres)** — le test que #60 ÉCHOUAIT. Forex faible (à down-weighter).

## 6. Données FTMO réelles — **PASS** (le test décisif de #60)
Indices (vrai OHLC ftmo-panel) + or (vrai M1 2007+) + crypto : **Sharpe MTM 0,70**, **alpha annualisé +2,5 %, t_NW = +4,0** (β marché −0,?? t=−2,7). #60 donnait t=0,6 ici → **Ross Hook passe largement.**

## 7. MTM + facteur tendance (rappel §audit initial)
Sharpe MTM 0,96 ; MaxDD réel **−6,0 %** ; skew **+2,32**. Régression sur **marché + TSMOM 12 m** : **alpha t_NW = 5,4**, charge TSMOM négligeable, **corr(TSMOM)=0,11**. Sous-périodes (Sharpe couvert) **1,06 / 0,93 / 1,05** (2000-09 / 2010-18 / **2019-26 vivant**).

## 8. Exposition / capacité / coûts
- **94 %** des jours avec ≥1 position ; **~253 trades/an** (~8/instrument/an) ; détention moy. **11,4 j**. Capacité et turnover sains.
- **Stress coûts** (délai+1) : +0 bps expR 0,040 (Sh 1,58) · +3 0,037 · +6 0,033 · **+10 bps 0,028 (Sh 1,09)**. Dégrade en douceur, **positif jusqu'à +10 bps**.
- **Contrôle #80 (SMA dual)** : DISCARD (beta long) sur le même univers → l'edge n'est pas « la tendance marche ici ».

## 9. Réserves (honnêteté)
1. **Fond = breakout-momentum** (le naïf est positif) ; le hook raffine de ~40 %. Prime réelle mais connue, pas un secret.
2. **Robuste au délai +5** → effet lent ; le « hook » précis n'est pas critique (on pourrait simplifier en « breakout + petite correction »).
3. **Forex faible** → restreindre à indices + commodités + crypto.
4. **Short faible en MTM** (long-dominé), même si two-sided passe au niveau trade.
5. **1 survivant sur 80** (multiple testing) — atténué par : significatif sur 3 sous-périodes disjointes, sur données réelles, placebo, robustesse coûts/délai.
6. **Commodités = futures proxy** pour la part non-or (pas d'OHLC FTMO réel pour softs/argent/PT/PD/oil) → revalider la part commodités sur données broker réelles.

## 10. Recommandation
🟢 **KEEP** (1ᵉʳ du projet). Config déployable : **indices + commodités + crypto** (retirer forex) ; entrée breakout post-correction, sortie ~10-20 j + stop ATR. **Avant capital réel** : (a) revalider la part commodités sur données FTMO réelles, (b) paper-trading pour confirmer le slippage des breakouts, (c) éventuellement simplifier/robustifier le hook (effet lent). C'est le résultat positif que tout le processus rigoureux visait à trouver.

## 11. Repro
`cd oxfordstrat_109/code && python strat_s076_ross_hook.py` (gates) ; `python s076_deepdive.py` (look-ahead, placebo, par classe, réel, coûts, figure → `results/s076_deepdive.png`). `ftmo_lab.py` inchangé (9dea332).
