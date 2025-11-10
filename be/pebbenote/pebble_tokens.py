from typing import Annotated

from fastapi import Depends, HTTPException, Header, status


def get_pebble_user_token(
    header: Annotated[str, Header(alias="X-pebble-user-token")],
):
    if not header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return header


PebbleUserToken = Annotated[str, Depends(get_pebble_user_token)]
