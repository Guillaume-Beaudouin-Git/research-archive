"""
Lightweight, dependency-free RL agent for the Module 3 demonstration: a linear-
softmax policy trained by REINFORCE (Monte-Carlo policy gradient). It drives the
exact same environment, reward, walk-forward and consistency gate that a deep PPO
agent would — at a fraction of the capacity and compute, so it runs in seconds in
a sandbox. A stable-baselines3 PPO adapter for full-scale runs is in ppo_adapter.py.

Checkpoint selection follows the video's rule: keep the checkpoint whose *weaker*
of {train-tail score, validation score} is strongest (min-score, not mean).
"""
from __future__ import annotations

import numpy as np


class LinearSoftmaxPolicy:
    def __init__(self, obs_dim, n_actions=3, seed=0, scale=0.01):
        rng = np.random.default_rng(seed)
        self.W = rng.normal(0, scale, size=(n_actions, obs_dim))
        self.b = np.zeros(n_actions)
        self.n_actions = n_actions

    def probs(self, x):
        z = self.W @ x + self.b
        z -= z.max()
        e = np.exp(z)
        return e / e.sum()

    def act(self, x, rng, greedy=False):
        p = self.probs(x)
        return (int(p.argmax()) if greedy else int(rng.choice(self.n_actions, p=p))), p

    def copy(self):
        c = LinearSoftmaxPolicy(self.W.shape[1], self.n_actions)
        c.W, c.b = self.W.copy(), self.b.copy()
        return c


def run_episode(env, policy, rng, greedy=False, collect=True):
    obs, _ = env.reset()
    done = False
    S, A, R = [], [], []
    while not done:
        a, _ = policy.act(obs, rng, greedy=greedy)
        obs, r, done, _, _ = env.step(a)
        if collect:
            S.append(obs); A.append(a); R.append(r)
    if collect:
        return np.asarray(S), np.asarray(A), np.asarray(R)
    return None


def reinforce_update(policy, S, A, R, lr, gamma):
    G = np.empty(len(R)); run = 0.0
    for i in range(len(R) - 1, -1, -1):
        run = R[i] + gamma * run
        G[i] = run
    if G.std() > 1e-9:
        G = (G - G.mean()) / (G.std() + 1e-8)
    Z = S @ policy.W.T + policy.b
    Z -= Z.max(1, keepdims=True)
    E = np.exp(Z)
    Pr = E / E.sum(1, keepdims=True)
    onehot = np.zeros_like(Pr)
    onehot[np.arange(len(A)), A] = 1.0
    dlog = (onehot - Pr) * G[:, None]
    policy.W += lr * (dlog.T @ S) / len(S)
    policy.b += lr * dlog.sum(0) / len(S)


def evaluate(env, policy, lo, hi, rng):
    env.set_window(lo, hi)
    run_episode(env, policy, rng, greedy=True, collect=False)
    return env.realized_R, env.n_trades


def evaluate_constant(env, action, lo, hi):
    """Greedy fixed-action baseline (e.g. always-long) over a window -> realized R."""
    env.set_window(lo, hi)
    obs, _ = env.reset()
    done = False
    while not done:
        obs, _, done, _, _ = env.step(action)
    return env.realized_R, env.n_trades


def train_fold(env, obs_dim, train, val, *, epochs=20, lr=0.05, gamma=0.99,
               eval_every=2, seed=0):
    """Train on the train window; checkpoint-select on min(train-tail, val) score."""
    rng = np.random.default_rng(seed)
    policy = LinearSoftmaxPolicy(obs_dim, seed=seed)
    tr_lo, tr_hi = train
    va_lo, va_hi = val
    tail = va_hi - va_lo
    tail_lo = max(tr_lo, tr_hi - tail)
    best, best_score, curve = policy.copy(), -1e18, []
    for ep in range(epochs):
        env.set_window(tr_lo, tr_hi)
        S, A, R = run_episode(env, policy, rng)
        reinforce_update(policy, S, A, R, lr, gamma)
        if ep % eval_every == 0 or ep == epochs - 1:
            tr_R, _ = evaluate(env, policy, tail_lo, tr_hi, rng)
            va_R, _ = evaluate(env, policy, va_lo, va_hi, rng)
            score = min(tr_R, va_R)
            curve.append((ep, float(tr_R), float(va_R), float(score)))
            if score > best_score:
                best_score, best = score, policy.copy()
    return best, curve, float(best_score)
