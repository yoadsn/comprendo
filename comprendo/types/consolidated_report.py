from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema


class ConsolidatedMeasurementResult(BaseModel):
    # Not included in the JSON schema so the model will not try to fill this in
    id: SkipJsonSchema[Optional[str]] = None

    description: str
    value: str | float | bool | None
    accept: bool
    flag_disagreement: bool = Field(
        ..., description="Flag this if the experts have a disagreement on the value for this measurement"
    )


class ConsolidatedBatch(BaseModel):
    results: List[ConsolidatedMeasurementResult]

    batch_number: Optional[str]
    expiration_date: Optional[str] = Field(..., description="Using ISO 8601 Date format")


class ConsolidatedReport(BaseModel):
    batches: List[ConsolidatedBatch]
    order_number: Optional[str]
    product_name: Optional[str]
    flag_identification_warning: bool
