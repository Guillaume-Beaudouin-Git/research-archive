"""brain.py — chargeur de spec v2.2 pour le build EA. NE RÉGÉNÈRE RIEN, NE RETAPE RIEN.

Contrat (amendement brief de build):
  - charge v22/spec_v22.yaml, vérifie le sha256 ÉPINGLÉ (dd6ab126…) avant tout usage;
  - drift-check inclus: les blocs challenge/funded/ORB_RT_BPS du yaml doivent être
    IDENTIQUES à config_v22.py (source de génération) — toute divergence = STOP;
  - vérifie la présence des commits baseline épinglés (warn-only hors repo);
  - expose des accesseurs typés; aucun nombre n'est défini ici.
Usage: python3 brain.py --check
"""
import sys, hashlib, subprocess
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
V22 = HERE.parent
sys.path.insert(0, str(V22))
import config_v22 as C22

SPEC_PATH = V22 / "spec_v22.yaml"
# v2.2.2 lot EA v2.8 (overlay leg_leverage_cap + 3e ancre de marge swing_measured).
#   ancien pin v2.2.1: 56fbdde78a2e5c4365e8e0f5bbda06d3697a198beccbcbf2dd02deea0eb27928
#   ancien pin v2.2  : dd6ab12680208c4e71ea34f83c254e9246e93e2c
PIN_SHA256 = "1f3081bfbfd04be29f886ad85459305bdc4a5dd740d488b462f6a15048cac4bb"
PIN_COMMITS = {
    "v22_contract": "605f4a426da3eac4f5a2644bca774a07f1e5f754",
    "v22_residuals": "4e1bac5cf6486fcd0070876d47dd2dcdc7a8f539",
    # v2.8 : commit de gel du yaml v2.2.2 (ancien v2.2.1: 87b6cd4080e2b1c9e666c6b9dd15680ce29a7e1e)
    "v22_spec_yaml": "ae52ea525208ce33f15d4e50aa1aceba16d0e5d2",
}
REPO = Path("<HOME>/Desktop/Algo_claude")


class SpecError(RuntimeError):
    pass


def load(path: Path = SPEC_PATH) -> dict:
    """Charge le yaml épinglé. Lève SpecError sur tout écart (hash, drift, pins)."""
    txt = path.read_text()
    sha = hashlib.sha256(txt.encode()).hexdigest()
    if sha != PIN_SHA256:
        raise SpecError(f"spec sha256 {sha[:12]}… != pin {PIN_SHA256[:12]}… — "
                        "la spec a bougé sans re-gel (ancre #19/#20) : STOP")
    spec = yaml.safe_load(txt)
    # drift-check vs la source de génération
    if spec["challenge"]["config"] != dict(C22.CFG_CHALLENGE):
        raise SpecError("drift challenge config yaml != config_v22.py")
    if spec["funded"]["config"] != dict(C22.CFG_FUNDED):
        raise SpecError("drift funded config yaml != config_v22.py")
    if spec["funded"]["ORB_RT_BPS"]["value"] != C22.ORB_RT_BPS:
        raise SpecError("drift ORB_RT_BPS yaml != config_v22.py")
    pins = spec["meta"]["baseline_commits"]
    for k in ("v22_contract", "v22_residuals"):
        if pins.get(k) != PIN_COMMITS[k]:
            raise SpecError(f"pin {k} du yaml != pin brain.py")
    return spec


def verify_pins_in_repo() -> list:
    """Warn-only: les SHAs épinglés existent-ils dans ce clone ?"""
    missing = []
    for name, sha in PIN_COMMITS.items():
        r = subprocess.run(["git", "cat-file", "-t", sha], capture_output=True,
                           text=True, cwd=REPO)
        if r.stdout.strip() != "commit":
            missing.append(f"{name}={sha[:7]}")
    return missing


# ---- accesseurs typés (zéro constante locale) ----
def challenge_cfg(spec): return spec["challenge"]["config"]
def funded_cfg(spec): return spec["funded"]["config"]
def micro_orb(spec): return spec["challenge"]["micro_orb_day_counter"]
def schedule_cet(spec): return spec["challenge"]["schedule_cet"]
def rules(spec): return spec["account"]["rules"]
def orb_rt_bps(spec): return spec["funded"]["ORB_RT_BPS"]["value"]
def switch_trigger(spec): return spec["funded"]["switch_trigger"]
def margin(spec): return spec["challenge"]["risk_engine"]["margin_cap"]


if __name__ == "__main__":
    if "--check" in sys.argv or len(sys.argv) == 1:
        spec = load()
        miss = verify_pins_in_repo()
        print(f"spec OK: {spec['meta']['version']} sha {PIN_SHA256[:12]}… "
              f"(drift-check PASS)")
        print(f"pins: {', '.join(k + '=' + v[:7] for k, v in PIN_COMMITS.items())}"
              + (f"  MANQUANTS REPO: {miss}" if miss else "  (tous présents)"))
        print(f"challenge: vm={challenge_cfg(spec)['vm']} micro_orb="
              f"{challenge_cfg(spec)['micro_orb']} orb_risk="
              f"{challenge_cfg(spec)['orb_risk']}")
        print(f"micro-ORB: {micro_orb(spec)['size_lots']} lot, condition 21:30 "
              f"(flag opened), is_the_day_counter={micro_orb(spec)['is_the_day_counter']}")
        print(f"funded: vm={funded_cfg(spec)['vm']} ORB_RT_BPS={orb_rt_bps(spec)} "
              f"(aucun ré-ancrage avant verdict 2026-06-15)")
