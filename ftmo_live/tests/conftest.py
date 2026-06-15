import sys
from pathlib import Path

import pytest

LIVE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIVE_ROOT))

from lib import LEGS  # noqa: E402,F401


@pytest.fixture()
def files_dir(tmp_path, monkeypatch):
    """Répertoire MQL5/Files simulé + runtime isolé."""
    d = tmp_path / "Files"
    d.mkdir()
    monkeypatch.setenv("FTMO_LIVE_MT5_FILES", str(d))
    monkeypatch.setenv("FTMO_LIVE_TG_DISABLED", "1")
    return d


@pytest.fixture()
def runtime_isolated(tmp_path, monkeypatch):
    """Isole lib.RUNTIME (et ses consommateurs déjà importés) dans tmp."""
    import lib
    from lib import statefiles
    rt = tmp_path / "runtime"
    rt.mkdir()
    monkeypatch.setattr(lib, "RUNTIME", rt)
    monkeypatch.setattr(statefiles, "RUNTIME", rt)
    for modname in ("supervisor", "reconcile"):
        if modname in sys.modules:
            m = sys.modules[modname]
            for attr in ("RUNTIME",):
                if hasattr(m, attr):
                    monkeypatch.setattr(m, attr, rt)
            if modname == "supervisor":
                monkeypatch.setattr(m, "ALERTS_STATE", rt / "alerts_state.json")
                monkeypatch.setattr(m, "SOD_DIR", rt / "sod")
                monkeypatch.setattr(m, "SNAP_PATH", rt / "snapshots.json")
                monkeypatch.setattr(m, "CAMPAIGN", rt / "campaign.json")
                # heartbeat watchdog FRAIS par défaut (méta-surveillance) ; les
                # tests dédiés le rendent périmé/absent explicitement
                alive = rt / "watchdog_alive"
                alive.write_text("fixture")
                monkeypatch.setattr(m, "WATCHDOG_ALIVE", alive)
            if modname == "reconcile":
                monkeypatch.setattr(m, "LOG", rt / "reconcile_log.csv")
                monkeypatch.setattr(m, "EOD_DIR", rt / "eod")
    return rt
