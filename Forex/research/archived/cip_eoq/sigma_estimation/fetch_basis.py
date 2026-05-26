"""
CIP basis 3M EUR/USD — multi-source acquisition.

Outputs (data/):
  xeurbi_daily.parquet          : CME XEURBI settlement (2024-07-27 → today)
  synthetic_basis_daily.parquet : reconstructed basis from spot + rates
  merged_basis.parquet          : aligned dataframe [xeurbi, synthetic, diff_bps]

Units: all series in basis-points (bps), annualised convention.
Sign: negative means USD is expensive via FX swap vs cash (typical post-GFC EUR/USD).
"""

from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import pandas_datareader.data as web
import requests
import yfinance as yf
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

START_DATE = "2010-01-01"
END_DATE = date.today().isoformat()
START_XEURBI = "2024-07-27"      # CME XEURBI launch date

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ─────────────────────────────────────────────────────────────────────────────
# Source 1: CME XEURBI settlement
# ─────────────────────────────────────────────────────────────────────────────

def fetch_cme_xeurbi() -> Optional[pd.Series]:
    """
    Attempt to retrieve CME XEURBI daily settlement values.
    CME XEURBI = EUR/USD 3M IMM Cross-Currency Basis Index, launched 2024-07-27.
    Settlements are in bps (already annualised by CME convention).
    Returns Series indexed by date, or None on failure.
    """
    cache_path = DATA_DIR / "xeurbi_daily.parquet"

    # ── Try 1: CME FTP/API endpoint ──────────────────────────────────────────
    url_api = (
        "https://www.cmegroup.com/CmeWS/mvc/Settlements/futures/tradeDate/"
        + pd.Timestamp.today().strftime("%Y%m%d")
        + "/productCode/XEURBI/pageSize=365"
    )
    try:
        resp = requests.get(url_api, headers=HEADERS, timeout=15)
        if resp.status_code == 200 and "settlements" in resp.text.lower():
            data = resp.json()
            records = data.get("settlements", [])
            if records:
                df = pd.DataFrame(records)
                log.info("CME API: retrieved %d rows", len(df))
    except Exception as e:
        log.warning("CME API attempt failed: %s", e)

    # ── Try 2: CME product page HTML scrape ─────────────────────────────────
    url_page = (
        "https://www.cmegroup.com/markets/fx/g10/"
        "eur-usd-cross-currency-basis.html"
    )
    try:
        resp = requests.get(url_page, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            # Look for settlement table or embedded JSON
            scripts = soup.find_all("script")
            for sc in scripts:
                text = sc.string or ""
                if "settlement" in text.lower() and "XEURBI" in text:
                    log.info("CME page: found settlement data in script tag")
                    # Parse JSON-like data embedded in script
                    match = re.search(r'"settlements"\s*:\s*(\[.*?\])', text, re.DOTALL)
                    if match:
                        import json
                        try:
                            rows = json.loads(match.group(1))
                            df = pd.DataFrame(rows)
                            log.info("CME page: parsed %d rows", len(df))
                        except json.JSONDecodeError:
                            pass
    except Exception as e:
        log.warning("CME page scrape failed: %s", e)

    # ── Try 3: Stooq.com free data (XEURBI or cross-currency basis ETF proxy) ─
    # Stooq carries CME FX products; try symbol XEURBI.F or similar
    for symbol in ["XEURBI", "XEURBI.IMM", "XEURBI.F"]:
        try:
            df_stooq = yf.download(symbol, start=START_XEURBI, progress=False, auto_adjust=True)
            if not df_stooq.empty:
                series = df_stooq["Close"].squeeze()
                series.name = "xeurbi_bps"
                series.index = pd.to_datetime(series.index)
                series.index.name = "date"
                series.to_frame().to_parquet(cache_path)
                log.info("yfinance %s: %d rows saved", symbol, len(series))
                return series
        except Exception as e:
            log.debug("yfinance %s failed: %s", symbol, e)

    # ── Try 4: Quandl/Nasdaq Data Link FRED equivalent ───────────────────────
    # No known free XEURBI FRED series as of 2026

    # ── Try 5: Build XEURBI proxy from Du et al. methodology ────────────────
    log.warning(
        "CME XEURBI direct fetch failed. "
        "Will rely on synthetic_basis as primary series."
    )
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Source 2: Synthetic CIP basis reconstruction
# ─────────────────────────────────────────────────────────────────────────────

def fetch_fred_series(series_id: str, start: str, end: str) -> pd.Series:
    """Fetch a FRED series; returns daily Series in percent (not bps)."""
    try:
        df = web.DataReader(series_id, "fred", start, end)
        series = df[series_id].dropna()
        series.index = pd.to_datetime(series.index)
        series.name = series_id
        log.info("FRED %s: %d obs (%s – %s)", series_id, len(series),
                 series.index.min().date(), series.index.max().date())
        return series
    except Exception as e:
        log.error("FRED %s failed: %s", series_id, e)
        return pd.Series(dtype=float, name=series_id)


def fetch_usd_rate_3m(start: str, end: str) -> pd.Series:
    """
    USD 3M risk-free rate in % per annum.
    Priority: DGS3MO (T-bill, 1982+) as clean risk-free proxy.
    OIS-based (SOFR 3M): IOSRSOR3M156N from 2020 onwards.
    """
    # T-bill rate: most complete history for USD "cash" rate
    tbill = fetch_fred_series("DGS3MO", start, end)
    if not tbill.empty:
        return tbill.rename("usd_rate_pct")

    log.warning("DGS3MO unavailable; trying SOFR 3M compounded")
    sofr3m = fetch_fred_series("IOSRSOR3M156N", start, end)
    return sofr3m.rename("usd_rate_pct")


def fetch_eur_rate_3m(start: str, end: str) -> pd.Series:
    """
    EUR 3M rate in % per annum.
    Primary: EURIBOR 3M (EUR3MTD156N, 2001+).
    Fallback: ECB deposit facility rate as floor proxy.
    """
    euribor = fetch_fred_series("EUR3MTD156N", start, end)
    if not euribor.empty:
        return euribor.rename("eur_rate_pct")

    log.warning("EURIBOR 3M unavailable; trying ECB deposit rate")
    ecb_rate = fetch_fred_series("ECBDFR", start, end)
    return ecb_rate.rename("eur_rate_pct")


def fetch_eurusd_spot(start: str, end: str) -> pd.Series:
    """EUR/USD spot rate from yfinance (EURUSD=X) or FRED (DEXUSEU)."""
    try:
        df = yf.download("EURUSD=X", start=start, end=end, progress=False, auto_adjust=True)
        if not df.empty:
            series = df["Close"].squeeze().dropna()
            series.index = pd.to_datetime(series.index)
            series.name = "eurusd_spot"
            log.info("yfinance EURUSD=X: %d obs", len(series))
            return series
    except Exception as e:
        log.warning("yfinance EURUSD=X failed: %s", e)

    log.info("Trying FRED DEXUSEU for EUR/USD spot")
    fred_spot = fetch_fred_series("DEXUSEU", start, end)
    return fred_spot.rename("eurusd_spot")


def fetch_investing_com_forward_points() -> Optional[pd.DataFrame]:
    """
    Attempt to scrape EUR/USD 3M forward points from Investing.com.
    Forward points in pips; divide by 10000 to get forward price offset.
    Returns DataFrame with columns [date, fwd_points_3m_pips] or None.
    """
    url = "https://www.investing.com/currencies/eur-usd-forward-rates"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            tables = soup.find_all("table")
            for tbl in tables:
                headers_row = tbl.find("tr")
                if headers_row and "3M" in headers_row.get_text():
                    rows = tbl.find_all("tr")[1:]
                    records = []
                    for row in rows:
                        cells = row.find_all("td")
                        if len(cells) >= 4:
                            try:
                                dt = pd.to_datetime(cells[0].get_text(strip=True))
                                val = float(cells[3].get_text(strip=True).replace(",", ""))
                                records.append({"date": dt, "fwd_points_3m_pips": val})
                            except (ValueError, IndexError):
                                continue
                    if records:
                        df = pd.DataFrame(records).set_index("date")
                        log.info("Investing.com 3M forward: %d rows", len(df))
                        return df
        log.warning("Investing.com forward rates: status %d", resp.status_code)
    except Exception as e:
        log.warning("Investing.com scrape failed: %s", e)
    return None


def compute_synthetic_basis(
    spot: pd.Series,
    usd_rate: pd.Series,
    eur_rate: pd.Series,
    fwd_points: Optional[pd.DataFrame] = None,
) -> pd.Series:
    """
    Compute CIP basis in bps (annualised) from spot, rates, and optional forward points.

    CIP deviation (Du-Tepper-Verdelhan 2018 methodology):
      x_t = r_USD_3M - r_EUR_3M - (F_t/S_t - 1) × (360/90)

    where F_t is the 3M outright EUR/USD forward.

    If forward points are available:
      F_t = S_t + fwd_points_pips / 10000

    Without forward points (fallback):
      We compute the "implied basis" using the interest rate differential only.
      This is a PROXY that captures the rate differential component but NOT
      the FX-specific premium (which is what the true CIP deviation adds).
      Proxy basis = -(r_USD - r_EUR)  [negative when USD rates > EUR rates]
      Note: This systematically underestimates the QE spike magnitude.

    Returns:
      Series of basis in bps per annum (annualised), negative = USD expensive via swap.
    """
    # Align on business days (intersection of available data)
    aligned = pd.DataFrame({
        "spot": spot,
        "usd_rate": usd_rate,
        "eur_rate": eur_rate,
    }).dropna()

    if fwd_points is not None and len(fwd_points) > 10:
        aligned = aligned.join(fwd_points["fwd_points_3m_pips"], how="left")
        aligned["fwd_points_3m_pips"].ffill(inplace=True)

        has_fwd = aligned["fwd_points_3m_pips"].notna()
        aligned.loc[has_fwd, "forward"] = (
            aligned.loc[has_fwd, "spot"]
            + aligned.loc[has_fwd, "fwd_points_3m_pips"] / 10000
        )

        # CIP: x_t = r_USD - r_EUR - (F/S - 1) × 4   [all in % per annum → ×100 for bps×100]
        # Rates in % → divide by 100 for decimal
        r_usd = aligned["usd_rate"] / 100
        r_eur = aligned["eur_rate"] / 100
        fwd_premium_ann = (aligned["forward"] / aligned["spot"] - 1) * 4

        # CIP deviation in decimal; convert to bps
        cip_dev = (r_usd - r_eur - fwd_premium_ann) * 10000

        # Fill rows without forward data with rate-differential proxy
        proxy = -(aligned["usd_rate"] - aligned["eur_rate"]) * 100  # in bps
        cip_dev.fillna(proxy, inplace=True)
        basis_method = "cip_with_fwd"
    else:
        # Proxy: -(USD_rate - EUR_rate) captures the rate differential component
        # Sign: when USD rates spike relative to EUR (QE stress), proxy goes negative
        proxy = -(aligned["usd_rate"] - aligned["eur_rate"]) * 100  # bps
        cip_dev = proxy
        basis_method = "rate_diff_proxy"
        log.warning(
            "No forward points available; using rate-differential proxy. "
            "QE spike magnitude will be UNDERSTATED. Label in outputs: %s",
            basis_method
        )

    series = cip_dev.copy()
    series.name = f"synthetic_basis_bps_{basis_method}"
    series.index.name = "date"
    log.info(
        "Synthetic basis (%s): %d obs, mean=%.1f bps, std=%.1f bps",
        basis_method, len(series), series.mean(), series.std()
    )
    return series


def fetch_synthetic_basis() -> pd.Series:
    """
    Orchestrate synthetic basis reconstruction from FRED + yfinance.
    Persists to data/synthetic_basis_daily.parquet.
    Returns daily Series in bps.
    """
    cache_path = DATA_DIR / "synthetic_basis_daily.parquet"

    spot = fetch_eurusd_spot(START_DATE, END_DATE)
    usd_rate = fetch_usd_rate_3m(START_DATE, END_DATE)
    eur_rate = fetch_eur_rate_3m(START_DATE, END_DATE)

    # Try to get forward points (best effort)
    fwd_pts = fetch_investing_com_forward_points()

    basis = compute_synthetic_basis(spot, usd_rate, eur_rate, fwd_pts)

    basis.to_frame().to_parquet(cache_path)
    log.info("Saved synthetic basis → %s", cache_path)
    return basis


# ─────────────────────────────────────────────────────────────────────────────
# Source 3: Academic dataset (Du-Tepper-Verdelhan 2018 replication data)
# ─────────────────────────────────────────────────────────────────────────────

def try_fetch_academic_dataset() -> Optional[pd.Series]:
    """
    Attempt to retrieve published CIP basis series from academic sources.

    Priority order:
    1. BIS Working Paper 669 (Borio et al. 2016) supplementary CSV at BIS.org
    2. Wenxin Du's Columbia research page data
    3. SSRN supplementary material for Du-Tepper-Verdelhan (2018)
    4. NY Fed Liberty Street Economics data

    Returns Series in bps or None if all fail.
    """
    # ── Try: Du's Columbia page (known to host replication data) ────────────
    du_urls = [
        "https://drive.google.com/uc?export=download&id=1xURHMz13mLyMuH9B-NbBiIHxFqL-oLMh",
        "https://sites.google.com/site/wenxinduswebsite/research/data",
    ]
    for url in du_urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
            if resp.status_code == 200 and len(resp.content) > 1000:
                log.info("Academic data candidate at %s: %d bytes", url, len(resp.content))
        except Exception:
            pass

    # ── Try: BIS research data portal ────────────────────────────────────────
    # BIS makes some series available via their stats portal
    bis_url = "https://stats.bis.org/api/v1/data/BIS,WS_XRU,1.0/M.N.B.EUR.USD.?detail=dataonly&startPeriod=2010-01&endPeriod=2026-05"
    try:
        resp = requests.get(bis_url, timeout=15)
        if resp.status_code == 200 and len(resp.content) > 100:
            log.info("BIS API returned data")
    except Exception as e:
        log.debug("BIS API: %s", e)

    log.info(
        "Academic dataset not retrieved automatically. "
        "Du et al. (2018) JF data requires manual download from "
        "https://onlinelibrary.wiley.com/doi/full/10.1111/jofi.12620 "
        "or author's website. Proceeding with CME + synthetic sources only."
    )
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Merge and save
# ─────────────────────────────────────────────────────────────────────────────

def build_merged_basis(
    xeurbi: Optional[pd.Series],
    synthetic: pd.Series,
) -> pd.DataFrame:
    """
    Align XEURBI and synthetic basis on common trading days.
    Compute diff_bps = xeurbi - synthetic for validation.
    """
    merged = pd.DataFrame({"synthetic": synthetic})
    merged.index = pd.to_datetime(merged.index)

    if xeurbi is not None and not xeurbi.empty:
        xeurbi.index = pd.to_datetime(xeurbi.index)
        merged = merged.join(xeurbi.rename("xeurbi"), how="outer")
    else:
        merged["xeurbi"] = np.nan

    merged["diff_bps"] = merged["xeurbi"] - merged["synthetic"]
    merged.index.name = "date"
    merged = merged.sort_index()

    log.info(
        "Merged basis: %d rows, XEURBI coverage: %.0f%% (from %s)",
        len(merged),
        merged["xeurbi"].notna().mean() * 100,
        merged["xeurbi"].first_valid_index(),
    )
    return merged


def log_missing_dates(series: pd.Series, name: str) -> None:
    """Report number of missing observations by year."""
    if series.empty:
        log.warning("%s: empty series", name)
        return
    annual_missing = (
        series.resample("YE").apply(lambda s: s.isna().sum())
    )
    for yr, n in annual_missing.items():
        if n > 0:
            log.info("%s missing days in %s: %d", name, yr.year, n)


def main() -> None:
    log.info("═══ CIP Basis Fetch Pipeline ═══")
    log.info("Period: %s → %s", START_DATE, END_DATE)

    # ── Source 1: CME XEURBI ─────────────────────────────────────────────────
    log.info("── Source 1: CME XEURBI ──")
    xeurbi = fetch_cme_xeurbi()
    if xeurbi is not None:
        log_missing_dates(xeurbi, "XEURBI")
    else:
        log.warning("XEURBI: unavailable from all sources")

    # ── Source 2: Synthetic ──────────────────────────────────────────────────
    log.info("── Source 2: Synthetic basis ──")
    synthetic = fetch_synthetic_basis()
    log_missing_dates(synthetic, "synthetic")

    # ── Source 3: Academic ──────────────────────────────────────────────────
    log.info("── Source 3: Academic dataset ──")
    academic = try_fetch_academic_dataset()

    # ── Merge ────────────────────────────────────────────────────────────────
    merged = build_merged_basis(xeurbi, synthetic)
    merged_path = DATA_DIR / "merged_basis.parquet"
    merged.to_parquet(merged_path)
    log.info("Saved merged basis → %s", merged_path)

    # Summary statistics
    log.info("── Summary ──")
    for col in ["xeurbi", "synthetic"]:
        s = merged[col].dropna()
        if not s.empty:
            log.info(
                "%s: N=%d, mean=%.1f bps, std=%.1f bps, "
                "min=%.1f, max=%.1f, last=%.1f (on %s)",
                col, len(s), s.mean(), s.std(),
                s.min(), s.max(), s.iloc[-1], s.index[-1].date(),
            )

    log.info("═══ Done ═══")


if __name__ == "__main__":
    main()
