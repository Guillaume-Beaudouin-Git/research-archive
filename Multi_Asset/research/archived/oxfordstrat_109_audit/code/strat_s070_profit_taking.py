"""
Strategy 70/109 — Profit-Taking: Perry Kaufman (Test Period 1, 1980-2011). Rating N/A (study).
https://oxfordstrat.com/trading-strategies/profit-taking-1/

Base system: EMA(EMA_Length) turns up (EMA[i]>EMA[i-1] & EMA[i-1]<EMA[i-2]) -> buy @close;
turns down -> sell @close. Exit: %-TARGET (close >= entry*(1+T/100)) + ATR stop(6).
The STUDY: does a profit target help? Source CONCLUSION (42 futures): "simple profit targets
REDUCE absolute AND risk-adjusted returns" (contradicts Kaufman's 3-market small sample).
Archetype = EMA-turn TREND entry = beta; the target is an exit overlay. We (a) run the gates
on the base case and (b) reproduce the finding by sweeping Target_Exit incl. a no-target case.
Self-contained sim (entry @close on EMA turn). Reuses ftmo_lab.atr + beta_bench.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb

ATR_LEN, ATR_STOP, TIME_CAP = 20, 6.0, 120
EMA_REP, TGT_REP = 40, 20.0           # EMA_Length, Target_Exit % (reference)
uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}


def simulate_pt(df, ema_len, target_pct, *, cost_bps=2.0, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values
    ema = pd.Series(c, index=df.index).ewm(span=ema_len, adjust=False).mean().values
    n = len(df); idx = df.index; trades = []; i = 2
    up = lambda k: ema[k] > ema[k - 1] and ema[k - 1] < ema[k - 2]
    dn = lambda k: ema[k] < ema[k - 1] and ema[k - 1] > ema[k - 2]
    while i < n - 1:
        d = 1 if up(i) else (-1 if dn(i) else 0)
        if d == 0 or not np.isfinite(A[i]) or A[i] <= 0:
            i += 1; continue
        if fill == 'stop':       eb = i; entry = c[eb]
        elif fill == 'next_open': eb = i + 1; entry = o[eb] if eb <= n - 1 else np.nan
        else: raise ValueError(fill)
        if eb > n - 1 or not np.isfinite(entry):
            i += 1; continue
        risk0 = A[i] * ATR_STOP; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        stop = entry - d * risk0
        tgt = entry * (1 + d * target_pct / 100.0) if target_pct is not None else None
        last = min(eb + TIME_CAP, n - 1); exit_p = exit_j = None
        for j in range(eb, last + 1):
            if d == 1 and l[j] <= stop:  exit_p, exit_j = stop, j; break
            if d == -1 and h[j] >= stop: exit_p, exit_j = stop, j; break
            if tgt is not None:
                if d == 1 and c[j] >= tgt:  exit_p, exit_j = c[j], j; break
                if d == -1 and c[j] <= tgt: exit_p, exit_j = c[j], j; break
            if j == last: exit_p, exit_j = c[j], j; break
        trades.append(lab._trade(idx[eb], idx[exit_j], 'x', d, d * (exit_p - entry) / risk0 - cost_R, exit_j - eb))
        i = exit_j + 1
    return pd.DataFrame(trades)


def run_pt(ema_len=EMA_REP, target_pct=TGT_REP, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_pt(df, ema_len, target_pct, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))


if __name__ == "__main__":
    pool = run_pt(); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_pt(fill='next_open'))
    print(f"=== S070 Profit-Taking / EMA-turn trend (EMA={EMA_REP} Target={TGT_REP}%) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(close) {pm['sharpe']:+.2f} -> open[i+1] {m_no['sharpe']:+.2f}")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    # reproduce the source finding: targets vs no-target
    print("PROFIT-TARGET STUDY (expR / Sharpe vs Target_Exit%):")
    for tg in [5.0, 10.0, 20.0, 50.0, None]:
        m = lab.trade_metrics(run_pt(EMA_REP, tg)); print(f"    target={str(tg):5s}: expR {m['expR']:+.4f} Sh {m['sharpe']:+.2f}")
    EMAs = [10, 40, 80, 160]; TGs = [10.0, 20.0, 50.0]
    sg = np.full((len(EMAs), len(TGs)), np.nan)
    for a, em in enumerate(EMAs):
        for b_, tg in enumerate(TGs):
            sg[a, b_] = lab.trade_metrics(run_pt(em, tg))['sharpe']
    pd.DataFrame(sg, index=[f"E{x}" for x in EMAs], columns=[f"T{x}" for x in TGs]).to_csv("s070_sensitivity_expectancy.csv")
    print("grid Sharpe (EMA x Target):\n" + pd.DataFrame(sg, index=[f"E{x}" for x in EMAs], columns=[f"T{x}" for x in TGs]).round(2).to_string())
    res = lab.run_gates(lambda fill='stop': run_pt(fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("GATES:")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") + (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s070_gates.csv", index=False)
