//+------------------------------------------------------------------+
//| spec_v22.mqh — GÉNÉRÉ depuis spec_v22.yaml par make_spec_mqh.py  |
//| NE PAS ÉDITER À LA MAIN (ancre #20: régénération byte-identique). |
//| Pins: 605f4a4 + 4e1bac5 + ad403ce ; yaml sha 3e7626f6…            |
//+------------------------------------------------------------------+
#define SPEC_VERSION        "v2.2.2"
#define SPEC_SHA256         "3e7626f6d3fdc53050a9ad1097c13c8af05179d380f5090141c323561060563b"
#define SPEC_PIN_CONTRACT   "605f4a426da3eac4f5a2644bca774a07f1e5f754"
#define SPEC_PIN_RESIDUALS  "4e1bac5cf6486fcd0070876d47dd2dcdc7a8f539"
#define SPEC_PIN_YAML       "ad403cefb7f8af9285acb1bdd424d0601080c5b5"

// ---- compte & règles FTMO (2-step Swing $10k) ----
#define ACCOUNT_SIZE_USD    10000
#define DAILY_LOSS_FRAC     0.05      // equity >= balance@00:00 Prague - 5% initial
#define MAX_LOSS_FRAC       0.10      // floor statique = 90% initial
#define TARGET_P1           0.1
#define TARGET_P2           0.05
#define MIN_TRADING_DAYS    4
#define WALL_DAYS           91
#define GAP_BDAYS           3
#define RETRY_BDAYS         2

// ---- horaires SPEC en CET (mapper au fuseau serveur via input EA, ne pas convertir ici) ----
#define SCHED_GER40_EXIT_CET    "09:00"
#define SCHED_US100_EXIT_CET    "15:30"
#define SCHED_GER40_ENTRY_CET   "17:35"
#define SCHED_REBALANCE_CET     "22:05"

// ---- challenge (P1/P2) ----
#define CH_VM               14
#define CH_P2_MULT          1.2
#define CH_ON_W             0.6
#define CH_ORB_RISK         0   // v2.2: ORB OFF comme sleeve P&L
#define CH_MICRO_ORB        true
#define CH_BREAKER_FRAC     0.3
#define CH_TAPER            0.02
#define CH_GLIDE            0.5
#define CH_PACE_ON          1
#define CH_PACE_K           1
#define CH_ABANDON_BUF      0.02
#define CH_ABANDON_DAYS     5
#define CH_MARGIN_CAP       0.6
#define MRATE_XAUUSD        0.02
#define MRATE_USDJPY        0.01
#define MRATE_US100         0.02
#define MRATE_GER40         0.02
#define LOT_STEP            0.01
#define LEG_CAP_PRE_VM      1.5

// ---- v2.8 : cap de NOTIONNEL par jambe (risk_overlays.leg_leverage_cap) ----
// Unité = notionnel/equity, INVARIANTE EN vm. Appliqué AVANT le cap marge.
// 0 = pas de cap. À NE PAS confondre avec LEG_CAP_PRE_VM ci-dessus (garde-fou
// anti-lot-aberrant à 42x eq, libellé pre-vm donc suiveur de vm).
#define LEG_LEV_CAP_XAUUSD   0
#define LEG_LEV_CAP_USDJPY   12
#define LEG_LEV_CAP_US100   0
#define LEG_LEV_CAP_GER40   0

// ---- MICRO-ORB = LE compteur de jours (bloc micro_orb_day_counter du yaml) ----
// entrée canonique post-OR (OR 15:30-16:00 CET, fill premier bar 5min post-OR);
// sorties V2+E7: stop = côté opposé OR (1R), trail-to-BE après +1R, time-stop 22:00 CET;
// CONDITION: posté seulement si AUCUN autre trade ouvert à 21:30 CET (flag opened, sémantique 605f4a4);
// backstop no-signal (fallback RARE, 50/13068 jours sim): open/close 0.01 lot si
//   aucun signal ORB ET rien d'ouvert ET min-days non atteint ET balance >= cible.
#define MICRO_ORB_SYMBOL    "US100.cash"
#define MICRO_ORB_LOTS      0.01
#define MICRO_OR_START_CET  "15:30"
#define MICRO_OR_END_CET    "16:00"
#define MICRO_TIMESTOP_CET  "22:00"
#define MICRO_COND_CET      "21:30"

// ---- funded (switch au funding, même événement que vm14->1.0) ----
#define FU_VM               1
#define FU_ON_W             0.35
#define FU_ORB_RISK         0.0025   // ORB ON full spec
#define FU_MICRO_ORB        false
#define FU_WD_EVERY_TDAYS   14
#define FU_SPLIT_TRADER     0.8
#define ORB_RT_BPS          "era"  // era jusqu'au verdict 2026-06-15

// ---- signaux (côté brain; embarqués pour complétude, zéro constante manuelle) ----
#define GOLD_LOOKBACKS      "60,120,250"
#define GOLD_THETA          0.34
#define GOLD_VOL_TARGET     0.1
#define J1_SIGNAL           "12-1 momentum LO (p[t-21]/p[t-252]-1 > 0)"
#define ON_NIGHTS           "Mon,Tue"

// ---- v2.2.1 bornes de sanité DATÉES (specs mesurées, source compte Standard) ----
// L'EA lit SYMBOL_SWAP_LONG/SHORT, SYMBOL_SWAP_ROLLOVER3DAYS et la marge live
// (OrderCalcMargin) à l'init + au rebalance ; hors borne -> ALERTE (state).
// Marge SWING officielle (fx 1:30, indices 1:15, métaux 1:9) À CONFIRMER sur
// les specs du serveur Swing au déploiement — gate bloquant (recost_v221).
#define SANITY_READ_DATE    "2026-06-10"
#define SANITY_SOURCE       "FTMO-Demo Standard"
#define SANITY_SWAP_REL     0.25
#define SANITY_MARGIN_REL   0.25
#define ANCHOR_SWL_XAUUSD     (-65.68)
#define ANCHOR_SWS_XAUUSD     (-14.53)
#define ANCHOR_R3D_XAUUSD     3   // ENUM_DAY_OF_WEEK
#define MARGIN_STD_XAUUSD     0.033333
#define MARGIN_SWING_XAUUSD   0.111111
#define MARGIN_MEAS_XAUUSD    0.066667
#define ANCHOR_SWL_USDJPY     (0.96)
#define ANCHOR_SWS_USDJPY     (-20.3)
#define ANCHOR_R3D_USDJPY     3   // ENUM_DAY_OF_WEEK
#define MARGIN_STD_USDJPY     0.010000
#define MARGIN_SWING_USDJPY   0.033333
#define MARGIN_MEAS_USDJPY    0.033335
#define ANCHOR_SWL_US100     (-637.16)
#define ANCHOR_SWS_US100     (27.49)
#define ANCHOR_R3D_US100     5   // ENUM_DAY_OF_WEEK
#define MARGIN_STD_US100     0.020000
#define MARGIN_SWING_US100   0.066667
#define MARGIN_MEAS_US100    0.066667
#define ANCHOR_SWL_GER40     (-393.88)
#define ANCHOR_SWS_GER40     (-48.68)
#define ANCHOR_R3D_GER40     5   // ENUM_DAY_OF_WEEK
#define MARGIN_STD_GER40     0.020000
#define MARGIN_SWING_GER40   0.066667
#define MARGIN_MEAS_GER40    0.066670

//+------------------------------------------------------------------+
//| Assert d'init: MQL5/Files/spec_v22.sha256 doit == SPEC_SHA256.    |
//| Refus de trader si absent ou différent (zéro constante manuelle). |
//+------------------------------------------------------------------+
bool SpecHashOK()
  {
   int h = FileOpen("spec_v22.sha256", FILE_READ|FILE_TXT|FILE_ANSI);
   if(h == INVALID_HANDLE)
     { Print("SPEC ASSERT FAIL: MQL5/Files/spec_v22.sha256 absent"); return(false); }
   string s = FileReadString(h);
   FileClose(h);
   StringTrimLeft(s); StringTrimRight(s);
   if(s != SPEC_SHA256)
     { Print("SPEC ASSERT FAIL: hash fichier ", s, " != embarqué ", SPEC_SHA256); return(false); }
   Print("SPEC OK ", SPEC_VERSION, " sha ", StringSubstr(SPEC_SHA256, 0, 12), "…");
   return(true);
  }
