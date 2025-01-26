from io import BytesIO
import os
from pathlib import Path

import magic
from pdf2image import convert_from_path
from PIL import Image

from comprendo.configuration import app_config
from comprendo.types.image_artifact import ImageArtifact


disable_pdf_to_image = app_config.bool("DISABLE_PDF_TO_IMAGE", False)


def detect_file_type(file_path: Path):
    # Create a magic object
    mime = magic.Magic(mime=True)

    # Identify the MIME type of the file
    mime_type = mime.from_file(file_path)

    return mime_type


def is_image_mime(mime: str) -> bool:
    return mime.startswith("image/")


def is_pdf_mime(mime: str) -> bool:
    return mime == "application/pdf"


def get_document_as_images(document_location: Path) -> list[ImageArtifact]:
    file_mime = detect_file_type(document_location)

    if is_pdf_mime(file_mime):
        pil_images = None
        # If cache sub folder files exists next to the document
        #  load all png images in it instead of converting the pdf to images
        # Order them by the name ascending

        cache_folder_path = document_location.parent / f"to_image_cache"
        cache_file_name_base = document_location.stem
        if cache_folder_path.exists():
            png_files = sorted(cache_folder_path.glob(f"{cache_file_name_base}.*.png"))
            if png_files:
                pil_images = [Image.open(png_file) for png_file in png_files]

        if disable_pdf_to_image:
            return []

        if not pil_images:
            # TODO - detect "image scanned pdfs" - and extract the image instead of rendering the pdf to an image
            # TODO - cache conversion output for restarts
            # TODO - consider other format that work better for text docs
            # Convert PDF to images; get the first page by default
            pil_images = convert_from_path(document_location, fmt="png")

            # store in the cache folder for subsequent runs
            # Create the cache folder if it doesn't exist

            cache_folder_path.mkdir(parents=True, exist_ok=True)
            for idx, pil_image in enumerate(pil_images):
                pil_image.save(cache_folder_path / f"{cache_file_name_base}.{idx}.png")

        if pil_images:
            result_images: list[ImageArtifact] = []
            for pil_image in pil_images:
                result_images.append(ImageArtifact.from_pil_image(pil_image))
            return result_images
        else:
            raise ValueError("The PDF file could not be converted.")

    elif is_image_mime(file_mime):
        # Open image using Pillow
        # TODO - make sure image format is one of the commonly supported image types by the target models
        with Image.open(document_location) as img:
            return [ImageArtifact.from_pil_image(img)]

    else:
        raise ValueError(f"Unknown file type: {file_mime}")
