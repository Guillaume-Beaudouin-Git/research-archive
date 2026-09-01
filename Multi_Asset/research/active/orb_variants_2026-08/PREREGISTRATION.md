# Pré-enregistrement — Balayage exhaustif ORB (NQ), voisinage de la spec déployée

Date : 2026-08-27. Compte concerné : FTMO funded `<ACCOUNT_ID>`, sleeve `FU_ORB_RISK`.
Worktree : `claude/orb-variants`. Écrit AVANT toute exécution du moteur.

## 1. Question

La spec déployée (OR 30 min RTH, cassure au **touch**, pas de confirmation, sortie au close RTH,
pas de TP, pas de filtre) est-elle un point quelconque d'un **voisinage mort**, ou un choix
défendable dans un **voisinage vivant** ? On ne cherche pas le meilleur réglage — on couvre l'espace
et on lit la distribution des t.

## 2. Données

- Prix : `data/raw/NQ_1min_databento_2010-2026.parquet` (canonique, GLBX dbn.zst), colonnes
  `open/high/low/close/volume/symbol/is_roll_day/is_rth`, index `timestamp_utc` tz-aware UTC.
  **Vérifié au tick** : les bornes RTH (`is_rth`) tombent à 13:30 UTC l'été (2694 jours) et 14:30 UTC
  l'hiver (1411 jours) = 9:30 ET exact, DST correctement géré à la source (pas de nom de champ à
  vérifier, L52 — confirmé, pas une hypothèse).
- **L60 (fourchette nulle)** : fraction de barres `high==low` = **0.09 %** sur le sous-ensemble RTH
  (0.0009), 6.6 % sur l'ensemble (nuit incluse, illiquidité normale hors session). Négligeable :
  ce n'est PAS un print de règlement façon XPT/XPD (L60), c'est un futur CME liquide. Continuer.
- Range : 2010-06-07 → 2026-05-29 (borne haute = fin du parquet), pour rester comparable au ledger
  figé (2010-06→2026-05, N=4013).
- VIX : `data/panels/vix.csv` (2007-2026, daily close, colonne `^VIX`) — pas de VXN dans le dépôt.
- FOMC : `data/personal_book/post_fomc_drift/data_cache/fomc_events.csv` (183 dates, 2004-2026).
- Jours fériés : **pas de calendrier externe disponible** (`pandas_market_calendars` absent de
  l'environnement). Opérationnalisation data-driven : un jour RTH est "veille de férié" si le jour
  RTH suivant saute ≥1 jour ouvré (jour de semaine sans données RTH) ; "lendemain de férié" si le
  jour RTH précédent en a sauté un. Détecté directement dans la série de dates RTH, pas d'hypothèse
  externe.
- Gamma / flux d'options / OI / 0DTE : **recherché explicitement dans le dépôt, ABSENT.**
  `find` sur `*gamma*`, `*0dte*`, `*gex*` ne renvoie que `Crypto/research/active/vrp_short_gamma`
  (options crypto, sans rapport) et une fiche `alpha_hunt/promising/` non exploitée sur les
  straddles 0DTE SPY. **Aucun proxy n'est fabriqué.** C'est une réponse en soi (§7) et une piste
  données-payantes à consigner (CBOE DataShop / OptionMetrics / SqueezeMetrics GEX, aucun n'est
  dans le dépôt ni gratuit).

## 3. Coût

0.962 bps RT (mesuré, fenêtre ORB, US100 CFD — donné, pas re-mesuré). Converti **par trade** :
`cost_R = entry_price * 0.962e-4 / |entry_price - stop_price|`. Jamais un levier médian fixe
(contrainte #2). Gross d'abord (coût=0), puis net.

## 4. Reconstruction depuis le M1 (pas depuis le ledger figé)

- Fuseau : conversion `timestamp_utc` → America/New_York (gère le DST automatiquement, pas de
  table figée). Jour RTH = date ET du jour où 09:30–16:00 ET a des barres.
- OR "RTH" : fenêtre [09:30 ET, 09:30+durée).
- OR "Globex" : fenêtre [reprise 18:00 ET du jour précédent, +durée). Reprise détectée dans la
  donnée (première barre à 18:00:00 ET après la pause de règlement), pas supposée.
- Chemin de surveillance post-OR : barres RTH ré-échantillonnées en **5 min** (aligné sur la
  granularité déjà utilisée par le ledger figé — `bi`, `ttb_5min` — choix de reproductibilité, pas
  d'optimisation), du **premier bar 5 min qui commence après la fin de la fenêtre OR** jusqu'à la
  clôture RTH 16:00 ET. Le type d'ouverture (RTH/Globex) ne change QUE la mesure de l'OR ; la
  fenêtre de surveillance et la sortie par défaut restent la session RTH du jour (choix de design
  explicite, documenté comme tel — une variante "sortie sur clôture Globex" n'est PAS couverte,
  §9).
- Cassure "touch" : `high` (long) / `low` (short) de la barre 5 min franchit `level ± marge`.
  Entrée au niveau exact (comme le ledger figé — idéalisation d'entrée déjà auditée bonne, gap
  d'entrée 0.27 %, PAS re-testée ici).
- Cassure "close" : `close` de la barre 5 min franchit `level ± marge`. Entrée au close de cette
  barre.
- ATR14 : ATR quotidien classique (Wilder, 14 jours) sur OHLC RTH quotidien, décalé T-1 (le jour
  courant n'entre jamais dans son propre ATR — signal à T-1, calcul à T-1).

## 5. Grille — conception **OFAT (one-factor-at-a-time) depuis un point d'ancrage**, pas factorielle
complète (l'espace complet ferait ~2 268 cellules pour 6 axes croisés ; **largeur des axes >
finesse des paramètres** est respectée en couvrant 6 axes à valeurs rondes, la profondeur
factorielle croisée est explicitement dans les "non couvertes", §9). L'ancrage = la spec déployée :
`RTH, 30 min, touch, marge 0, immédiat, aucun filtre, sortie close RTH`.

| Axe | Valeurs (rondes, pas optimisées) | # cellules |
|---|---|---|
| 1. Fenêtre OR | {RTH,Globex} × {15,30,60 min} | 6 |
| 2. Durcissement cassure | {touch,close} × marge {0, ¼ATR14, ½ATR14} | 6 |
| 3. Confirmation | immédiat · clôture de barre 5min · 2 barres 5min au-dessus · repli-retest | 4 |
| 4. Filtre largeur/vol | aucun · OR>médiane glissante 60j · OR terctile haut (60j) · OR/ATR14>1.0 · ATR14 pctile haut (252j) · ATR14 pctile bas (252j) · VIX tertile haut · VIX tertile bas | 8 |
| 5. Sortie | close RTH · time-stop 12:00 ET · time-stop 11:00 ET · TP 1R · TP 1.5R · TP 2R · stop à mi-OR · trailing ATR (chandelier 1×ATR14) | 8 |
| 6. Calendrier | aucun · exclure FOMC · exclure FOMC±1j · lundi seul · mardi seul · mercredi seul · jeudi seul · vendredi seul · exclure veille-férié · exclure lendemain-férié | 10 |

Total brut = 42 lignes, **ancrage compté une fois par axe → dédoublonné à 37 variantes uniques**
(l'ancrage apparaît 6 fois, retiré 5 fois). **Δn_tests = 37** (comptées comme configurations
neuves, règle du ledger : "if swapping it could have been the winner, it counts").

Chaque variante est rapportée : two-sided combiné, jambe longue seule, jambe courte seule (L25),
× 4 tranches de régime (2010-13, 2014-17, 2018-21, 2022-26), gross et net.

## 6. Sizing (axe demandé, L61)

**Non couvert par calcul dans cette grille.** L61 exige qu'un sizing dépendant du chemin
(pyramide, échelonné) soit comparé à un **placebo de construction identique** — faute de quoi on
fabrique du t positif sur du bruit pur (mesuré : 18/18 cellules >2.5, gross 2.91 bps, t+4.81 sur
bruit pur). Construire cette paire (variante + placebo identique) pour un axe entier est un travail
séparé, pas une case de plus dans cette grille. Documenté comme lacune explicite (§9), pas
fabriqué.

## 7. Statistiques

- HAC Newey-West lag-6 (`statsmodels`, `cov_type='HAC', cov_kwds={'maxlags':6}`), OLS R ~ const.
- Block bootstrap (Politis-Romano, bloc ≈ 20 jours de trading) pour IC95 de la moyenne, 2000 tirages.
- **Placebo de direction** : pour chaque variante, ~50 tirages où la direction du trade (long/short)
  est retirée du breakout réel et re-tirée à pile-ou-face (mêmes niveaux d'entrée/stop/sortie,
  même jour) → distribution de t sous H0 "la cassure ne prédit rien, seul le fait d'être exposé au
  NQ compte". Compare le t réel à cette distribution — cible directement le piège bêta (faiblesse
  #2 de la mission).
- **Placebo calendaire apparié** (axe 6 uniquement, style L49) : pour FOMC et pour chaque
  jour-de-semaine, ~500 tirages d'un même NOMBRE de jours choisis au hasard (pas seulement
  inconditionnel — apparié en compte), compare la stat réelle au percentile placebo.
- **Comparateur au max sous H0** : sur les 37 variantes, ~50 répétitions du placebo de direction
  donnent une distribution empirique de `max(|t_placebo|)` sur 37 tirages : le t max RÉEL est
  comparé à cette distribution (pas à N(0,1) théorique, qui suppose l'indépendance — ici les 37
  variantes sont corrélées par construction OFAT, donc le maximum empirique corrélé est le bon
  comparateur).
- Correction multiple : Šidák sur Δn=37 pour ce sprint (`α_variante = 1-(1-0.05)^(1/37) ≈ 0.00139`,
  seuil |t| ≈ 3.20) ; et sur le cumul déclaré n=1867 (MR intraday ~1454 + momentum 341 + reliquat) +
  37 = **1904**, seuil bien plus strict (|t| ≈ 4.0+), rapporté pour mémoire.
- Walk-forward ≥5 folds (expanding) **uniquement pour toute variante qui passe le kill-rule** (§8) —
  pas pour les 37 cellules brutes, ce serait 185 folds pour rien sur des cellules mortes.

## 8. Règle de kill (fixée avant calcul, pas ajustée après lecture des résultats)

Une variante est déclarée **"vivante"** (candidate à re-remplacer la spec déployée) SEULEMENT SI
TOUTES les conditions suivantes tiennent :
1. `|t_HAC net, two-sided, full-sample| > 3.20` (Šidák Δn=37) ;
2. le signe est le MÊME dans **≥3 des 4 tranches de régime** (pas seulement 2022-26 — sinon c'est
   la même concentration sous un autre nom, contrainte #5) ;
3. la jambe longue ET la jambe courte ont, **chacune**, un t net de même signe que le combiné
   (pas nécessairement significatif seule, mais pas de signe opposé — sinon piège bêta, L25) ;
4. le t réel dépasse le 95e percentile de la distribution placebo de direction (§7).

Toute variante qui échoue 1 est déjà notée `dead`. Le rapport final classe **DEDANS ou DEHORS**
selon ces 4 règles, écrites ici avant de voir un seul chiffre.

## 9. Variantes explicitement NON couvertes (à lister aussi dans le rapport final)

- Croisement factoriel complet des 6 axes (2 268 cellules) — seulement OFAT depuis l'ancrage.
- Sortie sur session Globex (au lieu de RTH close) quand l'OR est mesuré en Globex.
- Sizing dépendant du chemin (pyramide/échelonné) — nécessite placebo dédié (L61), non fait ici.
- Gamma/flux d'options/OI/0DTE — donnée absente du dépôt, non fabriquée (§2).
- VXN (vol implicite spécifique Nasdaq) — absent du dépôt ; VIX (S&P) utilisé comme proxy imparfait.
- Repli-retest à profondeur variable (seul un retest "au niveau exact" est testé, pas ¼/½ ATR de
  profondeur de repli).
- Trailing stop à des multiples d'ATR autres que 1× (0.5×, 1.5×, 2× non testés).
- Sizing conditionnel au régime / vol-targeting dynamique intra-sleeve (hors périmètre : c'est du
  sizing, cf. ci-dessus).
- FOMC intraday (heure exacte de l'annonce 14:00 ET) — seul le jour calendaire est testé, pas une
  fenêtre horaire de blackout intraday.

## 10. Sortie attendue

`grille_resultats.csv` (37 lignes × colonnes par jambe × par tranche, gross+net), `RAPPORT.md`
(distribution des t, comparateur H0, position de la spec déployée dans la distribution, verdict
DEDANS/DEHORS par variante selon §8, liste des non-couvertes ci-dessus reprise telle quelle).
