from http import HTTPStatus
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.note_model import NoteModel
from ...types import Response


def _get_kwargs(
    note_id: UUID,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/note/{note_id}/default".format(
            note_id=quote(str(note_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | NoteModel | None:
    if response.status_code == 200:
        response_200 = NoteModel.from_dict(response.json())

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[HTTPValidationError | NoteModel]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    note_id: UUID,
    *,
    client: AuthenticatedClient,
) -> Response[HTTPValidationError | NoteModel]:
    """Set Default Note

    Args:
        note_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | NoteModel]
    """

    kwargs = _get_kwargs(
        note_id=note_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    note_id: UUID,
    *,
    client: AuthenticatedClient,
) -> HTTPValidationError | NoteModel | None:
    """Set Default Note

    Args:
        note_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | NoteModel
    """

    return sync_detailed(
        note_id=note_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    note_id: UUID,
    *,
    client: AuthenticatedClient,
) -> Response[HTTPValidationError | NoteModel]:
    """Set Default Note

    Args:
        note_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | NoteModel]
    """

    kwargs = _get_kwargs(
        note_id=note_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    note_id: UUID,
    *,
    client: AuthenticatedClient,
) -> HTTPValidationError | NoteModel | None:
    """Set Default Note

    Args:
        note_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | NoteModel
    """

    return (
        await asyncio_detailed(
            note_id=note_id,
            client=client,
        )
    ).parsed
