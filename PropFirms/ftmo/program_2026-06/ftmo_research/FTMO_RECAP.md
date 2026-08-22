# FTMO — RÉCAP MAÎTRE (à lire en premier)

*Synthèse de tout l'arc de recherche FTMO (2026-06). Le fichier unique pour comprendre où on en est.*
*Met à jour et englobe `FTMO_decision_memo.md`. Détails dans les deliverables listés en fin de fichier.*

---

## TL;DR (le résultat en un paragraphe)

> **Aucune stratégie price-pattern retail-accessible ne bat la barrière ~50 % du challenge FTMO 2-step — vérifié en profondeur sur ~1 100+ trials systématiques, toutes les grandes familles, et toutes les classes d'actifs liquides FTMO (FX, indices, métaux, énergie, softs/grains), avec les vrais swaps FTMO.** Tout se réduit, après coûts honnêtes, soit à du **beta long déguisé** (une seule jambe marche, le côté short meurt), soit à des **signaux trop faibles** (Sharpe ≤ 0,34). Le **meilleur véhicule pour passer le challenge reste l'incumbent : ORB-30min + floor_taper (~46–50 %)** — qui n'est pas un alpha mais une exploitation maligne des règles (no-bust × temps illimité). **FTMO est un mécanisme de financement, pas une source d'alpha.**

---

## L'objectif et le résultat unifiant

**Objectif :** passer le challenge FTMO 2-step ($10k : +10 % phase 1, +5 % phase 2, DD journalier 5 %, DD total 10 %, temps illimité) avec une probabilité **meilleure que ~50 %**.

**Le résultat qui revient partout :** sur une barrière **symétrique** (+10 %/−10 %) sans limite de temps, sans **vrai alpha par-trade** la proba de passage est **~50 % par la math du no-bust**, quel que soit l'emballage. Donc battre 50 % exige un edge **two-sided** (qui gagne long ET short) qui **survit les vrais coûts**. C'est exactement ce qu'on ne trouve pas.

**Les 3 tests qui tuent tout (le protocole) :**
- **L25 — two-sided :** un edge directionnel doit être positif sur **les deux jambes**. Partout, seule la jambe long marche (= le drift equity = beta).
- **L26 — la poutre porteuse :** tout repose sur une hypothèse non-testée. Intraday : *same-bar fill → délai 1-bar*. Carry : *snapshot statique → base dynamique*. À chaque fois, la poutre s'effondre au test.
- **DSR / OOS :** sur l'espace total de recherche, les meilleurs t-stats (1,0–1,4) sont loin de la barre (~2,8–3,4) ; le rare qui passe in-sample (swing-MR) **décaye OOS**.

---

## Ce qui a été testé — tableau maître

| famille / actif | profondeur | résultat clé | verdict |
|---|---|---|---|
| **Overnight harvester** (MA200, NQ) | durci : financement, queue, temps, √N, vrais swaps | beta ; 82–88 % in-sample swap-free, mais **vrai swap US100 −3,31/nuit → p_funded 31 %** | **mort au vrai swap** (sauf compte Islamic swap-free) |
| **Alpha-hunt largeur** (5 familles) | 1 backtest chacune | tout = 0-EV ou beta one-sided ; le "bon" fade MR était un artefact overlap+look-ahead | rejeté |
| **MR intraday** (deep) | ~350 trials | 0 two-sided inconditionnel ; cellules régime t ≤ 1,44, knife-edge, OOS-instable | **clos** |
| **Stat-arb / paires FX** (deep) | 18 paires, 48 trials | half-life 22–180 j ; casse OOS ; financement-killed ; spread pas two-sided (drift relatif) | **clos** |
| **Breakout** (deep) | NQ artefact-fill + 190 trials multi-instr | edge = same-bar fill (s'effondre au délai) ; 0 two-sided sur NQ | **clos** |
| **Momentum intraday** (deep) | 176 trials | le plus one-sided de tous (beta long pur) | **clos** |
| **Swing momentum** (deep) | daily | faible, one-sided, s'effondre au délai | **clos** |
| **Swing mean-reversion** (deep) | ~346 trials | **le plus proche** : EURGBP t=3,53 in-sample (two-sided, delay-robust) mais **décaye OOS** (train 3,75 → test 0,89) et ne généralise pas (2/18) | **clos (un "non" de meilleure qualité)** |
| **Carry FX multi-jour** (vrais swaps) | — | encaissable < 1,2 %/an (markup) ; queue d'unwind −15 à −20 % > floor 10 % | **mort** |
| **Dédale** (algo de l'ami : trend+carry) | notre framework, vrais swaps | trade de régime décayé ; flat aux vrais swaps, **p(pass) 22–30 %** | **ne bat pas l'incumbent** |
| **Commodities — momentum** | 10 commodities, 2005-26 | faible (Sharpe 0,12–0,25), décayé mi-décennie | faible |
| **Commodities — saisonnalité** | expanding-OOS | **Sharpe 0,30, two-sided, positif chaque sous-période** | **le seul signal OOS-stable de l'arc (keeper)** |
| **Commodities — carry/basis** | make-or-break statique→dynamique | statique +0,46 = **hindsight** ; dynamique **−1,15** ; short-oil-contango = **−64 %/an** ; 77 % pétrole | **NO-GO** |
| **Commodities — relative-value métaux** | ratios or/argent etc. | pas cointégré, half-life 1–4 ans, **perd** (t=−6,4) | mort |
| **Commodities — COT/hedging-pressure** | CFTC 18 ans, 9 commodities | faible/décayé (meilleure variante TS 0,26) | faible |
| **Commodities — skewness** | Fernandez-Perez | Sharpe 0,06 | faible |
| **Commodities — combiné** (tous signaux two-sided) | décorrélés | **Sharpe 0,34 → p(pass) ~42 %** | **égale-à-sous l'incumbent** |

---

## Ce qui est arrivé le plus près (pricé honnêtement)

1. **Commodities** — **le meilleur asset de l'arc.** Les signaux y sont **vraiment two-sided** (pas de drift séculaire qui pollue le short) et la **saisonnalité est OOS-stable**. Vraie rupture qualitative vs le beta partout ailleurs. **Mais** chaque signal est trop faible (≤0,30), le combiné (0,34) ne bat pas le ~50 %, et le carry qui aurait fait la différence était du hindsight (dynamique −1,15).
2. **Overnight harvester** — la seule beta réelle, répliquée. 82–88 % in-sample **mais mort au vrai swap** (31 %), sauf compte swap-free Islamic + gestion keep-alive (règle d'inactivité 30 j).
3. **Swing-MR (EURGBP)** — a franchi le pré-filtre (t=3,53 in-sample, two-sided, delay-robust) mais **décaye OOS** + ne généralise pas. Un "non" de meilleure qualité que l'intraday.

---

## Ce qu'il faut faire concrètement

1. **Passer le challenge avec l'incumbent : ORB-30min + floor_taper (~46–50 %).** Ce n'est pas de l'alpha, c'est l'exploitation des règles (no-bust × temps illimité + skew). Aucun candidat trouvé ne le bat.
2. **Garde-fou swap-sign systématique** (`ftmo_swaps.py`) : ne jamais tenir le côté swap-négatif overnight (le vrai swap US100 long −3,31/nuit explique la mort de l'overnight indices).
3. **Garder la saisonnalité commodities** dans la boîte à outils (seul signal OOS-stable) — pas un upgrade seule.
4. **Recadrer le but :** FTMO finance ; on passe la barrière au moins cher, on ne cherche pas à imprimer de l'argent dessus. Le vrai EV, s'il existe, vit hors du menu price-pattern liquide retail (exécution sub-bp / market-maker, ou données payantes).

---

## Leçons méthodologiques (le protocole réutilisable)

- **L25** — two-sided obligatoire : un edge directionnel positif seulement à long = beta, rejeté.
- **L26** — tester la poutre porteuse : non-overlap + délai 1-bar (intraday) ; snapshot statique → base dynamique (carry). Le test décisif qui distingue l'edge de l'artefact.
- **L27** — market-neutral *par construction* ≠ two-sided *dans le spread* (un spread cointégré hérite d'un drift relatif).
- **L28** — une paire CFD market-neutral paie **2× le markup broker** en financement (le taux benchmark s'annule entre les jambes) ≈ 1,5 bps/nuit, **dans toutes les ères de taux**.
- **L29** — holding matché à la half-life : nécessaire mais pas suffisant (corrige un confounder, ne fabrique pas d'EV).
- **L30** — règle du signe du swap (Dédale, codée `ftmo_swaps.py`) : vrais swaps FTMO **asymétriques** (markup) ; la prime overnight (long) et le swap-positif d'un indice (short) sont incompatibles.
- **L31** — alpha-decay carry / reversal : réel dans son régime, décayé ensuite (carry FX, short-term-reversal indices) → test OOS/post-régime obligatoire.
- **L32 (nouveau)** — **carry commodity CFD one-sided-uncollectable** : le convenience yield qui rend une commodity backwardated attractive à l'achat la rend brutalement chère à shorter (short-WTI-contango = −64 %/an de swap). Le "carry two-sided" de la littérature n'est **pas collectable two-sided** au tarif retail.

---

## Outils & datasets construits (réutilisables)

- **Le protocole anti-faux-positif** : non-overlap + délai/dynamique + two-sided + DSR + OOS + swap-sign. À utiliser comme **filtre** (gate), pas comme mineur.
- `code/ftmo_swaps.py` — garde-fou swap-sign (vrais swaps FTMO FX + indices + commodities).
- `code/{overnight_harvester_sim, mr_deepdive, statarb_deepdive, directional_deepdive, swing_deepdive}.py` — moteurs de backtest.
- `outputs/commod_daily.parquet` — 10 commodities FTMO, 2005-2026.
- `outputs/cot/*.parquet` — **18 ans de COT CFTC** (9 commodities) — dataset fondamental gratuit.
- `ftmo_specs_full.csv` — vrais swaps/specs FTMO (FX, indices, métaux, énergie, softs).

---

## Leads restants (non testés / bloqués sur données)

- **Basis-momentum** (Boons-Prado 2019) — le seul facteur commodity académique encore non testé ; besoin de la **vraie structure de terme** (splice de contrats différés) — build de données lourd.
- **Exécution sub-bp / market-maker** — là où les reversions fines deviennent tradeable (pas retail-FTMO).
- **Données payantes** (Glassnode crypto, term-structure commodities propre).

---

## Index des deliverables

| fichier | sujet |
|---|---|
| `OVERNIGHT_drift_hardening.md` | overnight harvester (financement, queue, temps, √N) |
| `ALPHA_hunt_ftmo.md` | scan largeur 5 familles |
| `MR_deepdive_ftmo.md` | mean-reversion intraday (~350 trials) |
| `statarb_deepdive_ftmo.md` | paires/stat-arb FX |
| `breakout_deepdive_ftmo.md` (+ `_multiinstr`) | breakout |
| `momentum_deepdive_ftmo.md` | momentum intraday |
| `swing_carry_deepdive_ftmo.md` | swing + carry FX multi-jour |
| `dedale_eval_ftmo.md` | évaluation de l'algo de l'ami |
| `commodities_deepdive_ftmo.md` | commodities (momentum+saison+carry, premier passage) |
| `commod_carry_makeorbreak.md` | carry commodity : make-or-break (NO-GO) |
| `commod_extended_signals_ftmo.md` | relative-value métaux + COT + skewness |
| `FTMO_decision_memo.md` | memo de décision (englobé par ce récap) |
| **`FTMO_RECAP.md`** | **ce fichier — le récap maître** |

*Récap compilé 2026-06-02.*
