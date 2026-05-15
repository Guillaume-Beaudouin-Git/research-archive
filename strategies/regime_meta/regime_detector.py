"""
HMM v2 regime detector — 4-state with KMeans initialization.
Falls back to rule-based classifier if regime timeline fails validation.

Regimes: BULL_TREND, BEAR_TREND, RANGE, CRASH

Features (all lag-1, no look-ahead):
  trend_strength    = (close - SMA50) / SMA50
  vol_regime        = vol20 / vol60
  trend_consistency = mean(sign(log_ret), 10d)
  funding_zscore    = (funding_8h - 30d mean) / 30d std  [optional]
  btc_dom_chg       = BTC 5d ret - mean(ETH+SOL+BNB) 5d ret  [optional]
"""

import numpy as np
import pandas as pd
import warnings
from typing import Optional, Tuple, List
warnings.filterwarnings("ignore")

REGIME_LABELS = ["BULL_TREND", "BEAR_TREND", "RANGE", "CRASH"]
COLORS = {"BULL_TREND": "#2ecc71", "BEAR_TREND": "#e74c3c",
          "RANGE": "#95a5a6", "CRASH": "#1a1a2e"}


# ── Feature engineering ───────────────────────────────────────────────────────

def build_features(btc_close: pd.Series,
                   funding: Optional[pd.Series] = None,
                   dom_proxy: Optional[pd.Series] = None) -> pd.DataFrame:
    """
    Build 3-5 feature columns from BTC daily close price.
    All values are lag-1 (known at end of day T-1, used for trade at open T).
    """
    log_ret = np.log(btc_close / btc_close.shift(1))

    sma50 = btc_close.rolling(50).mean()
    trend_strength = ((btc_close - sma50) / sma50).shift(1)

    vol20 = log_ret.rolling(20).std()
    vol60 = log_ret.rolling(60).std()
    vol_regime = (vol20 / vol60.replace(0, np.nan)).fillna(1.0).shift(1)

    signs = np.sign(log_ret)
    trend_consistency = signs.rolling(10).mean().shift(1)

    feats = pd.DataFrame({
        "trend_strength":    trend_strength,
        "vol_regime":        vol_regime,
        "trend_consistency": trend_consistency,
    }, index=btc_close.index)

    features_used = ["trend_strength", "vol_regime", "trend_consistency"]

    if funding is not None:
        fund = funding.reindex(btc_close.index).ffill()
        f_mean = fund.rolling(30).mean()
        f_std  = fund.rolling(30).std().replace(0, np.nan)
        feats["funding_zscore"] = ((fund - f_mean) / f_std).shift(1)
        features_used.append("funding_zscore")

    if dom_proxy is not None:
        dp = dom_proxy.reindex(btc_close.index).ffill()
        feats["btc_dom_chg"] = dp.shift(1)
        features_used.append("btc_dom_chg")

    feats = feats.dropna()
    print(f"  Features used: {features_used}  ({len(feats)} rows after dropna)")
    return feats, features_used


def fetch_funding_rate(start_date: str = "2020-01-01") -> Optional[pd.Series]:
    """Fetch BTC 8h funding rate from Hyperliquid. Returns daily mean."""
    import requests
    start_ms = int(pd.Timestamp(start_date).timestamp() * 1000)
    url = "https://api.hyperliquid.xyz/info"
    payload = {"type": "fundingHistory", "coin": "BTC", "startTime": start_ms}
    for attempt in range(2):
        try:
            resp = requests.post(url, json=payload, timeout=20)
            data = resp.json()
            if not data:
                print(f"  [funding] empty response (attempt {attempt+1})")
                continue
            records = [
                (pd.Timestamp(d["time"], unit="ms").normalize(), float(d["fundingRate"]))
                for d in data
            ]
            df = pd.DataFrame(records, columns=["date", "funding"])
            daily = df.groupby("date")["funding"].mean()
            daily.index = pd.to_datetime(daily.index)
            print(f"  [funding] fetched {len(daily)} days from {daily.index[0].date()} to {daily.index[-1].date()}")
            return daily
        except Exception as e:
            print(f"  [funding] attempt {attempt+1} failed: {e}")
    return None


def build_dom_proxy(start: str, end: str) -> Optional[pd.Series]:
    """BTC dominance proxy: BTC 5d ret minus mean(ETH+SOL+BNB) 5d ret."""
    import yfinance as yf
    try:
        tickers = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"]
        raw = yf.download(tickers, start=start, end=end,
                          auto_adjust=True, progress=False)["Close"]
        if isinstance(raw, pd.Series):
            return None
        log_ret = np.log(raw / raw.shift(1))
        ret5_btc  = log_ret["BTC-USD"].rolling(5).sum()
        ret5_alts = log_ret[["ETH-USD", "SOL-USD", "BNB-USD"]].rolling(5).sum().mean(axis=1)
        dom = ret5_btc - ret5_alts
        dom.name = "btc_dom_chg"
        print(f"  [btc_dom] built proxy ({dom.dropna().shape[0]} rows)")
        return dom
    except Exception as e:
        print(f"  [btc_dom] failed: {e}")
        return None


# ── HMM fitting ───────────────────────────────────────────────────────────────

def fit_hmm(features_scaled: np.ndarray, n_states: int = 4) -> object:
    """Fit 4-state Gaussian HMM with KMeans initialization."""
    from hmmlearn.hmm import GaussianHMM
    from sklearn.cluster import KMeans

    kmeans = KMeans(n_clusters=n_states, random_state=42, n_init=20)
    kmeans.fit(features_scaled)
    labels = kmeans.labels_

    model = GaussianHMM(
        n_components=n_states,
        covariance_type="diag",
        n_iter=500,
        random_state=42,
        init_params="",   # manual init below
    )
    model.startprob_ = np.ones(n_states) / n_states
    # Sticky transitions: 85% stay, remainder split equally
    trans = 0.05 * np.ones((n_states, n_states))
    np.fill_diagonal(trans, 0.85)
    model.transmat_ = trans

    model.means_ = kmeans.cluster_centers_.copy()
    covars = []
    for k in range(n_states):
        mask = labels == k
        if mask.sum() > 1:
            var = np.var(features_scaled[mask], axis=0) + 1e-3
        else:
            var = np.ones(features_scaled.shape[1]) * 0.1
        covars.append(var)  # diag covariance = 1-D array of variances per feature
    model.covars_ = np.array(covars)  # shape (n_states, n_features)

    model.fit(features_scaled)
    return model


def label_states(model, feature_names: list) -> dict:
    """
    Map HMM state indices to economic labels using cluster means.
    Returns {state_idx: regime_label}
    """
    means = model.means_  # [n_states, n_features]
    idx_trend  = feature_names.index("trend_strength")
    idx_vol    = feature_names.index("vol_regime")
    idx_consist = feature_names.index("trend_consistency")

    trend_vals   = means[:, idx_trend]
    vol_vals     = means[:, idx_vol]
    consist_vals = means[:, idx_consist]

    remaining = list(range(4))
    mapping = {}

    # CRASH: highest vol_regime
    crash_state = int(np.argmax(vol_vals))
    mapping[crash_state] = "CRASH"
    remaining.remove(crash_state)

    # RANGE: lowest vol_regime among remaining
    range_state = remaining[int(np.argmin(vol_vals[remaining]))]
    mapping[range_state] = "RANGE"
    remaining.remove(range_state)

    # BULL_TREND: highest (trend_strength + trend_consistency) among remaining 2
    bull_score = trend_vals[remaining] + consist_vals[remaining]
    bull_state = remaining[int(np.argmax(bull_score))]
    mapping[bull_state] = "BULL_TREND"
    remaining.remove(bull_state)

    # BEAR_TREND: last one
    mapping[remaining[0]] = "BEAR_TREND"

    print("  HMM state → regime mapping:")
    for s, lbl in sorted(mapping.items()):
        print(f"    state {s}: {lbl}  "
              f"trend={trend_vals[s]:+.3f}  vol={vol_vals[s]:.3f}  consist={consist_vals[s]:+.3f}")
    return mapping


def apply_confirmation(raw_states: pd.Series, window: int = 3) -> pd.Series:
    """Only change regime if last `window` predictions all agree."""
    confirmed = raw_states.copy()
    current = raw_states.iloc[0]
    for i in range(len(raw_states)):
        if i < window:
            confirmed.iloc[i] = current
            continue
        last_k = raw_states.iloc[i - window + 1 : i + 1]
        if last_k.nunique() == 1:
            current = last_k.iloc[-1]
        confirmed.iloc[i] = current
    return confirmed


# ── Rule-based fallback ───────────────────────────────────────────────────────

def rule_based_regimes(feats: pd.DataFrame) -> pd.Series:
    """
    Deterministic fallback regime classifier.
    Cannot produce nonsensical labels like 44% BEAR in a bull year.
    """
    regimes = pd.Series("RANGE", index=feats.index, dtype=object)

    crash_mask = feats["vol_regime"] > 1.8
    bear_mask  = (feats["trend_strength"] < -0.03) & (feats["trend_consistency"] < -0.1)
    bull_mask  = (feats["trend_strength"] >  0.03) & (feats["trend_consistency"] >  0.1)

    regimes[bull_mask]  = "BULL_TREND"
    regimes[bear_mask]  = "BEAR_TREND"
    regimes[crash_mask] = "CRASH"       # crash overrides bear/bull

    dist = regimes.value_counts(normalize=True) * 100
    print("  Rule-based distribution:")
    for lbl in ["BULL_TREND", "BEAR_TREND", "RANGE", "CRASH"]:
        print(f"    {lbl}: {dist.get(lbl, 0):.1f}%")
    return regimes


# ── Validation ────────────────────────────────────────────────────────────────

EXPECTED_DOMINANT = {
    # (year, quarter): expected regime (approximate)
    (2021, 1): "BULL_TREND",
    (2021, 2): "CRASH",       # China ban, -50%
    (2021, 3): "BULL_TREND",
    (2021, 4): "BULL_TREND",
    (2022, 1): "BEAR_TREND",
    (2022, 2): "BEAR_TREND",
    (2022, 3): "BEAR_TREND",
    (2022, 4): "BEAR_TREND",
    (2023, 1): "BULL_TREND",
    (2023, 4): "BULL_TREND",
    (2024, 1): "BULL_TREND",  # ETF approval + halving
    (2024, 4): "BULL_TREND",
}


def validate_regime_timeline(regimes: pd.Series, verbose: bool = True) -> bool:
    """
    Check regime labels against known crypto market history.
    Returns True if roughly consistent (≥ 60% of checkpoints correct).
    """
    regimes.index = pd.to_datetime(regimes.index)
    checks_passed = 0
    checks_total  = 0

    print("\n  Regime validation vs known market history:")
    for (yr, qtr), expected in sorted(EXPECTED_DOMINANT.items()):
        try:
            q_start = pd.Timestamp(f"{yr}-{(qtr-1)*3+1:02d}-01")
            q_end   = q_start + pd.DateOffset(months=3)
            mask    = (regimes.index >= q_start) & (regimes.index < q_end)
            if mask.sum() == 0:
                continue
            dominant = regimes[mask].value_counts().index[0]
            ok = (dominant == expected)
            checks_total += 1
            checks_passed += int(ok)
            if verbose:
                tick = "✓" if ok else "✗"
                print(f"    {yr} Q{qtr}: got={dominant:<12} expected={expected:<12} {tick}")
        except Exception:
            pass

    if checks_total == 0:
        print("  [validate] no checkpoints in data range — skipping")
        return True

    hit_rate = checks_passed / checks_total
    print(f"  Validation: {checks_passed}/{checks_total} checkpoints correct ({hit_rate:.0%})")
    return hit_rate >= 0.60


# ── Public API ────────────────────────────────────────────────────────────────

def detect_regimes(btc_close: pd.Series,
                   train_end: str = "2022-12-31",
                   use_funding: bool = True,
                   use_dom: bool = True) -> Tuple[pd.Series, str]:
    """
    Fit HMM on [start, train_end] data, predict regimes on full series.
    Returns (regime_series, method_used).

    method_used: "hmm" or "rule_based"
    """
    print("\n[regime_detector] Building features...")
    data_start = btc_close.index[0].strftime("%Y-%m-%d")
    data_end   = btc_close.index[-1].strftime("%Y-%m-%d")

    # Optional feature augmentation
    funding = None
    if use_funding:
        print("  Fetching Hyperliquid funding rates...")
        funding = fetch_funding_rate(data_start)
        if funding is not None:
            # Need coverage over training period — if < 50% of train days, skip
            train_days = btc_close[:train_end].shape[0]
            fund_in_train = funding[:train_end].dropna().shape[0]
            if fund_in_train < train_days * 0.5:
                print(f"  [funding] insufficient train coverage ({fund_in_train}/{train_days}) — skipping")
                funding = None

    dom_proxy = None
    if use_dom:
        print("  Building BTC dominance proxy...")
        dom_proxy = build_dom_proxy(data_start, data_end)

    feats, feature_names = build_features(btc_close, funding=funding, dom_proxy=dom_proxy)

    # Scale on train period only
    from sklearn.preprocessing import StandardScaler
    train_mask = feats.index <= pd.Timestamp(train_end)
    scaler = StandardScaler()
    feats_scaled_train = scaler.fit_transform(feats[train_mask].values)
    feats_scaled_all   = scaler.transform(feats.values)

    # Try HMM
    print("\n[regime_detector] Fitting 4-state HMM on training data...")
    try:
        model = fit_hmm(feats_scaled_train, n_states=4)
        state_map = label_states(model, feature_names)

        # Predict on full period
        raw_state_idx = model.predict(feats_scaled_all)
        raw_regimes = pd.Series(
            [state_map[s] for s in raw_state_idx],
            index=feats.index,
            dtype=object,
        )
        confirmed_regimes = apply_confirmation(raw_regimes, window=3)

        # Validate
        print("\n[regime_detector] Validating HMM regime timeline...")
        if validate_regime_timeline(confirmed_regimes):
            print("  [HMM] Validation PASSED — using HMM regimes")
            return confirmed_regimes, "hmm"
        else:
            print("  [HMM] Validation FAILED — falling back to rule-based classifier")
    except Exception as e:
        print(f"  [HMM] fitting failed: {e} — falling back to rule-based classifier")

    # Fallback
    print("\n[regime_detector] Using rule-based regime classifier...")
    rule_regimes = rule_based_regimes(feats)
    confirmed_rule = apply_confirmation(rule_regimes, window=3)
    validate_regime_timeline(confirmed_rule)
    return confirmed_rule, "rule_based"
