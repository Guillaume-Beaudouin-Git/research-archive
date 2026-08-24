# PRE-REGISTRATION — Anatomie des busts FUNDED + décomposition cash-flow mensuelle

**Gelée AVANT résultats.** Author≠auditor. Continuation de real_metrics (worktree
`claude/real-book-metrics-lowcheck`, pré-reg 9a07bc7, audit CONFIRM-WITH-CAVEATS). Moteur canonique
(engine_v22 / cleanroom) NON muté ; on réutilise le `lowcheck_engine.py` **déjà audité** — l'anatomie
passe par un CLONE INSTRUMENTÉ de `run_funded` (observation-only), validé bit-pour-bit contre
`LC.run_funded` (self-EQUIV). Read-only, AUCUNE action live (compte <ACCOUNT_ID> intact).

## 0. Acquis (real_metrics, actés — ne pas re-litiguer)
Le stade FUNDED est le siège du tail : low-check bid 14–30 % busts (dom→all-leg) vs 3 % M5-close,
car funded tourne **vm1-PLEIN** (marge Swing FTMO 1:30/1:15/1:9 ne bind pas à vm1 ; la marge FTMO est
IDENTIQUE challenge/funded — la différence d'expo vient de NOTRE sizing vm1 vs vm14, pas d'une règle
FTMO). Carriers : OR le + robuste (survit dom-leg), puis JPY hors-zone, puis US100/nightly. Busts
tardifs (médiane ~169 j), 93 % conservent les retraits bankés. Config book actuel = **gate J1 ON**.

## 1. Setup & self-EQUIV (Volet 0)
- Stack : `LC.load_stack_lohi` (data → 2026-06-05, lo/hi bid/ask, même grille Paris). Signaux
  `E.build_signals()`. Gate J1 ON (`gate.suspend_causal` 160/155/10, causal, wt[:,1]*=(1−flag)).
- Marge : funded = vm1, marge policy (insensible per recost, vm1 ne bind jamais). Coûts = stack
  recost (swaps mesurés + comm), cohérent real_metrics.
- **Clone instrumenté** `funded_anat_engine.run_funded_anat` = clone EXACT de `LC.run_funded` +
  logs observation-only : à chaque bust `dict(date, kind, e, bal_start, daily_loss, at_open, seg,
  bar, life, n_pay, wd_banked, u_XAU/JPY/US100/GER40, dom_leg)` ; à chaque retrait `(date, day, amount)`.
- **G-SELF-EQUIV (STOP si échec)** : sur toute la grille funded, `run_funded_anat` == `LC.run_funded`
  sur (busted, wd, payouts, life, residual). Aucune divergence tolérée.
- Grille funded : **canonique `C22.FUNDED_WINDOWS`** (IS 2013-2017, OOS 2020-2024 ; horizons 504 j
  couvrent 2013-2019 + 2020-2026). Densité step **6** (≈380 starts) pour la couverture de l'anatomie ;
  les ABLATIONS Volet 2 restent sur FUNDED_WINDOWS canoniques (leçon overnight_basket : jamais une
  fenêtre de convenance). Rates par bootstrap-bloc (bloc 10, seed 23).

## 2. Volet 1 — Anatomie (mode primaire `low` = all-legs, borne dom-leg en sensibilité)
Classification GELÉE :
- **kind daily vs max-loss** : `daily` si `bal_start ≥ 9500` (barrière quotidienne −5 % active/atteinte
  en premier : lim_eff=limit) sinon `max_loss` (floor −10 % actif). = quelle règle FTMO ferme le compte.
  Reporter aussi la profondeur `e` et la perte du jour `bal_start − e`.
- **par sleeve** : `dom_leg` = argmin_k u_k (contribution adverse la + négative au bust) ; part de
  chaque sleeve. Sensibilité dom-leg (borne basse simultanéité).
- **type d'événement** : `at_open` (s==0 & bar==0 = ouverture, gap/overnight) vs intraday ; `gap_day`
  (date − date préc ≥ 3 j = week-end). Concentration régime : vol réalisée 20 j du dom_leg au bust
  (percentile causal) → busts en vol haute vs diffus.
- **de-dup** : FUNDED_WINDOWS se chevauchent → un même jour historique buste plusieurs starts.
  Reporter (a) **jours-bust UNIQUES** (dé-dupliqués par date = les vrais événements dangereux) ET
  (b) le taux cohorte (rate). L'anatomie porte sur (a) ; les rates/EV sur (b).
- **timing** : distribution `life` (jours-avant-bust, médiane ~169 à confirmer) ; `n_pay` + `wd_banked`
  au bust (les 93 % qui conservent).

## 3. Volet 2 — Réductibilité (CHIFFRER, décision FUTURE ; NE PAS adopter)
Overlays (sans toucher l'EA gelé → weight-mult / cfg, comme le gate J1). Chacun sur FUNDED_WINDOWS,
mode low, gate J1 ON de base. Métriques : Δ busts (unique-days + rate), ΔEV funded (VAL=FEE+0.8·E[extr]),
et **magnitude vs conversion** (le bust est-il évité, ou juste sa perte réduite ? cf. LCAP8 −60 % mais
buste toujours).
- **(a) Gate OR (XAUUSD)** : suspension gold quand vol réalisée gold 20 j > **p80** causal
  (self-contained, régime de choc). wt[:,0]*=(1−flag). Analogue du gate J1 sur le carrier principal.
- **(b) Gate JPY élargi hors-zone** : le gate actuel ne couvre J1 qu'EN zone (≥160) ; ajouter une
  suspension JPY sur vol réalisée JPY 20 j > p80 (attrape 2016/19/22 hors-zone). Mesurer le gain
  incrémental vs gate zone-seul.
- **(c) Sizing funded vm ∈ {1.0, 0.85, 0.7, 0.5}** : ⚠️ touche vm (ACTÉ). **CHIFFRER la courbe
  tail↓ vs EV↓, NE PAS trancher.** Fournir pour décision future explicite.
- Seuils p80 / grille vm **gelés ici** (pas de recherche de seuil post-résultat).

## 4. Volet 3 — Cash-flow mensuel (MC entreprise, 24 mois calendaires)
Assembler le timeline challenge→funded, MC ≥ 20 000 tirages (seed 23) :
- **Sorties** : −$96 par challenge acheté (re-purchase échantillonné des cohortes challenge
  `swing_ON_low` : funded?, attempts, camp_days) ; fees étalés aux débuts de campagne.
- **Entrées** : à la mise en funded, échantillonner une trajectoire funded (calendrier des retraits +
  jour de bust, du clone instrumenté). Chaque retrait → **+0.8·montant** (split 80 %). **1er payout :
  +$96 refund** (FTMO rembourse le fee du challenge réussi). Retraits ~ tous 14 j de trading.
- **Re-acquisition** : si le compte funded buste (à `life`), retour phase acquisition (re-challenge)
  et on continue jusqu'à 24 mois. Vue « entreprise ».
- **Livrables** : cash-flow cumulé mensuel → **mois de break-even** (cumul>0), distribution
  **p10/médian/p90** ; **$/mois espéré** en régime funded ; cash nominal.
- **Scaling (scénario OPTIONNEL)** : +25 % taille tous les 4 mois si (≥10 % net cumulé + ≥2 payouts +
  positif) → payouts ×1.25 après jalon. Overlay conditionnel, rapporté à part.
- **Actualisation** : nominal PRIMAIRE + note de sensibilité (ex. 0.5 %/mois) : change-t-elle la
  lecture du break-even ? (probablement mineur sur 24 mois — à confirmer).

## 5. Hypothèses de modèle FUNDED (gelées, déclarées)
wd_every=14 trading-days (conservateur vs bi-weekly officiel) ; split 80 % (base, pas de scaling par
défaut) ; refund fee au 1er payout ; min-withdrawal non modélisé (retire bal−INIT quel qu'il soit) ;
horizon funded 504 j de trading ≈ 2 ans. Ces hypothèses héritées de la chaîne v2.2.1 (VAL/EV cohérents
real_metrics).

## 6. Caveats hérités (real_metrics, gelés)
Low-check DISCRET (flash sous-M1 non modélisé) ; **surestime la perte** (liq FTMO ≈ floor, pas le low
→ détecte le bust, pas la perte exacte → `daily_loss`/`e` sont des bornes, pas la perte réalisée) ;
all-legs = borne haute (legs se hedgent en risk-off), bracketé dom-leg ; niveaux absolus indicatifs,
seul le **Δ** robuste ; couverture lo/hi US100 83.7 %/GER40 83.0 % (fallback conservateur → tail de ces
2 legs possiblement sous-estimé ; XAU 94 %/JPY 99.9 % bien couverts) ; échantillon → 2026-06-05
(flashs 07-02/03 hors-fenêtre ; valeur gate prospective).

## 7. Distinction DONNÉE vs JUGEMENT
Données (rétrospectif) : anatomie, Δ overlays, cash-flow sur l'historique 2013-2026. Jugement
(prospectif) : la valeur de protection d'un overlay contre un tail hors-modèle (comme le gate J1),
et l'extrapolation cash-flow à l'avenir. Séparés explicitement dans le report.

## 8. Ordre
V0 (dir + clone + self-EQUIV) → V1 anatomie → V2 overlays → V3 cash-flow → self-check → audit
indépendant → REPORT + mémoire. Pré-reg gelée AVANT tout résultat.
