# Rapport de stratégie — book FTMO funded, jour 1

**2026-08-17.** Compte `<ACCOUNT_ID>`, FTMO-Server3, hedging, $10 000, armé à 14:50 UTC.
Sources : simulation 2 ans 280 cohortes (`out/`), audit de bascule
(`orb_cost_funded_2026-08/AUDIT_BASCULE_FUNDED_2026-08-17.md`), analyse des sleeves éteintes
(`reaudit_vehicule_2026-08/SLEEVES_XAU_JPY_2026-08-17.md`), mesure de spread native
(`spread_log_202608.csv`, démarrée ce jour).

---

## 1. Ce que le book EST réellement aujourd'hui

Quatre moteurs sont spécifiés. **Deux sont éteints.**

| moteur | état | depuis | nature |
|---|---|---|---|
| Jambes ON (US100 22:05, GER40 17:35) | **actif**, lun+mar | — | exposition **calendaire**, LONG-only, **sans signal** |
| ORB funded (US100, ~16:00) | **actif**, $25/trade | ce jour | breakout intraday, deux stops opposés |
| Or (XAUUSD) | **ZÉRO** | 2026-04-15 (88 séances) | TSMOM sign-blend, deadband θ=0.34 |
| J1 (USDJPY) | **ZÉRO** | 2026-03-27 (101 séances) | momentum 12-1 long-only + gate à hystérésis |

**Le book déployé est donc : une exposition calendaire long-only sur indices, plus un bracket
intraday.** Ce n'est pas le book à quatre moteurs des documents de conception. Il faut le nommer
correctement avant d'en discuter les mérites.

---

## 2. Ce qui est solide

- **L'infrastructure.** La campagne P1+P2 est passée en 23 jours, zéro intervention, zéro
  breaker, slippage moyen **+0.13 bps** sur 10 jambes indices. Le redéploiement du jour (compile
  0/0, bascule de compte, purge d'état, redémarrage watchdog en 126 s) s'est fait sans incident.
- **La géométrie est comprise et respectée.** Plancher statique $9 000 (confirmé en source
  primaire ce jour), barrière daily `solde − $500`, retraits tous les 14 jours de trading.
- **La politique de retrait est la bonne.** Le cash sorti est à l'abri, le buffer ne grandit
  jamais, donc retirer agressivement est quasi sans coût. C'est déjà ce qui est fait.
- **L'ORB se défend sur les chiffres** : il triple presque la médiane 2 ans ($382 → $1 046) sans
  dégrader le 5e percentile ($74 → $92).

---

## 3. Ce qui ne va pas

### 3.1 Le gate J1 n'est pas une suspension, c'est une retraite — et personne ne l'a décidé

Pour rouvrir, il faut **10 clôtures consécutives ≤ 155**. Donc `p[t−21] ≤ 155`. Or le signal est
`p[t−21]/p[t−252] − 1 > 0`, long-only. **Les deux conditions sont anti-corrélées par
construction** : le prix qui rouvre le gate est précisément celui qui annule le momentum qu'il
protège. Mesuré : à 155 dans 63 séances, momentum = **−0.88 %**.

⇒ P(gate ouvert) 6 % / 27 % / 36 % à 1/3/6 mois, mais **P(sleeve réellement productive)
6.3 % / 2.4 % / 6.3 %, et 0.4 % à 12 mois.**

Et le seuil est **absolu**, donc non invariant au régime. Fraction du temps OFF : **0.0 % chaque
année de 2007 à 2023**, 11.2 % en 2024, 0 % en 2025, **62.5 % en 2026**. Conçu contre une queue
occupant 2.53 % du temps, il **est devenu le régime**.

**Le point grave** : l'étude a ratifié le bras GATE160 à **Δp +0.65 pt, IC [0.00, +1.95]** — un
effet qui contient zéro. Le bras FULLOFF, mesuré à **Δp −7.58 pt [−12.99, −2.81] / ΔEV −$87.6**,
a été déclaré « borne pire-cas » et **non retenu**. Depuis le 2026-03-27, le livre **subit
FULLOFF**. Le gate fonctionne exactement comme spécifié ; c'est la spécification qui a un état
absorbant que personne n'a choisi d'habiter.

### 3.2 Le θ de l'or vient d'un panier et a été porté verbatim sur une sleeve mono

`sig = moyenne des signes sur {60, 120, 250}` ne peut valoir que **±1 ou ±1/3**. Le deadband
`θ = 0.34` étant au-dessus de 1/3, il **exige l'unanimité des trois lookbacks**.

- `DOC_SIGNAL_PIPELINE.md:37` affirme « il faut ≥ 2 des 3 lookbacks d'accord » — **faux**, et la
  ligne se contredit elle-même dans sa parenthèse. Défaut de documentation à corriger.
- La valeur 0.34 provient d'une spec de **panier à 6 instruments**
  (`STRATEGY_DOSSIER_TSMOM.md:113`). Dans un panier, un deadband coûte de la *breadth*. Sur **un
  seul instrument**, c'est un **interrupteur** — et il éteint **43.9 % des séances** une sleeve
  décrite ailleurs comme le moteur n°1 du book. **Aucun document ne rapporte ce duty cycle.**
- Provenance de la valeur 0.34 elle-même : **introuvable dans le repo**.

État actuel : 60j −5.16 %, 120j −17.74 %, 250j +23.00 % ⇒ sig = −1/3 ⇒ zéro. Rallumage immédiat
exigerait le spot **≥ 5 288 (+19.7 %)** ou **≤ 3 536 (−20.0 %)** : un **corridor mort de 39.6 %
du spot**. À prix inchangé, premier état unanime vers **2026-11-02**, et il serait **négatif**.

### 3.3 Le breaker ne protège pas contre le mode de risque réel

Sur **840 cohortes-simulations de 2 ans, le breaker ne s'est déclenché aucune fois** (moyenne 0,
max 0). L'équité minimale médiane de **9 564** n'est pas un pic intraday : c'est le **solde**
qui a lentement dérivé. Le breaker exige des positions ouvertes ; l'érosion se produit entre
elles. Il protège d'un accident, pas d'un assèchement.

### 3.4 Les ancres de swap sont périmées sur les quatre symboles

`spec_bounds_breach = 1` : XAUUSD −93.35 vs ancre −65.68 (**+42 %**), USDJPY 3.35 vs 0.96,
US100 −620.31 vs −637.16, GER40 −448.82 vs −393.88.

Pour l'or ce n'est **pas** cosmétique : le signal tourne sur un **prix carry-ajusté**, donc le
swap est *dans* le signal. Un portage 42 % plus cher **mal spécifie le signal**, pas seulement
le P&L — et incline le rallumage vers le short.

### 3.5 Aucune alerte sur l'extinction prolongée d'une sleeve

101 séances et 88 séances à zéro. Rien ne l'a signalé. On ne l'a su qu'en le demandant.

---

## 4. Le profil de risque réel — ce que le taux de bust cachait

280 cohortes, 2 ans, vm 1.0, or et J1 à zéro :

| scénario ORB | net méd. | p5 | éq. min méd. | buffer consommé | P<9500 | **P<9250** | bust | % temps <10k |
|---|---|---|---|---|---|---|---|---|
| OFF | $382 | $74 | 9 651 | 35 % | 18 % | **2 %** | 0 % | 79 % |
| 0.96 (mesuré) | $1 046 | $92 | 9 596 | 40 % | 24 % | **14 %** | 1 % | 68 % |
| 2.17 (tout-compris) | $797 | $35 | 9 564 | 44 % | 25 % | **18 %** | 1 % | 75 % |

**Le bust (1 % vs 0 %) est indiscernable ; la probabilité de brûler ¾ du buffer est 7× plus
grande.** C'est la vraie signature de risque de l'ORB.

Trois faits à intégrer :

1. **Le compte est sous $10 000 entre 68 % et 79 % du temps.** Mécanique : les retraits ramènent
   le solde à 10 000, donc le plus-haut est remis à zéro en permanence.
2. **Toucher 9 500 coûte les deux tiers du rendement mais n'est pas fatal** ($370 de médiane
   contre $1 185).
3. **P(ne pas récupérer les €89 en 2 ans) ≈ 5-7 %.** P(net ≤ 0) = 2.5 % — exactement la
   population « zéro retrait ».

---

## 5. Sommes-nous dans un bon régime ?

**Non, et il faut le dire sans détour : le book est mono et le restera probablement des mois.**

| sleeve | perspective |
|---|---|
| J1 | **retraite de fait**. P(productive) 0.4 % à 12 mois. Ne plus la compter comme diversifieur. |
| Or | rallumage plausible **vers novembre 2026**, et **plutôt en SHORT** (38.5 % short contre 7.7 % long à 6 mois). |
| ON | actif, mais c'est de l'exposition calendaire — sa prime est celle du risque overnight, pas un edge. |
| ORB | actif, EV réelle **non tranchée** tant que le coût FTMO n'est pas mesuré. |

Le corollaire déplaisant : **la diversification prévue du book n'existe pas et ne reviendra pas
d'elle-même.** Les deux diversifieurs sont éteints par des seuils, pas par une décision.

---

## 6. Améliorations, par rapport valeur/risque

| # | action | coût | pourquoi |
|---|---|---|---|
| **1** | **Alerte Telegram si une sleeve est à zéro > 20 séances** | trivial, hors chaîne gelée | corrige la vraie faille : 101 séances d'extinction non signalées. Ne change aucune décision de trading. |
| **2** | **Ré-ancrer les swaps** (les 4) | ré-gel de spec | pour l'or, le swap est **dans le signal** : +42 % le mal-spécifient |
| **3** | **Documenter le duty cycle réel** de l'or et **corriger `DOC_SIGNAL_PIPELINE.md:37`** | nul | la doc affirme le contraire du code |
| **4** | **Ré-examiner θ pour une sleeve MONO**, pré-enregistré | ré-gel | ce n'est pas une optimisation : c'est demander si un seuil de panier a un sens sur un instrument seul |
| **5** | **`on_w` 0.35 → 0.60**, pré-enregistré | ré-gel | le vrai levier de sizing, local au sleeve (vm est global et `FU_VM` est figé) |
| **6** | **Finir la mesure de coût ORB** | en cours | tranche l'EV du moteur qui porte la moitié de la valeur |

**Ce qu'il ne faut PAS faire : toucher au gate J1.** Son motif de protection est vivant
(interventions MoF avril-mai ¥9 788,5 Md, et 30 juillet 163→157 conjointement avec le Treasury
US), et le seuil 160 a une justification économique documentée — ce n'est pas un seuil optimisé.
Le corriger rouvrirait une pré-registration gelée. **La bonne réponse est de le reconnaître comme
une retraite et de cesser de compter J1 dans les plans de book.**

---

## 7. Limites de ce rapport

- Les rendements ORB reposent sur un ledger **idéalisé sur ses deux jambes** (entrée == niveau
  4013/4013, sortie == stop 1590/1590) : optimistes d'une façon qu'aucun paramètre de coût ne
  corrige. **Le +$664 est un plafond.**
- Les 280 cohortes de 2 ans **se chevauchent** (pas ~13 ans de données) : l'échantillon
  indépendant vaut quelques fenêtres, pas 280. Les médianes sont informatives, les probabilités
  de queue le sont beaucoup moins.
- Les probabilités de rallumage des sleeves sont des Monte-Carlo à dérive nulle : elles décrivent
  une géométrie de seuil, **pas une prévision de marché**.
- Aucune mesure de régime propre n'a été calculée pour les jambes ON dans ce rapport.
