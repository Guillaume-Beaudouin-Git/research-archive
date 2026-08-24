# POSTMORTEM DE PROCESS — programme `btc_intraday_ftmo`

**Auditeur ≠ auteur · 2026-07-13 · offline.** Objet : PAS un audit de stratégie (les deux specs sont
mortes par le DSR du programme lui-même). Audit du **process** : deux kill rules pré-engagées franchies
sans arrêt. Sources : `N_ledger.md`, `Rapport_BTC_intraday_FTMO.docx` (#1), `Rapport_Regime_Rotation_BTC.docx` (#2).

## 1. Timeline de la dérive — où « UN shot » est devenu ~43 essais
| Étape (ledger) | N | Ce que le protocole autorisait |
|---|--:|---|
| F1a…F3, V-ctrl, V-hv, V-hv-stop | **7** | 3 familles pré-enregistrées |
| **« N=7. STOP »** (ledger l.18) | 7 | Null §9 gelé : **(a) UN shot** sur la direction fade **OU (b) STOP+POSTMORTEM** ; « Décision à trancher AVANT toute nouvelle spec » |
| Pre-reg #2 : MR oversold 6 cellules + gamma/expiry 6 cellules | **19** | ← **POINT DE RUPTURE** : ni (a) ni (b). 12 essais, re-framés en « nouvelle pré-reg » |
| Extension cross-asset (BTC+ETH+SOL, DOGE+XRP+BNB, DOGE) | ~25 | non incrémenté au ledger |
| Alpha-vs-beta (BTC last-Fri, ETH, up-morning, placebo ordinaire) | ~28 | non incrémenté |
| Sizing + overnight 21-23h | ~30 | non incrémenté |
| Rotation régime ét.1-3 + matrice 6×4 + vol-est ×4 (§5.4) + combos book ×4 (§5.5) + MA200/horizons | **~50** | non incrémenté |

**Diagnostic.** Le null §9 plafonnait l'après-STOP à **≤ 1 essai** (« UN shot »). Ce qui a été exécuté :
**~43 essais** (N 7 → ~50). Il n'y a **aucune entrée de décision** au ledger entre « N=7. STOP » et
Pre-reg #2 : l'option (a)/(b) n'a jamais été tranchée explicitement — c'est une **dérive**, pas un choix.
Le mécanisme : chaque question suivante (« est-ce du gamma ? cross-asset ? du beta ? quel sizing ? quel
régime ? ») a été **re-pré-enregistrée comme un null neuf**, remettant le compteur d'essais à zéro au lieu
de l'imputer au budget DSR ouvert au N=7. Le « re-pré-enregistrer pour reset le compteur » EST le failure mode.

## 2. Le DSR 0,02 — le fait établi (aucune accusation)
- **Calculé et écrit** : `N_ledger.md` l.46 (« Audit indépendant #2 monthly … **DSR 0,02**, sign-flip pré-2022 »).
- **Absent du rapport #1** : DOCX §5.1 liste **8 métriques** (N, WR, W/L, net moyen, HAC t, best, MAE moy, MAE pire) — **DSR omis**.
- **Euphémisé dans la fiche** : `SLEEVE_month_end_bounce.md` §6 « **DSR marginal** → incertitude large », promu §Statut « candidate validée ».
- **Le rapport #2 le SAIT** : §1/§7.1 « the same gate that **produced NO-GO on the earlier month-end sleeve** ». → **les deux rapports du même jour (12-07) se contredisent** : #1 promeut, #2 acte le NO-GO DSR de #1.
- **Pas d'écrasement git** : le ledger + les 2 DOCX sont des fichiers **non-suivis** (produits hors repo, ajoutés à la racine) → aucun historique de commit. Le 0,02 n'a pas été supprimé en git ; il a été **calculé (ledger) puis non repris dans la table de métriques du rapport**. Omission au stade rédaction, pas manipulation.

## 3. `n_trials` honnête + E[maxSR] + DSR recalculés
Ventilation : 19 déclarés + 6 cross-asset + 3 alpha-vs-beta + 2 overnight/sizing + matrice régime **6×4=24**
… bornée : les 6×4 se recouvrent avec le trend/capitulation retenus → **n_trials effectif ≈ 45-55, retenu 50.**

| grandeur | valeur (n_trials=50, base annualisée √365) |
|---|---|
| E[maxSR] (Bailey-LdP) | **1,37 / 1,82 / 2,28** pour sd(SR)=0,6 / 0,8 / 1,0 → **≈ 1,8-2,3** (sd réaliste 0,8-1,0 vu les Sharpe de −0,83 à +1,13) |
| Meilleur book obtenu | **1,13** → **≈ la moitié de E[maxSR]** |
| **DSR regime-rotation** (Sharpe 1,13, T≈3066 j) | **0,0000** (aussi 0,0000 à Sharpe 0,79) — confirme le « ≈0,00 » du rapport #2 |
| **DSR month-end** (par-trade, T=28, sd calendaire 0,367) | **0,075** à n_trials=50 (0,15 à N=25) — cohérent avec le **0,02** du ledger |

→ **Les deux specs promues sont DSR-mortes au n_trials honnête. 0,02-0,07 et 0,00, seuil 0,95. Confirmé, pas infirmé.**
Le budget de multiple-testing de l'espace prix/régime BTC est **épuisé** : E[maxSR]≈2 > tout Sharpe atteignable
mono-actif (plafond 1,1-1,2). Tout nouveau candidat de cet espace **naît mort** (y c. l'expiry-hebdo — non testé, cf. §2 des consignes).

## 4. Les trois erreurs arithmétiques du rapport #2
**(E1) EV §7 — mauvais p(pass).** `0,40 × 913 − 95 = 270,2` (le rapport écrit **266** : incohérence interne
de ~$4, cohérent seulement avec E[funded]≈$902 ou fee≈$99). Surtout : **0,40 = trend sleeve SEUL** (§5.5 ligne A),
alors que le **2-sleeve book = p(pass) 0,46** (§5.5). Au bon p : **0,46 × 913 − 95 = +$325** (≈ le +$326 attendu).
→ Le rapport **sous-estime son propre EV/attempt** en prenant le p du sleeve solo. Le bon chiffre au face-value = **+$325/attempt**.

**(E2) §5.5 — MaxDD −17 % ⁠sous barrière −10 % statique.** À sizing natif (1×), un book qui drawdown −17 %
**buste** (touche −10 % avant −17 %). Donc p(pass)=46 % est calculé à un **sizing réduit non déclaré** :
facteur ≈ **10/17 ≈ 0,59×** pour ramener −17 % sous −10 % (borne haute ; en pratique < pour laisser une marge).
Ce de-levering **divise aussi le rendement par ~0,59×** → +10 % atteint **~1,7× plus lentement** (cohérent avec la
note ledger « MaxDD −33 % → 0,30× → +10 % en ~22 mois »). **Le 46 % et le Sharpe 1,13 natif ne coexistent pas au même sizing.**

**(E3) EV par-attempt vs par-campagne — non comparable.** Le +$266 (ou +$325 corrigé) est **par attempt** (un achat de
challenge) ; le book affiche **+$740 par campagne** (91 j, rachats jusqu'au pass, puis funded). Normalisation (rachats
illimités jusqu'au 1ᵉʳ pass, **hors mur 91 j**) : `EV/campagne ≈ E[funded] − fee/p = 913 − 95/0,46 ≈ +$707` (**borne
haute**). Avec le mur 91 j **et** le sizing conservateur (E2, attempts plus lents → moins d'attempts casés, p(campagne)<1),
c'est **nettement moins**. → même normalisé, l'EV ne rachète rien : le tueur reste le **DSR 0,00**, pas l'EV.

## 5. Règle de process (3 lignes, proposée)
1. **DSR bloquant et dans la table de métriques principale** de tout rapport (pas en note de bas de page) : un
   rapport dont la table primaire omet le DSR est rejeté avant lecture.
2. **La décision de null pré-engagée (STOP vs UN-shot) doit être une entrée de ledger DATÉE et signée** avant toute
   nouvelle spec ; interdit de « re-pré-enregistrer » un nouveau null qui reset le compteur d'essais d'un espace déjà ouvert.
3. **`n_trials` cumulatif de l'ESPACE (pas du sous-null)** reporté dans chaque rapport, avec E[maxSR] ; « candidate validée » exige DSR ≥ seuil à ce `n_trials`-là.
