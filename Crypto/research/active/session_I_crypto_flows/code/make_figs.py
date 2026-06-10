"""Figures for the session report: I-1 dose-response, event-time profile, placebo hist."""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import lib_data as ld

FIGS = ld.ROOT / "figures"
FIGS.mkdir(exist_ok=True)


def main() -> None:
    r = json.load(open(ld.ROOT / "i1_results.json"))

    dec = r["stage_b"]["deciles"]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([d["decile"] for d in dec], [d["gross_mean"] for d in dec], color="#27496d")
    ax.set_xlabel("unlock-size decile (by % of circulating proxy)")
    ax.set_ylabel("mean gross SHORT drift, bps (T-7 close -> T+3 close)")
    ax.set_title(f"I-1 dose-response — Spearman rho={r['stage_b']['spearman_size_gross']:.3f} "
                 f"(p={r['stage_b']['spearman_p']:.3f})")
    ax.axhline(0, color="k", lw=0.7)
    fig.tight_layout()
    fig.savefig(FIGS / "i1_dose_response.png", dpi=110)

    prof = r["event_time_profile_descriptive"]
    ks = sorted(int(k) for k in prof)
    cum = np.nancumsum([prof[str(k)] for k in ks])
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(ks, cum, color="#27496d")
    ax.axvline(0, color="r", lw=0.8, ls="--", label="unlock day")
    ax.axvspan(-7, 3, color="orange", alpha=0.15, label="pre-registered window")
    ax.set_xlabel("event day offset")
    ax.set_ylabel("cumulative mean log-return, bps (DESCRIPTIVE)")
    ax.set_title("I-1 event-time profile (-30..+30d) — descriptive only")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGS / "i1_event_profile.png", dpi=110)

    pl = ld.CACHE / "i1_placebo_means.npy"
    if pl.exists() and "stage_d" in r:
        arr = np.load(pl)
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(arr, bins=50, color="#9fb8cd")
        ax.axvline(r["stage_d"]["real_mean"], color="r", lw=2, label=f"real {r['stage_d']['real_mean']:+.1f}")
        ax.axvline(r["stage_d"]["placebo_p95"], color="k", ls="--", label=f"p95 {r['stage_d']['placebo_p95']:+.1f}")
        ax.set_xlabel("placebo-calendar pooled net mean (bps/event)")
        ax.set_title("I-1 K2 placebo distribution (1000 vol-matched calendars)")
        ax.legend()
        fig.tight_layout()
        fig.savefig(FIGS / "i1_placebo.png", dpi=110)
    print("figures written to", FIGS)


if __name__ == "__main__":
    main()
