# EIA — résultats : hypothèse pré-enregistrée REJETÉE, kill mécanique

**2026-09-08.** Spec gelée : `PREREGISTRATION.md`. 437 événements, 2018-01 → 2026-06.
Coût RT mesuré : **7,53 bps** (spread médian de la série, 1 point = 0,001 USD).

## ⚠ Une erreur de ma part, corrigée avant conclusion

Mon premier passage a facturé le spread à **1 point = 0,01 USD**, donnant un coût de 75 bps. Faux :
le plus petit incrément de prix observé sur la série est **0,001**, donc 1 point = 0,001 et le coût
réel est **7,53 bps** — un facteur **10**. L'erreur aurait conclu au bon verdict pour la mauvaise
raison (mort au coût plutôt que mort au signal). Vérification faite en inspectant la granularité
réelle des prix, pas la documentation.

## Le résultat

Côté = −signe(surprise) : accumulation surprise ⇒ vente.

| horizon | n | brut | t_HAC | net | brut / 3×coût |
|---|---|---|---|---|---|
| 15 min | 437 | −3,89 bps | −1,03 | −11,42 | −0,17 |
| 60 min | 437 | −6,68 | −1,58 | −14,21 | −0,30 |
| 240 min | 437 | −11,60 | −1,41 | −19,14 | −0,51 |
| clôture | 436 | −10,56 | −1,24 | −18,09 | −0,47 |

**Le critère de KILL MÉCANIQUE du pré-enregistrement est atteint** : |t_HAC| < 2,0 aux quatre
horizons. L'hypothèse est rejetée.

Et elle l'est avec le **mauvais signe** : vendre après une accumulation surprise **perd**, de façon
consistante aux quatre horizons.

## Le contrôle de dose — informatif, et il complique la lecture

| tercile de \|surprise\| | n | médiane \|surp\| | h60 | t | h240 | t |
|---|---|---|---|---|---|---|
| T1 faible | 146 | 0,98 Mb | +5,57 | +0,79 | −3,96 | −0,26 |
| T2 moyen | 145 | 3,11 | −9,94 | −1,61 | −8,02 | −0,73 |
| T3 fort | 146 | 6,42 | **−15,69** | **−2,15** | **−22,81** | **−1,97** |

La réponse est **monotone** — donc ce n'est pas un effet de fenêtre ou de période, contrairement au
cas B3. Il existe une vraie relation dose-effet. **Mais elle va dans le sens de la perte** : plus la
surprise est grande, plus la position pré-enregistrée perd.

**Le diagnostic décisif** : la régression du rendement sur la surprise **signée** donne une pente de
**+0,007 bps par Mb (t +0,01)** à 60 min et **−0,246 (t −0,19)** à 240 min. **Plate.** L'effet est
attaché à la **magnitude**, pas à la **direction** — ce qui est incompatible avec le mécanisme
fondamental invoqué (une accumulation devrait faire baisser le prix).

## Ce que je ne fais PAS

Le motif suggère une **sur-réaction suivie d'un retour** : après une grosse surprise, le prix
revient sur ses pas, donc la position miroir gagnerait. **Je ne la teste pas ici**, pour trois
raisons :

1. **Retourner le signe après avoir vu le résultat est exactement la discipline qu'on s'interdit.**
   Une hypothèse de retournement est légitime, mais elle exige son propre pré-enregistrement et
   compte ses propres essais.
2. **Le gate de coût ne la sauve pas.** Le meilleur cas absolu est le tercile T3 à 240 min :
   22,81 bps contre **3 × 7,53 = 22,6 bps** requis. Ratio **1,01** — exactement à la ligne, sur un
   tercile sélectionné après coup, avec t = −1,97. L'espérance d'un test supplémentaire est faible.
3. **Un mécanisme fondamental qui fonctionne à l'envers est plus souvent un artefact qu'une
   découverte.** Avant de tester le retournement, il faudrait expliquer pourquoi le sens direct est
   absent — sans quoi on ajusterait une histoire au résultat.

## Verdict

**Kill mécanique de l'hypothèse pré-enregistrée.** L'axe « surprise d'inventaires EIA, sens direct »
est fermé.

⚠ **Nuance d'attribution** (candidate « attribution-du-kill ») : ce qui meurt est **le sens direct**,
pas toute la famille. L'axe de **retournement après grosse surprise** reste non testé, avec un ratio
au gate de coût de 1,01 — donc **rouvrable**, mais sans intérêt évident. À écrire dans l'énumération
plutôt qu'à poursuivre.

**Ce qui reste vrai et utile** : la breadth de ~52 paris/an est la meilleure du programme, et le
consensus point-in-time est disponible gratuitement et vérifié propre. Si une hypothèse
d'inventaires revient un jour, l'infrastructure de données est faite.

Compteur programme macro : 9 → 13 essais. Global figé.
