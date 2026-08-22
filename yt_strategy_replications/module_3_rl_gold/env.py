"""
Module 3 — gold trading environment + relative feature construction for the RL
replication. Framework-agnostic: usable directly by the numpy agent in agent.py
and (optionally) by stable-baselines3 PPO via the gymnasium.Env base class.

Faithful to the video's design choices:
  * features are RELATIVE only — no absolute prices (RSI, ATR-normalised distances,
    candle-shape/ATR, returns, time sin/cos, position state, unrealised R);
  * actions buy / sell / hold; on entry a stop is set at atr_mult x ATR and a take-
    profit at rr:1 (the video's dominant 1.5 x ATR / 2:1 choice — held fixed here for
    a tractable discrete action space);
  * reward = realised PnL in R-units (+rr on TP, -1 on SL) + 0.01 x unrealised-R nudge
    each bar held - tiny holding penalty each bar (pushes toward quick resolutions).

Execution discipline: features at bar t are causal (through close t); the decision is
taken at close t and the fill happens at open t+1; intrabar SL/TP use the next bar's
high/low (stop-first on ambiguity).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import indicators as ind

try:
    import gymnasium as gym
    from gymnasium import spaces
    _BASE = gym.Env
except Exception:  # pragma: no cover
    _BASE = object
    spaces = None

FEATURE_COLS = ["rsi", "c_ema20_atr", "c_ema50_atr", "ema20_50_atr", "c_ema200_atr",
                "range_atr", "body_atr", "atr_pct", "ret1", "ret5",
                "sin_h", "cos_h", "sin_d", "cos_d"]


def build_features(df: pd.DataFrame):
    """Return (features DataFrame [relative only], atr Series), warmup rows dropped."""
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    atr = ind.atr(h, l, c, 14)
    ema20, ema50, ema200 = ind.ema(c, 20), ind.ema(c, 50), ind.ema(c, 200)
    rsi = ind.rsi(c, 14)
    f = pd.DataFrame(index=df.index)
    f["rsi"] = rsi / 100.0 - 0.5
    f["c_ema20_atr"] = (c - ema20) / atr
    f["c_ema50_atr"] = (c - ema50) / atr
    f["ema20_50_atr"] = (ema20 - ema50) / atr
    f["c_ema200_atr"] = (c - ema200) / atr
    f["range_atr"] = (h - l) / atr
    f["body_atr"] = (c - o) / atr
    f["atr_pct"] = atr / c * 100.0
    f["ret1"] = c.pct_change() * 100.0
    f["ret5"] = c.pct_change(5) * 100.0
    hour = df.index.hour.to_numpy()
    dow = df.index.dayofweek.to_numpy()
    f["sin_h"] = np.sin(2 * np.pi * hour / 24)
    f["cos_h"] = np.cos(2 * np.pi * hour / 24)
    f["sin_d"] = np.sin(2 * np.pi * dow / 7)
    f["cos_d"] = np.cos(2 * np.pi * dow / 7)
    f = f[FEATURE_COLS].replace([np.inf, -np.inf], np.nan)
    valid = f.notna().all(axis=1) & atr.notna() & (atr > 0)
    f = f[valid].clip(-10, 10)
    return f, atr[valid]


class GoldTradingEnv(_BASE):
    """Bar-stepped trading env. Observation = relative features + [position, unreal_R]."""

    def __init__(self, feats: np.ndarray, o, h, l, c, atr, *, atr_mult=1.5, rr=2.0,
                 max_hold=50, w_unreal=0.01, hold_pen=2e-5, cost_frac=5e-5):
        self.F = np.asarray(feats, np.float32)
        self.o = np.asarray(o, float); self.h = np.asarray(h, float)
        self.l = np.asarray(l, float); self.c = np.asarray(c, float)
        self.atr = np.asarray(atr, float)
        self.n, self.nf = self.F.shape
        self.atr_mult, self.rr, self.max_hold = atr_mult, rr, max_hold
        self.w_unreal, self.hold_pen, self.cost_frac = w_unreal, hold_pen, cost_frac
        self.lo, self.hi = 0, self.n - 1
        if spaces is not None:
            self.observation_space = spaces.Box(-10, 10, shape=(self.nf + 2,), dtype=np.float32)
            self.action_space = spaces.Discrete(3)  # 0 hold/flat, 1 long, 2 short

    @property
    def obs_dim(self):
        return self.nf + 2

    def set_window(self, lo, hi):
        self.lo, self.hi = lo, hi

    def reset(self, *, seed=None, options=None):
        self.t = self.lo
        self.pos = 0
        self.entry = self.sl = self.tp = self.risk = 0.0
        self.bars = 0
        self.realized_R = 0.0   # cumulative realized PnL in R-units (for OOS eval / selection)
        self.n_trades = 0
        return self._obs(), {}

    def _obs(self):
        unreal = 0.0
        if self.pos != 0 and self.risk > 0:
            unreal = self.pos * (self.c[self.t] - self.entry) / self.risk
        return np.concatenate([self.F[self.t], [float(self.pos), float(np.clip(unreal, -5, 5))]]).astype(np.float32)

    def _open(self, direction, fill):
        self.pos = direction
        self.entry = fill
        self.risk = self.atr_mult * self.atr[self.t]
        if direction > 0:
            self.sl, self.tp = fill - self.risk, fill + self.rr * self.risk
        else:
            self.sl, self.tp = fill + self.risk, fill - self.rr * self.risk
        self.bars = 0
        entry_cost = -self.cost_frac * fill / self.risk if self.risk > 0 else 0.0  # entry cost in R
        self.realized_R += entry_cost
        return entry_cost

    def _close(self, exit_px):
        pnl_R = self.pos * (exit_px - self.entry) / self.risk if self.risk > 0 else 0.0
        cost_R = self.cost_frac * exit_px / self.risk if self.risk > 0 else 0.0
        self.pos = 0
        net = pnl_R - cost_R
        self.realized_R += net
        self.n_trades += 1
        return net

    def step(self, action):
        desired = {0: 0, 1: 1, 2: -1}[int(action)]
        reward = 0.0
        t1 = self.t + 1
        if t1 >= self.hi:   # hi is exclusive; never index past hi-1
            return self._obs(), 0.0, True, False, {}

        # --- advance to next bar; manage open position with risk rules first ---
        if self.pos != 0:
            self.bars += 1
            hit_sl = (self.l[t1] <= self.sl) if self.pos > 0 else (self.h[t1] >= self.sl)
            hit_tp = (self.h[t1] >= self.tp) if self.pos > 0 else (self.l[t1] <= self.tp)
            if hit_sl:  # stop-first on ambiguity
                reward += self._close(self.sl)
            elif hit_tp:
                reward += self._close(self.tp)
            elif self.bars >= self.max_hold:
                reward += self._close(self.c[t1])
            elif desired != self.pos:  # agent-initiated close / flip
                reward += self._close(self.o[t1])

        self.t = t1
        # --- act on the (now) current bar's open if flat ---
        if self.pos == 0 and desired != 0:
            reward += self._open(desired, self.o[self.t])

        # --- shaping terms while holding ---
        if self.pos != 0:
            unreal = self.pos * (self.c[self.t] - self.entry) / self.risk if self.risk > 0 else 0.0
            reward += self.w_unreal * unreal - self.hold_pen

        return self._obs(), float(reward), bool(self.t >= self.hi), False, {}
