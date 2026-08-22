# Re-audit complet des 30 stratégies — chasse aux faux verdicts

**Déclencheur :** le deep-dive de S012 avait fait basculer un verdict → légitime question : *combien d'autres verdicts changeraient si on creusait ?* On re-teste **les 30** avec une méthode anti-biais (éviter aussi bien les faux négatifs que les faux positifs). · **Code :** `code/reaudit_scan.py` (Tier 1), `code/reaudit_tier2.py` (Tier 2). · **Date :** 2026-06-07.

---

## Verdict (en tête)

> **Résultat net : 30/30 DISCARD. Aucun faux négatif trouvé — ET un faux POSITIF corrigé : le mien (S012).**
>
> 1. **Les 29 DISCARD sont confirmés.** Le cluster tendance est du **beta** pur (validé contre buy&hold), l'ORB est un **artefact de fill** (S002 s'inverse au fill réaliste), les bougies n'ont **pas d'edge**.
> 2. **S012 (que j'avais monté en BORDERLINE au tour précédent) redescend en DISCARD.** Test propre contre un buy&hold **apparié en exposition/volatilité** : S012 **ne bat pas le beta**. Mon « alpha-vs-neutre +0,018 » du deep-dive était **confondu** par la durée/cible de détention. Je corrige.
> 3. **Les v2-gates avaient raison.** Le seul verdict erroné du projet venait d'un *deep-dive trop généreux*, pas des gates.

---

## Méthode (2 tiers, anti-data-snooping)

Le piège : sur-découper 29 stratégies × (côté × classe × régime × params) **fabrique** des faux positifs (multiple testing). Garde-fous :
- **Tier 1 — scan uniforme** des 30 : full vs **OOS récent (2019+)**, meilleur sous-ensemble par classe, **timing-alpha vs drift**, two-sided récent. Repère les candidats à ré-examen.
- **Tier 2 — tests décisifs** sur les flaggés : (a) **benchmark buy&hold** par classe (contextualise tout « Sharpe récent élevé ») ; (b) **timing-alpha apparié au régime** (le vrai test S012, généralisé) ; (c) **delai+1** pour l'ORB.
- **Barre pour annuler un DISCARD :** sous-ensemble mécaniquement motivé **+** Sharpe récent **> buy&hold apparié** **+** alpha de timing **> 0** **+** persistance OOS. Tout ce qui n'est que « long en marché haussier » reste DISCARD.

## Le contexte qui change tout : 2019+ = rallye généralisé

| Classe | buy&hold Sharpe (full) | **buy&hold 2019+** |
|---|---|---|
| Indices (10) | +0,50 | **+0,93** |
| Crypto (2 : BTC/ETH) | +0,61 | +0,83 |
| Commodities (9) | +0,66 | +0,91 |
| Forex (9) | +0,06 | +0,14 |

→ **N'importe quelle stratégie long-biais affiche un Sharpe récent ~1,0–1,5 par le seul beta.** C'est l'illusion à neutraliser.

## Tier 1 — ce que le scan révèle

- **Le « meilleur sous-ensemble » est presque toujours le CRYPTO** (Sharpe récent 0,7–1,4) pour les stratégies tendance — mais le crypto = **2 instruments** (BTC/ETH) en bull historique. C'est du **beta 2-actifs**, sous le buy&hold crypto. Timing-alpha ≈ +0,002 (négligeable).
- **S002** ressort « two-sided récent + » (long +0,045 / short +0,014) → à vérifier au fill (Tier 2).
- **S012/S013/S016/S017** flaggés « MR-lens » → deep-dive S012.

## Tier 2 — tests décisifs

### a) Cluster tendance = beta (≈22 stratégies) — DISCARD confirmé
Indices-LONG **Sharpe récent** et **timing-alpha apparié au régime** (mean rendement 10 j sur les dates-signal − mean sur toutes les barres du même régime de tendance) :

| Strat | idx-LONG Sh récent | regime-alpha LONG (récent) | Lecture |
|---|---|---|---|
| S006 / S022 Donchian | +1,49 | +0,0025 | ≈ beta (BH 0,93) |
| S002 Crabel ORB | +1,52 | +0,0016 | ≈ beta (+ artefact fill, cf. c) |
| S023 Dow MTF | +1,10 | +0,0005 | ≈ beta |
| S011 ADX | +1,09 | +0,0049 | ≈ beta |
| S025/S026 Dual-Mom | +0,97 | +0,0005 | ≈ beta |

→ **Sharpe récent élevé = beta indices/crypto ; timing-alpha ≈ 0 partout.** Acheter la force ne bat pas être long. **Aucun edge** : DISCARD confirmé.

### b) ORB (S001, S002) = artefact de fill — DISCARD confirmé
**S002, OOS récent :** fill optimiste `stop` → expR **+0,0138** (Sh +0,84, long +0,045 / short +0,014, two-sided positif) **MAIS** fill réaliste `next_open` → expR **−0,0107** (Sh **−0,70**, long +0,013 / short **−0,011**). **Le two-sided récent s'INVERSE → c'est l'artefact de fill intrabar.** (S001 : artefact déjà établi par l'audit d'équipe — origine des v2-gates.)

### c) Bougies MR (S016/S017 Doji) — DISCARD confirmé
Indices-LONG Sharpe récent **0,64 / 0,68 < buy&hold 0,93** ; full-sample négatif (−0,60/−0,61). Pire que le beta. Pas d'edge.

### d) S012 / S013 (Bollinger %b) — **correction : BORDERLINE → DISCARD**
Le test décisif est le **benchmark apparié en exposition/volatilité** :

| Mesure | S012 | Buy&hold de référence |
|---|---|---|
| Indices-LONG, **Sharpe récent** | +0,97 | **+0,93** (BH indices toujours-investi) |
| Version **low-vol** (C2), Sharpe récent | +1,33 | **+1,41** (BH indices, jours low-vol seulement) |
| Timing-alpha apparié régime (10 j, récent) | **≈ 0** (+0,0004) | — |

→ **S012 ne bat pas le beta.** Plein ≈ buy&hold (0,97 vs 0,93, dans le bruit) ; la version low-vol (1,33) **sous-performe** un buy&hold restreint aux jours low-vol (1,41) — donc le gain low-vol était **mécanique** (les jours calmes ont un Sharpe plus élevé pour tout le monde), pas de l'alpha.

**Pourquoi mon deep-dive s'était trompé :** l'« alpha-vs-neutre +0,018 » comparait l'entrée dip (%b<0,2) à une entrée neutre (%b∈[0,4;0,6]) **avec la même sortie %b>0,8**. Or le dip vise une réversion **plus grande** (0,2→0,8) que le neutre (0,5→0,8) : il capte un mouvement plus gros **par construction de la cible**, pas par habileté de timing. Le confounder est la **durée/cible de détention**, pas l'entrée. Le benchmark vs buy&hold apparié, lui, est non-confondu — et il ne montre **aucun edge**.

## Leçon de méthode (à intégrer au pipeline)
**Ajouter aux gates un 5ᵉ test : « bat-il un buy&hold apparié en exposition/vol ? ».** Le two-sided + DSR attrapaient le beta symétrique ; mais un **sleeve long-only** peut tromper si on le compare à une mauvaise référence. La bonne référence n'est pas « entrée neutre, même sortie » (confondue par la cible) mais **buy&hold apparié en temps-de-marché et régime de vol**.

## Tableau final — 30 stratégies

| Cluster | Strat | Verdict original | **Re-audit** |
|---|---|---|---|
| ORB-stop | S001, S002 | DISCARD | ✅ DISCARD (artefact fill, S002 s'inverse) |
| Trend (KAMA/ADX/Aroon/DI) | S003–S011, S015 | DISCARD | ✅ DISCARD (beta, α≈0 vs BH) |
| Bollinger MR | **S012, S013** | ~~BORDERLINE/watchlist~~ | ⬇️ **DISCARD (ne bat pas le beta — correction)** |
| Bollinger/breakout | S014 | DISCARD | ✅ DISCARD (beta) |
| Doji | S016–S019 | DISCARD | ✅ DISCARD (< beta / négatif) |
| Donchian/Turtle | S020–S022 | DISCARD | ✅ DISCARD (beta) |
| Dow pivots | S023, S024 | DISCARD | ✅ DISCARD (beta) |
| Dual Momentum | S025, S026 | DISCARD | ✅ DISCARD (beta) |
| Engulfing | S027–S030 | DISCARD | ✅ DISCARD (pas d'edge) |

**Bilan : 30/30 DISCARD. 0 KEEP, 0 BORDERLINE.** Sur l'univers FTMO et les 30 premières fiches, **aucun edge de timing ne bat le buy&hold apparié**. Les v2-gates étaient justes ; le seul faux verdict (S012) venait d'un deep-dive trop indulgent, désormais corrigé.

## Suite
Continuer #31+ (False Breakout = vraie contre-tendance) **avec le test buy&hold-apparié ajouté**. Si un mean-reversion bat enfin le beta apparié sur données récentes → vrai signal, audit profond. Sinon, la conclusion du projet se dessine : ces archétypes classiques sont du beta sur cet univers.

*Repro : `cd oxfordstrat_109/code && python reaudit_scan.py && python reaudit_tier2.py`. Données : `results/reaudit_scan.csv`.*
