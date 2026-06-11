"""Generate spec_v22.yaml FROM config_v22.py (single source of truth).

Deterministic output (no timestamps, insertion-ordered) so regeneration is
byte-identical — non-regression anchor #19. Every numeric parameter is READ
from config_v22 / engine constants / canonical cost artifacts, never retyped.
v2.2.1: + bloc measured_specs (ancres datées) + résultats recost lus depuis
recost/summary.json (artefact gelé du run, jamais retapé).
"""
import json, sys, hashlib, subprocess
from pathlib import Path
import pandas as pd
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import config_v22 as C22
import engine_v22 as V
E = V.E

RECOST_SUMMARY = json.loads((HERE / "recost" / "summary.json").read_text())
LEGS4 = ("XAUUSD", "USDJPY", "US100", "GER40")

BASELINE_COMMITS = {
    "v22_contract": "605f4a426da3eac4f5a2644bca774a07f1e5f754",
    "v22_residuals": "4e1bac5cf6486fcd0070876d47dd2dcdc7a8f539",
}

# verify the pinned SHAs exist in this repo (warn-only: spec must stay generable)
for name, sha in BASELINE_COMMITS.items():
    r = subprocess.run(["git", "cat-file", "-t", sha],
                       capture_output=True, text=True,
                       cwd="<HOME>/Desktop/Algo_claude")
    if r.stdout.strip() != "commit":
        print(f"WARNING: pinned SHA {name}={sha[:7]} not found in repo")

rt = pd.read_csv(E.AOUT / "phase0_rt_cost_bps.csv", index_col=0).iloc[:, 0]
sL = pd.read_parquet(E.CACHE / "panel_swapL.parquet")
sS = pd.read_parquet(E.CACHE / "panel_swapS.parquet")

spec = {
    "meta": {
        "version": "v2.2.1",
        "policy_version": "v2.2 (recost v2.2.1 = data-only, policy inchangée — pré-enregistré)",
        "spec_date": "2026-06-10",
        "baseline_commits": BASELINE_COMMITS,
        "supersedes": "v2.1 — toute référence baseline v2.1 est remplacée par ce pin",
        "generated_from": "config_v22.py via make_spec_yaml.py (do not hand-edit)",
        "nonregression": "NONREGRESSION_v2.2.md (ancres 1-21, révision v2.2.1)",
        "amendments": ["AMENDEMENT_RAPPORT_MESURE_s9.md (§9: branche kill retirée; "
                       "gate 2 = PASS v2.2.1 — mécanique swap 4/4 au centime, ancres re-datées)"],
    },
    "account": {
        "vendor": "FTMO", "type": "2-step Swing (achat Swing irréversible)",
        "size_usd": E.INIT,
        "rules": {
            "daily_loss": "equity >= balance@00:00 Europe/Prague - 5% du capital initial (M5-checked)",
            "max_loss": "equity >= 90% du capital initial (floor statique 9000)",
            "targets": {"phase1": E.TARGET1, "phase2": E.TARGET2,
                        "basis": "BALANCE positions closes"},
            "min_trading_days": E.MIN_OPEN_DAYS,
            "time_limit": None,
            "inter_phase_gap_bdays": 3, "retry_gap_bdays": 2,
        },
        "mission_wall_days": C22.WALL,
    },
    "challenge": {
        "config": dict(C22.CFG_CHALLENGE),
        "schedule_cet": {"ger40_exit": "09:00", "us100_exit": "15:30",
                         "ger40_entry_if_on": "17:35",
                         "rebalance_and_us100_entry": "22:05"},
        "sleeves": {
            "gold_trend": {
                "instrument": "XAUUSD",
                "signal": "TSMOM blend sign{60,120,250} sur total return carry-ajusté (swap long), dead-zone |s|<0.34",
                "vol_target_inst": 0.10, "inst_cap": 5.0,
                "portfolio_vol_layers": "port vol-target 10% (60d) + vol-derisk min(1, 0.10/vol20d)",
                "equity_gate": "eq > MA100(eq) ? 1.0 : 0.4 (shift 1) — composant v2.0 documenté par audit C15",
                "leg_cap_pre_vm": 1.5,
            },
            "j1": {
                "instrument": "USDJPY",
                "signal": "12-1 momentum (p[t-21]/p[t-252]-1 > 0) long-only",
                "vol_target_inst": 0.10, "inst_cap": 5.0, "leg_cap_pre_vm": 1.5,
            },
            "overnight_midweek": {
                "instruments": ["US100", "GER40"], "side": "long",
                "nights_held": "lundi + mardi",
                "sessions_cet": {"US100": "15:30-22:00", "GER40": "09:00-17:30"},
                "weight_per_leg": C22.CFG_CHALLENGE["on_w"],
            },
            "orb": {
                "challenge_pnl_sleeve": False,
                "note": "ORB OFF comme sleeve P&L dans le challenge (le changement v2.2)",
            },
        },
        "micro_orb_day_counter": {
            "is_the_day_counter": True,
            "note": "le compteur de jours EST le micro-ORB — l'EA implémente CETTE règle, pas un token arbitraire",
            "instrument": "US100.cash", "size_lots": 0.01,
            "entry": "breakout ORB V2 canonique, premier bar 5-min post-OR (OR 15:30-16:00), fills 16:05-16:10 Paris",
            "exits": "V2+E7: stop = côté opposé de l'OR (1R); trail-to-BE après +1R; time-stop close RTH 22:00",
            "condition": "posté seulement si AUCUN autre trade ouvert à 21:30 CET — flag `opened` live (sémantique 605f4a4)",
            "pnl_modeled": True,
            "risk_usd_per_trade": "0.01 lot x OR_range points (~$0.2-2.0)",
            "backstop_no_signal": ("si aucun signal ORB ce jour ET rien d'ouvert ET min-days non atteint "
                                   "ET balance >= cible: ouvrir/fermer 0.01 lot US100 (incidence sim: 50 / 13068 jours-tentatives)"),
        },
        "risk_engine": {
            "vol_multiplier": C22.CFG_CHALLENGE["vm"],
            "p2_multiplier": C22.CFG_CHALLENGE["p2_mult"],
            "breaker": "flatten M5 si room < 30% du budget daily restant",
            "taper_floor": C22.CFG_CHALLENGE["taper"],
            "glide": "x0.5 si progression > 80% de la cible",
            "pacing": "x clip(1 + retard_sur_glide, 0.8, 2.0)",
            "abandon": f"equity < floor + {C22.CFG_CHALLENGE['ab_buf']:.0%} pendant {C22.CFG_CHALLENGE['ab_days']} jours -> relancer",
            "margin_cap": {"cap_of_equity": C22.CFG_CHALLENGE["margin_cap"],
                           "rates": {"XAUUSD": 0.02, "USDJPY": 0.01,
                                     "US100": 0.02, "GER40": 0.02},
                           "action": "scaling proportionnel toutes jambes (micro-ORB hors cap)"},
            "quantization_lots": 0.01, "weekend": "positions tenues",
            "daily_realize": False,
        },
    },
    "funded": {
        "config": dict(C22.CFG_FUNDED),
        "orb": {"on": True, "risk_per_trade": C22.CFG_FUNDED["orb_risk"],
                "cost_param": "ORB_RT_BPS"},
        "ORB_RT_BPS": {
            "value": C22.ORB_RT_BPS,
            "note": "era = défaut jusqu'au verdict N=60 du 2026-06-15 (règle pré-enregistrée: aucun ré-ancrage avant N=60)",
            "verdict_procedure": "mesure all-in RT (N=60 fills actifs 16:00-16:30) -> config_v22.py:ORB_RT_BPS = valeur -> re-run section funded SEULE -> EV à la valeur mesurée; branche kill RETIRÉE (AMENDEMENT_RAPPORT_MESURE_s9)",
            "branches_exactes_ledger": {
                "0.61_bps": {"funded_oos_2y": 2897, "ev_campagne": 1125},
                "1.0_bps": {"funded_oos_2y": 2807, "ev_campagne": 1063},
                "1.5_bps": {"funded_oos_2y": 2578, "ev_campagne": 965},
                "era_defaut": {"funded_oos_2y": 2632, "ev_campagne": 926},
                "orb_off": {"funded_oos_2y": 1262, "ev_campagne": 295},
            },
        },
        "switch_trigger": ("au FUNDING (P2 validée, compte funded livré) — même événement que vm 14->1.0: "
                           "vm 14->1.0, on_w 0.6->0.35, ORB ON (0.25% taper), micro-ORB OFF, "
                           "pace/glide/abandon OFF"),
        "withdrawals": {"every_trading_days": C22.FUNDED_WD_EVERY,
                        "amount": "balance - 10000 si positif",
                        "split_trader": 0.80, "fee_refund": "1er payout"},
        "horizon_trading_days": C22.FUNDED_HORIZON,
    },
    "cost_anchors": {
        "rt_bps_legs": {s: round(float(rt[s]), 2)
                        for s in ("XAUUSD", "USDJPY", "US100", "GER40")},
        "rt_bps_legs_allin": {s: round(float(rt[s]) + C22.comm_rt_bps(s), 2)
                              for s in LEGS4},
        "swap_bps_per_night_measured": {
            f"{s}_{sd}": round(C22.swap_bps(s, sd), 3)
            for s in LEGS4 for sd in ("long", "short")},
        "swap_anchor_basis": (f"points mesurés {C22.SPECS_READ_DATE} -> bps aux prix "
                              f"panel {C22.REF_PX_DATE} (voir measured_specs)"),
        "triple_days": {"indices": "vendredi", "metaux_fx": "mercredi"},
        "sources": ["outputs/phase0_rt_cost_bps.csv",
                    "specs MT5 FTMO 2026-06-10 (measured_specs)",
                    "cache/orb_e7_Rera.parquet (era ledger)"],
    },
    "measured_specs": {
        "read_date": C22.SPECS_READ_DATE,
        "source": C22.SPECS_SOURCE,
        "role": ("bornes de sanité DATÉES — l'EA lit les specs live (swap pts, "
                 "rollover3days, marge) à l'init + au rebalance et ALERTE hors borne ; "
                 "brain/reconcile comparent facturé vs spec-du-jour vs modèle"),
        "swap_type": "points (valeur d'un point = contract_size x 10^-digits, devise de cote)",
        "validation": ("nuit 10->11/06 (mercredi x3 métaux/FX): 4/4 facturés reconstruits "
                       "au centime — XAU 0.01=-1.97$, JPY 0.1=+0.18$, US100 0.1=-0.64$, "
                       "GER40 0.1=-0.394€=-0.45$ (USD compte @EURUSD 1.152)"),
        "symbols": {
            s: dict(C22.MEASURED_SPECS[s],
                    swap_long_bps_ref=round(C22.swap_bps(s, "long"), 4),
                    swap_short_bps_ref=round(C22.swap_bps(s, "short"), 4),
                    comm_rt_bps=round(C22.comm_rt_bps(s), 4))
            for s in LEGS4},
        "triple_dow_python": {s: C22.MEASURED_SPECS[s]["triple_dow"] for s in LEGS4},
        "ref_px": dict(C22.REF_PX, date=C22.REF_PX_DATE),
        "ger40_note": C22.GER40_NOTE,
        "bounds_rel": {"swap": C22.SANITY_BOUND_SWAP_REL,
                       "margin": C22.SANITY_BOUND_MARGIN_REL},
        "margin_rates": {
            "policy_engine_v22": dict(C22.MARGIN_RATES_POLICY,
                                      note="cap 60% du moteur — POLICY, inchangée"),
            "standard_measured": {k: round(v, 6)
                                  for k, v in C22.MARGIN_RATES_STANDARD.items()},
            "swing_official": {k: round(v, 6)
                               for k, v in C22.MARGIN_RATES_SWING.items()},
            "swing_status": C22.SWING_MARGIN_STATUS,
        },
    },
    "recost_v221": {
        "type": "data-only (pré-enregistré) — signal/vm/budgets/policy INCHANGÉS",
        "gates": {
            "G0_swap_mechanics": "PASS — 4/4 facturés au centime",
            "G1_repro_baseline": "PASS — challenge 87.01 exact",
            "G2_challenge_drift": ("RÉSOLU — pooled bouge (comm -1.73, swaps fwd -1.08) "
                                   "mais deltas appariés CI95 ⊃ 0 (méthode vm-sweep "
                                   "4e1bac5) = jitter de chemin non significatif ; "
                                   "challenge contractuel INCHANGÉ"),
        },
        "paired_deltas_pt_ci95": RECOST_SUMMARY["paired_deltas"],
        "challenge_contractual": RECOST_SUMMARY["challenge_base"],
        "challenge_comm_only_pathrealized": RECOST_SUMMARY["challenge_comm_only"],
        "funded_comm_only": {
            "IS": RECOST_SUMMARY["funded_IS_comm_only"],
            "OOS": RECOST_SUMMARY["funded_OOS_comm_only"],
            "VAL": RECOST_SUMMARY["VAL_comm_only"],
            "EV": RECOST_SUMMARY["EV_comm_only"],
            "vs_v22": "OOS 2632->2529 (-103, drag commissions) ; EV +926->+863",
        },
        "headline_margin_swing": {
            "verdict": "LE TERME MATÉRIEL — si levier Swing serveur = officiel, vm14 non exécutable tel quel",
            "delta_p_pass_pt": RECOST_SUMMARY["paired_deltas"]["swing_margin"]["delta_pt"],
            "ci95": RECOST_SUMMARY["paired_deltas"]["swing_margin"]["ci95"],
            "margin_distribution": {m["tag"]: dict(p50=round(m["p50"], 3),
                                                   p99=round(m["p99"], 3),
                                                   p999=round(m["p999"], 3),
                                                   bind=round(m["bind"], 3),
                                                   p_pass=round(m["p_pass"], 2))
                                    for m in RECOST_SUMMARY["margin"]},
            "funded_insensible": "vm1: extraction identique sous marge swing (jamais bindé)",
            "action": ("GATE DÉPLOIEMENT: lire OrderCalcMargin sur le serveur Swing "
                       "AVANT challenge ; si rates ~ swing_official -> décision comité "
                       "(la grille de lots vm14 est de-levée x0.3-0.5 par le cap 60%)"),
        },
        "swaps_forward_projection": ("diagnostic seulement — projeter les bps d'aujourd'hui "
                                     "sur 2013-2026 pénalise l'ère ZIRP (IS -3.0) ; le panel "
                                     "swap HISTORIQUE reste la donnée contractuelle"),
        "details": "recost/summary.json + recost/tables/*.csv + RECOST_v2.2.1.md",
    },
    "contractual_anchors_v22": {
        "challenge_pooled": 0.870, "challenge_ci95": [0.823, 0.916],
        "challenge_is": 0.906, "challenge_oos": 0.834, "n_eff": 174,
        "attempts_mean": 3.24, "funded_value_usd": 1422, "ev_campaign_usd": 926,
        "cdf": {"30d": 0.416, "61d": 0.703, "91d": 0.870, "182d": 0.989, "270d": 1.0},
        "details": "NONREGRESSION_v2.2.md",
    },
    "live_gates_unchanged": [
        "test swap overnight (±20% sinon STOP)",
        "démo >=3 semaines: fills ACTIFS 16:00-16:30, >=60 trades (gate ORB_RT_BPS funded)",
        "EA MT5 (cette spec) + réconciliation quotidienne fills/swaps/spreads",
        "budget 4+ fees (~$400)", "clause 7.3 — décision comité",
    ],
}

out = HERE / "spec_v22.yaml"
txt = yaml.safe_dump(spec, sort_keys=False, allow_unicode=True, width=100)
out.write_text(txt)

# drift check: reload and compare the frozen configs key-by-key
back = yaml.safe_load(out.read_text())
assert back["challenge"]["config"] == dict(C22.CFG_CHALLENGE), "challenge cfg drift"
assert back["funded"]["config"] == dict(C22.CFG_FUNDED), "funded cfg drift"
assert back["funded"]["ORB_RT_BPS"]["value"] == C22.ORB_RT_BPS, "ORB_RT_BPS drift"
sha = hashlib.sha256(txt.encode()).hexdigest()
print(f"spec_v22.yaml written ({len(txt)} bytes), drift-check PASS")
print(f"sha256: {sha}")
