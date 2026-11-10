from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.instructions_model import InstructionsModel
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: InstructionsModel,
    apply: bool | Unset = True,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["apply"] = apply

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/instruction/",
        "params": params,
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | InstructionsModel | None:
    if response.status_code == 200:
        response_200 = InstructionsModel.from_dict(response.json())

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
) -> Response[HTTPValidationError | InstructionsModel]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: InstructionsModel,
    apply: bool | Unset = True,
) -> Response[HTTPValidationError | InstructionsModel]:
    """Replace Instructions

     Replaces the standing instructions. Unless `apply` is false, the new ones
    are then applied in the background to every note of the user that is not
    changed in the meantime.

    Args:
        apply (bool | Unset):  Default: True.
        body (InstructionsModel):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | InstructionsModel]
    """

    kwargs = _get_kwargs(
        body=body,
        apply=apply,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: InstructionsModel,
    apply: bool | Unset = True,
) -> HTTPValidationError | InstructionsModel | None:
    """Replace Instructions

     Replaces the standing instructions. Unless `apply` is false, the new ones
    are then applied in the background to every note of the user that is not
    changed in the meantime.

    Args:
        apply (bool | Unset):  Default: True.
        body (InstructionsModel):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | InstructionsModel
    """

    return sync_detailed(
        client=client,
        body=body,
        apply=apply,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: InstructionsModel,
    apply: bool | Unset = True,
) -> Response[HTTPValidationError | InstructionsModel]:
    """Replace Instructions

     Replaces the standing instructions. Unless `apply` is false, the new ones
    are then applied in the background to every note of the user that is not
    changed in the meantime.

    Args:
        apply (bool | Unset):  Default: True.
        body (InstructionsModel):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | InstructionsModel]
    """

    kwargs = _get_kwargs(
        body=body,
        apply=apply,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: InstructionsModel,
    apply: bool | Unset = True,
) -> HTTPValidationError | InstructionsModel | None:
    """Replace Instructions

     Replaces the standing instructions. Unless `apply` is false, the new ones
    are then applied in the background to every note of the user that is not
    changed in the meantime.

    Args:
        apply (bool | Unset):  Default: True.
        body (InstructionsModel):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | InstructionsModel
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            apply=apply,
        )
    ).parsed
