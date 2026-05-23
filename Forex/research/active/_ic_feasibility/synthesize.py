"""
PHASE 1.5 Task 6 — Synthesis: GO A / GO B / GO BOTH / STOP
============================================================
Reads results from Tasks 3, 4, 5 and produces a decision matrix.
Prints _ic_feasibility.md section with all facts sourced from calculations.
"""

from __future__ import annotations
import json
from pathlib import Path

OUT_DIR = Path(__file__).parent
ACTIVE_DIR = OUT_DIR.parent

RES_A = OUT_DIR / "results_angle_a.json"
RES_B = OUT_DIR / "results_angle_b.json"
IC_FEASIBILITY_MD = ACTIVE_DIR / "_ic_feasibility.md"


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def best_horizon(horizons: dict) -> tuple[str, dict]:
    """Return horizon with strongest |t_HAC_NW6|."""
    if not horizons:
        return ("none", {})
    return max(horizons.items(), key=lambda x: abs(x[1].get("t_HAC_NW6", 0)))


def gate_summary_a(res: dict, pairs: list[str]) -> dict:
    """Aggregate Angle A results across pairs + signal variants."""
    best_t, best_ic, best_h, best_v, passed = 0.0, 0.0, "", "", []
    for p in pairs:
        pr = res.get(p, {})
        for variant in ("close_based", "hl_based"):
            vd = pr.get(variant, {})
            if vd.get("gate") == "FAIL_N" and not vd.get("horizons"):
                continue
            hrs = vd.get("horizons", {})
            h, hd = best_horizon(hrs)
            t = abs(hd.get("t_HAC_NW6", 0))
            ic = hd.get("IC_spearman", 0)
            if t > best_t:
                best_t, best_ic, best_h, best_v = t, ic, h, f"{p}/{variant}"
        if pr and pr.get("error") != "no_data":
            passed.append(p)
    return {"pairs_passed": passed, "best_t_HAC": best_t, "best_IC": best_ic,
            "best_horizon": best_h, "best_variant": best_v}


def gate_summary_b(res: dict, pairs: list[str]) -> dict:
    """Aggregate Angle B results across pairs."""
    best_t, best_ic, best_h, passed = 0.0, 0.0, "", []
    for p in pairs:
        pr = res.get(p, {})
        if pr.get("gate") == "FAIL_N":
            continue
        hrs = pr.get("horizons", {})
        h, hd = best_horizon(hrs)
        t = abs(hd.get("t_HAC_NW6", 0))
        ic = hd.get("IC_spearman", 0)
        if t > best_t:
            best_t, best_ic, best_h = t, ic, h
        passed.append(p)
    return {"pairs_passed": passed, "best_t_HAC": best_t, "best_IC": best_ic, "best_horizon": best_h}


def main():
    res_a = load(RES_A)
    res_b = load(RES_B)

    if not res_a and not res_b:
        print("ERROR: No results found. Run ic_angle_a.py and ic_angle_b.py first.")
        return

    pairs = ["EURUSD", "GBPUSD"]
    a_summary = gate_summary_a(res_a, pairs)
    b_summary = gate_summary_b(res_b, pairs)
    dual_corr = res_a.get("dual_pair_correlation", {})

    # Decision logic
    a_pass = a_summary["best_t_HAC"] > 1.65 and a_summary["best_IC"] > 0
    b_pass = b_summary["best_t_HAC"] > 1.65 and b_summary["best_IC"] > 0
    a_weak = 1.0 < a_summary["best_t_HAC"] <= 1.65 and a_summary["best_IC"] > 0
    b_weak = 1.0 < b_summary["best_t_HAC"] <= 1.65 and b_summary["best_IC"] > 0

    if a_pass and b_pass:
        decision = "GO BOTH"
        rationale = "Both angles show statistically detectable IC (t_HAC > 1.65). Develop both for portfolio diversification."
    elif a_pass and not b_pass:
        decision = "GO A"
        rationale = f"Angle A passes IC gate (t_HAC={a_summary['best_t_HAC']:.2f}). Angle B weak/fail."
    elif b_pass and not a_pass:
        decision = "GO B"
        rationale = f"Angle B passes IC gate (t_HAC={b_summary['best_t_HAC']:.2f}). Angle A weak/fail."
    elif a_weak or b_weak:
        decision = "WEAK — CONDITIONAL GO"
        rationale = "Neither angle strongly passes. Consider: extend sample, refine signal, or archive."
    else:
        decision = "STOP"
        note_a = f" Angle A: IC={a_summary['best_IC']:+.4f} (wrong direction — reversal not momentum)." if abs(a_summary["best_t_HAC"]) > 1.0 else ""
        rationale = f"Both angles fail IC gate (positive IC + t_HAC > 1.65 not achieved on any horizon/pair).{note_a} Archive FX ORB/news-fade as formulated."

    print("\n" + "="*60)
    print(f"PHASE 1.5 SYNTHESIS → {decision}")
    print("="*60)

    print(f"\nAngle A (London ORB):")
    print(f"  Pairs passed: {a_summary['pairs_passed']}")
    print(f"  Best t_HAC: {a_summary['best_t_HAC']:.2f} @ {a_summary['best_horizon']} ({a_summary['best_variant']})")
    print(f"  Best IC_spearman: {a_summary['best_IC']:+.4f}")

    print(f"\nAngle B (News-Fade):")
    print(f"  Pairs passed: {b_summary['pairs_passed']}")
    print(f"  Best t_HAC: {b_summary['best_t_HAC']:.2f} @ {b_summary['best_horizon']}")
    print(f"  Best IC_spearman: {b_summary['best_IC']:+.4f}")

    close_corr: dict = {}
    if dual_corr:
        close_corr = dual_corr.get("close", {})
        n_both = close_corr.get("N_both", "N/A")
        p_same = close_corr.get("P_same_direction") or 0.0
        print(f"\nEUR/GBP Breakout Correlation:")
        print(f"  Days both break out: {n_both}")
        print(f"  Same direction: {p_same:.1%}")
        if p_same > 0.75:
            print(f"  FINDING: High correlation ({p_same:.1%}) — dual-pair filter removes only {(1-p_same):.1%} of signals")
            print(f"           Marginal confirmation value. Single-pair may be preferable.")
        else:
            print(f"  FINDING: Moderate correlation ({p_same:.1%}) — dual-pair filter meaningful ({(1-p_same):.1%} removed)")

    print(f"\nDecision: {decision}")
    print(f"Rationale: {rationale}")

    # Build markdown block for _ic_feasibility.md
    summary_md = f"""
## SYNTHESIS — {decision}

### Angle A (London ORB)
- Pairs IC gate passed: {a_summary['pairs_passed']}
- Best t_HAC Newey-West (lag 6): {a_summary['best_t_HAC']:.2f} at {a_summary['best_horizon']}
- Best IC_spearman: {a_summary['best_IC']:+.4f}

### Angle B (News-Fade)
- Pairs IC gate passed: {b_summary['pairs_passed']}
- Best t_HAC Newey-West (lag 6): {b_summary['best_t_HAC']:.2f} at {b_summary['best_horizon']}
- Best IC_spearman: {b_summary['best_IC']:+.4f}

### EUR/GBP Breakout Correlation (Task 4)
- N days both break out: {close_corr.get('N_both', 'N/A')}
- P(same direction): {close_corr.get('P_same_direction', 'N/A')}

### Decision: **{decision}**
{rationale}
"""
    # Append to _ic_feasibility.md
    content = IC_FEASIBILITY_MD.read_text()
    marker = "## TASK 6 — SYNTHESIS"
    if marker in content:
        before = content[:content.index(marker)]
        content = before + f"## TASK 6 — SYNTHESIS\n" + summary_md
    else:
        content += "\n" + f"## TASK 6 — SYNTHESIS\n" + summary_md
    IC_FEASIBILITY_MD.write_text(content)
    print(f"\n_ic_feasibility.md updated with synthesis.")


if __name__ == "__main__":
    main()
