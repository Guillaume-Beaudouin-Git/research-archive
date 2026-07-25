"""Génère spec_v22.mqh (constantes EA + hash embarqué) + spec_v22.sha256 (MQL5/Files)
DEPUIS spec_v22.yaml exclusivement (via brain.load = hash-pin + drift-check).

Déterministe (zéro timestamp) → régénération byte-identique = ancre #20.
Zéro constante manuelle: tout vient du yaml; l'EA asserte à l'init que le fichier
MQL5/Files/spec_v22.sha256 == SPEC_SHA256 embarqué (SpecHashOK()).
"""
import sys, hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import brain

spec = brain.load()
ch = brain.challenge_cfg(spec)
fu = brain.funded_cfg(spec)
mo = brain.micro_orb(spec)
ru = brain.rules(spec)
sc = brain.schedule_cet(spec)
mg = brain.margin(spec)
g = spec["challenge"]["sleeves"]["gold_trend"]
acct = spec["account"]

def f(x): return f"{float(x):g}"

# ---- v2.2.1: bornes de sanité DATÉES depuis measured_specs (data-only) ----
ms = spec["measured_specs"]
LEGS4 = ("XAUUSD", "USDJPY", "US100", "GER40")
sanity_lines = []
for s in LEGS4:
    m = ms["symbols"][s]
    mql_dow = (int(m["triple_dow"]) + 1) % 7        # python lun=0 -> MQL5 dim=0
    sanity_lines += [
        f"#define ANCHOR_SWL_{s}     ({m['swap_long_pts']:g})",
        f"#define ANCHOR_SWS_{s}     ({m['swap_short_pts']:g})",
        f"#define ANCHOR_R3D_{s}     {mql_dow}   // ENUM_DAY_OF_WEEK",
        f"#define MARGIN_STD_{s}     {ms['margin_rates']['standard_measured'][s]:.6f}",
        f"#define MARGIN_SWING_{s}   {ms['margin_rates']['swing_official'][s]:.6f}",
        # v2.8 : TROISIÈME ancre = marge Swing réellement mesurée sur le compte armé.
        # La borne de sanité EA teste les trois ; MARGIN_SWING_ (officiel) reste le
        # fallback CONSERVATEUR de MarginRateEff, donc l'enforcement est inchangé.
        f"#define MARGIN_MEAS_{s}    {ms['margin_rates']['swing_measured'][s]:.6f}",
    ]
SANITY_BLOCK = "\n".join(sanity_lines)

# ---- v2.8 : overlay risque leg_leverage_cap (0 = pas de cap) ----
_ro = (spec.get("risk_overlays") or {}).get("leg_leverage_cap") or {}
_ro_on = bool(_ro.get("enabled"))
_ro_caps = _ro.get("caps") or {}
# L'EA n'a AUCUNE notion de phase : les #define sont les mêmes en challenge et en
# funded. Le Python, lui, respecte `applies_to` (lib/spec.py::leg_lev_cap_vector).
# Restreindre applies_to à une seule phase ferait donc diverger SILENCIEUSEMENT le
# modèle et l'EA sur l'autre. Fail-loud plutôt que divergence silencieuse : si ce
# besoin apparaît, il faudra câbler InpPhase dans LegLevCap(), pas contourner ici.
if _ro_on and sorted(_ro.get("applies_to") or []) != ["challenge", "funded"]:
    raise SystemExit(
        "make_spec_mqh: risk_overlays.leg_leverage_cap.applies_to = "
        f"{_ro.get('applies_to')!r} — l'EA ne sait pas distinguer les phases, il "
        "appliquerait le cap aux DEUX. Câbler InpPhase dans LegLevCap() avant de "
        "restreindre applies_to.")


def _legcap(s):
    v = _ro_caps.get(s)
    return "0" if (not _ro_on or v is None) else f"{float(v):g}"


LEGCAP_BLOCK = "\n".join(
    f"#define LEG_LEV_CAP_{s}   {_legcap(s)}" for s in LEGS4)

mqh = f"""//+------------------------------------------------------------------+
//| spec_v22.mqh — GÉNÉRÉ depuis spec_v22.yaml par make_spec_mqh.py  |
//| NE PAS ÉDITER À LA MAIN (ancre #20: régénération byte-identique). |
//| Pins: {brain.PIN_COMMITS['v22_contract'][:7]} + {brain.PIN_COMMITS['v22_residuals'][:7]} + {brain.PIN_COMMITS['v22_spec_yaml'][:7]} ; yaml sha {brain.PIN_SHA256[:8]}…            |
//+------------------------------------------------------------------+
#define SPEC_VERSION        "{spec['meta']['version']}"
#define SPEC_SHA256         "{brain.PIN_SHA256}"
#define SPEC_PIN_CONTRACT   "{brain.PIN_COMMITS['v22_contract']}"
#define SPEC_PIN_RESIDUALS  "{brain.PIN_COMMITS['v22_residuals']}"
#define SPEC_PIN_YAML       "{brain.PIN_COMMITS['v22_spec_yaml']}"

// ---- compte & règles FTMO (2-step Swing $10k) ----
#define ACCOUNT_SIZE_USD    {f(acct['size_usd'])}
#define DAILY_LOSS_FRAC     0.05      // equity >= balance@00:00 Prague - 5% initial
#define MAX_LOSS_FRAC       0.10      // floor statique = 90% initial
#define TARGET_P1           {f(ru['targets']['phase1'])}
#define TARGET_P2           {f(ru['targets']['phase2'])}
#define MIN_TRADING_DAYS    {ru['min_trading_days']}
#define WALL_DAYS           {acct['mission_wall_days']}
#define GAP_BDAYS           {ru['inter_phase_gap_bdays']}
#define RETRY_BDAYS         {ru['retry_gap_bdays']}

// ---- horaires SPEC en CET (mapper au fuseau serveur via input EA, ne pas convertir ici) ----
#define SCHED_GER40_EXIT_CET    "{sc['ger40_exit']}"
#define SCHED_US100_EXIT_CET    "{sc['us100_exit']}"
#define SCHED_GER40_ENTRY_CET   "{sc['ger40_entry_if_on']}"
#define SCHED_REBALANCE_CET     "{sc['rebalance_and_us100_entry']}"

// ---- challenge (P1/P2) ----
#define CH_VM               {f(ch['vm'])}
#define CH_P2_MULT          {f(ch['p2_mult'])}
#define CH_ON_W             {f(ch['on_w'])}
#define CH_ORB_RISK         {f(ch['orb_risk'])}   // v2.2: ORB OFF comme sleeve P&L
#define CH_MICRO_ORB        {str(ch['micro_orb']).lower()}
#define CH_BREAKER_FRAC     {f(ch['breaker'])}
#define CH_TAPER            {f(ch['taper'])}
#define CH_GLIDE            {f(ch['glide'])}
#define CH_PACE_ON          {ch['pace']}
#define CH_PACE_K           {f(ch['pace_k'])}
#define CH_ABANDON_BUF      {f(ch['ab_buf'])}
#define CH_ABANDON_DAYS     {ch['ab_days']}
#define CH_MARGIN_CAP       {f(mg['cap_of_equity'])}
#define MRATE_XAUUSD        {f(mg['rates']['XAUUSD'])}
#define MRATE_USDJPY        {f(mg['rates']['USDJPY'])}
#define MRATE_US100         {f(mg['rates']['US100'])}
#define MRATE_GER40         {f(mg['rates']['GER40'])}
#define LOT_STEP            0.01
#define LEG_CAP_PRE_VM      {f(g['leg_cap_pre_vm'])}

// ---- v2.8 : cap de NOTIONNEL par jambe (risk_overlays.leg_leverage_cap) ----
// Unité = notionnel/equity, INVARIANTE EN vm. Appliqué AVANT le cap marge.
// 0 = pas de cap. À NE PAS confondre avec LEG_CAP_PRE_VM ci-dessus (garde-fou
// anti-lot-aberrant à 42x eq, libellé pre-vm donc suiveur de vm).
{LEGCAP_BLOCK}

// ---- MICRO-ORB = LE compteur de jours (bloc micro_orb_day_counter du yaml) ----
// entrée canonique post-OR (OR 15:30-16:00 CET, fill premier bar 5min post-OR);
// sorties V2+E7: stop = côté opposé OR (1R), trail-to-BE après +1R, time-stop 22:00 CET;
// CONDITION: posté seulement si AUCUN autre trade ouvert à 21:30 CET (flag opened, sémantique 605f4a4);
// backstop no-signal (fallback RARE, 50/13068 jours sim): open/close 0.01 lot si
//   aucun signal ORB ET rien d'ouvert ET min-days non atteint ET balance >= cible.
#define MICRO_ORB_SYMBOL    "{mo['instrument']}"
#define MICRO_ORB_LOTS      {f(mo['size_lots'])}
#define MICRO_OR_START_CET  "15:30"
#define MICRO_OR_END_CET    "16:00"
#define MICRO_TIMESTOP_CET  "22:00"
#define MICRO_COND_CET      "21:30"

// ---- funded (switch au funding, même événement que vm14->1.0) ----
#define FU_VM               {f(fu['vm'])}
#define FU_ON_W             {f(fu['on_w'])}
#define FU_ORB_RISK         {f(fu['orb_risk'])}   // ORB ON full spec
#define FU_MICRO_ORB        {str(fu['micro_orb']).lower()}
#define FU_WD_EVERY_TDAYS   {spec['funded']['withdrawals']['every_trading_days']}
#define FU_SPLIT_TRADER     {f(spec['funded']['withdrawals']['split_trader'])}
#define ORB_RT_BPS          "{spec['funded']['ORB_RT_BPS']['value']}"  // era jusqu'au verdict 2026-06-15

// ---- signaux (côté brain; embarqués pour complétude, zéro constante manuelle) ----
#define GOLD_LOOKBACKS      "60,120,250"
#define GOLD_THETA          0.34
#define GOLD_VOL_TARGET     {f(g['vol_target_inst'])}
#define J1_SIGNAL           "12-1 momentum LO (p[t-21]/p[t-252]-1 > 0)"
#define ON_NIGHTS           "Mon,Tue"

// ---- v2.2.1 bornes de sanité DATÉES (specs mesurées, source compte Standard) ----
// L'EA lit SYMBOL_SWAP_LONG/SHORT, SYMBOL_SWAP_ROLLOVER3DAYS et la marge live
// (OrderCalcMargin) à l'init + au rebalance ; hors borne -> ALERTE (state).
// Marge SWING officielle (fx 1:30, indices 1:15, métaux 1:9) À CONFIRMER sur
// les specs du serveur Swing au déploiement — gate bloquant (recost_v221).
#define SANITY_READ_DATE    "{ms['read_date']}"
#define SANITY_SOURCE       "{ms['source']}"
#define SANITY_SWAP_REL     {f(ms['bounds_rel']['swap'])}
#define SANITY_MARGIN_REL   {f(ms['bounds_rel']['margin'])}
{SANITY_BLOCK}

//+------------------------------------------------------------------+
//| Assert d'init: MQL5/Files/spec_v22.sha256 doit == SPEC_SHA256.    |
//| Refus de trader si absent ou différent (zéro constante manuelle). |
//+------------------------------------------------------------------+
bool SpecHashOK()
  {{
   int h = FileOpen("spec_v22.sha256", FILE_READ|FILE_TXT|FILE_ANSI);
   if(h == INVALID_HANDLE)
     {{ Print("SPEC ASSERT FAIL: MQL5/Files/spec_v22.sha256 absent"); return(false); }}
   string s = FileReadString(h);
   FileClose(h);
   StringTrimLeft(s); StringTrimRight(s);
   if(s != SPEC_SHA256)
     {{ Print("SPEC ASSERT FAIL: hash fichier ", s, " != embarqué ", SPEC_SHA256); return(false); }}
   Print("SPEC OK ", SPEC_VERSION, " sha ", StringSubstr(SPEC_SHA256, 0, 12), "…");
   return(true);
  }}
"""

out = HERE / "spec_v22.mqh"
out.write_text(mqh)
(HERE / "spec_v22.sha256").write_text(brain.PIN_SHA256 + "\n")
sha_mqh = hashlib.sha256(mqh.encode()).hexdigest()
print(f"spec_v22.mqh written ({len(mqh)} bytes) + spec_v22.sha256 (déposer dans MQL5/Files)")
print(f"mqh sha256: {sha_mqh}")
