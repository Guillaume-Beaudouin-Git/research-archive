"""Build a daily currency-strength proxy (sign-adjusted average log return
across available major pairs) per currency, used for vol-regime matching in
the placebo construction (L58: placebo baseline must equal the unconditional
expectation, controlled for vol regime)."""
import pandas as pd
import numpy as np
import os
from lib import CCY_PAIRS, ALL_PAIRS, CACHE_DIR

OUT_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(OUT_DIR, exist_ok=True)


def daily_close(pair):
    df = pd.read_parquet(f"{CACHE_DIR}/{pair}_M1.parquet", columns=["close"])
    daily = df["close"].resample("1D").last().dropna()
    return daily


def main():
    pair_daily = {}
    for pair in ALL_PAIRS:
        d = daily_close(pair)
        ret = np.log(d).diff()
        pair_daily[pair] = ret
        print(pair, len(ret))

    for ccy, pairs in CCY_PAIRS.items():
        parts = []
        for pair, sign in pairs:
            parts.append(sign * pair_daily[pair].rename(pair))
        df = pd.concat(parts, axis=1)
        proxy = df.mean(axis=1, skipna=True)
        vol5 = proxy.rolling(5, min_periods=3).std()
        out = pd.DataFrame({"ret": proxy, "vol5": vol5})
        out.to_csv(f"{OUT_DIR}/proxy_{ccy}.csv")
        print(ccy, "n=", len(out), "pairs=", [p for p, _ in pairs])


if __name__ == "__main__":
    main()
