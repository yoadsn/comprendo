from pydantic import BaseModel
from typing import List, Optional


class MeasurementResultResponse(BaseModel):
    measurement_id: Optional[str]  # May be None if measurement is unknown or not matched
    measurement_name: str
    value: str | float | bool | None
    accept: bool
    flag_uncertain: bool


class BatchDataResponse(BaseModel):
    batch_number: str | None
    expiration_date: str | None
    results: List[MeasurementResultResponse]


class COAResponse(BaseModel):
    request_id: str
    order_number: str | None
    batches: List[BatchDataResponse]
    identification_warning: bool
    mock: Optional[bool] = False
