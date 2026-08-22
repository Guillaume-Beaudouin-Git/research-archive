# RÉSULTATS — Coût réel de l'ORB funded + sizing funded (P0/P1)

**Synthèse MD, 2026-08-13.** Protocole : `PREREGISTRATION.md` (gelé 2026-08-12, avant données).
Les 4 volets ont produit leurs données ; seul le volet A a écrit son rapport avant la coupure de
session. Les volets B, C, D sont synthétisés ici depuis leurs sorties brutes (`*/out/`), et le
calcul de composition finale — qu'aucun volet n'avait fait, chacun s'arrêtant à sa frontière —
a été refait au niveau MD.

---

> # ⚠ LIRE L'AMENDEMENT n°1 AVANT CE DOCUMENT
>
> **`PREREGISTRATION.md` §AMENDEMENT n°1 (2026-08-21).** Le verdict `ORB_KILL` ci-dessous **tient
> dans ses termes** — mais son entrée de coût (**1.80 bps**) a été mesurée **sur un autre broker**
> (violation L33). La mesure **native FTMO** donne **0.96-1.05 bps** ⇒ le t passe de **0.48 à
> 1.56**, ce qui reste **sous le seuil R2 de 2.0**.
>
> **Le sleeve est néanmoins ARMÉ en production** (`FU_ORB_RISK = 0.0025`, compte <ACCOUNT_ID>), par
> une **dérogation opérationnelle explicite et bornée** : EV ≈ 0 au coût mesuré, risque $25/trade,
> et les fills sont la **seule** route vers la mesure de dérapage manquante. Sortie de dérogation
> gelée : **N=30 fills, coût tout-compris > 2.5 bps ⇒ désarmement** (~octobre 2026).
>
> Ne pas conclure « kill non réconcilié » sans lire l'amendement — un audit indépendant l'a fait
> le 2026-08-21 et a classé à tort la contradiction en priorité n°1.

## 1. Verdict P1 : **ORB_KILL** par la règle R2

| coût RT (bps) | mean R | t HAC(6) | IC95 block-bootstrap | R2 |
|---:|---:|---:|---:|---|
| 0.00 | +0.04916 | 2.74 | [+0.0143, +0.0840] | PASS |
| 0.47 | +0.03861 | 2.15 | [+0.0037, +0.0734] | PASS |
| 0.94 | +0.02805 | 1.56 | [−0.0070, +0.0629] | KILL |
| 1.50 | +0.01547 | 0.86 | [−0.0196, +0.0505] | KILL |
| **1.80 (mesuré)** | **+0.00873** | **0.48** | **[−0.0264, +0.0438]** | **KILL** |
| 2.20 (codé en dur) | −0.00025 | −0.01 | [−0.0355, +0.0350] | KILL |

- **Frontière R2 (t HAC = 2.0) : 0.588 bps RT.**
- **Point mort de la MOYENNE : 2.189 bps RT.**
- Coût mesuré : **1.80 bps** ⇒ **R2 fire, avec un facteur 3 de marge.**

**R4 (walk-forward expanding 5 folds, au coût mesuré) : 2/5 folds positifs = 40 %**, sous le
seuil RESEARCH_PASS (50 %) et très sous PROPFIRM_PASS (60 %). Les deux folds positifs sont **les
deux derniers** (2021-02→2023-10 : +0.073, t 1.83 ; 2023-10→2026-05 : +0.088, t 2.04) ; les trois
premiers sont négatifs. L'edge est **entièrement récent**.

**Deux règles pré-enregistrées indépendantes tirent. Verdict : ORB_KILL.**

### 1.1 Le piège : on comparait au mauvais seuil

Le point mort de la **moyenne** vaut **2.189 bps** — soit, à 0.5 % près, la constante **2.2**
codée en dur dans `phase0_rt_cost_bps.csv`. Cette coïncidence a fait paraître le sleeve
« marginal mais vivant » dans toutes les analyses antérieures. Or le gate pré-enregistré n'est pas
la positivité de la moyenne : c'est **t HAC > 2.0 et IC excluant 0**, franchi dès **0.588 bps**.
Le ledger de branches de `spec_v22.yaml` ne montait qu'à 1.5 bps : **il n'a jamais affiché le
croisement**, ni celui de R2 ni celui de la moyenne.

## 2. L59 ne s'applique PAS à cet ORB — mon alarme d'ouverture était fausse

Le canal *gap* est **vide sur les deux jambes** :

| jambe | N | fraction ouvrant au-delà | ampleur |
|---|---:|---:|---|
| Sortie STOP (le chiffre L59) | 1587 | **0.00 %** (0/1587) | — |
| Entrée (barre de déclenchement) | 4013 | **0.274 %** (11/4013) | **tous exactement 1 tick** |

L'alignement est établi, pas supposé : reproduction du ledger sur le M1 à **4013/4013** pour
`or_hi, or_lo, level, stop_eff, exit_px, direction, bi, ttb_5min, outcome`, avec falsificateur
d'horloge (OR décalée de −60/+60 min ⇒ **0.00 % / 0.02 %** de reproduction). Contrôles de qualité :
0 barre à fourchette nulle (L60), 0 trou de cotation (un trou fabriquerait un faux gap).

**Mécanisme** : le 25 % de L59 vient de barres **DAILY à gap overnight**. Ici on est en **intraday
RTH continu** — un stop est franchi tick par tick, pas sauté. Les 11 gaps d'entrée sont tous sur
`ttb_5min = 0`, la seule minute où une ouverture peut sauter.

**Limite à ne pas effacer** : la mesure est partiellement circulaire (`exit_px` du ledger a été
*construit* sur ce même M1), et l'OHLC M1 ne résout pas l'infra-minute. « Le canal gap est vide »
est solide ; « le fill est gratuit » ne l'est pas.

## 3. Ce qui tue le sleeve : le spread, mesuré deux fois indépendamment

| source | N | coût |
|---|---:|---:|
| Cache spread US100 (`US100_daily_cet.parquet`, médiane 750 j) | 2497 j | **1.804 bps RT** |
| Fills LIVE du compte FTMO (entrée +2.169 − sortie 0.374) | 12 | **1.795 bps RT** |

Deux méthodes sans rapport, **même réponse à 0.5 % près**. Le 2.2 codé en dur est bien un défaut
(US500/US100/US30/GER40 portent **tous exactement 2.2** — signature d'une constante) : mécanisme
confirmé, valeur corrigée à 1.80.

**Décomposition entrée/sortie sur les fills réels** (la mesure que la procédure N=60 demandait) :

| jambe | N | moyenne (bps) | IC95 | % adverse |
|---|---:|---:|---|---:|
| **ENTRÉE** `micro_entry` (stop natif) | 12 | **+2.169** | [+1.254, +3.192] | **91.7 %** |
| SORTIE `micro_stop` (SL serveur) | 4 | +0.430 | [+0.04, +0.82] | 75 % |
| SORTIE `micro_time` (marché 22:00) | 6 | −0.997 | [−3.75, +0.67] | 33 % |

⚠ **N=12 ≪ 60** : la procédure pré-enregistrée n'est **pas** satisfaite. Mais l'IC de l'entrée
exclut décisivement tout ce qui est sous 1.25 bps, et **l'entrée seule dépasse déjà la frontière
R2 de 0.588 bps par un facteur 3.7**. Le tout-compris à 1.80 repose sur une sortie *favorable*
estimée sur 12 fills à écart-type 2.38 ; si les sorties valent en réalité 0, le tout-compris monte
à 2.17 et la moyenne elle-même passe négative. **Le kill est robuste dans les deux sens.**

**Véhicule (H4/L33)** : le ledger est en **NQ futures**, l'exécution en **US100.cash CFD**. Le
BUY STOP MT5 se déclenche sur l'**Ask** — le bid doit atteindre `level` + spread — ce qui explique
mécaniquement pourquoi l'entrée live coûte 2.17 bps quand le gap NQ vaut 0. La conclusion
« gap nul » est établie **sur NQ** et ne se transporte pas au CFD.

## 4. Verdict P0 : **vm funded = 0.85** (contre 1.0 déployé)

Grille 8 vm × 6 coûts × {IS 2013-17, OOS 2020-24}, N = 93 / 98 cohortes
(`funded_vm/out/vm_orb_grid.csv`).

**Le désaccord IS/OOS de `p3_funded_vm_regime` est REPRODUIT sur le moteur courant**, et la
falaise aussi. Colonne ORB OFF (la seule pertinente une fois P1 tranché) :

| vm | OOS bust | OOS ev504 | IS bust | IS ev504 |
|---:|---:|---:|---:|---:|
| 0.80 | 3.1 % | 1217 | 46.2 % | 625 |
| **0.85** | **4.1 %** | **1328** | **41.9 %** | **653** |
| 0.90 | 13.3 % | 1433 | 59.1 % | 670 |
| **1.00 (déployé)** | **34.7 %** | **1353** | **59.1 %** | **688** |
| 1.10 | 55.1 % | 1358 | 59.1 % | 778 |

**vm 0.85 contre vm 1.0 : −$25 d'EV en OOS, −$35 en IS — et −30.6 pt de bust en OOS, −17.2 pt en
IS.** L'EV est plate, la mortalité s'effondre. La zone **[0.80-0.90]** tient, et elle tient
**aussi bien ORB allumé qu'éteint** (à coût 1.8, ORB ON : bust 16.3 % à vm 0.85 contre **51.0 %**
à vm 1.0). Le point exact 0.85 reste du bruit — c'est la zone qui décide, conformément à p3.

Sur le critère funded correct (`μ/h`, cf. §5), l'écart est encore plus net : `v_inf` OOS ORB OFF
passe de **3 764** à vm 1.0 à **30 318** à vm 0.85. ⚠ Ces `v_inf` reposent sur 3-4 busts sur 98
cohortes et sont numériquement instables — à lire comme un ordre de grandeur, pas un chiffre.

## 5. Implication inconfortable

À la bascule, avec l'ORB tué (P1), l'or en dead-zone et le J1 suspendu par son gate à hystérésis
(reprise exige USDJPY < 155 pendant 10 j, niveau 159.3), **le book funded se réduit aux deux
jambes overnight à `on_w` 0.35 × vm 0.85**, soit ~0.30× l'équité par jambe. À ~8 bps de dérive
nette de swap sur ~$3 000 de notionnel, cela produit quelques dollars par nuit, deux nuits par
semaine.

**Le compte funded démarre donc sans moteur validé.** L'EV modélisée que l'ORB apportait
(+$967 en OOS à vm 0.85) n'était pas réelle : elle reposait sur un edge par trade dont l'IC
contient zéro et qui échoue 3 folds sur 5. La sim ne sait pas que la moyenne est indiscernable de
zéro — c'est exactement ce que la règle R3 (UNDERPOWERED ≠ PASS) existe pour attraper.

## 6. État des livrables

| Volet | Données | Rapport |
|---|---|---|
| A — entrée | complet | **`entry_cost/RAPPORT.md`, 336 lignes** |
| B — sortie L59 | complet (`b1_align.txt`, `b2_exit_stop.txt`) | non écrit (coupure) |
| C — spread/véhicule | complet (12 CSV) | non écrit (coupure) |
| D — sweep vm | complet (`vm_orb_grid.csv`, `pareto.csv`) | non écrit (coupure) |

Aucune donnée perdue. Les conclusions ci-dessus sont lues directement dans les sorties brutes.

## 7. Reste ouvert

1. **La procédure N=60 n'est pas satisfaite (N=12).** Le kill ne dépend pas d'elle — l'IC exclut
   tout ce qui sauverait le sleeve — mais la mesure propre reste à faire si on rouvre un jour.
2. **`ttb_5min = 0` porte 47 % des trades et 100 % des gaps d'entrée.** Non exploité (prereg §4
   interdit de toucher au signal), mais c'est une observation de structure à verser au dossier.
3. **Le gross ORB vit entièrement dans `regime_tag = trending`** (+0.0655 R sur 2877 trades) ;
   `chop` et `vol_shock` (1136 trades, 28 %) sont nuls **avant tout coût**. Remonté, pas exploité.
4. **Écart de fidélité entrée** : le LIVE place un stop AU REPOS (déclenché au *touch*), le ledger
   déclenche sur franchissement *strict* ⇒ le live serait entré **plus tôt sur 3.84 % des jours**.
   Écart de timing, pas de prix. Non corrigé (signal gelé).
