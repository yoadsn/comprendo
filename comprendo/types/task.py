from pydantic import BaseModel


class RequestMeasurement(BaseModel):
    id: str
    name: str
    qualitative: bool = False


class TaskRequest(BaseModel):
    doc_files: list[str]
    order_number: str
    measurements: list[RequestMeasurement]


class Task(BaseModel):
    request: TaskRequest
    id: str
    mock_mode: bool = False
