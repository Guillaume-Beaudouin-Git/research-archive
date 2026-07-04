# AUDIT INDÉPENDANT — gate J1 + patch brain.py (author ≠ auditor)

**VERDICT : APPROUVÉ (déployable)** — 1 durcissement recommandé (appliqué) + 2 caveats non-bloquants.
Audit read-only, adversarial, 13 items (A1-A6 étude, B7-B13 patch). Tous les chiffres re-dérivés
indépendamment des artefacts bruts + un run moteur frais. 2026-07-04.

## Confirmé (re-dérivé)
- **EQUIV PASS pooled=87.01**, 0 mismatch, 462 cohorts (233 IS/229 OOS).
- Causalité/hystérésis : latch à close≥160 (160.00 inclus), tout close>155 reset le compteur,
  reprise au 10e ≤155 consécutif ; `suspend_causal == off_state.shift(1)` élémentwise → **pas de
  look-ahead**. `lib._off_state` ≡ étude `gate.off_state` (sorties numériquement identiques).
- Δ appariés (block=10, 3000, seed=23) : FULLOFF Δp **−7.58 [−12.99,−2.81]** / ΔEV **−$87.6** ;
  GATE160 Δp **+0.65 [0.00,+1.95]** / ΔEV **+$12.6 [0,+35.2]** ; **3 flips, tous échec→réussite, 0
  pénalisée** ; affordable=TRUE. FULLOFF −7.58/−$88 = ablation J1 v2.3/levcap connue.
- Queue in-sample **byte-identique** baseline vs GATE160 (pire gap −2822.38 = Grexit 2015-06-29,
  USDJPY≈123.9 = PAS un jour zone) → framing « coût mesuré ≈0, protection de queue prospective » honnête.
- Gel pré-reg vérifié git : `PREREGISTRATION.md` committé `bdf7281`, jamais modifié après ; résultats
  dans `23cf6c5`.
- **EA flatten-and-stay-flat** confirmé sur le mq5 gelé (`Do2205Rebalance:1067` → `TradeLegTo(1,0)` →
  `CloseLegLots` si ouvert, no-op si flat). EA/mqh/yaml **inchangés** (diff `5fcbae1..5616a85` vide sur
  `*.mq5 *.mqh *.yaml`). Patch = exactement 4 fichiers.
- Zéro effet de bord destructeur : scale weight-independent ; US100/GER40 via `on_w` ; seul couplage =
  margin-cap qui **relâche** (FULLOFF risk_jpy 0.288→0 avec risk_gold 0.323→0.438 = relâchement bénin).
- Fail-safe bon sens : config absente/corrompue→défauts ; enabled=false→trade ; data JPY illisible→
  **fail-CLOSED**. targets.json atomique (mkstemp+os.replace), audit blob JSON-sérialisable. Pas de
  chemin dur/secret. Interactions (governor/ON-legs/micro-ORB/swap forecast) propres.
- Confirmation frappante : le 2024-07-05, le brain **non-patché** sizerait J1 à **+1.13 (≈16× long =
  régime du breach)** ; patché → **0**.

## Findings
1. **B9 (durcissement recommandé) — APPLIQUÉ.** Le retour du chemin succès de `evaluate()` appelait
   `.date()`/`float()` hors du try/except → « never raises » non littéral (AttributeError reproductible
   sur index non-datetime). Inatteignable en prod (cache toujours DatetimeIndex ; `signals.weights_for`
   frappe le même `.date()` avant le gate), et si ça tirait, `main()` catch → brain ERROR → EA « gestion
   seule » **tient J1 ouvert (fail-OPEN)**. **Correctif appliqué** : `evaluate()` = wrapper `try/_evaluate`,
   toute exception inattendue → **fail-CLOSED (suspend=True, reason=failclosed_exception)**. Test ajouté
   (`test_evaluate_never_raises_failclosed`, 13/13 pass). Convertit le fail-OPEN théorique en fail-CLOSED.
2. **Caveat data-provenance (non-bloquant).** La décision live dépend du close USDJPY du cache live vs
   la convention du panel backtest (EET, MT5). Immatériel : 160 = ligne ronde à marge pip, pas knife-edge ;
   un écart sous-pip source/tz ne compte qu'à ~1 pip de 160.00.
3. **Architectural (préexistant, hors patch).** L'overlay vaut ce que vaut le run brain 21:50 : un brain
   qui ne tourne pas → EA « gestion seule » tient J1. Mitigé par breaker M5/watchdog ; le gate est
   fail-CLOSED dès que le brain tourne.

## Note seuil (argument POUR 160)
GATE158 flippe 4↑/1↓ (net identique mais pas à sens unique) ; GATE160 = 3↑/0↓ (propre, une seule
direction). Le seuil déployé (160) est le plus net.
