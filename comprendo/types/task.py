from pydantic import BaseModel

from comprendo.server.types.extract_coa_input import COARequest


class Task(BaseModel):
    request: COARequest
    mock_mode: bool = False
