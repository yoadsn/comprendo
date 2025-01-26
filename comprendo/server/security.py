import os
from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from openai import BaseModel

from comprendo.configuration import app_config

auth_disabled = app_config.bool(f"DISABLE_AUTHENTICATION", False)
security = HTTPBearer(auto_error=not auth_disabled)


# Simple placeholder for stronger auth ifx
class ClientCredentials(BaseModel):
    id: str
    mock_only: bool = False


in_mem_cred_store: dict[str, ClientCredentials] = {}

for client_app_idx in range(10):
    client_app_credentials = app_config.str(f"CLIENT_APP_{client_app_idx}", None)
    if client_app_credentials:
        try:
            valid_api_key, client_app_id, mock_only_flag = client_app_credentials.split(";")
            in_mem_cred_store[valid_api_key] = ClientCredentials(id=client_app_id, mock_only=mock_only_flag == "1")
        except:
            pass


def validate_api_key(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
    if auth_disabled:
        return ClientCredentials(id="anonymous", mock_only=False)

    found_client_app_credentials = in_mem_cred_store.get(credentials.credentials, None)
    if found_client_app_credentials is None:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return found_client_app_credentials
