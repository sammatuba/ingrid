"""The outlook archive: records with a cutoff, inputs and a scoring receipt.

Modules are imported explicitly, so the package marker carries no re-exports and
adding one cannot disturb another module:

* :mod:`src.outlook.records` — the ``OutlookRecord`` and ``ScoringReceipt`` kinds
  and the directory-backed archive that issues and scores them (ARCH-1, plan
  note: ``docs/work/outlook-archive/intent.md``).
* ``src.outlook.register`` (ARCH-2) and ``src.outlook.dependency`` (ARCH-3) are
  later tasks in the same archive.

Standard library only, as the ARCH-1 brief requires.
"""
