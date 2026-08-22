# Skew Research — session_B_selectivity — Exploration 2026-06
*Objectif : sélectivité instrument/temps, mécanisme justifié. Sleeves SKEW+ / décorrélés (L7).
**Anti-mining strict** (L10 : mécanisme a priori, PAS de day-of-week mining — BTC-Monday t=3,29 = max-of-60 = bruit rejeté).
**Gate-0 tradeabilité FTMO**. Périmètre : écrit UNIQUEMENT dans `data/skew_research/session_B_selectivity/`. Rien figé/mergé.
Code : `code/skew_sessionB_seasonality.py`, `code/skew_sessionB_rest.py`.*

---

# SB-1 — Commodity seasonality OPÉRATIONNALISÉE (le livrable concret)
*But : la spec déployable (mois × instrument CFD FTMO), PAS re-prouver l'edge (keeper archive Sharpe 0,30, corr 0,10 TSMOM).*

## Finding #1 (piège quant décisif) : les ETF commodities saignent le contango → seasonality contaminée
Moyennes mensuelles saisonnières (bps/mois, full history) : **UNG (NatGas ETF) est négatif quasi tous les mois**
(−248 jan … −967 déc) = **roll-bleed de l'ETF**, PAS le gaz physique. Conséquence : « NatGas LONG Sep-Dec » via UNG =
**−453 bps/mo (t=−2,78)** → wrong-signed. Idem USO/UGA (skew −2 à −3, contaminés contango). → **On ne peut PAS
opérationnaliser l'énergie depuis les ETF** : il faut des **futures roll-adjusted** (la méthode de l'archive).

## Finding #2 : le seul seasonal PROPRE et déployable = OR (XAUUSD)
GLD track le spot (pas de roll-bleed) → seasonality propre et robuste :
- **Gold JANVIER : +347 bps, t=3,22, 15/22 ans positifs** (hit 68 %).
- Sleeve **[Jan, Aug, Sep] : +169 bps/mo, t=2,54, skew −0,08** (symétrique), **corr SPY +0,06** (décorrélé).
- OOS : pre-2013 +251 (t1,91) → **2013+ +120 (t1,66)** : décay mais reste positif.
- Mécanisme : demande physique Q1 (Nouvel An lunaire / festivals / mariages ; restock joailliers).

## SPEC DÉPLOYABLE FTMO
| Instrument FTMO | Mois LONG | Mécanisme | Edge (data dispo) | Statut |
|---|---|---|---|:--:|
| **XAUUSD (or)** | **Janvier** (cœur) + Aug-Sep (secondaire) | demande festival/mariage Q1 | Jan +347bps t=3,22 ; sleeve t=2,54 skew~0 décorrélé | ✅ **déployable** |
| USOIL / UKOIL (brut/Brent) | Fév-Mai (théorie driving season) | demande pré-été | contaminé ETF, t<1 ; skew −2 | ⚠ besoin futures roll-adj |
| NGAS (gaz) | Sep-Déc (théorie hiver) | chauffage hiver | ETF roll-bleed masque (t=−2,8) | ⚠ besoin futures roll-adj |

**Déploiement or** : entrer ~dernier jour ouvré de décembre (cœur janvier ; idem fin juillet pour Aug-Sep), tenir le
mois, sortir. Taille modeste (signal rare, 1-3 mois/an). **Avant live** : re-mesurer le net sur le CFD XAUUSD réel
(spread + swap nuit × jours tenus, L33) — l'or n'a pas de roll mais le CFD a un swap.
**Recommandation énergie** : récupérer des continuous futures roll-adjusted (spec archive) ; les CFD FTMO énergie ont
leur propre portage (swap = courbe) → mesurer le net sur l'instrument réel, ne pas déployer depuis l'ETF.

---

# SB-2 — Trend crypto BTC/ETH : brique décorrélée mais skew−
- BTC 100d trend (2-sided) : **Sharpe +0,54, skew −0,49** ; ETH : +0,64, skew −0,66 ; BTC long-only +0,78 / skew −1,13 (beta).
- **corr(BTC trend, TSMOM commo/FX) = +0,07 → brique DISTINCTE** (pas redondante → ce n'est pas du tuning).
- **Mais skew NÉGATIF** (crashs crypto frappent le trend) → **échoue le mandat skew+**.
→ Verdict : edge réel + décorrélé, **mauvais profil skew** → brique pour un book *Sharpe*, **hors mandat skew+**.

# SB-3 — Rotation momentum inter-classe : breadth-trap + un L/S skew+ modeste
*Classes FTMO-tradeables uniquement (SPY, GLD, DBC, BTC, UUP — **pas de bonds**, cf. B1). Momentum 3 mois.*
- Long-top **Sharpe 1,00** vs **EW-long 0,94** → la sélection **ne bat pas nettement l'EW** sur Sharpe (**breadth-trap
  quasi-confirmé** ; le long-top = concentration BTC, mean +451 bps/mo dominé par les bull-runs crypto).
- **Rotation L/S two-sided : Sharpe 0,80, skew +0,35**, hit 0,53 → candidat décorrélé skew+ (market-neutral-er).
→ Verdict : la sélection long-only n'ajoute pas d'alpha vs EW (juste beta/concentration) ; la version **L/S** est un
candidat **skew+ modeste à creuser** (⚠ dépendance BTC, n=137 mois).

# SB-4 — Crypto weekend : REJETÉ
weekend (Sat+Sun) **+7,6 bps t=0,97** < semaine +13,7 t=2,00. Pas d'effet weekend (les rendements crypto s'accumulent
en semaine). Hypothèse pré-spécifiée (liquidité weekend) **rejetée proprement** — sans day-mining.

# SB-5 — Vol-conditionné : REJETÉ
MR inconditionnel (Sh **0,51**) > MR|high-vol (0,43) > MR|low-vol (0,28) ; trend ≈0 partout. Le split vol (médian,
non-tuné) **n'améliore pas** → reconfirme `layering-filters-degrades` (batch 4).

---

## Reconcile archive (L31)
seasonality = keeper (Sharpe 0,30), **cité, NON re-prouvé** ; ici **opérationnalisé** → révèle le piège ETF-roll et
sort l'**or** comme cellule propre déployable. TSMOM cité (crypto trend décorrélé, corr 0,07). day-of-week
BTC-Monday = bruit (max-of-60), **non re-testé** (discipline anti-mining respectée).

## Verdict session_B
**Pièce livrable concrète : spec or-seasonal déployable (XAUUSD, cœur janvier, t=3,22, décorrélé corr +0,06,
skew~0, OOS-positif).** Énergie = non-déployable depuis ETF (piège roll), besoin futures roll-adjusted. Exploration :
crypto trend = brique Sharpe décorrélée mais **skew− (hors mandat)** ; rotation **L/S** = candidat skew+ modeste
(BTC-dépendant) ; weekend + vol-cond **rejetés**.

## Candidats-leçons (NOMMÉS)
> **LESSON-CANDIDATE: ETF-roll-contaminates-commodity-seasonality** — mesurer la saisonnalité commodities sur des ETF
> qui saignent le contango (USO/UNG : −250 à −970 bps/mois quasi partout) **conflate le seasonal avec la décote de roll** :
> le « long gaz hiver » via UNG sort NÉGATIF (t=−2,8). Utiliser des futures roll-adjusted, ou un instrument **sans-roll
> (or)** dont la saisonnalité est propre (Jan t=3,22).

> **LESSON-CANDIDATE: cross-asset-selection-rarely-beats-EW-on-Sharpe** (breadth-trap) — long-top-momentum (Sh 1,00)
> ≈ EW-long (0,94) : la sélection **n'ajoute pas d'alpha Sharpe**, juste de la concentration/timing (ici BTC). La valeur
> d'une rotation, si elle existe, est dans la version **L/S two-sided** (skew+ 0,35), pas le long-only — toujours
> benchmarker contre le panier EW avant de croire au « stock/asset-picking ».

> **LESSON-CANDIDATE: decorrelated-≠-skew-positive** — le trend crypto est décorrélé (corr 0,07 TSMOM) ET a de l'edge
> (Sh 0,54) MAIS skew −0,49 : décorrélation et skew+ sont deux critères **indépendants**. Pour le mandat L7 (skew+),
> une brique décorrélée à skew négatif ne qualifie pas — elle irait dans un book Sharpe, pas le book skew+.
