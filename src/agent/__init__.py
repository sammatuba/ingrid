"""The desk agent's service: threads, turns, drafts, confirmations, action receipts and the day meter.

Contract: docs/work/desk-agent-and-book-2026-10-18/agent-contract.md, sections 3 to 5 (DOCK-3).
The planner plans through the composer (src/judgment/view.py); this package runs the free actions
at once, parks every writing action behind the person's confirmation and keeps the records in the
private namespace. Nothing here imports the web layer; the routes are mounted by DOCK-5.
"""
