# Roadmap FTMO + IBKR — objectif $200k funded

**2026-08-20.** Compte funded `<ACCOUNT_ID>` armé depuis 3 jours, solde 10 013.88.
Ce document est décisionnel : chaque item porte un critère d'abandon.

---

## 1. Les trois questions posées, tranchées

### 1.1 Plusieurs comptes FTMO en parallèle ? — **NON**

`PropFirms/ftmo/rules.md:221` classe parmi les stratégies interdites les
*« group strategies sharing identical EA across many accounts beyond the maximum capital
allocation rule »*. C'est **exactement** ce qu'un second compte piloté par le même EA serait.

- Détenir plusieurs comptes est structurellement possible ; y faire tourner **le même EA** ne l'est pas.
- La sanction ne porte pas sur l'accès mais sur le **GAIN** : FTMO peut refuser un retrait.
- ⇒ **La parallélisation ne peut pas servir à accélérer la route vers $200k.** Un seul compte à la fois.

⚠ La « maximum capital allocation rule » n'est **pas citée en source primaire** dans le repo.
À lire sur ftmo.com **avant** tout achat au-dessus de $10k — c'est elle qui plafonne le total alloué.

**Corollaire matériel** : la question du 2ᵉ VPS / VNC **ne se pose pas**. Elle serait la conséquence
d'une décision interdite. Le VPS actuel (Hetzner CX22) porte un terminal MT5, et
`watchdog_mt5.sh` fait des `pkill -f terminal64` **non scopés** — une seconde instance se ferait
tuer. Ce chantier d'infra n'a de sens que le jour où deux stratégies DISTINCTES tourneraient.

### 1.2 Scaler le compte actuel ? — **BEAUCOUP trop tôt, et la voie est fermée sur les chiffres**

Le **scaling plan est le SEUL canal de compounding** en funded (le buffer ne grandit jamais :
les retraits ramènent le solde à 10 000). Il n'est **documenté nulle part dans ce dépôt**.

Ordre de grandeur du plan FTMO usuel : **+25 % de taille tous les 4 mois**, conditionné à
**≥ +10 % net** sur la période. Deux verrous :

| verrou | chiffre |
|---|---|
| Notre production mesurée | médiane **~$1 046 sur 2 ANS**, soit ~2.6 %/an du compte |
| Exigence du plan | **+10 % sur 4 mois** |
| ⇒ éligibilité | **jamais atteinte** |
| Et si elle l'était : 10k → 200k | ×20 = 13.4 paliers × 4 mois = **4.5 ans** |

⇒ **La route par le scaling est fermée deux fois** : on n'atteint pas le seuil, et même en
l'atteignant l'horizon est absurde. **La seule route vers $200k est l'ACHAT d'un challenge.**

### 1.3 Peut-on acheter directement du $200k ?

Tailles standard : $10K / $25K / $50K / $100K / **$200K** (`rules.md:229`).

Par **L24**, la p(pass) dépend de la **FORME** de la distribution quotidienne face à une barrière
**symétrique**, **PAS de la taille du compte** (mesuré : plateau ~44 % de $10k à $200k). Donc
p(pass) ne se dégrade pas à $200k, et la liquidité non plus (0.716 × $200k = $143k de notionnel
indices CFD, négligeable).

**Ce qui change, et qui joue en notre faveur** : les frais ne suivent pas la taille linéairement.
Le rapport production/frais **s'améliore** avec la taille. C'est le seul argument solide pour
monter — pas une amélioration de l'edge, une amélioration du ratio.

---

## 2. Roadmap vers $200k — et pourquoi 2026 est tendu

### Le calcul honnête

| | |
|---|---|
| p(campagne) du livre **déployé** (MONO) | **53.7 %** |
| Durée d'une tentative | ~38 jours |
| Tentatives attendues | **3.29** (mesuré, pas supposé) |
| ⇒ délai médian pour passer | ~76 jours · **espéré ~125 jours** |
| Coût attendu (frais $200k ≈ €1 080) | **~€3 553**, dont €1 080 remboursés au 1ᵉʳ retrait |

**Départ octobre ⇒ funded $200k entre fin décembre (médiane) et février (espérance).**
**L'objectif « $200k funded live en 2026 » est atteignable au MÉDIAN, pas à l'espérance.**
Et il n'existe **aucun** moyen légal d'accélérer par parallélisation (§1.1).

### Les jalons

| phase | fenêtre | contenu | critère d'abandon |
|---|---|---|---|
| **P0 — preuve** | août → oct. | Le compte 10k encaisse **≥ 2 retraits** sans breach. Mesure du dérapage ORB (N=30). Réconciliation `on_w`. | breach, ou dérapage ORB > 2.5 bps ⇒ ORB éteint et EV re-chiffrée avant tout achat |
| **P1 — décision de taille** | octobre | Lire la *maximum capital allocation rule*. Choisir $100k ou $200k selon la trésorerie supportable (3.29 × frais). | si la règle d'allocation plafonne sous $200k ⇒ viser le plafond réel |
| **P2 — campagne** | oct. → déc. | Un challenge à la fois. Même EA, même spec, sizing inchangé. | 3 échecs consécutifs ⇒ **STOP**, la p(pass) réelle est sous 40 %, re-mesurer avant de repayer |
| **P3 — funded** | déc. → | Retraits agressifs (le cash sorti est à l'abri, le buffer ne grandit jamais). | 2 breaches funded ⇒ le sizing est faux, pas la malchance |

### ⚠ Ce que ce plan NE fait pas

Il **n'améliore pas l'edge**. Il multiplie par 20 une production dont la médiane est **2.6 %/an
du compte**. Si l'edge est plus faible que mesuré, la taille amplifie l'erreur à l'identique.
**P0 existe pour ça** : ne pas payer €3 553 avant que le livre ait prouvé qu'il produit en réel.

---

## 3. Le concurrent interne : IBKR

À ne pas traiter comme un repli. `CLAUDE.md` le classe **véhicule de PREMIÈRE CLASSE**.

| | FTMO $200k funded | IBKR perso €12k |
|---|---|---|
| Production médiane | ~$10 500/an (80 % déjà déduits) | **23-44 %/an** à ¼-½ Kelly (SR combiné 1.02) |
| Capital requis | ~€3 553 de frais | déjà là |
| Compounding | **aucun** (buffer figé) | **oui** |
| Barrière / horloge | −5 % daily, −10 % total, min-days | **aucune** |
| Part du P&L | 80 % | **100 %** |
| Coût d'exécution | 1.0-2.4 bps RT (CFD) | **~0.4 bps RT** (futures) |
| Délai | ~4 mois | immédiat |

**Sur 118 edges inventoriés, 11 nomment le compte perso / les futures comme voie de ré-ouverture.
Zéro ne nomme FTMO.** Trois edges d'affilée ont eu IBKR pour maison.

⇒ Les deux ne sont **pas exclusifs** : instruments différents (futures vs CFD indices), horizons
différents (month-end / trend vs overnight calendaire), corrélation faible. **Mener les deux.**
Mais si l'effort marginal doit aller quelque part, les chiffres disent IBKR.

---

## 4. TO-DO, triée par urgence

### 🔴 Bloquant — avant tout achat de challenge

| # | tâche | qui | délai |
|---|---|---|---|
| 1 | **Lire la *maximum capital allocation rule*** sur ftmo.com. Elle plafonne le total alloué et conditionne tout le §2. | **toi** | 10 min |
| 2 | **Lire le scaling plan** sur ftmo.com et le graver dans `rules.md`. Seul canal de compounding, absent du repo. | **toi** | 10 min |
| 3 | **Dérapage ORB, N=30 fills.** Décide si l'ORB reste allumé. Il porte la moitié de l'EV simulée **et** 7× la probabilité de brûler ¾ du buffer. | automatique | **~octobre** |

### 🟠 Important — sous 2 semaines

| # | tâche | qui | note |
|---|---|---|---|
| 4 | **Amender le pré-enregistrement de l'ORB.** Il tourne en production contre son verdict R2+R4 du 13/08. La décision de le garder est chiffrée et défendable, mais **jamais formalisée**. | moi | dette de gouvernance |
| 5 | **`on_w` 0.35 → 0.60** — réconciliation faite : bust **2.6-3.8 %/an**, pas 15 %. Gain +$104/an médian (+44 %). Exige une chaîne de ré-gel. | décision **toi**, exécution moi | ⚠ le seuil tombe au minimum observé sur 1 292 nuits : **queue pricée sur 1 observation** |
| 6 | **Profil de spread à 2 semaines.** En cours, 13 000+ lignes. | automatique | ~2 sept. |
| 7 | **Alerte de RÉVEIL de sleeve.** L'extinction est désormais la baseline connue ; l'information est dans la transition. | moi | pas encore écrite |

### 🟡 À faire, sans urgence

| # | tâche | note |
|---|---|---|
| 8 | **Ré-ancrer les 4 swaps.** `spec_bounds_breach=1` sur 4/4. Aucun chemin automatique mesuré → panel. Impact mesuré : **nul sur le signal or** (marge > 11.8×), ~$15/2 ans en P&L. | à grouper avec un autre ré-gel |
| 9 | **Sweep `vm` sur le livre réellement déployé.** La grille existante tourne le livre COMPLET (bust 34.7 %) alors que le déployé est MONO (bust 0 %). Le sweep n'a **jamais** été refait sur le bon livre. | |
| 10 | Corriger `DOC_SIGNAL_PIPELINE.md:37` (affirme le contraire du code) et documenter le duty cycle réel de l'or (43.9 %). | trivial |
| 11 | Ajouter `ftmo_live/` au regex hard-fail de `auto-merge.yml:57`. Une PR sur `ftmo_live/brain.py` — **code déployé** — ne rencontre aujourd'hui que GARDE 2. | 1 ligne, PR dédiée |

### ⛔ Ne pas faire

| | pourquoi |
|---|---|
| **2ᵉ compte FTMO avec le même EA** | interdit, `rules.md:221`, risque sur le GAIN |
| **2ᵉ VPS / VNC** | conséquence d'une décision interdite ; sans objet |
| **Rallumer or + J1 pour « diversifier »** | mesuré : moyenne +32 % mais **bust 0 % → 46.6 %** et retraits 23.7 → 11.0. Le livre MONO est peut-être la bonne réponse sur cette géométrie |
| **Chercher un 2ᵉ sleeve FTMO** | 17 760 cellules, 162 specs ré-auditées, 241 exogènes, **zéro survivant**. Le coût mesuré ne rouvre rien (ΔSharpe médian **0.0000**) |
| **Monter `FU_VM`** | la grille donne `v_inf` 3 764 à vm 1.0 contre 30 318 à vm 0.85 ⇒ vm 1.0 est déjà **au-delà** de l'optimum `μ/h` |
