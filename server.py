import json
import os
import shutil
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

load_dotenv()

from comprendo.server.types.extract_coa_input import COARequest
from comprendo.server.types.extract_coa_output import (
    BatchData,
    COAResponse,
    MeasurementResult,
)
from comprendo.types.consolidated_report import (
    ConsolidatedBatch,
    ConsolidatedBatchMeasurement,
)
from comprendo.types.extraction_result import ExtractionResult
from comprendo.types.task import Task, TaskRequest
from main import get_task_storage_dir, process_task

app = FastAPI()
mock_mode_active = os.environ.get("MOCK_MODE")

def map_extracted_batch_result_to_response_measurement(
    result: ConsolidatedBatchMeasurement,
    description_to_id_mapping: dict[str, str],
    id_to_canonical_name: dict[str, str],
) -> MeasurementResult:
    potential_id = description_to_id_mapping.get(result.description, "?")
    found_id = potential_id if potential_id != "?" else None
    found_name = id_to_canonical_name.get(found_id, None)
    measurement_name = found_name if found_name else result.description
    return MeasurementResult(
        measurement_id=found_id,
        measurement_name=measurement_name,
        value=result.value,
        accept=result.accept,
        flag_uncertain=result.flag_disagreement,  # Other sources of uncertainty?
    )


def map_extracted_batch_to_response_batch(
    extracted_batch: ConsolidatedBatch,
    task: Task,
    description_to_id_mapping: dict[str, str],
    id_to_canonical_name: dict[str, str],
) -> BatchData:
    response_measurements = [
        map_extracted_batch_result_to_response_measurement(m, description_to_id_mapping, id_to_canonical_name)
        for m in extracted_batch.results
    ]

    return BatchData(
        batch_number=extracted_batch.batch_number,
        expiration_date=extracted_batch.expiration_date,
        results=response_measurements,
    )


def map_extraction_result_to_response(task: Task, extraction_result: ExtractionResult) -> COAResponse:
    measurement_mapping_table = extraction_result.measurements_mapping
    canonical_measurements_id_to_name = {rm.id: rm.name for rm in task.request.measurements}
    canonical_measurements_name_to_id = {rm.name: rm.id for rm in task.request.measurements}
    description_to_id_mapping = {m.description: m.mapped_to_id for m in measurement_mapping_table.entries}
    # Know how to map the canonical and the non canonicals to the ids
    description_to_id_mapping = {**description_to_id_mapping, **canonical_measurements_name_to_id}

    response_batches = [
        map_extracted_batch_to_response_batch(b, task, description_to_id_mapping, canonical_measurements_id_to_name)
        for b in extraction_result.consolidated_report.batches
    ]
    return COAResponse(
        task_id=task.id,
        order_number=extraction_result.consolidated_report.order_number,
        identification_warning=extraction_result.consolidated_report.flag_identification_warning,
        # Errors?
        batches=response_batches,
        mock=task.mock_mode,
    )


@app.get("/extract/coa")
async def extract_coa(
    # Accept multiple PDF files
    files: List[UploadFile] = File(...),
    request: str = Form(...),
):
    """
    Endpoint to process a COA PDF document and return structured data.
    Expects:
      - files (1 or more PDFs) in multipart/form-data
      - metadata (JSON) in multipart/form-data
    Returns:
      - JSON response conforming to COAResponse model
    """

    # Parse metadata JSON
    try:
        input_data = COARequest(**json.loads(request))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid metadata JSON: {str(e)}")

    task_id = str(uuid.uuid4())
    with TemporaryDirectory(suffix=f"-coa-{task_id}") as task_storage_dir:
        storage_dir_path = Path(task_storage_dir)
        # Store files locally in a temporary processing dir
        input_files = []
        for file in files:
            file_id = str(uuid.uuid4())
            file_path = storage_dir_path / f"{file_id}-{file.filename}"
            with open(file_path, "wb") as f:
                f.write(await file.read())
            input_files.append((file_path, file_id))

        task = Task(
            id=task_id,
            request=TaskRequest(
                doc_files=[str(doc_file_path) for doc_file_path, _ in input_files],
                order_number=input_data.order_number,
                measurements=[m.model_dump() for m in input_data.measurements],
            ),
            mock_mode=mock_mode_active,
        )
        extraction_result = process_task(task)
        response = map_extraction_result_to_response(task, extraction_result)

    # Clean up the file here, or schedule a cleanup.
    # For demonstration, we’ll do a simple immediate cleanup.
    # cleanup_storage_dir(storage_dir)

    return JSONResponse(content=response.model_dump())


def cleanup_storage_dir(storage_dir: Path) -> None:
    shutil.rmtree(storage_dir, ignore_errors=True)
