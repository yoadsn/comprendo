import os
from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from openai import BaseModel

security = HTTPBearer()


# Simple placeholder for stronger auth ifx
class ClientCredentials(BaseModel):
    id: str
    mock_only: bool = False


in_mem_cred_store: dict[str, ClientCredentials] = {}

for client_app_idx in range(10):
    client_app_credentials = os.environ.get(f"CLIENT_APP_{client_app_idx}")
    if client_app_credentials:
        try:
            valid_api_key, client_app_id, mock_only_flag = client_app_credentials.split(";")
            in_mem_cred_store[valid_api_key] = ClientCredentials(id=client_app_id, mock_only=mock_only_flag == "1")
        except:
            pass


def validate_api_key(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
    found_client_app_credentials = in_mem_cred_store.get(credentials.credentials, None)
    if found_client_app_credentials is None:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return found_client_app_credentials
