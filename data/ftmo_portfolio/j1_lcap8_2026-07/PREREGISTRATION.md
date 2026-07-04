# PRE-REGISTRATION — LCAP8 (cap de levier J1) sur chaîne régénérée + fenêtre étendue

**FROZEN before results.** 2026-07-04. Worktree `claude/j1-intervention-suspend`. Auteur ≠ auditeur
(sous-agent indépendant sur le résultat). Complément du gate (suspension en zone) : le gate coupe
J1 EN zone (USDJPY≥160) ; LCAP8 borne le levier de J1 QUAND il trade (hors zone). Complémentaires.

## Contexte & discipline (modif EA = recompute intégral)
LCAP8 = cap `|notional_J1|/eq ≤ 8×` appliqué à la cible 22:05 (pré-margin-cap). En LIVE c'est une
modif de l'EA GELÉ (le cap doit s'appliquer sur l'equity EA au fill) → recompile → **nouveau sha
EA documenté** + re-dépôt chaîne (yaml/mqh inchangés ; seul l'EA change). L'ÉTUDE modélise le cap
dans le sim via le hook `cfg["j1_lev_cap"]` de la levcap study (EQUIV-validé 462/462 quand inerte).
La levcap study (dbb9a61) a déjà mesuré LCAP8 sur v2.2 (Δp −1.5 ns / ΔEV +$1.3, pire gap −60 %) ;
ici on **régénère sur la chaîne courante v2.2.1** + fenêtre étendue + on traite le mode de
défaillance du sim.

## Décisions gelées (justifiées AVANT résultats)

### D1 — Baseline
Chaîne EQUIV-87.01 (moteur cleanroom + config_v22, marge POLICY), IDENTIQUE au gate study →
comparabilité directe gate vs LCAP8. **Caveat SWING** : le compte live est SWING (marge XAU 1/9,
JPY 1/30…) ; la mémoire situe p(pass) SWING ~71.4 (−15.6pt vs policy). On reporte le coût LCAP8 sur
POLICY (canonique) ET, si tractable, sur les taux SWING (`MARGIN_RATES_SWING`) — le Δ (coût du cap)
est ce qui compte, robuste au niveau absolu.

### D2 — Fenêtre étendue (06-05 → 07-04)
Fetch Dukascopy USDJPY (+ XAU/US100/GER40 si tractable) M5 06-05→07-04, rebuild panels. **Honnêteté
gelée** : étendre le MC canonique M5-CLOSE à 07-04 ajoute ~4 cohorts et **NE capture PAS les flashs**
(cf. D3) → valeur faible pour le coût (immatériel), fait pour complétude. La capture des flashs
02/07-03/07 vit dans la sensibilité intra-barre (D3), pas dans le MC M5-close.

### D3 — Mode de défaillance du sim (RÉPONSE à la question ouverte)
**Constat (donnée) :** le sim est M5-CLOSE (`sim_m5.parquet` = 1 prix/barre = close ; bust testé au
close de barre). Le 02/07 : barre 06:45→06:50, close 161.795 → eq $9,477 > floor $9,427 → le sim
enregistre une **SURVIE**, alors que FTMO a liquidé en continu à 161.717 intra-barre (eq $9,393 <
floor). **Le sim sous-estime le tail d'intervention.**
**Peut-on le corriger ? OUI, partiellement, et c'est le bon modèle :** tester le bust contre le
**LOW intra-barre M5** (extrême adverse pour un long) est un détecteur de bust CORRECT (bust ssi
eq(low) < floor ⇒ l'equity a franchi le floor dans la barre ⇒ FTMO a liquidé). Le LOW M5 capture le
02/07 (low 161.501 → eq ~$9,393 < floor → BUST). Limite honnête : le LOW M5 reste plus grossier que
la liquidation tick-continue (prix de liq ≈ floor, pas le low) → il **détecte** correctement le bust
mais peut **sur-estimer la perte** ; et il ne modélise pas un flash sous-M5 qui se recouvre (rare).
**Implémentation gelée :** sensibilité SÉPARÉE (ne PAS muter le moteur canonique — sinon tout le
87.01 bouge). Fetch M5 OHLC (low) pour USDJPY sur (a) les jours de flash réels 02/07-03/07 (données
étendues D2) et (b) un échantillon de jours haut-vol historiques (BoJ 2022/2024, Grexit, SVB).
Re-check bust intra-barre-low : baseline vs LCAP8 vs suspension. Reporter combien de jours basculent
survie→bust sous la sémantique intra-barre, et si LCAP8/suspension les évitent.
**Si non tractable en full-history :** documenter que LCAP8 reste un overlay de risque comme le gate,
justifié par l'arithmétique du notionnel (16.8× → −0.5 yen tue le compte), pas par un edge MC.

## Arms (FROZEN)
1. **equiv** — clone == engine_v22.run_funnel (EQUIV 87.01, sinon STOP).
2. **baseline** — WT inchangé.
3. **LCAP8** — `cfg["j1_lev_cap"]=8.0` (hook levcap).
4. (report only) **LCAP10/12** — sensibilité, comme levcap (pas des candidats concurrents).
Marge : POLICY (canonique) + SWING (réalisme live) si le rebuild SWING est tractable.

## Métriques (par arm)
- **Triplet** : p_pooled/IS/OOS, attempts, EV (VAL=$1,422, FEE=$96).
- **Queue gauche (PRIMARY)** : pire jour J1, pire gap week-end (M5-close, canonique) ; **+ bust
  intra-barre-low** (D3) sur les jours flash + échantillon haut-vol ; levier J1 réalisé median/p95/max,
  frac >15× / >20× (le cap doit mordre).
- **Arithmétique du tail (prospectif)** : perte J1 par gap −0.5/−1/−2/−3 yen à 16.8× vs 8× vs
  suspendu, vs floors ($500 daily / $1000 static). Réplique du breach.
- **Δ appariés vs baseline** : Δp, ΔEV, Δbust, Δgap — CI 90 % bootstrap bloc circulaire
  (blocs=10, 3000, seed=23).

## Règle de décision (FROZEN, asymétrique — overlay de risque)
LCAP8 **ADOPTÉ** ssi : (1) coût abordable — Δp CI90 ≥ −2.0 pts ET ΔEV CI90 ≥ −$40 (idem gate/levcap) ;
ET (2) réduction de tail matérielle — pire gap réduit (M5-close) OU bust intra-barre-low réduit sur
les jours flash. La protection prospective (arithmétique notionnel) est reportée quel que soit le
verdict MC. **Complémentarité gate×LCAP8** évaluée explicitement : le gate protège EN zone, LCAP8
HORS zone à la reprise — quantifier le recouvrement (les jours LCAP8-utiles sont-ils déjà couverts
par le gate ?).

## Comptabilité
+3 arms (equiv/baseline/LCAP8) + LCAP10/12 report. 1 règle fixe, seuils gelés. Overlay de risque
(pas alpha). Author≠auditor sur le résultat. **FROZEN. Modif post-résultats = invalidation.**
