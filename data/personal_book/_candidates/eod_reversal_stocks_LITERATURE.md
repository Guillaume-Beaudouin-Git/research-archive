# Candidat — End-of-Day Reversal en coupe d'actions (⚠ NON MESURÉ CHEZ NOUS)

> **Statut** : **pointeur de littérature, ZÉRO mesure interne.** Écarté du programme FTMO pour un
> **problème d'UNIVERS, pas de coût** — donc rouvrable sur un véhicule qui a des actions
> individuelles. Aucun chiffre ci-dessous n'est de nous.
> **Source** : `Multi_Asset/research/active/literature_sweep_2026-08/SWEEP.md`.

## Pourquoi il est ici

C'est le **seul** mécanisme de la revue 2022-2026 qui ait été écarté « à regret » : il annonce
**plus de 20 % d'alpha brut**, il est **explicitement non-gamma** (donc pas une simple prime de
risque de couverture), et il a reçu le 2e prix Quantpedia 2025. Il ne meurt chez nous que parce
qu'il exige une **coupe d'actions individuelles**, absente de l'univers FTMO CFD (17 instruments :
FX, indices, métaux, énergie).

**Un compte courtier classique lève exactement cette contrainte.**

## Référence

Baltussen, Da, Soebhag — *End-of-Day Reversal*. À récupérer et lire intégralement avant tout
travail : la revue n'a **pas** pu extraire les magnitudes conditionnelles (paywall).

## Ce qu'il faudrait faire — et l'ordre compte

1. **Matrice de véhicule AVANT le backtest** (L53) : combien d'actions faut-il réellement pour que
   la coupe fonctionne, quel est le coût réel par jambe chez le courtier, et la marge du panier
   minimal tient-elle dans le capital ? **Si le panier minimal ne tient pas, l'affaire s'arrête là**
   et il ne faut pas coder une ligne.
2. **Ne pas reproduire le papier** — s'en inspirer. La question utile n'est pas « retrouve-t-on
   20 % ? » mais « que reste-t-il du mécanisme à notre nombre d'actions, à notre coût, à notre
   granularité de lot ? ».
3. **Contrôles obligatoires** avant toute revendication : gate au **gross** d'abord ; **L58**
   baseline inconditionnelle (une coupe long/short sur actions a une espérance inconditionnelle non
   nulle) ; **L25** two-sided à jambes disjointes ; **L59** delay+1 sur l'entrée **et** la sortie —
   ⚠ un effet « de fin de journée » est le cas le plus exposé à ce piège, l'expérience du dossier
   momentum de clôture ayant montré que **31-43 % du gross vivait dans le dernier print**.
4. **Prior à garder froid** : notre propre test de dose sur la fenêtre de clôture des indices a
   conclu à un **kill mécanique**, avec un contrôle négatif qui inversait l'ordre attendu. Ce n'est
   pas le même objet (coupe d'actions vs niveau d'indice) et cela ne réfute pas Baltussen — mais ça
   invite à la prudence sur tout ce qui vit dans les dernières minutes.

## Données

**Non disponibles dans le dépôt.** Aucune série d'actions individuelles ; le levier « données
payantes » reste explicitement fermé. Ce candidat est donc **bloqué sur la donnée**, et il faut le
dire plutôt que de le laisser espérer.
