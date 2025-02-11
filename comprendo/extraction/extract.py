import logging

from comprendo.extraction.experts.experts import expert_extraction_from_images
from comprendo.extraction.supervisors.supervisors import (
    supervisor_consolidation,
    supervisor_mapping,
)
from comprendo.types.consolidated_report import ConsolidatedReport
from comprendo.types.extraction_result import ExtractionResult
from comprendo.types.image_artifact import ImageArtifact
from comprendo.types.measurement_mapping import MeasurementMappingTable
from comprendo.types.task import Task

logger = logging.getLogger(__name__)


def remap_measurements_to_canonical(
    task: Task, consolidated_report: ConsolidatedReport, mapping_table: MeasurementMappingTable
) -> ConsolidatedReport:
    # Go over all measurement descriptions.
    # Either map them to a canonical (if description is found in mapping table)
    # or leave them unmapped
    lookup = {e.raw_description.strip().lower(): e.mapped_to_canonical_id for e in mapping_table.entries}
    canonical_names = set([m.name for m in task.request.measurements])

    for batch in consolidated_report.batches:
        # first pass - assign ids to canonicals. They take priority
        used_canonical_ids = set()
        for m in batch.results:
            if m.description in canonical_names:
                found_mapped_id = lookup.get(m.description.strip().lower())
                if found_mapped_id:
                    m.id = found_mapped_id
                    used_canonical_ids.add(found_mapped_id)

        for m in batch.results:
            found_mapped_id = lookup.get(m.description.strip().lower())
            if (
                found_mapped_id
                # Ensure thius mapped id was not taken by another measurement already
                and not found_mapped_id in used_canonical_ids
            ):
                used_canonical_ids.add(found_mapped_id)
                m.id = found_mapped_id

    return consolidated_report


def generate_extraction_result(
    task: Task, consolidated_report: ConsolidatedReport, mapping_table: MeasurementMappingTable
) -> ExtractionResult:
    consolidated_report = remap_measurements_to_canonical(task, consolidated_report, mapping_table)

    final_extraction_results = ExtractionResult(request_id=task.request.id, consolidated_report=consolidated_report)
    logger.info(f"Final extraction results: payload={final_extraction_results.model_dump_json()}")
    return final_extraction_results


async def extract(task: Task, image_artifacts: list[ImageArtifact]):
    expert_results = await expert_extraction_from_images(task, image_artifacts)

    consolidated_report: ConsolidatedReport = await supervisor_consolidation(task, expert_results)
    # print_report_formatted(task, consolidated_report)

    mapping_table = await supervisor_mapping(task, consolidated_report)
    # print_mapping_table(mapping_table)

    extraction_result = generate_extraction_result(task, consolidated_report, mapping_table)

    logger.info(f"Total extraction cost: cost={task.cost:.7f}")

    return extraction_result


def print_report_formatted(task: Task, report: ConsolidatedReport) -> None:
    # Print header
    print("=== Analysis Report ===")
    print(f"Product Name: {report.product_name or 'N/A'}")
    print(f"Order Number: {report.order_number or 'N/A'}")
    print(f"Identification Warning: {'Yes' if report.flag_identification_warning else 'No'}")
    print("\n=== Results ===")

    for batch in report.batches:
        print(f"Batch Number: {batch.batch_number or 'N/A'}")
        print(f"Exp. Date: {batch.expiration_date or 'N/A'}")

        # Print table header
        header = f"{'Measurement Name':<40}{'Value':<20}{'Accept':<10}{'Disagreement':<15}"
        print(header)
        print("=" * len(header))

        # Print each result
        for result in batch.results:
            measurement_desc = result.description
            value_str = str(result.value) if result.value is not None else "None"
            accepted_str = "Yes" if result.accept else "No"
            disagreement_str = "Yes" if result.flag_disagreement else "No"
            print(f"{measurement_desc:<40}{value_str:<20}{accepted_str:<10}{disagreement_str:<15}")
    print(f"<-{'-' * 40}->")


def print_mapping_table(mapping_table: MeasurementMappingTable) -> None:
    print("=== Measurement Mapping Table ===")
    for entry in mapping_table.entries:
        print(f"{entry.mapped_to_canonical_id}: {entry.raw_description}")
    print(f"<-{'-' * 40}->")
