# Test §6.4 exécuté — B1 survit au basculement de régime de corrélation

**2026-09-07.** Test spécifié par `RAPPORT.md` §6.4 (jamais exécuté avant). **Audit sur données
existantes, pas une modification** — ne consomme aucun slot du budget de 3 mods. Δn_tests = 0.

## Ce que le test tranche

L'axe corrélation posait une question à la sleeve **B1 (month-end obligataire, +17,6 %/an,
Sharpe 0,92)**, la seule sleeve validée du book personnel : sa performance repose-t-elle en partie
sur le régime de corrélation **négative** qui a prévalu jusqu'en 2021 ?

Le piège nommé (forme testable de L54) : la théorie prédit que la prime de risque de l'actif de
couverture monte exactement quand sa qualité de couverture se dégrade. Si B1 était un pari de
duration déguisé, il aurait dû s'affaiblir après la bascule de 2021 — et *a fortiori* pendant le
marché baissier obligataire de 2022.

**Critère écrit d'avance** : rendement conditionnel stable ou meilleur après 2021 ⇒ hypothèse de
risque caché **falsifiée**. Significativement plus faible ⇒ B1 structurellement plus fragile que sa
moyenne plein-échantillon.

## Résultat

Rendements en **excès**, une observation par mois, HAC lag-6.

### IEF (7-10 ans) — le proxy pertinent, B1 se déploie sur ZN

| période | n mois | bps/mois | t_HAC | MDE80 | effet/MDE | %/an | vol ann. |
|---|---|---|---|---|---|---|---|
| 2004-2020 (ρ<0) | 204 | **+21,21** | +5,11 | 12,59 | +1,68 | +2,55 | 2,22 % |
| 2021-2026 (ρ>0) | 65 | **+19,01** | +2,75 | 23,71 | +0,80 | +2,28 | 2,36 % |
| plein | 269 | +20,68 | +5,73 | 11,11 | +1,86 | +2,48 | 2,25 % |

**Écart : −2,20 bps/mois (−0,26 pt/an). Welch t = −0,23, p = 0,819.**

### TLT (20+ ans) — contrôle sur duration longue

| période | n mois | bps/mois | t_HAC | MDE80 | effet/MDE | %/an | vol ann. |
|---|---|---|---|---|---|---|---|
| 2004-2020 (ρ<0) | 204 | +38,81 | +4,72 | 25,91 | +1,50 | +4,66 | 4,58 % |
| 2021-2026 (ρ>0) | 65 | +24,71 | +1,96 | 46,18 | +0,53 | +2,96 | 4,60 % |
| plein | 269 | +35,40 | +5,01 | 22,58 | +1,57 | +4,25 | 4,58 % |

**Écart : −14,11 bps/mois (−1,69 pt/an). Welch t = −0,75, p = 0,457.**

## Verdict

**Hypothèse de risque caché FALSIFIÉE sur le véhicule pertinent.** Sur IEF, l'écart de −2,20 bps
est **d'un ordre de grandeur sous le plancher de détection** (MDE80 = 23,71) : ce n'est pas
« non significatif faute de puissance », c'est stable.

**Ni la moyenne ni la variance ne se dégradent** : la volatilité annualisée passe de 2,22 % à
2,36 % sur IEF, de 4,58 % à 4,60 % sur TLT. Et B1 reste individuellement significatif sur la
sous-période récente seule (t 2,75 sur IEF).

⇒ **B1 n'est pas un pari de duration déguisé.** Le mécanisme de flux de fin de mois a traversé la
bascule de corrélation de 2021 et le marché baissier obligataire de 2022 sans s'éroder. C'est un
argument de robustesse fort pour la seule sleeve validée du book personnel, et il ne coûtait qu'une
repartition d'un échantillon déjà présent.

## Honnêteté sur les limites

**TLT est moins concluant qu'IEF.** L'écart ponctuel y vaut −14,11 bps contre un MDE de 46,18 :
dans le bruit, mais l'estimation ponctuelle est assez grande pour qu'on ne puisse pas exclure une
dégradation réelle sur la duration longue. Comme B1 se déploie sur ZN (10 ans), c'est IEF qui
tranche — mais si une variante longue duration était envisagée un jour, ce résultat ne la couvre pas.

**La sous-période récente est courte** (65 mois) : le ratio effet/MDE y vaut 0,53-0,80, donc B1 seul
sur 2021-2026 est sous-puissant. Ça n'invalide pas le plein échantillon (ratio 1,57-1,86), mais
interdit de conclure quoi que ce soit à partir du récent seul.

**Le découpage de régime est repris de la littérature** (bascule ~2021), pas estimé de façon
endogène ici. Par L64, une rupture s'estime plutôt qu'elle ne s'impose. Ici la date est **exogène**
— elle vient de sources externes, pas de nos données — ce qui écarte le biais de sélection que L64
vise, mais une estimation endogène reste préférable si l'axe devait être poussé plus loin.
