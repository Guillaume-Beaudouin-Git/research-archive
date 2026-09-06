# Porte préalable de l'axe H — existe-t-il une attente mesurable ? OUI, par un détour

**2026-09-07.** Vérification gratuite exigée par `SYNTHESE_ROUND3.md` avant toute ligne de code.
Δn_tests = 0.

## La question

Une « surprise de refinancement » suppose une attente publiée. Sans elle, on régresse sur le
**NIVEAU** — et le contrôle de dose révélerait que le seuil sélectionne une période, exactement ce
qui vient de tuer l'axe B3.

## Ce qui existe, et ce qui n'existe pas

**Le consensus de dealers n'est PAS exploitable.** Les prévisions de primary dealers apparaissent
dans les minutes du TBAC, **publiées après** l'annonce, et dans des notes de recherche
propriétaires. Les « dealers attendaient X » de la presse ne constituent pas une série archivée et
lisible par machine. ⇒ **Pas de consensus utilisable gratuitement.**

**Mais la structure du processus fournit une surprise mécanique et archivée.** Le calendrier est en
deux temps, tous les premiers mercredis de février, mai, août et novembre :

1. **Lundi** — Treasury publie ses *Marketable Borrowing Estimates* ;
2. **Mercredi 8h30** — l'annonce de refinancement complète, avec les tailles d'adjudication.

Or chaque publication d'estimation couvre **le trimestre en cours ET le trimestre suivant**. Il
existe donc, pour un même trimestre Q, deux estimations successives publiées par la même source :

```
révision(Q) = estimation_t(Q) − estimation_{t−1}(Q)
```

C'est une **révision Treasury contre Treasury**, entièrement archivée sur treasury.gov, mécanique,
sans donnée propriétaire, et disponible sur tout l'historique des communiqués.

## Conséquence

**La porte est franchie**, mais l'objet mesuré change de nature : ce n'est pas un écart au consensus
de marché, c'est une **révision de l'émetteur par rapport à sa propre prévision**. C'est plus faible
en théorie — le marché a pu anticiper la révision — mais c'est mesurable, honnête et gratuit.

⚠ **À pré-enregistrer explicitement** : l'hypothèse porte sur la révision de l'émetteur, pas sur une
surprise de consensus. Ne pas présenter l'une pour l'autre.

⚠ **Le contrôle de dose est obligatoire dès la conception** (candidate « contrôle de dose », issue de
B3) : mesurer l'effet sur les trimestres dont la révision est **sous** le seuil et exiger qu'il soit
proche de zéro. Avec 4 annonces par an, l'échantillon est petit — la puissance sera la contrainte
liante, et le MDE à 80 % doit être calculé **avant** de lancer quoi que ce soit.
