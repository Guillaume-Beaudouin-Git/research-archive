"""v2.1 — RÉGÉNÉRATION UNIQUE de tous les chiffres contractuels (audit équipe, pt 3).
UN stack (audit_stack + swaps mesurés), UN moteur (simulator avec token-rule + margin cap),
UN run. Toute valeur publiée ailleurs qui diffère de cette sortie est périmée.
"""
import pandas as pd, numpy as np
import config as C, simulator as S, run_phase3 as R, audit_stack as A, funded as F

CFG = dict(R.BASE, taper_buf=0.02, abandon_buf=0.02, abandon_days=5, max_cal_days=91,
           p2_mult=1.2, vol_mult=14.0, on_w=0.6, orb_risk=0.0025, margin_cap=0.60)
FEE = 96.0
out = {}

def funnel(D, WT, ON, lo, hi, step=7, wall=91, **over):
    cfg = dict(CFG); cfg.update(over); cfg["max_cal_days"] = wall
    st = A.cohorts(D, lo, hi, step=step)
    res = [S.run_funnel(D, i0, WT, ON, cfg, wall_days=wall, retries=True) for i0 in st]
    df = pd.DataFrame(res)
    return df.funded.mean(), df.attempts.mean(), df

D = A.load_audited(); WT, ON = R.align(D)

# --- funded (pour la valeur d'EV, calculée AVANT le challenge pour cohérence)
cf = dict(target=10.0, on_w=0.35, breaker_frac=0.30, orb_risk=0.0025, taper_buf=0.02,
          glide=1.0, quantize=True, pace=0, daily_realize=False, weekend_flat=False,
          max_cal_days=None, vol_mult=1.0, margin_cap=0.60)
g_oos = pd.DataFrame([F.run_funded(D, i0, WT, ON, cf, 504, 14)
                      for i0 in A.cohorts(D, "2020-01-01", "2024-06-01", 12)])
g_is = pd.DataFrame([F.run_funded(D, i0, WT, ON, cf, 504, 14)
                     for i0 in A.cohorts(D, "2013-10-01", "2019-12-31", 12)])
eo = (g_oos.wd + g_oos.residual); ei = (g_is.wd + g_is.residual)
n_pool = len(g_is) + len(g_oos)
extr_pool = (ei.sum() + eo.sum()) / n_pool
VAL = FEE + 0.8 * extr_pool
out["funded"] = dict(OOS=eo.mean(), OOS_med=eo.median(), OOS_bust=g_oos.busted.mean(),
                     IS=ei.mean(), IS_med=ei.median(), pooled=extr_pool, VAL=VAL)
print(f"FUNDED: OOS ${eo.mean():,.0f} (méd ${eo.median():,.0f}, bust {g_oos.busted.mean()*100:.0f}%) | "
      f"IS ${ei.mean():,.0f} | pooled ${extr_pool:,.0f} | valeur funded = ${VAL:,.0f}", flush=True)

# --- challenge (base + ablations + stress), tout au même grid step=7
p_is, a_is, _ = funnel(D, WT, ON, "2013-10-01", "2019-12-31")
p_oos, a_oos, _ = funnel(D, WT, ON, "2020-01-01", "2026-03-01")
n_is = len(A.cohorts(D, "2013-10-01", "2019-12-31", 7)); n_oos = len(A.cohorts(D, "2020-01-01", "2026-03-01", 7))
p_pool = (p_is*n_is + p_oos*n_oos)/(n_is+n_oos); a_pool = (a_is*n_is + a_oos*n_oos)/(n_is+n_oos)
print(f"CHALLENGE: IS {p_is:.3f}/{a_is:.2f} | OOS {p_oos:.3f}/{a_oos:.2f} | POOLED {p_pool:.3f} | "
      f"EV pooled = ${p_pool*VAL - a_pool*FEE:+,.0f}", flush=True)
p_tok, a_tok, _ = funnel(D, WT, ON, "2013-10-01", "2026-03-01", step=11, orb_risk=0.0)
print(f"ABLATION ORB (token only): p={p_tok:.3f} -> contribution P&L ORB = {p_pool-p_tok:+.3f}", flush=True)
p_noon, _, _ = funnel(D, WT, ON, "2013-10-01", "2026-03-01", step=11, on_w=0.0)
print(f"ABLATION overnight (on_w=0, iso-reste): p={p_noon:.3f} -> contribution = {p_pool-p_noon:+.3f}", flush=True)
