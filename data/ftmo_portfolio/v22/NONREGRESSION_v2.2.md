# NON-RÉGRESSION v2.2 — ancres + tolérances
*Chaque ancre régénérée par ce run (2026-06-10). Commandes depuis `v22/` ;
stack gelé ; /usr/bin/python3. Toute future modification doit re-passer CE fichier.*

| # | Commande / source | Ancre attendue | Tolérance |
|---|---|---|---|
| 1 | `run_battery.py` → challenge_91 | IS 90.6 / OOS 83.4 / **pooled 87.0** | ±1.5 pt |
| 2 | idem → CDF | 30j 41.6 / 61j 70.3 / 182j 98.9 / 270j 100.0 ; **monotone** | ±2 pts ; monotonie STRICTE |
| 3 | idem → essais / med_t | 3.24 ; IS 35j / OOS 29j | ±0.2 ; ±3j |
| 4 | idem → funded (ORB_RT_BPS=era) | IS $684 / OOS **$2,632**, bust 3.2/1.0%, payouts 3.3/10.8 | ±10% ; ±1 pt ; ±1 |
| 5 | idem → VAL / EV chaîne | **$1,422 / +$926** | ±10% (VAL re-dérivée, jamais héritée) |
| 6 | idem → placebo | 71.2% ; edge **+15.8 pts** | edge ∈ [+8 ; +25] |
| 7 | idem → anticausal −1j | 83.1% ≤ pooled | ne doit JAMAIS dépasser pooled +1 pt (= leak) |
| 8 | idem → swap×1.5 / spread×2 | 86.4 / 77.9 | ±2 pts |
| 9 | idem → marge pré-cap | p50 21 / p99 79 / max 116 ; bind 5.6% | ±10 pts ; ±2 pts |
| 10 | idem → gap weekend ×1.5/×2 | 84.9 / 85.1 | ≥ pooled −5 pts |
| 11 | idem → vm 10/12/16/18 | 84.2 / 83.8 / 84.4 / 84.6 | tous ∈ pooled ±6 pts (pas de falaise) |
| 12 | `run_pathboot.py` | moyenne 87.6 / p5 76.7 / **min 71.4** / P(>50%)=100% | min > 60 ; P=100% |
| 13 | micro-ORB | 9,248 poses ; **100% cohortes ≥1** ; backstop **50** | 100% strict ; backstop < 100 |
| 14 | identité comptable | assertions cash-conservation par tentative : 0 levée | STRICT (exact) |
| 15 | `diag_runner_equiv.py` | micro-OFF+backstop = 88.8/87.8/**88.31** (≡ référence cleanroom 88.3) | ±0.5 pt (équivalence moteur) |
| 16 | ancres de coûts (héritées audit, inchangées) | EURUSD 1.13 / US100 2.20 / BTC 18.50 bps ; swap US100 −$6.45/lot/n ; +3.45bps t=2.10 ; 967 trous | ±20% ; exact |
| 17 | borne théorique compteur | micro-ORB coûte ≤ 2 pts vs token idéal (87.0 vs 88.3) | Δ ∈ [0 ; 2.5] |

**Procédure ORB_RT_BPS (verdict démo N=60)** : éditer `config_v22.py:ORB_RT_BPS` (float bps
all-in mesuré), relancer la SECTION funded de `run_battery.py` → nouvelles ancres #4/#5.
Le challenge (#1-3, 6-13) est INSENSIBLE à ce paramètre par construction v2.2 (ORB off) —
toute dérive du challenge après ce changement = bug, STOP.
