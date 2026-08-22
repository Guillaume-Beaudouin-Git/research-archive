"""
Module 3 demonstration runner. Trains the linear REINFORCE agent through a sliding
walk-forward on gold H1 with the video's reward, checkpoint selection and
consistency gate — and, crucially, benchmarks every fold against always-long /
always-short to expose the gold secular-bull (long-bias) confound.

Run folds in subsets to stay within the sandbox time limit:
    python run_demo.py train 0 1 2
    python run_demo.py train 3 4
    python run_demo.py aggregate
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from engine import data  # noqa: E402
from env import build_features, GoldTradingEnv  # noqa: E402
from agent import train_fold, evaluate, evaluate_constant  # noqa: E402
from walkforward import sliding_folds, consistency_gate  # noqa: E402

RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)
FOLDS_FILE = RESULTS / "folds.json"
CFG = dict(train=6000, val=1500, test=1500, n_folds=5, epochs=20, lr=0.05, gamma=0.99)


def make_env():
    gold = data.load_h1("XAUUSD")
    feats, atr = build_features(gold)
    g = gold.loc[feats.index]
    env = GoldTradingEnv(feats.to_numpy(np.float32), g["open"].to_numpy(), g["high"].to_numpy(),
                         g["low"].to_numpy(), g["close"].to_numpy(), atr.to_numpy())
    return env, feats, g


def _save(records):
    existing = {}
    if FOLDS_FILE.exists():
        existing = {r["fold"]: r for r in json.load(open(FOLDS_FILE))}
    for r in records:
        existing[r["fold"]] = r
    json.dump([existing[k] for k in sorted(existing)], open(FOLDS_FILE, "w"))


def train_folds(idxs):
    env, feats, g = make_env()
    folds = sliding_folds(len(feats), CFG["n_folds"], CFG["train"], CFG["val"], CFG["test"])
    out = []
    for i in idxs:
        f = folds[i]
        pol, curve, score = train_fold(env, env.obs_dim, f["train"], f["val"],
                                       epochs=CFG["epochs"], lr=CFG["lr"], gamma=CFG["gamma"], seed=i)
        rng = np.random.default_rng(123)
        ag_R, ag_nt = evaluate(env, pol, *f["test"], rng)
        lo_R, _ = evaluate_constant(env, 1, *f["test"])
        sh_R, _ = evaluate_constant(env, 2, *f["test"])
        ts0, ts1 = f["test"]
        bh = float(g["close"].iloc[ts1 - 1] / g["close"].iloc[ts0] - 1)
        rec = dict(fold=i, test_start=str(g.index[ts0].date()), test_end=str(g.index[ts1 - 1].date()),
                   agent_test_R=float(ag_R), agent_trades=int(ag_nt),
                   always_long_R=float(lo_R), always_short_R=float(sh_R),
                   gold_bh_test=bh, select_score=float(score), curve=curve)
        _save([rec])  # incremental: a later-fold crash never loses earlier folds
        print(f"fold{i} [{rec['test_start']}..{rec['test_end']}] agentR={ag_R:+.2f}(nt={ag_nt}) "
              f"longR={lo_R:+.2f} shortR={sh_R:+.2f} goldBH={bh:+.1%}")


def aggregate():
    recs = json.load(open(FOLDS_FILE))
    ag = np.array([r["agent_test_R"] for r in recs])
    lo = np.array([r["always_long_R"] for r in recs])
    sh = np.array([r["always_short_R"] for r in recs])
    summary = dict(
        n_folds=len(recs), cfg=CFG,
        agent_mean_test_R=float(ag.mean()), agent_pos_folds=int((ag > 0).sum()),
        always_long_mean_test_R=float(lo.mean()), always_long_pos_folds=int((lo > 0).sum()),
        agent_gate=consistency_gate(ag), always_long_gate=consistency_gate(lo),
        corr_agent_long=(float(np.corrcoef(ag, lo)[0, 1]) if len(recs) > 2 else None),
        gold_bh_mean=float(np.mean([r["gold_bh_test"] for r in recs])),
    )
    json.dump(summary, open(RESULTS / "module3_summary.json", "w"), indent=2)
    print(json.dumps(summary, indent=2))

    x = np.arange(len(recs)); w = 0.27
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - w, ag, w, label="RL agent", color="seagreen")
    ax.bar(x, lo, w, label="always-long", color="steelblue")
    ax.bar(x + w, sh, w, label="always-short", color="indianred")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"F{r['fold']}\n{r['test_start'][:7]}" for r in recs], fontsize=8)
    ax.set_ylabel("Test-window realized R")
    ax.set_title("Module 3 — OOS test R per fold: RL agent vs always-long / always-short (gold H1)")
    ax.legend(); ax.grid(alpha=0.25, axis="y")
    fig.tight_layout(); fig.savefig(RESULTS / "fig_A_folds.png", dpi=120); plt.close(fig)

    curve = np.array(recs[-1]["curve"])
    if curve.size:
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.plot(curve[:, 0], curve[:, 1], label="train-tail score", color="steelblue")
        ax.plot(curve[:, 0], curve[:, 2], label="validation score", color="crimson")
        ax.plot(curve[:, 0], curve[:, 3], label="min (selection metric)", color="black", ls="--")
        ax.set_xlabel("epoch"); ax.set_ylabel("greedy realized R")
        ax.set_title("Module 3 — checkpoint selection curves (last fold)")
        ax.legend(); ax.grid(alpha=0.25)
        fig.tight_layout(); fig.savefig(RESULTS / "fig_B_selection.png", dpi=120); plt.close(fig)
    print("figures:", [p.name for p in sorted(RESULTS.glob('fig_*.png'))])


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "train":
        train_folds([int(x) for x in sys.argv[2:]])
    elif cmd == "aggregate":
        aggregate()
    else:
        train_folds(list(range(CFG["n_folds"])))
        aggregate()
