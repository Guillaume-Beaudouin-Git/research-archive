"""Parse the consolidated economic calendar into per-(currency, family) event
tables, restricted to the M1 data coverage window (2018-01-01 .. 2026-06-05,
the max range of deep_history_utc / TradingView calendar overlap)."""
import pandas as pd
import os

CAL_PATH = "<HOME>/Desktop/Algo_claude/data/deep_history_utc/calendar/economic_calendar_2018_2026_full.csv"
OUT_DIR = os.path.join(os.path.dirname(__file__), "events")
os.makedirs(OUT_DIR, exist_ok=True)

M1_START = pd.Timestamp("2018-01-02", tz="UTC")
M1_END = pd.Timestamp("2026-06-04", tz="UTC")  # leave 24h margin before series end 06-05 20:59

RATE_DECISION_EVENT = {
    "USD": "Fed Interest Rate Decision",
    "EUR": "ECB Interest Rate Decision",
    "GBP": "BoE Interest Rate Decision",
    "JPY": "BoJ Interest Rate Decision",
    "AUD": "RBA Interest Rate Decision",
    "CAD": "BoC Interest Rate Decision",
    "CHF": "SNB Interest Rate Decision",
    "NZD": "RBNZ Interest Rate Decision",
}

CPI_EVENT = {
    "USD": "Inflation Rate YoY",
    "EUR": "Inflation Rate YoY Flash",
    "GBP": "Inflation Rate YoY",
    "JPY": "Inflation Rate YoY",
    "AUD": "Inflation Rate YoY",
    "CAD": "Inflation Rate YoY",
    "CHF": "Inflation Rate YoY",
    "NZD": "Inflation Rate YoY",
}

NFP_EVENT = {"USD": "Non Farm Payrolls"}

GDP_EVENT = {
    "USD": "GDP Growth Rate QoQ Adv",
    "EUR": "GDP Growth Rate QoQ Flash",
    "GBP": "GDP Growth Rate QoQ Prel",
    "JPY": "GDP Growth Rate QoQ Prel",
}

PMI_EVENT = {
    "USD": "ISM Manufacturing PMI",
    "EUR": "HCOB Manufacturing PMI Flash",
    "GBP": "S&P Global Manufacturing PMI Flash",
}

FAMILIES = {
    "rate_decision": RATE_DECISION_EVENT,
    "cpi": CPI_EVENT,
    "nfp": NFP_EVENT,
    "gdp": GDP_EVENT,
    "pmi": PMI_EVENT,
}


def main():
    cal = pd.read_csv(CAL_PATH, parse_dates=["datetime_utc"])
    cal["datetime_utc"] = cal["datetime_utc"].dt.tz_localize("UTC")

    summary = []
    for fam, mapping in FAMILIES.items():
        for ccy, event_name in mapping.items():
            sub = cal[(cal["currency"] == ccy) & (cal["event"] == event_name)].copy()
            sub = sub[(sub["datetime_utc"] >= M1_START) & (sub["datetime_utc"] <= M1_END)]
            sub = sub.sort_values("datetime_utc").drop_duplicates("datetime_utc")
            out_path = f"{OUT_DIR}/{fam}_{ccy}.csv"
            sub[["datetime_utc", "currency", "event", "actual", "forecast", "previous"]].to_csv(out_path, index=False)
            summary.append({"family": fam, "currency": ccy, "event_name": event_name, "n_events": len(sub)})
            print(f"{fam:15s} {ccy}  n={len(sub):4d}  -> {out_path}")

    pd.DataFrame(summary).to_csv(f"{OUT_DIR}/_summary.csv", index=False)


if __name__ == "__main__":
    main()
