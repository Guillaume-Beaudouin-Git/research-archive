# L'amélioration : 1 essai, <2 mois — passer en 1-STEP

*La seule chose qui double le p(pass) à horizon <2 mois. 2026-06-02.*

---

## Le résultat en une ligne

> **Garde l'ORB V2+E7 exactement tel quel. Change de CONTAINER : un challenge 1-step (cible ≤ drawdown) au lieu de FTMO 2-step fait passer le p(pass) 1-essai/<2mois de ~25 % à ~48-52 %, médiane de résolution ~1,5-2 semaines.**

## Pourquoi (et pourquoi rien d'autre ne marche)

L'edge per-trade de l'ORB est ≈ 0 (DSR FAILS, prouvé). Sur une barrière, **seul le drift remonte le p(pass)** — et on ne peut pas l'augmenter :
- **Filtres signal** (long-only, régime, jour) : long-only double le drift MAIS divise les trades par ~2 → sizing forcé plus haut → mur du DD journalier → **pire** (testé : 1-step long-only 12 % vs blended 48 %).
- **Timing du départ** : impossible, μ_ORB est un bruit blanc semaine-à-semaine (prouvé, `OPTIM_regime_timing_intraday.md`).
- **Floor-taper / down-sizing** : monte le p(pass) à 80-98 % MAIS exige un grind de 2-15 mois — l'inverse de <2 mois.

Le seul levier restant à horizon court = **la géométrie de la barrière**. FTMO 2-step = passer +10 % PUIS +5 % = p(P1)×p(P2) ≈ 48 %×52 % ≈ **25 %**. Un 1-step n'a qu'**une** barrière → **~48 %**. C'est structurel, pas un edge.

## Les chiffres (sim calibrée fichier, cap 42 trades ~2 mois, blended ORB V2+E7, DAILY-3%)

⚠ **Le daily DD 3 % plafonne le sizing à 2,5 %.** La pire perte ORB = −1,19R ; à 2,5 % → 3,0 % = pile la limite journalière. Au-delà de 2,8 % de sizing, une seule perte busté → le pass s'effondre (8-10 %). **Sizing fixe = 2,5 %, pas 3 %.**

| container (cible / DDtot / daily-3%) | sizing | **PASS <2mo** | bust | n-rés | médiane |
|---|---|---:|---:|---:|---:|
| **FTMO 2-step** (+10/+5, d5, t10) — baseline | 3,5 % | **25 %** | 72 % | 3 % | 2,9 sem |
| **1-step +8 % / t10 / daily-3 %** ★ | 2,5 % | **52 %** | 43 % | 5 % | 1,8 sem |
| 1-step +10 % / t10 / daily-3 % | 2,5 % | 46 % | 46 % | 8 % | 2,5 sem |
| 1-step +6 % / t6 / daily-3 % | 2,0 % | 47 % | 51 % | 2 % | 1,4 sem |
| CTI 1-step (+8 % / DD −5 % balance) | 2 % | 38 % | 59 % | 3 % | 2,0 sem |

**Les 2 règles de choix de firme (cruciales) :**
1. **Cible ≤ DD total** (sinon la barrière joue contre toi). +8 %/−10 % = idéal. Évite +8 %/−5 % ou +9 %/−6 % (→ ~38 %, gain fondu de moitié).
2. **Vise la cible +8 %, pas +10 %.** Sous daily-3 %, le sizing plafonné à 2,5 % ne permet pas d'atteindre +10 % à temps (46 % + 8 % non-résolus) alors que +8 % passe à 52 %.

## ⚠ STRESS D'EXÉCUTION — le 52 % est un chiffre d'exécution PARFAITE

Robustesse du 52 % (cible +8 %) : stable au bruit MC (±0,3), au mean_R (50 % en conservateur +0,007), à la méthodo (contigu réel 53 %). **MAIS fragile au slippage sur stop**, et le **daily-3 % est le coupable** :

| structure firme | exéc. parfaite | slip modéré | slip agressif |
|---|---:|---:|---:|
| **daily-3 % / 2,5 %** | 52 % | **34 %** | **25 %** |
| daily-3 % / 2,0 % (sizing réduit) | 49 % | 40 % | 23 % |
| daily-5 % / 2,5 % | 52 % | 48 % | 37 % |
| **no-daily / total-10 % balance** | 52 % | 48 % | **41 %** |
| CTI +8 % / total-5 % balance | 38 % | 34 % | 28 % |

*(slip modéré = 12 % des pertes −0,3R, 3 % −0,7R ; agressif = 20 % −0,5R, 5 % −1,0R.)*

**Mécanisme :** perte 1R à 2,5 %/daily-3 % = 2,98 % → **0,02 % de marge**. Un stop qui gappe (news/momentum) busté instantanément. Le rebuild idéalise le fill (0 perte > −1,2R). **Baisser le sizing ne répare PAS** (daily-3 % reste trop serré). **Le daily-3 % est un piège pour une stratégie à stop 1R intraday.**

**→ NE PAS confirmer 52 % sous daily-3 %.** Vrai opérationnel sous daily-3 % + slippage = **~25-35 %** (≈ FTMO 2-step). Pour un ~40-48 % robuste : **daily-5 %** ou **no-daily / balance-based total ≥10 %**.

## Le plan concret

1. **Container : 1-step, cible +8 %, DD total ≥10 %, STATIQUE (pas trailing), sans limite de temps. ÉVITE le daily-3 % — vise daily-5 % OU no-daily/balance-based.** C'est le facteur #1 de robustesse (le daily-3 % coupe le 52 % à ~25-35 % au slippage). Priorité : daily large + cible basse.
2. **Stratégie : ORB V2+E7 inchangée** (OR 09:30-10:00 ET, break, stop 1R opposé, trail-BE@1R, filtre rng≥10bps, fill au niveau).
3. **Sizing : 2,5 % fixe** sur daily-5 %/no-daily (tampon large, robuste au slippage). Pas de floor-taper, pas de long-only (testés, pires). Médiane ~1,8 sem, ~95 % résolus avant 2 mois.
4. **1 seul essai.** Si bust (~49 %), c'est tranché vite → tu décides de recommencer ou pas.

## Caveats honnêtes

- **~48 % = plancher conservateur** (ma sim mélange les régimes). La méthodo contigüe du fichier donnerait ~60-65 %. La vérité forward est entre les deux.
- **Vérifie les specs AVANT d'acheter** (elles changent) : DD **statique** et non trailing ; pas de **règle de consistance** qui mord (certaines 1-step plafonnent le profit d'un seul jour) ; cible ≤ DD.
- **Ce n'est toujours pas >50 % garanti sur 1 essai** — c'est ~2× FTMO et le meilleur véhicule 1-essai/<2mois trouvé. Le >70 % exigerait soit plusieurs essais, soit un vrai edge (inexistant en retail price-pattern, prouvé sur ~1 100 trials).
- **Route futures alternative** (tu as déjà l'infra Tradeify/NQ) : éval 1-step futures, mais **DD trailing** → géométrie différente, à simuler séparément avant de trancher.

## VERDICT — 1 essai + FTMO + >60 % : le mur Sharpe (mesuré 16 ans)

Courbe p(pass) single-attempt FTMO 2-step vs edge (full sample 2010-26, sizing optimal) :

| mean_R | Sharpe ann | p(pass) <2mo | p(pass) <6mo |
|---|---:|---:|---:|
| +0,016 (ORB) | 0,22 | 26 % | 32 % |
| +0,050 | 0,70 | 32 % | 42 % |
| +0,100 | 1,39 | 42 % | **59 %** |

- **<2 mois : plafond ~42 % à TOUT Sharpe** (les 2 phases ne se franchissent pas vite sans sizing qui busté).
- **60 % single-attempt exige Sharpe ~1,4 sur 6 mois.** ORB = 0,22 ; meilleur edge robuste de l'arc = 0,34 ; gap ×4 non-comblable en price-pattern retail.
- Le 79-100 % d'`OPTIM_ftmo_2step_uncapped` = artefact du sous-échantillon **bull 2022-26 (mean_R +0,086 = 5× normal)**, pas forward. 1-step FTMO (3 % daily + trailing) = 19-41 %, mort.

**{1 essai} + {FTMO} + {>60 %} = incompatibles. Choisir 2 :** (a) FTMO+>60 % → 3-4 essais (~70 %) ; (b) 1 essai+>60 % → quitter FTMO pour 1-step DD-large faible-cible (~55-58 %) ; (c) 1 essai+FTMO → accepter ~45 %.

---
*Sim : `outputs/orb_v2e7.parquet` + sim container/Sharpe-curve inline. Stratégie : `ORB_deepening_NQ.md`. Prior : `OPTIM_ftmo_2step_uncapped.md` (révisé : 79 % était bull-2022-26 N≈1), `OPTIM_regime_timing_intraday.md`.*
