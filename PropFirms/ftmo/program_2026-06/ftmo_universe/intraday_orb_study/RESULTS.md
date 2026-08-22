# FTMO 2-step — étude intraday « page blanche » (2026-06-02)

Reconstruction indépendante, à partir des données brutes du dossier, sans réutiliser les
conclusions antérieures. Objectif testé : passer le challenge FTMO 2-step ($10k, +10 % puis
+5 %, DD jour 5 %, DD total 10 % statique à $9 000) avec **>50 % de chances en <2 mois**.

## Méthode (résumé)
- **Données** : M1 brut, horloge broker EET (vérifiée par le profil de volatilité intraday :
  pic à 16:30 EET = open cash US). FX & or 2018-2026 ; indices US M1 réels seulement 2021+.
  Pour un test multi-régime honnête de l'ORB, validation sur **NQ databento 2010-2026 (16 ans,
  flag RTH)**, proxy propre du Nasdaq (≈ US100.cash). Coûts réalistes : spread (colonne tick) +
  commission specs + slippage (~1 bp RT indices, ~0,6 bp EURUSD).
- **3 familles intraday testées** sur le même moteur (pas de look-ahead, fills intrabar
  conservateurs, sortie à la clôture) : mean-reversion VWAP/z, ORB (cassure de l'opening range),
  momentum intraday.
- **Simulateur FTMO 2-step** : sizing par le risque (ρ % d'équité/trade), stop journalier perso,
  floor-taper (risque ∝ distance au floor statique), Monte-Carlo par **stationary block bootstrap**
  (préserve le clustering de volatilité ; vérifié stable pour blocs 1→40).

## Screen des familles (après coûts)
| Famille | Meilleur instrument | meanR net | Sharpe quot. | two-sided ? | Verdict |
|---|---|---:|---:|---|---|
| **ORB** | **US100 / NQ** | **+5,3 bps** (fill réaliste) | **~1,0 (2021+)** | oui (L+/S+) | **gagnant** |
| Mean-reversion VWAP | tous | −0,5 à −1,5 bps | négatif | — | tué par les coûts |
| Momentum intraday | US100 | +0,9 bps | 0,35 | non | trop faible |

ORB sur US500/GER40/XAU : faible (Sharpe 0,24-0,53). Le gagnant net est **l'ORB Nasdaq**.

## Le point dur : l'ORB n'a pas d'alpha par-trade (c'est un effet de régime)
Sur **2021-2026** l'ORB US100 paraît excellent (Sharpe ~1,0-1,4). Mais sur **16 ans de NQ avec
fills réalistes (next-bar)** : meanR **+0,47 bps, Sharpe 0,11, t=0,4 ≈ zéro**, et **négatif à 2 bps**
de coûts. L'edge est concentré **2021-2024** (2022 : +10,9 bps) et **négatif 2010-2020**
(2015 : −5,9 ; 2020 : −9,3). Voir `figs/fig1_regime.png`. → le « beau » résultat récent = régime
favorable + hypothèse de fill optimiste, **pas un edge robuste**.

## p(pass) — le chiffre demandé (single attempt, Monte-Carlo)
| Scénario | meilleur **p(<2 mois)** | bust | p(éventuel, sans limite) |
|---|---:|---:|---:|
| **Honnête (16 ans, fills réels)** | **27 %** (ρ=3 %) | 70 % | ~32 % |
| Fill optimiste (au niveau) | 30 % | 67 % | ~35 % |
| **Si le régime 2021+ persiste** | **38 %** (ρ=3 %) | 56 % | ~54 % |

**Aucun sizing n'atteint 50 % en <2 mois, dans aucun scénario.** C'est structurel : sur une
barrière +10 %/−10 % puis +5 %/−10 % sans vrai edge par-trade, le p(pass) éventuel plafonne
près de ~33 % (produit de deux ruines du joueur quasi-driftless), et la contrainte de temps le
fait baisser. Le compromis est fondamental (`fig3`) : **vite** (ρ élevé → p(<2 mois) plus haut
mais ~70 % de bust) **ou sûr** (floor-taper → 0 % bust mais grind de plusieurs mois).

## La seule route honnête vers >50 % en <2 mois : essais multiples
p(≥1 succès sur n essais) = 1−(1−p)ⁿ, chaque essai sizé pour la vitesse (ρ≈3 %), petit compte
($10k, ~155 € remboursés au 1er payout) :

| | 1 essai | 2 essais | 3 essais | 4 essais |
|---|---:|---:|---:|---:|
| Honnête (p=27 %) | 27 % | 47 % | **62 %** | 72 % |
| Régime 2021+ (p=38 %) | 38 % | **62 %** | 77 % | 86 % |

→ **>50 % en <2 mois = 3 essais (cas honnête) ou 2 essais (si régime favorable)**, en parallèle.
C'est de l'ingénierie de barrière + structure, **pas un alpha**.

## Verdict
1. Le meilleur véhicule intraday FTMO-tradeable de ce dataset est **l'ORB Nasdaq (US100.cash)**,
   two-sided et compatible DD-journalier (la perte d'un jour ≈ ρ, sous la limite 5 %).
2. Il **n'a pas d'edge par-trade robuste** (Sharpe 16 ans ≈ 0,1) ; sa force récente est
   régime-conditionnelle. À traiter comme une exploitation de la structure de barrière, pas une
   machine à alpha.
3. **>50 % en <2 mois sur un seul essai n'est pas atteignable** ici (max ~27-38 %). Atteignable
   par **2-3 essais parallèles** sizés agressivement (bust individuel ~60-70 % assumé).
4. EV net marginale (frais coulés ~1-2 essais avant funding). Le vrai livrable CV = la **rigueur**
   (timezone vérifiée, fills réalistes, multi-régime, first-passage), pas le jackpot.

Fichiers : `ftmo_orb_results.csv` (table complète), `figs/` (5 graphiques), `code/` (moteur reproductible).
