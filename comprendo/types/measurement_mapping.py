from typing import List

from pydantic import BaseModel


class MeasurementMappingEntry(BaseModel):
    raw_description: str
    mapped_to_canonical_id: str


class MeasurementMappingTable(BaseModel):
    entries: List[MeasurementMappingEntry]
