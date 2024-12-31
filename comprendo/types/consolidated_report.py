from typing import List, Optional

from pydantic import BaseModel, Field


class ConsolidatedBatchMeasurement(BaseModel):
    description: str
    value: str | float | bool | None
    accept: bool
    flag_disagreement: bool = Field(
        ..., description="Flag this if the experts have a disagreement on the value for this measurement"
    )


class ConsolidatedBatch(BaseModel):
    results: List[ConsolidatedBatchMeasurement]

    batch_number: Optional[str]
    expiration_date: Optional[str] = Field(..., description="Using ISO 8601 Date format")


class ConsolidatedReport(BaseModel):
    batches: List[ConsolidatedBatch]
    order_number: Optional[str]
    product_name: Optional[str]
    flag_identification_warning: bool
