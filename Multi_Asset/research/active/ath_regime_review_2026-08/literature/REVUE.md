# Revue de littérature — « proximité du plus haut » et rendements futurs
### Transposabilité vers une exposition LONGUE overnight sur NQ100 / DAX40, ~15 h, lundi + mardi, FTMO Phase 2 10 k€

Date : 2026-08-09 · Auteur : agent revue-littérature · Dossier : `Multi_Asset/research/active/ath_regime_review_2026-08/literature/`

**Convention d'étiquetage utilisée partout dans ce document :**
- `[ÉTABLI]` = résultat lu dans le texte du papier (ou son abstract officiel), reproduit tel quel.
- `[SUGGÉRÉ]` = interprétation avancée par les auteurs eux-mêmes sans test direct.
- `[EXTRAPOLATION]` = raisonnement à MOI, non présent dans la littérature. À traiter comme hypothèse, jamais comme preuve.
- Statut de lecture de chaque source : voir bibliographie en fin de document (`LU-INTÉGRAL` / `LU-PARTIEL` / `ABSTRACT-SEULEMENT` / `MÉTADONNÉES-SEULEMENT` / `NON VÉRIFIÉ`).

---

## ⚠ VERDICT DE TRANSPOSABILITÉ (5 lignes)

1. **NON.** Le corpus « proximité du plus haut » est cross-sectionnel sur ACTIONS INDIVIDUELLES à horizon 1–12 mois ; il ne dit rien d'une décision de timing sur indice.
2. La seule exception marché-agrégé (Li & Yu 2012) prédit avec DEUX ancres de signes OPPOSÉS (`x52` +, `xmax` −) : à l'état exact du desk (proche des DEUX), les effets se compensent par construction — le papier n'identifie que leur DIVERGENCE.
3. **Zéro résultat publié sur la proximité du plus haut à horizon intrajournalier ou overnight.** Aucun. Le seul résultat sub-mensuel existant est un indicateur d'ÉVÉNEMENT (record du Dow → ≈ −8 bps le lendemain, close-to-close, in-sample US 1963-2008), et son mécanisme publié (Yuan 2015 : vente retail à l'ouverture) le place dans la jambe INTRADAY, pas dans la jambe du desk.
4. Côté variance, la littérature dit : **approcher** un plus haut ABAISSE la vol (Driessen-Lin-Van Hemert) alors que **le franchir** la RELÈVE (+46 % de variance idio le lendemain) — donc « près de l'ATH » n'est pas un état unique et l'intuition « basse vol » n'est vraie que d'un des deux sous-états.
5. **Implication L54 directe :** dans le sous-état « approche », le régime prédit une vol BASSE et une moyenne NEUTRE-À-POSITIVE ⇒ la condition liante de L54 (variance et moyenne dans le MÊME sens) est **violée** ⇒ un overlay qui suspend l'exposition sur la distance à l'ATH ne peut structurellement pas aider. Le seul angle non refermé par la littérature est le **TAIL** (Greenwood-Shleifer-You), pas la moyenne.

---

# 1. Ce que chaque papier établit vraiment

## 1.1 George & Hwang (2004), *The 52-Week High and Momentum Investing*, Journal of Finance 59(5), 2145-2176 — `LU-INTÉGRAL`

**Univers / période.** `[ÉTABLI]` Toutes les actions CRSP, 1963–2001 (rendements de portefeuille juillet 1963 – décembre 2001). Données collectées « exactly as described in Moskowitz-Grinblatt ». Aucun test hors États-Unis.

**Définition exacte de la variable — chirurgical.** `[ÉTABLI]` La variable est
> `P_{i,t-1} / high_{i,t-1}`, où `P_{i,t-1}` est le prix de l'action i à la FIN DU MOIS t−1 et `high_{i,t-1}` le prix le PLUS HAUT de l'action i sur la période de **12 mois** se terminant le dernier jour du mois t−1.

Points à ne pas confondre :
- c'est un **ratio borné dans (0,1]**, mesuré au **pas mensuel**, sur une fenêtre **glissante 12 mois** ;
- ce n'est **pas** une distance au plus haut **historique** (max expanding depuis l'origine) — Li & Yu (2012) traitent ces deux objets comme des variables DIFFÉRENTES aux signes OPPOSÉS (§1.3) ;
- ce n'est **pas** un drawdown depuis un max expanding ;
- la variable n'est jamais utilisée en **niveau absolu** pour décider d'être investi ou non : elle sert exclusivement à **classer les titres entre eux**.

**Construction de portefeuille.** `[ÉTABLI]` Stratégie (6,6) : chaque mois, tri des actions sur la mesure ; portefeuille winner = 30 % supérieurs, loser = 30 % inférieurs, **équipondérés** ; détention 6 mois, portefeuilles chevauchants (le rendement du mois t est la moyenne de 6 portefeuilles formés en t−6…t−1) ; **auto-financé long-short** ; un mois sauté entre classement et détention pour neutraliser le bid-ask bounce. Robustesse annoncée en (6,12), (12,6), (12,12).

**Signe et taille de l'effet.** `[ÉTABLI]` Table I :

| Stratégie (6,6) | Winner | Loser | Winner − Loser | t |
|---|---|---|---|---|
| Jegadeesh-Titman (momentum 6 mois) | 1.53 % | 1.05 % | **0.48 %/mois** | 2.35 |
| Moskowitz-Grinblatt (momentum industrie) | 1.48 % | 1.03 % | **0.45 %/mois** | 3.43 |
| **52-week high** | 1.51 % | 1.06 % | **0.45 %/mois** | **2.00** |

Le t de 2.00 est le plus FAIBLE des trois. `[ÉTABLI]` En régressions Fama-MacBeth avec contrôles (taille, bid-ask bounce, dummies JT/MG/52wh), la mesure 52-week high **domine** les deux autres.

**Robustesse.** `[ÉTABLI]` Pas de renversement à long terme pour la stratégie 52wh (contrairement à JT et MG dont les gagnants se retournent) — c'est le résultat central du papier. `[ÉTABLI, PAR ABSENCE]` **Aucune analyse de coûts de transaction** dans le papier ; aucun test hors-échantillon temporel ; aucun test hors-USA. Les portefeuilles sont ÉQUIPONDÉRÉS (donc chargés en small caps).

**Nature du test — décisif pour §2.** `[ÉTABLI]` 100 % cross-sectionnel. Le papier n'exécute jamais une régression de série temporelle prédisant le rendement d'un indice à partir de sa propre proximité au plus haut.

## 1.2 Chen, Stivers & Sun (2024), *Short-term momentum and reversals, turnover, and a stock's price-to-52-week-high ratio*, Journal of Empirical Finance 79, 101556 — `ABSTRACT-SEULEMENT`

`[ÉTABLI, abstract]` Univers : actions individuelles US (je n'ai pas pu vérifier la période exacte ni le filtre d'univers — **paywall ScienceDirect, 403**). Variable : PTH = prix / plus-haut-52-semaines du mois précédent. Horizon : rendements mensuels CONSÉCUTIFS (t−1 → t), soit l'horizon du **short-term reversal**, pas du momentum 6-12 mois.

`[ÉTABLI, abstract]` Résultat : le **reversal de court terme DÉCROÎT** avec (a) le turnover et (b) le PTH du mois précédent, et **bascule en MOMENTUM** pour les titres à la fois à turnover élevé ET PTH élevé. Robuste aux sous-périodes, aux ajustements de risque, à des méthodologies alternatives.

`[SUGGÉRÉ, abstract]` Mécanisme proposé : sous-réaction par ancrage sur le PTH, canal « contrarian price-dampening », renforcé par le turnover ; renforce le canal de rémunération de la fourniture de liquidité.

**Ce que ça apporte à l'arbitrage du §2c :** c'est un papier du camp **sous-réaction / continuation**, et il place l'INTERACTION (PTH × turnover) au cœur — donc le signe du PTH seul n'est pas stable, il dépend d'une seconde variable. Je n'ai pas pu lire les magnitudes ni les t-stats.

## 1.3 Li & Yu (2012), *Investor attention, psychological anchors, and stock return predictability*, JFE 104(2), 401-419 — version publiée `ABSTRACT-SEULEMENT` ; **working paper 2009 lu intégralement** (`LU-INTÉGRAL`, Carlson School)

**⚠ C'est le seul papier du corpus qui répond à la question du desk (niveau MARCHÉ AGRÉGÉ). Tous les chiffres ci-dessous proviennent du WP 2009 « Psychological Anchors, Underreaction, Overreaction, and Asset Prices », que j'ai lu au texte. Les tables exactes de la version JFE 2012 n'ont pas pu être consultées (paywall) — les signes et le message y sont identiques d'après l'abstract publié, les valeurs numériques peuvent avoir changé.**

**Définitions exactes.** `[ÉTABLI]`
- `x52,t = p_t / p52,t` — niveau du Dow Jones Industrial Average divisé par son plus haut **52 semaines**.
- `xmax,t = p_t / pmax,t` — niveau du Dow divisé par son plus haut **historique** (max expanding).
- `D_t` = indicatrice **événement** : 1 si le Dow atteint un **record historique** le jour t. Moyenne = 0.04 (≈ 4 % des jours).
- `I_t` = indicatrice **régime** : 1 si le plus haut 52 semaines ÉGALE le plus haut historique (⇔ « une seule ancre » ⇔ l'indice est à/près de son ATH). Moyenne = 0.51.

**Le desk est simultanément dans `x52 ≈ 1`, `xmax ≈ 1`, `I_t = 1`, et `D_t = 1` les jours de nouveau record.** Retenir cette cartographie, elle porte tout le §2.

**Données.** `[ÉTABLI]` Dow Jones + rendements CRSP value-weighted quotidiens, 1963–2008. Contrôles macro : DEF, TERM, taux réel, inflation, cay, dividend yield. Régressions chevauchantes échantillonnées au pas quotidien + version non chevauchante. t de Newey-West.

**Persistance des régresseurs.** `[ÉTABLI]` AC(1) mensuel : `x52` 0.88, `xmax` 0.93. Corrélation `x52`–`xmax` = **0.84**, `xmax`–`I_t` = 0.57.

**Résultats — Table 3 (Dow, contrôles macro, chevauchant, 1963-2008), coefficients de `D_t`/`I_t`/`DEF` en pourcentage :**

| Horizon | `r_t` | `x52` | `xmax` | `D_t` | `I_t` | R² |
|---|---|---|---|---|---|---|
| **jour** | 0.09 (4.55) | **0.01 (2.34)** | **−0.01 (−3.42)** | **−0.08 (−2.87)** | 0.04 (1.56) | **0.01** |
| semaine | −0.03 (−1.15) | 0.06 (3.49) | −0.06 (−4.02) | −0.08 (−0.64) | 0.25 (1.49) | 0.02 |
| mois | −0.01 (−0.27) | 0.18 (3.45) | −0.19 (−4.15) | −0.04 (−0.13) | 0.86 (1.63) | 0.05 |
| trimestre | −0.05 | 0.56 (3.83) | −0.58 (−4.70) | −0.14 | 2.64 (1.82) | 0.13 |
| 6 mois | −0.01 | 0.81 (3.58) | −1.01 (−5.18) | 0.26 | 5.39 (2.14) | 0.22 |
| an | 0.06 | 0.74 (2.04) | −1.29 (−3.53) | 2.51 (1.56) | 4.84 (0.88) | 0.32 |

Version **non chevauchante** (Table 4) : mêmes signes, R² annuel **0.46** — c'est le « 46 % » de l'abstract.

**Lecture honnête de ces chiffres :**
- `[ÉTABLI]` Le signe est stable : proximité au plus haut **52 semaines** = **POSITIF** ; proximité au plus haut **HISTORIQUE** = **NÉGATIF**. Les t de `xmax` vont de −3.42 (jour) à −5.18 (6 mois).
- `[ÉTABLI]` Les magnitudes de `x52` et `xmax` sont **quasi égales et opposées à tous les horizons** (jour +0.01/−0.01 ; mois +0.18/−0.19 ; trimestre +0.56/−0.58 ; 6 mois +0.81/−1.01). Les auteurs le disent eux-mêmes : « le marché monte le plus quand le Dow est proche de son plus haut 52 semaines **mais loin en dessous de son plus haut historique** ». **Le papier identifie une DIVERGENCE entre deux ancres, pas un niveau.**
- `[ÉTABLI]` Sous-échantillons 1963-85 vs 1986-2008 : `xmax` reste significatif partout (t −1.71 à −3.29), `x52` **s'affaiblit nettement** dans la seconde moitié (t 1.06 à 2.15). Les auteurs le concèdent.
- `[ÉTABLI]` Substituer le Dow par la capi NYSE/AMEX **détruit l'essentiel du pouvoir prédictif** (Table 5 : `xN52` t 1.46 au jour, R² 0.008). Les auteurs y voient une confirmation de la thèse d'ancrage (le Dow est l'ancre médiatique) — `[SUGGÉRÉ]`. C'est aussi, `[EXTRAPOLATION]`, un avertissement : le résultat dépend du CHOIX de l'indice-ancre, ce qui est exactement le degré de liberté qu'un desk répliquerait sur NQ ou DAX.
- `[ÉTABLI]` Robustesse déclarée : G7 (dans la version JFE 2012 — **non vérifié au texte**), échantillon long 1928-2008 où le pouvoir de `x52` est **plus faible** (les auteurs invoquent la Grande Dépression), et remplacer 52 semaines par 26/13/4 semaines donne des résultats **moins significatifs**.
- `[ÉTABLI, PAR ABSENCE]` **Aucun test hors-échantillon (OOS R², Goyal-Welch) dans le WP 2009.** Aucun coût de transaction. Aucune stratégie tradable simulée.
- `[EXTRAPOLATION]` Drapeaux méthodologiques à lever avant toute réutilisation : régresseurs très persistants (AC 0.88/0.93) + rendements chevauchants ⇒ biais de Stambaugh et t de Newey-West anti-conservateurs à horizon long ; un R² in-sample de 32-46 % à horizon annuel sur 45 ans de données chevauchantes est le profil-type de ce que Goyal-Welch montrent ne pas survivre en OOS. **Rien dans ce que j'ai lu ne prouve que ces résultats survivent hors échantillon.**

## 1.4 Tomtosov (2024), *Momentum on historical high*, Finance Research Letters (nov. 2024), DOI 10.1016/j.frl.2024.106216 — `ABSTRACT-SEULEMENT` (paywall, 403 sur ScienceDirect ; abstract non retourné par Semantic Scholar — chiffres ci-dessous issus des extraits de recherche web, **fiabilité réduite, marqués comme tels**)

`[ÉTABLI, abstract/extraits — À RE-VÉRIFIER SUR TEXTE INTÉGRAL]`
- Décomposition des positions LONGUES d'un portefeuille momentum par « localisation de prix » : les titres proches de leur **plus haut historique** représentent **45 % des positions et 70 % des rendements**.
- Momentum formé dans l'univers restreint aux titres proches du plus haut historique : **alpha 6.2 %** contre **1.3 %** pour le momentum formé hors de cet univers.
- Le résultat survit au contrôle du momentum décalé de Novy-Marx (2012) et du ratio 52-week-high de George-Hwang (2004).
- Une source secondaire annonce « +23 % vs le momentum original » — **non vérifié**.

`[SUGGÉRÉ]` Mécanisme : les titres proches du plus haut historique sont très visibles et présentent la plus faible divergence d'opinions (ancrage positif).

**Nature du test :** `[ÉTABLI]` cross-sectionnel actions, tri momentum classique conditionné par la localisation de prix. Horizon mensuel. **Pas de timing d'indice.**

## 1.5 Blau, Griffith, Whitby & Woodward (2023), *Anchor Reversion: The Case of the 52-Week High and Asset Prices*, Journal of Behavioral Finance 26(1), 82-94 — `ABSTRACT-SEULEMENT` (abstract officiel récupéré intégralement)

`[ÉTABLI, abstract]` Définition d'« anchor reversion » : tendance du prix d'une action à **revenir vers son ancre**, ici le plus haut 52 semaines. Résultat : plus une action **s'éloigne** de son plus haut 52 semaines, plus elle a de chances d'y **revenir** le mois suivant ; inversement, une action qui s'est **rapprochée** de son plus haut ce mois-ci a **moins** de chances de faire un grand mouvement vers ce plus haut le mois suivant. Portefeuilles long-short « anchor reversion » : **1.40 % à 1.62 % par mois**. Robuste aux facteurs de risque et à plusieurs caractéristiques cross-sectionnelles, dont le short-term reversal mensuel.

`[ÉTABLI, abstract]` Univers actions, horizon **mensuel**, construction **long-short cross-sectionnelle**. Période et filtres d'univers : **non vérifiés** (paywall Taylor & Francis, 403).

**⚠ Point de vigilance que je signale explicitement :** la variable de tri est **la VARIATION de la distance à l'ancre sur le mois écoulé** (mouvement vers/loin de l'ancre), **pas le NIVEAU de la distance**. Ce n'est donc pas la même variable que celle de George-Hwang ni celle du desk. `[EXTRAPOLATION]` Un long-short mensuel qui achète les titres qui viennent de S'ÉLOIGNER de leur plus haut et vend ceux qui viennent de s'en RAPPROCHER est, mécaniquement, très proche d'un short-term reversal standard ; les auteurs affirment contrôler pour cela, mais je n'ai pas pu vérifier comment. À 1.4-1.6 %/mois brut, la robustesse aux coûts n'est pas démontrée dans l'abstract.

## 1.6 Papiers de contexte lus ou vérifiés (utiles à l'arbitrage)

| Papier | Ce qu'il établit | Statut |
|---|---|---|
| **Huddart, Lang & Yetman (2009)**, Management Science 55(1), 16-31 | `[ÉTABLI, abstract]` Le VOLUME est nettement plus élevé quand le prix franchit la borne haute OU basse de son range passé ; l'effet croît avec le temps écoulé depuis le dernier extrême, avec la petitesse de la firme, avec l'intérêt des particuliers et avec l'ambiguïté de valorisation. Après l'un ou l'autre franchissement, les rendements sont « reliably positive » et les trades classés acheteurs sont élevés chez les petits investisseurs. | `ABSTRACT-SEULEMENT` |
| **Driessen, Lin & Van Hemert (2012)**, Review of Finance 16(1), DOI 10.1093/rof/rfr026 | `[ÉTABLI, abstract]` Les volatilités implicites ET les bêtas **DIMINUENT** à l'approche d'un plus haut ou d'un plus bas 52 semaines ; les volatilités **AUGMENTENT après franchissement**. Effets « economically large and significant ». Approche expliquée par l'ancrage ; franchissement par ancrage + attention. `[ÉTABLI, source secondaire CXO/résumés — à re-vérifier]` variance idiosyncratique −32 % à l'approche du plus haut ; +46 % (plus haut) et +111 % (plus bas) le jour suivant un franchissement ; vol implicite −1 point (moyenne d'échantillon 43). | `ABSTRACT-SEULEMENT` + chiffres secondaires |
| **Yuan (2015)**, JFE 116(3), *Market-wide attention, trading, and stock returns* | `[ÉTABLI, abstract]` Les événements d'attention marché-large (dont **niveaux RECORD du Dow** et articles en une) prédisent que les investisseurs **VENDENT massivement quand le niveau du marché est HAUT** ; cette vente agressive réduit les rendements de marché de **19 bps les jours suivant** l'événement. Données particuliers (courtier) + flux de fonds. | `ABSTRACT-SEULEMENT` (PDF inaccessible : certificat invalide) |
| **Baker, Pan & Wurgler (2012)**, JFE 106(1), 49-71 | `[ÉTABLI, abstract]` Les prix d'offre en M&A sont biaisés vers le **plus haut 52 semaines** (mode = exactement ce prix) ; la probabilité d'acceptation saute de façon discontinue quand l'offre dépasse le plus haut 52 semaines ; +10 % de plus-haut ⇒ jusqu'à +3 % de prime. **Preuve directe que le plus haut 52 semaines est une ancre comportementale** — dans un contexte de négociation, pas de trading. | `ABSTRACT-SEULEMENT` |
| **Della Vedova, Grant & Westerholm (2023)**, *Investor Behavior at the 52-Week High*, JFQA 58(7), 2852-2889 | Existence et métadonnées confirmées (Crossref). Contenu **non lu**. | `MÉTADONNÉES-SEULEMENT` |
| **Du (2008)**, *The 52-week high and momentum investing in international stock indexes*, Quarterly Review of Economics and Finance 48(1), 61-77 | `[ÉTABLI, résultats de recherche]` Applique la mesure 52wh à **18 indices boursiers de pays développés**, déc. 1969 – juil. 2004 ; trouve un rendement de momentum 52wh **positif et significatif**, mais **qui SE RETOURNE à long terme** — contrairement à George-Hwang sur actions. `[EXTRAPOLATION mais quasi certaine]` la stratégie est **cross-sectionnelle ENTRE indices** (long les indices proches de leur plus haut, short les autres), pas un timing d'un indice sur lui-même. | `ABSTRACT/SECONDAIRE` — abstract officiel indisponible (RePEc : « no abstract available ») |
| **Sun (2026)**, *Beyond Volatility: The 52-Week High and the Conditional BAB Puzzle*, SSRN 6516598 | `[ÉTABLI, abstract]` Structure à deux dimensions : au niveau TITRE, BAB est le plus fort parmi les actions **loin sous** leur propre plus haut 52 semaines ; **au niveau AGRÉGÉ, le facteur BAB est le plus fort quand le MARCHÉ dans son ensemble est proche de ses plus hauts**. PTH domine le conditionnement par la volatilité réalisée en horse-race. | `ABSTRACT-SEULEMENT` (working paper 2026, non publié — poids de preuve faible) |
| **Greenwood, Shleifer & You (2019)**, *Bubbles for Fama*, JFE 131(1), 20-43 | `[ÉTABLI, abstract/résumés]` Une forte hausse de prix d'un portefeuille sectoriel **ne prédit PAS** de rendements futurs anormalement bas (les rendements post-run-up ≈ marché sur 2 ans), **mais prédit une probabilité de KRACH nettement accrue**. | `ABSTRACT-SEULEMENT` |

---

# 2. Transposabilité — le cœur du livrable

## 2a) Cross-sectionnel ou série temporelle ? — **Hypothèse de travail CONFIRMÉE**

`[ÉTABLI]` Répartition du corpus demandé :

| Papier | Nature | Objet trié | Décision qu'il éclaire |
|---|---|---|---|
| George & Hwang (2004) | **Cross-sectionnel** | actions US | quelles actions acheter/vendre RELATIVEMENT |
| Chen, Stivers & Sun (2024) | **Cross-sectionnel** | actions US | idem, conditionné au turnover |
| Tomtosov (2024) | **Cross-sectionnel** | actions | idem, univers restreint |
| Blau et al. (2023) | **Cross-sectionnel** | actions | idem, sur la VARIATION de distance |
| Du (2008) | **Cross-sectionnel** | 18 indices pays | quel PAYS surpondérer vs les autres |
| Huddart et al. (2009) | Cross-sectionnel / événementiel | actions | volume, pas timing |
| Driessen et al. (2012) | Cross-sectionnel / événementiel | actions & options | volatilité, pas timing |
| **Li & Yu (2012)** | **SÉRIE TEMPORELLE, MARCHÉ AGRÉGÉ** | Dow / CRSP VW | **être investi ou non — la question du desk** |
| Yuan (2015) | Série temporelle, marché agrégé | Dow / marché US | idem, mais sur un ÉVÉNEMENT d'attention |

Le verdict est net : **hors Li & Yu (2012) et Yuan (2015), rien de ce corpus ne porte sur la décision du desk.** Un tri cross-sectionnel n'a aucun contenu directionnel : la stratégie de George-Hwang est **auto-financée**, son rendement de 0.45 %/mois est un ÉCART entre deux paniers d'actions ; elle ne dit strictement rien sur l'opportunité d'être long d'un indice. Du (2008) est le piège le plus proche : il porte sur des INDICES, ce qui donne l'illusion de transposabilité, mais il classe 18 indices les uns par rapport aux autres — le desk n'a que deux indices et une décision binaire d'exposition, pas un classement.

Sur Li & Yu, précisément :

`[ÉTABLI]` **Ce qu'il trouve :** au niveau du marché agrégé, `x52` (proximité au plus haut 52 semaines) prédit POSITIVEMENT et `xmax` (proximité au plus haut HISTORIQUE) prédit NÉGATIVEMENT, à des horizons allant du **jour à l'année**, avec des t de Newey-West de 2.04 à 3.83 (`x52`) et −3.42 à −5.18 (`xmax`) en spécification avec contrôles macro.

`[ÉTABLI]` **À quel R² :** 0.01 (jour), 0.02 (semaine), 0.05 (mois), 0.13 (trimestre), 0.22 (6 mois), 0.32 (an) en chevauchant ; 0.46 à l'année en non chevauchant. **Tous in-sample.**

`[ÉTABLI]` **Pourquoi ça ne transpose quand même pas à l'état du desk :** les coefficients de `x52` et `xmax` sont opposés et de magnitude quasi identique à chaque horizon. Le desk est proche des DEUX plus hauts simultanément (NQ et DAX proches de leurs ATH ⇒ `x52 ≈ xmax ≈ 1` ⇒ `I_t = 1`). Dans cette configuration les deux termes s'annulent numériquement. Le signal de Li-Yu est **un écartement entre deux ancres** ; il est maximal quand le marché est près de son plus haut annuel **mais très loin sous son plus haut historique** — c'est-à-dire dans un état de reprise post-krach, l'exact OPPOSÉ de l'état actuel. Les auteurs l'écrivent noir sur blanc.

`[ÉTABLI]` Ce qui RESTE identifiable dans l'état du desk, ce sont les deux indicatrices : `I_t` (régime « une seule ancre » = ATH) au coefficient **positif** (t 1.56 au jour, 1.63 au mois, 2.14 à 6 mois avec contrôles macro ; plus fort encore sans contrôles : t 2.52 / 2.78 / 3.26) et `D_t` (**jour de nouveau record**) au coefficient **négatif au jour** : −0.08 % avec t −2.87 (chevauchant) et −2.93 (non chevauchant), redevenant positif aux horizons longs.

`[EXTRAPOLATION]` Traduit pour le desk : la littérature agrégée, prise au pied de la lettre, dit que **le régime ATH lui-même est plutôt BÉNIN voire favorable**, et que la seule pénalité identifiée est un effet d'ÉVÉNEMENT d'une journée après un nouveau record. Ce n'est **pas** un argument pour suspendre l'exposition ; ce serait au mieux un argument pour ne pas la porter le lendemain d'un record — et le §2b détruit même cette lecture.

## 2b) L'horizon — **la réponse est NON, en toutes lettres**

**Il n'existe, à ma connaissance après cette recherche, AUCUN résultat publié sur l'effet de la proximité du plus haut (52 semaines ou historique) à horizon INTRAJOURNALIER ou OVERNIGHT.** `[ÉTABLI par absence — voir la méthode de recherche ci-dessous]`

Les horizons effectivement couverts par le corpus :

| Horizon | Couverture | Source |
|---|---|---|
| 1–12 mois (cross-section actions) | dense | George-Hwang, Chen-Stivers-Sun, Tomtosov, Blau et al., Du |
| 1 mois – 1 an (marché agrégé) | Li & Yu | R² 0.05 → 0.46, in-sample |
| **1 jour (marché agrégé, close-to-close)** | **Li & Yu Table 3/4 + Yuan 2015** | R² **0.01** ; `D_t` = −0.08 %, t −2.87 ; Yuan −19 bps |
| **intraday (heures de séance)** | **RIEN sur l'ancre-plus-haut** | — |
| **overnight (clôture → ouverture)** | **RIEN sur l'ancre-plus-haut** | — |

Méthode : recherches ciblées combinant « 52-week high » / « historical high » / « anchoring » avec « intraday », « overnight », « high-frequency », « daily horizon » ; aucune n'a fait remonter un papier étudiant la distance au plus haut comme conditionneur d'un rendement overnight ou intraday. La littérature overnight/intraday existante (Lou-Polk-Skouras, Boyarchenko et al., Berkman et al., Bogousslavsky, Cliff-Cooper-Gulen) ne mentionne **jamais** la proximité au plus haut comme variable de conditionnement — j'ai grepé le texte intégral de Lou-Polk-Skouras (2019) : **zéro occurrence** de « 52-week », « all-time » ou « record high ».

**Conséquence pour le desk (importance de premier ordre) :**
- Le desk détient **~15 heures** ; le résultat publié le plus court concernant l'ancre est un rendement **quotidien close-to-close** couvrant à la fois une séance US complète ET une nuit.
- `[EXTRAPOLATION, mais mécaniquement fondée]` Le mécanisme publié de l'effet quotidien négatif (Yuan 2015) est la **vente des particuliers déclenchée par l'attention médiatique au record** ; Berkman et al. (2012) `[ÉTABLI, abstract]` montrent que l'activité des particuliers attirés par l'attention se matérialise par un **prix d'OUVERTURE haut suivi d'un reversal PENDANT LA SÉANCE**. Les deux mécanismes placent l'effet post-record dans la **jambe INTRADAY**, pas dans la jambe overnight du desk. Si cela est vrai, transposer un chiffre close-to-close à une position overnight n'est pas seulement imprécis, c'est **potentiellement du signe inverse**. **C'est mon extrapolation, pas un résultat publié**, et c'est exactement le genre de test que l'agent empirique du dossier peut trancher sur les données du repo (décomposer le rendement post-nouveau-record en jambes overnight et intraday sur NQ/DAX).
- Rappel de discipline maison : L52 (une décomposition intraday/overnight n'est pas définie sans dire de quel jour et de quelle horloge on parle) et L56 (un drift de session est ancré à l'horloge de l'ÉCHANGE, pas UTC). Aucun des papiers ci-dessus ne fournit la granularité horaire nécessaire pour l'exercice du desk.

## 2c) Le mécanisme — sous-réaction (continuation) ou sur-réaction (réversion) ? Arbitrage honnête

**Il y a un désaccord réel dans la littérature, et je ne vais pas le lisser.** Voici les deux camps et ce qui les sépare.

**Camp CONTINUATION (l'ATH est bénin) :** George-Hwang (2004), Tomtosov (2024), Chen-Stivers-Sun (2024, dans la cellule turnover-haut × PTH-haut), et Li-Yu sur la composante `x52` et l'indicatrice `I_t`.
**Camp RÉVERSION (l'ATH est dangereux) :** Blau et al. (2023), Li-Yu sur la composante `xmax`, Yuan (2015) sur l'événement record, Du (2008) pour le renversement à long terme sur indices.

Les quatre lignes de faille qui expliquent le désaccord — c'est ici que se joue l'arbitrage :

1. **La variable n'est pas la même.** C'est la source de conflit n°1 et elle est décisive. Li & Yu apportent la preuve la plus propre : **dans une seule et même régression**, `x52` (ancre 52 semaines) est POSITIF et `xmax` (ancre historique) est NÉGATIF. Ce ne sont pas deux résultats contradictoires, ce sont **deux variables différentes**. `[ÉTABLI]` Blau et al. utilisent une TROISIÈME variable encore (la VARIATION mensuelle de la distance, pas son niveau) — leur « anchor reversion » n'est donc pas l'inverse de George-Hwang, c'est autre chose. **Conclusion : la moitié apparente du désaccord n'en est pas un ; c'est un défaut de nomenclature.**

2. **L'horizon.** `[ÉTABLI]` George-Hwang : formation 6 mois, détention 6 mois. Chen-Stivers-Sun : mois consécutifs (horizon du short-term reversal). Blau et al. : mois suivant. Du (2008) : momentum à moyen terme MAIS renversement à long terme. Le motif classique momentum-à-moyen-terme / réversion-à-long-terme est présent, et il n'a aucune raison de dire quoi que ce soit à 15 heures.

3. **L'interaction avec le turnover (Chen-Stivers-Sun).** `[ÉTABLI, abstract]` Le signe du PTH **n'est pas stable seul** : le reversal décroît avec le PTH et bascule en momentum uniquement quand le turnover est AUSSI élevé. C'est-à-dire que même dans son univers d'origine, la variable a besoin d'un second conditionneur pour avoir un signe déterminé. `[EXTRAPOLATION]` Une variable dont le signe dépend d'une interaction dans l'univers où elle a été découverte est une très mauvaise candidate à l'export vers un autre univers.

4. **L'univers.** Actions individuelles partout, sauf Li-Yu (indice agrégé US) et Du (indices pays). Aucun test sur un contrat à terme d'indice.

**Mon arbitrage `[EXTRAPOLATION]` :** la littérature ne soutient ni « l'ATH est dangereux » ni « l'ATH est bénin » **pour la décision du desk**. Ce qu'elle soutient, c'est : (i) sur ACTIONS, à horizon MENSUEL, la proximité au plus haut 52 semaines est plutôt un signal de CONTINUATION relative ; (ii) sur le MARCHÉ AGRÉGÉ, la proximité au plus haut HISTORIQUE est le seul terme robustement négatif du corpus, mais il est identifié **par écart** avec l'ancre 52 semaines — écart quasi nul dans l'état du desk ; (iii) le seul effet négatif directement attaché à un ATH d'indice est un effet d'**événement d'attention** d'une journée (−8 à −19 bps), dont le mécanisme publié le loge dans la séance et non dans la nuit. Aucune de ces trois briques n'autorise un verdict directionnel sur une position overnight.

## 2d) Indice vs action — les mécanismes comportementaux survivent-ils à l'agrégation ?

`[ÉTABLI]` Les mécanismes invoqués au niveau du titre sont : ancrage/adjustment insuffisant (Kahneman-Slovic-Tversky via George-Hwang), effet de disposition et capital-gains overhang (Grinblatt-Han via George-Hwang), attention des particuliers (Huddart et al., Berkman et al.), ambiguïté de valorisation (Huddart et al. : l'effet volume est **plus fort** pour les petites firmes, les titres à fort intérêt particulier et à valorisation ambiguë).

`[EXTRAPOLATION]` Chacun de ces conditionneurs pousse dans le sens d'un effet **PLUS FAIBLE sur un indice** : un indice de grandes capitalisations n'est ni petit, ni ambigu à valoriser, ni dominé par les particuliers. Huddart et al. établissent la pente ; l'indice se situe au mauvais bout de cette pente.

`[ÉTABLI]` Mais deux résultats vont dans l'autre sens et je dois les rapporter :
- Li & Yu montrent que l'effet marché-agrégé est **beaucoup plus fort mesuré sur le DOW que sur la capi NYSE/AMEX** (Table 5 : t de `xN52` tombe à 1.46 au jour, R² 0.008), et l'attribuent explicitement à la **visibilité médiatique** du Dow. Autrement dit, l'ancrage peut opérer au niveau d'un INDICE précisément parce que l'indice est l'objet dont la presse parle. `[SUGGÉRÉ par les auteurs]`
- Yuan (2015) `[ÉTABLI, abstract]` documente un effet d'attention marché-large déclenché par les **records du Dow**, avec des flux vendeurs mesurés chez les particuliers ET les fonds. C'est de l'ancrage/attention **au niveau indice**, avec preuve de flux.

`[ÉTABLI]` Sur les ETF/futures d'indice spécifiquement : je n'ai trouvé **aucune** étude académique de l'effet 52wh/ATH sur des ETF ou des contrats à terme d'indice actions. Il existe un travail sur les **futures de matières premières** (Journal of Behavioral Finance 2024, « How is Trading Behavior in Commodity Futures Affected by the 52-Week High and Low? » — `MÉTADONNÉES-SEULEMENT`, non lu) mais rien sur les indices actions. Le NQ100 et le DAX40 en CFD n'ont, à ma connaissance, **aucune couverture académique sur cette question**.

`[EXTRAPOLATION]` Verdict §2d : le canal « attention médiatique sur l'indice-vedette » est le SEUL des mécanismes documentés qui survit plausiblement à l'agrégation, et il est de nature **événementielle** (le jour du record fait la une), pas de nature **état** (« être près de l'ATH »). Un overlay qui coupe l'exposition tant que l'indice reste dans une zone haute ne correspond à aucun mécanisme publié.

---

# 3. Volatilité et asymétrie conditionnelles à la proximité du plus haut

## 3.1 Ce que dit la littérature spécifique aux plus hauts

`[ÉTABLI, abstract]` **Driessen, Lin & Van Hemert (2012), Review of Finance** — le papier central de cette section :
> « We find that IVs and stock betas **decrease when approaching a high or low**, and that **volatilities increase after breakthroughs**. The effects are economically large and significant. »

`[ÉTABLI, sources secondaires — à re-vérifier sur texte intégral]` Magnitudes rapportées : variance idiosyncratique **−32 %** à l'approche du plus haut 52 semaines ; **+46 %** le lendemain d'un **franchissement** du plus haut (et +111 % pour un franchissement du plus bas) ; volatilité implicite −1 point sur une moyenne d'échantillon de 43.

`[ÉTABLI, abstract]` **Huddart, Lang & Yetman (2009)** : le VOLUME explose au franchissement des bornes du range passé, puis retombe graduellement. Le volume n'est pas la volatilité, mais les deux co-bougent.

`[ÉTABLI, abstract]` **Chen, Chen, Tu, Wang & Wang (2026), JEDC, DOI 10.1016/j.jedc.2026.105286, « Proximity to the 52-week high and the risk-return trade-off »** : la relation risque-rendement est **POSITIVE parmi les titres à H52 élevé** et négative parmi les titres à H52 faible — motif prédit par la théorie des perspectives. `ABSTRACT-SEULEMENT`, abstract officiel non récupéré (403), résumé issu des extraits de recherche — **à re-vérifier**.

## 3.2 L'intuition standard « près du plus haut = basse volatilité réalisée » : VÉRIFIÉE, MAIS AVEC UNE EXCEPTION QUI COMPTE

`[ÉTABLI]` L'intuition est **confirmée pour le sous-état « APPROCHE »** (le prix se rapproche du plus haut sans le franchir) : Driessen et al. mesurent une baisse des IV, des bêtas et de la variance idiosyncratique. Elle est **INFIRMÉE pour le sous-état « FRANCHISSEMENT »** (nouveau plus haut), où la volatilité **augmente** nettement le lendemain.

`[ÉTABLI]` Le socle général va dans le même sens que l'intuition : la **volatilité asymétrique** — Black (1976), Christie (1982) pour l'effet de levier ; Bekaert & Wu (2000, RFS) qui **rejettent** le modèle de pur levier et concluent à un **« down market effect »** dominé par la rétroaction de volatilité plutôt que par la structure du capital. Un marché qui monte est un marché à volatilité conditionnelle décroissante ; un marché près de son plus haut est, par construction, un marché qui a monté.

`[ÉTABLI, abstract]` **Contre-poids indispensable — Greenwood, Shleifer & You (2019), JFE** : une forte hausse de prix ne prédit **PAS** de rendements moyens futurs bas (post-run-up ≈ marché sur 2 ans) **MAIS prédit une probabilité de KRACH accrue**. Traduction : basse volatilité **réalisée** et queue gauche **épaissie** peuvent coexister. C'est un avertissement direct contre l'usage de la volatilité réalisée comme mesure suffisante du risque dans cet état.

`[EXTRAPOLATION]` Ce que je n'ai PAS trouvé et qu'il faut mesurer soi-même : aucune étude ne régresse la **volatilité réalisée d'un INDICE** sur sa **distance à son ATH**, ni ne décompose cette volatilité entre séance et nuit. Toute la matière ci-dessus est du niveau TITRE (Driessen et al., Huddart et al.) ou du niveau agrégé mais sur une variable différente (rendement passé, pas distance à l'ATH). **C'est une mesure à faire dans le repo, pas à importer.**

## 3.3 Implication L54 — formulée explicitement, comme demandé

Rappel de la constitution (L54, gravée 2026-07-30) :
> « La condition liante d'un overlay de régime n'est PAS le MaxDD : c'est que le régime prédisant la VARIANCE prédise la MOYENNE dans le MÊME SENS. […] Un overlay de régime n'aide qu'un book dont les régimes de haute vol sont AUSSI ses régimes de bas rendement. »

Appliquée à « distance au plus haut historique » comme régime candidat, avec ce que la littérature établit :

| Sous-état | Variance prédite | Moyenne prédite | Verdict L54 |
|---|---|---|---|
| **Approche de l'ATH** (le desk, en régime calme) | **BASSE** (Driessen et al. : IV, bêta et variance idio en baisse ; Bekaert-Wu : marché haussier = vol conditionnelle basse) | **NEUTRE à POSITIVE** (Li-Yu : `x52` et `xmax` s'annulent, `I_t` positif ; Greenwood et al. : rendements post-run-up ≈ marché ; littérature praticienne : pas de désavantage à investir aux plus hauts) | **CONDITION VIOLÉE.** Variance basse + moyenne neutre/positive = l'exact opposé de ce qu'un overlay peut exploiter. Couper ici retranche des jours **peu chers en risque et pas pires en rendement** — c'est la signature du dossier `regime_overlay_ftmo` déjà clos en échec. |
| **Franchissement / nouveau record** | **HAUTE** (Driessen et al. : +46 % de variance idio le lendemain ; Huddart et al. : volume en pic) | **LÉGÈREMENT NÉGATIVE à 1 jour** (Li-Yu `D_t` = −0.08 %, t −2.87 ; Yuan −19 bps), positive aux horizons longs | **CONDITION POTENTIELLEMENT REMPLIE — mais sur un sous-état ÉVÉNEMENTIEL d'un jour, mesuré sur ACTIONS pour la variance et sur le DOW close-to-close pour la moyenne, et dont le mécanisme publié loge l'effet moyen dans la SÉANCE et non dans la NUIT.** Fenêtre étroite, preuve indirecte, univers non concordant. |

**Conclusion §3, `[EXTRAPOLATION]` fondée sur `[ÉTABLI]` :** dans sa formulation naturelle — « le NQ et le DAX sont proches de leurs plus hauts, donc suspendons » — le dossier se **referme sur L54**. La littérature ne décrit pas cet état comme un état de haute variance, et ne le décrit pas comme un état de rendement moyen dégradé. La seule reformulation qui reste ouverte est **événementielle et à queue** : « le desk porte-t-il des nuits qui SUIVENT un jour de nouveau record, et ces nuits-là ont-elles une queue gauche plus lourde ? » — question de TAIL, sur un sous-échantillon étroit, à laquelle la littérature ne répond pas et que seul un test empirique sur les données du repo peut trancher.

---

# 4. La prime overnight elle-même

## 4.1 Le fait de base

`[ÉTABLI, LU-INTÉGRAL]` **Lou, Polk & Skouras (2019), JFE 134(1), 192-213.** Échantillon CRSP-Compustat US 1993–2013 (contraint par TAQ). Décomposition du rendement du marché :
> l'indice CRSP value-weighted a un **excès de rendement intraday moyen de 0.38 %/mois** et un **rendement overnight moyen de 0.55 %/mois**.

Les auteurs relativisent immédiatement : le marché US est ouvert ~27 % des 24 h et capte ~40 % de la prime, donc le partage est « à peu près » proportionnel au temps — **ils rejettent explicitement la thèse « la prime de risque est essentiellement overnight »** dans sa version large.

**MAIS — et c'est le point qui concerne le desk** `[ÉTABLI]` :
> « much of that research bases their conclusions on narrow market proxies like an ETF tracking the Dow 30. […] The figure shows that **for the largest stocks, essentially all of their risk premium is earned overnight**. »

`[EXTRAPOLATION]` Le NQ100 et le DAX40 sont des indices de très grandes capitalisations — le segment où Lou-Polk-Skouras trouvent que **toute** la prime est overnight. C'est le soutien le plus solide, dans la littérature académique, à l'existence même de la sleeve du desk. Ce n'est pas une mesure sur NQ ni sur DAX.

`[ÉTABLI, abstract]` **Berkman, Koch, Tuttle & Zhang (2012), JFQA 47(4), 715-741** : forte tendance à des rendements positifs overnight **suivis de reversals pendant la séance**, portée par un prix d'ouverture élevé relativement aux prix intraday ; concentrée sur les titres qui viennent d'attirer l'attention des PARTICULIERS, plus marquée pour les titres difficiles à valoriser et coûteux à arbitrer, et plus forte en période de fort sentiment retail. **Qui paie :** les particuliers qui achètent près de l'ouverture — les coûts implicites dépassent souvent le demi-spread effectif.

`[ÉTABLI, abstract]` **Cliff, Cooper & Gulen (2008)** documentent le même clivage nuit/jour (référence historique, `MÉTADONNÉES/ABSTRACT` seulement).

## 4.2 Le mécanisme, et où exactement la prime s'accumule

`[ÉTABLI, LU-PARTIEL — NY Fed Staff Report 917, révisé août 2022, publié RFS 36(9), 2023]` **Boyarchenko, Larsen & Whelan, « The Overnight Drift ».** Échantillon : futures S&P 500 (ES, avec raccord SP), quotes 24 h, **5 janvier 1998 – 31 décembre 2020 (23 ans)**, rendements calculés sur les mid des meilleures limites.

- `[ÉTABLI]` Le rendement se concentre dans la fenêtre **2:00–3:00 ET** (ouverture des marchés actions européens) : **3.7 % annualisé, soit 1.48 bps/jour**.
- `[ÉTABLI]` Robustesse anti-data-mining sérieuse : bootstrap sur toutes les heures (l'intervalle 2.5 % de la fenêtre est au-dessus de l'intervalle 97.5 % groupé, pour les points comme pour les t) ; valeurs critiques ajustées Bonferroni et Benjamini-Yekutieli ⇒ **2:00-3:00 est la SEULE heure qui reste significative en échantillon complet et en sous-échantillons** ; positive **20 années sur 23**, significative dans **17** ; significative **tous les jours de la semaine** et **9 mois sur 12**.
- `[ÉTABLI]` Mécanisme : résolution overnight des déséquilibres d'ordres de la clôture US précédente ; cadre Grossman-Miller de gestion d'inventaire par des teneurs de marché averses au risque. Les annonces macro, de politique monétaire et de résultats **n'expliquent pas** le drift ⇒ l'information asymétrique seule est écartée.
- `[ÉTABLI]` **Asymétrie, directement pertinente :** « market **selloffs** generate robust positive overnight reversals, while **reversals following market RALLIES are much more modest** ». Attribuée à une capacité de portage du risque des dealers variable dans le temps (contrainte de type VaR ⇒ aversion effective accrue lors des selloffs).

`[EXTRAPOLATION]` Conséquence pour le desk : un indice proche de son ATH est, par construction, un indice qui vient de RALLIER. Si l'on prend l'asymétrie de Boyarchenko et al. au sérieux, **la prime overnight est structurellement PLUS FAIBLE dans l'état actuel du desk** — non pas parce que l'ATH serait dangereux, mais parce que le carburant de la prime (déséquilibre vendeur de clôture) est absent. **C'est le seul lien mécanique publié que j'ai trouvé entre « le marché a monté » et « la prime overnight est plus faible ». Il ne passe PAS par l'ancre-plus-haut, il passe par le déséquilibre d'ordres de clôture — variable QUOTIDIENNE et observable.** Si le desk veut un conditionneur, celui-là a une fondation mécanique que la distance à l'ATH n'a pas.

## 4.3 La prime a-t-elle décayé ? — vérification de l'affirmation du repo

**Affirmation du repo (MEMORY.md) :** « Overnight drift ES/NQ mort depuis 2021, tué par ses auteurs [par la publication] ».

**Verdict : la MORT est CONFIRMÉE ; la CAUSE attribuée est CONTREDITE par les auteurs eux-mêmes.**

`[ÉTABLI]` Source : **Boyarchenko, Larsen & Whelan, « The Disappearing Overnight Drift »**, Liberty Street Economics (Fed de New York), juillet 2026, + SSRN 7035838 (1er juillet 2026). Contenu vérifié en lisant le billet Liberty Street :
- la fenêtre 2:00–3:00 ET valait **≈ 3.7 %/an sur 1998–2020**, soit ~**60 %** du rendement close-to-close annualisé de 5.9 % du contrat ;
- sur **janvier–décembre 2025**, cette même fenêtre a rendu « close to zero » ; le motif s'est éteint après 2021 ;
- **le motif s'éteint de façon cohérente sur E-mini Nasdaq-100 et E-mini Dow Jones** — donc **NQ est explicitement concerné** ;
- les auteurs attribuent la disparition à la **compression de la dispersion des déséquilibres d'ordres de clôture** : écart-type du signed volume relatif de fin de séance passé de **6.5 % à 2.9 % (−55 %)**, avec l'explication « les ordres à cours limité postés à la clôture sont devenus plus petits, cohérent avec des fournisseurs de liquidité algorithmiques découpant le flux plus finement » ;
- **ils écartent l'effet de publication comme cause principale**, et notent que le VIX et les mesures de liquidité overnight sont **restés essentiellement inchangés**, ce qui isole le déséquilibre d'ordres ;
- anecdote de marché citée : les ETF overnight de NightShares (NSPY, NIWM), lancés en juin 2022 sur ce mécanisme, ont fermé quatorze mois plus tard.

`[ÉTABLI]` Aucun t-stat n'est fourni dans le billet ; le papier SSRN n'a pas pu être ouvert (403 SSRN).

`[EXTRAPOLATION]` Corrections à apporter à la mémoire du projet : (1) dire « tué par ses auteurs / par la publication » est **inexact** — les auteurs testent trois canaux (dispersion des déséquilibres, niveau de variance, capacité de portage des dealers) et retiennent le premier, pas la publication ; (2) le fait porte sur la **fenêtre 2:00-3:00 ET**, pas sur « la nuit » en général — un book qui détient toute la nuit ne détient pas le même objet que celui que les auteurs mesurent ; (3) la nuance a une conséquence opératoire : si la cause est microstructurelle (découpage algorithmique du flux de clôture) et non informationnelle, **rien ne garantit qu'elle se réverse**, et rien ne garantit non plus qu'elle s'applique au DAX, dont le cycle de clôture/ouverture est différent.

## 4.4 Ce que la littérature ne couvre pas pour ce desk

`[ÉTABLI par absence]`
- **Aucune étude académique du rendement overnight du DAX40** trouvée. Tout ce qui remonte sur « DAX overnight bias » est de la littérature de courtier/blog, sans échantillon, sans t, sans coûts. À ne PAS citer.
- **Aucune étude conditionnant la prime overnight d'un indice sur sa distance au plus haut.**
- **Aucune étude de la prime overnight sur véhicule CFD** (donc rien sur le swap overnight, qui est le tueur documenté maison — L36, L28, L30 : la facture de portage agrégée sur FTMO consomme l'essentiel de toute prime tenue).
- Effets **jour-de-la-semaine** : Boyarchenko et al. établissent que le drift 2:00-3:00 était significatif **tous les jours de la semaine** — donc rien de publié ne singularise lundi/mardi. Le choix lundi+mardi du desk n'a **aucun appui dans la littérature**, ni pour ni contre.

---

# 5. PRIOR DIRECTIONNEL (pas une recommandation de trading)

**Formulation.** Ma lecture de la littérature ne fournit **aucune base pour conditionner l'exposition overnight sur indice à la distance au plus haut historique.** Le prior que je transmets est :

> **« La proximité du plus haut historique n'est pas, à horizon overnight, un prédicteur identifié du rendement moyen ni de la volatilité réalisée d'un indice. »**
> — degré de confiance : **ÉLEVÉ sur l'absence de preuve** (aucun résultat publié à cet horizon : c'est un fait vérifiable), **MOYEN sur l'absence d'effet** (l'absence de littérature n'est pas une preuve de nullité, elle est une preuve d'ignorance).

**Prior secondaire, plus faible mais mieux fondé mécaniquement :**
> **« Si un affaiblissement de la prime overnight existe dans l'état actuel, il passe plus vraisemblablement par le déséquilibre d'ordres de clôture (Boyarchenko et al. : les reversals après RALLIES sont beaucoup plus modestes) et par l'extinction post-2021 du drift 2:00-3:00, que par l'ancre-plus-haut. »**
> — degré de confiance : **MOYEN**. Les deux briques sont `[ÉTABLI]`, le pont entre « près de l'ATH » et « déséquilibre de clôture faible » est `[EXTRAPOLATION]`.

**Domaine de validité de ces priors :** indices actions larges, marchés développés, données post-1993 pour la partie overnight, post-1963 pour la partie ancrage. **Hors domaine :** tout ce qui touche au véhicule CFD (spread, swap overnight, barrière FTMO), à la granularité 15 h, aux jours lundi/mardi, au DAX, et à la queue gauche à horizon d'une nuit. Sur ces cinq points la littérature est **muette** et le repo devra trancher par la mesure.

**Ce que je transmettrais aux trois agents parallèles (formulé comme hypothèses testables, pas comme conclusions) :**
1. **Décomposer overnight vs intraday** le rendement des jours qui suivent un nouveau record sur NQ et DAX. Prédiction de mon extrapolation §2b : l'effet négatif publié (−8 à −19 bps close-to-close) devrait se loger dans la SÉANCE, pas dans la NUIT. Si c'est vrai, le dossier se referme définitivement.
2. **Séparer les deux sous-états** « approche » (près du plus haut sans le franchir) et « franchissement » (nouveau record). Driessen et al. prédisent des signes de variance OPPOSÉS. Les confondre sous « près de l'ATH » est l'erreur de conception la plus probable de ce dossier.
3. **Mesurer la queue, pas la moyenne.** Greenwood-Shleifer-You est le seul résultat qui autorise à s'inquiéter, et il porte sur la probabilité de krach à hausse forte, pas sur la moyenne. Avec un plancher à 9 000 € et un budget quotidien de 500 €, c'est la seule dimension où la littérature laisse une porte entrouverte — et elle ne l'a jamais mesurée à horizon d'une nuit.
4. **Piège L58 à anticiper :** la distance à l'ATH est un état **hautement autocorrélé** (Li-Yu : AC(1) de `xmax` = 0.93 au pas mensuel). Tout test conditionnel sur cette variable créera des blocs de jours contigus. Bootstrap iid interdit ; placebo à autocorrélation appariée obligatoire ; et vérifier que la moyenne du pool placebo égale l'espérance INCONDITIONNELLE de la forme de trade.

---

# Bibliographie avec statut de vérification

**Légende :** `LU-INTÉGRAL` = texte complet lu · `LU-PARTIEL` = texte complet obtenu, sections ciblées lues · `ABSTRACT-SEULEMENT` = seul l'abstract officiel a pu être obtenu · `SECONDAIRE` = chiffres issus de résumés tiers, non confirmés au texte · `MÉTADONNÉES-SEULEMENT` = existence/auteurs/revue confirmés (Crossref), contenu non lu · `NON VÉRIFIÉ` = existence non confirmée.

### Corpus « proximité du plus haut »

1. **George, T. J., & Hwang, C.-Y. (2004).** The 52-Week High and Momentum Investing. *Journal of Finance*, 59(5), 2145-2176. DOI 10.1111/j.1540-6261.2004.00695.x — PDF auteur : https://www.bauer.uh.edu/tgeorge/papers/gh4-paper.pdf — **`LU-INTÉGRAL`**

2. **Li, J., & Yu, J. (2012).** Investor attention, psychological anchors, and stock return predictability. *Journal of Financial Economics*, 104(2), 401-419. https://www.sciencedirect.com/science/article/abs/pii/S0304405X11002121 — **`ABSTRACT-SEULEMENT` pour la version publiée.**
   Version working paper lue : **Li, J., & Yu, J. (2009).** *Psychological Anchors, Underreaction, Overreaction, and Asset Prices.* Carlson School of Management, 26 oct. 2009. http://assets.csom.umn.edu/assets/153169.pdf — **`LU-INTÉGRAL`.** ⚠ Le WP se présente lui-même comme « a very preliminary version and not for circulation » ; **tous les chiffres cités dans cette revue proviennent de ce WP, pas de la version JFE.** Le robustesse G7 annoncée dans l'abstract publié est **`NON VÉRIFIÉE`** (absente du WP).

3. **Chen, C., Stivers, C., & Sun, L. (2024).** Short-term momentum and reversals, turnover, and a stock's price-to-52-week-high ratio. *Journal of Empirical Finance*, 79, 101556. DOI 10.1016/j.jempfin.2024.101556 — **`ABSTRACT-SEULEMENT`** (ScienceDirect 403 malgré statut open-access hybride CC-BY-NC-ND ; période d'échantillon, magnitudes et t-stats **non vérifiés**).

4. **Tomtosov, A. (2024).** Momentum on historical high. *Finance Research Letters*, nov. 2024. DOI 10.1016/j.frl.2024.106216 — **`SECONDAIRE`** (métadonnées confirmées par Crossref ; abstract officiel **non obtenu** — Semantic Scholar renvoie `abstract: null`, ScienceDirect 403. Les chiffres 45 %/70 %, 6.2 % vs 1.3 % proviennent d'extraits de recherche web et sont **à re-vérifier avant tout usage**).

5. **Blau, B. M., Griffith, T. G., Whitby, R. J., & Woodward, D. (2023).** Anchor Reversion: The Case of the 52-Week High and Asset Prices. *Journal of Behavioral Finance*, 26(1), 82-94. DOI 10.1080/15427560.2023.2244103 — **`ABSTRACT-SEULEMENT`** (abstract officiel obtenu intégralement via Semantic Scholar ; texte intégral 403).

6. **Du, D. (2008).** The 52-week high and momentum investing in international stock indexes. *Quarterly Review of Economics and Finance*, 48(1), 61-77. https://www.sciencedirect.com/science/article/abs/pii/S106297690700021X — **`SECONDAIRE`** (RePEc indique « no abstract available » ; univers 18 pays développés, déc. 1969 – juil. 2004, et le renversement à long terme proviennent de citations tierces — **à re-vérifier**).

7. **Huddart, S., Lang, M., & Yetman, M. H. (2009).** Volume and Price Patterns Around a Stock's 52-Week Highs and Lows: Theory and Evidence. *Management Science*, 55(1), 16-31. DOI 10.1287/mnsc.1080.0920 — **`ABSTRACT-SEULEMENT`**

8. **Driessen, J., Lin, T.-C., & Van Hemert, O. (2012).** How the 52-Week High and Low Affect Option-Implied Volatilities and Stock Return Moments. *Review of Finance*, 16(1). DOI 10.1093/rof/rfr026 (version SSRN 2011 : DOI 10.2139/ssrn.1572269) — **`ABSTRACT-SEULEMENT`** ; les magnitudes (−32 %, +46 %, +111 %, −1 pt d'IV) sont **`SECONDAIRE`**, issues de résumés tiers.

9. **Chen, X., Chen, Z., Tu, J., Wang, Liyao, & Wang, Luying (2026).** Proximity to the 52-week high and the risk-return trade-off. *Journal of Economic Dynamics and Control*, avril 2026. DOI 10.1016/j.jedc.2026.105286 — **`MÉTADONNÉES-SEULEMENT`** (existence et auteurs confirmés par Crossref ; le résultat « relation risque-rendement positive parmi les H52 élevés » est **`SECONDAIRE`**).

10. **Sun, L. (2026).** Beyond Volatility: The 52-Week High and the Conditional Betting-Against-Beta Puzzle. SSRN 6516598, DOI 10.2139/ssrn.6516598 — **`ABSTRACT-SEULEMENT`**. ⚠ Working paper non publié, non revu par les pairs : poids de preuve faible.

11. **Della Vedova, J., Grant, A., & Westerholm, P. J. (2023).** Investor Behavior at the 52-Week High. *Journal of Financial and Quantitative Analysis*, 58(7), 2852-2889. DOI 10.1017/s002210902200148x — **`MÉTADONNÉES-SEULEMENT`** (non lu ; cité uniquement pour signaler son existence à un futur approfondissement du mécanisme).

12. **« How is Trading Behavior in Commodity Futures Affected by the 52-Week High and Low? »** *Journal of Behavioral Finance* (2024). DOI 10.1080/15427560.2024.2335521 — **`MÉTADONNÉES-SEULEMENT`**, auteurs non relevés. Seule occurrence trouvée de l'effet 52wh sur des FUTURES ; matières premières, pas indices actions.

### Ancrage / attention (mécanisme)

13. **Yuan, Y. (2015).** Market-wide attention, trading, and stock returns. *Journal of Financial Economics*, 116(3). https://www.sciencedirect.com/science/article/abs/pii/S0304405X15000410 — **`ABSTRACT-SEULEMENT`** (PDF miroir inaccessible : erreur de certificat TLS). Le chiffre de **−19 bps** est issu de l'abstract/extraits ; il concorde avec le coefficient `D_t` = −0.08 % lu au texte dans Li-Yu (2009).

14. **Baker, M., Pan, X., & Wurgler, J. (2012).** The effect of reference point prices on mergers and acquisitions. *Journal of Financial Economics*, 106(1), 49-71. PDF : https://pages.stern.nyu.edu/~jwurgler/papers/wurgler_baker_pan.pdf — **`ABSTRACT-SEULEMENT`**.
   ⚠ **Note sur « Baker & Xuan » demandé dans la mission :** la référence d'ancrage sur le plus haut 52 semaines est **Baker, Pan & Wurgler**, pas Baker & Xuan. **Baker, M., & Xuan, Y., « Under New Management: Equity Issuance and the Attribution of Past Returns » (Journal of Financial Economics)** existe et porte sur un prix de référence différent (le prix à l'arrivée du dirigeant) — **`NON VÉRIFIÉ`** (métadonnées exactes non confirmées ; **ne pas citer en l'état**).

15. **Grinblatt, M., & Han, B.** — effet de disposition / capital gains overhang comme ancre alternative. Discuté et testé dans George-Hwang (2004) `LU-INTÉGRAL`, où il est dominé par la mesure 52wh. Référence primaire **`NON VÉRIFIÉE`** ici.

### Prime overnight / intraday

16. **Lou, D., Polk, C., & Skouras, S. (2019).** A tug of war: Overnight versus intraday expected returns. *Journal of Financial Economics*, 134(1), 192-213. PDF auteur : https://personal.lse.ac.uk/polk/research/TugOfWar.pdf — **`LU-PARTIEL`** (texte complet obtenu ; abstract, §1, §4.2.1 « The equity premium » lus au texte). Vérifié par grep : **zéro occurrence** de « 52-week », « all-time » ou « record high » dans le papier.

17. **Boyarchenko, N., Larsen, L. C., & Whelan, P. (2023).** The Overnight Drift. *Review of Financial Studies*, 36(9), 3502-3547. Version working paper lue : **Federal Reserve Bank of New York Staff Report n° 917**, févr. 2020, révisé août 2022. https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf — **`LU-PARTIEL`** (PDF téléchargé et converti ; abstract, introduction, sections d'asymétrie et de sous-échantillons lues au texte).

18. **Boyarchenko, N., Larsen, L. C., & Whelan, P. (2026).** The Disappearing Overnight Drift. SSRN 7035838 (1er juil. 2026) + billet Liberty Street Economics, Fed de New York, juil. 2026. https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/ — **`LU-INTÉGRAL` pour le billet Liberty Street** ; **`ABSTRACT-SEULEMENT`** pour le papier SSRN (403).

19. **Berkman, H., Koch, P. D., Tuttle, L. A., & Zhang, Y. (2012).** Paying attention: overnight returns and the hidden cost of buying at the open. *Journal of Financial and Quantitative Analysis*, 47(4), 715-741 (version SSRN : DOI 10.2139/ssrn.1625495) — **`ABSTRACT-SEULEMENT`**.

20. **Cliff, M. T., Cooper, M. J., & Gulen, H. (2008).** Return Differences between Trading and Non-Trading Hours: Like Night and Day. SSRN, DOI 10.2139/ssrn.1004081 — **`MÉTADONNÉES-SEULEMENT`**.

21. **Bogousslavsky, V. (2021).** The Cross-Section of Intraday and Overnight Returns. *Journal of Financial Economics* (version SSRN 2016 : DOI 10.2139/ssrn.2869624) — **`MÉTADONNÉES-SEULEMENT`** pour le papier. Sa **discussion FMA 2022 de « The Overnight Drift »** a été lue : https://bogousslavsky.github.io/files/FMA_2022_discussion.pdf — **`LU-INTÉGRAL`** ; il y soulève que le reversal de clôture devrait être bilatéral, que Grossman-Miller prédit un impact de prix à la clôture d'ampleur comparable au drift (« not apparent in the figures/tables »), et que les tests conditionnent sur le **déséquilibre** de clôture et non sur le **rendement** — critique méthodologique utile si le repo veut répliquer.

### Volatilité conditionnelle / queue

22. **Bekaert, G., & Wu, G. (2000).** Asymmetric Volatility and Risk in Equity Markets. *Review of Financial Studies*, 13(1). PDF : https://www.bauer.uh.edu/wu/Papers/RFS2000_AsyVol.pdf — **`ABSTRACT-SEULEMENT`** (PDF localisé mais non extrait).

23. **Black, F. (1976)** ; **Christie, A. A. (1982)** — effet de levier, sources primaires de l'asymétrie volatilité-rendement. **`NON VÉRIFIÉES`** directement ; connues ici uniquement via les descriptions secondaires et via Bekaert-Wu, qui **rejettent** le modèle de pur levier de Christie.

24. **Greenwood, R., Shleifer, A., & You, Y. (2019).** Bubbles for Fama. *Journal of Financial Economics*, 131(1), 20-43 (NBER WP 23191, DOI 10.3386/w23191). PDF : https://www.nber.org/system/files/working_papers/w23191/w23191.pdf — **`ABSTRACT-SEULEMENT`** (PDF localisé, non extrait).

### Sources écartées explicitement

- Toute la littérature de courtier / blog sur « investir aux plus hauts historiques » (Chase, Hartford Funds, RBC GAM, ofdollarsanddata, Nautilus Research, informedmomentum, etc.) : **ÉCARTÉE**. Aucune n'expose d'échantillon, de statistique de test, de correction de tests multiples ni de coûts. Elle est unanime (« les ATH ne sont pas un mauvais moment pour investir ») et cette unanimité est **cohérente** avec Greenwood et al. et avec Li-Yu, mais elle ne constitue pas une preuve et n'entre pas dans le prior.
- Toute source sur « DAX overnight bias » : **ÉCARTÉE**, même motif. **Il n'existe, à ma connaissance, aucune étude académique du rendement overnight du DAX.**

---

## Annexe — ce que je n'ai PAS pu obtenir (à traiter comme dette de vérification)

| Élément | Blocage | Impact sur les conclusions |
|---|---|---|
| Tables exactes de Li & Yu **version JFE 2012** | Paywall ScienceDirect (403) | **Modéré.** Les signes et le message sont identiques d'après l'abstract publié, mais les valeurs numériques citées ici sont celles du WP 2009 auto-qualifié de « very preliminary ». Toute citation chiffrée doit préciser « WP 2009 ». |
| Robustesse **G7** de Li & Yu | Absente du WP, paywall sur la version publiée | **Modéré.** C'est le seul élément qui rendrait le résultat marché-agrégé transposable hors USA — donc pertinent pour le DAX. Statut : `NON VÉRIFIÉ`. |
| Existence d'un test **hors-échantillon** chez Li & Yu | Absent du WP ; version publiée non consultée | **Élevé.** Un R² in-sample de 32-46 % à horizon annuel sur régresseurs à AC 0.93 sans OOS est le profil-type de ce que Goyal-Welch invalident. |
| Texte intégral de Chen-Stivers-Sun, Blau et al., Tomtosov, Driessen et al. | Paywalls (403) | **Modéré.** Les abstracts suffisent à trancher la question de transposabilité (§2), qui se joue sur l'univers et l'horizon, tous deux donnés par les abstracts. Les magnitudes citées restent à vérifier. |
| t-stats du papier « Disappearing Overnight Drift » | SSRN 403 ; le billet Fed n'en donne aucun | **Faible.** Le fait qualitatif (drift ≈ 0 depuis 2021, y compris sur le E-mini Nasdaq-100) est établi par les auteurs eux-mêmes. |
| Toute mesure sur **NQ100/DAX40 en CFD**, sur **15 h de détention**, sur **lundi/mardi**, ou sur la **queue gauche overnight** | N'existe pas dans la littérature | **Élevé, mais irréductible.** Ce sont les questions que seul le repo peut trancher. |
