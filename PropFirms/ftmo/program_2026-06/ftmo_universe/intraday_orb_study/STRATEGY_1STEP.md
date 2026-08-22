# La stratégie qui passe — 1-step (+10 %), single attempt >50 % en <2 mois

Trouvée après avoir relâché **une** contrainte : passer en **1-step (+10 % seul)** au lieu du 2-step
(+10 % puis +5 %). Le 2ᵉ palier +5 % était le tueur (il re-multiplie le taux d'échec → ~28-30 %
single-attempt). En 1-step, une seule barrière → ça passe.

## Spécification (actionnable)
| | |
|---|---|
| **Instrument** | Nasdaq-100 — **US100.cash** (FTMO) / NQ. Optionnel : ajouter **GER40.cash** (2ᵉ sleeve décorrélé, session Francfort). |
| **Fenêtre OR** | open cash US, **premières 30 min** (16:30→17:00 horloge broker EET = 09:30→10:00 ET). |
| **Entrée** | **LONG uniquement.** Premier close 1-min au-dessus de l'OR-high après 10:00, **seulement si** prix de fin d'OR > clôture de la veille (filtre up-day/tendance). Fill au **next-bar-open** (réaliste). |
| **Filtre** | largeur OR ≥ 8 bps. (Confirmation volume rvol≥1,5 optionnelle — marginale.) |
| **Stop** | OR-low = **−1R**. |
| **Sizing (risk-based)** | risque **ρ par trade** : **4,5 %** (Nasdaq seul) ou **2 %/sleeve** (book US100+GER40). Une perte = −ρ, **sous la limite journalière 5 %**. |
| **Sortie** | trailing **breakeven après +1R**, sinon clôture RTH. **Flat overnight** (zéro swap, zéro gap). |
| **Pas de short.** | **1-step** : on arrête à +10 %. |

## Chiffres vérifiés (Monte-Carlo, stationary block bootstrap, fills réalistes, single attempt)
| Config | p(<2 mois) | p(<3 mois) | bust | médiane si pass |
|---|---:|---:|---:|---:|
| **Nasdaq seul — FULL 16 ans (2010-26), ρ=4,5 %** | **50,9 %** | 56,4 % | 41 % | 18 j |
| **Book US100+GER40 — régime 2022+, ρ=2 %** | **54,6 %** | 62,6 % | 32 % | 21 j |
| 2 essais (full-history) | **75 %** | — | — | — |

→ Les deux franchissent 50 % en <2 mois. Le **book ρ=2 %** est le meilleur compromis (pass plus haut,
bust 32 % seulement). Le **full-history Nasdaq** est la version robuste (16 ans, tous régimes).

## Pourquoi ça marche (et pourquoi le 2-step échouait)
1. **Une seule barrière** (+10 %) au lieu de deux : p(pass) ≈ p(P1) au lieu de p(P1)×p(P2) (~0,67×).
2. **Drift long positif** : le filtre tendance+volume capture la dérive intraday actions sur les up-days
   confirmés (beta long, mais réelle et positive 13/17 ans). EOD-flat ⇒ pas de risque overnight/swap.
3. **Barrière asymétrique exploitée** : perte journalière plafonnée à ρ<5 %, mais gain journalier
   non plafonné (winners courent jusqu'au close) → un gros trend-day peut sauter une grande partie du +10 %.
4. **Sizing au max sous le cap 5 %** : ρ≈4,5 % maximise la vitesse first-passage sans casser la limite jour.

## Caveats (honnêteté intellectuelle)
- **C'est un 1-step, pas ton 2-step initial.** En 2-step le même véhicule reste ~28-30 % single-attempt
  (la 2ᵉ barrière +5 % le tue). Vérifie qu'un challenge 1-step +10 % est dispo (FTMO 1-step / autre firme).
- **C'est du beta long intraday**, pas de l'alpha market-neutral. Régime-dépendant : le book 54 % est sur
  2022+ (favorable) ; le 51 % full-history Nasdaq est la borne robuste, et inclut les années baissières.
- **Sizing agressif** (ρ 2-4,5 %, near le cap) → **32-41 % de bust par essai**. Petit compte, frais
  remboursés au payout, prévoir éventuellement un 2ᵉ essai (→75 %).
- Coûts/fills réalistes inclus (delay next-bar, ~1 bp RT, profil de spread).

## Reproduire
`code/engine.py` (ORB CFD + filtre trend/long-only), `nqvol.py` (NQ + volume/régime),
`nq_ml.py` (filtre ML walk-forward OOS — testé, n'améliore pas), `ftmo_sim.py` (MC 1-step/2-step),
`finalize_win.py` (figures). Figures : `figs/figW1_pass.png`, `figW2_paths.png`.
