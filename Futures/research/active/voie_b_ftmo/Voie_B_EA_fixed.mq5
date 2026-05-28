//+------------------------------------------------------------------+
//| Voie_B_EA_fixed.mq5                                             |
//| Intraday gap-continuation on US indices, FTMO 2-step            |
//| FIXES vs v1.00:                                                  |
//|   Bug1: DST-aware UTC session times (EDT/EST automatic)          |
//|   Bug2: challenge_start_balance via GlobalVariable               |
//|   Bug3: prev_close lookup uses DST-aware close hour              |
//|   Bug4: vol-targeting aligned with Python backtest               |
//+------------------------------------------------------------------+
#property copyright "Voie B - Quant Research"
#property version   "1.10"
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

// GlobalVariable key for persistent challenge start balance
#define GV_START_BAL "VoieB_StartBalance"

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
   eod_h    = 16 + off;  // close at 16:00 ET, used for prev_close lookup
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
   PrintFormat("Voie B EA v1.10 init. ET offset=%dh (UTC-%d, %s)",
               off, off, off == 4 ? "EDT" : "EST");
   PrintFormat("Entry %02d:%02d UTC | Exit %02d:%02d UTC | EOD close %02d:00 UTC",
               eh, em, xh, xm, eod);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { EventKillTimer(); }

//+------------------------------------------------------------------+
//| Current UTC time struct                                          |
//+------------------------------------------------------------------+
MqlDateTime UtcNow() {
   MqlDateTime dt; TimeToStruct(TimeGMT(), dt);
   return dt;
}

//+------------------------------------------------------------------+
//| Skip FOMC/NFP days                                               |
//+------------------------------------------------------------------+
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
   // build yesterday's close timestamp
   dt.hour = close_hour_utc; dt.min = 0; dt.sec = 0;
   datetime target = StructToTime(dt);
   if(target >= now) target -= 86400;
   // skip weekends
   MqlDateTime dt2; TimeToStruct(target, dt2);
   while(dt2.day_of_week == 0 || dt2.day_of_week == 6) {
      target -= 86400; TimeToStruct(target, dt2);
   }
   // fetch M1 bar at target
   MqlRates rates[];
   int copied = CopyRates(sym, PERIOD_M1, target, 1, rates);
   if(copied >= 1) return rates[0].close;
   // fallback M5
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
   // skip bar[0] (incomplete today), take VolLookbackDays closed bars
   int n = CopyRates(Symbol_1, PERIOD_D1, 1, VolLookbackDays, daily);
   if(n < 20) {
      PrintFormat("WARN: vol estimate only %d bars, using BaseLeverage=%.2f", n, BaseLeverage);
      return BaseLeverage;
   }
   // daily log-returns (close-to-close)
   double rets[];
   ArrayResize(rets, n - 1);
   int cnt = 0;
   for(int i = 0; i < n - 1; i++) {
      if(daily[i].close > 0 && daily[i + 1].close > 0) {
         rets[cnt++] = MathLog(daily[i + 1].close / daily[i].close);
      }
   }
   if(cnt < 10) return BaseLeverage;
   // compute std
   double mean = 0;
   for(int i = 0; i < cnt; i++) mean += rets[i];
   mean /= cnt;
   double var = 0;
   for(int i = 0; i < cnt; i++) var += (rets[i] - mean) * (rets[i] - mean);
   var /= MathMax(cnt - 1, 1);
   double daily_std = MathSqrt(var);
   double ann_vol   = daily_std * MathSqrt(252.0);
   if(ann_vol < 0.01) return BaseLeverage;
   double lev = VolTargetAnnual / ann_vol;
   return MathMax(MathMin(lev, MaxLeverage), 0.0);
}

//+------------------------------------------------------------------+
//| Bug2 fix: ratchet using persistent challenge_start_balance       |
//| Only used when UseVolTarget=false                                |
//+------------------------------------------------------------------+
double EffectiveLeverageRatchet(double cur_equity) {
   double start_bal = GlobalVariableGet(GV_START_BAL);
   if(start_bal <= 0) start_bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double pct = cur_equity / start_bal - 1.0;   // gain from challenge start, not from rolling balance
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
//| Close all EA positions                                           |
//+------------------------------------------------------------------+
void CloseAllPositions(string reason) {
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      if(!trade.PositionClose(ticket))
         PrintFormat("ERROR closing #%I64u: %s", ticket, trade.ResultRetcodeDescription());
      else if(VerboseLog)
         PrintFormat("Closed #%I64u (%s)", ticket, reason);
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

         // Bug4 fix: vol-target OR ratchet (legacy), not both
         double lev;
         if(UseVolTarget)
            lev = ComputeVolTargetLeverage();
         else
            lev = EffectiveLeverageRatchet(equity);   // Bug2 fix inside

         double total_notional = equity * lev;
         double per_symbol     = total_notional / 4.0;
         double thr            = GapThresholdBps / 10000.0;
         int orders = 0;

         for(int i = 0; i < 4; i++) {
            bool align = (dir == 1 && gaps[i] > thr) || (dir == -1 && gaps[i] < -thr);
            if(!align) continue;
            double lots = LotsForSymbol(g_symbols[i], per_symbol);
            if(lots <= 0) continue;
            bool ok = (dir == 1) ? trade.Buy(lots, g_symbols[i])
                                 : trade.Sell(lots, g_symbols[i]);
            if(ok) {
               orders++;
               PrintFormat("ENTRY %s %s %.2f lots (gap=%.1fbp lev=%.2fx) [%s]",
                           dir == 1 ? "LONG" : "SHORT", g_symbols[i], lots,
                           gaps[i] * 10000, lev,
                           UseVolTarget ? "vol-tgt" : "ratchet");
            } else
               PrintFormat("ERROR entry %s: %s", g_symbols[i], trade.ResultRetcodeDescription());
         }
         if(orders > 0) {
            g_entered_today       = true;
            g_last_entry_day      = today_midnight;
            g_equity_at_entry     = equity;
            g_levered_kill_threshold = equity * (1.0 + KillSwitchUnlev * lev);
         }
      } else if(VerboseLog)
         PrintFormat("No signal. Gaps[bp]: %.1f %.1f %.1f %.1f",
                     gaps[0]*1e4, gaps[1]*1e4, gaps[2]*1e4, gaps[3]*1e4);
   }

   // ---- 3. Kill-switch ----
   if(g_entered_today && g_levered_kill_threshold > 0) {
      double eq = AccountInfoDouble(ACCOUNT_EQUITY);
      if(eq <= g_levered_kill_threshold) {
         PrintFormat("KILL-SWITCH: equity %.2f <= threshold %.2f",
                     eq, g_levered_kill_threshold);
         CloseAllPositions("kill-switch");
         g_entered_today = false;
      }
   }

   // ---- 4. Scheduled exit ----
   if(g_entered_today && dt.hour == xh && dt.min >= xm) {
      CloseAllPositions("scheduled-exit");
      g_entered_today = false;
   }

   // ---- 5. Daily reset after market close ----
   if(dt.hour >= eod_h + 1) g_entered_today = false;
}

void OnTick() {}
