import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.routing import APIRoute

from .actions.router import action_router
from .auth import get_current_user
from .config import settings
from .instructions.router import instruction_router
from .notes.exceptions import NoteDoesNotExist
from .notes.router import note_router
from .worker import broker

logging.basicConfig(level=logging.INFO)


is_local = settings.ENVIRONMENT == "local"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The worker process starts the broker on its own
    if not broker.is_worker_process:
        await broker.startup()
    yield
    if not broker.is_worker_process:
        await broker.shutdown()


def route_name_as_operation_id(route: APIRoute) -> str:
    """Simple operation IDs, so generated API clients get simple function names."""
    return route.name


app = FastAPI(
    title="PebbeNote",
    generate_unique_id_function=route_name_as_operation_id,
    lifespan=lifespan,
    docs_url="/docs" if is_local else None,
    redoc_url=None,
    openapi_url="/openapi.json" if is_local else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


if is_local:

    @app.get("/", include_in_schema=False)
    def redirect_to_docs():
        return RedirectResponse("/docs")


@app.exception_handler(NoteDoesNotExist)
async def note_does_not_exist_handler(request: Request, exc: NoteDoesNotExist):
    return JSONResponse(status_code=404, content={"detail": "Note not found"})


app.include_router(note_router, dependencies=[Depends(get_current_user)])
app.include_router(action_router, dependencies=[Depends(get_current_user)])
app.include_router(instruction_router, dependencies=[Depends(get_current_user)])
