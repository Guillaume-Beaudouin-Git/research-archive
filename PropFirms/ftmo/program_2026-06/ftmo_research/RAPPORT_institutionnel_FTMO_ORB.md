# Rapport de décision — Challenge propfirm via la stratégie ORB
### Document de délibération d'équipe · Desk systématique · 2026-06-02 · v1.0

> **Statut épistémique (à lire en premier).** Toutes les métriques de ce rapport sont issues de **backtest + simulation Monte-Carlo sur données historiques**. **Zéro jour de trading live.** Les chiffres sont des estimations d'ordre de grandeur, pas des garanties. Les conclusions *structurelles* (math de barrière) sont robustes ; les *niveaux absolus* de p(pass) sont incertains (±10-20 pts, dominés par le régime). Ce document est conçu pour la délibération, pas comme une recommandation d'investissement engageante.

---

## 1. Synthèse exécutive (BLUF)

**Objectif posé :** passer un challenge FTMO 2-step (compte $10k ; Phase 1 +10 %, Phase 2 +5 % ; perte journalière max 5 % ; perte totale max 10 % statique ; min 4 jours ; **sans limite de temps**) avec une probabilité **> 60 %**, en **un seul essai**.

**Conclusion centrale :** cet objectif, tel quel, **n'est pas atteignable** avec une stratégie price-pattern retail. Les trois contraintes **{1 essai} + {FTMO} + {>60 %} sont mutuellement incompatibles** — démontré par la math de barrière et confirmé sur 16 ans de données. On peut en satisfaire **deux sur trois**, pas les trois.

**Ce qui EST atteignable :**

| Si l'équipe priorise… | …en lâchant… | Résultat réaliste |
|---|---|---|
| FTMO + >60 % | 1 essai → 3-4 essais | ~70 % d'être financé (arithmétique multi-essais) |
| **1 essai + maximiser p(pass)/temps** | **FTMO → 1-step DD-large** | **~48-52 % en médiane ~2 semaines** |
| 1 essai + FTMO | >60 % → ~25-42 % | le vrai plafond honnête d'un essai FTMO |

**Recommandation pour délibération :** si le critère est « maximiser p(pass) dans le temps le plus court par essai », le véhicule optimal est un **challenge 1-step hors-FTMO à drawdown large et statique**, stratégie ORB inchangée, sizing 2,5 % → **~48-52 % par essai, médiane ~2 semaines**. Aucun véhicule à essai unique ne dépasse ~55 %. Le franchissement de 60 % n'est possible que par **essais multiples** (structure, pas signal).

**Risque #1 à acter :** le résultat est **dominé par le régime de marché** (volatilité/tendance) au moment du départ — non prévisible — avec une dispersion historique de **31 % (2015) à 74 % (2022)** pour le même véhicule. Le « ~50 % » est une tendance centrale, pas un acquis.

---

## 2. Objectif & contraintes

Le challenge FTMO 2-step impose une **double barrière en série** sur un compte à drawdown borné :

| Paramètre | Phase 1 (Challenge) | Phase 2 (Verification) |
|---|---|---|
| Cible de profit | +10 % | +5 % |
| Perte journalière max | 5 % (du solde initial) | 5 % |
| Perte totale max | 10 % **statique** | 10 % statique |
| Jours min | 4 | 4 |
| Limite de temps | **aucune** (2026) | aucune |

*(Source : FTMO Trading Objectives, vérifié 2026-06. FTMO propose aussi un produit 1-step — voir §5.3 — avec daily 3 % + drawdown **trailing**, qui dégrade fortement le profil pour cette stratégie.)*

La difficulté structurelle vient de la **série de deux barrières** : p(financé) = p(Phase 1) × p(Phase 2 | Phase 1). Comme la Phase 2 (+5 %) est elle-même une mini-barrière, le produit s'écrase bien en dessous de la probabilité d'une phase unique.

---

## 3. La stratégie évaluée — ORB V2+E7

**Opening Range Breakout 30 minutes sur NQ (Nasdaq-100).**

| Élément | Spécification |
|---|---|
| Instrument | NQ (futures ou CFD US100, corr 0,87) |
| Fenêtre Opening Range | 09:30 → 10:00 ET (30 barres 1-min) |
| Entrée | premier *break* de l'OR : > OR_high = long, < OR_low = short, fill au niveau |
| Stop initial | côté opposé de l'OR = 1R (largeur de l'OR) |
| Sortie (E7) | trailing à breakeven après +1R ; sinon clôture RTH 15:59 ET |
| Filtre (V2) | largeur OR ≥ 10 bps |
| Fréquence | ~1 trade / jour ouvré |
| Coût modélisé | 2 bps round-trip |

**Métriques per-trade (2010-2026, n=3 993, calibrées) :**

| Métrique | Valeur | Lecture |
|---|---:|---|
| mean_R / trade | +0,016 | edge brut très faible |
| Hit rate | 39 % | majorité de pertes |
| Skew | +1,79 | l'edge vient de la queue droite |
| Win/Loss ratio | 1,60 | les gains paient les pertes fréquentes |
| Long / Short mean_R | +0,024 / +0,006 | les deux positifs (test two-sided ✓) |
| Sharpe / trade (annualisé) | **0,22** | **le facteur limitant — voir §6** |
| MaxDD (série de trades) | −34 % | |

> **Avertissement d'honnêteté intellectuelle.** Le test de significativité multiple (DSR Bailey-López de Prado) sur le Sharpe per-trade **échoue** (per-trade SR ≈ 0,014). **L'ORB n'a quasiment pas d'edge de trading exploitable.** Ce qui rend un passage de challenge possible n'est pas un alpha, c'est **l'exploitation des règles** (barrière + temps illimité) appliquée à une distribution à queue droite. À traiter comme une *option à faible mise*, pas comme une machine à générer du rendement.

---

## 4. Méthodologie & provenance des chiffres

*(Section demandée explicitement — « d'où sortent nos métriques ».)*

**Chaîne de production, étape par étape :**

1. **Donnée brute (solide).** Bougies **NQ 1-minute databento, 2010-2026** (16 ans). Source primaire, non dérivée.
2. **Reconstruction des trades.** Application de la logique ORB V2+E7 à la donnée 1-min → **3 993 trades**, chacun avec son résultat en R. *Limite : la reconstruction idéalise le fill du stop (exactement 1R, sans gap), et donne mean_R +0,007 ; le build d'origine du desk donne +0,016. Nous retenons +0,016 (le plus optimiste des deux — à noter pour la délibération).*
3. **Simulation Monte-Carlo.** Rééchantillonnage par **blocs de 21 jours** (block-bootstrap, préserve l'autocorrélation court-terme) → **12 000 comptes-challenge synthétiques** passés dans les règles du container → comptage pass / bust / temps.
4. **Lecture des sorties :**
   - **« 52 % »** = fraction des 12 000 comptes simulés qui atteignent la cible avant de buster.
   - **« ~2 semaines »** = **médiane** du temps-pour-passer **parmi les gagnants** (étalement réel : p10 = 0,6 sem, p90 = 5,2 sem). Les comptes qui bustent se résolvent encore plus vite.

**Ce qui est SOLIDE vs MOU :**

| Élément | Statut | Confiance |
|---|---|---|
| Donnée 16 ans NQ 1-min | source primaire | élevée |
| Conclusions structurelles (1-step ≈ 2× 2-step ; mur Sharpe ; <2 mois ≠ 60 %) | math de barrière | élevée |
| Niveau absolu p(pass) (48-52 %) | dépend de mean_R + bootstrap + exéc + régime | **modérée à faible (±10-20 pts)** |
| Validité live | **0 jour tradé** | nulle (tout est backtest) |

**Sensibilité du niveau absolu aux hypothèses (config 1-step +8 %) :**

| Hypothèse | p(pass) |
|---|---:|
| mean_R conservateur (+0,007, rebuild brut) | 50 % |
| mean_R calibré (+0,016, build desk) | 52 % |
| calibré + slippage d'exécution réaliste | 47 % |
| régime bull 2022-26 (+0,086) | 64 % ← *origine des « 79-100 % » de notes antérieures, NON forward* |

→ **La fourchette 48-52 % = zone calibré / exécution correcte.** Plancher ~40-47 % (slippage / régime faible), plafond ~55 % (bonne exécution), 64 % seulement si un régime bull type 2023 se répète.

---

## 5. Résultats — analyse des containers (le levier dominant)

L'analyse établit que **le choix de container, pas la stratégie, est le levier de premier ordre.** L'edge per-trade étant ~0, on ne peut pas augmenter le drift (filtres, timing, sizing testés et rejetés — voir §8). Reste la **géométrie de la barrière.**

### 5.1 Tableau comparatif (1 essai, calibré, full-sample)

| Container | Sizing | p(pass) | Médiane | >60 % ? |
|---|---|---:|---:|:---:|
| **FTMO 2-step**, rapide | 4 % | 25 % | ~2 sem | non |
| FTMO 2-step, down-sizé | 0,75 % | ~40 % | **~9 mois** | non |
| FTMO 1-step (3 % daily + trailing) | 2,5 % | 41 % parfait / **19 % slippage** | ~2 sem | non |
| **1-step hors-FTMO, +8 % / DD-10 % statique / daily-5 %** | 2,5 % | **52 % parfait / 47 % slippage** | **~2 sem** | presque |

### 5.2 Le résultat structurel : 1-step ≈ 2× le 2-step

Mécaniquement : FTMO 2-step = p(P1) × p(P2) ≈ 48 % × 52 % ≈ **25 %**. Un container 1-step n'a **qu'une** barrière → ~48-52 %. **Le passage de 2-step à 1-step double quasiment la probabilité.** C'est un effet de structure, robuste, indépendant de l'edge.

### 5.3 Deux pièges à éviter

- **FTMO 1-step :** daily **3 %** + drawdown **trailing**. Le daily-3 % laisse ~0,02 % de marge au-dessus d'un stop 1R à 2,5 % de sizing → **tout stop qui gappe busté instantanément** (p(pass) 41 % → 19 % sous slippage réaliste). Le trailing aggrave. **Inutilisable pour l'ORB.**
- **1-step à DD serré** (type +8 % / DD −5 % balance) : la cible dépasse le drawdown → barrière asymétrique *contre* le trader → ~38 % seulement. **Règle : cible ≤ drawdown total, DD statique large (≥10 %), daily ≥5 % ou balance-based.**

---

## 6. Le mur Sharpe — pourquoi >60 % en 1 essai est hors d'atteinte

Sur une barrière (quasi-)symétrique, **seul le drift (l'edge) remonte p(pass) au-dessus de ~50 %.** Voici la probabilité de passage d'un essai unique FTMO 2-step en fonction de l'edge :

| mean_R | Sharpe annualisé | p(pass) ≤ 2 mois | p(pass) ≤ 6 mois |
|---|---:|---:|---:|
| +0,016 (**ORB actuel**) | 0,22 | 26 % | 32 % |
| +0,035 | 0,49 | 29 % | 37 % |
| +0,050 | 0,70 | 32 % | 42 % |
| +0,070 | 0,98 | 36 % | 49 % |
| +0,100 | **1,39** | **42 %** | **59 %** |

**Deux verdicts mathématiques :**
1. **En ≤ 2 mois, plafond ~42 % à TOUT Sharpe** : les deux phases ne peuvent être franchies vite sans un sizing qui busté la moitié des comptes.
2. **60 % en 1 essai exige un Sharpe ~1,4 maintenu sur ~6 mois.** L'ORB délivre 0,22 ; le **meilleur edge robuste de tout le programme de recherche** (16 mois, ~1 100 hypothèses, toutes classes d'actifs) plafonne à **0,34**. L'écart est un **facteur ~4**, non comblable en price-pattern retail.

---

## 7. Dispersion par régime — analyse année par année (16 ans)

Le « ~50 % » est une moyenne. Pour la même config 1-step +8 %, le p(pass) d'un essai unique aurait varié ainsi selon l'année de départ :

| Année | n trades | mean_R | p(pass) 1-step +8 % | médiane (sem) |
|---|---:|---:|---:|---:|
| 2010 | 144 | −0,007 | 50 % | 2,2 |
| 2011 | 252 | +0,006 | 51 % | 1,8 |
| 2012 | 247 | +0,034 | 56 % | 1,6 |
| **2013** | 245 | −0,064 | **38 %** | 1,8 |
| 2014 | 241 | −0,042 | 45 % | 1,8 |
| **2015** | 253 | −0,122 | **31 %** | 1,6 |
| **2016** | 251 | −0,054 | **39 %** | 1,6 |
| 2017 | 250 | +0,037 | 51 % | 2,0 |
| 2018 | 250 | +0,035 | 55 % | 1,6 |
| 2019 | 247 | +0,024 | 54 % | 2,0 |
| 2020 | 251 | −0,008 | 49 % | 1,8 |
| 2021 | 251 | +0,026 | 58 % | 2,2 |
| **2022** | 253 | +0,136 | **74 %** | 1,8 |
| **2023** | 248 | +0,063 | **62 %** | 1,8 |
| **2024** | 254 | +0,145 | **72 %** | 1,8 |
| 2025 | 252 | +0,015 | 50 % | 2,0 |
| 2026 (partiel) | 104 | +0,050 | 64 % | 2,6 |

**Statistiques :** moyenne **53 %**, médiane **51 %**, **min 31 % (2015)**, **max 74 % (2022)**. Années < 40 % : 2013, 2015, 2016 (chop / baissier). Années > 60 % : 2022-2024, 2026 (bull). **Le temps de résolution reste stable (~1,6-2,6 sem) quel que soit le régime** — c'est le *taux de passage*, pas la *vitesse*, qui dépend du régime.

**Implication de décision :** le résultat d'un essai unique est essentiellement **un tirage conditionné par le régime de marché**, que l'on ne peut pas chronométrer (le timing du départ est un bruit blanc, testé et établi). L'équipe parie sur le régime autant que sur la stratégie.

---

## 8. Sensibilités & risques (registre)

| # | Risque | Description | Mitigation |
|---|---|---|---|
| R1 | **Régime de marché** | Dispersion 31-74 % selon l'année ; non prévisible | Aucune (timing = bruit blanc). Accepter la variance. |
| R2 | **Exécution / slippage** | Stop qui gappe → busts ; critique sous daily serré | Choisir daily ≥5 % / no-daily ; sizing ≤ tampon ; fills au niveau |
| R3 | **Risque de modèle** | Block-bootstrap suppose futur ≈ mélange du passé ; ne voit pas un régime inédit | Marquer in-sample ; ne pas sur-interpréter le niveau |
| R4 | **mean_R optimiste** | +0,016 (build desk) vs +0,007 (rebuild) | Les deux donnent ~50 % → robuste à cette hypothèse |
| R5 | **0 jour live** | Aucune validation réelle | Paper trading avant capital réel |
| R6 | **EV économique** | Rules-exploitation, ~0 alpha ; atteindre un payout post-financement est lui-même une loterie | Traiter comme option à petite mise ; frais remboursés au 1er payout |
| R7 | **Risque firme / réglementaire** | Specs propfirm changeantes ; restauration d'une limite de temps tuerait l'approche down-sizée ; risque de contrepartie | Vérifier specs avant achat ; DD statique ; petits comptes |

**Économie :** frais d'inscription modestes (~€90-150 pour un $10k selon promo — *à confirmer*), **remboursés au premier payout**. Coût coulé attendu jusqu'au financement ≈ (1 / p) essais. EV nette **marginale et dominée par la variance** sans vrai edge.

---

## 9. Cadre de décision — le trilemme

```
            {1 essai}
               /\
              /  \
   ~48-52% / 2sem    ~25-42% (FTMO seul)
   (lâche FTMO)  \  /
                  \/
        {>60%}----{FTMO}
         \________/
       3-4 essais → ~70%
       (lâche 1 essai)
```

**On peut tenir deux sommets, jamais les trois.** Aucune configuration ne réalise simultanément 1 essai, FTMO, et >60 %.

---

## 10. Recommandation pour délibération

Le rapport ne tranche pas à la place de l'équipe ; il cadre trois voies cohérentes :

**Voie A — maximiser p(pass) par unité de temps (1 essai).** Container **1-step hors-FTMO** (cible +8 %, DD ≥10 % statique, daily ≥5 % ou balance-based, sans limite de temps) ; ORB V2+E7 inchangé ; sizing **2,5 % fixe**. → **~48-52 % par essai, médiane ~2 semaines, 1 frais.** *Plafond ~55 %, ne dépasse pas 60 %.* C'est le meilleur compromis probabilité/temps/coût pour un essai unique.

**Voie B — viser >60 % (multi-essais).** FTMO ou 1-step, **3-4 essais** (parallèles ≈ 2 mois, ou séquentiels ≈ 6-8 mois), petits comptes. → **~70 % d'être financé** (1 − (1−p)ⁿ). Seule voie qui franchit 60 %. Coût : 3-4 frais coulés.

**Voie C — rester strictement FTMO, 1 essai.** Accepter le plafond honnête : **~25 % (rapide, 2 sem)** ou **~40 % (down-sizé, ~9 mois)**. Non recommandé : dominé par A sur les deux axes.

**Prochaine étape proposée si l'équipe valide une voie :** (1) vérification live des specs de 2-3 firmes candidates ; (2) **paper trading** de l'ORB sur ≥20 sessions pour mesurer le slippage réel du stop (le paramètre R2, le plus impactant) ; (3) go/no-go capital après réconciliation paper-vs-backtest.

---

## Annexe A — Reproductibilité

| Artefact | Chemin |
|---|---|
| Trades ORB V2+E7 (n=3 993) | `outputs/orb_v2e7.parquet` |
| Donnée source | `data/raw/NQ_1min_databento_2010-2026.parquet` |
| Spécification & métriques ORB | `data/ftmo_research/ORB_deepening_NQ.md` |
| Analyse containers + stress | `data/ftmo_research/ORB_1step_improvement.md` |
| Optimisation 2-step (révisée) | `data/ftmo_research/OPTIM_ftmo_2step_uncapped.md` |
| Timing du départ (= bruit blanc) | `data/ftmo_research/OPTIM_regime_timing_intraday.md` |
| Récap maître du programme | `data/ftmo_research/FTMO_RECAP.md` |

**Paramètres de simulation :** block-bootstrap blocs 21 j ; 12 000 comptes/config ; mean_R calibré +0,016 ; coût 2 bps RT ; cap temps selon test ; daily/total DD selon container. Seeds fixés, reproductible.

## Annexe B — Le programme de recherche en une ligne

La décision ci-dessus est l'aboutissement de ~1 100 hypothèses testées sur 16 mois (overnight drift, MR intraday, stat-arb/paires, breakout, momentum, swing, carry FX, commodities momentum/saison/carry/COT/skew, FOMC, turn-of-month) — **toutes classes d'actifs liquides FTMO**. Le résultat unifiant : **aucun edge price-pattern retail two-sided ne survit aux coûts honnêtes et bat la barrière FTMO.** Tout se réduit à du beta long déguisé ou à des signaux trop faibles (Sharpe ≤ 0,34). Le véhicule de passage de challenge est de l'**ingénierie de barrière**, pas de l'alpha. *(Détail : `FTMO_RECAP.md`.)*

---
*Rapport compilé 2026-06-02. Desk systématique. Pour délibération interne — ne constitue pas un conseil en investissement. Tous chiffres backtest, 0 jour live.*
