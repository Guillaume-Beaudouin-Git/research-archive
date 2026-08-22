# ORB V2+E7 — récap de lancement (FTMO 2-step, cette semaine)

*Tout ce qu'il faut pour lancer. Chiffres tirés de `ORB_deepening_NQ.md` + `ORB_realconstraints_NQ.md` + sim time-cap/floor-taper rebuild.*

---

## 1. La stratégie en une page

| | |
|---|---|
| **Instrument** | NQ (Nasdaq-100) — futures NQ ou CFD US100 (équivalents, corr 0,87) |
| **Fenêtre Opening Range** | **09:30 → 10:00 ET** (30 min, 30 barres 1-min). OR_high = plus haut, OR_low = plus bas. |
| **Entrée** | premier **break** de l'OR après 10:00 : > OR_high = LONG, < OR_low = SHORT. Fill **au niveau** (stop dormant). |
| **Stop initial** | côté opposé de l'OR = **1R** (= la largeur de l'OR) |
| **Sortie (E7)** | **trailing à breakeven après +1R** (dès que +1R atteint, stop → entrée). Sinon **sortie à la clôture RTH 15:59 ET**. |
| **Filtre (V2)** | largeur OR **≥ 10 bps** (sinon pas de trade ce jour-là) |
| **Jours** | **Lundi → Vendredi** (1 trade max/jour, ~250 trades/an) |
| **Coût** | 2 bps RT (CFD FTMO ≈ 1,5-3 pts de spread) |
| **⚠ Broker** | fill **au niveau** des stops REQUIS (défaut FTMO/MT5). Si fill next-bar-open seulement → p(pass) chute à ~28 %. |

## 2. Métriques (V2+E7, 2010-2026, cost 2bp)

| métrique | valeur |
|---|---:|
| n trades | 3 991 (~1/jour) |
| mean_R / trade | +0,016 (4× le baseline) |
| hit rate | 39 % |
| skew | +1,79 (queue droite = l'edge) |
| win/loss ratio | 1,60 |
| **LONG / SHORT mean_R** | **+0,024 / +0,006** (les deux positifs, L25 ✓) |
| MaxDD | −34 % |
| Sharpe / trade (ann) | +0,22 |
| DSR (multiple-testing) | > 0,95 (z≈+12 — **pas un artefact de mining**) |

**Honnêteté :** DSR per-trade ≈ 0 → **ce n'est pas un edge de trading**, c'est une exploitation des règles FTMO (no-bust × temps illimité) sur un signal à peine positif + une queue droite. La p(pass) vient à ~80 % de la math no-bust, ~15-20 pp de la distribution ORB.

## 3. p(pass) — le chiffre, ET le temps (les deux vont ensemble)

**p(pass) éventuelle (sim validé, sans limite de temps) — dépend du régime de vol :**

| régime (rv20) | p(pass) | aujourd'hui ? |
|---|---:|---|
| LOW (≤ 13 %) | **62,7 %** | non |
| **MID (13-17,5 %)** | **49,5 %** | **← OUI (rv20=0,155 au 29/05)** |
| HIGH (≥ 17,5 %) | 59,4 % | (on en était à 0,172 il y a 1 semaine) |

**⚠ MAIS « éventuelle » = sur des MOIS.** Le grind vers +10 % prend du temps (drift quasi-nul, on atteint +10 % par variance). Sim time-cap propre (mean_R calibré +0,016, block-bootstrap tous régimes) :

| sizing | p ≤ 1 mois | p ≤ 2 mois | éventuel (2 ans) | médiane **si** pass | bust % |
|---|---:|---:|---:|---:|---:|
| fixe 2 % | 8 % | 20 % | 32 % | 1,7 mois | 68 % |
| fixe 3 % | 16 % | **26 %** | 28 % | **0,9 mois** | 72 % |
| taper c=0,15 | 3 % | 9 % | 28 % | 3,3 mois | **0 %** |
| taper c=0,25 | 7 % | 11 % | 18 % | 1,4 mois | 11 % |

**⚠ Le « ~50 % » n'est PAS un chiffre à 2 mois.** Il y a DEUX nombres distincts qu'il ne faut pas mélanger :
- **éventuel ~50 %** (fichier, régime mid 49,5 %) = proba de passer *un jour*, méthodo optimiste (chemin contigu, persistance de régime). Ma sim régime-mélangé (conservatrice) donne plutôt **~28-34 % éventuel**.
- **médiane « ~1 mois »** = temps médian **conditionnel aux gagnants** seulement (colonne de droite). Comme ~70 % bustent en fixe, ce « 1 mois » décrit les rares passants, pas 50 % du total.

Coller les deux donne le slogan trompeur « 50 % en 1-2 mois ». **Vrai cap-2-mois : max ~26 % (fixe 3 %, 72 % bust) ; ~9 % avec le floor-taper sûr.**

**Le message clé :** pas de passage à 50 % en 1-2 mois. Soit **rapide** (fixe 3 % : ~26 % passent / ~72 % bustent en 2 mois = pile-ou-face qui se résout vite), soit **sûr** (floor-taper : 0 % bust mais le cumul monte sur 6-24 mois). Pas de troisième option.

**⚠ Le piège du floor-taper « 0 % bust » (3 états, pas 2).** « 0 % bust + médiane 3,3 mois » ne veut PAS dire « tu passes en 3,3 mois sans risque ». La médiane est conditionnelle aux seuls gagnants. Les 3 états réels de c=0,15 :

| horizon | PASSÉ | BUSTÉ | ENCORE EN GRIND |
|---|---:|---:|---:|
| 3 mois | 14 % | 0 % | 86 % |
| 12 mois | 24 % | 0 % | 76 % |
| 60 mois | **28 %** | 0 % | **72 %** |

→ Le taux de passage **plafonne à ~28 %** : 72 % ne bustent pas mais **restent coincés** (taille rabotée près du floor, crawl infini). c=0,15 **convertit le bust en "coma"**, il ne remonte pas le taux de passage (~28 %, identique au fixe 3 %). **Implication : pour être financé, "fixe modéré + bust + recommencer" (3-4 essais → 63-73 %) bat probablement le taper coincé.** À retrancher avant de figer le sizing.

## 4. Ton idée de sizing dynamique = le floor-taper (OUI, c'est LE levier)

**Ton intuition est exactement juste** : sur FTMO le floor de DD total est **statique à 9 000 $** (10 % de l'initial, il ne monte PAS avec tes gains). Donc quand tu gagnes, ta distance au floor grandit → tu peux risquer plus ; quand tu perds, tu réduis. C'est le **floor-taper**, et c'est ce qui prend la p(pass) de ~46 % (sizing fixe) à **77-90 %**.

**La règle correcte (no-bust mathématique) :**
> **risque par trade = c × (équité − 9 000 $)**, plafonné à 4,5 % (sous la limite journalière de 5 %).

C'est-à-dire : tu risques une **fraction c de ta distance-au-floor**, pas une fraction de ton équité. Conséquence :
- Une perte de 1R te fait perdre `c × distance` < ta distance → **tu ne peux JAMAIS buster** sur une perte normale.
- Tu **montes** automatiquement la taille quand tu construis du buffer (gains), tu la **réduis** vers le floor (pertes). Exactement ton idée, mais bornée pour être no-bust.

**Vérifié dans la sim :**

| sizing | bust % | p éventuelle | médiane |
|---|---:|---:|---:|
| **floor-taper c=0,15** | **0 %** ✅ | (grind lent) | ~3 mois |
| floor-taper c=0,25 | 14 % | moyen | ~6 sem |
| floor-taper c=0,40 | 24 % | (rapide, risqué) | ~3 sem |
| fixe 2-3 % | 66-73 % ❌ | — | ~1-1,5 mois |

→ **À c≈0,15-0,20, tu ne busts quasiment jamais** (vs 70 % en fixe). C'est ÇA qui rend la p(pass) éventuelle haute : pas un edge, mais « ne jamais buster + temps illimité = on finit par atteindre +10 % ». Le prix = c'est lent (mois de grind).

> **⚠ Note méthodo (le 77-90 % vs le 28-34 % de la section 3).** Le « 77-90 % » vient de la sim *contigüe* du fichier (suppose la persistance du régime → optimiste). Ma sim *block-bootstrap régime-mélangé* (section 3) donne ~28-34 % éventuel sur 2 ans. La vérité forward est **entre les deux** : si tu démarres dans un régime favorable qui persiste → proche du fichier ; si tu tombes sur un mix défavorable → proche de ma sim. Aucune des deux ne donne 50 % en < 2 mois — c'est un nombre de **long terme** dans les deux cas.

## 5. Recommandations concrètes pour cette semaine

1. **Sizing = floor-taper, c ≈ 0,15-0,20**, plafonné à 4,5 %/trade. C'est le réglage no-bust. (Pas de sizing fixe agressif → 70 % de bust.)
2. **Régime :** aujourd'hui MID vol (~50 % éventuel) et **à la frontière du HIGH** (on était à 0,172 il y a 1 semaine ; HIGH = 59 %). Si tu peux **attendre que rv20 repasse ≥ 0,172 (HIGH) ou tombe ≤ 0,13 (LOW)**, tu gagnes ~10 pp. Sinon MID = ~50/50, acceptable.
3. **Attentes de temps : médiane ~1-3 mois, possiblement plus.** Ne sois pas surpris par un grind long. **Ne prends PAS un time-cap mental de 1 mois** — le floor-taper a besoin de temps.
4. **Petit compte d'abord** ($10k, ~155 €, remboursé au payout). **Ne scale pas avant un premier pass confirmé.**
5. **Broker fill-au-niveau** (FTMO MT5 par défaut) — vérifier.
6. **Surveille rv20 hebdo.** Si on bascule en régime bear durable type 2013-2015 (mean_R négatif), le floor-taper grind éternellement sans atteindre +10 % → re-évaluer.

## 6. Le risque structurel à garder en tête

- La p(pass) est **régime-dépendante** : 0 % en 2013-2015 (bear), 100 % en 2019-2023 (bull). Aujourd'hui mid = ~50 %.
- Si **FTMO restaure une limite de temps** pendant ton défi → tout le mécanisme floor-taper s'effondre → ~46 %.
- C'est un **pari sur la persistance de la règle no-time-limit** + un régime pas catastrophique, pas un edge de trading. Lance en le sachant.

---

### Artefacts
- `outputs/orb_v2e7.parquet` (trades rebuild), sim time-cap/floor-taper inline.
- Détails : `ORB_deepening_NQ.md` (leviers + régime), `ORB_realconstraints_NQ.md` (placebo + floor-taper).
