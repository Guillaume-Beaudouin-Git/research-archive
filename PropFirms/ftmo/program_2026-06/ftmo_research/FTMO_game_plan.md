# FTMO — plan de jeu (le document actionnable qui clôt l'arc)

*Comment atteindre l'objectif >70 % de financement, honnêtement, avec ce qu'on a. 2026-06.*

---

## Le recadrage (la conclusion de tout l'arc)

> **>70 % sur UN essai avec une stratégie retail n'existe pas** — prouvé sur ~1 100+ trials, toutes les familles, toutes les classes d'actifs FTMO. **>70 % de FINANCEMENT s'atteint par la STRUCTURE :** un véhicule par-essai correct **× essais multiples** (math 1−(1−p)ⁿ). C'est de l'ingénierie de barrière, pas de la chasse au signal.

---

## 1. Le véhicule par-essai : l'incumbent (ORB-30min + floor_taper)

**p(pass) et temps vont TOUJOURS ensemble** (arbitrage first-passage : plus on size petit, plus p monte mais plus c'est lent).

| candidat (DD-journalier inclus) | p(pass)/essai | temps/essai (si pass) | commentaire |
|---|---:|---:|---|
| **Incumbent ORB-30min + floor_taper** | **~46–50 %** | **~1–3 mois** (intraday, ~1 trade/j) | exploitation des règles. Gagne sur p ET temps. |
| Book combiné, sizing lent (k=1,5) | 41 % | **16 mois** ❌ | trop lent (Sharpe 0,25 → dérive lente vers +10 %) |
| Book combiné, sizing rapide (k=4) | 26 % | 2,7 mois | rapide mais p s'effondre |
| Overnight harvester | 31 % | ~1,5–3,5 ans ❌ | mort au vrai swap + lent |
| Random | 33 % | — | référence |

**Pourquoi le book combiné ne gagne pas — sur les DEUX axes :** (a) la limite de **DD journalier 5 %** cape le levier (monter la taille fait sauter le 5 % sur un mauvais jour → p baisse) ; (b) son Sharpe honnête (0,25 daily point-in-time) est trop bas → au sizing qui donne le meilleur p (41 %), il met **16 mois/essai** (impraticable). L'incumbent, en tradant intraday, atteint ±10 % en **~1–3 mois** ET avec un p plus haut. **→ Véhicule retenu : l'incumbent.** (Temps incumbent = estimation ; à confirmer via `trailing_dd_simulator.py`.)

## 2. Le levier décisif : essais multiples

**⚠ Lecture correcte : 1 − (1−p)ⁿ = la proba qu'AU MOINS UN des n essais passe** (PAS que chaque essai passe à ce taux). Chaque essai individuel reste à p (~48 %). « 2 essais → 73 % » veut dire : sur 2 tentatives, 73 % de chances qu'au moins une réussisse (27 % qu'aucune ne passe).

| p par-essai | 1 essai | **2 essais** | **3 essais** | 4 essais |
|---|---:|---:|---:|---:|
| **48 % (incumbent)** | 48 % | **73 %** | **86 %** | 93 % |
| 41 % (book combiné) | 41 % | 65 % | 79 % | 88 % |

**→ 2 essais de l'incumbent → 73 % d'avoir ≥1 financement. 3 essais → 86 %.**

**Avec le temps (incumbent, ~1–3 mois/essai) :**
- **Parallèle** (2-3 comptes en même temps) : 73–86 % en **~1–3 mois**, mais 2-3 frais payés d'avance.
- **Séquentiel** (un à la fois jusqu'au pass) : 73–86 % étalé sur **~3–9 mois**, mais tu arrêtes de payer dès funded.

(Le book combiné à 16 mois/essai → 2-3 essais = **des années** : exclu pour cette raison aussi.)

## 3. L'économie honnête (financé ≠ rentable)

- **Frais :** ~155 € (compte $10k), **remboursé au premier payout**.
- **Coût coulé attendu jusqu'au financement :** ~1/0,48 ≈ 2,1 essais → ~1-2 frais coulés (~200-300 €) avant d'être funded.
- **Le caveat critique :** l'incumbent est ~0 alpha par-trade (exploitation de règles). Une fois funded, atteindre un payout (+5 %) est une **loterie ~67 %** par cycle ; sur 3 essais, p(≥1 payout) ≈ 70 %. Le payout net (~+5 % × 80 % split + refund) couvre les frais coulés mais **l'EV nette est marginale et dominée par la variance** (constat confirmé sur le projet de Briux). 
- **→ Conclusion économique :** >70 % de **financement** est atteignable et peu cher ; mais **le profit net est faible/variance-dominé** sans vrai edge. À traiter comme une **option à petite mise**, pas une machine à imprimer.

## 4. Le plan concret

1. **Véhicule :** ORB-30min + floor_taper sur NQ/US100 (Strategy C / l'incumbent). Sizing géré par `trailing_dd_simulator.py` + `ftmo_swaps.py` (garde-fou swap-sign).
2. **Choisir le bon challenge :** comparer **1-step vs 2-step** (le 1-step a un p par-essai plus haut, une seule barrière) et **FTMO vs Apex/Topstep/Tradeify** (modèle de DD qui colle mieux au profil lumpy) — tourner `trailing_dd_simulator.py` par firme avant achat. Objectif : maximiser le p par-essai.
3. **Budget d'essais :** prévoir **2-3 essais** (financement >70-86 %). Petit compte ($10k, ~155 €/essai) pour limiter le coût coulé ; scaler la taille seulement après un premier financement.
4. **Garde-fous :** swap-sign (ne jamais tenir le côté swap-négatif overnight), catastrophe-halt, règle d'inactivité 30 j (si une stratégie reste flat).

## 5. Ce qu'on garde de l'arc (le toolkit réutilisable)

- **Le protocole anti-faux-positif** (two-sided + délai/dynamique + DSR + OOS + swap-sign) — comme **gate**, pas mineur. C'est le vrai livrable.
- **Les vrais edges décorrélés** (turn-of-month equity OOS-stable, saisonnalité commodities) — trop faibles pour FTMO seuls, mais des **briques** pour un book personnel hors-propfirm où la barrière symétrique ne s'applique pas.
- **`ftmo_swaps.py`** (garde-fou), **dataset COT 18 ans**, **commod_daily**, les moteurs de backtest.

## 6. Verdict final de l'arc

**Le vrai gain de cette recherche n'est pas une stratégie magique — c'est :**
1. La **preuve rigoureuse** qu'aucun alpha price-pattern retail ne bat la barrière FTMO (économise tous les futurs essais aveugles).
2. Le **process** qui distingue l'edge de l'artefact (et qui a évité plusieurs fois de risquer du capital sur un faux positif : same-bar→delay-1, static→dynamic carry, monthly→daily-DD).
3. Le **plan honnête pour >70 %** : incumbent + 2-3 essais, avec l'EV vue clairement.

**Pour le CV/GitHub, c'est exactement ce qui fait un bon quant : la discipline et l'honnêteté intellectuelle, pas le jackpot.** Le "non" gagné en profondeur vaut plus qu'un faux "oui".

---

### Entrée research-log
*FTMO objectif >70 % — RÉSOLU par structure, pas par signal. Véhicule par-essai = incumbent ORB+floor (~46-50 %, DD-journalier inclus) ; book combiné de vrais edges (ToM+saison+momentum, Sharpe 0,25) = ~41 %, ne bat pas l'incumbent. >70 % financement = incumbent × 2-3 essais (1−(1−0,48)² = 73 %). EV nette marginale (rules-exploitation, ~0 alpha) → traiter comme option petite-mise. Toolkit : protocole anti-faux-positif, ftmo_swaps, dataset COT.*

### Deliverables liés
`FTMO_RECAP.md` (récap maître), `FTMO_decision_memo.md`, + les 13 deep-dives. Code : `outputs/book_daily.parquet` (book combiné), `code/ftmo_swaps.py`.
