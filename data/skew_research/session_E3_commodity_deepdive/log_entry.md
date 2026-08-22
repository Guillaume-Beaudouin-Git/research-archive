# Entrée de log — session_E3_commodity_deepdive (CANDIDAT, HOME commodity ; à merger par le mainteneur)
*Périmètre session_E3 uniquement. Ne PAS écrire dans le log partagé. Rien figé. Dédup vs session_E/E2 flaggé. Phases 2-3 à venir (même session).*

---

## [2026-06] Commodity deep-dive Phase 1 + MC book

**Mandat** : moteur TSMOM mort (F), intraday-flat vide (G) → commodities = endroit le plus plausible. L37 carry-sign. Swaps mesurés. Détail : `data/skew_research/session_E3_commodity_deepdive/exploration_2026-06.md`.

**Verdict : pas de moteur commodity ; un grinder saisonnier lent low-levier, oil mort.**

- **GATE-0 (catch majeur)** : `commod_daily` USOIL = future WTI (min −$37,6 avr-2020) ≠ CFD cash FTMO. Bloque OOS-2020 + risque double-compte carry. **Oil [C] data-bloqué.**
- **Seasonals carry-alignés** : COFFEE long-Jul **revit** (NET +179bp t1,96 ; swap mesuré ≈0 vs mon −5bp/nuit E2 faux) mais fragile (edge gel-2020, pre-2020 +98). PRECIOUS-Jan robuste (NET +355bp t2,82). Aug/Sep faibles → Janvier seul. Soybean/cocoa/wheat shorts **mal-timés** (bon signe carry, mauvais mois — soy monte en Oct). Wheat long-May combat son carry.
- **[B]/[C] oil moteur = MORT** : carry-sign a flippé contango mars-2020 et est sorti (75% flat) MAIS SR −0,05, MaxDD −93%, 2020 −65% (basis mensuel sort trop tard) ; **oil trop violent pour caps FTMO**. « +25%/an » naïf = artefact carry statique. Carry L37 réel mais véhicule inutilisable.
- **MC book (précieux-Jan + coffee-Jul, 2 fenêtres)** : L1 95,9%/5ans, L2 85,7%/<1%breach/2ans, L≥3 32%+ breach. Densité aide (8→5 ans) mais ne dissout pas la sparsité ; **grinder lent, pas moteur** ; cell L2 dépend de coffee fragile.

**Candidats-leçons (nommés) :**
- « GATE-0 série-vs-CFD : le future WTI (négatif 2020) ≠ CFD cash — réconcilier avant tout net oil ».
- « Carry L37 réel mais l'oil trop violent pour les barrières FTMO » (MaxDD −90%, carry-sign mensuel sort trop tard).
- « Carry statique × régime = surcompte » (+20% appliqué en contango = faux +25%/an ; carry time-varying obligatoire).
- « Coffee revit avec le swap mesuré ; swap générique de classe = faux » (carry par instrument).
- « Short carry-aligné ≠ short au bon mois » (signe carry correct mais glut-decline pas dans le mois pré-spec).
- « Densité 2-fenêtres aide mais ne fait pas un moteur » (Jan+Jul : 8→5 ans, L≥3 buste).

**Verdict structure** : commodity = topping décorrélé skew+ low-levier (précieux-Jan ± coffee-Jul) sur une structure (A), PAS le moteur déployable espéré. Piste carry-oil fermée (violence instrument).

**Phases 2-3 à venir (même session)** : [D] trend long-only oil (exige CFD cash réel), [E] overlay COT/inventaire 18y, [F] event ag. PRESPEC + gates, additionnalité au book Phase-1.

**Statut** : 0 jour live, backtest. GATE-0 série/swap, HAC lag-6, DSR déflaté, MC 20k. Réconcilié archive (session_E/E2/F — pas de re-preuve). Écrit uniquement dans `session_E3_commodity_deepdive/`, non touché aux autres sessions ni `overnight_research/`. Ne pas merger sans revue.
