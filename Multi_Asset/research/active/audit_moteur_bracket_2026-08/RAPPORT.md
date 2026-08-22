# Audit du biais de moteur — départage intra-barre pessimiste — RAPPORT

**Date:** 2026-08-21. **Isolation:** shared main working dir, zero git HEAD operations, branch
stays `claude/book-idle-escalation`. Interpreter: `/usr/bin/python3`. Writes confined to this
folder; no engine and no other study's files were modified (only read/imported).

---

## Synthèse (12 lignes)

Le biais existe, est mesuré, et **est éliminable** : au point le plus tendu de l'abaque
(bracket 1.0×ATR, hold 8 barres — exactement la cellule canonique du programme MR), le
départage pessimiste vaut **jusqu'à −2.2 bps/trade sur donnée synthétique fat-tail** mais
seulement **−0.3 à −0.4 bps/trade mesuré directement sur données réelles** (US100, XAUUSD) —
le marché réel dilue l'artefact d'un facteur ~6-7×. Le biais **s'effondre en largeur** (déjà
négligeable à 2×ATR) et **sature en durée** au-delà de ~6-8 barres. Un résolveur M1 (construit et
validé ici) **récupère 77-79 % du biais réel mesuré**, résidu 0.8 %-15 % selon l'instrument. **9
études candidates auditées** dans `inventaire_contamination.csv` : **1 exposition directe
confirmée** (`intraday_mr_ftmo`, cellule canonique exacte) dont **le verdict ne change pas**
(bias mesuré 100-1000× trop petit pour franchir les seuils de significativité concernés) ; le
corpus des **109 stratégies**, flagué comme le gisement le plus probable, s'avère **quasiment
immunisé** (0/1268-1434 ties mesurées, brackets 6×ATR daily vs le seuil dangereux ≤1.5×ATR) —
mais porte une **ambiguïté d'ENTRÉE distincte** (14.5 % des trades S001) non quantifiée ici. **0
verdict de stratégie ne bascule.** Sur l'ORB funded (chantier D) : **une session parallèle a déjà
mesuré et tué ce sleeve** (`orb_cost_funded_2026-08`, 2026-08-12/13, R2 fire à t=0.48 sous coût
mesuré 1.80bps) — ce n'est PAS un biais de départage intra-barre mais un **biais de véhicule**
(NQ simulé vs CFD exécuté) ; **le point le plus important de ce rapport est opérationnel** :
ce kill ne semble pas reflété dans les mémoires de session au 2026-08-12, à vérifier
d'urgence — ce sleeve porte la moitié de l'EV funded modélisée.

---

## 0. Contexte — ce qui a été établi avant ce rapport

`Multi_Asset/research/active/mr_intraday_grille_2026-08/RAPPORT.md` (lu intégralement en
préalable) a établi trois preuves : ordonnancement monotone sur la géométrie de sortie (bracket
serré → t plus négatif), marche aléatoire pure (t ∈ [−4.1, −1.4]), placebo à autocorrélation
appariée (0/450 positifs, t ≈ −4.2 à −5.2). Ce rapport instruit la **mesure quantitative**
(chantier A), le **résolveur** (chantier B), l'**inventaire de contamination** (chantier C) et
**l'ORB production** (chantier D).

**Découverte annexe faite en cours de route** : une session parallèle
(`Multi_Asset/research/active/mr_grille_suite_2026-08/`, gelée le même jour, PREREGISTRATION.md
§2) travaille EXACTEMENT sur le même problème (résolution M1 des brackets larges) et cite
explicitement ce dossier (`audit_moteur_bracket_2026-08/`) comme référence — vérifié absent à son
heure de gel. Ses résultats bruts (`axis_A_results.csv`) sont une **corroboration indépendante,
sur données réelles, des chantiers A et B** ci-dessous ; ils sont cités, pas dupliqués.

---

## A. Caractérisation du biais

### A.1 La règle, citée

`yt_strategy_replications/engine/backtest.py` :
- **Docstring, lignes 8-10** : *"Exit logic uses each bar's high/low. When both stop and target
  are touched inside the same bar the outcome is ambiguous at this resolution; we resolve it
  pessimistically (stop first) by default — the honest choice."*
- **Signature, ligne 51** (`run_backtest_vectorized`) et **ligne 138** (`run_backtest`, boucle
  bar-par-bar) : `sl_first_on_tie=True` par défaut, dans les DEUX implémentations (prouvées
  trade-for-trade équivalentes par `tests/test_engine.py`).
- **Résolution effective** : vectorisé, ligne 124 :
  `pick, off = ("sl", sidx) if sl_first_on_tie else ("tp", tidx)` (le cas `sidx == tidx`, les deux
  barrières touchées pour la première fois dans la MÊME barre) ; boucle, ligne 179 :
  `xp, xr, exited = (sl_px, "sl", True) if sl_first_on_tie else (tp_px, "tp", True)`.
- **Test dédié** : `tests/test_engine.py:38-44` (`test_stop_first_on_tie`) — construit une barre
  qui touche stop ET cible, vérifie que `reason == "sl"`.

### A.2 Méthode de décomposition (propre, sans deviner une règle "juste")

Pour isoler le biais SANS supposer de règle de résolution équitable : rejouer les MÊMES tirages
de prix et le MÊME signal deux fois, en ne changeant QUE `sl_first_on_tie` (True/False). Comme
l'indice de sortie d'une vraie égalité (`sidx == tidx`) ne dépend PAS du flag (`backtest.py:107-
124`), les deux runs produisent des trades **identiques** (même entry_time/exit_time) sauf sur les
barres ambiguës, où seuls `exit_px`/`reason` diffèrent. On construit alors :
`unbiased = 0.5×(ret_pessimiste + ret_optimiste)` sur les trades ambigus, `= ret_pessimiste`
ailleurs — exactement ce qu'un tirage à pile-ou-face 50/50 produirait en espérance.
`biais = pessimiste − unbiased`. Vérifié sur les 63×2 tirages : **0 désalignement** entry_time
(`n_draw_mismatch = 0` partout, `bias_surface_synthetic_fattail.py`).

### A.3 L'abaque — largeur × durée, données SANS contenu

`bias_surface_synthetic_fattail.py` → `abaque_biais.csv` (63 lignes). Génération : retours
log iid Gaussiens (zéro autocorrélation, zéro drift) + fourchette (high-low) **bootstrappée iid**
depuis la distribution RÉELLE d'US100 15-min (478k valeurs, queue grasse préservée, autocorrélation
détruite par le tirage iid) — c'est la lecture littérale de la méthode du rapport source ("zero
fat tails BEYOND the resampled bar-range distribution"). 12 tirages × 20 000 barres, largeurs
{0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0}×ATR, durées {2,3,4,6,8,12,16,24,32} barres.

| largeur (×ATR) | hold=4 | hold=8 | hold=16 | hold=32 | frac_tie @hold=8 |
|--:|--:|--:|--:|--:|--:|
| 0.5 | t=−27.04, −3.95bps | t=−27.18, −3.99bps | t=−27.19, −3.99bps | t=−27.19, −3.99bps | 18.0% |
| 0.75 | t=−11.70, −2.84bps | t=−11.81, −3.05bps | t=−11.92, −3.06bps | t=−11.93, −3.06bps | 9.2% |
| **1.0** | t=−5.82, −1.86bps | **t=−6.31, −2.20bps** | t=−6.53, −2.28bps | t=−6.56, −2.29bps | 5.0% |
| 1.25 | t=−2.73, −1.22bps | t=−3.95, −1.58bps | t=−3.98, −1.75bps | t=−3.90, −1.78bps | 2.9% |
| 1.5 | t=−1.76, −0.81bps | t=−2.40, −1.10bps | t=−2.55, −1.33bps | t=−2.88, −1.39bps | 1.7% |
| 2.0 | t=−1.07, −0.42bps | t=−0.93, −0.63bps | t=−0.63, −0.83bps | t=−0.35, −0.88bps | 0.7% |
| 3.0 | t=−0.33, −0.19bps | t=−0.37, −0.28bps | t=+0.91, −0.38bps | t=+0.50, −0.50bps | 0.2% |

(`bias_t`/`bias_bps` = pessimiste − unbiased ; `t_pessimistic` mêlé pour lecture directe.
CSV complet : toutes colonnes, N par cellule 8,000-25,000 trades pooled sur 12 tirages.)

**Lecture** : le biais est **monotone décroissant en largeur** (facteur ~10× entre 0.5× et 3.0×
ATR) et **sature en durée** au-delà de ~6-8 barres à largeur fixée (la queue de distribution qui
compte est celle de la barre de sortie elle-même, pas le nombre de barres qu'on autorise à
attendre). La cellule canonique du programme MR (**1.0×ATR, H=8**) tombe exactement au **milieu**
de cette pente — ni le pire cas ni un cas anodin.

**Robustesse — dépendance à la fatness de la queue** (`bias_surface_synthetic_thin_tail.py` →
`abaque_biais_synthetic_thin_tail.csv`, marche aléatoire GBM lissée intrabar, PAS de bootstrap de
fourchette réelle) : à la MÊME cellule (1.0×ATR, H=8), `frac_tie` tombe à **0.000** et `bias_t`
à **−0.03** — un ordre de grandeur en dessous. **Le biais n'est pas une propriété universelle du
random walk ; c'est une propriété de la fatness de la distribution de fourchette intrabar.** Une
marche gaussienne lisse le sous-estime radicalement ; du bootstrap de vraies barres (queue grasse
réelle) le fait apparaître à sa vraie taille. C'est pourquoi le rapport source insistait sur
"zero fat tails BEYOND the resampled bar-range distribution" — ce n'est pas un détail cosmétique.

**Confirmation sur placebo à autocorrélation appariée** (`bias_surface_placebo_confirm.py` →
`abaque_biais_placebo_confirm.csv`, réutilise en lecture seule `mr_intraday_grille_2026-08/
placebo.py::synthetic_frame`, block-shuffle mean=100, 9 instruments réels × 8 tirages) : même
forme qualitative (biais décroît avec la largeur — width=0.75→1.5, bias_t passe de −99 à −16), et
même ordre de grandeur de `frac_tie` (6.9-12.9 % vs 5.0-9.2 % sur le bootstrap synthétique).
⚠ **Découverte annexe, non résolue ici** : la référence "unbiased" sur ce placebo real-structure
ressort **franchement positive** (t +12 à +48), signe d'un **second mécanisme distinct** (probable
effet de sélection de l'ancre SMA20 sur une série encore auto-corrélée par le shuffle) qui
s'ajoute au biais de départage plutôt que de le neutraliser. Nommé, non gravé :
`sma-anchor-selection-effect-on-block-shuffled-placebo` — **hors scope de ce mandat**, à instruire
séparément (le pooling brut multi-instruments sans mise à l'échelle vol-target est aussi une
limite méthodologique de ce test de confirmation, à corriger avant toute conclusion ferme dessus).

**Corroboration indépendante, données réelles, 9 instruments** — `mr_grille_suite_2026-08/
axis_A_results.csv` (session parallèle, résolution M1, même cellule canonique) : à 1.0×ATR
M1-résolu, t va de −3.87 (USDJPY) à +1.06 (XAUUSD), moyenne ≈ **−0.2** — à comparer au **−1.25**
(moyenne, 9 instruments, résolution 15-min) rapporté par l'étude source. La résolution M1 rapproche
la moyenne réelle de zéro d'environ **1 point de t**, cohérent avec le chantier B ci-dessous.

---

## B. Le résolveur

### B.0 Vérification du fuseau (préalable obligatoire, L52/L56)

**Test de falsification appliqué** (indépendant de celui déjà logué par
`mr_timezone_repair_2026-08`/`gross_surface_map_2026-08`) : l'heure de pic de volume d'US100 doit
se décaler d'1h entre janvier et juillet si `timestamp_utc` est du VRAI UTC (l'ouverture cash US à
9:30 ET tombe à 14:30 UTC en hiver EST, 13:30 UTC en été EDT). **Mesuré** : pic janvier = heure 15
UTC, pic juillet = heure 14 UTC — décalage exact d'1h dans le bon sens. **[V] Confirmé.** Une
série mal étiquetée en heure locale fixe n'aurait montré AUCUN décalage saisonnier.

### B.1 Le résolveur (`m1_resolver.py`)

Pour toute barre 15-min ambiguë (identifiée par la même méthode qu'en A.2), on découpe la fenêtre
`[bar_start, bar_start+15min)` dans le M1 canonique et on avance minute par minute : la première
minute qui touche `sl_px` OU `tp_px` détermine la sortie. Si une MÊME minute touche les deux
(ambiguïté résiduelle, irréductible à cette granularité), repli sur le départage pessimiste,
**comptabilisé séparément, jamais masqué** (`frac_m1_still_ambiguous`).

### B.2 Résultats

| expérience | n_trades | n_ties | frac_tie | frac_m1_still_ambig | t_pessimiste | t_M1_résolu | t_référence_non_biaisée | biais AVANT (bps) | biais APRÈS (bps) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| B1 synthétique (M1 iid + fourchette M1 bootstrappée réelle) | 14,854 | 28 | 0.19% | **78.6%** ⚠ | −0.835 | −0.748 | −0.596 | −0.0349 | −0.0224 |
| B2 réel — **US100** | 7,432 | 121 | 1.63% | **0.83%** | −2.188 | −1.355 | −1.120 | −0.3673 | **−0.0836** |
| B2 réel — **XAUUSD** | 13,653 | 214 | 1.57% | **15.42%** | −1.426 | −0.229 | +0.097 | −0.2751 | **−0.0587** |

**Lecture** : sur données réelles, le résolveur M1 récupère **77 %** (US100) et **79 %**
(XAUUSD) du biais mesuré, laissant un résidu petit (US100) à modéré (XAUUSD, plus volatil,
nécessitant parfois une granularité plus fine que la minute). ⚠ **Limite honnête sur B1** : le
générateur synthétique M1 utilise la même approximation corps+mèche (symétrique, sans vrai
chemin intra-minute) qu'ailleurs dans le dépôt — un "tie" au sein d'une SEULE barre M1 synthétique
ne porte donc quasiment aucune information réelle sur l'ordre des touches, d'où le taux
`frac_m1_still_ambiguous` de 78.6% qui est un artefact de construction, pas un fait de marché.
**Le test décisif est B2 (données réelles)**, pas B1.

**Corroboration indépendante** : `mr_grille_suite_2026-08/PREREGISTRATION.md` §2 documente le même
résolveur (marche minute par minute sur le M1 session-filtré, repli stop-first uniquement sur
égalité stricte à la minute) et rapporte les mêmes ordres de grandeur de récupération (§A.3
ci-dessus). Deux implémentations indépendantes, même conclusion.

---

## C. Inventaire de contamination

Fichier complet : `inventaire_contamination.csv` (13 études auditées). Méthode : identifier chaque
étude import(ant) un moteur à bracket ATR (`grep` ciblé sur `sl_dist`/`tp_dist`/`sl_pct`/
`run_backtest`/`sl_first_on_tie`), lire sa largeur/durée réelles, appliquer l'abaque du chantier A,
et statuer sur un renversement de verdict.

### C.1 Exposition confirmée — `yt_strategy_replications/intraday_mr_ftmo`
**La cellule canonique EXACTE** (`s_sl=s_tp=1.0×ATR, H=8` — `signals.py:32-33`,
`run_robustness.py:56-58`) — c'est l'ancêtre direct du programme MR, cité par le rapport source
comme ayant "silently sat inside" ce biais. Verdict original : **FALSIFIÉ** (aucun edge MR
two-sided net-tradable ; le seul cas positif, US500-long SR+2.20/DSR 0.63, est un piège bêta L25
tué par sa jambe short −0.87). **Verdict corrigé : INCHANGÉ.** Le biais RÉEL mesuré à cette
cellule exacte sur des instruments comparables (chantier B2, US100/XAUUSD) est de **0.3-0.4
bps/trade** — deux ordres de grandeur trop petit pour déplacer un |t| de plusieurs points
(USDJPY −2.81, EURUSD/GBPUSD ≈ −0.7 à −1.3), et le seul cas "proche" (US500 long) est tué par un
mécanisme totalement indépendant (bêta, pas départage).

### C.2 Le gisement flagué comme le plus probable — le corpus des 109 stratégies
`Multi_Asset/research/archived/oxfordstrat_109_audit/code/ftmo_lab.py:92-162` implémente
**indépendamment** la même philosophie ("stop assumed first... conservative", docstring lignes
8-10, et ligne 150 `if l[j] <= stop: ... break` **testé avant** la cible) — mais sur barres
**quotidiennes** avec `ATR_STOP = 6.0` (confirmé sur 43/109 fichiers en lecture directe du code,
uniforme) : un bracket **6× plus large** que le seuil dangereux (≤1.5×ATR) caractérisé en A.3.
**Mesure empirique directe** (S001 Crabel NR ORB, 15 instruments réels, `target_index` 1.0 puis
0.3 en stress) : **0 égalité de sortie sur 1,268 puis 1,434 trades — 0.00 % dans les deux cas.**
**Verdict : ce corpus n'est PAS exposé à ce biais précis.** C'est le résultat le plus contre-
intuitif de cet audit : le gisement le plus suspecté s'avère le mieux protégé, par construction
de sa géométrie (daily bars, brackets larges), pas par chance.

**Découverte annexe, distincte, non quantifiée ici** : une AUTRE ambiguïté intra-barre existe dans
ce même moteur — l'ENTRÉE, pas la sortie (`ftmo_lab.py:124`, "both sides -> assume loser (spec)") :
sur S001, **14.5 % des trades (459/3,160)** ont un breakout ORB simultané dans les deux sens,
toujours score comme perte. C'est une ambiguïté structurellement DIFFÉRENTE (déclenchement, pas
sortie), plus fréquente que tout ce qui a été mesuré ici, et mérite un audit dédié — **hors
mandat**, signalée pour référence future.

### C.3 Familles NON exposées, vérifiées
`mr_stress_conditional_2026-08` et `mr_timezone_repair_2026-08` (les deux plus gros contributeurs
au pool "943 cellules déjà dépensées" cité par l'étude source) utilisent **exclusivement des
sorties à horizon fixe, open-to-open, delay+1** ("no stop / no bracket", `mr_state.py` docstring) —
immunes par construction. `gross_surface_map_2026-08` (~8,695 cellules) est une étude de rendement
conditionnel forward, aucun code de bracket trouvé. `pairs_cointegration_2026-08` (171 paires) est
tué en amont par la porte de demi-vie (véhicule), avant toute question de sortie.

### C.4 Autres études du moteur partagé — exposition faible, verdicts inchangés
`breakout_ftmo` (q2/q3, superseded par `q4_honest.py`) : bracket **asymétrique 1:3** (cible 3×ATR)
— la double-touche exige qu'une seule barre couvre 4×ATR, quasi jamais observé (le tp ne se
remplit que sur 2-12 % des trades du tout). Déjà NO-GO sur DSR (0.226) et coût de stress ; aucune
correction plausible ne comble cet écart. `module_2_pinbar_gold` : 1.5×/3.0×ATR asymétrique, t
brut déjà **positif** (+0.51) — une correction ne fait qu'accentuer un signal qui reste loin sous
2.5. `module_1_crypto_scalping` (5 stratégies) : S1/S2/S4 négatifs même en gross (rien à corriger
dans le sens utile) ; S3/S5 positifs en gross mais nécessitent un coût ~20× moins cher que la
réalité (17bps) pour survivre — aucune correction de quelques points de base ne comble un facteur
20×.

### C.5 Non audité, identifié pour la suite
`PropFirms/ftmo/program_2026-06/ftmo_universe/{intraday_orb_study, ftmo_orb_1step}` partagent la
même signature textuelle ("check stop first (conservative)") mais dans un moteur encore différent
— budget de cette session insuffisant pour un audit complet ; recommandé en priorité #1 de la
prochaine session, même méthode que C.1-C.2.

**Bilan** : **0 verdict de stratégie ne bascule.** 1 exposition directe confirmée (biais réel
mesuré 100-1000× trop petit), 1 gisement suspecté disculpé empiriquement (0 incidence mesurée),
le reste soit non exposé par construction, soit tué par un facteur indépendant trop large pour
qu'une correction de quelques bps compte.

---

## D. L'ORB funded — le point le plus sensible

### D.1 Ce qui a été vérifié dans le ledger
`PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet` (N=4,013) : confirmé
`entry == level` sur 4,013/4,013, `exit_px == stop_eff` sur les sorties STOP (ex. lignes vérifiées
manuellement : 1844.25==1844.25, 1826.25==1826.25). Idéalisation confirmée au niveau du ledger.

### D.2 Ce que révèle une étude parallèle déjà réalisée
`Multi_Asset/research/active/orb_cost_funded_2026-08/` (fichiers datés 2026-08-12/13, gelés avant
cette session) a **déjà mesuré exactement cette question** :
- **Canal gap ENTRÉE, sur NQ futures** : 11/4,013 barres de déclenchement (0.274 %) ouvrent
  au-delà du niveau, **toutes exactement 1 tick**. Reproduction du ledger au tick : 4,013/4,013.
- **Canal gap SORTIE (le chiffre L59)** : **0/1,587 (0.00 %)** — contrairement au cas daily-bar de
  L59, l'ORB tourne en RTH intraday continu (M1 sans trou 4,012/4,013), le stop est franchi tick
  par tick, pas sauté. **L59 ne s'applique PAS à cet ORB.**
- **⇒ L'idéalisation `entry==level`/`exit==stop_eff` est empiriquement JUSTIFIÉE sur le NQ
  futures lui-même** — ce n'est PAS là que vit le biais optimiste.
- **Le vrai biais optimiste : un mésappariement de VÉHICULE.** Le ledger simule sur NQ futures
  (quasi sans friction) ; l'exécution live tourne sur **US100.cash CFD** via un ordre MT5 STOP
  déclenché sur l'**Ask** — mesuré sur les fills LIVE réels (N=12, échantillon signalé petit) :
  coût d'entrée **+2.169 bps** (91.7 % adverse), coût de sortie stop +0.430bps, sortie temps
  −0.997bps. Coût RT total mesuré : **1.80 bps** (deux méthodes indépendantes convergent à 0.5 %
  près : cache de spread médian et fills live).

### D.3 Le verdict, déjà rendu (cité, pas re-rendu ici)
Règle R2 (t HAC > 2.0, IC excluant 0) : à 1.80bps mesuré, **t = 0.48** — **KILL**, avec un facteur
**3× de marge** sous le seuil. Point mort de la moyenne : 2.189bps (à 0.5 % du 2.2bps codé en dur
qui masquait ce résultat dans les analyses antérieures). Walk-forward (5 folds expanding) :
**2/5 positifs (40 %)**, sous RESEARCH_PASS (50%). **Verdict : ORB_KILL.**

### D.4 Les deux biais, sur la même échelle
| | signe | où | ampleur mesurée |
|---|---|---|---|
| Départage intra-barre (chantiers A/B, ce rapport) | **pessimiste (négatif)** | sortie, moteur MR 15-min | −0.3 à −0.4 bps/trade (réel, canonique) ; jusqu'à −2.2 bps/trade (synthétique pire cas) |
| Idéalisation de véhicule (ORB, `orb_cost_funded_2026-08`) | **optimiste (positif)** | coût de véhicule, pas départage de barre | **+1.80 bps/trade** de coût non modélisé (7-9× le biais de départage) |

Les deux biais sont de nature différente (résolution de barre vs coût de véhicule) et de sens
opposé, mais celui de l'ORB est **6 à 9× plus grand en magnitude** et suffit, seul, à tuer un
sleeve qui affichait un t=2.74 brut prometteur.

### D.5 ⚠ Le point opérationnel le plus important de ce rapport
Les fichiers mémoire de session (`funded_transition_2026-08-12.md`, cité dans
`Portfolio`/`MEMORY.md`) décrivent encore, à leur date, ce sleeve comme portant **la moitié de
l'EV modélisée du compte funded**, armé à 0.25 % de risque par trade, **sans référence au verdict
ORB_KILL** rendu le lendemain (2026-08-13) par `orb_cost_funded_2026-08/RESULTS.md`. Cet audit,
en lecture seule, **ne peut pas vérifier** si le book LIVE a été mis à jour depuis. **C'est la
recommandation la plus urgente de ce rapport : vérifier si ce kill a été réconcilié avec le
déploiement réel**, avant toute autre action sur ce sleeve. Ce n'est pas un biais non chiffré —
il a été chiffré, il y a plus d'une semaine — la question est de savoir si le book en tient compte.

---

## Fichiers produits

- `bias_surface_synthetic_fattail.py` / `abaque_biais.csv` — abaque primaire (chantier A)
- `bias_surface_synthetic_thin_tail.py` / `abaque_biais_synthetic_thin_tail.csv` — contrôle de
  robustesse (sensibilité à la fatness de la queue)
- `bias_surface_placebo_confirm.py` / `abaque_biais_placebo_confirm.csv` — confirmation sur
  placebo à autocorrélation appariée (données réelles, 9 instruments)
- `m1_resolver.py` / `m1_resolver_results.csv` — le résolveur (chantier B)
- `inventaire_contamination.csv` — inventaire complet (chantier C, 13 études)

## Reproduction
```
cd Multi_Asset/research/active/audit_moteur_bracket_2026-08
/usr/bin/python3 bias_surface_synthetic_fattail.py      # ~20s
/usr/bin/python3 bias_surface_synthetic_thin_tail.py    # ~20s
/usr/bin/python3 bias_surface_placebo_confirm.py        # ~140s
/usr/bin/python3 m1_resolver.py                         # ~20s
```
Aucune opération git. Aucun chemin live (`ftmo_live/`, `Portfolio/`, `strategies/`,
`Futures/live/`, `.github/`, `*.mq5`) touché. VPS non utilisé (aucune donnée requise).
