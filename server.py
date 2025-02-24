import json
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, List

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from fastapi.middleware.cors import CORSMiddleware

from comprendo import __version__ as SERVER_VERSION
from comprendo.app_logging import set_logging_context
from comprendo.configuration import app_config
from comprendo.process import process_task
from comprendo.server.security import ClientCredentials, validate_api_key
from comprendo.server.types.extract_coa_input import COARequest
from comprendo.server.types.extract_coa_output import (
    BatchDataResponse,
    COAResponse,
    MeasurementResultResponse,
)
from comprendo.types.consolidated_report import (
    ConsolidatedBatch,
    ConsolidatedMeasurementResult,
)
from comprendo.types.extraction_result import ExtractionResult
from comprendo.types.task import Task

app = FastAPI()

if app_config.bool("CORS_ALLOW_ALL", False):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def map_extracted_batch_result_to_response_measurement(
    result: ConsolidatedMeasurementResult,
) -> MeasurementResultResponse:
    return MeasurementResultResponse(
        measurement_id=result.id,
        measurement_name=result.description,
        value=result.value,
        accept=result.accept,
        flag_uncertain=result.flag_disagreement,  # Other sources of uncertainty?
    )


def map_extracted_batch_to_response_batch(
    extracted_batch: ConsolidatedBatch,
) -> BatchDataResponse:
    response_measurements = [map_extracted_batch_result_to_response_measurement(m) for m in extracted_batch.results]

    return BatchDataResponse(
        batch_number=extracted_batch.batch_number,
        expiration_date=extracted_batch.expiration_date,
        results=response_measurements,
    )


def map_extraction_result_to_response(task: Task, extraction_result: ExtractionResult) -> COAResponse:
    response_batches = [map_extracted_batch_to_response_batch(b) for b in extraction_result.consolidated_report.batches]
    response = COAResponse(
        request_id=task.request.id,
        order_number=extraction_result.consolidated_report.order_number,
        identification_warning=extraction_result.consolidated_report.flag_identification_warning,
        estimated_cost=task.cost,
        # Errors?
        batches=response_batches,
    )

    if task.mock_mode:
        response.mock = True

    return response


def detect_mock_mode(
    client: Annotated[ClientCredentials, Depends(validate_api_key)],
    x_comprendo_mock_mode: Annotated[bool | None, Header()] = False,
) -> bool:
    forced_mock_mode_active = app_config.bool("MOCK_MODE", False)
    return forced_mock_mode_active or client.mock_only or x_comprendo_mock_mode


@app.get("/ping")
async def ping():
    return JSONResponse(content={"server_version": SERVER_VERSION})


@app.post("/extract/coa")
async def extract_coa(
    client: Annotated[ClientCredentials, Depends(validate_api_key)],
    mock_mode: Annotated[bool, Depends(detect_mock_mode)],
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

    if not input_data.id:
        input_data.id = str(uuid.uuid4())

    with TemporaryDirectory(suffix=f"-coa-{input_data.id}") as task_storage_dir:
        storage_dir_path = Path(task_storage_dir)
        # Store files locally in a temporary processing dir
        input_files = []
        for file in files:
            file_id = str(uuid.uuid4())
            input_filename = Path(file.filename).name
            file_path = storage_dir_path / f"{file_id}-{input_filename}"
            with open(file_path, "wb") as f:
                f.write(await file.read())
            input_files.append((file_path, file_id))

        documents_paths = [Path(doc_file_path) for doc_file_path, _ in input_files]
        task = Task(
            request=input_data,
            mock_mode=mock_mode,
        )
        set_logging_context(task=task, client=client)
        extraction_result = await process_task(task, documents_paths)
        response = map_extraction_result_to_response(task, extraction_result)

    return JSONResponse(content=response.model_dump())


FastAPIInstrumentor.instrument_app(app)
