//+------------------------------------------------------------------+
//| Voie_B_EA.mq5                                                    |
//| Intraday gap-continuation on US indices, FTMO 14:30-21:00 UTC    |
//| Causal: signal observed at US Open, exit at US Close.            |
//| Author: Quant research notes - May 2026                          |
//+------------------------------------------------------------------+
#property copyright "Voie B - Quant Research"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
CTrade trade;

//--- inputs --------------------------------------------------------
input group           "=== Universe & Signal ==="
input string          Symbol_1            = "US500.cash";
input string          Symbol_2            = "US100.cash";
input string          Symbol_3            = "US30.cash";
input string          Symbol_4            = "US2000.cash";
input double          GapThresholdBps     = 15.0;     // 15 bp threshold
input int             MinConfirmation     = 2;        // need >=2/4 same dir

input group           "=== Sizing ==="
input double          BaseLeverage        = 2.5;      // 2-step config (1.6 for 1-step)
input double          MaxLeverage         = 3.75;     // cap = 0.045/stop for 2-step
input double          Ratchet             = 25.0;     // cushion-ratchet coefficient
input double          VolTargetAnnual     = 0.10;     // 10% portfolio vol target
input double          KillSwitchUnlev     = -0.012;   // -1.2% unlevered intraday stop

input group           "=== Timing (UTC) ==="
input int             EntryHourUTC        = 14;
input int             EntryMinuteUTC      = 31;       // 1 min after US Open to let auction settle
input int             ExitHourUTC         = 20;
input int             ExitMinuteUTC       = 58;       // 2 min before Close

input group           "=== Risk filters ==="
input bool            SkipFOMC            = true;     // skip FOMC days (manual flag below)
input string          SkipDates           = "";       // comma sep YYYY-MM-DD to skip (FOMC, NFP days)

input group           "=== Logging ==="
input int             MagicNumber         = 20260601;
input bool            VerboseLog          = true;

//--- global state --------------------------------------------------
string   g_symbols[4];
double   g_prev_close[4];    // close at 21:00 UTC previous day
bool     g_entered_today = false;
datetime g_last_entry_day = 0;
double   g_equity_at_entry = 0;
double   g_levered_kill_threshold = 0; // computed at entry

//+------------------------------------------------------------------+
//| Init                                                             |
//+------------------------------------------------------------------+
int OnInit() {
   g_symbols[0] = Symbol_1; g_symbols[1] = Symbol_2;
   g_symbols[2] = Symbol_3; g_symbols[3] = Symbol_4;
   // ensure all symbols are available
   for(int i=0; i<4; i++) {
      if(!SymbolSelect(g_symbols[i], true)) {
         Print("ERROR: cannot select symbol ", g_symbols[i]);
         return INIT_FAILED;
      }
   }
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(20);
   EventSetTimer(20);   // check every 20 seconds
   Print("Voie B EA initialised. Universe = ", Symbol_1, ",", Symbol_2, ",", Symbol_3, ",", Symbol_4);
   Print("Entry ", EntryHourUTC, ":", EntryMinuteUTC, " UTC | Exit ", ExitHourUTC, ":", ExitMinuteUTC, " UTC");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { EventKillTimer(); }

//+------------------------------------------------------------------+
//| Get current UTC time                                             |
//+------------------------------------------------------------------+
MqlDateTime UtcNow() {
   datetime t = TimeGMT();
   MqlDateTime dt; TimeToStruct(t, dt);
   return dt;
}

//+------------------------------------------------------------------+
//| Is this UTC date skipped (FOMC/NFP)?                             |
//+------------------------------------------------------------------+
bool IsSkippedDate(MqlDateTime &dt) {
   string today = StringFormat("%04d-%02d-%02d", dt.year, dt.mon, dt.day);
   if(StringFind(SkipDates, today) >= 0) return true;
   return false;
}

//+------------------------------------------------------------------+
//| Compute previous-day Close at 21:00 UTC for a symbol             |
//| Strategy: scan M1 bars to find the one timestamped 21:00 UTC     |
//| of the most recent trading day before today.                     |
//+------------------------------------------------------------------+
double GetPrevCloseAt21UTC(string sym) {
   datetime now = TimeGMT();
   MqlDateTime dt; TimeToStruct(now, dt);
   // build "today 00:00 UTC" then walk back to find yesterday's 21:00
   dt.hour = 21; dt.min = 0; dt.sec = 0;
   datetime target = StructToTime(dt);
   if(target >= now) target -= 86400;  // yesterday
   // skip weekends
   MqlDateTime dt2; TimeToStruct(target, dt2);
   while(dt2.day_of_week == 0 || dt2.day_of_week == 6) {
      target -= 86400; TimeToStruct(target, dt2);
   }
   // get M1 bar close at target
   MqlRates rates[];
   int copied = CopyRates(sym, PERIOD_M1, target, 1, rates);
   if(copied < 1) {
      // fallback: nearest M5 or H1
      copied = CopyRates(sym, PERIOD_M5, target, 1, rates);
      if(copied < 1) return 0;
   }
   return rates[0].close;
}

//+------------------------------------------------------------------+
//| Determine direction from cross-instrument confirmation           |
//| Returns: +1 long, -1 short, 0 none. Fills gaps[] with per-symbol |
//+------------------------------------------------------------------+
int DetermineDirection(double &gaps[]) {
   int n_up = 0, n_dn = 0;
   double thr = GapThresholdBps / 10000.0;
   for(int i=0; i<4; i++) {
      double cur = SymbolInfoDouble(g_symbols[i], SYMBOL_BID);
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
//| Compute levered position size (lots) per symbol                  |
//+------------------------------------------------------------------+
double LotsForSymbol(string sym, double per_symbol_notional) {
   double price    = SymbolInfoDouble(sym, SYMBOL_BID);
   double contract = SymbolInfoDouble(sym, SYMBOL_TRADE_CONTRACT_SIZE);
   double notional_per_lot = price * contract;
   if(notional_per_lot <= 0) return 0;
   double lot = per_symbol_notional / notional_per_lot;
   double min_lot = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double step    = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   double max_lot = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   lot = MathMax(MathMin(lot, max_lot), min_lot);
   lot = MathFloor(lot/step) * step;
   return NormalizeDouble(lot, 2);
}

//+------------------------------------------------------------------+
//| Cushion-ratchet leverage as a function of current equity         |
//+------------------------------------------------------------------+
double EffectiveLeverage(double equity_pct_gain) {
   double lev = BaseLeverage + Ratchet * equity_pct_gain;
   return MathMax(MathMin(lev, MaxLeverage), 0.0);
}

//+------------------------------------------------------------------+
//| Close all positions owned by this EA                             |
//+------------------------------------------------------------------+
void CloseAllPositions(string reason) {
   for(int i = PositionsTotal()-1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      if(!trade.PositionClose(ticket))
         Print("ERROR closing #", ticket, " : ", trade.ResultRetcodeDescription());
      else if(VerboseLog) Print("Closed #", ticket, " (", reason, ")");
   }
}

//+------------------------------------------------------------------+
//| Main timer event (every 20s)                                     |
//+------------------------------------------------------------------+
void OnTimer() {
   MqlDateTime dt = UtcNow();

   // ---- 1. Pre-entry: at EntryHour-1, fetch previous Close at 21:00 ----
   if(dt.hour == EntryHourUTC && dt.min <= EntryMinuteUTC-1 && !g_entered_today) {
      for(int i=0; i<4; i++) {
         g_prev_close[i] = GetPrevCloseAt21UTC(g_symbols[i]);
         if(VerboseLog) PrintFormat("%s prev_close_21UTC = %.2f", g_symbols[i], g_prev_close[i]);
      }
   }

   // ---- 2. Entry window: at EntryHour:EntryMinute UTC ----
   datetime today_midnight = StructToTime(dt);
   today_midnight = today_midnight - dt.hour*3600 - dt.min*60 - dt.sec;
   if(g_last_entry_day == today_midnight) ; // already traded today, fall through to monitoring
   else if(dt.hour == EntryHourUTC && dt.min >= EntryMinuteUTC
           && !g_entered_today
           && dt.day_of_week >= 1 && dt.day_of_week <= 5
           && !IsSkippedDate(dt)) {
      double gaps[]; ArrayResize(gaps, 4);
      int dir = DetermineDirection(gaps);
      if(dir != 0) {
         double equity = AccountInfoDouble(ACCOUNT_EQUITY);
         // cushion-ratchet: equity gain from baseline (assume start at challenge entry)
         double pct = equity/AccountInfoDouble(ACCOUNT_BALANCE) - 1.0;
         double lev = EffectiveLeverage(pct);
         double total_notional = equity * lev;
         double per_symbol = total_notional / 4.0;
         double thr = GapThresholdBps/10000.0;
         int orders = 0;
         for(int i=0; i<4; i++) {
            bool align = (dir==1 && gaps[i] > thr) || (dir==-1 && gaps[i] < -thr);
            if(!align) continue;
            double lots = LotsForSymbol(g_symbols[i], per_symbol);
            if(lots <= 0) continue;
            bool ok = (dir==1) ? trade.Buy(lots, g_symbols[i]) : trade.Sell(lots, g_symbols[i]);
            if(ok) { orders++;
               PrintFormat("ENTRY %s %s %.2f lots (gap=%.1f bp lev=%.2fx)",
                            (dir==1?"LONG":"SHORT"), g_symbols[i], lots, gaps[i]*10000, lev);
            } else Print("ERROR entry ", g_symbols[i], " : ", trade.ResultRetcodeDescription());
         }
         if(orders > 0) {
            g_entered_today = true;
            g_last_entry_day = today_midnight;
            g_equity_at_entry = equity;
            // kill switch threshold = -1.2% * leverage (since equity moves at lev x daily return)
            g_levered_kill_threshold = equity * (1.0 + KillSwitchUnlev * lev);
         }
      } else if(VerboseLog) Print("No signal: confirms insufficient. Gaps in bp: ",
                                  gaps[0]*10000," ",gaps[1]*10000," ",gaps[2]*10000," ",gaps[3]*10000);
   }

   // ---- 3. Kill-switch monitoring (intraday) ----
   if(g_entered_today && g_levered_kill_threshold > 0) {
      double eq = AccountInfoDouble(ACCOUNT_EQUITY);
      if(eq <= g_levered_kill_threshold) {
         Print("KILL-SWITCH triggered: equity=", DoubleToString(eq,2),
               " <= threshold=", DoubleToString(g_levered_kill_threshold,2));
         CloseAllPositions("kill-switch");
         g_entered_today = false;
      }
   }

   // ---- 4. Scheduled exit at ExitHour:ExitMinute UTC ----
   if(g_entered_today && dt.hour == ExitHourUTC && dt.min >= ExitMinuteUTC) {
      CloseAllPositions("scheduled-exit");
      g_entered_today = false;
   }

   // ---- 5. Daily reset (after 23:00 UTC) ----
   if(dt.hour == 23) g_entered_today = false;
}

//+------------------------------------------------------------------+
//| OnTick (unused — we drive via OnTimer)                           |
//+------------------------------------------------------------------+
void OnTick() {}
