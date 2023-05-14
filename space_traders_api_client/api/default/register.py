from http import HTTPStatus
from typing import Any, Dict, Optional

import httpx

from ... import errors
from ...client import Client
from ...models.register_json_body import RegisterJsonBody
from ...models.register_response_201 import RegisterResponse201
from ...types import Response


def _get_kwargs(
    *,
    client: Client,
    json_body: RegisterJsonBody,
) -> Dict[str, Any]:
    url = "{}/register".format(client.base_url)

    headers: Dict[str, str] = client.get_headers()
    cookies: Dict[str, Any] = client.get_cookies()

    json_json_body = json_body.to_dict()

    return {
        "method": "post",
        "url": url,
        "headers": headers,
        "cookies": cookies,
        "timeout": client.get_timeout(),
        "follow_redirects": client.follow_redirects,
        "json": json_json_body,
    }


def _parse_response(*, client: Client, response: httpx.Response) -> Optional[RegisterResponse201]:
    if response.status_code == HTTPStatus.CREATED:
        response_201 = RegisterResponse201.from_dict(response.json())

        return response_201
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: Client, response: httpx.Response) -> Response[RegisterResponse201]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Client,
    json_body: RegisterJsonBody,
) -> Response[RegisterResponse201]:
    """Register New Agent

     Creates a new agent and ties it to a temporary Account.

    The agent symbol is a 3-14 character string that will represent your agent. This symbol will prefix
    the symbol of every ship you own. Agent symbols will be cast to all uppercase characters.

    A new agent will be granted an authorization token, a contract with their starting faction, a
    command ship with a jump drive, and one hundred thousand credits.

    > #### Keep your token safe and secure
    >
    > Save your token during the alpha phase. There is no way to regenerate this token without starting
    a new agent. In the future you will be able to generate and manage your tokens from the SpaceTraders
    website.

    You can accept your contract using the `/my/contracts/{contractId}/accept` endpoint. You will want
    to navigate your command ship to a nearby asteroid field and execute the
    `/my/ships/{shipSymbol}/extract` endpoint to mine various types of ores and minerals.

    Return to the contract destination and execute the `/my/ships/{shipSymbol}/deliver` endpoint to
    deposit goods into the contract.

    When your contract is fulfilled, you can call `/my/contracts/{contractId}/fulfill` to retrieve
    payment.

    Args:
        json_body (RegisterJsonBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[RegisterResponse201]
    """

    kwargs = _get_kwargs(
        client=client,
        json_body=json_body,
    )

    response = httpx.request(
        verify=client.verify_ssl,
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Client,
    json_body: RegisterJsonBody,
) -> Optional[RegisterResponse201]:
    """Register New Agent

     Creates a new agent and ties it to a temporary Account.

    The agent symbol is a 3-14 character string that will represent your agent. This symbol will prefix
    the symbol of every ship you own. Agent symbols will be cast to all uppercase characters.

    A new agent will be granted an authorization token, a contract with their starting faction, a
    command ship with a jump drive, and one hundred thousand credits.

    > #### Keep your token safe and secure
    >
    > Save your token during the alpha phase. There is no way to regenerate this token without starting
    a new agent. In the future you will be able to generate and manage your tokens from the SpaceTraders
    website.

    You can accept your contract using the `/my/contracts/{contractId}/accept` endpoint. You will want
    to navigate your command ship to a nearby asteroid field and execute the
    `/my/ships/{shipSymbol}/extract` endpoint to mine various types of ores and minerals.

    Return to the contract destination and execute the `/my/ships/{shipSymbol}/deliver` endpoint to
    deposit goods into the contract.

    When your contract is fulfilled, you can call `/my/contracts/{contractId}/fulfill` to retrieve
    payment.

    Args:
        json_body (RegisterJsonBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        RegisterResponse201
    """

    return sync_detailed(
        client=client,
        json_body=json_body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Client,
    json_body: RegisterJsonBody,
) -> Response[RegisterResponse201]:
    """Register New Agent

     Creates a new agent and ties it to a temporary Account.

    The agent symbol is a 3-14 character string that will represent your agent. This symbol will prefix
    the symbol of every ship you own. Agent symbols will be cast to all uppercase characters.

    A new agent will be granted an authorization token, a contract with their starting faction, a
    command ship with a jump drive, and one hundred thousand credits.

    > #### Keep your token safe and secure
    >
    > Save your token during the alpha phase. There is no way to regenerate this token without starting
    a new agent. In the future you will be able to generate and manage your tokens from the SpaceTraders
    website.

    You can accept your contract using the `/my/contracts/{contractId}/accept` endpoint. You will want
    to navigate your command ship to a nearby asteroid field and execute the
    `/my/ships/{shipSymbol}/extract` endpoint to mine various types of ores and minerals.

    Return to the contract destination and execute the `/my/ships/{shipSymbol}/deliver` endpoint to
    deposit goods into the contract.

    When your contract is fulfilled, you can call `/my/contracts/{contractId}/fulfill` to retrieve
    payment.

    Args:
        json_body (RegisterJsonBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[RegisterResponse201]
    """

    kwargs = _get_kwargs(
        client=client,
        json_body=json_body,
    )

    async with httpx.AsyncClient(verify=client.verify_ssl) as _client:
        response = await _client.request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Client,
    json_body: RegisterJsonBody,
) -> Optional[RegisterResponse201]:
    """Register New Agent

     Creates a new agent and ties it to a temporary Account.

    The agent symbol is a 3-14 character string that will represent your agent. This symbol will prefix
    the symbol of every ship you own. Agent symbols will be cast to all uppercase characters.

    A new agent will be granted an authorization token, a contract with their starting faction, a
    command ship with a jump drive, and one hundred thousand credits.

    > #### Keep your token safe and secure
    >
    > Save your token during the alpha phase. There is no way to regenerate this token without starting
    a new agent. In the future you will be able to generate and manage your tokens from the SpaceTraders
    website.

    You can accept your contract using the `/my/contracts/{contractId}/accept` endpoint. You will want
    to navigate your command ship to a nearby asteroid field and execute the
    `/my/ships/{shipSymbol}/extract` endpoint to mine various types of ores and minerals.

    Return to the contract destination and execute the `/my/ships/{shipSymbol}/deliver` endpoint to
    deposit goods into the contract.

    When your contract is fulfilled, you can call `/my/contracts/{contractId}/fulfill` to retrieve
    payment.

    Args:
        json_body (RegisterJsonBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        RegisterResponse201
    """

    return (
        await asyncio_detailed(
            client=client,
            json_body=json_body,
        )
    ).parsed
