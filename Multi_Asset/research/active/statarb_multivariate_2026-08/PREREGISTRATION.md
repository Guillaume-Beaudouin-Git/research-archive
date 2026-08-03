# Pré-enregistrement — Arbitrage statistique MULTIVARIÉ sur véhicule FTMO CFD

**Famille neuve. Compteur LOCAL N1.** Écrit et committé **avant** tout contact avec la donnée de
marché de cette étude. Terrain : structure factorielle, résidus multi-actifs, réseaux
d'avance-retard. **Hors périmètre : le pairs trading bivarié / la cointégration** (agent frère).

Date : 2026-08-03. Branche `claude/statarb-multivariate`. Base `origin/main` `49804922`.

---

## 0. Le livrable n°1 est un calcul, pas un backtest

L'arbitrage statistique est une machine à convertir de la **largeur** en Sharpe. Notre univers
tradable fait **17 instruments**, pas 500 actions. Avant de coder quoi que ce soit, il faut
répondre à : *que peut-on espérer d'un stat-arb à N=17 ?* Le **Bloc A** ci-dessous répond, sans
toucher une seule barre de prix — il n'utilise que (i) la loi fondamentale de la gestion active,
(ii) des constantes de coût **déjà mesurées dans ce repo**, (iii) la littérature publiée.

Si le Bloc A dit que l'IC requis est hors d'atteinte, **c'est le résultat**, et les blocs
empiriques se réduisent à un seul test de falsification ciblé — pas à trois jours de code.

---

## 1. Mécanisme revendiqué (ce qui devrait être vrai pour que la famille existe)

**M1 — Réversion du résidu (branche multi-jours, à la Avellaneda-Lee).** Les 17 instruments
partagent des facteurs macro nommés (dollar, risk-on/risk-off, duration, complexe matières). Un
choc idiosyncratique sur un instrument — flux, couverture, dislocation temporaire — l'écarte de sa
valeur implicite par les facteurs. Le résidu est stationnaire et revient. On vend le résidu haut,
on l'achète bas, on est neutre aux facteurs par construction.

**M2 — Avance-retard (branche intraday-flat).** Deux instruments chargés sur le même facteur
n'intègrent pas l'information à la même vitesse (profondeur de carnet, horaires de séance,
localisation du price discovery). Le meneur prédit le suiveur sur un horizon court. On trade le
suiveur, à plat le soir.

**Ces deux mécanismes sont en tension directe avec deux contraintes structurelles de notre
véhicule** — c'est cette tension que le Bloc A chiffre :
- M1 tient des positions **plusieurs jours** ⇒ paie le **portage** (swap asymétrique sur le
  notionnel tenu, L28/L36) sur **chaque jambe**.
- M2 ne paie pas de portage mais opère à un horizon où la **volatilité disponible** est petite
  devant le **coût d'un panier à K jambes** (K × coût RT, à l'entrée **et** à la sortie).

---

## 2. BLOC A — Faisabilité à N=17 (0 cellule, 0 donnée de marché)

Entrées, toutes sourcées :

| Constante | Valeur | Source |
|---|--:|---|
| N tradable | 17 | univers mesuré (7 softs/NGAS exclus : COCOA 1189 bps RT … COFFEE 142) |
| Coefficient de transfert TC | 0.40 | toolkit repo (IJR 2017) |
| Coût RT par jambe, indices | **~1.8 bps** (centre 0.9, p95 2.3, max 4.5) | `COST_AUDIT.md` §5-§6 |
| Coût RT par jambe, XAUUSD | **1.84** centre / **3.88** queue | `COST_AUDIT.md` §3 |
| Swap, paire market-neutral CFD | **~1.5 bps/nuit** (⇒ 0.75 /jambe) | L28 |
| Swap, livre agrégé FTMO | **6.75 %/an** du notionnel tenu | L36 (mesuré) |
| Gate pré-vol intraday | `gross_per_trade / cost_p95 ≥ 1.5` | L43 |

### A1 — L'IC requis explose quand la largeur s'effondre

`IR_gross = TC × IC × √BR`, avec `BR = N × 252 / HL` (HL = demi-vie du signal en jours ; des paris
qui se recouvrent ne sont **pas** des paris indépendants — c'est L12b).

| univers | HL (j) | BR/an | √BR | IC requis pour IR=0.7 | IC requis pour IR=1.0 |
|---|--:|--:|--:|--:|--:|
| N=500 (actions) | 7 | 18 000 | 134.2 | 0.0130 | 0.0186 |
| **N=17 (nous)** | 1 | 4 284 | 65.5 | 0.0267 | 0.0382 |
| **N=17 (nous)** | **7** | **612** | **24.7** | **0.0707** | **0.1011** |
| N=17 (nous) | 21 | 204 | 14.3 | 0.1225 | 0.1750 |

⇒ À la demi-vie typique d'un résidu Avellaneda-Lee (~7 j), atteindre un Sharpe **brut** de 1.0 à
N=17 demande un **IC transversal de 0.10**. Les IC de réversion de résidu documentés en actions
sont de l'ordre de **0.02-0.05**. Et ce chiffre est **avant** tout coût et tout swap.

### A2 — Transfert de largeur depuis le résultat publié

À IC identique, `SR ∝ √BR`. De N=500/HL=7 vers N=17/HL=7 : facteur **0.1844**.

| Résultat publié | SR publié | ⇒ à N=17 | ⇒ à N=17 avec bonus IC ×2 |
|---|--:|--:|--:|
| Avellaneda-Lee 1997-2007 | 1.44 | **0.266** | 0.531 |
| Avellaneda-Lee 2003-2007 (leur propre déclin) | 0.90 | **0.166** | 0.332 |
| Fischer-Krauss, S&P 500, post-2010, **net de coûts** | ~0.00 | 0.000 | 0.000 |

Le « bonus IC ×2 » est une concession délibérément généreuse à l'idée que 17 instruments macro
liquides portent un IC supérieur à 500 actions.

### A3 — Le portage, converti en unités de Sharpe (branche M1)

Un livre de résidus est **toujours en position**. À levier brut G et cible de vol 10 % :

| G | swap/an (L28, 0.75 bps/nuit/jambe) | Perte de Sharpe |
|--:|--:|--:|
| 1.0 | 1.89 % | 0.19 |
| 2.0 | 3.78 % | 0.38 |
| **2.5** | **4.72 %** | **0.47** |
| 3.0 | 5.67 % | 0.57 |
| — | *L36 mesuré : 6.75 %* | *0.68* |

Un panier de résidus market-neutral a une vol brute faible : viser 10 % demande G ≈ 2-3.

**A2 + A3 :** SR brut plausible **0.17-0.53**, moins **0.38-0.68** de portage ⇒ **SR net ≈ 0 ou
négatif, avant même de payer l'exécution.**

### A4 — Les ciseaux d'horizon (branche M2, intraday-flat)

Sans portage, mais le coût d'un panier à K=2 jambes est `2 × c_rt`, et le gate L43 demande
`gross ≥ 1.5 × coût`, soit **6.0 bps** (centre) / **12.0 bps** (queue) en unités de notionnel
d'une jambe. Face à cela, la vol disponible à l'horizon h (`σ_h = σ_jour × √(h/390)`, σ_jour ≈ 90 bps
sur indice) :

| h (min) | σ_h (bps) | ρ requis (coût centre) | ρ requis (coût queue) |
|--:|--:|--:|--:|
| 1 | 4.6 | 1.317 | 2.633 |
| 5 | 10.2 | 0.589 | 1.178 |
| 15 | 17.7 | **0.340** | 0.680 |
| 30 | 25.0 | 0.240 | 0.481 |
| 60 | 35.3 | **0.170** | 0.340 |
| 120 | 49.9 | 0.120 | 0.240 |

`ρ` = corrélation que la prévision d'avance-retard doit avoir avec le rendement des h minutes
suivantes, **uniquement pour franchir le coût**. La littérature d'avance-retard donne ρ ≈ 0.02-0.10
à l'échelle de la minute, **et décroissant en h**.

**Prédiction structurelle testable — les ciseaux :** ρ requis décroît en `1/√h`, ρ disponible
décroît (plus vite) en h. La famille n'existe que si les deux courbes se croisent. **C'est la seule
chose qu'il vaille la peine de mesurer.**

---

## 3. Cellules pré-enregistrées et règles de mort — 88 cellules au total

### BLOC B — Terme de structure de l'avance-retard (84 cellules) — **le test décisif**

Grille figée **avant** la donnée. Paires **motivées par un mécanisme nommé**, jamais un balayage
des 17×16 = 272 paires ordonnées (ce serait du data-mining, et ça déflaterait le DSR de tout
candidat futur).

| # | meneur → suiveur | mécanisme |
|---|---|---|
| 1-2 | GER40 ⇄ US500 | même facteur risk-on, recouvrement de séance Europe/US |
| 3-4 | GER40 ⇄ US100 | idem |
| 5-6 | GER40 ⇄ US30 | idem |
| 7-8 | XAUUSD ⇄ XAGUSD | même facteur métal précieux, liquidité très asymétrique |
| 9-10 | UKOIL ⇄ USOIL | même sous-jacent physique, deux points de livraison |
| 11-12 | COPPER ⇄ AUDUSD | cuivre ↔ devise-matière |
| 13-14 | GER40 ⇄ EURUSD | actions domestiques ↔ devise domestique |

**7 paires non ordonnées × 2 sens (L25, jambes DISJOINTES) × 6 horizons
h ∈ {1, 5, 15, 30, 60, 120} min = 84 cellules.**

Statistique principale, **au GROSS (`cost_rt = 0`)** : `ρ(meneur_{t-1} → suiveur_{t→t+h})`, puis
le **ratio de faisabilité** `R = gross_par_trade / coût_total_du_panier`.

**Règle de mort pré-enregistrée B :** si `max` sur les 84 cellules de `R < 1.5` **au coût centre**,
la branche M2 est **REJECTED** — sans correction de tests multiples, parce qu'un maximum
optimiste-biaisé qui ne franchit **quand même pas** le gate est un rejet *a fortiori*. La
correction (Šidák à n=84, puis DSR) n'est requise que dans le cas d'un PASS.

### BLOC C — Réversion de résidu, modèle à facteurs walk-forward (4 cellules)

ACP **en fenêtre glissante**, quotidien. La fenêtre d'estimation (252 j) **ne touche jamais** la
fenêtre de trading : bêtas et facteurs estimés sur `[t-252, t-1]`, résidu et signal calculés en `t`,
trade en `t+1`. **Une ACP sur échantillon complet est du look-ahead pur** et ne sera pas produite.

- K facteurs ∈ {3, 5} × seuils s-score (entrée/sortie) ∈ {(1.25, 0.50) canonique AL, (2.00, 0.50)}
  = **4 cellules**.

**Règle de mort pré-enregistrée C :** si `max` sur les 4 cellules du Sharpe **brut**
(`cost_rt = 0`, `swap = 0`) `< 0.70`, la branche M1 est **REJECTED**. Justification : 0.70 est le
seuil RESEARCH_PASS ; ne pas l'atteindre **à coût nul** signifie qu'aucun modèle de coût ne peut
la sauver. On rapportera aussi la demi-vie mesurée du résidu, qui pilote la facture de swap (A3).

### Contrôles obligatoires (appliqués à toute cellule qui survivrait)

- **Gross d'abord** : toute cellule est jugée à `cost_rt = 0` avant d'être coûtée.
- **L25** — two-sided à jambes disjointes : les deux sens de chaque paire sont rapportés.
- **L58** — baseline **inconditionnelle appariée** (pas la moyenne pleine fenêtre) ; la moyenne du
  pool placebo doit égaler l'espérance inconditionnelle de la forme de trade.
- **L38** — R² de la sleeve contre un buy-and-hold vol-targeté de son actif primaire ; **> 30 % ⇒
  pas une sleeve neuve**.
- **L59** — delay+1 sur l'**ENTRÉE et la SORTIE**, séparément.
- **L60** — fraction de barres M1 à fourchette nulle, par série et par année, **avant** usage.
- **Look-ahead** : fenêtre d'estimation disjointe de la fenêtre de trading, vérifiable dans le code.
- **Bootstrap par blocs** (Politis-Romano), jamais iid.
- **DSR** via `dsr.py` racine **uniquement** (⚠ `framework.py:131` et `ftmo_lab.py:232` sont
  cassées : σ_SR_trials absent).
- **Placebo à autocorrélation appariée** (décalage circulaire) obligatoire avant tout p(pass) : une
  série de moyenne strictement nulle mais persistante achète Δp = +0.1495 à elle seule.

### Hygiène de données — décidé d'avance

- Source unique : `data/deep_history_utc/` M1 **vrai UTC**, rééchantillonné en M5 par un script de
  cette étude. **Interdits** : `data/panels/m5_indices/` (EET mal étiqueté),
  et **toute** série issue de `overnight_futures_2026-07/code/step3_performance.py` (winsorisation
  0.5/99.5 dans le constructeur).
- La colonne `spread` **n'est pas** utilisée comme modèle de coût (zéro-inflée : US30 74.9-100 % de
  barres nulles 2019-2021, EURUSD 33 % de jours nuls). Les coûts viennent du panneau mesuré de
  `COST_AUDIT.md`.
- La fraction de barres M1 à fourchette nulle est mesurée à la construction du panneau (contrôle
  L60), en amont de tout test.

---

## 4. Ce qu'un PASS exigerait, et ce qu'un REJECT signifierait

**PASS** demande, cumulativement : `R ≥ 1.5` au gross ; survie à Šidák(84) et au DSR ; L38 < 30 % ;
delay+1 entrée **et** sortie ; supériorité sur le placebo à autocorrélation appariée ; et enfin —
seulement alors — un gain sur **Δp(pass) et Δdurée** au niveau du livre, pas sur ΔSR.

**REJECT** ne dira **pas** « l'avance-retard n'existe pas ». Il dira que **sur cet univers, à ce
tier de coût, la fenêtre entre le signal disponible et le coût du panier est vide.** C'est un kill
de type **COÛT/LARGEUR** au sens de la politique de ré-ouverture — donc **rouvrable** si le
véhicule change (futures à ~0.4 bps RT, compte IBKR perso) ou si l'univers s'élargit. Ce n'est
**pas** un kill mécanique.

**UNDERPOWERED** sera prononcé, et distingué de REJECTED, si l'IC ponctuel est du bon signe mais
que l'IC à 95 % contient zéro sans que le gate de coût soit tranché.
