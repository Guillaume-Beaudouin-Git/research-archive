"""
Full-scale path (optional) — stable-baselines3 PPO over GoldTradingEnv.

The sandbox demo uses the linear REINFORCE agent in agent.py because torch is too
heavy to install here. On a machine with `pip install stable-baselines3 torch`,
this module reproduces the video's deep-RL setup over the *same* environment,
reward and relative features, with periodic checkpointing, the min(train-tail, val)
selection rule, and the consistency gate from walkforward.py.

This is the code the user runs on their VPS for a faithful, full-capacity result;
it is intentionally not exercised in the sandbox.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from env import GoldTradingEnv


def _greedy_eval(model, feats, prices, lo, hi, **env_kw) -> float:
    o, h, l, c, atr = prices
    env = GoldTradingEnv(feats, o, h, l, c, atr, **env_kw)
    env.set_window(lo, hi)
    obs, _ = env.reset()
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, _, done, _, _ = env.step(int(action))
    return env.realized_R


def train_ppo_fold(feats, prices, fold, *, total_steps=2_000_000, ckpt_every=100_000,
                   seed=0, save_dir="results/ppo", **env_kw):
    """Train PPO on a fold's train window; checkpoint-select on min(train-tail, val)."""
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv

    o, h, l, c, atr = prices
    tr_lo, tr_hi = fold["train"]
    va_lo, va_hi = fold["val"]
    tail = va_hi - va_lo

    def _make():
        e = GoldTradingEnv(feats, o, h, l, c, atr, **env_kw)
        e.set_window(tr_lo, tr_hi)
        return e

    venv = DummyVecEnv([_make])
    model = PPO("MlpPolicy", venv, n_steps=4096, batch_size=512, gamma=0.99,
                gae_lambda=0.95, ent_coef=0.01, learning_rate=3e-4, seed=seed, verbose=0)

    Path(save_dir).mkdir(parents=True, exist_ok=True)
    best_path, best_score = None, -1e18
    trained = 0
    while trained < total_steps:
        model.learn(ckpt_every, reset_num_timesteps=False)
        trained += ckpt_every
        tr_R = _greedy_eval(model, feats, prices, tr_hi - tail, tr_hi, **env_kw)
        va_R = _greedy_eval(model, feats, prices, va_lo, va_hi, **env_kw)
        score = min(tr_R, va_R)                      # the video's selection rule
        if score > best_score:
            best_score = score
            best_path = f"{save_dir}/fold{fold.get('idx', 0)}_best"
            model.save(best_path)
    return best_path, float(best_score)


def evaluate_ppo(model_path, feats, prices, lo, hi, **env_kw) -> float:
    from stable_baselines3 import PPO
    model = PPO.load(model_path)
    return _greedy_eval(model, feats, prices, lo, hi, **env_kw)
