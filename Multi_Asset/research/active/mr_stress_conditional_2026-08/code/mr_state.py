"""The conditional Nagel test: intraday mean-reversion BY STATE QUANTILE.

The only element added relative to `mr_timezone_repair_2026-08` (384 unconditional
cells, mean -1.78 bps) is the **state conditioning**.  Trade forms are taken as-is
from that archived grid so the two studies differ in exactly one dimension.

Design (pre-registered in ../PREREGISTRATION.md, written before any measurement):
  * state measured at T-1, constant inside session T -> no intra-session leakage;
  * expanding percentile (>=500 prior obs) -> bucket boundaries carry no future info;
  * disjoint legs (L25), delay+1 on ENTRY *and* EXIT (L59), no stop / no bracket;
  * L58 baseline computed INSIDE THE SAME STATE (the trap for this dossier);
  * gate at GROSS, cost_rt = 0;
  * gradient (continuous slope, HAC(6)) is the mechanism test -- not the top quantile.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else CACHE
RNG = np.random.default_rng(20260802)

SPEC = {  # instrument -> (tz, session open minute, session close minute)
    "US500": ("America/New_York", 9 * 60 + 30, 16 * 60),
    "US100": ("America/New_York", 9 * 60 + 30, 16 * 60),
    "US30":  ("America/New_York", 9 * 60 + 30, 16 * 60),
    "GER40": ("Europe/Berlin",    9 * 60,      17 * 60 + 30),
}
TF_MIN = {"5m": 5, "15m": 15, "30m": 30}
H_BY_TF = {"5m": 6, "15m": 4, "30m": 2}
THETAS = {"sma20_z": (1.5, 2.5), "ema20_z": (1.5, 2.5), "vwap_z": (1.5, 2.5),
          "rsi14": (20, 25), "range_fade": (0.8, 0.92)}
MIN_PRIOR = 500          # expanding-percentile burn-in
NQ = 5                   # quintiles


_BARS: dict = {}
_DEV: dict = {}


# --------------------------------------------------------------------------- bars
def rth_bars(name: str, tf: str) -> pd.DataFrame:
    if (name, tf) in _BARS:
        return _BARS[(name, tf)]
    _BARS[(name, tf)] = _rth_bars(name, tf)
    return _BARS[(name, tf)]


def _rth_bars(name: str, tf: str) -> pd.DataFrame:
    tz, om, cl = SPEC[name]
    df = pd.read_parquet(CACHE / f"{name}_M1.parquet")
    idx = df.index.tz_convert(tz)
    mod = idx.hour * 60 + idx.minute
    m = (mod >= om) & (mod < cl) & (idx.dayofweek < 5)
    d = pd.DataFrame({"open": df["open"].values[m], "close": df["close"].values[m]},
                     index=idx[m])
    step = TF_MIN[tf]
    day = d.index.normalize()
    k = ((d.index.hour * 60 + d.index.minute) - om) // step
    grp = [pd.Series(day, index=d.index, name="day"),
           pd.Series(np.asarray(k), index=d.index, name="k")]
    out = pd.DataFrame({"open": d["open"].groupby(grp).first(),
                        "px": d["close"].groupby(grp).last()}).reset_index()
    return out[out["k"] >= 0].reset_index(drop=True)


# -------------------------------------------------------------------------- state
def expanding_pct(s: pd.Series, min_prior: int = MIN_PRIOR) -> pd.Series:
    """Rank of x_t among x_0..x_{t-1} (STRICTLY prior). NaN before `min_prior`."""
    v = s.values.astype(float)
    n = len(v)
    out = np.full(n, np.nan)
    order = np.argsort(v[:0])  # placeholder for clarity
    hist: list[float] = []
    srt = np.empty(n)
    cnt = 0
    for i in range(n):
        if cnt >= min_prior and np.isfinite(v[i]):
            out[i] = np.searchsorted(srt[:cnt], v[i], side="left") / cnt
        if np.isfinite(v[i]):
            pos = np.searchsorted(srt[:cnt], v[i], side="left")
            srt[pos + 1:cnt + 1] = srt[pos:cnt]
            srt[pos] = v[i]
            cnt += 1
    del order, hist
    return pd.Series(out, index=s.index)


def daily_state(name: str) -> pd.DataFrame:
    """Per-session state percentiles P1 (VIX), P2 (realised vol), P3 (intraday dispersion).

    Every value is a function of data through the CLOSE OF THE PREVIOUS SESSION.
    """
    tz, om, cl = SPEC[name]
    df = pd.read_parquet(CACHE / f"{name}_M1.parquet")
    idx = df.index.tz_convert(tz)
    mod = idx.hour * 60 + idx.minute
    m = (mod >= om) & (mod < cl) & (idx.dayofweek < 5)
    px = pd.Series(df["close"].values[m], index=idx[m])
    day = px.index.normalize()

    sess_close = px.groupby(day).last()
    lr = np.log(sess_close).diff()

    # P2: 20-session realised vol, as of the close of T-1 -> shift(1)
    rv = lr.rolling(20, min_periods=20).std().shift(1)

    # P3: mean |5-min return| inside session T-1 -> shift(1)
    p5 = px.resample("5min").last().dropna()
    d5 = p5.index.normalize()
    disp = (np.log(p5).groupby(d5).diff().abs().groupby(d5).mean()).shift(1)
    disp = disp.reindex(sess_close.index)

    # P1: VIX close of T-1
    vix = pd.read_parquet(CACHE / "vix.parquet").set_index("Date")["vix"]
    vix.index = pd.to_datetime(vix.index)
    vixp = expanding_pct(vix)                       # ranked on the VIX calendar
    vix_l = pd.Series(vixp.values, index=vix.index).shift(1)
    key = pd.Index(sess_close.index.tz_localize(None).normalize())
    p1 = pd.Series(vix_l.reindex(key).values, index=sess_close.index)

    out = pd.DataFrame({
        "P1": p1,
        "P2": expanding_pct(rv).values,
        "P3": expanding_pct(disp).values,
        "vix_raw": pd.Series(vix.shift(1).reindex(key).values, index=sess_close.index),
        "rv_raw": rv.values,
    }, index=sess_close.index)
    return out


# ------------------------------------------------------------------------ signals
def compute_dev(df: pd.DataFrame, logic: str) -> np.ndarray:
    px, sess = df["px"], df["day"]
    g = px.groupby(sess)
    if logic in ("sma20_z", "ema20_z", "vwap_z"):
        if logic == "sma20_z":
            anc = g.transform(lambda x: x.rolling(20, min_periods=20).mean())
        elif logic == "ema20_z":
            anc = g.transform(lambda x: x.ewm(span=20, min_periods=20).mean())
        else:
            anc = px.groupby(sess).expanding().mean().reset_index(level=0, drop=True)
        sd = g.transform(lambda x: x.rolling(20, min_periods=20).std())
        return ((px - anc) / sd).values
    if logic == "rsi14":
        d = px.groupby(sess).diff()
        up, dn = d.clip(lower=0), (-d).clip(lower=0)
        ru = up.groupby(sess).transform(lambda x: x.ewm(alpha=1 / 14, min_periods=14).mean())
        rd = dn.groupby(sess).transform(lambda x: x.ewm(alpha=1 / 14, min_periods=14).mean())
        return (100 - 100 / (1 + ru / rd.replace(0, np.nan)) - 50).values
    if logic == "range_fade":
        hi, lo = px.groupby(sess).cummax(), px.groupby(sess).cummin()
        return (((px - lo) / (hi - lo) - 0.5) * 2).values
    raise ValueError(logic)


def build_trades(op, dev, sess, theta, exit_type, H, delay=1):
    """Non-overlapping fade trades. delay+1 on ENTRY and EXIT (both bar OPENs).

    Legs are DISJOINT (L25): dev > +theta -> SHORT, dev < -theta -> LONG.  Neither
    leg is ever obtained by negating the other.  No stop, no bracket -> no barrier
    fill, so the L59 exit-repricing failure mode is structurally absent.
    """
    n = len(op)
    i = 0
    side, ret, dur, ent = [], [], [], []
    while i < n - 2:
        di = dev[i]
        if not (np.isfinite(di) and abs(di) > theta):
            i += 1
            continue
        j = i + delay
        if j >= n - 1 or sess[j] != sess[i]:
            i += 1
            continue
        s = -1.0 if di > 0 else 1.0
        if exit_type == "ts":
            k = j + H
        else:
            k = j
            while k + 1 < n and sess[k + 1] == sess[j]:
                if not np.isfinite(dev[k]) or s * dev[k] >= 0:
                    break
                k += 1
        k = min(k, n - 2)
        while k > j and sess[k + 1] != sess[j]:
            k -= 1
        if k <= j:
            i += 1
            continue
        side.append(s)
        ret.append(s * (op[k + 1] / op[j] - 1.0) * 1e4)
        dur.append(k + 1 - j)
        ent.append(j)
        i = max(k, i + 1)
    return (np.array(side), np.array(ret, float),
            np.array(dur, int), np.array(ent, int))


# --------------------------------------------------------------------- statistics
def hac_t(x, lags: int = 6) -> float:
    x = np.asarray(x, float)
    n = len(x)
    if n < 30:
        return np.nan
    e = x - x.mean()
    s = (e @ e) / n
    for l in range(1, lags + 1):
        s += 2 * (1 - l / (lags + 1)) * ((e[l:] @ e[:-l]) / n)
    return x.mean() / np.sqrt(s / n) if s > 0 else np.nan


def hac_slope(y, x, lags: int = 6):
    """OLS y ~ 1 + x with Newey-West(6). Returns (slope, t, p)."""
    y, x = np.asarray(y, float), np.asarray(x, float)
    ok = np.isfinite(y) & np.isfinite(x)
    y, x = y[ok], x[ok]
    if len(y) < 50 or x.std() == 0:
        return np.nan, np.nan, np.nan
    import statsmodels.api as sm
    r = sm.OLS(y, sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(r.params[1]), float(r.tvalues[1]), float(r.pvalues[1])


def block_boot_diff(a, b, nboot: int = 2000, L: int = 5):
    """Block bootstrap (Politis-Romano style, circular blocks) of mean(b) - mean(a)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 30 or len(b) < 30:
        return np.nan, np.nan
    def draw(x):
        n = len(x)
        nb = int(np.ceil(n / L))
        st = RNG.integers(0, n, size=(nboot, nb))
        idx = (st[:, :, None] + np.arange(L)[None, None, :]).reshape(nboot, -1)[:, :n] % n
        return x[idx].mean(axis=1)
    d = draw(b) - draw(a)
    obs = b.mean() - a.mean()
    p = min(2 * min((d <= 0).mean(), (d >= 0).mean()), 1.0)
    return float(obs), float(p)


def uncond_table(op, sess_code, sess_q, durs_all) -> dict:
    """Pre-compute, for every realised holding length d and every quantile q, the
    UNCONDITIONAL mean of the same trade form (long, holding d) over all bars of
    sessions in q.  Computed once per cell and reused for all 5 quantiles x 2 legs.

    This is the L58 baseline **inside the state** -- the version that bites here,
    because stress sessions have a different unconditional mean by construction.
    """
    n = len(op)
    tab: dict = {}
    for d in np.unique(durs_all):
        a = np.arange(0, n - int(d))
        ok = sess_code[a] == sess_code[a + int(d)]
        rr = (op[a + int(d)] / op[a] - 1.0) * 1e4
        qq = sess_q[a]
        for q in range(1, NQ + 1):
            m = ok & (qq == q)
            tab[(int(d), q)] = float(rr[m].mean()) if m.sum() >= 50 else np.nan
    return tab


def uncond_state(tab: dict, durs, q) -> float:
    if len(durs) == 0:
        return np.nan
    u, w = np.unique(durs, return_counts=True)
    v = np.array([tab.get((int(d), q), np.nan) for d in u], float)
    m = np.isfinite(v)
    return float(np.sum(v[m] * w[m]) / w[m].sum()) if m.any() else np.nan


# ------------------------------------------------------------------------- driver
def run_cell(name, tf, logic, theta, exit_type, proxy, states):
    df = rth_bars(name, tf)
    op = df["open"].values.astype(float)
    if (name, tf, logic) not in _DEV:
        _DEV[(name, tf, logic)] = compute_dev(df, logic)
    dev = _DEV[(name, tf, logic)]
    days = pd.DatetimeIndex(df["day"])
    sess_code = pd.factorize(days)[0]

    st = states[name][proxy]
    pct_by_day = pd.Series(st.values, index=st.index)
    pct_bar = pct_by_day.reindex(days).values                # state of the bar's session
    q_bar = np.floor(np.clip(pct_bar, 0, 0.999999) * NQ) + 1
    q_bar = np.where(np.isfinite(pct_bar), q_bar, np.nan)

    s, r, d, e = build_trades(op, dev, sess_code, theta, exit_type, H_BY_TF[tf])
    if len(r) == 0:
        return None, None, None
    qt, pt = q_bar[e], pct_bar[e]
    keep = np.isfinite(qt)
    s, r, d, e, qt, pt = s[keep], r[keep], d[keep], e[keep], qt[keep], pt[keep]
    if len(r) < 100:
        return None, None, None

    sess_q = np.where(np.isfinite(q_bar), q_bar, -1)
    tab = uncond_table(op, sess_code, sess_q, d)
    rows = []
    for q in range(1, NQ + 1):
        mq = qt == q
        if mq.sum() < 20:
            rows.append(dict(q=q, n=int(mq.sum())))
            continue
        L, S = r[mq & (s > 0)], r[mq & (s < 0)]
        uL = uncond_state(tab, d[mq & (s > 0)], q) if len(L) else np.nan
        uS = uncond_state(tab, d[mq & (s < 0)], q) if len(S) else np.nan
        rows.append(dict(
            q=q, n=int(mq.sum()), m=float(r[mq].mean()), t=hac_t(r[mq]),
            nL=len(L), mL=float(L.mean()) if len(L) else np.nan, tL=hac_t(L),
            exL=float(L.mean() - uL) if len(L) else np.nan,
            nS=len(S), mS=float(S.mean()) if len(S) else np.nan, tS=hac_t(S),
            exS=float(S.mean() + uS) if len(S) else np.nan,
            uncondL=uL, uncondS=uS))
    prof = pd.DataFrame(rows)

    slope, tsl, psl = hac_slope(r, pt)
    q1, q5 = r[qt == 1], r[qt == 5]
    dq, pq = block_boot_diff(q1, q5)
    mq = prof.dropna(subset=["m"])
    rho = (pd.Series(mq["m"].values).corr(pd.Series(mq["q"].values), method="spearman")
           if len(mq) >= 4 else np.nan)

    summ = dict(instr=name, tf=tf, logic=logic, theta=theta, exit=exit_type, proxy=proxy,
                n=len(r), m_all=float(r.mean()), t_all=hac_t(r),
                slope=slope, t_slope=tsl, p_slope=psl,
                q5_minus_q1=dq, p_q5q1=pq, spearman=rho,
                m_q5=float(q5.mean()) if len(q5) else np.nan,
                m_q1=float(q1.mean()) if len(q1) else np.nan)
    prof.insert(0, "proxy", proxy)
    prof.insert(0, "exit", exit_type)
    prof.insert(0, "theta", theta)
    prof.insert(0, "logic", logic)
    prof.insert(0, "tf", tf)
    prof.insert(0, "instr", name)
    trades = pd.DataFrame(dict(date=days.values[e], side=s, ret=r, dur=d,
                               q=qt, pct=pt))
    return summ, prof, trades


if __name__ == "__main__":
    pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 500)
    states = {n: daily_state(n) for n in SPEC}
    for n, s in states.items():
        v = s.dropna(subset=["P2"])
        print(f"{n}: sessions with state P1/P2/P3 = "
              f"{s.P1.notna().sum()}/{s.P2.notna().sum()}/{s.P3.notna().sum()} "
              f"| span {v.index.min().date()}..{v.index.max().date()}")

    # ---------------- PRIMARY: canonical form, 4 instruments x 3 proxies = 12 cells
    print("\n########## PRIMARY — sma20_z, 5m, theta 2.5, exit ts (H=6) ##########")
    P, PR, TR = [], [], []
    for name in SPEC:
        for proxy in ("P1", "P2", "P3"):
            su, pr, tr = run_cell(name, "5m", "sma20_z", 2.5, "ts", proxy, states)
            if su:
                P.append(su)
                PR.append(pr)
                tr.insert(0, "proxy", proxy)
                tr.insert(0, "instr", name)
                TR.append(tr)
            print(f"  primary done: {name} {proxy}", flush=True)
    S = pd.DataFrame(P)
    PROF = pd.concat(PR, ignore_index=True)
    S.to_csv(OUT / "primary_summary.csv", index=False)
    PROF.to_csv(OUT / "primary_profiles.csv", index=False)
    pd.concat(TR, ignore_index=True).to_csv(OUT / "primary_trades.csv", index=False)
    print(S.round(3).to_string(index=False))
    print("\n--- full quantile profiles (the main result) ---")
    print(PROF.round(2).to_string(index=False))

    # ---------------- BREADTH: every archived form x P2 (mechanism distribution)
    print("\n########## BREADTH — all forms x P2 (realised vol) ##########")
    B, BP = [], []
    for name in SPEC:
        for tf in TF_MIN:
            for logic in THETAS:
                for th in THETAS[logic]:
                    for ex in ("ts", "mt"):
                        su, pr, _ = run_cell(name, tf, logic, th, ex, "P2", states)
                        if su:
                            B.append(su)
                            BP.append(pr)
                print(f"  breadth done: {name} {tf} {logic}", flush=True)
    BB = pd.DataFrame(B)
    BB.to_csv(OUT / "breadth_summary.csv", index=False)
    pd.concat(BP, ignore_index=True).to_csv(OUT / "breadth_profiles.csv", index=False)
    print(f"forms measured: {len(BB)}")
    print(BB.round(3).to_string(index=False))
