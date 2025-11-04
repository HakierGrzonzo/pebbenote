import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.routing import APIRoute

from .auth import validate_api_key
from .notes.router import note_router
from .actions.router import action_router

logging.basicConfig(level=logging.INFO)


app = FastAPI(title="PebbeNote", dependencies=[Depends(validate_api_key)])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def redirect_to_docs():
    return RedirectResponse("/docs")


app.include_router(note_router)
app.include_router(action_router)


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
