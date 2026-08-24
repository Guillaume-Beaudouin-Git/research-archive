# ÉTUDE — Gold dans le book : dosage de la sleeve ASIA + or-trend vs ASIA

**Date :** 2026-06-20 · **Branche :** `claude/gold-dosing-compare` (worktree `Algo_claude_goldcompare`, depuis origin/main)
**Pré-registration :** `PREREGISTRATION_GOLD.md` (committée AVANT résultats, commit `74c7de3`)
**Auteur :** session Claude Code (author≠auditor). **Cadre :** RECHERCHE PURE, sandboxée. AUCUN déploiement,
AUCUN toucher au book live (EA gelé). Lecture seule. Engines v2.2 + asia (validés) réutilisés.

---

## VERDICT

**Partie A — DOSING DILEMMA PROUVÉ.** Il n'existe **aucune dose** de gold ASIA net-positive à survie tenue :
toute dose qui contribue dilue la survie funded du book bien au-delà du seuil, et toute dose assez petite pour
ne pas contribuer dilue quand même (et n'extrait rien). Porte **fermée** sur l'intégration d'ASIA au book funded.

**Partie B — COMPLÉMENTAIRES mais l'INTÉGRATION reste fermée.** or-trend et ASIA sont **décorrélées** (ρ 0.08
full ; **0.226 OOS 2020-26** — plus faible récemment), avec un épisode anti-phase fort (or-trend +5.4 % en
2018-19 quand ASIA fait −7.7 %) — **la complémentarité annoncée est RÉELLE** (mais portée surtout par la faible
corrélation + 1 épisode régime, pas une loi anti-phase forte — cf. nuance audit §B). MAIS **or-trend est le MEILLEUR conteneur
gold pour CE book** sur les DEUX gates (challenge ET funded), **malgré un Sharpe standalone bien pire**, parce
que le book récompense le **faible risque always-on** (l'intermittence/gate d'or-trend), PAS le Sharpe. La
complémentarité est **non-récoltable sur FTMO** : le floor-proximity funded tue tout ajout always-on d'ASIA.

**L'angle « les deux gold ensemble » sur FTMO = CLOS** (book[BOTH] funded 65.4 % vs book seul 97.9 %). Il
resterait un angle pour un **book personnel non-floor-contraint** (Sharpe-maximisant) — hors périmètre FTMO.

| | challenge p_funded | funded survie-12m (canonique) | sens |
|---|--:|--:|---|
| **book[or-trend] (live, std)** | **87.01 %** | **97.9 %** | le conteneur actuel — correct |
| book[ASIA remplace or-trend] | 80.95 % | 72.3 % | pire sur les DEUX gates |
| book[BOTH or-trend + ASIA] | 87.45 % | 65.4 % | challenge ~idem, funded crashé |
| book + ASIA dose 0.10× (Part A) | — | 85.3 % (Δ−12.6) | dilue même minuscule |
| book + ASIA dose 1.0× (Part A) | — | 65.4 % (Δ−32.5) | dilue + extrait |

**Cohérent avec le rejet solo d'ASIA** : non seulement ASIA échoue solo, mais **aucune dose** ne l'intègre, et
même comparée tête-à-tête c'est or-trend (déjà dans le book) le bon conteneur. **Le book a raison.**

---

## PARTIE A — Dosage : pas de dose net-positive (dilemme prouvé)

Ablation funded **canonique** (book vs book+ASIA_dosé, stop −2.5 % appliqué UNE fois, sans double-K). Anchor
book-only **97.9 % / fundedV $1442** (reproduit). Dose = fraction × taille contributive K=1.

| dose | book+ASIA survie-12m | Δsurvie | fundedV | Δextraction | net-positif ? |
|--:|--:|--:|--:|--:|:--:|
| 0.10× | 85.3 % | **−12.6** | $1 274 | **−168** | non (dilue + extrait NÉGATIF) |
| 0.25× | 67.5 % | **−30.4** | $1 020 | −422 | non |
| 0.50× | 68.6 % | −29.3 | $1 470 | +28 | non |
| 0.75× | 64.9 % | −33.0 | $1 736 | +294 | non |
| 1.00× | 65.4 % | −32.5 | $2 124 | +682 | non |

**Lecture (dilemme prouvé) :**
- **Aucune dose** n'a Δsurvie ≥ −2.5 pt ET Δextraction > 0. **DILEMME.**
- **Même la plus petite dose (0.10×, ~0.68 % vol) dilue −12.6 pt** ET extrait NÉGATIF (−168) : les busts qu'elle
  cause coûtent plus que le rendement minuscule qu'elle ajoute. À 0.25× la dilution **sature déjà à −30 pt**
  (≈ la dose pleine) avec extraction encore négative (−422).
- **Première dose qui contribue (Δextract>0) = 0.50× ; première dose qui dilue (<−2.5 pt) = 0.10×.** Le seuil de
  dilution (0.1) est **très en-dessous** du seuil de contribution (0.5) → pour contribuer, il faut une dose qui
  dilue déjà ~−29 pt. **Découplés dans le mauvais sens.**
- **Mécanisme (funded-survival-is-drawdown-governed, fine résolution ; preuve renforcée à l'audit)** : le book
  funded **frôle déjà le floor statique −10 %** (survie 97.9 % = quelques % déjà bustés). **Preuve directe (audit) :
  à dose ~0.02× (négligeable), 52/56 busts surviennent avec le solde à $9 000–$9 004** (soit $0.70–$3.60 au-dessus
  du floor) — le minuscule dip ASIA est la **dernière goutte** dans 52/52 cas. Ajouter **n'importe quelle** source
  de drawdown always-on bascule les cohortes marginales sous le floor → survie chute. La dilution **sature vite**
  (0.25×) car l'ensemble des cohortes frôlant le floor est fixe ; au-delà, plus de dose n'ajoute que de
  l'extraction (et un peu de bust). *(NB métrique : le `min_eq` du moteur est faussé par le breaker [pre-flatten] —
  non cité ; la preuve floor-grazing utilise le solde-à-l'ouverture-ASIA, plus robuste.)* Ce n'est **pas un
  tradeoff lisse, c'est une marche** : dilution dès la dose
  minimale, contribution seulement aux grosses doses.

## PARTIE B — or-trend (book) vs ASIA (overnight)

**(a) Standalone (2007-2026 commun)** — ASIA est le BIEN meilleur edge gold ; or-trend est faible et intermittent :

| | Sharpe (full/active) | annret | maxDD | skew | jours actifs |
|---|--:|--:|--:|--:|--:|
| **or-trend** (WT[XAU]) | 0.3 / 0.4 | +2.52 % | −30.4 % | +0.12 | **56.9 %** (signal-dépendant) |
| **ASIA** (overnight) | **1.14** / 1.14 | **+7.76 %** | **−19.0 %** | **+0.41** | 99.2 % (always-on) |

**(b) Corrélation** or-trend vs ASIA : **ρ 0.084** (all-days), 0.107 (both-active), 0.011 (2018-19) → **DÉCORRÉLÉES**.

**(c) Complémentarité temporelle — la complémentarité du rapport est RÉELLE :**

| fenêtre | or-trend | ASIA | lecture |
|---|--:|--:|---|
| **2018-19 (régime ASIA-mort)** | **+5.4 %** / Sh 0.68 | **−7.7 %** / Sh −1.22 | or-trend GAGNE quand ASIA meurt ✓ |
| **jours or-trend OFF** (43 %) | 0 (coupé) | **+8.8 %** / Sh 1.36 | ASIA comble le trou ✓ |
| jours or-trend ON | +4.4 % / Sh 0.40 | +7.0 % / Sh 0.98 | les deux contribuent (overlap) |

→ **Complémentaires, mais nuance honnête (audit)** : la preuve ROBUSTE est la **faible corrélation** (ρ 0.08
full) — **qui MONTE toutefois à 0.226 en OOS 2020-26** (décorrélation plus faible récemment, à surveiller). Le
« ASIA +8.8 % les jours or-trend-OFF » est **en partie mécanique** (ASIA gagne ~+3 bps *tous* les jours, ON ou
OFF) ; le vrai anti-phase fort (or-trend gagne quand ASIA meurt) **repose sur le seul épisode 2018-19** (réel
mais n=1 régime). Seuil pré-enregistré (ρ < 0.50 ET anti-phase) **atteint** — mais l'anti-phase est 1 épisode +
ρ qui remonte OOS, pas une loi forte. **(d)** ASIA always-on (99 %), or-trend intermittent (57 %).

**(e) Swap hypothétique (NE PAS déployer ; EA gelé) — or-trend est le meilleur conteneur des DEUX gates :**

| book | challenge p_funded | funded survie-12m |
|---|--:|--:|
| **[or-trend] (live)** | **87.01 %** | **97.9 %** |
| [ASIA remplace or-trend] | 80.95 % (−6.1) | 72.3 % (−25.6) |
| [BOTH or-trend + ASIA] | 87.45 % | 65.4 % (−32.5) |

**Le paradoxe central : ASIA est un MEILLEUR edge (Sharpe 1.14 vs 0.4) mais un PIRE conteneur de book.** Remplacer
or-trend par ASIA dégrade le challenge (87→81 : l'always-on 6.8 %-vol d'ASIA perce plus la barrière à vm=14, vs
or-trend flat 43 % du temps) ET le funded (98→72 : always-on empile du drawdown vs le floor). **Le book récompense
le faible risque always-on (l'intermittence/gate d'or-trend), PAS le Sharpe** — exactement *two-FTMO-stages-reward-
opposite-axes* + *funded-survival-drawdown-governed*. L'intermittence d'or-trend (un défaut côté Sharpe standalone)
est précisément ce qui en fait le bon conteneur. **Ajouter les deux (BOTH) dilue le funded (65.4 %)** = le dilemme
de dosage de la Partie A. **Le book live a raison d'utiliser or-trend, pas ASIA.**

## Verdict & synthèse

- **Partie A : DILEMME DE DOSAGE prouvé** (aucune dose net-positive ; dilution dès 0.1×, contribution seulement
  ≥0.5× qui dilue −29). Intégration d'ASIA au book funded : **close à toute taille**.
- **Partie B : COMPLÉMENTAIRES** (ρ 0.08, anti-phase régimes — la complémentarité du rapport est RÉELLE) **mais
  or-trend est le meilleur conteneur gold pour ce book** (les deux gates), car le book pénalise le risque
  always-on, pas le Sharpe. **« Both gold » sur FTMO = CLOS** (funded 65.4 %).
- **L'angle complémentarité serait récoltable sur un book PERSONNEL non-floor-contraint** (Sharpe-maximisant :
  combiner or-trend 0.4 + ASIA 1.14 décorrélées améliorerait le Sharpe portefeuille) — mais **PAS sur FTMO**, où
  le floor statique −10 % gouverne et tue tout ajout always-on. **Hors périmètre FTMO** (à noter pour le book perso).
- **Cohérence avec les verdicts rendus** : ASIA solo = rejet ; ici on prouve que (i) **aucune dose** ne l'intègre,
  (ii) tête-à-tête c'est or-trend le bon conteneur. La complémentarité réelle ≠ intégrabilité (cf. leçon panier :
  *décorrélation ≠ bénéfice funded*).

### Candidats de leçon (NOMMÉS, non gravés)
1. **« container-intermittency-beats-standalone-Sharpe-for-a-floor-constrained-book »** : une sleeve gold gated/
   intermittente à FAIBLE Sharpe (or-trend 0.4, off 43 % des jours) est un MEILLEUR conteneur de book FTMO (challenge
   ET funded) qu'une sleeve always-on à HAUT Sharpe (ASIA 1.14), car les deux gates pénalisent l'exposition
   drawdown always-on, pas le Sharpe. Extension de *two-stages-opposite-axes* + *funded-drawdown-governed*.
2. **« complementarity-real-but-unharvestable-on-FTMO »** : deux gold strategies génuinement complémentaires
   (ρ 0.08, anti-phase régimes) ne se combinent PAS sur FTMO — le floor-proximity funded tue tout ajout always-on
   quelle que soit la décorrélation (dilemme de dosage Partie A). Récoltable seulement sur un book non-floor-contraint.

---

## Reproductibilité
- Pré-reg : `PREREGISTRATION_GOLD.md` (commit `74c7de3`, avant résultats).
- Code (`code/`) : `validate_baselines.py` (ASIA-OFF→87.01, book canonique 97.9/$1442, stop−2.5 intact, or-trend
  reconstruit), `partA_dosing.py` (courbe de dose, canonique, stop appliqué une fois), `partB_compare.py`
  (standalone/corr/temporel/swap). Réutilise `asia_inject/series/stop/fp` (copiés validés de `claude/asia-23-8-funded`),
  cleanroom `build_signals` (or-trend), moteur v2.2 pin `605f4a4`.
- Résultats (`results/`) : `partA_dosing.json`, `partB_compare.json`, `*_console.txt`.
- Données : `XAUUSD_M1.csv` (true-UTC, gitignored). Env `/usr/bin/python3` (numpy 2.0.2, pandas 2.2.3).
- **Aucun fichier live touché.** Worktree isolé.

### Note de probité (author≠auditor)
- Ablation funded sur la fenêtre **CANONIQUE** (leçon panier appliquée) — PAS la fenêtre de convenance de
  l'asia-funded (qui donnait book 98.6 %). Dose appliquée **une fois** (apply_stop(K=dose)+asia_lev=1.0), corrigeant
  le double-K de l'asia-funded K-sensitivity (apply_stop(K)×asia_lev=K → K²).
- Aucun seuil déplacé. Verdict A repose sur la courbe de dose ; verdict B sur corr+temporel+swap.
- **Audit indépendant (`AUDIT_INDEPENDENT.md`) : CONFIRM-WITH-CAVEATS, A/B/C/D/F PASS, E CONCERN.** Tous les
  chiffres reproduits exactement (87.01 / 97.9 / $1442 / dose-curve / swap 87→81/72→65). **Vérifié au-delà du
  re-run** : dose appliquée UNE fois (P&L linéaire 0.31→3.06 bps, pas de double-K) ; swap **vol-équitable**
  (ASIA K=1 vol 6.83 % vs or-trend déployé 7.10 %, ratio 0.96× — ASIA n'est PAS sur-dimensionnée, elle perd
  purement sur l'axe always-on à vol égale → la thèse « le book récompense le faible risque always-on, pas le
  Sharpe » tient) ; dilemme robuste à la fenêtre (−8.9 pt @0.10× sur fenêtre large). **2 corrections INTÉGRÉES** :
  (1) `min_eq` faussé par le breaker → remplacé par la preuve solde-à-l'ouverture ($9 000–$9 004, 52/52, **mécanisme
  RENFORCÉ**) ; (2) « anti-phase » sur-vendu → reformulé (ρ 0.08 full mais 0.226 OOS ; +8.8 % off-days partiellement
  mécanique ; anti-phase = 1 épisode 2018-19). **Aucune correction ne renverse les verdicts A ni B.**
