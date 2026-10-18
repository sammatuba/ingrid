"""Explicit local Uvicorn factory. Run with access logging disabled."""
import os
from contextlib import asynccontextmanager
from src.adapters.firestore import FirestoreStore
from src.adapters.identity import FirebaseIdentity
from src.review.storage import PersistentRepository
from . import create_app


def app():
    project = os.environ.get('GCLOUD_PROJECT', '')
    store = FirestoreStore(project, os.environ.get('NOWCAST_NAMESPACE', ''))
    identity = FirebaseIdentity(project)
    application = create_app(PersistentRepository(store), identity)
    @asynccontextmanager
    async def lifespan(app):
        yield
        identity.close()
        store.close()
    application.router.lifespan_context = lifespan
    return application
