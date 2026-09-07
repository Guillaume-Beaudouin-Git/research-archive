# PRÉ-ENREGISTREMENT — segmentation Ranaldo, univers multi-paires

> **GELÉ avant tout contact avec les rendements.** 2026-09-08.
> Origine : `macro_round6_2026-09/ARITHMETIQUE_RANALDO.md`, seul axe non varié identifié.

## 1. La question, et pourquoi elle est décisive

Sur **EURUSD seul**, la segmentation Ranaldo donne un brut de **2,07 bps/jour, t 3,55, SR brut 0,73**,
bilatéral (les deux jambes t > 2,5). Elle meurt uniquement au coût : le SR brut de 0,73 contre un
gate à 0,70 ne laisse qu'un budget de **0,04 bps par jambe**, hors d'atteinte de tout véhicule.

**Le SR de 0,73 est mono-paire.** Agréger N sources faiblement corrélées multiplie le SR sans
augmenter le coût par jour (à notionnel total constant, le coût reste 2 aller-retours). Si la
diversification remonte le SR brut, un budget de coût apparaît.

⚠ **Prior défavorable, écrit d'avance** : toutes les majeures sont cotées **contre le dollar**.
C'est exactement la construction **en étoile** dont on a démontré qu'elle plafonne la corrélation
résiduelle à 0,5 et la breadth effective à **2, quel que soit N**. J'attends donc une corrélation
élevée entre paires et un gain de diversification faible. Le test sert à le **mesurer**.

## 2. Spécification — reprise à l'identique, un seul axe change

Du code gelé `Forex/research/active/fix_reversal/step1_backtest.py` :
- jambe **courte** : entrée 03:00 ET, sortie 11:00 ET ;
- jambe **longue** : entrée 11:00 ET, sortie 16:00 ET ;
- heures **ET avec DST** (`ZoneInfo("America/New_York")`), délai 0, prix *as-of*.

**Seul changement : l'univers.** Toutes les majeures USD disponibles dans `data/deep_history_utc/`.

⚠ **Convention de signe, à poser avant de mesurer** : l'effet est un motif **du dollar**. Sur
EURUSD, « short 03-11 » = **long USD**. Pour appliquer le même motif partout, la position est
exprimée en dollars : signe **inchangé** sur les paires où l'USD est au dénominateur (EURUSD,
GBPUSD, AUDUSD, NZDUSD), signe **inversé** sur celles où il est au numérateur (USDJPY, USDCAD,
USDCHF). Une erreur ici transformerait la moitié de l'univers en bruit.

## 3. Ce qui est mesuré

1. Brut par paire (bps/jour) et SR brut par paire.
2. **La matrice de corrélation des rendements quotidiens de stratégie** — c'est la mesure qui décide.
3. SR brut du portefeuille équipondéré, et **breadth effective** `N/(1+(N−1)ρ̄)`.
4. Le budget de coût que ce SR agrégé autorise.

À notionnel total constant, le coût reste **2 aller-retours par jour**, indépendant de N.

## 4. Critères, écrits avant de voir quoi que ce soit

**KILL DÉFINITIF** — si le SR brut agrégé ne dépasse pas **0,90** (soit ~1,2× le mono-paire), ou si
le brut médian par paire est sous **1,0 bps**, l'agrégation n'apporte rien. L'axe se ferme, plus
aucune ré-ouverture : véhicule, coût et univers auront tous été testés.

**CANDIDAT** — SR brut agrégé tel que le net dépasse **0,70** au coût futures (0,4 bps/jambe, soit
0,8 bps/jour). Alors seulement : walk-forward, placebo, et mesure de coût réelle.

**Entre les deux** — non concluant, à documenter comme tel sans poursuivre.

## 5. Comptage

**1 essai** (une spécification, un univers). Programme macro : 17 → 18.
