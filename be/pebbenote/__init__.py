import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.routing import APIRoute

from .actions.router import action_router
from .auth import get_current_user
from .config import settings
from .notes.exceptions import NoteDoesNotExist
from .notes.router import note_router

logging.basicConfig(level=logging.INFO)


is_local = settings.ENVIRONMENT == "local"

app = FastAPI(
    title="PebbeNote",
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


def use_route_names_as_operation_ids(app: FastAPI) -> None:
    """
    Simplify operation IDs so that generated API clients have simpler function
    names.

    Should be called only after all routes have been added.

    Borrowed from FastAPI docs
    """
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name


use_route_names_as_operation_ids(app)
