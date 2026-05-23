# Sprint 1 IC Scan — Verdict

**Generated**: 2026-05-23 19:56  
**Universe**: SPY, QQQ, EWQ | **Horizons**: 1, 3, 5, 10d  
**n_tests this sprint**: 92 (AMTP not applied at IC scan stage)  

**Gates**: |IC| > 0.02, |t_HAC| > 2.0, stability > 0.70, post-2020 consistent

---

## Results Table

```
        signal asset  h  n_obs  ic_mean  t_hac  ic_post2020  stability verdict
        s1_vrp   SPY  1   5026    0.033  2.391        0.040      0.756      GO
        s1_vrp   SPY  3   5024    0.041  2.027        0.043      0.794      GO
        s1_vrp   SPY  5   5022    0.049  1.965        0.045      0.831   NO-GO
        s1_vrp   SPY 10   5017    0.037  1.148        0.036      0.699   NO-GO
        s1_vrp   QQQ  1   5026    0.050  3.592        0.069      0.854      GO
        s1_vrp   QQQ  3   5024    0.064  3.096        0.072      0.844      GO
        s1_vrp   QQQ  5   5022    0.073  2.840        0.082      0.841      GO
        s1_vrp   QQQ 10   5017    0.075  2.330        0.087      0.831      GO
   s2_vix_term   SPY  1   4014   -0.042 -2.704       -0.035      0.939      GO
   s2_vix_term   SPY  3   4012   -0.058 -2.500       -0.064      0.834      GO
   s2_vix_term   SPY  5   4010   -0.070 -2.537       -0.084      0.853      GO
   s2_vix_term   SPY 10   4005   -0.080 -2.278       -0.144      0.845      GO
   s2_vix_term   QQQ  1   4014   -0.033 -2.100       -0.039      0.968      GO
   s2_vix_term   QQQ  3   4012   -0.035 -1.534       -0.048      0.778   NO-GO
   s2_vix_term   QQQ  5   4010   -0.051 -1.886       -0.076      0.821   NO-GO
   s2_vix_term   QQQ 10   4005   -0.060 -1.745       -0.115      0.826   NO-GO
   s2_vix_term   EWQ  1   4014   -0.042 -2.703       -0.036      0.970      GO
   s2_vix_term   EWQ  3   4012   -0.043 -1.867       -0.061      0.901   NO-GO
   s2_vix_term   EWQ  5   4010   -0.038 -1.363       -0.068      0.859   NO-GO
   s2_vix_term   EWQ 10   4005   -0.038 -1.113       -0.096      0.708   NO-GO
        s3_tom   SPY  1   5026   -0.004 -0.293        0.001      0.599   NO-GO
        s3_tom   SPY  3   5024    0.005  0.275        0.025      0.498   NO-GO
        s3_tom   SPY  5   5022    0.011  0.475        0.046      0.557   NO-GO
        s3_tom   SPY 10   5017    0.027  1.113        0.045      0.618   NO-GO
        s3_tom   QQQ  1   5026   -0.008 -0.533        0.006      0.568   NO-GO
        s3_tom   QQQ  3   5024   -0.003 -0.148        0.019      0.477   NO-GO
        s3_tom   QQQ  5   5022   -0.001 -0.057        0.037      0.469   NO-GO
        s3_tom   QQQ 10   5017    0.015  0.617        0.033      0.598   NO-GO
        s3_tom   EWQ  1   5026   -0.008 -0.550       -0.017      0.549   NO-GO
        s3_tom   EWQ  3   5024   -0.016 -0.760        0.028      0.666   NO-GO
        s3_tom   EWQ  5   5022   -0.023 -0.993        0.053      0.674   NO-GO
        s3_tom   EWQ 10   5017   -0.000 -0.001        0.080      0.435   NO-GO
  s4a_pcr_only   SPY  1   3204   -0.025 -1.412          NaN      0.846   NO-GO
  s4a_pcr_only   SPY  3   3204   -0.047 -1.737          NaN      0.870   NO-GO
  s4a_pcr_only   SPY  5   3204   -0.059 -1.769          NaN      0.809   NO-GO
  s4a_pcr_only   SPY 10   3204   -0.071 -1.596          NaN      0.733   NO-GO
  s4a_pcr_only   QQQ  1   3204   -0.024 -1.391          NaN      0.835   NO-GO
  s4a_pcr_only   QQQ  3   3204   -0.040 -1.481          NaN      0.850   NO-GO
  s4a_pcr_only   QQQ  5   3204   -0.050 -1.482          NaN      0.815   NO-GO
  s4a_pcr_only   QQQ 10   3204   -0.060 -1.352          NaN      0.798   NO-GO
  s4a_pcr_only   EWQ  1   3204   -0.017 -1.006          NaN      0.859   NO-GO
  s4a_pcr_only   EWQ  3   3204   -0.035 -1.319          NaN      0.850   NO-GO
  s4a_pcr_only   EWQ  5   3204   -0.056 -1.611          NaN      0.875   NO-GO
  s4a_pcr_only   EWQ 10   3204   -0.074 -1.618          NaN      0.785   NO-GO
s4b_naaim_only   SPY  1   4923    0.007  0.505        0.009      0.682   NO-GO
s4b_naaim_only   SPY  3   4921    0.023  1.064        0.031      0.817   NO-GO
s4b_naaim_only   SPY  5   4919    0.024  0.923        0.036      0.782   NO-GO
s4b_naaim_only   SPY 10   4914    0.029  0.847        0.082      0.786   NO-GO
s4b_naaim_only   QQQ  1   4923    0.012  0.858        0.011      0.723   NO-GO
s4b_naaim_only   QQQ  3   4921    0.022  1.034        0.034      0.767   NO-GO
s4b_naaim_only   QQQ  5   4919    0.025  0.954        0.040      0.716   NO-GO
s4b_naaim_only   QQQ 10   4914    0.019  0.560        0.062      0.677   NO-GO
s4b_naaim_only   EWQ  1   4923    0.005  0.343        0.007      0.661   NO-GO
s4b_naaim_only   EWQ  3   4921    0.021  0.957        0.039      0.714   NO-GO
s4b_naaim_only   EWQ  5   4919    0.033  1.230        0.066      0.735   NO-GO
s4b_naaim_only   EWQ 10   4914    0.043  1.248        0.119      0.717   NO-GO
 s4c_composite   SPY  1   3196   -0.017 -0.977          NaN      0.750   NO-GO
 s4c_composite   SPY  3   3196   -0.027 -0.996          NaN      0.770   NO-GO
 s4c_composite   SPY  5   3196   -0.045 -1.357          NaN      0.838   NO-GO
 s4c_composite   SPY 10   3196   -0.083 -1.930          NaN      0.879   NO-GO
 s4c_composite   QQQ  1   3196   -0.012 -0.669          NaN      0.577   NO-GO
 s4c_composite   QQQ  3   3196   -0.020 -0.771          NaN      0.560   NO-GO
 s4c_composite   QQQ  5   3196   -0.037 -1.138          NaN      0.671   NO-GO
 s4c_composite   QQQ 10   3196   -0.080 -1.853          NaN      0.676   NO-GO
 s4c_composite   EWQ  1   3196   -0.018 -1.078          NaN      0.730   NO-GO
 s4c_composite   EWQ  3   3196   -0.030 -1.136          NaN      0.696   NO-GO
 s4c_composite   EWQ  5   3196   -0.054 -1.591          NaN      0.855   NO-GO
 s4c_composite   EWQ 10   3196   -0.101 -2.389          NaN      0.928   NO-GO
     s5_xs_mom   SPY  1   4931   -0.001 -0.096       -0.010      0.608   NO-GO
     s5_xs_mom   SPY  3   4929   -0.017 -0.808       -0.040      0.779   NO-GO
     s5_xs_mom   SPY  5   4927   -0.016 -0.594       -0.051      0.727   NO-GO
     s5_xs_mom   SPY 10   4922   -0.015 -0.419       -0.049      0.711   NO-GO
     s5_xs_mom   QQQ  1   4931    0.011  0.760        0.027      0.418   NO-GO
     s5_xs_mom   QQQ  3   4929   -0.004 -0.162        0.011      0.688   NO-GO
     s5_xs_mom   QQQ  5   4927   -0.001 -0.029        0.011      0.647   NO-GO
     s5_xs_mom   QQQ 10   4922   -0.012 -0.322        0.005      0.664   NO-GO
     s5_xs_mom   EWQ  1   4931   -0.012 -0.895        0.003      0.663   NO-GO
     s5_xs_mom   EWQ  3   4929   -0.009 -0.430        0.025      0.605   NO-GO
     s5_xs_mom   EWQ  5   4927   -0.008 -0.315        0.026      0.590   NO-GO
     s5_xs_mom   EWQ 10   4922   -0.012 -0.331        0.001      0.581   NO-GO
     s6_hy_oas   SPY  1   4982   -0.003 -0.190        0.018      0.573   NO-GO
     s6_hy_oas   SPY  3   4980   -0.012 -0.593        0.029      0.573   NO-GO
     s6_hy_oas   SPY  5   4978   -0.013 -0.585        0.027      0.583   NO-GO
     s6_hy_oas   SPY 10   4973    0.010  0.388        0.011      0.425   NO-GO
     s6_hy_oas   QQQ  1   4982    0.007  0.491        0.011      0.536   NO-GO
     s6_hy_oas   QQQ  3   4980   -0.001 -0.061        0.024      0.488   NO-GO
     s6_hy_oas   QQQ  5   4978   -0.009 -0.376        0.007      0.631   NO-GO
     s6_hy_oas   QQQ 10   4973    0.013  0.538        0.006      0.434   NO-GO
     s6_hy_oas   EWQ  1   4982   -0.013 -0.914       -0.006      0.658   NO-GO
     s6_hy_oas   EWQ  3   4980   -0.019 -0.976       -0.016      0.728   NO-GO
     s6_hy_oas   EWQ  5   4978   -0.012 -0.535        0.008      0.620   NO-GO
     s6_hy_oas   EWQ 10   4973    0.010  0.400        0.037      0.470   NO-GO
```

---

## Per-Signal Narrative

### S1_VRP
**Status**: GO on 6 (signal×asset×h) combinations.  
**Best**: QQQ h=1d — IC=0.050, t=3.59, stab=0.85  

### S2_VIX_TERM
**Status**: GO on 6 (signal×asset×h) combinations.  
**Best**: QQQ h=1d — IC=-0.033, t=-2.10, stab=0.97  

### S3_TOM
**Status**: NO-GO (all tested combinations fail at least one gate).  
Best t_HAC: SPY h=10d — IC=0.027, t=1.11  

### S4A_PCR_ONLY
**Status**: NO-GO (all tested combinations fail at least one gate).  
Best t_HAC: SPY h=5d — IC=-0.059, t=-1.77  

### S4B_NAAIM_ONLY
**Status**: NO-GO (all tested combinations fail at least one gate).  
Best t_HAC: EWQ h=10d — IC=0.043, t=1.25  

### S4C_COMPOSITE
**Status**: NO-GO (all tested combinations fail at least one gate).  
Best t_HAC: EWQ h=10d — IC=-0.101, t=-2.39  

### S5_XS_MOM
**Status**: NO-GO (all tested combinations fail at least one gate).  
Best t_HAC: EWQ h=1d — IC=-0.012, t=-0.90  

### S6_HY_OAS
**Status**: NO-GO (all tested combinations fail at least one gate).  
Best t_HAC: EWQ h=3d — IC=-0.019, t=-0.98  

---

## Known Limitations & Sprint 2 Items

- **EWQ S1 VRP**: VSTOXX not available on free platforms (yfinance 404, Stooq requires API key). EWQ VRP excluded. Sprint 2: download `data/vstoxx_manual.csv` from STOXX.com.
- **S2 primary (VX1/VX2)**: CBOE VX futures require manual CSV. Sprint 1 uses VIX9D/VIX fallback (2011+).
- **S4 AAII**: Akamai-blocked. S4a/S4c use PCR only (2006-2019), S4b uses NAAIM alone.
- **S4 PCR coverage**: CBOE PCR frozen at 2019-10-04. S4a and S4c limited to this window.
- **BAMLH0A0HYM2 (HY OAS)**: ICE licensing restricts FRED download to ~3y. S6 uses HYG proxy (2007+).

## S3 TOM Event Study

```
 offset  n_events  mean_ret  std_ret  t_stat
     -1       233    0.0004   0.0118  0.5130
      0       233   -0.0005   0.0103 -0.7120
      1       232    0.0010   0.0128  1.2150
      2       232    0.0008   0.0113  1.1120
      3       232    0.0004   0.0113  0.5050
```
