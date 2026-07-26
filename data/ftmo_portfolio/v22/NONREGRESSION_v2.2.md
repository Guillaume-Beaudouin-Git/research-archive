# NON-RÉGRESSION v2.2 — ancres + tolérances *(révision v2.2.1 re-cost, 2026-06-11)*
*Chaque ancre régénérée par son run (v2.2 : 2026-06-10 ; v2.2.1 : 2026-06-11). Commandes
depuis `v22/` ; stack gelé ; /usr/bin/python3. Toute future modification doit re-passer CE fichier.*

> ## ADDENDUM v2.2.2 — lot EA v2.8 (2026-07-26)
> **Le tableau ci-dessous est daté v2.2.1 et ses valeurs ne sont PAS réécrites** (le champ
> `meta.nonregression` du yaml le référence comme « révision v2.2.1 » ; le réécrire imposerait
> un nouveau re-gel de la chaîne). Pour la spec courante **v2.2.2**, les ancres #19 et #20 valent :
>
> | # | Ancre | v2.2.1 *(tableau ci-dessous)* | **v2.2.2 (courant)** |
> |---|---|---|---|
> | 19 | sha256 `spec_v22.yaml` | `56fbdde78a2e…` | **`3e7626f6d3fdc53050a9ad1097c13c8af05179d380f5090141c323561060563b`** |
> | 20 | sha256 `spec_v22.mqh` | `2fc65503ef66…` | **`d8d3dcb1ad88ec6bf2338ef88c4710d8595d5a0e9f1ca847d9e0ab0c8fe0388b`** |
> | — | commit de gel du yaml (pin P2) | `87b6cd4` | **`ad403cef`** |
> | — | log Experts attendu à l'init | `SPEC OK v2.2.1 sha 56fbdde78a2e…` | **`SPEC OK v2.2.2 sha 3e7626f6d3fd…`** |
>
> Les deux régénérations restent BYTE-IDENTIQUES ×2 (ancres #19/#20 tenues) et le drift-check
> `challenge.config`/`funded.config` PASSE inchangé : l'overlay `risk_overlays.leg_leverage_cap`
> vit HORS de ces blocs, donc **tous les chiffres pinnés v2.2 se reproduisent à l'identique**
> avec un cfg sans overlay — vérifié A/B sur 462 cohortes (82.47 % / 381, 0 cohorte divergente).
> Contenu du lot et raisons : `ea/README_BUILD.md` §« Re-geler la chaîne ».

| # | Commande / source | Ancre attendue | Tolérance |
|---|---|---|---|
| 1 | `run_battery.py` → challenge_91 | IS 90.6 / OOS 83.4 / **pooled 87.0** | ±1.5 pt |
| 2 | idem → CDF | 30j 41.6 / 61j 70.3 / 182j 98.9 / 270j 100.0 ; **monotone** | ±2 pts ; monotonie STRICTE |
| 3 | idem → essais / med_t | 3.24 ; IS 35j / OOS 29j | ±0.2 ; ±3j |
| 4 | idem → funded (ORB_RT_BPS=era) — *v2.2 sans commissions* | IS $684 / OOS $2,632, bust 3.2/1.0%, payouts 3.3/10.8 | ±10% ; ±1 pt ; ±1 |
| 4b | **v2.2.1** `run_recost_v221.py` → funded comm-only (coûts mesurés) | IS **$683** / OOS **$2,529** | ±10% |
| 5 | VAL / EV chaîne — *v2.2* | $1,422 / +$926 | ±10% (VAL re-dérivée, jamais héritée) |
| 5b | **v2.2.1** VAL / EV (commissions incluses) | **$1,381 / +$863** | ±10% |
| 6 | idem → placebo | 71.2% ; edge **+15.8 pts** | edge ∈ [+8 ; +25] |
| 7 | idem → anticausal −1j | 83.1% ≤ pooled | ne doit JAMAIS dépasser pooled +1 pt (= leak) |
| 8 | idem → swap×1.5 / spread×2 | 86.4 / 77.9 | ±2 pts |
| 9 | idem → marge pré-cap (policy) | p50 21 / p99 79 / max 116 ; bind 5.6% | ±10 pts ; ±2 pts |
| 9b | **v2.2.1** marge mesurée (diagnostic, M coûts mesurés) | Standard: p50 22/p99 104/bind 10.1% ; **Swing: p50 69/p99 395/p999 511/bind 56.0%, p(pass) 71.4 (Δ apparié −15.58 [−24.0;−7.1] SIGNIF)** | ±10 pts ; le verdict SWING = gate déploiement (lire OrderCalcMargin serveur Swing) |
| 10 | idem → gap weekend ×1.5/×2 | 84.9 / 85.1 | ≥ pooled −5 pts |
| 11 | idem + vm_diag → vm 10/12/13/15/16/18 | 84.2 / 83.8 / 86.2 / 87.7 / 84.4 / 84.6 ; deltas appariés vs vm14 TOUS CI95 ⊃ 0 | tous ∈ pooled ±6 pts ; aucun delta apparié CI hors 0 (sinon = knife-edge, STOP) |
| 12 | `run_pathboot.py` | moyenne 87.6 / p5 76.7 / **min 71.4** / P(>50%)=100% | min > 60 ; P=100% |
| 13 | micro-ORB | 9,248 poses ; **100% cohortes ≥1** ; backstop **50** | 100% strict ; backstop < 100 |
| 14 | identité comptable | assertions cash-conservation par tentative : 0 levée | STRICT (exact) |
| 15 | `diag_runner_equiv.py` | micro-OFF+backstop = 88.8/87.8/**88.31** (≡ référence cleanroom 88.3) | ±0.5 pt (équivalence moteur) |
| 16 | **ancres de coûts v2.2.1 — MESURÉES specs MT5 10/06** (remplacent les héritées audit, périmées prix) | swap pts: XAU −65.68/−14.53 (mer ×3), JPY +0.96/−20.30 (mer), US100 −637.16/+27.49 (ven), GER40 −393.88/−48.68 (ven) ; comm RT: JPY 0.50 bps, XAU 0.14, indices 0 ; **G0: 4/4 facturés 10→11/06 reconstruits au centime** | exact (pts) ; G0 au centime ($±0.005) |
| 17 | borne théorique compteur | micro-ORB coûte ≤ 2 pts vs token idéal (87.0 vs 88.3) | Δ ∈ [0 ; 2.5] |
| 18 | branches ORB_RT_BPS (rerun exact ledger) | 0.61→OOS $2,897 EV +$1,125 ; 1.0→$2,807 +$1,063 ; 1.5→$2,578 +$965 ; off→$1,262 +$295-310 | ±10% ; EV > 0 sur tout le domaine |
| 19 | `make_spec_yaml.py` (lit `recost/summary.json`, jamais retapé) | spec_v22.yaml régénéré BYTE-IDENTIQUE, sha256 **`56fbdde78a2e5c4365e8e0f5bbda06d3697a198beccbcbf2dd02deea0eb27928`** *(v2.2 : dd6ab1268020…)* ; drift-check PASS | toute divergence = la spec a bougé sans re-gel → STOP ; ne JAMAIS éditer le yaml à la main |
| 20 | `ea/brain.py --check` + `ea/make_spec_mqh.py` | brain: spec OK v2.2.1 + pins présents + REJET yaml altéré ; mqh BYTE-IDENTIQUE sha256 **`2fc65503ef666d5221ca2d75b5fc2683afcbd454e7037bf29fe750e13a007cc2`** *(v2.2 : 1d834546…)* ; EA OnInit logge `SPEC OK v2.2.1 sha 56fbdde78a2e…` ; **re-déposer ea/spec_v22.sha256 dans MQL5/Files** | brain doit REFUSER tout écart ; mqh jamais édité à la main ; EA sans le fichier Files = refuse de trader |
| 21 | **v2.2.1 gates re-cost** (`run_recost_v221.py` + `ftmo_live/tests/`) | G0 swap PASS 4/4 ; G1 repro 87.01 EXACT ; G2: pooled comm −1.73 / swaps-fwd −1.08, **appariés CI95 ⊃ 0 (ns)** → challenge contractuel INCHANGÉ, marge policy ne touche pas p(pass) ✓ ; bornes live: swap hors borne → alerte (`test_live_bounds.py` 8 tests) ; ftmo_live **154/154 PASS** | G0 au centime ; G1 exact ; tout delta apparié challenge CI hors 0 = STOP ; tests 100% |

**Procédure ORB_RT_BPS (verdict démo N=60, §9-§10 AMENDEMENT)** : éditer `config_v22.py:ORB_RT_BPS`
(float bps all-in mesuré), relancer la SECTION funded → nouvelles ancres #4b/#5b, EV à la valeur
mesurée (table #18 = pré-calcul). Le challenge (#1-3, 6-13) est INSENSIBLE à ce paramètre par
construction v2.2 — toute dérive = bug, STOP. Branche kill RETIRÉE ; gate 2 (mécanique swap)
**PASS** v2.2.1 (§10).

**Convention v2.2.1** : le backtest contractuel garde le panel swap HISTORIQUE (donnée) ; les
points mesurés datés gouvernent le modèle FORWARD (forecast live, bornes EA `measured_specs`,
extension panels) ; commissions incluses au modèle forward + funded (#4b/#5b). Projection
forward-constante sur 2013-2026 = diagnostic seulement (pénalise l'ère ZIRP, IS −3.0).
