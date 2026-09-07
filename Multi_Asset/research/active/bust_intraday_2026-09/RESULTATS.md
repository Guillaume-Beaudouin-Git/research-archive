# Bust intra-journalier — le zéro tient, et on sait enfin de combien

**2026-09-08.** Complète `funded_5ans_2026-09/RECAP.md`, qui ne voyait que les **clôtures** et le
disait. Ici l'équité est reconstruite **minute par minute** depuis les M1 en vrai UTC.
Δn_tests = 0 — simulation sur données existantes.

## Méthode

Les jambes **overnight** sont les seules **non stoppées** du book : elles portent donc tout le
risque d'excursion intraday. L'ORB, lui, est protégé par un stop broker à 1R (~25 $) — son
excursion est bornée par construction.

Pour chacune des **493 nuits ON** (lundi et mardi) de 2021-09 à 2026-06 : notionnel 0,35 × équité
par jambe, US100 tenu de 22:05 à 15:30 Paris, GER40 de 17:35 à 09:00, marquage sur grille minute
commune, et **scission à 00:00 Paris** puisque la barrière FTMO se ré-ancre à minuit.

## Résultat

| | |
|---|---|
| nuits évaluées | **493** |
| franchissements intraday, jour D | **0** |
| franchissements intraday, jour D+1 | **0** |
| pire excursion jour D | **−217,92 $** — 43,6 % de la barrière |
| pire excursion jour D+1 | −207,19 $ — 41,4 % |

**Zéro franchissement intraday.** La pire excursion de cinq ans atteint **44 % de la barrière**.
Avec le risque borné de l'ORB (~25 $) par-dessus, le pire cas cumulé reste sous **50 %**.

## Ce que le modèle quotidien ne voyait pas — et l'écart est mesuré

| nuit | excursion intraday | clôture du book | ratio |
|---|---|---|---|
| 2025-04-08 | **−217,92 $** | −166,52 | 1,31× |
| 2026-03-02 | −199,02 | −168,92 | 1,18× |
| 2025-04-15 | −176,87 | −157,10 | 1,13× |
| 2026-03-23 | −136,13 | −125,31 | 1,09× |
| 2022-06-21 | −137,54 | −97,65 | **1,41×** |
| **2021-11-29** | **−127,92** | **+11,69** | **10,95×** |

L'excursion intraday dépasse la perte de clôture de **10 à 40 %** en général. Et la dernière ligne
est le cas d'école : une nuit qui plonge à **−128 $** et **clôture à +12 $** — totalement invisible
dans un modèle quotidien.

⇒ **Le facteur de sous-estimation du modèle de clôture est d'environ 1,4× dans le pire cas mesuré.**
Ce n'est pas un ordre de grandeur : le zéro de la barrière journalière survit largement à la
correction, puisqu'il faudrait un facteur **2,3×** pour l'atteindre.

## Ce qui reste hors du modèle, honnêtement

**L'or et USDJPY sont à poids ZÉRO** dans la configuration funded actuelle et n'entrent donc pas
dans ce calcul. Or le seul breach réel de l'historique — compte <ACCOUNT_ID>, juillet — était un flash
move **USDJPY**. Cette queue-là ne s'applique pas au book déployé aujourd'hui, mais elle
reviendrait avec la sleeve J1.

**Les M1 s'arrêtent au 2026-06-05.** Les trois derniers mois ne sont pas couverts.

**Un halt ou un gap de cotation** apparaîtrait comme un saut entre deux barres consécutives, donc
il est capturé — mais l'exécution réelle pendant un halt ne l'est pas.

## Conclusion, et ce qu'elle change

Le verdict de `funded_5ans_2026-09` **tient après correction intraday** : la barrière journalière
n'est pas le mode de mort de ce book. Le pire cas mesuré est à moins de la moitié du seuil, sur
cinq ans et 493 nuits d'exposition.

Le danger reste ce qu'on avait identifié : **le plancher statique par érosion lente**, pas
l'accident d'une séance. Et le breaker M5 — mise à plat si la marge descend sous 30 % du budget
journalier — n'a jamais eu à se déclencher dans cet échantillon, ce qui est cohérent avec une pire
excursion à 44 %.
