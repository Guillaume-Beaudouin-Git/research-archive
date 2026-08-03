# Résultats — Arbitrage statistique MULTIVARIÉ sur véhicule FTMO CFD

**2026-08-03.** Compteur LOCAL **N1 = 132 cellules** (84 pré-enregistrées + 48 post-hoc).
Pré-enregistrement : `PREREGISTRATION.md`, committé `6cf44fbc`, **avant** tout contact avec la
donnée de marché. Code : `code/`. Tables : `results/`.

---

## 0. Verdict en une page

| Branche | Cellules | Verdict | Ce qui la tue |
|---|--:|---|---|
| **M1 — réversion du résidu multi-jours** (ACP walk-forward, à la Avellaneda-Lee) | 4 | **REJECTED** | Sharpe **BRUT** max **0.398** < 0.70. Meurt à coût NUL. |
| **M2 — avance-retard, stratégie de SIGNE** (pré-enregistrée) | 84 | **REJECTED** | max `R = gross/coût` = **0.437** < gate 1.5 |
| **M2b — avance-retard conditionné sur l'amplitude** (post-hoc) | 48 | mixte, voir ci-dessous | — |
| ↳ GER40 → US30, h=60 | — | **REJECTED** | walk-forward **1-2 folds / 5** : tout l'edge est dans le fold COVID (2019-08→2020-09, gross +31.5 bps contre −1.1 / −2.3 / −0.5 ailleurs) |
| ↳ **XAGUSD → XAUUSD, h=120** | — | **UNDERPOWERED** | passe 5/5 folds, two-sided, placebo, latence, L38 — mais **DSR 0.61 < 0.95** à n=132, **SR annualisé 0.49 < 0.70**, et le levier nécessaire pour le monétiser (**×6.9**) met **un seul trade** au-delà de la barrière journalière |

**La réponse à la question posée — que peut-on espérer d'un stat-arb à N=17 ? — est un
chiffre : l'IC transversal requis pour un Sharpe brut de 1.0 y est 0.101, contre 0.019 à
N=500.** La littérature documente des IC de réversion de résidu de 0.02-0.05. Le déficit est
d'un facteur 2 à 5, et il est **structurel** : il ne se recalibre pas.

---

## 1. BLOC A — La faisabilité, chiffrée avant la première ligne de backtest

*(0 cellule consommée, 0 donnée de marché touchée — littérature + constantes déjà mesurées ici.)*

### A1 — L'IC requis explose quand la largeur s'effondre

`IR_gross = TC × IC × √BR`, `BR = N × 252 / HL`. Des paris qui se recouvrent ne sont **pas**
indépendants : c'est la demi-vie du signal, pas le calendrier, qui fixe la largeur (L12b).

| univers | HL (j) | BR/an | √BR | IC requis, IR=0.7 | IC requis, IR=1.0 |
|---|--:|--:|--:|--:|--:|
| N=500 (actions) | 7 | 18 000 | 134.2 | 0.0130 | 0.0186 |
| N=17 | 1 | 4 284 | 65.5 | 0.0267 | 0.0382 |
| **N=17** | **7** | **612** | **24.7** | **0.0707** | **0.1011** |
| N=17 | 21 | 204 | 14.3 | 0.1225 | 0.1750 |

**Le Bloc C a mesuré la demi-vie du résidu à 6.8-6.9 jours** — la ligne HL=7 est donc la bonne
ligne, et ce n'était pas une hypothèse commode : c'est une prédiction du Bloc A confirmée par la
donnée.

### A2 — Transfert de largeur depuis les résultats publiés

À IC identique, `SR ∝ √BR`. De N=500/HL=7 vers N=17/HL=7 : **×0.1844**.

| Résultat publié | SR | ⇒ N=17 | ⇒ N=17, bonus IC ×2 |
|---|--:|--:|--:|
| Avellaneda-Lee 1997-2007 | 1.44 | 0.266 | 0.531 |
| Avellaneda-Lee 2003-2007 (leur propre déclin) | 0.90 | 0.166 | 0.332 |
| Fischer-Krauss, S&P 500, post-2010, **net de coûts** | ~0.00 | 0.000 | 0.000 |

Le « bonus IC ×2 » est une concession délibérément généreuse. Même ainsi, on plafonne à 0.53.

### A3 — Le portage, en unités de Sharpe

| G (levier brut) | swap/an (L28) | perte de Sharpe à σ=10 % |
|--:|--:|--:|
| 1.0 | 1.89 % | 0.19 |
| 2.5 | 4.72 % | **0.47** |
| 3.0 | 5.67 % | 0.57 |
| *L36 mesuré* | *6.75 %* | *0.68* |

**A2 + A3 : brut plausible 0.17-0.53, moins 0.38-0.68 de portage ⇒ net ≈ 0 ou négatif, avant
même de payer l'exécution.** Le Bloc C l'a vérifié en donnée.

### A4 — Les ciseaux d'horizon (branche intraday-flat), et là où le Bloc A s'est trompé

Le Bloc A prédisait que `ρ` disponible **décroîtrait** en h (intuition microstructure/HFT),
condamnant la branche par les deux bouts. **La mesure dit le contraire** : `|IC|` moyen **croît**
avec l'horizon.

| h (min) | 1 | 5 | 15 | 30 | 60 | 120 |
|---|--:|--:|--:|--:|--:|--:|
| `\|IC\|` moyen mesuré | 0.0031 | 0.0071 | 0.0052 | 0.0053 | **0.0148** | **0.0159** |
| `max R` mesuré | 0.009 | 0.011 | 0.033 | 0.066 | **0.437** | 0.251 |

⇒ **l'avance-retard exploitable ici n'est PAS un effet de latence.** Un effet de latence vit en
secondes et meurt en minutes ; celui-ci est absent à 1-5 min et n'apparaît qu'à 60-120 min. C'est
un effet de **diffusion d'information entre séances/instruments**, pas une course à la vitesse.
Confirmation directe au contrôle D1 : l'edge **survit à 15 minutes de retard d'entrée**
(6.10 → 4.47 bps sur GER40→US30 ; il **augmente** sur XAG→XAU, 6.22 → 7.11 bps à d=5).

**C'est le résultat méthodologique de l'étude** : sur cet univers, la piste avance-retard n'est
pas fermée par le tier de latence. Elle est fermée par la largeur et par la taille du coût
relativement à la vol disponible.

---

## 2. BLOC C — Réversion du résidu : REJECTED au brut (4 cellules)

ACP en fenêtre glissante 252 j, bêtas gelés avant le calcul du rendement factoriel du jour t,
s-score connu à la clôture t−1, position tenue sur t. **Aucune ACP sur échantillon complet.**
Panneau 3 187 jours × 19 instruments, 2013-10 → 2026-06.

| K | s_open | s_close | **SR BRUT** | pos. moy. | hold médian | HL résidu médian | trades |
|--:|--:|--:|--:|--:|--:|--:|--:|
| 3 | 1.25 | 0.50 | +0.040 | 6.6 | 10 j | 6.9 j | 1 533 |
| 3 | 2.00 | 0.50 | +0.300 | 2.0 | 13 j | 6.9 j | 403 |
| 5 | 1.25 | 0.50 | +0.319 | 6.7 | 10 j | 6.8 j | 1 550 |
| **5** | **2.00** | **0.50** | **+0.398** | 1.9 | 12 j | 6.8 j | 391 |

**Règle de mort C appliquée : max SR brut 0.398 < 0.70 ⇒ REJECTED.** À coût **nul** et swap
**nul**. Aucun modèle de coût ne peut sauver ça.

Deux chiffres expliquent pourquoi, et ils sont exactement ceux du Bloc A :
- **positions simultanées moyennes : 1.9 à 6.7.** La « largeur » réelle d'un stat-arb à N=17 est
  de deux à sept paris à la fois. C'est le Bloc A rendu tangible.
- **hold médian 10-13 nuits, HL résiduelle 6.8 j** ⇒ facture de portage **8.2 bps par trade et
  par jambe** (L28). Contre un brut qui ne franchit déjà pas le seuil.

---

## 3. BLOC B — Avance-retard, grille pré-enregistrée : REJECTED (84 cellules)

7 paires motivées par un mécanisme nommé × 2 sens (L25, jambes disjointes) × 6 horizons. Trades
**non chevauchants par construction** (échantillonnage sur grille de pas h, jamais un balayage
glouton qui sélectionnerait sur la donnée). Entrée **et** sortie retardées d'une barre (L59).
Barres de fourchette nulle du meneur exclues (L60). K=1 jambe — on ne trade que le **suiveur**,
soit la variante la **moins chère** : si elle échoue, la variante neutre à 2 jambes échoue
a fortiori.

- **max R = 0.437** (gate L43 = 1.5) — **0 cellule sur 84** franchit le gate
- max gross = 0.643 bps ; max |IC| = 0.086 ; 37/84 cellules à gross > 0

**Règle de mort B appliquée ⇒ REJECTED.** Pas de correction de tests multiples nécessaire : un
maximum biaisé à la hausse qui **ne franchit quand même pas** le gate est un rejet *a fortiori*.

### L'anomalie qui a obligé à continuer

La meilleure cellule (GER40 → US30, h=60) porte **IC 0.086, t_HAC 4.70, n=40 422** — un signal
**réel** — mais ne rend que **0.643 bps**. Sous normalité bivariée une stratégie de SIGNE devrait
rendre `0.798 × ρ × σ_h = 2.42 bps`. Elle en rend un quart.

⇒ **l'IC est porté par les GRANDS mouvements du meneur, et prendre le signe de chaque mouvement
jette le conditionnement.** Le coût étant FIXE par trade et le gross croissant avec l'amplitude,
c'est la seule manière naturelle de franchir un gate de coût. **Prononcer le kill sans tester
cette variante aurait été un faux négatif.**

---

## 4. BLOC B2 — Conditionnement sur l'amplitude (48 cellules, POST-HOC assumé)

Ces cellules ne sont **pas** pré-enregistrées. Elles sont explorées dans la direction
**généreuse**, précisément pour éprouver la solidité d'un kill.

| q (quantile de \|mouvement du meneur\|) | 0.50 | 0.80 | 0.90 | 0.95 |
|---|--:|--:|--:|--:|
| gross moyen (bps) | 0.334 | 0.661 | 1.225 | **2.165** |
| max R | 0.808 | 1.676 | 2.451 | **4.149** |

**7 cellules sur 48 franchissent le gate 1.5.** La monotonie en q est nette et elle est
mécaniquement attendue : le gross croît avec l'amplitude, le coût ne bouge pas.

---

## 5. BLOC D — La batterie de contrôles, et ce qu'elle tue

| Contrôle | GER40→US30 h=60 q=0.95 | XAGUSD→XAUUSD h=120 q=0.95 |
|---|---|---|
| gross / coût / **R** | 6.10 / 1.47 / **4.15** | 6.22 / 1.84 / **3.38** |
| t_HAC (lag-6) | +3.43 | +2.98 |
| **D1 latence** (d=1→15 min) | 6.10 → 4.47 bps — **survit** | 6.22 → 7.11 bps (d=5) — **survit** |
| **D2 walk-forward 5 folds** | **2/5** — fold COVID +31.5 bps, les autres −1.1 / −2.3 / +2.9 / −0.5 | **5/5** (+2.9 / +2.3 / +8.1 / +4.5 / +13.2) |
| **D3 two-sided (L25)** | long +7.07 (t 2.66) / short +5.28 (t 2.27) | long +5.80 (t 2.10) / short +6.58 (t 2.15) |
| **D4 placebo autocorr. appariée** | obs +6.10 vs médiane −0.02, p95 +1.77 — **p=0.0000** | obs +6.22 vs médiane +0.05, p95 +3.40 — **p=0.0000** |
| **D5 L38 orthogonalité** | R² **0.0 %**, α t +1.43 | R² **0.6 %**, α t +2.65 |
| **D6 DSR** (n=132, `dsr.py` racine) | 0.714 — **ÉCHEC** | 0.610 — **ÉCHEC** |
| **Verdict** | **REJECTED** (walk-forward) | **UNDERPOWERED** |

**GER40 → US30 est REJECTED, et le contrôle qui le tue est le walk-forward, pas la
significativité.** Il passe le placebo à p=0.0000, il est two-sided, il est orthogonal au beta
(R² 0.0 %), et la variante q=0.80 passe même le **DSR à 0.982** — parce que le DSR ne voit pas la
concentration de régime. **1 à 2 folds sur 5** : tout l'edge tient dans 2019-08 → 2020-09. Un
DSR qui passe sur un edge à 1/5 folds est un rappel utile : **la déflation par tests multiples et
la stabilité de régime sont deux filtres orthogonaux, et il faut les deux.**

---

## 6. BLOC E — Le survivant converti en métrique de décision

XAGUSD → XAUUSD, h=120 min, intraday-flat (2 h de tenue ⇒ **aucun swap**), 19.4 ans,
**66 trades/an** à q=0.95.

| | coût centre 1.84 bps | coût queue p95 3.88 bps |
|---|--:|--:|
| net / trade | **+4.377 bps** | +2.337 bps |
| écart-type / trade | 72.3 bps | 72.3 bps |
| **Sharpe annualisé** (L47, √66 — **pas** √252) | **+0.491** | +0.262 |
| rendement à 1× | +2.87 %/an | +1.53 %/an |

Bootstrap **par blocs** (Politis-Romano, b=20, 5 000 tirages) sur le net par trade :
**IC95 [+0.371 ; +8.850] bps — exclut zéro**, mais de justesse. À q=0.90 l'IC95 est
**[−0.003 ; +5.051] — contient zéro**.

### Pourquoi c'est inexploitable dans un challenge

Horizon de décision **182 jours** ⇒ ~33 trades attendus.

- Levier requis pour viser **+10 %** : **×6.9**
- À ×6.9, **1 écart-type d'UN SEUL trade = 5.00 % de l'équité** — soit **exactement la barrière
  journalière**
- **Pire trade observé, au même levier : −25.15 %** — deux fois et demie le **plancher statique**
  −10 %, en **une seule position**
- MC iid-trades, purement indicatif : 56.3 % atteignent +10 %, 42.4 % touchent le plancher
  statique d'abord. **Ce chiffre est un plafond optimiste** : il ignore la barrière journalière et
  traite des trades à queue épaisse comme iid.

Le rapport signal/bruit par trade (4.4 bps de moyenne contre 72 bps d'écart-type) impose un levier
qui fait du plancher statique — celui qui lie réellement, à **49.7 %** des morts de ce livre — un
événement à **un seul trade**. La sleeve est **un vrai edge, et un edge non monétisable sur ce
véhicule**.

---

## 7. Ce que cette étude NE prouve PAS

1. **Elle ne prouve pas que l'avance-retard n'existe pas.** XAGUSD → XAUUSD passe 5/5 folds sur
   19 ans, two-sided, placebo à p=0.0000, orthogonal au beta (R² 0.6 %). Le signal est là. Ce qui
   manque, c'est le **rapport moyenne/écart-type par trade**, et la **fréquence** (66/an).
2. **Elle ne prouve pas que le stat-arb multivarié est mort en général** — elle montre qu'à
   **N=17**, la largeur plafonne le Sharpe atteignable **avant** toute question de talent de
   modélisation. Le Bloc C mesure 1.9 à 6.7 positions simultanées : c'est ça, la « largeur » ici.
3. **Elle ne teste pas les modèles à facteurs non linéaires** (autoencodeurs, transformers). Mais
   l'argument A1/A2 est un plafond de **largeur**, pas de **méthode** : un meilleur modèle relève
   l'IC, il ne crée pas de paris indépendants. Il faudrait un IC de **0.101** — 2 à 5× la
   littérature — pour un Sharpe brut de 1.0.
4. **Les coûts non mesurés sont des estimations.** XAGUSD (3.00), COPPER / UKOIL / USOIL (3.00)
   ne sont pas dans `COST_AUDIT.md`. Les conclusions n'en dépendent pas : les cellules concernées
   échouent, ou échouent ailleurs (XAG→XAU est jugé sur le coût **de XAUUSD**, lui **mesuré**).
5. **Le Bloc B2 est post-hoc.** Ses cellules ne pourraient valider une sleeve qu'après
   pré-enregistrement et test OOS. Elles sont ici pour **éprouver un kill**, pas pour le renverser.

---

## 8. Nature des kills, et politique de ré-ouverture

| Branche | Nature du kill | Rouvrable ? |
|---|---|---|
| M1 résidu multi-jours à N=17 | **LARGEUR** (mécanique : brut 0.398 à coût nul) | **NON** sur cet univers. Recalibrer ne ressuscite pas un brut sous-seuil. Rouvrable **uniquement** si N augmente substantiellement. |
| M2 avance-retard, stratégie de signe | **COÛT** | **OUI** — 1.8-3.0 bps RT en CFD contre ~0.4 bps RT en futures : le gate change d'un ordre de grandeur |
| GER40 → US30 conditionné | **MÉCANIQUE** (régime : 1-2/5 folds) | **NON** — un edge qui n'existe qu'en mars 2020 n'est pas un edge |
| **XAGUSD → XAUUSD h=120** | **PUISSANCE + GÉOMÉTRIE** | **OUI** — UNDERPOWERED ≠ REJECTED. Angle nouveau requis, écrit avant la donnée. |

**La piste la plus prometteuse ouverte par cette étude n'est pas FTMO.** XAG→XAU est
intraday-flat, ne paie aucun swap, tient 5/5 folds sur 19 ans, et meurt sur le **levier** qu'exige
une barrière de challenge. Sur le **compte IBKR personnel** — pas de barrière, pas d'horloge,
100 % du P&L — la contrainte de levier disparaît, et 2.87 %/an à 1× devient une brique de
diversification jugeable au critère ΔSR>0 au poids ERC plutôt qu'au critère p(pass). C'est
exactement le motif L53 : **la matrice de véhicule passe AVANT le backtest.**

Avant d'y consacrer un essai, il faudra un angle explicitement nouveau et pré-enregistré : la
version actuelle est post-hoc, et son DSR (0.61 à n=132) dit qu'elle n'a pas encore payé son
billet.
