"""
Where the PILAR-2b checkout is, and the CP2b v5.1 pieces read from it.

This repository keeps the CP2b evidence and sensitivity work out of the PILAR-2b
history. It still reads three things from a PILAR-2b checkout, read-only:

  analysis/build_biogram_reconciliation.py   the snapshot path (CP2B_SNAPSHOT_DIR
                                             override) and loader_constant()
  backend/scripts/load_cp2b_potential.py     file names, sha256, substrates and
                                             state totals of the v5.1 snapshot
  data/canonical_parameters/feedstocks.yaml  the platform's BMP ranges

The checkout is PILAR2B_DIR, or a sibling folder named Pilar2b or Pilar-2b. The
scripts refuse to run against a loader whose method version is not v5.1.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHOD_VERSION = "CP2b v5.1 (24/09/2026)"


def checkout() -> Path:
    env = os.environ.get("PILAR2B_DIR")
    candidates = [Path(env)] if env else [ROOT.parent / "Pilar2b", ROOT.parent / "Pilar-2b"]
    for path in candidates:
        if (path / "analysis" / "build_biogram_reconciliation.py").exists():
            return path.resolve()
    raise SystemExit("PILAR-2b checkout not found: set PILAR2B_DIR or clone it next to this repository "
                     f"(tried {', '.join(str(p) for p in candidates)}).")


PILAR2B = checkout()
NEWLOOK = PILAR2B / "cp2b-workspace" / "NewLook"
FEEDSTOCKS = NEWLOOK / "data" / "canonical_parameters" / "feedstocks.yaml"


def reconciliation():
    """PILAR-2b's build_biogram_reconciliation module, after checking the loader is v5.1."""
    path = PILAR2B / "analysis" / "build_biogram_reconciliation.py"
    spec = importlib.util.spec_from_file_location("biogram_reconciliation", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    version = mod.loader_constant("METHOD_VERSION")
    if version != METHOD_VERSION:
        raise SystemExit(f"PILAR-2b loader is {version!r}, these scripts read {METHOD_VERSION!r}.")
    return mod
