import argparse
import asyncio
import json
from pathlib import Path

from comprendo.configuration import app_config
from comprendo.process import process_task
from comprendo.server.types.extract_coa_input import COARequest
from comprendo.types.task import Task

mock_mode_active = app_config.bool("MOCK_MODE", False)
BASE_STORAGE_DIR = Path("storage")
TASK_REQUEST_FILE_NAME = "request.json"


def get_task_storage_dir(task_id: str) -> Path:
    return BASE_STORAGE_DIR / task_id


def load_task(task_id: str) -> tuple[Task, list[str]]:
    task_dir = get_task_storage_dir(task_id)
    request_file = task_dir / TASK_REQUEST_FILE_NAME
    with open(request_file, "r") as f:
        task_data = json.loads(f.read())
        request = COARequest(**task_data.get("request"))
        doc_files = task_data.get("doc_files")
        task = Task(request=request, mock_mode=mock_mode_active)
        return task, doc_files


def main():
    parser = argparse.ArgumentParser(description="Run Doc analyzer flow")
    parser.add_argument("id", type=str, help="Inbound task id")

    args = parser.parse_args()

    task_id = args.id

    task, doc_files = load_task(task_id)
    task.request.id = task_id  # Force this for local testing
    task.mock_mode = mock_mode_active
    # For CLI run - depend on local files from a predefined task storage folder
    documents_paths = [get_task_storage_dir(task.request.id) / doc_file for doc_file in doc_files]
    result = asyncio.run(process_task(task, documents_paths))
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
