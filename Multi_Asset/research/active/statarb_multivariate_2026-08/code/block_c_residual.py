"""BLOC C — réversion du résidu d'un modèle à facteurs walk-forward (Avellaneda-Lee
adapté à un petit univers), jugée au GROSS.

4 cellules pré-enregistrées : K facteurs {3,5} x seuils s-score {(1.25,0.50),(2.00,0.50)}.

ANTI-LOOK-AHEAD (l'erreur classique de cette famille) :
  - l'ACP et les bêtas sont estimés sur [t-252, t-1] UNIQUEMENT ;
  - les vecteurs propres sont GELÉS avant de calculer le rendement factoriel du jour t ;
  - le s-score reflète l'information à la clôture de t-1, la position est tenue sur t.
  Aucune ACP sur échantillon complet n'est produite, nulle part.

Règle de mort C : max sur les 4 cellules du Sharpe BRUT (cost=0, swap=0) < 0.70
=> branche REJECTED (ne pas atteindre RESEARCH_PASS à coût nul est irrattrapable).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

M5DIR = sys.argv[1] if len(sys.argv) > 1 else "m5"
OUTDIR = sys.argv[2] if len(sys.argv) > 2 else "."

UNIVERSE = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
            "EURGBP", "EURJPY", "AUDJPY", "US500", "US100", "US30", "GER40",
            "XAUUSD", "XAGUSD", "COPPER", "UKOIL", "USOIL"]

W = 252      # fenêtre d'estimation (jours)
M = 60       # fenêtre du processus résiduel cumulé (AL)
SNAP = 20    # heure UTC de la photo quotidienne
KILL_SR = 0.70


def daily_panel() -> pd.DataFrame:
    cols = {}
    for s in UNIVERSE:
        p = os.path.join(M5DIR, f"{s}_M5.parquet")
        if not os.path.exists(p):
            continue
        d = pd.read_parquet(p)[["close"]]
        d = d[d.index.hour < SNAP]
        cols[s] = d.groupby(d.index.normalize())["close"].last()
    px = pd.DataFrame(cols).sort_index()
    px = px[px.index.dayofweek < 5]
    return px


def ar1(x: np.ndarray):
    """AR(1) on the cumulative residual: X_{n+1} = a + b X_n + xi."""
    y, xl = x[1:], x[:-1]
    xm, ym = xl.mean(), y.mean()
    den = ((xl - xm) ** 2).sum()
    if den <= 0:
        return None
    b = ((xl - xm) * (y - ym)).sum() / den
    if not (1e-6 < b < 0.9999):
        return None
    a = ym - b * xm
    xi = y - (a + b * xl)
    v = xi.var(ddof=2)
    if v <= 0:
        return None
    return a / (1 - b), np.sqrt(v / (1 - b * b)), np.log(2) / (-np.log(b))


def run(R: np.ndarray, K: int, s_open: float, s_close: float):
    T, N = R.shape
    pos = np.zeros(N)
    rets, n_open, hls, hold = [], [], [], np.zeros(N)
    holds_done = []
    for t in range(W, T):
        win = R[t - W:t]                       # rows t-W .. t-1  (info <= close t-1)
        mu, sd = win.mean(0), win.std(0, ddof=1)
        sd = np.where(sd > 0, sd, np.nan)
        Z = (win - mu) / sd
        if not np.isfinite(Z).all():
            rets.append(0.0)
            continue
        C = np.corrcoef(Z, rowvar=False)
        ev, V = np.linalg.eigh(C)
        Q = (V[:, ::-1][:, :K].T / sd).T        # eigenportfolio weights, N x K
        Fw = win @ Q                            # factor returns over the window
        A = np.column_stack([np.ones(W), Fw])
        coef, *_ = np.linalg.lstsq(A, win, rcond=None)   # (1+K) x N
        eps_w = win - A @ coef                  # residuals over the window

        # today's residual, FROZEN loadings, using day-t returns only
        f_t = R[t] @ Q
        eps_t = R[t] - coef[0] - f_t @ coef[1:]

        X = np.cumsum(eps_w[-M:], axis=0)
        s = np.full(N, np.nan)
        for i in range(N):
            fit = ar1(X[:, i])
            if fit is None:
                continue
            m, seq, hl = fit
            if not (1.0 <= hl <= 30.0) or seq <= 0:   # canonical AL speed filter
                continue
            s[i] = (X[-1, i] - m) / seq
            hls.append(hl)

        # trade rule on the s-score known at close t-1, P&L realised on day t
        prev = pos.copy()
        for i in range(N):
            if np.isnan(s[i]):
                continue
            if pos[i] == 0:
                if s[i] < -s_open:
                    pos[i] = 1.0
                elif s[i] > s_open:
                    pos[i] = -1.0
            elif pos[i] > 0 and s[i] > -s_close:
                pos[i] = 0.0
            elif pos[i] < 0 and s[i] < s_close:
                pos[i] = 0.0
        for i in range(N):
            if prev[i] != 0 and pos[i] == 0:
                holds_done.append(hold[i])
                hold[i] = 0
            elif pos[i] != 0:
                hold[i] += 1

        k = np.abs(pos).sum()
        n_open.append(k)
        rets.append(float((pos @ np.nan_to_num(eps_t)) / k) if k > 0 else 0.0)

    r = np.asarray(rets)
    # daily vol targeting to 10% annual, trailing 63d, strictly lagged
    sd63 = pd.Series(r).rolling(63).std().shift(1).to_numpy()
    scale = np.where(sd63 > 0, (0.10 / np.sqrt(252)) / sd63, 0.0)
    rv = np.nan_to_num(r * np.clip(scale, 0, 10))
    sr = rv.mean() / rv.std(ddof=1) * np.sqrt(252) if rv.std() > 0 else np.nan
    return {
        "K": K, "s_open": s_open, "s_close": s_close,
        "sharpe_gross": float(sr),
        "n_days": int(len(rv)),
        "mean_open": float(np.mean(n_open)) if n_open else 0.0,
        "median_hold_d": float(np.median(holds_done)) if holds_done else np.nan,
        "median_resid_hl_d": float(np.median(hls)) if hls else np.nan,
        "n_closed_trades": len(holds_done),
    }


def main() -> None:
    px = daily_panel()
    R = np.log(px).diff().dropna()
    print(f"panneau quotidien : {R.shape[0]} jours x {R.shape[1]} instruments  "
          f"{R.index.min().date()}..{R.index.max().date()}")
    print("instruments :", list(R.columns))
    Rv = R.to_numpy()

    rows = []
    for K in (3, 5):
        for s_open, s_close in ((1.25, 0.50), (2.00, 0.50)):
            out = run(Rv, K, s_open, s_close)
            rows.append(out)
            print(f"K={K} s=({s_open},{s_close})  SR_gross={out['sharpe_gross']:+.3f}  "
                  f"jours={out['n_days']}  pos_moy={out['mean_open']:.1f}  "
                  f"hold_med={out['median_hold_d']:.1f}j  "
                  f"HL_resid_med={out['median_resid_hl_d']:.1f}j  "
                  f"trades={out['n_closed_trades']}", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTDIR, "block_c_cells.csv"), index=False)
    best = df["sharpe_gross"].max()
    print("\n" + "=" * 74)
    print(f"BLOC C — 4/4 cellules évaluées. max Sharpe BRUT = {best:+.3f}")
    print(f"Règle de mort C : max SR_brut < {KILL_SR} => REJECTED.  "
          f"VERDICT = {'PASS-CANDIDATE' if best >= KILL_SR else 'REJECTED'}")
    hl = df["median_hold_d"].median()
    if np.isfinite(hl):
        swap = 0.75 * hl / 1e4      # L28 : 0.75 bps/nuit/jambe
        print(f"\nFacture de portage implicite : hold médian {hl:.1f} nuits "
              f"=> {swap*1e4:.1f} bps par trade et par jambe (L28)")


if __name__ == "__main__":
    main()
