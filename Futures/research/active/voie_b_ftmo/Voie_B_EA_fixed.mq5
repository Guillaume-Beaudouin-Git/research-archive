//+------------------------------------------------------------------+
//| Voie_B_EA_fixed.mq5                                             |
//| Intraday gap-continuation on US indices, FTMO 2-step            |
//| FIXES vs v1.00:                                                  |
//|   Bug1: DST-aware UTC session times (EDT/EST automatic)          |
//|   Bug2: challenge_start_balance via GlobalVariable               |
//|   Bug3: prev_close lookup uses DST-aware close hour              |
//|   Bug4: vol-targeting aligned with Python backtest               |
//| v1.20: per-symbol trade log with raw fill prices (slip in Python)|
//| v1.21: exit guard (hour>xh || hour==xh&&min>=xm) + forced-eod   |
//+------------------------------------------------------------------+
#property copyright "Voie B - Quant Research"
#property version   "1.21"
#property strict

#include <Trade\Trade.mqh>
CTrade trade;

//--- inputs --------------------------------------------------------
input group           "=== Universe & Signal ==="
input string          Symbol_1            = "US500.cash";
input string          Symbol_2            = "US100.cash";
input string          Symbol_3            = "US30.cash";
input string          Symbol_4            = "US2000.cash";
input double          GapThresholdBps     = 15.0;
input int             MinConfirmation     = 2;

input group           "=== Sizing ==="
input bool            UseVolTarget        = true;       // true=vol-target (aligned w/ Python), false=ratchet
input double          VolTargetAnnual     = 0.10;       // [ACTIVE] 10% portfolio vol target
input int             VolLookbackDays     = 60;         // rolling window for vol estimate
input double          MaxLeverage         = 5.0;        // cap (Python: 5x)
// Ratchet params (only used when UseVolTarget=false — legacy mode)
input double          BaseLeverage        = 2.5;
input double          Ratchet             = 25.0;

input double          KillSwitchUnlev     = -0.012;     // -1.2% unlevered intraday stop

input group           "=== Risk filters ==="
input string          SkipDates           = "";         // comma sep YYYY-MM-DD (FOMC, NFP)

input group           "=== Logging ==="
input int             MagicNumber         = 20260601;
input bool            VerboseLog          = true;

//--- global state --------------------------------------------------
string   g_symbols[4];
double   g_prev_close[4];
bool     g_entered_today    = false;
datetime g_last_entry_day   = 0;
double   g_equity_at_entry  = 0;
double   g_levered_kill_threshold = 0;

#define GV_START_BAL "VoieB_StartBalance"
#define LOG_FILE "VoieB_decisions.csv"
int      g_log_handle = INVALID_HANDLE;

//--- Trade entry staged at entry, completed at exit ----------------
// Raw fill prices only — slippage computed in slip_analysis.py
struct TradeEntry {
   string date_utc;      // "YYYY-MM-DD"
   string sym;
   int    dir;           // +1 LONG, -1 SHORT
   double gap_bps;
   double lev;
   double lots;
   double mid_signal;    // (BID+ASK)/2 captured before order
   double fill_entry;    // trade.ResultPrice() after buy/sell
   double spread_bps;    // (ASK-BID)/mid*1e4 at entry tick
   string ts_entry;      // "YYYY-MM-DD HH:MM:SS" UTC at fill
   bool   active;
};
TradeEntry g_entries[4];

//+------------------------------------------------------------------+
//| CSV trade log — one row per symbol traded                        |
//| Slippage NOT calculated here — raw prices for Python analysis    |
//+------------------------------------------------------------------+
void OpenDecisionLog() {
   bool new_file = !FileIsExist(LOG_FILE, FILE_COMMON);
   g_log_handle = FileOpen(LOG_FILE,
                           FILE_WRITE | FILE_READ | FILE_CSV | FILE_ANSI | FILE_COMMON,
                           ',');
   if(g_log_handle == INVALID_HANDLE) {
      PrintFormat("WARN: cannot open log %s (error %d)", LOG_FILE, GetLastError());
      return;
   }
   FileSeek(g_log_handle, 0, SEEK_END);
   if(new_file)
      FileWrite(g_log_handle,
                "date_utc", "symbol", "direction", "gap_bps", "leverage", "lots",
                "mid_signal", "fill_entry", "spread_signal_bps", "ts_entry_utc",
                "mid_exit", "fill_exit", "ts_exit_utc", "exit_reason",
                "pnl_points", "pnl_account_pct");
}

void WriteTradeLog(TradeEntry &e, double mid_exit, double fill_exit,
                   string ts_exit, string exit_reason,
                   double pnl_pts, double pnl_pct) {
   if(g_log_handle == INVALID_HANDLE) return;
   FileWrite(g_log_handle,
             e.date_utc, e.sym, e.dir,
             NormalizeDouble(e.gap_bps, 1),
             NormalizeDouble(e.lev, 4),
             NormalizeDouble(e.lots, 2),
             NormalizeDouble(e.mid_signal, 4),
             NormalizeDouble(e.fill_entry, 4),
             NormalizeDouble(e.spread_bps, 2),
             e.ts_entry,
             NormalizeDouble(mid_exit, 4),
             NormalizeDouble(fill_exit, 4),
             ts_exit,
             exit_reason,
             NormalizeDouble(pnl_pts, 2),
             NormalizeDouble(pnl_pct * 100.0, 6));
   FileFlush(g_log_handle);
}

//+------------------------------------------------------------------+
//| DST helpers                                                      |
//+------------------------------------------------------------------+

// Day of the Nth Sunday in a given year/month (1-based day).
int NthSunday(int year, int month, int n) {
   MqlDateTime d; ZeroMemory(d);
   d.year = year; d.mon = month; d.day = 1; d.hour = 12;
   datetime t = StructToTime(d);
   MqlDateTime tmp; TimeToStruct(t, tmp);
   // first Sunday: if day_of_week=0(Sun) it's day 1, else 8-dow
   int first_sun = (tmp.day_of_week == 0) ? 1 : 8 - tmp.day_of_week;
   return first_sun + (n - 1) * 7;
}

// US Eastern UTC offset: returns 4 (EDT) or 5 (EST).
// EDT: 2nd Sun March 07:00 UTC → 1st Sun November 06:00 UTC.
int GetETOffsetHours() {
   datetime utc_now = TimeGMT();
   MqlDateTime dt; TimeToStruct(utc_now, dt);
   int y = dt.year;

   MqlDateTime edt_start_s; ZeroMemory(edt_start_s);
   edt_start_s.year = y; edt_start_s.mon = 3;
   edt_start_s.day  = NthSunday(y, 3, 2);
   edt_start_s.hour = 7;   // 02:00 EST = 07:00 UTC
   datetime edt_start = StructToTime(edt_start_s);

   MqlDateTime edt_end_s; ZeroMemory(edt_end_s);
   edt_end_s.year = y; edt_end_s.mon = 11;
   edt_end_s.day  = NthSunday(y, 11, 1);
   edt_end_s.hour = 6;    // 02:00 EDT = 06:00 UTC
   datetime edt_end = StructToTime(edt_end_s);

   return (utc_now >= edt_start && utc_now < edt_end) ? 4 : 5;
}

// Derive UTC session bounds from ET offset.
// US Open  = 09:31 ET,  US Close-2min = 15:58 ET,  EOD = 16:00 ET.
void GetSessionBoundsUTC(int &entry_h, int &entry_m,
                          int &exit_h,  int &exit_m,
                          int &eod_h) {
   int off  = GetETOffsetHours();
   entry_h  = 9  + off; entry_m  = 31;
   exit_h   = 15 + off; exit_m   = 58;
   eod_h    = 16 + off;
}

//+------------------------------------------------------------------+
//| Init                                                             |
//+------------------------------------------------------------------+
int OnInit() {
   g_symbols[0] = Symbol_1; g_symbols[1] = Symbol_2;
   g_symbols[2] = Symbol_3; g_symbols[3] = Symbol_4;
   for(int i = 0; i < 4; i++) {
      if(!SymbolSelect(g_symbols[i], true)) {
         Print("ERROR: cannot select ", g_symbols[i]);
         return INIT_FAILED;
      }
      g_entries[i].active = false;
   }
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(20);
   EventSetTimer(20);

   // Persist challenge start balance (first run only)
   if(!GlobalVariableCheck(GV_START_BAL) || GlobalVariableGet(GV_START_BAL) <= 0) {
      double start = AccountInfoDouble(ACCOUNT_BALANCE);
      GlobalVariableSet(GV_START_BAL, start);
      PrintFormat("Challenge start balance set: %.2f (persisted in GlobalVariable)", start);
   } else {
      PrintFormat("Challenge start balance loaded: %.2f", GlobalVariableGet(GV_START_BAL));
   }

   int eh, em, xh, xm, eod; GetSessionBoundsUTC(eh, em, xh, xm, eod);
   int off = GetETOffsetHours();
   PrintFormat("Voie B EA v1.21 init. ET offset=%dh (UTC-%d, %s)",
               off, off, off == 4 ? "EDT" : "EST");
   PrintFormat("Entry %02d:%02d UTC | Exit %02d:%02d UTC | EOD close %02d:00 UTC",
               eh, em, xh, xm, eod);
   OpenDecisionLog();

   // Orphan recovery: any position open under our MagicNumber on fresh init
   // means the EA (or MT5) crashed while a levered trade was running without
   // an active kill-switch. Close immediately to bound max-loss exposure.
   int orphans = 0;
   for(int i = 0; i < PositionsTotal(); i++) {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && (int)PositionGetInteger(POSITION_MAGIC) == MagicNumber) orphans++;
   }
   if(orphans > 0) {
      PrintFormat("ORPHAN RECOVERY: %d position(s) MagicNumber=%d found on restart — closing",
                  orphans, MagicNumber);
      CloseAllPositions("orphan-recovery");
      PrintFormat("ORPHAN RECOVERY: done — positions closed, kill-switch was inactive during downtime");
   }

   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   EventKillTimer();
   if(g_log_handle != INVALID_HANDLE) { FileClose(g_log_handle); g_log_handle = INVALID_HANDLE; }
}

//+------------------------------------------------------------------+
//| Utility                                                          |
//+------------------------------------------------------------------+
MqlDateTime UtcNow() {
   MqlDateTime dt; TimeToStruct(TimeGMT(), dt);
   return dt;
}

bool IsSkippedDate(MqlDateTime &dt) {
   string today = StringFormat("%04d-%02d-%02d", dt.year, dt.mon, dt.day);
   return (StringFind(SkipDates, today) >= 0);
}

//+------------------------------------------------------------------+
//| Bug3 fix: get prev-day close at DST-aware close hour UTC        |
//+------------------------------------------------------------------+
double GetPrevCloseEOD(string sym) {
   int off = GetETOffsetHours();
   int close_hour_utc = 16 + off;   // 16:00 ET → 20:00 UTC EDT | 21:00 UTC EST

   datetime now = TimeGMT();
   MqlDateTime dt; TimeToStruct(now, dt);
   dt.hour = close_hour_utc; dt.min = 0; dt.sec = 0;
   datetime target = StructToTime(dt);
   if(target >= now) target -= 86400;
   MqlDateTime dt2; TimeToStruct(target, dt2);
   while(dt2.day_of_week == 0 || dt2.day_of_week == 6) {
      target -= 86400; TimeToStruct(target, dt2);
   }
   MqlRates rates[];
   int copied = CopyRates(sym, PERIOD_M1, target, 1, rates);
   if(copied >= 1) return rates[0].close;
   copied = CopyRates(sym, PERIOD_M5, target, 1, rates);
   if(copied >= 1) return rates[0].close;
   PrintFormat("WARN: cannot get prev EOD close for %s at %s", sym, TimeToString(target));
   return 0;
}

//+------------------------------------------------------------------+
//| Bug4 fix: vol-target leverage from US500 rolling 60d vol proxy   |
//| Aligns with Python: lever = TARGET_VOL / ann_vol, clip [0, max] |
//+------------------------------------------------------------------+
double ComputeVolTargetLeverage() {
   MqlRates daily[];
   int n = CopyRates(Symbol_1, PERIOD_D1, 1, VolLookbackDays, daily);
   if(n < 20) {
      PrintFormat("WARN: vol estimate only %d bars, using BaseLeverage=%.2f", n, BaseLeverage);
      return BaseLeverage;
   }
   double rets[];
   ArrayResize(rets, n - 1);
   int cnt = 0;
   for(int i = 0; i < n - 1; i++) {
      if(daily[i].close > 0 && daily[i + 1].close > 0)
         rets[cnt++] = MathLog(daily[i + 1].close / daily[i].close);
   }
   if(cnt < 10) return BaseLeverage;
   double mean = 0;
   for(int i = 0; i < cnt; i++) mean += rets[i];
   mean /= cnt;
   double var = 0;
   for(int i = 0; i < cnt; i++) var += (rets[i] - mean) * (rets[i] - mean);
   var /= MathMax(cnt - 1, 1);
   double ann_vol = MathSqrt(var) * MathSqrt(252.0);
   if(ann_vol < 0.01) return BaseLeverage;
   return MathMax(MathMin(VolTargetAnnual / ann_vol, MaxLeverage), 0.0);
}

//+------------------------------------------------------------------+
//| Bug2 fix: ratchet using persistent challenge_start_balance       |
//| Only used when UseVolTarget=false                                |
//+------------------------------------------------------------------+
double EffectiveLeverageRatchet(double cur_equity) {
   double start_bal = GlobalVariableGet(GV_START_BAL);
   if(start_bal <= 0) start_bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double pct = cur_equity / start_bal - 1.0;   // NOT ACCOUNT_BALANCE (croît avec profits)
   double lev = BaseLeverage + Ratchet * pct;
   return MathMax(MathMin(lev, MaxLeverage), 0.0);
}

//+------------------------------------------------------------------+
//| Cross-instrument confirmation                                    |
//+------------------------------------------------------------------+
int DetermineDirection(double &gaps[]) {
   int n_up = 0, n_dn = 0;
   double thr = GapThresholdBps / 10000.0;
   for(int i = 0; i < 4; i++) {
      double cur  = SymbolInfoDouble(g_symbols[i], SYMBOL_BID);
      double prev = g_prev_close[i];
      if(prev <= 0 || cur <= 0) { gaps[i] = 0; continue; }
      gaps[i] = (cur - prev) / prev;
      if(gaps[i] >  thr) n_up++;
      if(gaps[i] < -thr) n_dn++;
   }
   if(n_up >= MinConfirmation) return +1;
   if(n_dn >= MinConfirmation) return -1;
   return 0;
}

//+------------------------------------------------------------------+
//| Position sizing                                                  |
//+------------------------------------------------------------------+
double LotsForSymbol(string sym, double notional) {
   double price    = SymbolInfoDouble(sym, SYMBOL_BID);
   double contract = SymbolInfoDouble(sym, SYMBOL_TRADE_CONTRACT_SIZE);
   double nperlot  = price * contract;
   if(nperlot <= 0) return 0;
   double lot  = notional / nperlot;
   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   double mn   = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double mx   = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   lot = MathFloor(lot / step) * step;
   return NormalizeDouble(MathMax(MathMin(lot, mx), mn), 2);
}

//+------------------------------------------------------------------+
//| Close all EA positions — captures exit prices for slip logging   |
//+------------------------------------------------------------------+
void CloseAllPositions(string exit_reason) {
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      string pos_sym = PositionGetString(POSITION_SYMBOL);

      // Capture mid before close (slip_exit computed from this in Python)
      double bid_x = SymbolInfoDouble(pos_sym, SYMBOL_BID);
      double ask_x = SymbolInfoDouble(pos_sym, SYMBOL_ASK);
      double mid_x = (bid_x + ask_x) / 2.0;

      if(!trade.PositionClose(ticket)) {
         PrintFormat("ERROR closing #%I64u: %s", ticket, trade.ResultRetcodeDescription());
         continue;
      }

      double fill_x  = trade.ResultPrice();
      datetime now_x = TimeGMT();
      MqlDateTime dtx; TimeToStruct(now_x, dtx);
      string ts_x = StringFormat("%04d-%02d-%02d %02d:%02d:%02d",
                                  dtx.year, dtx.mon, dtx.day,
                                  dtx.hour, dtx.min, dtx.sec);

      if(VerboseLog)
         PrintFormat("Closed #%I64u %s (%s) fill=%.4f mid=%.4f",
                     ticket, pos_sym, exit_reason, fill_x, mid_x);

      // Match staged entry by symbol and write complete trade row
      for(int j = 0; j < 4; j++) {
         if(!g_entries[j].active || g_entries[j].sym != pos_sym) continue;
         double pnl_pts = (double)g_entries[j].dir * (fill_x - g_entries[j].fill_entry);
         double tick_sz  = SymbolInfoDouble(pos_sym, SYMBOL_TRADE_TICK_SIZE);
         double tick_val = SymbolInfoDouble(pos_sym, SYMBOL_TRADE_TICK_VALUE);
         double pnl_pct  = 0.0;
         if(tick_sz > 0 && g_equity_at_entry > 0) {
            double pnl_usd = (fill_x - g_entries[j].fill_entry) * (double)g_entries[j].dir
                             / tick_sz * tick_val * g_entries[j].lots;
            pnl_pct = pnl_usd / g_equity_at_entry;
         }
         WriteTradeLog(g_entries[j], mid_x, fill_x, ts_x, exit_reason, pnl_pts, pnl_pct);
         g_entries[j].active = false;
         break;
      }
   }
}

//+------------------------------------------------------------------+
//| Main timer                                                       |
//+------------------------------------------------------------------+
void OnTimer() {
   MqlDateTime dt = UtcNow();
   if(dt.day_of_week == 0 || dt.day_of_week == 6) return;  // skip weekends
   if(IsSkippedDate(dt)) return;

   int eh, em, xh, xm, eod_h;
   GetSessionBoundsUTC(eh, em, xh, xm, eod_h);

   // ---- 1. Pre-fetch prev_close one window before entry ----
   if(dt.hour == eh && dt.min < em && !g_entered_today) {
      for(int i = 0; i < 4; i++) {
         g_prev_close[i] = GetPrevCloseEOD(g_symbols[i]);
         if(VerboseLog)
            PrintFormat("%s prev_close(DST-aware) = %.4f", g_symbols[i], g_prev_close[i]);
      }
   }

   // ---- 2. Entry window ----
   datetime today_midnight = TimeGMT() - dt.hour * 3600 - dt.min * 60 - dt.sec;
   bool already_traded = (g_last_entry_day == today_midnight);

   if(!already_traded && !g_entered_today
      && dt.hour == eh && dt.min >= em) {

      double gaps[]; ArrayResize(gaps, 4);
      int dir = DetermineDirection(gaps);

      if(dir != 0) {
         double equity = AccountInfoDouble(ACCOUNT_EQUITY);
         double lev;
         if(UseVolTarget)
            lev = ComputeVolTargetLeverage();
         else
            lev = EffectiveLeverageRatchet(equity);

         double total_notional = equity * lev;
         double per_symbol     = total_notional / 4.0;
         double thr            = GapThresholdBps / 10000.0;
         double lots_arr[4];  ArrayInitialize(lots_arr, 0);
         int orders = 0;

         for(int i = 0; i < 4; i++) {
            bool align = (dir == 1 && gaps[i] > thr) || (dir == -1 && gaps[i] < -thr);
            if(!align) continue;
            lots_arr[i] = LotsForSymbol(g_symbols[i], per_symbol);
            if(lots_arr[i] <= 0) continue;

            // Capture pre-trade mid/spread — raw prices only, slip computed in Python
            double bid_s = SymbolInfoDouble(g_symbols[i], SYMBOL_BID);
            double ask_s = SymbolInfoDouble(g_symbols[i], SYMBOL_ASK);
            double mid_s = (bid_s + ask_s) / 2.0;
            double spr_s = (mid_s > 0) ? (ask_s - bid_s) / mid_s * 1e4 : 0.0;

            bool ok = (dir == 1) ? trade.Buy(lots_arr[i], g_symbols[i])
                                 : trade.Sell(lots_arr[i], g_symbols[i]);
            if(ok) {
               double   fill_e  = trade.ResultPrice();
               datetime fill_ts = TimeGMT();
               MqlDateTime fill_dt; TimeToStruct(fill_ts, fill_dt);
               string ts_e   = StringFormat("%04d-%02d-%02d %02d:%02d:%02d",
                                            fill_dt.year, fill_dt.mon, fill_dt.day,
                                            fill_dt.hour, fill_dt.min, fill_dt.sec);
               string date_e = StringFormat("%04d-%02d-%02d",
                                            fill_dt.year, fill_dt.mon, fill_dt.day);
               orders++;
               g_entries[i].date_utc   = date_e;
               g_entries[i].sym        = g_symbols[i];
               g_entries[i].dir        = dir;
               g_entries[i].gap_bps    = gaps[i] * 1e4;
               g_entries[i].lev        = lev;
               g_entries[i].lots       = lots_arr[i];
               g_entries[i].mid_signal = mid_s;
               g_entries[i].fill_entry = fill_e;
               g_entries[i].spread_bps = spr_s;
               g_entries[i].ts_entry   = ts_e;
               g_entries[i].active     = true;

               PrintFormat("ENTRY %s %s %.2f lots (gap=%.1fbp lev=%.2fx fill=%.4f spr=%.1fbp) [%s]",
                           dir == 1 ? "LONG" : "SHORT", g_symbols[i], lots_arr[i],
                           gaps[i] * 10000, lev, fill_e, spr_s,
                           UseVolTarget ? "vol-tgt" : "ratchet");
            } else
               PrintFormat("ERROR entry %s: %s", g_symbols[i], trade.ResultRetcodeDescription());
         }

         if(orders > 0) {
            g_entered_today          = true;
            g_last_entry_day         = today_midnight;
            g_equity_at_entry        = equity;
            g_levered_kill_threshold = equity * (1.0 + KillSwitchUnlev * lev);
         }
      } else {
         if(VerboseLog)
            PrintFormat("No signal. Gaps[bp]: %.1f %.1f %.1f %.1f",
                        gaps[0]*1e4, gaps[1]*1e4, gaps[2]*1e4, gaps[3]*1e4);
      }
   }

   // ---- 3. Kill-switch ----
   if(g_entered_today && g_levered_kill_threshold > 0) {
      double eq = AccountInfoDouble(ACCOUNT_EQUITY);
      if(eq <= g_levered_kill_threshold) {
         PrintFormat("KILL-SWITCH: equity %.2f <= threshold %.2f",
                     eq, g_levered_kill_threshold);
         CloseAllPositions("killswitch");
         g_entered_today = false;
      }
   }

   // ---- 4. Scheduled exit ----
   // Guard: any hour AFTER exit hour also closes — not just the exact minute.
   // Handles late-restart scenario: MT5 down during xh:xm, restarts at xh+1:xx.
   if(g_entered_today && (dt.hour > xh || (dt.hour == xh && dt.min >= xm))) {
      CloseAllPositions("scheduled");
      g_entered_today = false;
   }

   // ---- 5. Forced EOD close + daily state reset at 23:00 UTC ----
   // 23 UTC covers EDT close (20:00) and EST close (21:00) with buffer.
   // NEVER reset state while a position is still open.
   if(dt.hour >= 23) {
      int lingering = 0;
      for(int i = 0; i < PositionsTotal(); i++) {
         ulong ticket = PositionGetTicket(i);
         if(ticket > 0 && (int)PositionGetInteger(POSITION_MAGIC) == MagicNumber) {
            lingering++; break;
         }
      }
      if(lingering > 0) {
         PrintFormat("FORCED-EOD: %d position(s) still open at %02d:%02d UTC — closing",
                     lingering, dt.hour, dt.min);
         CloseAllPositions("forced-eod");
      }
      g_entered_today = false;
   }
}

void OnTick() {}
