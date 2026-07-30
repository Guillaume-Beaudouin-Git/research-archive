"""Step 2b — apples-to-apples: futures window vs the GAP-EXCLUDED M1 CFD window,
identical sessions, identical exchange-clock anchor.

The step-2 headline compared the futures against the H1 CFD spec, which silently
carries the halt gap. This compares like with like, and separately reports the CFD's
own behaviour restricted to the futures-overlap period, so a level difference cannot
be blamed on the period.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import OUT, hac_t, sharpe

cfd = pd.read_csv(OUT / "step1c_daily_series.csv", index_col=0, parse_dates=True)
fut = pd.read_csv(OUT / "step2_futures_daily.csv", index_col=0, parse_dates=True)

rows = []
for name in ["GOLD", "SILVER", "WTI", "SOYBEAN"]:
    c_all = cfd[cfd["sleeve"] == name]["window_cap"].dropna()
    f = fut[fut["sleeve"] == name]["window_cap"].dropna()
    if len(c_all) == 0 or len(f) == 0:
        continue
    ov0, ov1 = f.index.min(), f.index.max()
    c_ov = c_all[(c_all.index >= ov0) & (c_all.index <= ov1)]
    common = c_ov.index.intersection(f.index)
    r = dict(sleeve=name,
             N_cfd_full=len(c_all),
             cfd_full_bps=round(1e4 * c_all.mean(), 2),
             cfd_full_SR=round(sharpe(c_all), 3),
             N_cfd_overlap=len(c_ov),
             cfd_overlap_bps=round(1e4 * c_ov.mean(), 2) if len(c_ov) else np.nan,
             N_fut=len(f),
             fut_bps=round(1e4 * f.mean(), 2),
             N_common=len(common))
    if len(common) > 50:
        a, b = c_all.reindex(common), f.reindex(common)
        r["cfd_common_bps"] = round(1e4 * a.mean(), 2)
        r["fut_common_bps"] = round(1e4 * b.mean(), 2)
        r["diff_bps"] = round(1e4 * (b - a).mean(), 2)
        r["t_diff"] = round(hac_t(b - a)[1], 2)
        r["corr"] = round(float(np.corrcoef(a, b)[0, 1]), 3)
        r["capture_ratio"] = (round(float(b.mean() / a.mean()), 2)
                              if a.mean() > 0 else np.nan)
    rows.append(r)

res = pd.DataFrame(rows)
pd.set_option("display.width", 260, "display.max_columns", 40)
print(res.to_string(index=False))
res.to_csv(OUT / "step2b_apples.csv", index=False)

print("""
capture_ratio = futures drift / CFD drift on the SAME sessions, both gap-excluded,
both anchored on the exchange clock. 1.0 = the CFD is a faithful proxy of the
tradable contract. <<1.0 = the archived CFD edge does not exist on the instrument
you would actually trade.""")
