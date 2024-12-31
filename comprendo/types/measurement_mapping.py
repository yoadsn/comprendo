from typing import List

from pydantic import BaseModel


class MeasurementMappingEntry(BaseModel):
    description: str
    mapped_to_id: str


class MeasurementMappingTable(BaseModel):
    entries: List[MeasurementMappingEntry]
