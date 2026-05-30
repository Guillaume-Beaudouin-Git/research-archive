"""
Test d'intégration du RegimeFilterHandler contre les vraies données Strategy A.
À lancer depuis la racine du repo :

    cd ~/Desktop/Algo_claude
    /usr/bin/python3 _automation/feasibility/handlers/test_regime_filter_handler.py

Ce script :
  1. Lance le handler sur 4 hypothèses synthétiques (vol regime, trend, HMM, NQ).
  2. Vérifie le routing : HMM → REQUIRES_HUMAN, NQ → REQUIRES_HUMAN.
  3. Pour les cas testables, exécute les 3 niveaux + le rapport sur données réelles.
  4. Affiche le baseline Sharpe (doit être ~1.3, cohérent avec Strategy A) +
     l'advisory L15.

Attendu (vu L15 et SR_A ~1.33) : les overlays de régime FAIL ou CONDITIONAL,
PAS un PASS franc. Un PASS franc serait suspect et mériterait inspection.
"""
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from _automation.feasibility.handlers.regime_filter_handler import RegimeFilterHandler


def _md(text: str) -> str:
    f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False)
    f.write(text)
    f.close()
    return f.name


def main() -> None:
    print("=" * 70)
    print("TEST INTÉGRATION RegimeFilterHandler")
    print("=" * 70)

    hypotheses = {
        "Vol regime (testable)":
            "Regime filter on Strategy A: condition the crypto TSMOM signal on a "
            "low-volatility regime — only trade when BTC realised vol is low.",
        "Trend regime (testable)":
            "Add a trend-filter regime to Strategy A momentum: only trade when BTC "
            "is above its 100-day moving average.",
        "HMM (→ REQUIRES_HUMAN)":
            "Use a hidden Markov model to detect market regimes and filter the TSMOM signal.",
        "NQ regime (→ REQUIRES_HUMAN)":
            "Regime filter on the NQ opening range: only trade in a trending regime.",
    }

    for label, text in hypotheses.items():
        print("-" * 70)
        print(f"HYPOTHÈSE : {label}")
        print("-" * 70)
        p = _md(text)

        if not RegimeFilterHandler.classify(p):
            print("  ⚠ classify=False — handler inactif. Skip.")
            continue

        h = RegimeFilterHandler(p)
        a = h.run_level_A()
        print(f"  Level A : verdict={a.get('verdict')} pass={a.get('pass')}")
        if a.get("verdict") == "REQUIRES_HUMAN":
            print(f"            reason={a.get('reason', '')[:80]}")
            continue

        base_sr = a.get("baseline_sharpe", float("nan"))
        print(f"            baseline SR={base_sr:.3f}")
        print(f"            L15: {a.get('l15_advisory', '')[:90]}")
        for name, g in a.get("gate_results", {}).items():
            print(f"            {name:10s} ΔSR={g.get('delta_sharpe', float('nan')):+.3f} "
                  f"p={g.get('bootstrap_p_le_zero', float('nan')):.3f} → {g.get('verdict')}")

        b = h.run_level_B()
        if not b.get("skipped"):
            print(f"  Level B : pass={b.get('pass')} best={b.get('best_variant')}")
        else:
            print(f"  Level B : skipped ({b.get('reason')})")

        c = h.run_level_C()
        if not c.get("skipped"):
            print(f"  Level C : pass={c.get('pass')} n_pass={c.get('n_pass')}/4 "
                  f"(switch={c.get('regime_switch_frequency', float('nan')):.1%}/day, "
                  f"in_regime={c.get('in_regime_fraction', float('nan')):.0%})")
        else:
            print(f"  Level C : skipped ({c.get('reason')})")

        report = h.generate_report()
        slug = label.split(" ")[0]
        out = REPO / "_automation" / "feasibility" / f"_TEST_regime_{slug}.md"
        out.write_text(report)
        print(f"  Rapport : {out.name} ({len(report)} chars)")
        print()

    print("=" * 70)
    print("✓ TEST TERMINÉ")
    print("  baseline SR doit être ~1.3 (Strategy A connue).")
    print("  Vu L15, attends-toi à des FAIL/CONDITIONAL sur les overlays, pas un PASS franc.")
    print("  Un PASS franc serait à inspecter (possible overfitting du seuil).")
    print("  Supprime les _TEST_regime_*.md après vérification.")
    print("=" * 70)


if __name__ == "__main__":
    main()
