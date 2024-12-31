from pydantic import BaseModel
from typing import List, Optional


class MeasurementResult(BaseModel):
    measurement_id: Optional[str]  # May be None if measurement is unknown or not matched
    measurement_name: str
    value: str | float | bool | None
    accept: bool
    flag_uncertain: bool


class BatchData(BaseModel):
    batch_number: str | None
    expiration_date: str | None
    results: List[MeasurementResult]


class COAResponse(BaseModel):
    task_id: str
    order_number: str | None
    identification_warning: bool
    batches: List[BatchData]
    mock: bool = False
