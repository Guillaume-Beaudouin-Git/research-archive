//+------------------------------------------------------------------+
//| book_executor.mq5 — EA exécuteur du book CHALLENGE v2.2 (FTMO)    |
//|                                                                    |
//| ZÉRO logique de signal : les poids viennent de Files/targets.json  |
//| (brain.py 21:50 Paris). ZÉRO constante manuelle : tout #define     |
//| vient de spec_v22.mqh GÉNÉRÉ (pin sha 1d834546…, ancre #20) ;      |
//| OnInit refuse de trader sans Files/spec_v22.sha256 == SPEC_SHA256. |
//|                                                                    |
//| Horaires : spec en CE(S)T (= Paris/Prague) ; serveur FTMO EET =    |
//| CET+1 constant toute l'année (README_BUILD) — mapping via          |
//| InpServerTZOffsetMin, jamais en éditant les constantes.            |
//|                                                                    |
//| Fills ASYNCHRONES (serveur mesuré 2-19 s, pattern slippage_probe2  |
//| v1.11) : jamais trade.Result*() ; entrée = POSITION_PRICE_OPEN     |
//| (delta de volume signé), sortie = scan d'historique (magic +       |
//| symbol + DEAL_ENTRY_OUT) avec retries. Aucune logique ne suppose   |
//| un fill synchrone ; les stops dormants n'ont pas de timeout.       |
//|                                                                    |
//| Politique = miroir 1:1 de ftmo_live/lib/invariants.py (validé vs   |
//| l'oracle sim E._target_for_segment par ftmo_live/tests/) :         |
//|  - rebalance 22:05 CET depuis targets.json (quantize 0.01 ;        |
//|    stale > 26 h = AUCUN risque nouveau, gestion seule + alerte)    |
//|  - jambes ON (lun+mar) : GER40 17:35, US100 22:05, on_w x scale    |
//|  - micro-ORB day-counter (bloc yaml TEL QUEL) : 0.01 lot           |
//|    US100.cash, OR 15:30-16:00 CET, stops dormants OCO aux niveaux  |
//|    (entrée canonique premier bar post-OR, fills 16:05-16:10),      |
//|    sorties V2+E7 (stop côté opposé 1R, trail-to-BE à +1R,          |
//|    time-stop 22:00), posé seulement si rien d'ouvert à 21:30       |
//|    (flag opened, sémantique 605f4a4 : jamais armé un jour ON) ;    |
//|    backstop token = fallback rare du yaml, séparé                  |
//|  - invariants M5 : daily floor = balance@00:00 CE(S)T − 5% init ;  |
//|    floor statique + taper 2% ; flatten si room < 30% du budget ;   |
//|    cap marge 60% (scaling proportionnel TOUTES jambes, sim) ;      |
//|    caps lots sanity (dérivés mqh) ; target-lock intraday           |
//|  - kill-file FLAT = flatten + disable (heartbeat continue)         |
//|  - switch funded (bloc yaml, même événement que vm14→1.0) :        |
//|    vm 1.0, on_w 0.35, ORB ON 0.25% taper, micro OFF, pace/glide/   |
//|    abandon OFF, compteur retraits wd14 (alerte supervisor)         |
//| Écrit state.json (heartbeat M1), fills.csv (req/fill par jambe),   |
//| swaps_billed.csv (nuitées), market_export.json (21:45, D1+specs),  |
//| m5_today.json + snapshot EOD (22:58) — audit trail intégral.       |
//+------------------------------------------------------------------+
#property strict
#property version "1.00"
#include "spec_v22.mqh"

// ---- inputs opérationnels (AUCUNE constante de spec ici) ----
input int      InpServerTZOffsetMin = 60;   // serveur(EET) − Paris, minutes (+1h)
input int      InpPhase             = 1;    // 1=P1 2=P2 3=FUNDED
input datetime InpAttemptStart      = 0;    // début tentative 00:00 (ancre pace) REQUIS P1/P2
input long     InpMagicBase         = 220500;
input string   InpSymXAU            = "XAUUSD";
input string   InpSymJPY            = "USDJPY";
input string   InpSymUS100          = "";   // vide = MICRO_ORB_SYMBOL du mqh
input string   InpSymGER40          = "GER40.cash";
input double   InpMicroMinWidthBps  = 10.0; // V2 canonique (FTMO_CANONICAL_STATE §1)
input int      InpFillTimeoutSec    = 60;   // confirm async ordres market (latence 2-19 s)
input double   InpSanityAbsPtsFloor = 2.0;  // plancher dénominateur borne swap (petites ancres)

#define N_LEGS 4
#define MAGIC_MICRO    10
#define MAGIC_BACKSTOP 11
#define MAGIC_FORB     12
#define PENDING_MAX    64

string  g_legs[N_LEGS] = {"XAUUSD","USDJPY","US100","GER40"};
string  g_sym[N_LEGS];
double  g_mrate[N_LEGS];
string  g_micro_sym;

// ---- état persistant (ea_state.json) ----
double  g_anchor_balance = 0.0;
string  g_anchor_date    = "";
bool    g_opened_today=false, g_flat_today=false, g_breaker_today=false;
int     g_open_days=0, g_zombie_days=0, g_wd_tdays=0;
int     g_micro_state=0;            // 0 IDLE 1 ARMED 2 OPEN 3 DONE 4 SKIPPED
double  g_or_hi=0, g_or_lo=0, g_or_end_close=0;
double  g_micro_entry=0;
bool    g_micro_be=false;
bool    g_backstop_close_due=false;
bool    g_done_0900=false, g_done_1530=false, g_done_or=false, g_done_1600=false,
        g_done_1735=false, g_done_2130=false, g_done_2145=false, g_done_2200=false,
        g_done_2205=false, g_done_2258=false;
bool    g_killed=false;
int     g_pending_unconfirmed=0;
string  g_last_error="";
string  g_targets_status="MISSING";
bool    g_mode_mismatch=false;
string  g_last_rebalance="";
long    g_last_m5_slot=0;
datetime g_last_state_write=0;

// ---- suivi fills asynchrones (slippage_probe2 v1.11) ----
struct Pending
  {
   long     id;
   string   symbol;
   int      side;                  // +1 buy −1 sell
   double   lots;
   double   req_px;
   long     magic;
   string   reason;
   datetime sent;
   double   vol_before;            // volume signé du magic avant l'ordre
   bool     is_close;              // sortie -> scan DEAL_ENTRY_OUT
   bool     is_resting;            // stop dormant -> pas de timeout
   bool     done;
  };
Pending g_pend[PENDING_MAX];
int     g_pend_n=0;
long    g_pend_seq=0;

double  g_swl_val[256];             // delta POSITION_SWAP par ticket (facturation)
long    g_swl_tk[256];
int     g_swl_n=0;

// ---- v2.2.1: specs LIVE vs bornes de sanité datées (mqh) ----
double  g_live_swl[N_LEGS], g_live_sws[N_LEGS], g_live_mrate[N_LEGS];
int     g_live_r3d[N_LEGS];
double  g_anc_swl[N_LEGS], g_anc_sws[N_LEGS];
int     g_anc_r3d[N_LEGS];
double  g_mrate_std[N_LEGS], g_mrate_swing[N_LEGS];
bool    g_spec_breach=false;
string  g_spec_breach_detail="";

//+------------------------------------------------------------------+
//| Temps                                                              |
//+------------------------------------------------------------------+
datetime ParisNow() { return (datetime)(TimeCurrent() - InpServerTZOffsetMin*60); }
void ParisStruct(MqlDateTime &p) { TimeToStruct(ParisNow(), p); }
string ParisDate()
  {
   MqlDateTime p; ParisStruct(p);
   return StringFormat("%04d-%02d-%02d", p.year, p.mon, p.day);
  }
int  ParisHM()  { MqlDateTime p; ParisStruct(p); return p.hour*100 + p.min; }
int  ParisDow() { MqlDateTime p; ParisStruct(p); return p.day_of_week; }  // 0=dim
bool IsONDay()  { int d=ParisDow(); return (d==1 || d==2); }              // lun, mar
bool IsWeekend(){ int d=ParisDow(); return (d==0 || d==6); }
string TsParis()
  {
   MqlDateTime p; ParisStruct(p);
   return StringFormat("%04d.%02d.%02d %02d:%02d:%02d",
                       p.year, p.mon, p.day, p.hour, p.min, p.sec);
  }
string TsServer() { return TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS); }
datetime ServerOfParisHM(int hm)
  {
   MqlDateTime p; ParisStruct(p);
   p.hour=hm/100; p.min=hm%100; p.sec=0;
   return (datetime)(StructToTime(p) + InpServerTZOffsetMin*60);
  }

//+------------------------------------------------------------------+
//| Spec / phase (tout vient du mqh généré)                            |
//+------------------------------------------------------------------+
double VmEff()
  {
   if(InpPhase==3) return FU_VM;
   if(InpPhase==2) return CH_VM*CH_P2_MULT;
   return CH_VM;
  }
double OnWEff()      { return (InpPhase==3) ? FU_ON_W : CH_ON_W; }
double PhaseTarget() { return (InpPhase==1) ? TARGET_P1 : (InpPhase==2 ? TARGET_P2 : 0.0); }
bool   MicroEnabled(){ return (InpPhase!=3) && CH_MICRO_ORB; }
bool   FundedOrbOn() { return (InpPhase==3) && (FU_ORB_RISK > 0.0); }
double TargetEq()    { return ACCOUNT_SIZE_USD*(1.0+PhaseTarget())*(1.0+2e-4); } // EPS_T engine
double StaticFloor() { return ACCOUNT_SIZE_USD*(1.0-MAX_LOSS_FRAC); }
double DailyBudget() { return ACCOUNT_SIZE_USD*DAILY_LOSS_FRAC; }
double DailyFloor()  { return g_anchor_balance - DailyBudget(); }
double LimEff()      { return MathMax(DailyFloor(), StaticFloor()); }
double BreakerLine() { return LimEff() + CH_BREAKER_FRAC*DailyBudget(); } // funded: 0.30 idem (yaml)

// gouverneur — miroir lib/invariants.py (oracle sim E._target_for_segment)
double GovTaper(double eq)
  {
   double room=(eq-StaticFloor())/ACCOUNT_SIZE_USD;
   return MathMax(0.0, MathMin(1.0, room/CH_TAPER));
  }
double Glide(double eq)
  {
   if(InpPhase==3) return 1.0;                          // yaml switch: glide OFF
   double prog=(eq/ACCOUNT_SIZE_USD-1.0)/PhaseTarget();
   return (prog>0.8) ? CH_GLIDE : 1.0;
  }
double Pace(double eq)
  {
   if(InpPhase==3 || CH_PACE_ON==0 || InpAttemptStart==0) return 1.0; // funded: OFF
   double frac_t=(double)((long)(ParisNow()-InpAttemptStart)/86400)/(double)WALL_DAYS;
   double prog=(eq/ACCOUNT_SIZE_USD-1.0)/PhaseTarget();
   double x=1.0+CH_PACE_K*(frac_t-MathMax(prog,0.0));
   return MathMax(0.8, MathMin(2.0, x));
  }
double Scale(double eq) { return VmEff()*GovTaper(eq)*Glide(eq)*Pace(eq); }
double OrbTaper0()
  {
   return MathMax(0.0, MathMin(1.0,
          (g_anchor_balance-StaticFloor())/ACCOUNT_SIZE_USD/CH_TAPER));
  }

//+------------------------------------------------------------------+
//| Symboles / conversions                                             |
//+------------------------------------------------------------------+
double UsdPerUnit(string sym)            // $ par unité de prix par lot (fx incl.)
  {
   double tv=SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double ts=SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   if(tv<=0 || ts<=0) return 0.0;
   return tv/ts;
  }
double UsdPerLot(string sym, double price) { return price*UsdPerUnit(sym); }
double MidPrice(string sym)
  {
   MqlTick t;
   if(!SymbolInfoTick(sym, t)) return 0.0;
   if(t.bid>0 && t.ask>0) return (t.bid+t.ask)/2.0;
   return t.last>0 ? t.last : t.bid;
  }
double SidePrice(string sym, int side)
  {
   MqlTick t;
   if(!SymbolInfoTick(sym, t)) return 0.0;
   return side>0 ? t.ask : t.bid;
  }

double SignedVolume(string sym, long magic)
  {
   double v=0;
   for(int i=PositionsTotal()-1; i>=0; i--)
     {
      ulong tk=PositionGetTicket(i);
      if(tk==0 || !PositionSelectByTicket(tk)) continue;
      if(PositionGetInteger(POSITION_MAGIC)!=magic) continue;
      if(PositionGetString(POSITION_SYMBOL)!=sym) continue;
      double lots=PositionGetDouble(POSITION_VOLUME);
      v += (PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY) ? lots : -lots;
     }
   return v;
  }
double LegLots(int k) { return SignedVolume(g_sym[k], InpMagicBase+k); }
double LegAvgPxByMagic(string sym, long magic)
  {
   double num=0, den=0;
   for(int i=PositionsTotal()-1; i>=0; i--)
     {
      ulong tk=PositionGetTicket(i);
      if(tk==0 || !PositionSelectByTicket(tk)) continue;
      if(PositionGetInteger(POSITION_MAGIC)!=magic) continue;
      if(PositionGetString(POSITION_SYMBOL)!=sym) continue;
      num += PositionGetDouble(POSITION_PRICE_OPEN)*PositionGetDouble(POSITION_VOLUME);
      den += PositionGetDouble(POSITION_VOLUME);
     }
   return den>0 ? num/den : 0.0;
  }
double LegAvgPx(int k) { return LegAvgPxByMagic(g_sym[k], InpMagicBase+k); }
// notionnel "sim" = marqué au prix d'ENTRÉE (pos[k] du moteur, jamais re-marké)
double LegNotionalAtAvg(int k)
  {
   double lots=LegLots(k);
   if(lots==0.0) return 0.0;
   double avg=LegAvgPx(k);
   if(avg<=0) return 0.0;
   return lots*UsdPerLot(g_sym[k], avg);
  }
double LegNotionalMid(int k)
  {
   double px=MidPrice(g_sym[k]);
   if(px<=0) return 0.0;
   return LegLots(k)*UsdPerLot(g_sym[k], px);
  }
double LegSwapAcc(int k)
  {
   double s=0;
   for(int i=PositionsTotal()-1; i>=0; i--)
     {
      ulong tk=PositionGetTicket(i);
      if(tk==0 || !PositionSelectByTicket(tk)) continue;
      if(PositionGetInteger(POSITION_MAGIC)!=InpMagicBase+k) continue;
      if(PositionGetString(POSITION_SYMBOL)!=g_sym[k]) continue;
      s += PositionGetDouble(POSITION_SWAP);
     }
   return s;
  }
bool OurPositionsExist()
  {
   for(int i=PositionsTotal()-1; i>=0; i--)
     {
      ulong tk=PositionGetTicket(i);
      if(tk==0 || !PositionSelectByTicket(tk)) continue;
      long m=PositionGetInteger(POSITION_MAGIC);
      if(m>=InpMagicBase && m<=InpMagicBase+MAGIC_FORB) return true;
     }
   return false;
  }
double QuantLots(string sym, double lots)
  {
   double stp=SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   if(stp<=0) stp=LOT_STEP;
   double q=MathRound(lots/stp)*stp;
   double vmax=SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   if(vmax>0 && MathAbs(q)>vmax) q=(q>0?vmax:-vmax);
   return q;
  }
double LegLotCap(int k, double eq)         // cap sanity dérivé du mqh (pace max 2.0 sim)
  {
   double px=MidPrice(g_sym[k]);
   double one=UsdPerLot(g_sym[k], px);
   if(one<=0) return 0.0;
   return LEG_CAP_PRE_VM*VmEff()*2.0*eq/one;
  }

//+------------------------------------------------------------------+
//| v2.2.1 — specs live (swap pts, rollover3days, marge) vs bornes     |
//+------------------------------------------------------------------+
void InitAnchors()
  {
   g_anc_swl[0]=ANCHOR_SWL_XAUUSD; g_anc_sws[0]=ANCHOR_SWS_XAUUSD;
   g_anc_swl[1]=ANCHOR_SWL_USDJPY; g_anc_sws[1]=ANCHOR_SWS_USDJPY;
   g_anc_swl[2]=ANCHOR_SWL_US100;  g_anc_sws[2]=ANCHOR_SWS_US100;
   g_anc_swl[3]=ANCHOR_SWL_GER40;  g_anc_sws[3]=ANCHOR_SWS_GER40;
   g_anc_r3d[0]=ANCHOR_R3D_XAUUSD; g_anc_r3d[1]=ANCHOR_R3D_USDJPY;
   g_anc_r3d[2]=ANCHOR_R3D_US100;  g_anc_r3d[3]=ANCHOR_R3D_GER40;
   g_mrate_std[0]=MARGIN_STD_XAUUSD;   g_mrate_swing[0]=MARGIN_SWING_XAUUSD;
   g_mrate_std[1]=MARGIN_STD_USDJPY;   g_mrate_swing[1]=MARGIN_SWING_USDJPY;
   g_mrate_std[2]=MARGIN_STD_US100;    g_mrate_swing[2]=MARGIN_SWING_US100;
   g_mrate_std[3]=MARGIN_STD_GER40;    g_mrate_swing[3]=MARGIN_SWING_GER40;
  }

void ReadLiveSpecs()
  {
   g_spec_breach=false;
   g_spec_breach_detail="";
   for(int k=0;k<N_LEGS;k++)
     {
      string sym=g_sym[k];
      g_live_swl[k]=SymbolInfoDouble(sym, SYMBOL_SWAP_LONG);
      g_live_sws[k]=SymbolInfoDouble(sym, SYMBOL_SWAP_SHORT);
      g_live_r3d[k]=(int)SymbolInfoInteger(sym, SYMBOL_SWAP_ROLLOVER3DAYS);
      double px=MidPrice(sym), need=0.0;
      double one=UsdPerLot(sym, px);
      g_live_mrate[k]=0.0;
      if(px>0 && one>0 && OrderCalcMargin(ORDER_TYPE_BUY, sym, 1.0, px, need)
         && need>0)
         g_live_mrate[k]=need/one;
      // bornes datées (mqh, source Standard 2026-06-10)
      double dl=MathAbs(g_live_swl[k]-g_anc_swl[k])
                /MathMax(MathAbs(g_anc_swl[k]), InpSanityAbsPtsFloor);
      double ds=MathAbs(g_live_sws[k]-g_anc_sws[k])
                /MathMax(MathAbs(g_anc_sws[k]), InpSanityAbsPtsFloor);
      if(dl>SANITY_SWAP_REL || ds>SANITY_SWAP_REL)
        {
         g_spec_breach=true;
         g_spec_breach_detail+=StringFormat("%s swap %.2f/%.2f vs ancre %.2f/%.2f; ",
            g_legs[k], g_live_swl[k], g_live_sws[k], g_anc_swl[k], g_anc_sws[k]);
        }
      if(g_live_r3d[k]!=g_anc_r3d[k])
        {
         g_spec_breach=true;
         g_spec_breach_detail+=StringFormat("%s r3d %d vs ancre %d; ",
            g_legs[k], g_live_r3d[k], g_anc_r3d[k]);
        }
      if(g_live_mrate[k]>0)
        {
         bool near_std=MathAbs(g_live_mrate[k]-g_mrate_std[k])
                       /g_mrate_std[k]<=SANITY_MARGIN_REL;
         bool near_swing=MathAbs(g_live_mrate[k]-g_mrate_swing[k])
                         /g_mrate_swing[k]<=SANITY_MARGIN_REL;
         if(!near_std && !near_swing)
           {
            g_spec_breach=true;
            g_spec_breach_detail+=StringFormat("%s marge %.4f hors Std %.4f/Swing %.4f; ",
               g_legs[k], g_live_mrate[k], g_mrate_std[k], g_mrate_swing[k]);
           }
        }
     }
   if(g_spec_breach) Print("SPEC BOUNDS BREACH: ", g_spec_breach_detail);
  }

// taux de marge pour l'ENFORCEMENT du cap 60% : live si lisible, sinon
// conservateur max(Swing anchor, policy mqh) — jamais la seule policy v2.2
double MarginRateEff(int k)
  {
   if(g_live_mrate[k]>0) return g_live_mrate[k];
   return MathMax(g_mrate_swing[k], g_mrate[k]);
  }

//+------------------------------------------------------------------+
//| Erreurs / fichiers                                                 |
//+------------------------------------------------------------------+
void SetError(string e) { g_last_error=e; Print("ERROR ", e); WriteState(true); }

void AtomicWrite(string fname, string content)
  {
   string tmp=fname+".tmp";
   int h=FileOpen(tmp, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h==INVALID_HANDLE) { Print("AtomicWrite FAIL ", fname); return; }
   FileWriteString(h, content);
   FileClose(h);
   if(!FileMove(tmp, 0, fname, FILE_REWRITE)) Print("FileMove FAIL ", fname);
  }

//+------------------------------------------------------------------+
//| Ordres — pattern slippage_probe2 v1.11 (jamais Result*)            |
//+------------------------------------------------------------------+
bool RawSend(MqlTradeRequest &req)
  {
   MqlTradeResult res;
   ZeroMemory(res);
   bool ok=OrderSend(req, res);
   if(!ok || (res.retcode!=TRADE_RETCODE_DONE && res.retcode!=TRADE_RETCODE_PLACED
              && res.retcode!=TRADE_RETCODE_DONE_PARTIAL))
     {
      SetError(StringFormat("OrderSend %s ret=%d %s", req.symbol, res.retcode, res.comment));
      return false;
     }
   return true;        // la confirmation de fill vient des scans async uniquement
  }

int PendAdd(string sym, int side, double lots, double req_px, long magic,
            string reason, bool is_close, bool is_resting)
  {
   if(g_pend_n>=PENDING_MAX) { SetError("pendings saturés"); return -1; }
   Pending p;
   p.id=++g_pend_seq; p.symbol=sym; p.side=side; p.lots=lots; p.req_px=req_px;
   p.magic=magic; p.reason=reason; p.sent=TimeCurrent();
   p.vol_before=SignedVolume(sym, magic);
   p.is_close=is_close; p.is_resting=is_resting; p.done=false;
   g_pend[g_pend_n]=p;
   return g_pend_n++;
  }

bool SendMarket(string sym, int side, double lots, long magic, string reason, bool is_close)
  {
   if(g_killed) return false;
   lots=MathAbs(lots);
   if(lots<LOT_STEP/2.0) return false;
   double req_px=SidePrice(sym, side);
   MqlTradeRequest req;
   ZeroMemory(req);
   req.action=TRADE_ACTION_DEAL;
   req.symbol=sym;
   req.volume=lots;
   req.type=side>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   req.price=req_px;
   req.deviation=50;
   req.magic=magic;
   req.comment=reason;
   req.type_filling=ORDER_FILLING_IOC;
   int pi=PendAdd(sym, side, lots, req_px, magic, reason, is_close, false);
   if(pi<0) return false;
   if(!RawSend(req)) { g_pend[pi].done=true; return false; }
   return true;
  }

bool CloseLegLots(string sym, long magic, double lots_to_close, string reason)
  {
   double remaining=MathAbs(lots_to_close);
   for(int i=PositionsTotal()-1; i>=0 && remaining>LOT_STEP/2.0; i--)
     {
      ulong tk=PositionGetTicket(i);
      if(tk==0 || !PositionSelectByTicket(tk)) continue;
      if(PositionGetInteger(POSITION_MAGIC)!=magic) continue;
      if(PositionGetString(POSITION_SYMBOL)!=sym) continue;
      double vol=PositionGetDouble(POSITION_VOLUME);
      double cl=MathMin(vol, remaining);
      int side=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY) ? -1 : +1;
      MqlTradeRequest req;
      ZeroMemory(req);
      req.action=TRADE_ACTION_DEAL;
      req.position=tk;
      req.symbol=sym;
      req.volume=QuantLots(sym, cl);
      req.type=side>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      req.price=SidePrice(sym, side);
      req.deviation=50;
      req.magic=magic;
      req.comment=reason;
      req.type_filling=ORDER_FILLING_IOC;
      int pi=PendAdd(sym, side, req.volume, req.price, magic, reason, true, false);
      if(pi<0) return false;
      if(!RawSend(req)) { g_pend[pi].done=true; return false; }
      remaining -= req.volume;
     }
   return true;
  }

void TradeLegTo(int k, double target_lots, string reason)
  {
   double cur=LegLots(k);
   double d=target_lots-cur;
   if(MathAbs(d)<LOT_STEP/2.0) return;
   long magic=InpMagicBase+k;
   if(cur!=0.0 && ((cur>0 && d<0) || (cur<0 && d>0)))
     {
      double reduce=MathMin(MathAbs(d), MathAbs(cur));
      if(!CloseLegLots(g_sym[k], magic, reduce, reason)) return;
      d = target_lots - (cur + (cur>0 ? -reduce : reduce));
      if(MathAbs(d)<LOT_STEP/2.0) return;
     }
   SendMarket(g_sym[k], d>0?+1:-1, MathAbs(d), magic, reason, false);
  }

bool PlaceStopOrder(string sym, int side, double lots, double level, double sl,
                    long magic, string reason)
  {
   int dg=(int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   MqlTradeRequest req;
   ZeroMemory(req);
   req.action=TRADE_ACTION_PENDING;
   req.symbol=sym;
   req.volume=lots;
   req.type=side>0 ? ORDER_TYPE_BUY_STOP : ORDER_TYPE_SELL_STOP;
   req.price=NormalizeDouble(level, dg);
   req.sl=NormalizeDouble(sl, dg);
   req.magic=magic;
   req.comment=reason;
   req.type_time=ORDER_TIME_SPECIFIED;
   req.expiration=ServerOfParisHM(2200);
   int pi=PendAdd(sym, side, lots, level, magic, reason, false, true);
   if(pi<0) return false;
   MqlTradeResult res;
   ZeroMemory(res);
   bool ok=OrderSend(req, res);
   if(!ok || (res.retcode!=TRADE_RETCODE_DONE && res.retcode!=TRADE_RETCODE_PLACED))
     {
      req.type_time=ORDER_TIME_DAY;                     // fallback brokers sans SPECIFIED
      req.expiration=0;
      ZeroMemory(res);
      ok=OrderSend(req, res);
      if(!ok || (res.retcode!=TRADE_RETCODE_DONE && res.retcode!=TRADE_RETCODE_PLACED))
        {
         g_pend[pi].done=true;
         SetError(StringFormat("stop %s ret=%d %s", sym, res.retcode, res.comment));
         return false;
        }
     }
   return true;
  }

void CancelPendingStops(long magic, int keep_side)
  {
   for(int i=OrdersTotal()-1; i>=0; i--)
     {
      ulong tk=OrderGetTicket(i);
      if(tk==0) continue;
      if(OrderGetInteger(ORDER_MAGIC)!=magic) continue;
      long ot=OrderGetInteger(ORDER_TYPE);
      int side=(ot==ORDER_TYPE_BUY_STOP) ? +1 : (ot==ORDER_TYPE_SELL_STOP ? -1 : 0);
      if(side==0 || side==keep_side) continue;
      MqlTradeRequest req;
      ZeroMemory(req);
      req.action=TRADE_ACTION_REMOVE;
      req.order=tk;
      RawSend(req);
      MarkRestingDone(magic, side);
     }
  }
void CancelAllPendingOrders(long magic)
  {
   for(int i=OrdersTotal()-1; i>=0; i--)
     {
      ulong tk=OrderGetTicket(i);
      if(tk==0) continue;
      long m=OrderGetInteger(ORDER_MAGIC);
      if(magic!=0 && m!=magic) continue;
      if(magic==0 && (m<InpMagicBase || m>InpMagicBase+MAGIC_FORB)) continue;
      MqlTradeRequest req;
      ZeroMemory(req);
      req.action=TRADE_ACTION_REMOVE;
      req.order=tk;
      RawSend(req);
     }
  }
void MarkRestingDone(long magic, int side)
  {
   for(int n=0; n<g_pend_n; n++)
      if(!g_pend[n].done && g_pend[n].is_resting && g_pend[n].magic==magic
         && (side==0 || g_pend[n].side==side))
         g_pend[n].done=true;
  }

void ModifyPositionSL(string sym, long magic, double new_sl)
  {
   for(int i=PositionsTotal()-1; i>=0; i--)
     {
      ulong tk=PositionGetTicket(i);
      if(tk==0 || !PositionSelectByTicket(tk)) continue;
      if(PositionGetInteger(POSITION_MAGIC)!=magic) continue;
      if(PositionGetString(POSITION_SYMBOL)!=sym) continue;
      MqlTradeRequest req;
      ZeroMemory(req);
      req.action=TRADE_ACTION_SLTP;
      req.position=tk;
      req.symbol=sym;
      req.sl=NormalizeDouble(new_sl, (int)SymbolInfoInteger(sym, SYMBOL_DIGITS));
      req.tp=PositionGetDouble(POSITION_TP);
      RawSend(req);
     }
  }

void FlattenAll(string reason)
  {
   CancelAllPendingOrders(0);
   MarkRestingDone(InpMagicBase+MAGIC_MICRO, 0);
   MarkRestingDone(InpMagicBase+MAGIC_FORB, 0);
   for(int i=PositionsTotal()-1; i>=0; i--)
     {
      ulong tk=PositionGetTicket(i);
      if(tk==0 || !PositionSelectByTicket(tk)) continue;
      long magic=PositionGetInteger(POSITION_MAGIC);
      if(magic<InpMagicBase || magic>InpMagicBase+MAGIC_FORB) continue;
      string sym=PositionGetString(POSITION_SYMBOL);
      CloseLegLots(sym, magic, PositionGetDouble(POSITION_VOLUME), reason);
     }
   g_flat_today=true;
  }

// confirmation asynchrone : entrée = delta de volume signé puis POSITION_PRICE_OPEN ;
// sortie = scan historique DEAL_ENTRY_OUT (retries) ; stops dormants sans timeout
void ConfirmPendings()
  {
   g_pending_unconfirmed=0;
   for(int n=0; n<g_pend_n; n++)
     {
      if(g_pend[n].done) continue;
      double fill=0.0;
      long deal_tk=0;
      if(g_pend[n].is_close)
         fill=ScanExitDeal(g_pend[n], deal_tk);
      else
        {
         double dv=SignedVolume(g_pend[n].symbol, g_pend[n].magic)-g_pend[n].vol_before;
         if(dv*g_pend[n].side >= g_pend[n].lots - LOT_STEP/2.0)   // delta SIGNÉ côté ordre
            fill=EntryFillPx(g_pend[n]);
        }
      if(fill>0)
        {
         g_pend[n].done=true;
         double slip=(fill/g_pend[n].req_px-1.0)*g_pend[n].side*1e4;
         LogFill(g_pend[n], fill, slip, deal_tk);
         if(!g_pend[n].is_close) OnOpenedFill(g_pend[n], fill);
        }
      else if(!g_pend[n].is_resting && TimeCurrent()-g_pend[n].sent>InpFillTimeoutSec)
        {
         g_pend[n].done=true;
         SetError(StringFormat("fill NON CONFIRMÉ %s %s %.2f lots (>%ds)",
                  g_pend[n].symbol, g_pend[n].reason, g_pend[n].lots, InpFillTimeoutSec));
        }
      else if(!g_pend[n].is_resting)
         g_pending_unconfirmed++;
     }
   while(g_pend_n>0 && g_pend[g_pend_n-1].done) g_pend_n--;
  }

double EntryFillPx(Pending &p)
  {
   // hedging: position la plus récente magic+symbol ; netting: PRICE_OPEN (pondéré)
   datetime best_t=0;
   double best_px=0, wnum=0, wden=0;
   for(int i=PositionsTotal()-1; i>=0; i--)
     {
      ulong tk=PositionGetTicket(i);
      if(tk==0 || !PositionSelectByTicket(tk)) continue;
      if(PositionGetInteger(POSITION_MAGIC)!=p.magic) continue;
      if(PositionGetString(POSITION_SYMBOL)!=p.symbol) continue;
      datetime t=(datetime)PositionGetInteger(POSITION_TIME);
      double px=PositionGetDouble(POSITION_PRICE_OPEN);
      double vol=PositionGetDouble(POSITION_VOLUME);
      wnum+=px*vol; wden+=vol;
      if(t>=best_t) { best_t=t; best_px=px; }
     }
   long mm=AccountInfoInteger(ACCOUNT_MARGIN_MODE);
   if(mm==ACCOUNT_MARGIN_MODE_RETAIL_HEDGING) return best_px;
   return wden>0 ? wnum/wden : best_px;
  }

double ScanExitDeal(Pending &p, long &deal_tk)
  {
   if(!HistorySelect(p.sent-60, TimeCurrent()+60)) return 0.0;
   for(int i=HistoryDealsTotal()-1; i>=0; i--)
     {
      ulong tk=HistoryDealGetTicket(i);
      if(tk==0) continue;
      if(HistoryDealGetInteger(tk, DEAL_MAGIC)!=p.magic) continue;
      if(HistoryDealGetString(tk, DEAL_SYMBOL)!=p.symbol) continue;
      if(HistoryDealGetInteger(tk, DEAL_ENTRY)!=DEAL_ENTRY_OUT) continue;
      if((datetime)HistoryDealGetInteger(tk, DEAL_TIME) < p.sent-5) continue;
      deal_tk=(long)tk;
      return HistoryDealGetDouble(tk, DEAL_PRICE);
     }
   return 0.0;
  }

void OnOpenedFill(Pending &p, double fill)
  {
   if(!g_opened_today)
     {
      g_opened_today=true;
      g_open_days++;
      if(InpPhase==3) g_wd_tdays++;
      SaveState();
     }
   if(p.magic==InpMagicBase+MAGIC_MICRO && g_micro_state<=1)
     {
      g_micro_state=2;
      g_micro_entry=fill;
      CancelPendingStops(InpMagicBase+MAGIC_MICRO, p.side);    // OCO: annule l'autre côté
      SaveState();
     }
   if(p.magic==InpMagicBase+MAGIC_FORB)
      CancelPendingStops(InpMagicBase+MAGIC_FORB, p.side);
  }

//+------------------------------------------------------------------+
//| Détection des sorties serveur (SL/expiration) sur micro/forb       |
//+------------------------------------------------------------------+
datetime g_exit_scan_from=0;
void DetectServerExits()
  {
   long magics[2];
   magics[0]=InpMagicBase+MAGIC_MICRO;
   magics[1]=InpMagicBase+MAGIC_FORB;
   if(g_exit_scan_from==0) g_exit_scan_from=TimeCurrent()-3600;
   if(!HistorySelect(g_exit_scan_from-60, TimeCurrent()+60)) return;
   for(int i=HistoryDealsTotal()-1; i>=0; i--)
     {
      ulong tk=HistoryDealGetTicket(i);
      if(tk==0) continue;
      long m=HistoryDealGetInteger(tk, DEAL_MAGIC);
      if(m!=magics[0] && m!=magics[1]) continue;
      if(HistoryDealGetInteger(tk, DEAL_ENTRY)!=DEAL_ENTRY_OUT) continue;
      datetime dt=(datetime)HistoryDealGetInteger(tk, DEAL_TIME);
      if(dt<=g_exit_scan_from) continue;
      g_exit_scan_from=dt;
      long rsn=HistoryDealGetInteger(tk, DEAL_REASON);
      string label;
      if(m==magics[1]) label="funded_orb_exit";
      else if(rsn==DEAL_REASON_SL) label=g_micro_be ? "micro_be" : "micro_stop";
      else label="micro_time";
      Pending fake;
      fake.id=0; fake.lots=HistoryDealGetDouble(tk, DEAL_VOLUME);
      fake.symbol=HistoryDealGetString(tk, DEAL_SYMBOL);
      fake.side=(HistoryDealGetInteger(tk, DEAL_TYPE)==DEAL_TYPE_BUY)?+1:-1;
      // sortie short = deal BUY ; req de référence: SL courant (BE ou côté opposé)
      fake.req_px=(m==magics[0] && g_micro_be) ? g_micro_entry :
                  (g_micro_entry>0 ? (fake.side>0 ? g_or_hi : g_or_lo) : 0.0);
      fake.magic=m; fake.reason=label; fake.sent=dt;
      fake.vol_before=0; fake.is_close=true; fake.is_resting=true; fake.done=true;
      double px=HistoryDealGetDouble(tk, DEAL_PRICE);
      double slip=(fake.req_px>0) ? (px/fake.req_px-1.0)*fake.side*1e4 : 0.0;
      LogFill(fake, px, slip, (long)tk);
      if(m==magics[0] && g_micro_state==2) { g_micro_state=3; SaveState(); }
     }
  }

//+------------------------------------------------------------------+
//| targets.json (clés plates ea_*)                                    |
//+------------------------------------------------------------------+
string g_tj_txt="";
bool TargetsRead()
  {
   g_tj_txt="";
   int h=FileOpen("targets.json", FILE_READ|FILE_TXT|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(h==INVALID_HANDLE) { g_targets_status="MISSING"; return false; }
   while(!FileIsEnding(h)) g_tj_txt += FileReadString(h)+"\n";
   FileClose(h);
   if(StringLen(g_tj_txt)<10) { g_targets_status="MISSING"; return false; }
   return true;
  }
string JKey(string key)
  {
   int i=StringFind(g_tj_txt, "\""+key+"\"");
   if(i<0) return "";
   int c=StringFind(g_tj_txt, ":", i);
   if(c<0) return "";
   int e1=StringFind(g_tj_txt, ",", c);
   int e2=StringFind(g_tj_txt, "\n", c);
   int e=(e1<0) ? e2 : ((e2<0) ? e1 : MathMin(e1, e2));
   if(e<0) e=StringLen(g_tj_txt);
   string v=StringSubstr(g_tj_txt, c+1, e-c-1);
   StringTrimLeft(v); StringTrimRight(v);
   StringReplace(v, "\"", "");
   return v;
  }
double JD(string key) { return StringToDouble(JKey(key)); }

double TargetsAgeH()
  {
   string gen=JKey("ea_generated_at_paris");           // "YYYY.MM.DD HH:MM:SS"
   if(StringLen(gen)<19) return -1;
   datetime g=StringToTime(gen);                       // format natif MQL5 (points)
   if(g<=0) return -1;
   return (double)((long)(ParisNow()-g))/3600.0;
  }

bool TargetsValidate()                                  // true = risque nouveau autorisé
  {
   if(!TargetsRead()) return false;
   if(JKey("ea_spec_sha256")!=SPEC_SHA256) { g_targets_status="BAD_SHA"; return false; }
   double age_h=TargetsAgeH();
   if(age_h<0) { g_targets_status="BAD_FORMAT"; return false; }
   if(age_h>26.0) { g_targets_status="STALE"; return false; }
   int on_file=(int)JD("ea_on_day");
   if(on_file != (IsONDay()?1:0)) { g_targets_status="BAD_ONDAY"; return false; }
   g_mode_mismatch=false;                               // alarme seulement, mqh = autorité
   if(MathAbs(JD("ea_vm")-VmEff())>1e-9) g_mode_mismatch=true;
   if(MathAbs(JD("ea_on_w")-OnWEff())>1e-9) g_mode_mismatch=true;
   if((int)JD("ea_micro_orb") != (MicroEnabled()?1:0)) g_mode_mismatch=true;
   string ph=JKey("ea_phase_hint");
   if((InpPhase==1 && ph!="P1") || (InpPhase==2 && ph!="P2")
      || (InpPhase==3 && ph!="FUNDED")) g_mode_mismatch=true;
   g_targets_status="OK";
   return true;
  }

//+------------------------------------------------------------------+
//| Sizing commun : cap marge proportionnel (sim) + quantize + caps    |
//+------------------------------------------------------------------+
void CapQuantizeTrade(double &tgt[], double eq, string reason, bool &trade_mask[])
  {
   // v2.2.1: enforcement au taux de marge LIVE (OrderCalcMargin) — le broker
   // rejetterait sinon ; la policy v2.2 (MRATE_*) reste le miroir sim, l'écart
   // Swing vs policy est LE headline du recost (Δ p(pass) -15.6 pt si Swing).
   double need=0;
   for(int k=0;k<N_LEGS;k++) need += MathAbs(tgt[k])*MarginRateEff(k);
   bool capped=(eq>0 && need>CH_MARGIN_CAP*eq);          // funded: même cap (yaml)
   if(capped)
     {
      double f=CH_MARGIN_CAP*eq/need;
      for(int k=0;k<N_LEGS;k++) { tgt[k]*=f; trade_mask[k]=true; }  // sim: TOUTES jambes
     }
   for(int k=0;k<N_LEGS;k++)
     {
      if(!trade_mask[k]) continue;
      double px=MidPrice(g_sym[k]);
      double one=UsdPerLot(g_sym[k], px);
      if(one<=0) continue;
      double lots=QuantLots(g_sym[k], tgt[k]/one);
      double cap=LegLotCap(k, eq);
      if(cap>0 && MathAbs(lots)>cap) lots=(lots>0?cap:-cap);
      TradeLegTo(k, lots, reason);
     }
  }

//+------------------------------------------------------------------+
//| Actions de schedule                                                |
//+------------------------------------------------------------------+
void Do0900() { if(LegLots(3)!=0.0) TradeLegTo(3, 0.0, "ger40_off"); }
void Do1530() { if(LegLots(2)!=0.0) TradeLegTo(2, 0.0, "us100_off"); }

void DoBuildOR()
  {
   MqlRates r[];
   datetime t0=ServerOfParisHM(1530), t1=ServerOfParisHM(1600);
   int n=CopyRates(g_micro_sym, PERIOD_M5, t0, t1-1, r);
   if(n<4) { g_micro_state=4; SaveState(); return; }     // OR invalide → skip
   g_or_hi=-1; g_or_lo=1e18;
   for(int i=0;i<n;i++) { g_or_hi=MathMax(g_or_hi, r[i].high); g_or_lo=MathMin(g_or_lo, r[i].low); }
   g_or_end_close=r[n-1].close;
   SaveState();
  }

void Do1600Arm()
  {
   bool width_ok=(g_or_end_close>0 && g_or_hi>g_or_lo &&
                  (g_or_hi-g_or_lo)/g_or_end_close*1e4 >= InpMicroMinWidthBps);
   if(MicroEnabled())
     {
      // sémantique 605f4a4 : jamais armé un jour ON (le GER40 17:35 marquera
      // `opened`) ; ni si déjà ouvert ; ni targets non-OK (risque nouveau).
      // Week-end stale impossible ici: lun/mar = jours ON, jamais armés.
      TargetsValidate();
      if(IsONDay() || g_opened_today || g_flat_today || !width_ok
         || g_targets_status!="OK")
        { g_micro_state=4; SaveState(); return; }
      if(PlaceStopOrder(g_micro_sym, +1, MICRO_ORB_LOTS, g_or_hi, g_or_lo,
                        InpMagicBase+MAGIC_MICRO, "micro_entry") &&
         PlaceStopOrder(g_micro_sym, -1, MICRO_ORB_LOTS, g_or_lo, g_or_hi,
                        InpMagicBase+MAGIC_MICRO, "micro_entry"))
         g_micro_state=1;
      else g_micro_state=4;
     }
   else if(FundedOrbOn() && width_ok && !g_flat_today)
     {
      double risk=FU_ORB_RISK*ACCOUNT_SIZE_USD*OrbTaper0();
      double upp=UsdPerUnit(g_micro_sym);
      double lots=0.0;
      if(upp>0 && g_or_hi>g_or_lo)
         lots=MathFloor(risk/((g_or_hi-g_or_lo)*upp)/LOT_STEP)*LOT_STEP;
      if(lots>=LOT_STEP)
        {
         if(PlaceStopOrder(g_micro_sym, +1, lots, g_or_hi, g_or_lo,
                           InpMagicBase+MAGIC_FORB, "funded_orb_entry") &&
            PlaceStopOrder(g_micro_sym, -1, lots, g_or_lo, g_or_hi,
                           InpMagicBase+MAGIC_FORB, "funded_orb_entry"))
            g_micro_state=1;
        }
     }
   SaveState();
  }

void MicroManage()                  // trail-to-BE à +1R (V2+E7, spec yaml)
  {
   if(g_micro_be) return;
   long magic=MicroEnabled() ? InpMagicBase+MAGIC_MICRO : InpMagicBase+MAGIC_FORB;
   double v=SignedVolume(g_micro_sym, magic);
   if(v==0.0) return;
   if(g_micro_entry<=0) g_micro_entry=LegAvgPxByMagic(g_micro_sym, magic);
   double R=g_or_hi-g_or_lo;
   if(R<=0 || g_micro_entry<=0) return;
   double px=MidPrice(g_micro_sym);
   if(px<=0) return;
   if((v>0 && px>=g_micro_entry+R) || (v<0 && px<=g_micro_entry-R))
     {
      ModifyPositionSL(g_micro_sym, magic, g_micro_entry);
      g_micro_be=true;
      SaveState();
     }
  }

void Do1735()                       // GER40 on (jour ON) — gouverneur live
  {
   if(!IsONDay() || g_flat_today) return;
   TargetsValidate();
   if(g_targets_status!="OK")
     { SetError("17:35 GER40 skip: targets "+g_targets_status); return; }
   double eq=AccountInfoDouble(ACCOUNT_EQUITY);
   double tgt[N_LEGS];
   bool mask[N_LEGS];
   for(int k=0;k<N_LEGS;k++) { tgt[k]=LegNotionalAtAvg(k); mask[k]=false; } // sim: pos.copy()
   tgt[3]=OnWEff()*Scale(eq)*eq;
   mask[3]=true;
   CapQuantizeTrade(tgt, eq, "ger40_on", mask);
  }

void Do2130Backstop()
  {
   if(InpPhase==3) return;
   double bal=AccountInfoDouble(ACCOUNT_BALANCE);
   // yaml: aucun signal ORB ce jour ET rien d'ouvert ET min-days non atteint
   // ET balance >= cible (incidence sim: 50/13068)
   if(!g_opened_today && g_open_days<MIN_TRADING_DAYS && bal>=TargetEq()
      && !OurPositionsExist())
     {
      CancelAllPendingOrders(InpMagicBase+MAGIC_MICRO);  // pas de double comptage
      MarkRestingDone(InpMagicBase+MAGIC_MICRO, 0);
      if(SendMarket(g_micro_sym, +1, MICRO_ORB_LOTS, InpMagicBase+MAGIC_BACKSTOP,
                    "backstop_open", false))
         g_backstop_close_due=true;
     }
  }
void BackstopCloseIfDue()
  {
   if(!g_backstop_close_due) return;
   double v=SignedVolume(g_micro_sym, InpMagicBase+MAGIC_BACKSTOP);
   if(v!=0.0)
     {
      CloseLegLots(g_micro_sym, InpMagicBase+MAGIC_BACKSTOP, MathAbs(v), "backstop_close");
      g_backstop_close_due=false;
     }
  }

void Do2200TimeStop()
  {
   long magics[2];
   magics[0]=InpMagicBase+MAGIC_MICRO;
   magics[1]=InpMagicBase+MAGIC_FORB;
   for(int m=0;m<2;m++)
     {
      CancelAllPendingOrders(magics[m]);
      MarkRestingDone(magics[m], 0);
      double v=SignedVolume(g_micro_sym, magics[m]);
      if(v!=0.0)
         CloseLegLots(g_micro_sym, magics[m], MathAbs(v),
                      m==0 ? "micro_time" : "funded_orb_exit");
     }
   if(g_micro_state<3) g_micro_state=3;
   SaveState();
  }

void Do2205Rebalance()
  {
   ReadLiveSpecs();                  // v2.2.1: specs du jour avant le sizing
   bool ok=TargetsValidate();
   if(g_flat_today) return;
   if(!ok)
     {
      SetError("22:05 rebalance SKIP: targets "+g_targets_status+" — gestion seule");
      return;
     }
   double eq=AccountInfoDouble(ACCOUNT_EQUITY);
   double sc=Scale(eq);
   double tgt[N_LEGS];
   bool mask[N_LEGS];
   tgt[0]=JD("ea_w_xauusd")*sc*eq;  mask[0]=true;
   tgt[1]=JD("ea_w_usdjpy")*sc*eq;  mask[1]=true;
   tgt[2]=IsONDay() ? OnWEff()*sc*eq : 0.0;  mask[2]=true;
   tgt[3]=LegNotionalAtAvg(3);      mask[3]=false;       // GER40 untouched (sim s=4)
   CapQuantizeTrade(tgt, eq, "rebalance", mask);
   g_last_rebalance=StringFormat(
      "{\"ts\":\"%s\",\"eq_used\":%.2f,\"scale\":%.6f,"
      "\"targets_usd\":{\"XAUUSD\":%.2f,\"USDJPY\":%.2f,\"US100\":%.2f,\"GER40\":%.2f}}",
      TsParis(), eq, sc, tgt[0], tgt[1], tgt[2], tgt[3]);
   SaveState();
   WriteState(true);
  }

//+------------------------------------------------------------------+
//| Invariants M5                                                      |
//+------------------------------------------------------------------+
void InvariantCheckM5()
  {
   double eq=AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq<BreakerLine() && !g_flat_today && OurPositionsExist())
     {
      g_breaker_today=true;
      FlattenAll("breaker_flat");
      SetError(StringFormat("BREAKER eq %.2f < ligne %.2f — flatten", eq, BreakerLine()));
      return;
     }
   if(InpPhase!=3 && eq>=TargetEq() && !g_flat_today && OurPositionsExist())
     {
      FlattenAll("target_lock_flat");
      Print("TARGET LOCK eq ", DoubleToString(eq,2), " >= ", DoubleToString(TargetEq(),2));
     }
  }

//+------------------------------------------------------------------+
//| Rollover quotidien (00:00 Paris/Prague — ancre FTMO)               |
//+------------------------------------------------------------------+
void DayRollover()
  {
   LogSwapsBilled();                                   // nuit écoulée, avant reset
   g_anchor_balance=AccountInfoDouble(ACCOUNT_BALANCE);
   g_anchor_date=ParisDate();
   g_opened_today=false; g_flat_today=false; g_breaker_today=false;
   g_micro_state=0; g_or_hi=0; g_or_lo=0; g_or_end_close=0;
   g_micro_entry=0; g_micro_be=false; g_backstop_close_due=false;
   g_done_0900=g_done_1530=g_done_or=g_done_1600=g_done_1735=false;
   g_done_2130=g_done_2145=g_done_2200=g_done_2205=g_done_2258=false;
   g_pend_n=0;
   double eq=AccountInfoDouble(ACCOUNT_EQUITY);
   if(InpPhase!=3)                                     // abandon: zombie EOD (alerte)
     {
      if(eq < StaticFloor()+CH_ABANDON_BUF*ACCOUNT_SIZE_USD) g_zombie_days++;
      else g_zombie_days=0;
     }
   SaveState();
   WriteState(true);
  }

void LogSwapsBilled()
  {
   for(int i=PositionsTotal()-1; i>=0; i--)
     {
      ulong tk=PositionGetTicket(i);
      if(tk==0 || !PositionSelectByTicket(tk)) continue;
      long magic=PositionGetInteger(POSITION_MAGIC);
      if(magic<InpMagicBase || magic>InpMagicBase+MAGIC_FORB) continue;
      double sw=PositionGetDouble(POSITION_SWAP);
      double d=sw-SwapLastGet((long)tk);
      SwapLastSet((long)tk, sw);
      if(MathAbs(d)<0.0001) continue;
      string sym=PositionGetString(POSITION_SYMBOL);
      double lots=PositionGetDouble(POSITION_VOLUME);
      double px=MidPrice(sym);
      double notional=lots*UsdPerLot(sym, px)
            *((PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY)?1:-1);
      int h=FileOpen("swaps_billed.csv",
                     FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ);
      if(h!=INVALID_HANDLE)
        {
         if(FileSize(h)==0)
            FileWriteString(h, "date_paris,symbol,lots_held,notional_usd,swap_usd\n");
         FileSeek(h, 0, SEEK_END);
         datetime y=ParisNow()-86400;                  // la nuit facturée = date de la veille
         MqlDateTime p; TimeToStruct(y, p);
         FileWriteString(h, StringFormat("%04d-%02d-%02d,%s,%.2f,%.2f,%.2f\n",
                         p.year, p.mon, p.day, sym, lots, notional, d));
         FileClose(h);
        }
     }
  }
double SwapLastGet(long tk)
  {
   for(int i=0;i<g_swl_n;i++) if(g_swl_tk[i]==tk) return g_swl_val[i];
   return 0.0;
  }
void SwapLastSet(long tk, double v)
  {
   for(int i=0;i<g_swl_n;i++) if(g_swl_tk[i]==tk) { g_swl_val[i]=v; return; }
   if(g_swl_n<256) { g_swl_tk[g_swl_n]=tk; g_swl_val[g_swl_n]=v; g_swl_n++; }
  }

//+------------------------------------------------------------------+
//| Exports                                                            |
//+------------------------------------------------------------------+
void Do2145Export()
  {
   ReadLiveSpecs();                  // export = specs du jour (brain/reconcile)
   string js="{\n\"generated_at_paris\": \""+TsParis()+"\",\n";
   js+=StringFormat("\"server_minus_paris_min\": %d,\n", InpServerTZOffsetMin);
   js+=StringFormat("\"account\": {\"balance\": %.2f, \"equity\": %.2f, \"phase\": %d},\n",
       AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY), InpPhase);
   js+="\"symbols\": {\n";
   for(int k=0;k<N_LEGS;k++)
     {
      string sym=g_sym[k];
      MqlRates r[];
      int n=CopyRates(sym, PERIOD_D1, 0, 520, r);
      js+="\""+g_legs[k]+"\": {";
      js+=StringFormat("\"broker_symbol\": \"%s\", \"digits\": %d, \"contract\": %.2f, ",
          sym, (int)SymbolInfoInteger(sym, SYMBOL_DIGITS),
          SymbolInfoDouble(sym, SYMBOL_TRADE_CONTRACT_SIZE));
      js+=StringFormat("\"tick_value\": %.6f, \"tick_size\": %.6f, ",
          SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE),
          SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE));
      js+=StringFormat("\"swap_long\": %.4f, \"swap_short\": %.4f, \"swap_mode\": %d, ",
          SymbolInfoDouble(sym, SYMBOL_SWAP_LONG), SymbolInfoDouble(sym, SYMBOL_SWAP_SHORT),
          (int)SymbolInfoInteger(sym, SYMBOL_SWAP_MODE));
      js+=StringFormat("\"swap_r3d\": %d, \"margin_rate_live\": %.6f,\n",
          g_live_r3d[k], g_live_mrate[k]);
      js+="\"d1\": [";
      for(int i=0;i<n;i++)
        {
         MqlDateTime b; TimeToStruct(r[i].time, b);
         js+=StringFormat("[\"%04d.%02d.%02d\",%.5f,%.5f,%.5f,%.5f]%s",
             b.year, b.mon, b.day, r[i].open, r[i].high, r[i].low, r[i].close,
             i<n-1 ? "," : "");
        }
      js+="]}";
      js+=(k<N_LEGS-1) ? ",\n" : "\n";
     }
   js+="}\n}\n";
   AtomicWrite("market_export.json", js);
  }

void Do2258EOD()
  {
   string js="{\n\"date\": \""+ParisDate()+"\",\n\"legs\": {\n";
   datetime t0=ServerOfParisHM(0);
   for(int k=0;k<N_LEGS;k++)
     {
      MqlRates r[];
      int n=CopyRates(g_sym[k], PERIOD_M5, t0, TimeCurrent(), r);
      js+="\""+g_legs[k]+"\": [";
      for(int i=0;i<n;i++)
        {
         MqlDateTime b; TimeToStruct(r[i].time-InpServerTZOffsetMin*60, b);
         js+=StringFormat("[\"%02d:%02d\",%.5f]%s", b.hour, b.min, r[i].close,
                          i<n-1 ? "," : "");
        }
      js+="]";
      js+=(k<N_LEGS-1) ? ",\n" : "\n";
     }
   js+="}\n}\n";
   AtomicWrite("m5_today.json", js);
   WriteState(true);                                   // état avec bloc eod
  }

//+------------------------------------------------------------------+
//| state.json / fills.csv / ea_state.json                             |
//+------------------------------------------------------------------+
void LogFill(Pending &p, double fill, double slip_bps, long deal_tk)
  {
   int h=FileOpen("fills.csv", FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ);
   if(h==INVALID_HANDLE) return;
   if(FileSize(h)==0)
      FileWriteString(h, "ts_server,ts_paris,phase,reason,symbol,side,lots,req_price,"
                         "fill_price,slip_bps,latency_ms,order_ticket,deal_ticket,"
                         "position_id,magic,comment\n");
   FileSeek(h, 0, SEEK_END);
   long lat_ms=(long)(TimeCurrent()-p.sent)*1000;
   if(p.is_resting) lat_ms=0;                          // stop dormant: latence non pertinente
   FileWriteString(h, StringFormat("%s,%s,%d,%s,%s,%s,%.2f,%.5f,%.5f,%.2f,%I64d,%d,%I64d,%d,%I64d,\n",
       TsServer(), TsParis(), InpPhase, p.reason, p.symbol, p.side>0?"BUY":"SELL",
       p.lots, p.req_px, fill, slip_bps, lat_ms, 0, deal_tk, 0, p.magic));
   FileClose(h);
   WriteState(true);
  }

string PositionsJson()
  {
   string js="[";
   bool first=true;
   for(int k=0;k<N_LEGS;k++)
     {
      double lots=LegLots(k);
      if(lots==0.0) continue;
      if(!first) js+=",";
      js+=StringFormat("{\"leg\":\"%s\",\"symbol\":\"%s\",\"lots\":%.2f,\"dir\":%d,"
                       "\"avg\":%.5f,\"notional_usd\":%.2f,\"swap_acc\":%.2f}",
          g_legs[k], g_sym[k], MathAbs(lots), lots>0?1:-1, LegAvgPx(k),
          MathAbs(LegNotionalAtAvg(k)), LegSwapAcc(k));
      first=false;
     }
   long extra[3];
   extra[0]=InpMagicBase+MAGIC_MICRO;
   extra[1]=InpMagicBase+MAGIC_BACKSTOP;
   extra[2]=InpMagicBase+MAGIC_FORB;
   string names[3];
   names[0]="MICRO"; names[1]="BACKSTOP"; names[2]="FORB";
   for(int m=0;m<3;m++)
     {
      double v=SignedVolume(g_micro_sym, extra[m]);
      if(v==0.0) continue;
      if(!first) js+=",";
      double avg=LegAvgPxByMagic(g_micro_sym, extra[m]);
      js+=StringFormat("{\"leg\":\"%s\",\"symbol\":\"%s\",\"lots\":%.2f,\"dir\":%d,"
                       "\"avg\":%.5f,\"notional_usd\":%.2f,\"swap_acc\":0}",
          names[m], g_micro_sym, MathAbs(v), v>0?1:-1, avg,
          MathAbs(v)*UsdPerLot(g_micro_sym, avg));
      first=false;
     }
   return js+"]";
  }

void WriteState(bool force)
  {
   if(!force && TimeCurrent()-g_last_state_write<60) return;
   g_last_state_write=TimeCurrent();
   double eq=AccountInfoDouble(ACCOUNT_EQUITY);
   double bal=AccountInfoDouble(ACCOUNT_BALANCE);
   double margin=AccountInfoDouble(ACCOUNT_MARGIN);
   double age_h=-1;
   if(TargetsRead()) age_h=TargetsAgeH();
   string sspecs="{";
   for(int k=0;k<N_LEGS;k++)
      sspecs+=StringFormat("\"%s\":{\"tick_value\":%.6f,\"tick_size\":%.6f,\"price\":%.5f}%s",
          g_legs[k], SymbolInfoDouble(g_sym[k], SYMBOL_TRADE_TICK_VALUE),
          SymbolInfoDouble(g_sym[k], SYMBOL_TRADE_TICK_SIZE), MidPrice(g_sym[k]),
          k<N_LEGS-1?",":"}");
   string phase_s=InpPhase==1?"P1":(InpPhase==2?"P2":"FUNDED");
   double wd_due=0.0;
   if(InpPhase==3 && g_wd_tdays>0 && g_wd_tdays%FU_WD_EVERY_TDAYS==0
      && bal>ACCOUNT_SIZE_USD)
      wd_due=bal-ACCOUNT_SIZE_USD;
   string js="{\n";
   js+="\"schema\": \"ftmo_live.state.v1\",\n";
   js+="\"ts_server\": \""+TsServer()+"\",\n";
   js+="\"ts_paris\": \""+TsParis()+"\",\n";
   js+="\"phase\": \""+phase_s+"\",\n";
   js+="\"attempt_start\": \""+TimeToString(InpAttemptStart, TIME_DATE)+"\",\n";
   js+=StringFormat("\"equity\": %.2f,\n\"balance\": %.2f,\n", eq, bal);
   js+=StringFormat("\"anchor_balance\": %.2f,\n\"anchor_date\": \"%s\",\n",
       g_anchor_balance, g_anchor_date);
   js+=StringFormat("\"daily_floor\": %.2f,\n\"static_floor\": %.2f,\n"
       "\"breaker_line\": %.2f,\n", DailyFloor(), StaticFloor(), BreakerLine());
   js+=StringFormat("\"room_daily_usd\": %.2f,\n\"target_equity\": %.2f,\n",
       eq-LimEff(), InpPhase==3 ? 0.0 : TargetEq());
   js+=StringFormat("\"breaker_fired_today\": %d,\n\"opened_today\": %d,\n"
       "\"flat_today\": %d,\n", g_breaker_today?1:0, g_opened_today?1:0, g_flat_today?1:0);
   js+=StringFormat("\"open_days\": %d,\n\"min_days\": %d,\n", g_open_days, MIN_TRADING_DAYS);
   js+=StringFormat("\"margin_used_pct_equity\": %.1f,\n", eq>0 ? margin/eq*100.0 : 0.0);
   js+=StringFormat("\"micro_state\": %d,\n\"micro_enabled\": %d,\n",
       g_micro_state, MicroEnabled()?1:0);
   js+=StringFormat("\"micro_or_hi\": %.2f,\n\"micro_or_lo\": %.2f,\n\"micro_be\": %d,\n",
       g_or_hi, g_or_lo, g_micro_be?1:0);
   js+=StringFormat("\"targets_age_h\": %.2f,\n\"targets_status\": \"%s\",\n",
       age_h, g_targets_status);
   js+=StringFormat("\"mode_mismatch\": %d,\n\"kill\": %d,\n",
       g_mode_mismatch?1:0, g_killed?1:0);
   js+=StringFormat("\"abandon_zombie_days\": %d,\n", g_zombie_days);
   js+=StringFormat("\"pending_unconfirmed\": %d,\n", g_pending_unconfirmed);
   js+=StringFormat("\"spec_bounds_breach\": %d,\n", g_spec_breach?1:0);
   js+="\"spec_bounds_detail\": \""+g_spec_breach_detail+"\",\n";
   string lspec="{";
   for(int k=0;k<N_LEGS;k++)
      lspec+=StringFormat("\"%s\":{\"swap_long\":%.4f,\"swap_short\":%.4f,"
            "\"r3d\":%d,\"margin_rate\":%.6f}%s", g_legs[k], g_live_swl[k],
            g_live_sws[k], g_live_r3d[k], g_live_mrate[k], k<N_LEGS-1?",":"}");
   js+="\"live_specs\": "+lspec+",\n";
   js+=StringFormat("\"wd_due_usd\": %.2f,\n\"trading_days_since_wd\": %d,\n",
       wd_due, InpPhase==3 ? g_wd_tdays%FU_WD_EVERY_TDAYS : 0);
   js+=StringFormat("\"governor\": {\"taper\": %.4f, \"glide\": %.2f, \"pace\": %.4f, "
       "\"scale\": %.4f, \"vm\": %.2f},\n", GovTaper(eq), Glide(eq), Pace(eq),
       Scale(eq), VmEff());
   js+="\"symbol_specs\": "+sspecs+",\n";
   js+="\"positions\": "+PositionsJson()+",\n";
   if(g_last_rebalance!="") js+="\"last_rebalance\": "+g_last_rebalance+",\n";
   if(g_done_2258)
      js+="\"eod\": {\"date\": \""+ParisDate()+"\","
          +StringFormat("\"balance\": %.2f, \"equity\": %.2f,", bal, eq)
          +"\"positions\": "+PositionsJson()+"},\n";
   js+="\"last_error\": \""+g_last_error+"\",\n";
   js+=StringFormat("\"spec_sha\": \"%s\",\n\"heartbeat_epoch\": %d\n",
       SPEC_SHA256, (int)TimeCurrent());
   js+="}\n";
   AtomicWrite("state.json", js);
  }

double JjsNum(string txt, string key)
  {
   int i=StringFind(txt, "\""+key+"\":");
   if(i<0) return 0.0;
   int c=StringFind(txt, ":", i);
   int e1=StringFind(txt, ",", c);
   int e2=StringFind(txt, "}", c);
   int e=(e1<0) ? e2 : ((e2<0) ? e1 : MathMin(e1, e2));
   string v=StringSubstr(txt, c+1, e-c-1);
   StringReplace(v, "\"", "");
   return StringToDouble(v);
  }
string JjsStr(string txt, string key)
  {
   int i=StringFind(txt, "\""+key+"\":");
   if(i<0) return "";
   int q1=StringFind(txt, "\"", StringFind(txt, ":", i)+1);
   if(q1<0) return "";
   int q2=StringFind(txt, "\"", q1+1);
   return StringSubstr(txt, q1+1, q2-q1-1);
  }

void SaveState()
  {
   string js=StringFormat(
      "{\"anchor_balance\":%.2f,\"anchor_date\":\"%s\",\"opened_today\":%d,"
      "\"flat_today\":%d,\"breaker_today\":%d,\"open_days\":%d,\"zombie\":%d,"
      "\"wd_tdays\":%d,\"micro_state\":%d,\"or_hi\":%.5f,\"or_lo\":%.5f,"
      "\"or_end_close\":%.5f,\"micro_entry\":%.5f,\"micro_be\":%d,"
      "\"d09\":%d,\"d1530\":%d,\"dor\":%d,\"d16\":%d,\"d1735\":%d,\"d2130\":%d,"
      "\"d2145\":%d,\"d22\":%d,\"d2205\":%d,\"d2258\":%d,\"exit_scan\":%d}",
      g_anchor_balance, g_anchor_date, g_opened_today?1:0, g_flat_today?1:0,
      g_breaker_today?1:0, g_open_days, g_zombie_days, g_wd_tdays, g_micro_state,
      g_or_hi, g_or_lo, g_or_end_close, g_micro_entry, g_micro_be?1:0,
      g_done_0900?1:0, g_done_1530?1:0, g_done_or?1:0, g_done_1600?1:0,
      g_done_1735?1:0, g_done_2130?1:0, g_done_2145?1:0, g_done_2200?1:0,
      g_done_2205?1:0, g_done_2258?1:0, (int)g_exit_scan_from);
   AtomicWrite("ea_state.json", js);
  }

void LoadState()
  {
   int h=FileOpen("ea_state.json", FILE_READ|FILE_TXT|FILE_ANSI|FILE_SHARE_READ);
   if(h==INVALID_HANDLE) return;
   string txt="";
   while(!FileIsEnding(h)) txt+=FileReadString(h)+"\n";
   FileClose(h);
   if(JjsStr(txt, "anchor_date")!=ParisDate()) return;   // autre jour: rollover gérera
   g_anchor_balance=JjsNum(txt, "anchor_balance");
   g_anchor_date   =JjsStr(txt, "anchor_date");
   g_opened_today  =JjsNum(txt, "opened_today")>0.5;
   g_flat_today    =JjsNum(txt, "flat_today")>0.5;
   g_breaker_today =JjsNum(txt, "breaker_today")>0.5;
   g_open_days     =(int)JjsNum(txt, "open_days");
   g_zombie_days   =(int)JjsNum(txt, "zombie");
   g_wd_tdays      =(int)JjsNum(txt, "wd_tdays");
   g_micro_state   =(int)JjsNum(txt, "micro_state");
   g_or_hi         =JjsNum(txt, "or_hi");
   g_or_lo         =JjsNum(txt, "or_lo");
   g_or_end_close  =JjsNum(txt, "or_end_close");
   g_micro_entry   =JjsNum(txt, "micro_entry");
   g_micro_be      =JjsNum(txt, "micro_be")>0.5;
   g_done_0900=JjsNum(txt,"d09")>0.5;   g_done_1530=JjsNum(txt,"d1530")>0.5;
   g_done_or  =JjsNum(txt,"dor")>0.5;   g_done_1600=JjsNum(txt,"d16")>0.5;
   g_done_1735=JjsNum(txt,"d1735")>0.5; g_done_2130=JjsNum(txt,"d2130")>0.5;
   g_done_2145=JjsNum(txt,"d2145")>0.5; g_done_2200=JjsNum(txt,"d22")>0.5;
   g_done_2205=JjsNum(txt,"d2205")>0.5; g_done_2258=JjsNum(txt,"d2258")>0.5;
   g_exit_scan_from=(datetime)(long)JjsNum(txt,"exit_scan");
  }

//+------------------------------------------------------------------+
//| Lifecycle                                                          |
//+------------------------------------------------------------------+
int OnInit()
  {
   if(!SpecHashOK())
     {
      Print("INIT REFUSÉ: MQL5/Files/spec_v22.sha256 absent ou != SPEC_SHA256");
      return INIT_FAILED;
     }
   if(InpPhase<1 || InpPhase>3) { Print("InpPhase invalide"); return INIT_FAILED; }
   if(InpPhase!=3 && InpAttemptStart==0)
     { Print("InpAttemptStart REQUIS en challenge (ancre pace)"); return INIT_FAILED; }
   g_micro_sym=(InpSymUS100=="") ? MICRO_ORB_SYMBOL : InpSymUS100;
   g_sym[0]=InpSymXAU; g_sym[1]=InpSymJPY; g_sym[2]=g_micro_sym; g_sym[3]=InpSymGER40;
   g_mrate[0]=MRATE_XAUUSD; g_mrate[1]=MRATE_USDJPY;
   g_mrate[2]=MRATE_US100;  g_mrate[3]=MRATE_GER40;
   for(int k=0;k<N_LEGS;k++)
      if(!SymbolSelect(g_sym[k], true))
        { Print("Symbole introuvable: ", g_sym[k]); return INIT_FAILED; }
   InitAnchors();
   ReadLiveSpecs();                  // v2.2.1: specs live + bornes dès l'init
   LoadState();
   if(g_anchor_date=="")
     {
      g_anchor_balance=AccountInfoDouble(ACCOUNT_BALANCE);
      g_anchor_date=ParisDate();
      SaveState();
     }
   EventSetTimer(1);
   Print(StringFormat("book_executor v2.2 INIT — phase %d, serveur−Paris %d min, "
         "vm_eff %.1f, micro %s, magic %d", InpPhase, InpServerTZOffsetMin, VmEff(),
         MicroEnabled()?"ON":"OFF", (int)InpMagicBase));
   WriteState(true);
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason) { EventKillTimer(); WriteState(true); }

void OnTimer()
  {
   if(FileIsExist("FLAT"))                              // kill-file: flatten + disable
     {
      if(!g_killed)
        {
         g_killed=true;
         FlattenAll("kill_flat");
         SetError("kill-file FLAT — EA désarmé");
        }
      ConfirmPendings();
      WriteState(false);
      return;
     }
   g_killed=false;

   if(ParisDate()!=g_anchor_date) DayRollover();

   ConfirmPendings();
   DetectServerExits();
   BackstopCloseIfDue();

   if(!IsWeekend())
     {
      MqlDateTime p; ParisStruct(p);
      long slot=(long)(ParisNow()/300);
      if(p.min%5==0 && slot!=g_last_m5_slot)            // grille M5 (sémantique sim)
        {
         g_last_m5_slot=slot;
         InvariantCheckM5();
        }
      MicroManage();

      int hm=ParisHM();
      if(hm>=900  && !g_done_0900) { g_done_0900=true; Do0900(); SaveState(); }
      if(hm>=1530 && !g_done_1530) { g_done_1530=true; Do1530(); SaveState(); }
      if(hm>=1600 && !g_done_or)   { g_done_or=true;   DoBuildOR(); }
      if(hm>=1600 && hm<2000 && g_done_or && !g_done_1600)
        { g_done_1600=true; Do1600Arm(); }
      if(hm>=1735 && hm<2130 && !g_done_1735) { g_done_1735=true; Do1735(); SaveState(); }
      if(hm>=2130 && !g_done_2130) { g_done_2130=true; Do2130Backstop(); SaveState(); }
      if(hm>=2145 && !g_done_2145) { g_done_2145=true; Do2145Export(); }
      if(hm>=2200 && !g_done_2200) { g_done_2200=true; Do2200TimeStop(); }
      if(hm>=2205 && hm<2330 && !g_done_2205) { g_done_2205=true; Do2205Rebalance(); }
      if(hm>=2258 && !g_done_2258) { g_done_2258=true; Do2258EOD(); SaveState(); }
     }
   WriteState(false);
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   // détection passive — la vérité vient des scans (jamais Result*)
   if(trans.type==TRADE_TRANSACTION_DEAL_ADD)
     {
      ConfirmPendings();
      DetectServerExits();
     }
  }
