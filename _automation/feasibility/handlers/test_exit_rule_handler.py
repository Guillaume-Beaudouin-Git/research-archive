"""
Test d'intégration de l'ExitRuleHandler contre les vraies données NQ.
À lancer depuis la racine du repo :

    cd ~/Desktop/Algo_claude
    /usr/bin/python3 _automation/feasibility/handlers/test_exit_rule_handler.py

Ce script :
  1. Vérifie que les imports recherche fonctionnent (_IMPORT_OK True).
  2. Lance le handler sur 3 hypothèses synthétiques (tp, time-stop, dollar).
  3. Exécute les 3 niveaux + le rapport sur données réelles.
  4. Vérifie que le baseline reproduit bien iter_10 (sanity).

Si _IMPORT_OK est False, le script affiche l'erreur d'import à corriger
(probablement un chemin ou un module manquant) AVANT d'intégrer au registry.
"""
import sys
import tempfile
from pathlib import Path

# Import du handler via le package normal.
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from _automation.feasibility.handlers.exit_rule_handler import (
    ExitRuleHandler, _IMPORT_OK, _IMPORT_ERR,
)


def _md(text: str) -> str:
    f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False)
    f.write(text)
    f.close()
    return f.name


def main() -> None:
    print("=" * 70)
    print("TEST INTÉGRATION ExitRuleHandler")
    print("=" * 70)
    print(f"_IMPORT_OK = {_IMPORT_OK}")
    if not _IMPORT_OK:
        print(f"\n❌ Imports recherche KO : {_IMPORT_ERR}")
        print("   Corrige le chemin/module avant d'intégrer au registry.")
        sys.exit(1)
    print("✓ Imports recherche OK (data.cache, engine, iter_05)\n")

    # Cas de test : modif réaliste sur Strategy C.
    hypotheses = {
        "TP 2.0R": "On Strategy C NQ (iter_10), test raising the take-profit to 2.0R.",
        "Time stop 11:30": "For the NQ opening range strategy, move the time stop from 12:30 to exit at 11:30.",
        "Dollar stop $300": "On Strategy C NQ, tighten the dollar stop to $300 cap.",
    }

    for label, text in hypotheses.items():
        print("-" * 70)
        print(f"HYPOTHÈSE : {label}")
        print("-" * 70)
        p = _md(text)
        h = ExitRuleHandler(p)

        if not ExitRuleHandler.classify(p):
            print("  ⚠ classify=False — le handler ne s'activerait pas. Skip.")
            continue

        a = h.run_level_A()
        print(f"  Level A : verdict={a.get('verdict')} pass={a.get('pass')}")
        if a.get("verdict") == "REQUIRES_HUMAN":
            print(f"            reason={a.get('reason', '')[:80]}")
            continue
        if "baseline" in a and "variant" in a:
            b, v = a["baseline"], a["variant"]
            print(f"            baseline: n={b['n_trades']} pnl=${b['total_pnl_usd']:.0f} SR={b['sharpe_hac']:.2f}")
            print(f"            variant : n={v['n_trades']} pnl=${v['total_pnl_usd']:.0f} SR={v['sharpe_hac']:.2f}")

        b = h.run_level_B()
        if not b.get("skipped"):
            print(f"  Level B : pass={b.get('pass')} "
                  f"WF_var={b.get('wf_var_pct_positive')}% "
                  f"WF_base={b.get('wf_base_pct_positive')}% "
                  f"p_ev={b.get('bootstrap_p_ev_zero')}")
        else:
            print(f"  Level B : skipped ({b.get('reason')})")

        c = h.run_level_C()
        if not c.get("skipped"):
            print(f"  Level C : pass={c.get('pass')} n_pass={c.get('n_pass')}/3 "
                  f"(cost={c.get('cost_stress_pass')} "
                  f"regime={c.get('regime_concentration_pass')} "
                  f"ablation={c.get('ablation_beats_baseline')})")
        else:
            print(f"  Level C : skipped ({c.get('reason')})")

        # Rapport
        report = h.generate_report()
        out = REPO / "_automation" / "feasibility" / f"_TEST_report_{label.replace(' ', '_').replace('$', '')}.md"
        out.write_text(report)
        print(f"  Rapport écrit : {out.name} ({len(report)} chars)")
        print()

    print("=" * 70)
    print("✓ TEST TERMINÉ")
    print("  Vérifie les rapports _TEST_report_*.md générés dans _automation/feasibility/")
    print("  Si les baselines reproduisent iter_10 (n_trades ~346, PnL cohérent),")
    print("  le handler est prêt à intégrer au HANDLER_REGISTRY.")
    print("  Pense à supprimer les _TEST_report_*.md après vérification.")
    print("=" * 70)


if __name__ == "__main__":
    main()
