"""The desk API (UX-B): search, previews, suggested prompts and grounded answers over the bake.

The command bar's server half (docs/work/ui-refinement-2026-10-18/desk-api.md). It reads the same
baked replay directory the `/grid-data` route serves, lazily and once per build, and composes every
answer deterministically from those records: no model call, no invented figure, nothing later than
the replay clock. Standard library only; the routes import FastAPI when they are registered.

* `bake.py`: the loader (both bake shapes, both timestamp shapes, missing files as empty);
* `search.py`: `search` and `preview`;
* `answer.py`: the intents, free-text matching, prompts and the composed answer;
* `routes.py`: `register(app, data_dir)`, mounted by `src/api/hosted.py`.
"""
from .routes import register

__all__ = ['register']
