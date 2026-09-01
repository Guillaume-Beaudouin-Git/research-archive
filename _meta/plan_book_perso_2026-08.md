# Book personnel — plan au 2026-08-28

Capital ~€12-15k, compte IBKR, hors propfirm. Objectif : croissance maximale du capital
sous contrainte de non-ruine.

---

## 1. La contradiction du dossier, et sa résolution

Deux études du dossier se contredisent frontalement :

| | date | verdict | source |
|---|---|---|---|
| Growth engine | 2026-07-18 | **NO-GO à €13k** — meilleure config SR 0.25, +2.8 %/an ; month-end micro-yield ≈ **plat** (+$208 sur 7 ans) | `growth_engine_2026-07/BACKTEST_RESULTS.md` |
| Month-end vehicle | 2026-07-30 | **+$2 275/an (+17.6 %), Sharpe 0.92**, marge $1 800 = 14 % du compte | `month_end_vehicle_2026-07/RESULTS.md:241` |

**Ce n'est pas une divergence statistique, c'est une divergence de VÉHICULE.**

L'étude du 18 juillet a supposé qu'à €13k le contrat ZN complet était inaccessible et s'est
rabattue sur le **Micro Treasury Yield** (5YY/10YY, DV01 **$10/bp**). Son propre diagnostic est
juste : « month-end micro-yield ≈ FLAT — DV01 $10/bp trop petit à €13k ».

Mais ZN est trop gros **en notionnel** ($110-120k), pas **en marge**. Les futures de taux ont une
marge faible parce que leur volatilité est faible : **~$1 800, soit 14 % d'un compte de €13k**.
Le DV01 de ZN vaut ~6.5× celui du micro. Le correctif n'est pas d'attendre plus de capital,
c'est de prendre le bon contrat (L53).

⚠ **Conséquence : la conclusion « €13k est sous le seuil de viabilité » ne tient plus pour le
sleeve month-end.** Elle reste vraie pour le book *continu* (trend multi-contrats), qui lui exige
bien €30-50k.

---

## 2. Ce qui est déployable aujourd'hui

**Sleeve unique — month-end Treasury flow-alpha.** Long 1 ZN sur les 3 derniers jours ouvrés du mois.

| | |
|---|---|
| validation | t_HAC **4.76** (ZN), 24 ans (2002-2026), placebo **p=0.000** |
| décroissance | **aucune** — SR 0.90 pré-2022, **0.89** post-2022 (le « déclin » observé était un artefact de l'ETF TLT) |
| autres jours | **−0.71 bps** ⇒ effet concentré = flux, pas bêta |
| espérance | **+$2 275/an (+17.6 %)**, sd $2 473, **Sharpe 0.92 net de coûts** |
| pire événement historique | **−$2 009 (−15.5 %)** |
| exposition | **14 % des jours** — flat 86 % du temps |
| marge | ~$1 800 (14 % du capital) |
| fréquence | 12 événements/an |

**Pourquoi le risque de ruine est structurellement bas ici** : l'intermittence. Un book continu
levé 8× encaisse −73 % de drawdown réel ; ce sleeve, exposé 14 % des jours, reste peu profond.
C'est l'intermittence qui autorise le levier, pas le money management (L53, et le contre-exemple
du book continu dans `VALIDATED_month_end.md`).

**C'est tout le book déployable à €13k. Un sleeve.** Et c'est cohérent : croissance = SR²/2,
et un SR de 0.92 sur une sleeve à 12 événements/an donne ~17.6 %/an, pas davantage.

---

## 3. La contrainte de capital, chiffrée

Le piège n'est pas le capital en soi, c'est la **granularité** — un contrat ou rien (L57).

| contrat | notionnel / marge | déployable à €13k ? |
|---|---|---|
| **ZN** (10 ans) | notionnel ~$115k, **marge ~$1 800** | ✅ le cœur |
| **ZF** (5 ans) | marge ~$1 000 | ✅ candidat n°2 (SR **1.11**, le meilleur des trois) |
| M2K / MCL / M6E | $8-14k/lot | ✅ mais sleeves trend faibles (SR 0.35-0.47) |
| MES / MGC | $38-40k/lot | ❌ arrondit à 0 au Kelly survivable |
| ZN + ZF + trend simultanément | — | ❌ c'est là qu'est la vraie barrière €30-50k |

Donc la formulation exacte du problème rencontré : **on ne peut pas activer le book *diversifié*
à €13k — mais on peut activer sa meilleure sleeve.**

---

## 4. Eightcap — vérification

Faits relevés (Raw account) : EURUSD spread moyen **~0.11 pip** + commission **$7 RT/lot**, soit
**~0.81 pip tout compris ≈ 0.75 bps RT** sur $108k de notionnel. Régulé ASIC/FCA/CySEC, levier
retail plafonné **1:30**.

**C'est réellement bon marché** — ~3.3× moins cher que les **2.48 bps RT** mesurés chez FTMO, et
sous la fourchette 2-7 bps que le dépôt attribue au CFD retail. La recommandation de ton ami
n'est pas fausse sur le courtier.

Trois raisons pour lesquelles ça ne change pas le plan :

1. **Eightcap n'a pas de futures CME.** Il ne peut pas héberger la seule sleeve validée. C'est
   dirimant.
2. **Ça ne ressuscite pas le FX intraday.** L43 exige `gross/cost_p95 ≥ 1.5` ; le meilleur ratio
   jamais observé est **0.36** à ~2.5 bps. À 0.75 bps le ratio monte à **~1.1** — mieux, toujours
   sous la porte. Et L43 a été **répliquée trois fois** (0.336 / 0.38 / 0.36) puis une quatrième
   fois hors FX (0.38) : c'est une constante du tier retail, pas un accident de courtier.
3. **IBKR est déjà moins cher à taille correcte** (~0.4-0.5 bps RT sur IDEALPRO) — avec une
   réserve L57 : le minimum de **$2/ordre** rend le petit notionnel coûteux (~1.6 bps à $25k).

**Verdict : venue secondaire légitime, à garder en réserve si une sleeve FX passe un jour la
porte. Pas la venue primaire.** Le problème n'a jamais été le courtier FX, c'est que nos edges
ne sont pas en FX.

---

## 5. Feuille de route

| phase | capital | contenu | attendu |
|---|---|---|---|
| **0 — construire** | — | compte + couche d'exécution + marge vérifiée | fenêtre **28-30 sept.** |
| **1** | €13k → €20k | month-end ZN seul, 1 contrat | ~17.6 %/an, pire événement −15.5 % |
| **2** | €30-50k | + ZF, + sleeve trend | SR combiné ~1.0 → 18-25 %/an |
| **3** | €50k+ | book diversifié complet | SR 1.68 true-OOS, mais non levierable à 50 % |

**Temps de doublement à 17.6 % : ~4.3 ans.** C'est le chiffre honnête.

⚠ **Ce que le dossier a déjà prouvé trois fois, par trois voies indépendantes** (queue
quotidienne, déployabilité, corrélation de crise) : **une croissance rapide à faible risque
n'existe pas à €13k**. « >50 %/an rigoureux » exige ~25× de levier, dont la queue de ruine croît
plus vite que la croissance. Ce n'est pas un manque d'effort, c'est de l'arithmétique
(croissance = SR²/2). Toute proposition future promettant mieux doit être traitée comme une
erreur de mesure jusqu'à preuve du contraire.

---

## 6. Urgent

1. **Compte IBKR ouvert et alimenté ?** — la couche d'exécution n'existe pas (`growth_engine_2026-07`).
2. **Vérifier la marge ZN réelle** — l'étude la note « indicative, non scrapée ».
3. **Écrire la couche d'exécution** — signal déterministe (3 derniers jours ouvrés), pas de
   discrétion. Le moteur testé existe : `growth_engine_2026-07/survival_core/signal_engine.py`.
4. **Fenêtre suivante : 28-30 septembre 2026.** Celle d'août (27-28-31) est en cours et perdue.

## 7. Pistes à creuser, par espérance

| piste | pourquoi | Δn_tests |
|---|---|---|
| **Ajouter ZF** | SR **1.11**, le meilleur des trois maturités ; marge ~$1 000 | 0 (déjà mesuré) |
| **Commodity TSMOM sur vrais futures** | testé sur **12 ETF** dont USO/UNG, alors que Hurst-Ooi-Pedersen opère sur **~60 futures** — trois violations simultanées des règles maison | **0** (correction) |
| **Carry cross-asset (Koijen 2018)** | le carry FX et le carry commodités CFD sont fermés, mais la construction **multi-classe** ne l'a jamais été — écart de breadth **1/6** | > 0 |
| **Les 11 edges rouvrables** | sur 118 edges inventoriés, 11 nomment le compte personnel comme voie de ré-ouverture, **zéro ne nomme FTMO** | variable |
