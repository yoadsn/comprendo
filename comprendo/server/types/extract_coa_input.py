from pydantic import BaseModel
from typing import List


class RequestMeasurement(BaseModel):
    id: str
    name: str
    qualitative: bool


class COARequest(BaseModel):
    order_number: str
    measurements: List[RequestMeasurement]
