import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from comprendo.extraction.extract import extract as live_extract
from comprendo.extraction.mock_extract import extract as mock_extract
from comprendo.preprocess.document import get_document_as_images
from comprendo.types.task import Task, TaskRequest
from comprendo.types.image_artifact import ImageArtifact


mock_mode_active = os.environ.get("MOCK_MODE")
BASE_STORAGE_DIR = Path("storage")
TASK_REQUEST_FILE_NAME = "request.json"


def get_task_storage_dir(task_id: str) -> Path:
    return BASE_STORAGE_DIR / task_id


def load_task(task_id: str) -> Task:
    task_dir = get_task_storage_dir(task_id)
    request_file = task_dir / TASK_REQUEST_FILE_NAME
    with open(request_file, "r") as f:
        req = TaskRequest.model_validate_json(f.read())
        task = Task(id=task_id, request=req)
        return task


def get_task_documents_paths(task: Task) -> list[Path]:
    return [Path(doc_file) for doc_file in task.request.doc_files]


def load_task_document_image_artifacts(task: Task) -> list[ImageArtifact]:
    task_documents_paths = get_task_documents_paths(task)
    # Assuming get_document_as_images returns a list of images for each document
    # TODO Consider passing the image through technical improvements
    # TODO Consider filtering out images which do not contain relevant data for this task - Reduce costs and processing time
    return [img for doc in task_documents_paths for img in get_document_as_images(doc)]


def process_task(task: Task):
    image_artifacts = load_task_document_image_artifacts(task)
    extract_fn = mock_extract if task.mock_mode else live_extract
    extraction_result = extract_fn(task, image_artifacts)
    return extraction_result


def main():
    parser = argparse.ArgumentParser(description="Run Doc analyzer flow")
    parser.add_argument("id", type=str, help="Inbound task id")

    args = parser.parse_args()

    task_id = args.id

    task = load_task(task_id)
    task.mock_mode = mock_mode_active
    # For CLI run - depend on local files from a predefined task storage folder
    task.request.doc_files = [get_task_storage_dir(task.id) / doc_file for doc_file in task.request.doc_files]
    process_task(task)


if __name__ == "__main__":
    main()
