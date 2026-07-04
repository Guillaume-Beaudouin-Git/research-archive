"""J1 (USDJPY) intervention-zone suspension gate — PRE-REGISTERED (PREREGISTRATION.md).

Deterministic function of the USDJPY daily-close series — NO persisted state.
  OFF (suspend) latches when close >= T_off.
  ON (resume)   only after N consecutive closes <= T_on (T_on < T_off), never on an up-break.
Causal: the decision for day T uses closes <= T-1 (shift 1).

The SAME `suspend_causal()` is intended for BOTH the live brain (reads panel_px USDJPY at 21:50,
then `weights["USDJPY"] = 0.0` when the flag is True) and this backtest (reads the frozen panel,
then `WT[:,1] *= (1 - flag)`). Identical mechanism, so live == backtest by construction.
"""
import numpy as np
import pandas as pd

T_OFF = 160.0
T_ON = 155.0
N_RESUME = 10


def off_state(close: pd.Series, t_off: float = T_OFF, t_on: float = T_ON,
              n: int = N_RESUME) -> pd.Series:
    """Boolean OFF-state per date (True = J1 suspended). NON-causal (uses close[t] itself).
    Start ON (False). OFF latches on close>=t_off; clears only after n consecutive closes<=t_on."""
    c = close.to_numpy(float)
    off = np.zeros(len(c), dtype=bool)
    state = False          # False = ON, True = OFF
    run_below = 0          # consecutive closes <= t_on while OFF
    for i in range(len(c)):
        if not state:
            if np.isfinite(c[i]) and c[i] >= t_off:
                state = True
                run_below = 0
        else:                                  # currently OFF
            if np.isfinite(c[i]) and c[i] <= t_on:
                run_below += 1
                if run_below >= n:
                    state = False              # frank pullback confirmed -> resume
                    run_below = 0
            else:
                run_below = 0                  # any close > t_on breaks the resume streak
        off[i] = state
    return pd.Series(off, index=close.index)


def suspend_causal(close: pd.Series, t_off: float = T_OFF, t_on: float = T_ON,
                   n: int = N_RESUME) -> pd.Series:
    """Causal suspension flag for day T: OFF-state through T-1 (shift 1)."""
    return off_state(close, t_off=t_off, t_on=t_on, n=n).shift(1, fill_value=False)
