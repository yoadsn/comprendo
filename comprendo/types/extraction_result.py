from pydantic import BaseModel
from typing import List, Optional

from comprendo.types.consolidated_report import ConsolidatedReport
from comprendo.types.measurement_mapping import MeasurementMappingTable


class ExtractionResult(BaseModel):
    measurements_mapping: MeasurementMappingTable
    consolidated_report: ConsolidatedReport
    errors: Optional[List[str]] = None
