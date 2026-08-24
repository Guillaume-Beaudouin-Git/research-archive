"""Q1 — tail-decorrelation breakout vs book (container prerequisite). ρ_tail ≤ 0.3 gate."""
import sys, time, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
import lib_inject as LI

HERE = Path(__file__).resolve().parent; CACHE = HERE/"_cache"; RES = HERE/"results"
t0 = time.time()
M = LI.load_stack()
WT, ON = LI.V.align(M, *LI.E.build_signals())
print(f"v22 stack n={M['n']} {M['dates_idx'][0].date()}..{M['dates_idx'][-1].date()} [{time.time()-t0:.0f}s]")
BK = LI.book_daily_series(M, WT, ON)
BK.to_parquet(CACHE/"book_daily.parquet")
print(f"book daily: vol {BK.book_ret.std()*np.sqrt(252)*100:.1f}%/yr mean {BK.book_ret.mean()*1e4:+.1f}bps "
      f"worst {BK.book_ret.min()*100:.2f}% [{time.time()-t0:.0f}s]")

brk = pd.read_parquet(CACHE/"brk_pooled_lb.parquet")["net"]
df = pd.DataFrame({"book": BK.book_ret, "brk": brk.reindex(BK.index)}).dropna()
df = df[df.brk != 0.0]      # days the breakout actually traded
print(f"aligned days (breakout active): {len(df)}")

b_q10 = df.book.quantile(.10); k_q10 = df.brk.quantile(.10); b_q05 = df.book.quantile(.05)
book_bot = df.book <= b_q10; brk_bot = df.brk <= k_q10
union = book_bot | brk_bot
rho_tail = float(spearmanr(df.book[union], df.brk[union]).correlation)
rho_full = float(spearmanr(df.book, df.brk).correlation)
pear_full = float(df.book.corr(df.brk))
co = float((book_bot & brk_bot).mean()); lift = co / (0.10 * 0.10)
p_brk_given_book = float(brk_bot[book_bot].mean()); lift_cond = p_brk_given_book / 0.10
brk_on_bookworst5 = float(df.brk[df.book <= b_q05].mean())
brk_mean_all = float(df.brk.mean())

print(f"\nρ_tail (Spearman, union bottom-decile) = {rho_tail:+.3f}   [gate ≤ 0.30]")
print(f"  full-sample ρ_Spearman {rho_full:+.3f} | Pearson {pear_full:+.3f}")
print(f"  tail co-occurrence: P(both bottom-10%) {co:.4f} vs indep 0.0100 → lift {lift:.2f}")
print(f"  P(brk bottom-10% | book bottom-10%) {p_brk_given_book:.3f} vs 0.10 → lift {lift_cond:.2f}")
print(f"  breakout mean on book WORST-5% days {brk_on_bookworst5*1e4:+.2f}bps (vs all-days {brk_mean_all*1e4:+.2f}bps)"
      f"  → {'PAYS when book bleeds (container ideal)' if brk_on_bookworst5>0 else 'also loses on book-crash days'}")
GATE = rho_tail <= 0.30
print(f"\nQ1 GATE ρ_tail ≤ 0.30: {'PASS — breakout is tail-decorrelated, container logic can apply' if GATE else 'FAIL — tail-correlated, cannot help'}")

json.dump(dict(rho_tail=rho_tail, rho_full=rho_full, pearson_full=pear_full,
               co_occ=co, co_lift=lift, p_brk_given_book=p_brk_given_book, cond_lift=lift_cond,
               brk_on_bookworst5_bps=brk_on_bookworst5*1e4, brk_mean_all_bps=brk_mean_all*1e4,
               n_days=len(df), gate_pass=bool(GATE)), open(RES/"q1_tail.json","w"), indent=1)
print(f"saved q1 [{time.time()-t0:.0f}s]")
