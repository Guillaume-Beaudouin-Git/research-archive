# PRÉ-REGISTRATION — nightly US100 : variance, ou book devenu mono-sleeve ?

> Figée 2026-07-14 AVANT tout résultat. Compte armé <ACCOUNT_ID> (equity ~$9,238, ~$238 du floor
> $9,000). **LECTURE SEULE sur le live. Aucune action live.** Moteur audité (cleanroom) réutilisé,
> JAMAIS muté. Author≠auditor : l'analyse (auteur) sera auditée indépendamment avant le verdict.
> Ce contrat lie l'analyse : toute déviation = amendement daté, pas de ré-écriture silencieuse.

## 1. Le fait à expliquer
Deux pertes majeures consécutives sur la sleeve nightly US100, toutes deux flattées par le breaker M5 :
- **06/07 22:05 → 07/07 02:15** : US100 BUY 2.83 lots → breaker_flat, −$354.14 (~$84k notionnel).
- **13/07 22:05 → 14/07 01:45** : US100 BUY 2.97 lots → breaker_flat, −$402.65.
Equity 10000 → 9641 → 9238. Profil identique : ouverte au rebalance 22:05 d'un **lundi** (jour ON),
dérive nocturne, breaker en pleine nuit (marché US actif, pas de gap).

## 2. Hypothèses (mutuellement exclusives au niveau du verdict)
- **H0 — variance normale.** Les 2 pertes sont dans la distribution attendue du nightly US100. N=2
  ne prouve rien. Verdict (a) = ne rien faire. **PARFAITEMENT ACCEPTABLE.**
- **Hb1 — le nightly a un problème INTRINSÈQUE** (indépendant du nombre de sleeves) : queue épaisse,
  Sharpe insuffisant, ou breaker inadapté à la dérive overnight.
- **Hb2 — concentration mono-sleeve (hypothèse prioritaire).** Depuis le déploiement du gate J1
  (2026-07-03) : J1 gaté à 0 (USD/JPY en zone), or plat (signal 0), **et GER40 skippé les lundis**
  (bug STALE, corrigé 2026-07-14). Le book ne porte plus QUE l'US100 certaines nuits ON. Le sizing
  nightly (on_w=0.6, vm=14 → 8.4×) a été calibré (vm-sweep) sur le book DIVERSIFIÉ (4 jambes ρ~0) ;
  en mono-sleeve il porte seul tout le risque, et le cap de marge peut REDISTRIBUER le budget libéré
  vers l'US100 (uncapping → position plus grosse). Effet de bord du gate (nécessaire), pas du nightly.

Distinguer Hb1 (« le nightly est cassé ») de Hb2 (« le book a perdu sa diversification et l'US100
est sur-sizé/dé-cappé en mono-sleeve ») est le cœur du livrable.

## 3. Données & outils (tous LECTURE SEULE, chemins absolus depuis le main dir)
- Moteur MC audité (NON muté) : `/Users/…/Algo_claude/data/ftmo_portfolio/audit_v2_independent/cleanroom/engine.py`
  (build_signals vol-targeté ; _target_for_segment `tgt=on_w·scale·eq`, scale=vm·taper·glide·pace ;
  breaker `lim+0.30·DAILY_BUDGET` ; margin cap Σ|notionnel|·rate ≤ 60% eq ; CFG_V2 vm=14 on_w=0.6).
- Moteur M5/M1 tail audité : `…/data/ftmo_portfolio/real_metrics_2026-07/lowcheck_engine.py`.
- Fills réels (vérité terrain) : VPS `MQL5/Files/fills.csv` (40 fills 2026-06-17→07-14, 1 compte ;
  US100×25, USDJPY×10, GER40×5, gold×0). Comptes 1-2 antérieurs : archivés si dispo (sinon N limité).
- Prix minute US100 pour le replay : `…/data/deep_history_utc/US100_M1.csv` (réparé).
- Caches book (gitignored, main dir) : `…/data/ftmo_portfolio/cache/`.

## 4. Volets, tests, et SEUILS pré-spécifiés (kill-rules)

### Volet 0 — le book est-il mono-sleeve de facto ? (priorité)
- **M0a** : fraction des nuits ON depuis 2026-07-03 où l'US100 est la SEULE jambe overnight active
  (GER40+J1+gold tous absents/0), reconstruite des fills réels. *Descriptif.*
- **M0b** : levier/notionnel US100 réalisé quand SEUL vs quand ≥2 jambes. **Seuil : median(lev|seul)
  ≥ 1.5× median(lev|partagé)** ⇒ US100 matériellement plus gros seul (uncapping/redistribution marge).
- **M0c** : vol quotidienne & maxDD du book, MC-conditionné « régime mono-sleeve » (J1 suspendu +
  or plat + GER40-lundi-skippé) vs « book complet diversifié ». **Seuils : vol_mono ≥ 1.3× vol_div
  ET Δp(pass) ≥ 5 pts** ⇒ perte de diversification matérielle.

### Volet 1 — les 2 pertes sont-elles dans la distribution attendue ?
- Distribution MC (moteur audité, ~13 ans) des PnL quotidiens de la jambe nightly US100 : μ, σ,
  quantiles, pire jour, fréquence < −$300.
- Percentile de −$354 et −$402. Corps (p10–p25) vs queue (p1–p5).
- **K1a (fréquence)** : P(≥2 pertes nightly ≥$350 en 2 entrées ON consécutives | MC, conditionné au
  régime mono-sleeve). **≥10% ⇒ variance banale ; <1% ⇒ le modèle ne colle pas au live** (chercher un
  écart d'implémentation).
- **K1b — TEST DÉCISIF (replay chemin réel)** : rejouer la position du moteur sur le chemin M1 US100
  RÉEL des nuits 06-07/07 et 13-14/07. **|perte_sim − perte_réelle| ≤ 25% de la réelle ⇒ perte
  expliquée par (chemin × taille), pas de bug d'implémentation** → la question devient « la TAILLE
  était-elle correcte » (Volet 0/2). **perte_réelle > 1.5× perte_sim ⇒ écart d'exécution** (slippage/
  timing/sizing) à localiser.

### Volet 2 — le sizing/breaker overnight est-il sain ?
- Levier nominal prévu : on_w·vm = 0.6·14 = 8.4× (confirmé design, pas dérive) — le vérifier sur les
  positions réelles (2.83/2.97 lots).
- Distribution MC du levier nightly US100 réalisé : **8.4× est-il la médiane ou une queue ?** Rapporter
  médiane + p95. **Flag si le levier des 2 pertes > p90** (⇒ les pertes coïncident avec des nuits
  haut-levier — lien Volet 0 uncapping).
- **Breaker** : sur le chemin M1 réel, a-t-il flatté près de sa ligne ou dépassé ? **exit ≤ 1.2×
  perte-ligne ⇒ efficace (US100 continu, pas de gap, contrairement à J1) ; dépassement > 1.5× ⇒
  breaker inadapté à la dérive overnight.**

### Volet 3 — PnL réel du nightly US100
- PnL cumulé réel de la jambe nightly (fills réels, ce compte + comptes archivés si dispo) : entrées,
  gagnantes/perdantes, net. Comparer au PnL MC attendu sur le même nombre d'entrées. **CI, N petit,
  descriptif — pas de kill-rule, pas de surinterprétation.**

### Volet 4 — SI (b) : mécanisme + remède chiffrés
- Localiser le mécanisme précis (uncapping mono-sleeve ? queue intrinsèque ? coûts ? breaker ?).
- Overlay candidat (chiffré Δbust/ΔEV comme gate J1 / LCAP8) : **sizing adaptatif au nombre de sleeves
  actives** (à risque de portefeuille égal, un book mono-sleeve doit porter MOINS de levier — ex.
  vm_eff = vm·f(n_active)). Alternatives : cap levier nightly, réduction on_w, gate régime-vol.
- **⚠️ on_w est une CONSTANTE COMPILÉE dans l'EA GELÉ (`OnWEff()`, book_executor.mq5:163)** → toute
  modif = nouvelle version EA (recompile, nouveau sha, chaîne régénérée). **SIGNALER, ne pas trancher.**
- Rappel funded : les gates ciblés ÉCHOUAIENT, seul le sizing marchait (tester si idem ici).

## 5. Matrice de décision (pré-spécifiée)
- **(a) VARIANCE — ne rien faire** SI : K1a ≥10% ET K1b reproduit les pertes (≤25%) ET M0b <1.5× ET
  M0c vol-ratio <1.3× ET pertes dans le corps MC (levier ≤ p90, PnL ≥ p5).
- **(b2) CONCENTRATION MONO-SLEEVE** SI : M0b ≥1.5× (US100 dé-cappé plus gros seul) OU (M0c vol-ratio
  ≥1.3× ET Δp(pass) ≥5 pts), ET les 2 pertes coïncident avec des nuits mono-sleeve haut-levier (Volet 2
  > p90). Remède : sizing sleeve-adaptatif (Volet 4). Note : le fix monday_restamp (2026-07-14) restaure
  déjà GER40 les lundis → atténue partiellement (2 jambes overnight au lieu d'1) — le quantifier.
- **(b1) NIGHTLY INTRINSÈQUE** SI : la jambe nightly du book DIVERSIFIÉ a déjà queue/Sharpe hors gate
  (p1 loss > capacité breaker, ou Sharpe nightly < seuil) indépendamment du nombre de sleeves.
Les verdicts (b) ne sont PAS exclusifs entre eux dans le diagnostic ; le verdict FINAL nomme le
mécanisme DOMINANT chiffré.

## 6. Garde-fous
- LECTURE SEULE live ; worktree dédié `claude/nightly-us100-investigation` ; moteur cleanroom + lowcheck
  importés du main dir par chemin absolu, jamais mutés ; aucune écriture VPS/targets/crontab.
- **Author≠auditor** : audit indépendant (session fraîche) du respect de cette pré-reg + des chiffres +
  du verdict, AVANT de conclure.
- **Anti-biais de confirmation** : un verdict (a) est un succès si les chiffres y mènent. Ne PAS
  « trouver » un problème. Les seuils ci-dessus sont gelés ; tout ajustement post-résultat = invalidation.
- Séparer DONNÉES (rétrospectif, ce qui s'est passé) et JUGEMENT (prospectif, ce qu'il faut faire).
- N=2 : la fréquence (K1a) et le replay (K1b) tranchent, pas les 2 points bruts.

## 7. Précisions (2026-07-14, AVANT résultats — sharpening ; seuils §4/§5 INCHANGÉS)
- **K1b décomposition taille × chemin.** Rejouer le sim avec la taille RÉELLE (2.83/2.97 lots) ET la
  taille nominale (~1.3 lots). L'écart nominal→réel relève de Hb2 (sizing), PAS d'un bug. Un écart de
  CHEMIN/exécution ne se lit qu'à taille ÉGALE (réel vs réel). Rapporter les deux effets séparément.
- **Mécanisme précis Hb2 = binding du CAP DE MARGE 60%.** Tester explicitement si le clip de marge
  BINDAIT les nuits partagées (autres jambes consomment la marge → US100 bridé) et PAS les nuits
  mono-sleeve (US100 seul → cap ne bride rien → US100 récupère toute la marge → gonflé). M0b MESURE
  l'effet ; ce test en établit la CAUSE. Méthode : invoquer la logique de cap du moteur audité
  (non mutée) sur les 2 régimes à equity réelle, comparer US100 pré/post-cap.
- **Volet 4 — effet du monday_restamp (déployé 2026-07-14).** Dès le 20/07, GER40 entre les lundis →
  lundis plus mono-sleeve → US100 re-bridé par le cap. Le fix GER40 corrige donc PARTIELLEMENT le
  sur-sizing (effet non conçu pour). Quantifier : taille US100 attendue les lundis post-restamp ;
  suffit-elle, ou remède sizing encore nécessaire (J1 reste gaté → book 2-3 jambes, pas 4) ?

## 8. Amendement daté (2026-07-15, APRÈS Volet 0/1/1b) — déviation de méthode K1b, seuils INCHANGÉS
- **Mur de données.** Le M1 canonique `data/deep_history_utc/US100_M1.csv` s'arrête **2026-06-05**,
  idem le cache `sim_m5[_repaired].parquet` → **le chemin M1 intra-nuit des nuits 06-07/07 et
  13-14/07 n'est PAS local** (il ne vit que sur le VPS MT5 live). Le pré-reg §4 K1b demandait un
  replay barre-à-barre M1 ; impossible sans toucher au live au-delà de la lecture des fills/state.
- **Méthode retenue (équivalent-endpoint, décisif pour le MÊME test).** Les fills réels donnent les
  bornes EXACTES (entrée + sortie breaker, slip ≤0.14 bps) et `state.json` donne les ancres de
  risque EXACTES de la nuit 2 (anchor_balance, breaker_line, governor.scale). Le test d'écart
  d'implémentation (K1b : |recon − réel| ≤ 25%) et la décomposition taille×chemin se calculent
  intégralement de cette vérité terrain. L'overshoot breaker se lit sur l'ancre exacte (N2) plutôt
  que sur le chemin M1. **Le seuil K1b (25%) et la logique §4/§5 sont INCHANGÉS** ; seule la SOURCE
  du chemin change (endpoints réels au lieu des barres M1). Nuit 1 : ancre inférée (~reset $10k),
  gouverneur supposé baseline vm14 — le test exécution/taille reste robuste (fills exacts).
- **Dette infra notée (séparée du verdict).** (i) `fills.csv` n'est pas un registre de positions
  fiable (manque des closes, chevauche le reset 06/24 — Volet 0). (ii) Le chemin M1 US100 post-06/05
  n'est pas rapatrié du VPS → tout replay intra-nuit futur exige un pull M1 read-only du VPS. Ces
  deux points sont de la dette d'infrastructure d'audit, pas des findings de la stratégie.
