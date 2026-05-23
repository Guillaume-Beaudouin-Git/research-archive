# Sprint 2 — Full Backtest Results

**Generated**: 2026-05-23 20:18  
**Vol target**: 10% annualized  
**Cost**: 0.10% round-trip (conservative ETF/next-day entry)  
**Position model**: daily vol-targeted; signal z-score 252d rolling; clip ±3σ  

**Gates**:  
- RESEARCH_PASS: Sharpe > 0.7, MaxDD > -25%, WF positive fraction > 50%  
- PROPFIRM_PASS: Sharpe > 1.0, MaxDD > -10%, WF positive fraction > 60%  

---

## Results Summary

```
       strategy  n_years  sharpe_gross  sharpe_net  ann_ret  ann_vol  max_dd  calmar  turnover_ann  wf_pos_frac verdict
     s1_vrp_SPY   20.000         0.309       0.143    0.020    0.140  -0.538   0.037        46.682        0.400    FAIL
     s1_vrp_QQQ   20.000         0.467       0.341    0.044    0.129  -0.416   0.106        32.874        0.800    FAIL
s2_vix_term_SPY   15.900         0.184      -0.129   -0.019    0.144  -0.655  -0.028        71.808        0.200    FAIL
s2_vix_term_QQQ   15.900         0.174      -0.085   -0.012    0.136  -0.467  -0.025        56.085        0.400    FAIL
s2_vix_term_EWQ   15.900         0.259       0.017    0.002    0.137  -0.482   0.005        52.860        0.600    FAIL
      combo_SPY   19.500           NaN       0.171    0.022    0.129  -0.465   0.048           NaN        0.400    FAIL
      combo_QQQ   19.500           NaN       0.319    0.036    0.114  -0.290   0.125           NaN        0.600    FAIL
  portfolio_erc   20.000           NaN       0.088    0.006    0.074  -0.247   0.026           NaN        0.400    FAIL
```

---

## Per-Strategy Detail

### s1_vrp_SPY
**Verdict**: FAIL  
**Period**: 20.0 years, 5047 days  
**Sharpe**: 0.143  
**Ann. return**: 2.01%  
**Ann. vol**: 14.03%  
**Max DD**: -53.77%  
**Calmar**: 0.037  
**Sharpe (gross/net)**: 0.309 / 0.143  
**Annual turnover**: 46.7× (position notional)  
**WF positive frac**: 40% (5 folds)  
**WF fold Sharpes**: [np.float64(0.085), np.float64(-0.066), np.float64(-0.676), np.float64(0.734), np.float64(-0.283)]  

### s1_vrp_QQQ
**Verdict**: FAIL  
**Period**: 20.0 years, 5047 days  
**Sharpe**: 0.341  
**Ann. return**: 4.40%  
**Ann. vol**: 12.90%  
**Max DD**: -41.64%  
**Calmar**: 0.106  
**Sharpe (gross/net)**: 0.467 / 0.341  
**Annual turnover**: 32.9× (position notional)  
**WF positive frac**: 80% (5 folds)  
**WF fold Sharpes**: [np.float64(0.049), np.float64(-0.284), np.float64(0.033), np.float64(0.881), np.float64(0.316)]  

### s2_vix_term_SPY
**Verdict**: FAIL  
**Period**: 15.9 years, 4014 days  
**Sharpe**: -0.129  
**Ann. return**: -1.86%  
**Ann. vol**: 14.44%  
**Max DD**: -65.48%  
**Calmar**: -0.028  
**Sharpe (gross/net)**: 0.184 / -0.129  
**Annual turnover**: 71.8× (position notional)  
**WF positive frac**: 20% (5 folds)  
**WF fold Sharpes**: [np.float64(-0.193), np.float64(-0.139), np.float64(-0.763), np.float64(-0.315), np.float64(0.516)]  

### s2_vix_term_QQQ
**Verdict**: FAIL  
**Period**: 15.9 years, 4014 days  
**Sharpe**: -0.085  
**Ann. return**: -1.16%  
**Ann. vol**: 13.63%  
**Max DD**: -46.73%  
**Calmar**: -0.025  
**Sharpe (gross/net)**: 0.174 / -0.085  
**Annual turnover**: 56.1× (position notional)  
**WF positive frac**: 40% (5 folds)  
**WF fold Sharpes**: [np.float64(-0.585), np.float64(0.215), np.float64(-0.485), np.float64(-0.225), np.float64(0.54)]  

### s2_vix_term_EWQ
**Verdict**: FAIL  
**Period**: 15.9 years, 4014 days  
**Sharpe**: 0.017  
**Ann. return**: 0.23%  
**Ann. vol**: 13.71%  
**Max DD**: -48.21%  
**Calmar**: 0.005  
**Sharpe (gross/net)**: 0.259 / 0.017  
**Annual turnover**: 52.9× (position notional)  
**WF positive frac**: 60% (5 folds)  
**WF fold Sharpes**: [np.float64(-0.163), np.float64(0.212), np.float64(-0.718), np.float64(0.436), np.float64(0.339)]  

### combo_SPY
**Verdict**: FAIL  
**Period**: 19.5 years, 4922 days  
**Sharpe**: 0.171  
**Ann. return**: 2.21%  
**Ann. vol**: 12.93%  
**Max DD**: -46.51%  
**Calmar**: 0.048  
**Sharpe (gross/net)**: nan / 0.171  
**Annual turnover**: nan× (position notional)  
**WF positive frac**: 40% (5 folds)  
**WF fold Sharpes**: [np.float64(-0.012), np.float64(0.246), np.float64(-0.662), np.float64(0.328), np.float64(0.0)]  

### combo_QQQ
**Verdict**: FAIL  
**Period**: 19.5 years, 4922 days  
**Sharpe**: 0.319  
**Ann. return**: 3.63%  
**Ann. vol**: 11.37%  
**Max DD**: -29.01%  
**Calmar**: 0.125  
**Sharpe (gross/net)**: nan / 0.319  
**Annual turnover**: nan× (position notional)  
**WF positive frac**: 60% (5 folds)  
**WF fold Sharpes**: [np.float64(-0.092), np.float64(0.068), np.float64(-0.197), np.float64(0.64), np.float64(0.333)]  

### portfolio_erc
**Verdict**: FAIL  
**Period**: 20.0 years, 5047 days  
**Sharpe**: 0.088  
**Ann. return**: 0.65%  
**Ann. vol**: 7.41%  
**Max DD**: -24.69%  
**Calmar**: 0.026  
**Sharpe (gross/net)**: nan / 0.088  
**Annual turnover**: nan× (position notional)  
**WF positive frac**: 40% (5 folds)  
**WF fold Sharpes**: [np.float64(-0.004), np.float64(-0.101), np.float64(-0.32), np.float64(0.258), np.float64(0.227)]  

---

## Cost Sensitivity (ETF 0.10% RT vs Futures 0.01% RT)

Futures cost projection = gross_sharpe − drag_etf × 0.10  (linear cost assumption)

| Strategy | Gross SR | ETF net (0.10%RT) | Fut net (0.01%RT) | Turnover/yr |
|----------|----------|-------------------|--------------------|-------------|
| s1_vrp_SPY | 0.309 | 0.143 | 0.292 | 47× |
| s1_vrp_QQQ | 0.467 | 0.341 | 0.454 | 33× |
| s2_vix_term_SPY | 0.184 | -0.129 | 0.153 | 72× |
| s2_vix_term_QQQ | 0.174 | -0.085 | 0.148 | 56× |
| s2_vix_term_EWQ | 0.259 | 0.017 | 0.235 | 53× |
| combo_SPY | nan | 0.171 | nan | nan× |
| combo_QQQ | nan | 0.319 | nan | nan× |
| portfolio_erc | nan | 0.088 | nan | nan× |

---

## Sprint 2 Remaining Items

1. **S1 EWQ VRP with VSTOXX**: download `data/vstoxx_manual.csv` from STOXX.com
2. **S2 primary (VX1/VX2)**: download `data/vx_futures_manual.csv` from CBOE;    VX ratio is the mechanistically correct term structure signal
3. **S4 extended coverage**: AAII weekly + post-2019 CBOE PCR (manual downloads)
4. **Propfirm sizing**: if PROPFIRM_PASS, compute MES/MNQ contract sizing for $50K account
