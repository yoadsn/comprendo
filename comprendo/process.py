import logging
from pathlib import Path

from comprendo.extraction.extract import extract as live_extract
from comprendo.extraction.mock_extract import extract as mock_extract
from comprendo.preprocess.document import get_document_as_images
from comprendo.types.image_artifact import ImageArtifact
from comprendo.types.task import Task


logger = logging.getLogger(__name__)


def load_task_document_image_artifacts(documents_paths: list[Path]) -> list[ImageArtifact]:
    # Assuming get_document_as_images returns a list of images for each document
    # TODO Consider passing the image through technical improvements
    # TODO Consider filtering out images which do not contain relevant data for this task - Reduce costs and processing time
    return [img for doc in documents_paths for img in get_document_as_images(doc)]


def process_task(task: Task, documents_paths: list[Path]):
    logger.info(f"Processing extraction task with {len(documents_paths)} documents")
    image_artifacts = load_task_document_image_artifacts(documents_paths)
    logger.info(f"Derived {len(image_artifacts)} images")
    extract_fn = mock_extract if task.mock_mode else live_extract
    extraction_result = extract_fn(task, image_artifacts)
    return extraction_result
