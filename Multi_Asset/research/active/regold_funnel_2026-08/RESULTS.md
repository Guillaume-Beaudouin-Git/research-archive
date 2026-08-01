# Re-passage de l'écran or au coût mesuré — funnel FTMO 164 tests

**2026-08-01. Réparation de mesure, `N0` : cet exercice ne consomme aucun essai et ne déflate
rien.** Il re-lit un écran déjà payé avec un instrument corrigé. Tout candidat qui en ressort et
qu'on voudrait *revendiquer* devra être pré-enregistré en **N2** avec sa kill rule écrite avant —
c'est dit explicitement pour chaque survivant au §6.

Dénominateur : `Multi_Asset/research/active/cost_denominator_2026-07/COST_AUDIT.md` §3.
Code : `code/{regold_lib,run_recost,run_controls,run_attribution}.py`. Interpréteur `/usr/bin/python3`.

---

## 1. Le défaut et son périmètre exact

`PropFirms/ftmo/program_2026-06/top10_test/framework.py:29` coûte l'or à **3.50 bps RT**, valeur
de catalogue (« per rules.md »), jamais mesurée. La mesure :

| composant | source | bps |
|---|---|--:|
| spread médian XAUUSD (750 derniers jours) | `data/ftmo_portfolio/cache/XAUUSD_daily_cet.parquet` | 0.699 |
| slippage, provision du modèle 2 × 0.50 | `research_panel.py:16` | 1.000 |
| commission RT (2 × 0.0007 %) | `data/ftmo_portfolio/config.py:35` | 0.140 |
| **RT mesuré** | | **1.839** |

Deuxième défaut, découvert en re-lisant : `FTMO_SWAP_BPS_PER_NIGHT` code l'or à **−2.9 bps/nuit
symétrique**. Le swap or est **asymétrique** (`cache/panel_swapL/S.parquet`) : sur la fenêtre du
funnel (2020+), médiane **long −2.065 / short −0.335**. Les trois familles porteuses tiennent
1 nuit, donc la charge totale par trade passe de **6.400** à **3.904 bps**.

**Périmètre.** 142 specs dans `summary_batch_142.csv` + 22 specs de `run_tests.py` (les `ang_*` /
`lit_*`) = les 164 du programme. `run_tests.py` ne contient **aucun** instrument métal (grep
`XAU|Metals_CFD_gold|gold` → 0 hit). Le périmètre or est donc **exactement les 16 lignes
XAUUSD de `summary_batch_142.csv`** — inventaire dans `perimeter.csv`.

**Combien ont été rejetés sur un critère de coût : les 16.** Le funnel appliquait un gate
`cost_gate_ratio = |gross moyen| / coût ≥ 3.0` (`run_batch.py`, « PRACTICAL FTMO GATE »).
Au coût catalogue, **0 / 15** candidats re-jouables l'atteignaient (meilleur : 2.946). Au coût
mesuré, **10 / 15** le franchissent. C'est le réservoir d'erreurs de type II annoncé par l'audit,
chiffré.

### Ce qui n'a pas pu être re-joué

| spec | raison |
|---|---|
| `pr_XAUUSD_XAGUSD_z1.5_h5` | `Forex/data/cache/dukascopy_m5` supprimé au cleanup P2 2026-06-10 → XAGUSD indisponible pour ce chemin. **Tranché analytiquement** : gross **−7.28 bps** (négatif), donc kill *mécanique*, fermé par la politique de ré-ouverture. Et la correction va dans le **mauvais sens** pour lui : le funnel costait XAGUSD à 3.50 (classe `Metals_CFD_gold`) alors que son spread médian mesuré est **5.37 bps** (RT ≈ 6.51) — l'argent était **sous**-facturé de 1.9×, pas sur-facturé. |

---

## 2. Validation du harnais avant toute conclusion

Les CSV `data/panels/m5_indices/*_M1.csv` ont été supprimés au cleanup P2 ; la même série survit
en `*_m1_panel.parquet`. Le shim est déclaré (`regold_lib.py`) et la reproduction est **vérifiée,
pas supposée** (`reproduction.csv`) :

- **11 / 15 specs reproduites à la précision machine** (|Δgross| ≤ 1.8e-15, |ΔSR| ≤ 5.6e-17).
  Ce sont toutes les familles adossées au fichier d'événements (2020-2025), dont les 3 survivants
  du §5 pour deux d'entre eux.
- **4 specs re-jouées sur une fenêtre plus courte** : `im_XAUUSD_*` (257 vs 292 trades),
  `gv_XAUUSD_*` (297 vs 393), `cal_XAUUSD_tom_+1` (401 vs 523). Le parquet couvre
  2020-01-02 → 2026-05-29 (1 655 jours, aucun trou : médiane 1 365 barres/jour, 2 jours < 100
  barres sur 1 655) ; le CSV disparu en couvrait ~30 % de plus, donc démarrait vers 2018.
  **Conséquence** : pour ces 4 specs, la comparaison avant/après est faite contre **mon propre
  re-run C0 sur la fenêtre disponible**, jamais contre le chiffre publié. Le delta attribué au
  coût reste propre ; c'est le niveau absolu qui n'est pas comparable au funnel d'origine.

---

## 3. Table avant / après — les 15 specs re-jouables

Coûts comparés (RT bps / swap long,short bps par nuit) :

| modèle | RT | swap L | swap S | ce que c'est |
|---|--:|--:|--:|---|
| `C0_catalog` | 3.500 | −2.900 | −2.900 | ce que le funnel a réellement appliqué |
| `C1_measured` | 1.839 | −2.065 | −0.335 | **l'écran corrigé** — spread mesuré + provision slippage du modèle |
| `C2_centre` | 0.946 | −2.065 | −0.335 | espérance honnête : slippage **réalisé médian** (0.10/côté) au lieu de la provision |
| `C3_tail` | 3.881 | −2.065 | −0.335 | **provision de queue** : spread p75 + slippage **p95** (1.485/côté) sur *chaque* trade |

`net_bps` = moyenne par trade ; `SR` = Sharpe excess vol-targeté 8 % ; `p2` = p(pass) 2 phases,
plancher **statique** (§4) ; `cgr` = cost_gate_ratio.

| id | cgr C0 → C1 | net_bps C0 → C1 | SR C0 → C1 | t_HAC C0 → C1 | p2 C0 → C1 | net C3_tail |
|---|--:|--:|--:|--:|--:|--:|
| `me_fom_nfp_cpi_XAUUSD_+1` | 2.68 → **4.39** | 10.74 → **13.24** | 0.790 → **1.049** | 2.02 → **2.68** | 53.0 % → **62.1 %** | 11.19 |
| `ed_cpi_us_XAUUSD_LO` | 2.79 → **4.57** | 11.46 → **13.95** | 0.637 → **0.816** | 1.59 → 2.05 | 43.7 % → **54.0 %** | 11.91 |
| `cal_XAUUSD_tom_+1` | 2.91 → **4.77** | 12.22 → **14.72** | 0.521 → 0.663 | 1.17 → 1.49 | 51.9 % → **57.6 %** | 12.68 |
| `ed_fomc_XAUUSD_LO` | 2.95 → **4.83** | 12.45 → **14.95** | 0.357 → 0.433 | 0.88 → 1.07 | 25.6 % → 28.3 % | 12.91 |
| `ed_nfp_us_XAUUSD_SS` | 2.22 → **3.65** | 7.83 → **10.33** | 0.081 → 0.281 | 0.20 → 0.70 | 14.0 % → 22.4 % | 8.28 |
| `gv_XAUUSD_t1.5_fade` | 2.78 → **5.30** | 6.24 → 7.90 | −0.096 → 0.001 | −0.26 → 0.00 | 22.1 % → 25.8 % | 5.86 |
| `per_fomc_XAUUSD_4h` | 0.49 → 0.94 | −1.78 → −0.12 | −0.36 → −0.31 | −0.90 → −0.76 | 9.8 % → 11.1 % | −2.16 |
| `im_XAUUSD_1430_1530_fade` | 0.19 → 0.35 | −4.15 → −2.49 | −0.80 → −0.53 | −2.03 → −1.36 | 4.5 % → 8.5 % | −4.53 |
| `im_XAUUSD_1430_1530_mom` | 0.19 → 0.35 | −2.85 → −1.19 | −0.80 → −0.53 | −2.04 → −1.36 | 4.0 % → 7.7 % | −3.23 |
| `gv_XAUUSD_t1.5_cont` | 2.78 → **5.30** | −13.24 → −11.58 | −0.70 → −0.60 | −1.87 → −1.61 | 5.6 % → 7.1 % | −13.62 |
| `per_fomc_XAUUSD_2h` | 0.22 → 0.41 | −2.75 → −1.08 | −1.52 → −1.22 | −3.75 → −3.02 | 0.0 % → 0.0 % | −3.13 |
| `ed_fomc_XAUUSD_SS` | 2.95 → **8.68** | −25.25 → −21.03 | −1.10 → −0.99 | −2.74 → −2.46 | 0.6 % → 1.0 % | −23.07 |
| `ed_nfp_us_XAUUSD_LO` | 2.22 → **6.55** | −20.63 → −16.40 | −1.60 → −1.33 | −4.06 → −3.34 | 0.2 % → 0.6 % | −18.45 |
| `ed_cpi_us_XAUUSD_SS` | 2.79 → **8.22** | −24.26 → −20.03 | −1.97 → −1.74 | −5.05 → −4.42 | 0.0 % → 0.0 % | −22.07 |
| `per_fomc_XAUUSD_1h` | 0.17 → 0.33 | −2.89 → −1.23 | −2.43 → −2.03 | −6.05 → −5.01 | 0.0 % → 0.0 % | −3.27 |

Table complète : `recost.csv`. Le `cost_gate_ratio` est **aveugle au signe** (il prend
`|gross|`) : c'est pourquoi des specs à gross franchement négatif « franchissent » le gate à
4-8× — le gate seul ne sélectionne rien, il ne fait qu'écarter.

**Trois specs seulement atteignent un seuil de décision au coût corrigé**, et une seule le
franchit *pour la première fois* : `ed_cpi_us_XAUUSD_LO` (SR 0.637 → 0.816 franchit
RESEARCH_PASS ; p2 43.7 % → 54.0 %). Les deux autres étaient déjà au-dessus de p2 = 50 % au coût
catalogue et étaient tuées **par le gate de coût**, que la correction lève.

### Attribution : combien vient du spread, combien du swap

Les trois candidats concernés sont **long, 1 nuit**, donc la charge se décompose en forme close
(`cost_attribution.csv`) :

| | charge/trade | Δ SR `me_fom` | Δ p2 `me_fom` |
|---|--:|--:|--:|
| `C0_catalog` | 6.400 | — | — |
| `D1_spread_only` (RT 1.839, swap catalogue) | 4.739 | +0.173 | +6.2 pt |
| `D2_swap_only` (RT 3.50, swap mesuré) | 5.565 | +0.087 | +3.1 pt |
| `C1_measured` | 3.904 | +0.259 | +9.1 pt |

**Le correctif du spread porte les deux tiers de l'effet, le swap un tiers.** Nuance qui compte :
en provision de **queue** (`C3_tail`), le RT mesuré remonte à **3.881**, soit **au-dessus** du
catalogue 3.50 — dans la queue, seule la correction du swap sauve encore quelque chose. Le
« l'or a été screené à 1.9× son coût réel » est vrai **au centre de la distribution**, pas dans
la queue. C'est précisément la forme d'erreur décrite au §6.2 de l'audit.

---

## 4. Deux corrections d'instrument faites au passage

**(a) Le plancher de perte max était en cliquet.** `framework.py:283` :
`mll_floor = max(1 - MLL, hwm_eod - MLL)` — un plancher qui monte avec le high-water mark. Ce
mécanisme n'existe que sur le **1-step**, écarté ; sur le 2-step le plancher est **statique à
−10 % du capital initial** (confirmé 2026-08-01). Le cliquet est strictement plus dur, donc le
funnel **sous-estimait p(pass) pour les 164 candidats**. Effet mesuré ici : marginal
(`me_fom` 52.8 % publié → 53.0 % en statique au même coût) — les candidats meurent avant
d'accumuler du HWM. Correction faite, effet honnêtement nul.

**(b) Le DSR du funnel est inutilisable tel quel.** `framework.deflated_sharpe` compare le Sharpe
à `sqrt(2 ln N)·(1 − γ/sqrt(2 ln N))`, qui est E[max de N normales **standard**] — une quantité en
unités de σ_SR, valide seulement si σ_SR = 1. Recalcul avec `dsr.py` canonique et une dispersion
d'essais **mesurée sur les 142 Sharpes du funnel** (σ_SR = 0.866) au §6.

---

## 5. Les survivants — vocabulaire à trois valeurs

Trois candidats atteignent un seuil au coût corrigé. **Aucun n'est un PASS.** Les kill rules
ci-dessous ont été écrites dans l'en-tête de `run_controls.py` **avant** exécution :

> **K1** R² contre un buy-and-hold or vol-targeté > 0.30 sur jours actifs → pas une sleeve neuve.
> **K2** moyenne jour-sélectionné ≤ espérance **inconditionnelle** de la même forme de trade
> (t_HAC de la différence < 2.0) → pas d'alpha d'événement.
> **K3** moyenne réelle sous le p90 du placebo calendaire apparié → REJECTED.
> **K4** net bps/trade ≤ 0 en provision de queue `C3_tail` → cost-dead dans la queue.

### L'éléphant, mesuré d'abord

La fenêtre re-jouable est **2020-01-02 → 2026-05-29 : l'or fait +193.9 %, soit 18.34 %/an,
7.13 bps/jour**. Toute sleeve **long-only or tenue une nuit** hérite de cette dérive. L'espérance
**inconditionnelle** de chaque forme de trade, mesurée sur *tous* les jours de la fenêtre :

| forme de trade | espérance inconditionnelle |
|---|--:|
| `close(T−1) → 13:30 le lendemain` (familles event_drift / multi_event) | **+6.43 bps** |
| `open(T) → close(T+1)` (famille calendar) | **+12.49 bps** |

C'est le contrôle L58 : la baseline du placebo doit être **cette** valeur, pas zéro.

### S1 — `me_fom_nfp_cpi_XAUUSD_+1` — **UNDERPOWERED**

Or long, entrée close T−1, sortie à la publication (FOMC + NFP + CPI). N = 187 trades, 1 nuit.

| contrôle | résultat | verdict |
|---|---|---|
| **K3 placebo apparié** (décalage circulaire du masque, préserve le clustering) | réel **14.91** vs p50 6.34, p90 12.46, p95 14.38 → **96.1ᵉ percentile** | **passe** |
| **K2 vs inconditionnel** | 14.91 vs 6.43 → excédent **+8.48 bps**, t_HAC **2.57** | **passe** |
| **L58 biais de baseline** | moyenne du pool 5.36 vs inconditionnel 6.43 → biais **−1.08 bps** | déclaré ; ici il **flatte** le signal, donc à retrancher |
| **K1 L38 β-orthogonalité** (jours actifs, n=183) | β **1.57** (t 6.99), α **25.4 bps/j** (t 2.18), **R² 0.286** | passe **de justesse** (seuil 0.30) |
| L38 plein échantillon (n=1535, duty cycle 12 %) | β 0.250, α 4.03 bps/j (t 2.62), R² 0.046 | diversifieur bas duty-cycle |
| **L25 jambes disjointes** (split sur le trend or 60j **antérieur**, hors fenêtre de trade) | tendance haussière +9.63 (t 2.34, n=118) / tendance **baissière +19.28** (t 3.70, n=60) | **les deux jambes positives** |
| **L59 delay+1** entrée ET sortie | entrée +1 min : gross 17.14 → 15.07 (−12 %), t_HAC 3.07 → 2.76 ; sortie +1/+5/+15 min : stable | robuste |
| **K4 queue** | net **+11.19 bps** à `C3_tail`, p2 **54.6 %** | **passe** |
| **DSR corrigé** (σ_SR mesurée 0.866) | SR 1.248 vs benchmark **2.297** à N=142 → **DSR 0.002** | **échoue** |
| **AMTP Šidák** | t 2.683, p brut 0.0073 → **p 0.646** à N=142, 0.110 à N=16 | **échoue** |
| durée | p(pass) 2 phases **62.1 %**, **médiane 229 jours** | non exploitable seul |
| MaxDD | **−10.7 %** au vol target de recherche (8 %) | **déjà sous le plancher FTMO −10 %** avant tout levier |

Le mécanisme survit à tous les falsificateurs mécaniques — y compris le placebo apparié, qui est
ce qui a tué l'unlock-drift (L49) et le calendrier ZN (L58). Ce qui le bloque est **la puissance** :
187 trades, 6.4 ans, et un compteur d'essais de 142-164 devant lui. Ce n'est pas REJECTED, c'est
**UNDERPOWERED**. La note de vérification β-orthogonalité (R² 0.286 sur jours actifs, β 1.57)
dit qu'il est **près** du seuil L38 : la moitié de sa variance en jour actif est de l'or.

**Si on veut le revendiquer : pré-enregistrement N2 obligatoire**, spec gelée
(instrument XAUUSD, événements FOMC/NFP_US/CPI_US, entrée close T−1, sortie 1ʳᵉ barre ≥ heure de
publication, long unconditionnel, coût C1, provision de queue C3), avec pour kill rule écrite
avant : *« excédent sur l'inconditionnel < 4 bps, ou t_HAC de cet excédent < 2.0, ou percentile
placebo < 90, ou R² L38 jours actifs > 0.30, sur ≥ 40 nouveaux événements hors échantillon
(2026-06 → ) ⇒ mort. »* Les 40 événements sont le seuil, pas une suggestion.

### S2 — `ed_cpi_us_XAUUSD_LO` — **UNDERPOWERED** (et non indépendant de S1)

Même forme, CPI seul. **C'est un sous-ensemble de S1** (S1 empile FOMC+NFP+CPI) : les deux ne
comptent pas comme deux confirmations.

| contrôle | résultat | verdict |
|---|---|---|
| K3 placebo | 17.86 vs p90 16.00, p95 18.62 → **93.7ᵉ percentile** | passe, sans marge |
| K2 vs inconditionnel | 17.86 vs 6.43 → +11.42 bps, t_HAC **2.09** | passe de justesse |
| K1 L38 jours actifs (n=70) | β 1.09 (t 2.13), α 50.7 bps/j (t 2.05), **R² 0.071** | passe proprement |
| L25 jambes disjointes | hausse +16.41 (t 2.18, n=44) / baisse +16.88 (t 2.63, n=24) | deux jambes positives |
| L59 delay+1 | gross 17.86 → 16.91 entrée+1 min ; t_HAC 2.55 → 2.45 | robuste |
| K4 queue | net +11.91 à `C3_tail`, p2 **45.8 %** (< 50 %) | passe K4, **retombe sous 50 % de p(pass)** |
| DSR corrigé | SR 1.092 vs benchmark 2.297 → **0.00015** | échoue |
| AMTP Šidák | t 2.049 → **p 0.997** à N=142 | échoue |
| durée | p2 54.0 % mais **médiane 333 jours** | inexploitable |

**N = 71 trades.** UNDERPOWERED, et la première chose qu'il perd quand on provisionne la queue
est le seuil de décision lui-même. Même exigence N2 que S1 s'il devait être revendiqué —
mais il n'a pas d'angle propre à côté de S1.

### S3 — `cal_XAUUSD_tom_+1` — **REJECTED**

Or long, tour du mois (jours 27-3), open(T) → close(T+1). N = 401.

| contrôle | résultat | verdict |
|---|---|---|
| **K3 placebo apparié** | réel 18.62 vs p50 **13.10**, p90 **21.96** → **79.5ᵉ percentile** | **ÉCHEC** |
| **K2 vs inconditionnel** | 18.62 vs **12.49** → excédent +6.13 bps, **t_HAC 0.72** | **ÉCHEC** |
| **K1 L38 jours actifs** (n=396) | β **1.50** (t 16.6), **R² 0.509**, α t **0.75** | **ÉCHEC** |
| L25 jambes disjointes | hausse +23.65 (t 2.19) / **baisse +9.10 (t 0.78)** | jambe baissière nulle |

**REJECTED.** Ce n'est pas un effet de tour du mois : c'est la dérive de l'or 2020-2026 captée
par un masque calendaire qui couvre 24 % des jours, avec un β de 1.5 et un α insignifiant. Sa
« Sharpe » ne vient pas du signal. C'est la signature exacte de L49 (unlock-drift : réel en
absolu, sous le placebo apparié) — et le contrôle L58 le confirme : la moyenne du pool placebo
(10.53) diffère de l'inconditionnel (12.49) de −1.96 bps, donc un placebo naïf l'aurait *flatté*
et il échoue quand même.

---

## 6. Le défaut L25 du batch, vérifié sur tout le périmètre or

Le mandat l'annonçait ; c'est confirmé **exactement** : `batch_strategies.py:571` instancie la
jambe short par `side=-side_long`, donc `gross_SS ≡ −gross_LO` au bit près. Sur les 5 paires
miroir du périmètre or, la somme des gross est **exactement 0.0** dans les 5 cas
(`controls.json:mirror_check_L25`). Sur les 142 du batch, **36 lignes sont des jambes miroir
exactes** : le funnel a compté 142 essais là où il y a **106** hypothèses distinctes.

Les colonnes `_SS` ne sont donc pas utilisées ici. Le test two-sided a été **réécrit à jambes
disjointes** : partition des mêmes événements sur le signe du rendement or à 60 jours **décalé
de 1** (donc entièrement antérieur à la fenêtre de trade), et exigence que la dérive soit
positive **des deux côtés**. S1 et S2 la passent ; S3 échoue.

Nuance à ne pas sur-vendre : ce test falsifie « l'effet n'est que du trend-following déguisé ».
Il ne construit pas une jambe short réelle — **ces specs n'ont pas de forme two-sided**, elles
sont long inconditionnel. C'est pour ça que le contrôle qui tranche est L38 + le placebo, pas L25.

**Sur le compteur d'essais** : retirer les miroirs ne relâche pas le DSR. Dispersion mesurée des
Sharpes du funnel : **0.866 sur les 142**, **0.920 sur les 106 sans miroirs** — le benchmark
E[max SR] passe de 2.297 à 2.348, il **monte**. L'hypothèse « les miroirs gonflent artificiellement
la dispersion d'essais » est **fausse**, testée et rapportée comme telle.

---

## 7. Ce que ça ne prouve pas

1. **Ça ne prouve pas que l'or porte un edge d'événement.** Le seul candidat qui survit à tous
   les falsificateurs mécaniques (S1) échoue le DSR et l'AMTP à son propre compteur d'essais.
   **UNDERPOWERED n'est pas PASS** — et 43 % de son gross (6.43 sur 14.91) est la dérive
   inconditionnelle de l'or sur une fenêtre à +18.3 %/an.

2. **Ça ne prouve pas que 1.84 bps soit une constante.** C'est un centre de distribution. Le p95
   de slippage réalisé est 1.485/côté et le max observé 3.67 (audit §6.2), ce qui met le RT de
   queue à **3.881 — au-dessus du catalogue 3.50**. Un candidat qui n'existe qu'au centre
   n'existe pas à la barrière. S2 le montre : p(pass) 54.0 % → 45.8 % en provision de queue.

3. **Ça ne prouve rien sur les 148 autres candidats du funnel.** L'audit de coût note que les
   indices sont eux aussi sur-facturés (2.20 supposé vs 1.47-1.82 mesuré) et que le FX est
   **sous**-facturé (colonne spread zéro-inflée). Ce re-passage ne couvre que l'or. Les familles
   FX tuées sur le coût en sortent **renforcées**, pas rouvertes.

4. **Le p(pass) est optimiste par construction.** Le simulateur teste la limite journalière sur
   l'équité **de clôture** : avec un ledger quotidien il n'y a pas de chemin intra-journalier.
   L'incident du 2026-07-02 (<ACCOUNT_ID>) a établi que la liquidation continue bat un breaker
   discret. Traiter ces p(pass) comme des bornes hautes.

5. **Les durées tuent l'usage propfirm autonome.** Médianes de campagne 2 phases : 229 j (S1),
   333 j (S2), 241 j (S3). FTMO n'impose pas de limite de temps, mais une sleeve à ~29 trades/an
   au vol target de recherche ne finance pas un challenge seule. Le cadre correct est
   **ΔSR au poids ERC + Δp(pass) + Δdurée** dans un livre (`Portfolio/admission/`), pas un
   déploiement solo.

6. **Le MaxDD n'est pas invariant d'échelle (L54).** S1 est déjà à **−10.7 %** au vol target de
   recherche de 8 % — sous le plancher FTMO. Tout dimensionnement se juge **au levier déployé**.

7. **Fenêtre.** 4 des 15 specs (les familles quotidiennes, dont S3) ont été re-jouées sur
   2020-2026 au lieu de la fenêtre d'origine ~2018-2026, faute des CSV M1 supprimés au cleanup
   P2. Le delta de coût reste valide (même ledger avant/après) ; les niveaux absolus de ces 4-là
   ne sont pas comparables au funnel publié.

---

## 8. Verdict

| | |
|---|---|
| candidats or du funnel rejetés sur un critère de coût | **16** (dont 15 re-jouables) |
| franchissant le gate de coût au coût **catalogue** | **0 / 15** |
| franchissant le gate de coût au coût **mesuré** | **10 / 15** (6 avec net positif) |
| atteignant un seuil de décision au coût mesuré | **3** |
| **PASS** | **0** |
| **UNDERPOWERED** — à pré-enregistrer en N2 avant toute revendication | **2** — `me_fom_nfp_cpi_XAUUSD_+1` (le seul avec un angle propre), `ed_cpi_us_XAUUSD_LO` (sous-ensemble du premier) |
| **REJECTED** | **14** — 13 re-jouables + `pr_XAUUSD_XAGUSD` (kill mécanique, gross négatif, et l'argent était **sous**-facturé) ; dont `cal_XAUUSD_tom_+1` explicitement tué par le placebo apparié et L38 (β or, R² 0.509) |

**L'écran réparé rend un candidat, pas un edge.** Le dénominateur faussé avait bien fermé une
porte — le gate de coût écartait la totalité du périmètre or — mais derrière la porte il y a une
hypothèse sous-puissante, à 43 % de dérive inconditionnelle, qui échoue le DSR à son propre
compteur d'essais. C'est un résultat utile : il ferme la question « et si l'or avait été
sur-pénalisé ? » avec un chiffre, au lieu de la laisser ouverte comme dette.

### Leçon candidate (nommée, non numérotée — la gravure se fait à la réconciliation)

**`cost-fix-is-not-a-pass`** — réparer un dénominateur faussé déplace un candidat de *rejeté sur
le coût* vers *évaluable*, jamais vers *validé* : le coût est un gate d'entrée, pas une preuve.
Sur les 16 or, la correction 1.9× a fait franchir le gate à 10, un seul seuil de décision à 1
nouveau, et **zéro** aux falsificateurs de mécanisme. Corollaire opératoire : mesurer
l'**espérance inconditionnelle de la forme de trade** *avant* de re-screener — ici 6.4 à 12.5 bps
d'or gratuit sur la fenêtre, soit 43 à 67 % du gross des « survivants ». Et corollaire de queue :
la correction au **centre** (1.84 < 3.50) s'inverse dans la **queue** (3.88 > 3.50), donc un
re-passage au coût mesuré doit rapporter les deux, sinon il fabrique un faux positif de barrière.
