import datetime
import random
import string
from typing import Mapping
from comprendo.types.consolidated_report import ConsolidatedBatch, ConsolidatedBatchMeasurement, ConsolidatedReport
from comprendo.types.extraction_result import ExtractionResult
from comprendo.types.image_artifact import ImageArtifact
from comprendo.types.measurement_mapping import MeasurementMappingEntry, MeasurementMappingTable
from comprendo.types.task import Task


def random_decide(prob: float = 0.5) -> bool:
    return random.random() < prob


def random_str(length: int = 7) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def random_date(min_days_forward: int, max_days_forward: int) -> str:
    days_forward = random.randint(min_days_forward, max_days_forward)
    # ISO 8601 format date part
    return f"{datetime.date.today() + datetime.timedelta(days=days_forward)}"


mock_potential_descriptions = [
    "Density @ 25°C (g/cm³)",
    "Melting Point (95% purity) °C",
    "Ash Content (muffle furnace) %",
    "Particle Size (D50) μm",
    "Free Acid (HCl equivalent) mg/kg",
    "Moisture Content (oven-dry) %",
    "Refractive Index (20°C)",
    "Tensile Strength (ASTM D882) MPa",
    "Residue on 325 Mesh (% w/w)",
    "Boiling Range (ASTM D1078) °C",
]


def create_random_measurement_descriptions(task: Task, amount: int = 1) -> str:
    assert amount > 0

    if task.request.measurements:
        canonical_names = [m.name for m in task.request.measurements]
    else:
        canonical_names = []

    all_potentials = mock_potential_descriptions + canonical_names
    random.shuffle(all_potentials)

    return all_potentials[:amount]


def create_mock_batch_result(task: Task, description: str) -> ConsolidatedBatchMeasurement:
    return ConsolidatedBatchMeasurement(
        accept=random_decide(0.7),
        description=description,
        flag_disagreement=random_decide(0.3),
        value=round(random.uniform(0, 100), 2) if random_decide(0.8) else True,
    )


def create_mock_consolidated_batch(task) -> ConsolidatedBatch:
    batch_size = random.randint(2, 5)
    descriptions = create_random_measurement_descriptions(task, batch_size)
    return ConsolidatedBatch(
        batch_number=random_str(),
        expiration_date=random_date(30, 300) if random_decide(0.6) else None,
        results=[create_mock_batch_result(task, descriptions[i]) for i in range(batch_size)],
    )


def create_mock_consolidated_report(task: Task, image_artifacts: list[ImageArtifact]) -> ConsolidatedReport:
    # Imagine each image is a page
    # imagine each page is batch
    mock_report = ConsolidatedReport(
        order_number=task.request.order_number,
        product_name="mock produce name",
        flag_identification_warning=random_decide(0.2),
        batches=[create_mock_consolidated_batch(task) for _ in image_artifacts],
    )

    return mock_report


def create_mock_mapping_table(task: Task, consolidated_report: ConsolidatedReport) -> MeasurementMappingTable:
    all_used_measurement_descriptions = set([m.description for b in consolidated_report.batches for m in b.results])
    entries = []
    if task.request.measurements:
        canonical_ids = [m.id for m in task.request.measurements]
        for canonical_id in canonical_ids:
            if random_decide(0.8):
                map_from_desc = random.choice(list(all_used_measurement_descriptions))
                # Don't map form it again
                all_used_measurement_descriptions.remove(map_from_desc)

                if not all_used_measurement_descriptions:  # nothing to map further?
                    break

                entries.append(MeasurementMappingEntry(description=map_from_desc, mapped_to_id=canonical_id))

    return MeasurementMappingTable(entries=entries)


def extract(task: Task, image_artifacts: list[ImageArtifact]):

    consolidated_report: ConsolidatedReport = create_mock_consolidated_report(task, image_artifacts)
    mapping_table: MeasurementMappingTable = create_mock_mapping_table(task, consolidated_report)

    extraction_result = ExtractionResult(measurements_mapping=mapping_table, consolidated_report=consolidated_report)
    return extraction_result
