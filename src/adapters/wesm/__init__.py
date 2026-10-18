"""Bounded local readers for the company WESM copy.

Two additive, read-only adapters over orchestrator-produced JSON lines:
:mod:`~src.adapters.wesm.advisories` for the system-operator advisories and
:mod:`~src.adapters.wesm.registry` for the registered-capacity register. The
export itself (``scripts/data/wesm/export.sh``) runs in the orchestrator seat
with the repo-local gcloud configuration; these modules read local bytes only and
make no network, credential or service call.

The submodules are imported on demand (``from src.adapters.wesm import
registry``) and not eagerly here, so ``python3 -m src.adapters.wesm.registry``
runs without the runpy double-import warning.
"""
__all__ = ["advisories", "registry"]
