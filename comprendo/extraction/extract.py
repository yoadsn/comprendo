import logging
import os
import pathlib
import json
from typing import Optional


from langchain_anthropic import ChatAnthropic
from langchain_core.load import dumps
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from comprendo.configuration import app_config
from comprendo.caching.cache import SimpleFileCache
from comprendo.types.consolidated_report import ConsolidatedReport
from comprendo.types.extraction_result import ExtractionResult
from comprendo.types.image_artifact import ImageArtifact
from comprendo.types.measurement_mapping import MeasurementMappingEntry, MeasurementMappingTable
from comprendo.types.task import Task
from comprendo.extraction.cost import usage_metadata_to_cost

base_cache_dir = pathlib.Path("analysis_cache")

logger = logging.getLogger(__name__)


def get_experts_cache_dir(task: Task) -> pathlib.Path:
    return base_cache_dir / task.request.id / "experts"


def get_supervisor_consolidation_cache_dir(task: Task) -> pathlib.Path:
    return base_cache_dir / task.request.id / "supervisor_consolidation"


def get_supervisor_mapping_cache_dir(task: Task) -> pathlib.Path:
    return base_cache_dir / task.request.id / "supervisor_mapping"


gemini_expert_model_name = "gemini-1.5-flash"
gemini_analysis_expert_llm = ChatGoogleGenerativeAI(
    model=gemini_expert_model_name,
    temperature=0,
    max_tokens=1024,
    timeout=None,
    max_retries=1,
    api_key=app_config.str("GEMINI_API_KEY", None),
).with_config({"model": gemini_expert_model_name})

anthropic_expert_model_name = "claude-3-5-sonnet-20240620"
anthropic_analysis_expert_llm = ChatAnthropic(
    model=anthropic_expert_model_name,
    temperature=0,
    max_tokens=1024,
    timeout=None,
    max_retries=1,
).with_config({"model": anthropic_expert_model_name})

supervisor_consolidator_model_name = "gpt-4o"
supervisor_consolidator_llm = (
    ChatOpenAI(
        model=supervisor_consolidator_model_name,
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        streaming=False,
    )
    .with_structured_output(ConsolidatedReport, method="json_schema", include_raw=True)
    .with_config({"run_name": "supervisor_consolidator", "model": supervisor_consolidator_model_name})
)

supervisor_mapper_model_name = "gpt-4o"
supervisor_mapper_llm = (
    ChatOpenAI(
        model=supervisor_mapper_model_name, temperature=0, max_tokens=None, timeout=None, max_retries=2, streaming=False
    )
    .with_structured_output(MeasurementMappingTable, method="json_schema", include_raw=True)
    .with_config({"run_name": "supervisor_mapper", "model": supervisor_mapper_model_name})
)


expert_system_prompt = "You are an expert in the field of material quality analysis and inspection. You output Markdown"

expert_query_prompt = """Please extract the inspection result values and identifying data from the provided document.
Only report results never ranges. Only report results based on the actual content.
Report results for each batch separately.
# General details to extract:
purchase order no.
## Each batch:
batch no.
expiration date
batch results:
- measurement: result, Accept/Reject
- ...
"""


expert_prompt_template = ChatPromptTemplate(
    [
        SystemMessage(content=expert_system_prompt),
        ("placeholder", "{images}"),
        expert_query_prompt,
    ]
)

experts_cache_context = ["1", expert_system_prompt, expert_query_prompt]


def extract_from_images(expert_llm: BaseChatModel, task: Task, image_artifacts: list[ImageArtifact]):
    logger.info(f"Extraction using {expert_llm.config['model']}")
    cache = SimpleFileCache(get_experts_cache_dir(task), experts_cache_context)
    cache_key = f"expert_response_{expert_llm.config['model']}"
    cached_response = cache.get(cache_key)
    if cached_response:
        logger.info(f"Using cached response from {expert_llm.config['model']}: payload={json.dumps(cached_response)}")
        return cached_response

    images_message = HumanMessage(
        content=[
            {
                "type": "image_url",
                "image_url": {"url": f"data:{image_artifact.mime_type};base64,{image_artifact.base64}"},
            }
            for image_artifact in image_artifacts
        ],
    )

    prompt = expert_prompt_template.format_messages(
        images=[images_message],
    )

    extraction_message: AIMessage = expert_llm.invoke(prompt)
    usage_metadata = extraction_message.usage_metadata
    logger.info(f"Extraction usage metadata: payload={json.dumps(extraction_message.usage_metadata)}")
    cost = usage_metadata_to_cost(expert_llm.config["model"], usage_metadata)
    task.cost += cost
    logger.info(f"Extraction usage cost: {cost:.7f}")

    cache.put(cache_key, extraction_message.content)
    logger.info(f"Extracted content: payload={json.dumps(extraction_message.content)}")
    return extraction_message.content


expert_input_template = PromptTemplate.from_template("# Expert {expert_id}\n\n{expert_input}\n\n")

supervisor_system_prompt = "You are an inspection analysis process supervisor"
supervisor_consolidation_query_prompt = """Here are the same inspection results of multiple batches / materials by independent experts:

{expert_inputs}
# Your Task - Consolidate results

Please consolidate expert responses into a coherent analysis report.

Qualitative results should be reported as Boolean values: accept=True / reject=False
If there is a disagreement between experts - Flag the inspected value.
Compensate for descriptions and units as much as possible - identification may not be precise.
If the identification of the inspection like batch no. purchase order no. etc. is incoherent between experts - flag this as an identification warning.
Measurements description should be descriptive and based on the reported measurements only"""

supervisor_consolidation_prompt_template = ChatPromptTemplate(
    [
        SystemMessage(content=supervisor_system_prompt),
        supervisor_consolidation_query_prompt,
    ]
)

supervisor_consolidation_cache_context = [
    "1",
    supervisor_system_prompt,
    supervisor_consolidation_query_prompt,
    json.dumps(ConsolidatedReport.model_json_schema()),
]


def supervisor_consolidation(task: Task, expert_results: list[str]) -> ConsolidatedReport:
    logger.info(
        f'Consolidating {len(expert_results)} expert results using {supervisor_consolidator_llm.config["model"]}'
    )
    cache = SimpleFileCache(get_supervisor_consolidation_cache_dir(task), supervisor_consolidation_cache_context)
    cache_key = "supervisor"
    supervisor_cached_response = cache.get(cache_key)
    if supervisor_cached_response:
        logger.info(f"Using cached supervisor consolidation response: {supervisor_cached_response}")
        output_as_json = supervisor_cached_response
        return ConsolidatedReport.model_validate_json(output_as_json)

    expert_responses_inputs = "\n".join(
        [expert_input_template.format(expert_id=i, expert_input=result) for i, result in enumerate(expert_results)]
    )

    prompt = supervisor_consolidation_prompt_template.format_messages(
        expert_inputs=expert_responses_inputs,
    )

    logger.info(f"Invoking supervisor consolidator with prompt: payload={dumps(prompt)}")

    full_response: dict = supervisor_consolidator_llm.invoke(prompt)
    response: ConsolidatedReport = full_response["parsed"]
    response_message: AIMessage = full_response["raw"]
    parsing_error: Optional[BaseException] = full_response["parsing_error"]
    if parsing_error:
        logger.error(f"Error parsing supervisor consolidation response: {parsing_error}")
        raise parsing_error

    usage_metadata = response_message.usage_metadata
    logger.info(f"Supervisor consolidation usage metadata: payload={response_message.usage_metadata}")
    cost = usage_metadata_to_cost(supervisor_consolidator_llm.config["model"], usage_metadata)
    task.cost += cost
    logger.info(f"Supervisor consolidation cost: {cost:.7f}")

    response_as_json_dump = response.model_dump_json()
    cache.put(cache_key, response_as_json_dump)
    logger.info(f"Supervisor consolidation response: payload={response_as_json_dump}")

    return response


supervisor_measurement_mapping_query_prompt = """Here is a list of measurement descriptions coming from analysis reports:

# Raw Measurement Descriptions
{raw_measurement_descriptions}

# Your Task - Map each to the canonical measurement id

Below is the canonical list of measurements in use.
Please consider the meaning of the description and match to each raw description the proper canonical measurement id.
If no apparent match is found - Use "?" as the id to mark "no match".
Partial matches are expected.

# Canonical Measurements
{canonical_measurement_list}
"""

supervisor_measurement_mapping_prompt_template = ChatPromptTemplate(
    [SystemMessage(content=supervisor_system_prompt), supervisor_measurement_mapping_query_prompt]
)

supervisor_mapping_cache_context = [
    "1",
    supervisor_system_prompt,
    supervisor_measurement_mapping_query_prompt,
    json.dumps(MeasurementMappingTable.model_json_schema()),
]


def supervisor_mapping(task: Task, consolidated_report: ConsolidatedReport) -> MeasurementMappingTable:
    logger.info(f'Invoking supervisor mapping of consolidated report using {supervisor_mapper_llm.config["model"]}')
    cache = SimpleFileCache(get_supervisor_mapping_cache_dir(task), supervisor_mapping_cache_context)
    cache_key = "supervisor"
    supervisor_cached_response = cache.get(cache_key)
    if supervisor_cached_response:
        output_as_json = supervisor_cached_response
        return MeasurementMappingTable.model_validate_json(output_as_json)

    canonical_measurements_spec_rows = "\n".join([f"{m.id}: {m.name}" for m in task.request.measurements])

    # Gather all raw measurement descriptions from the report
    raw_descs = list(set([r.description for b in consolidated_report.batches for r in b.results]))
    raw_descs_str = "\n".join(raw_descs)

    prompt = supervisor_measurement_mapping_prompt_template.format_messages(
        raw_measurement_descriptions=raw_descs_str,
        canonical_measurement_list=canonical_measurements_spec_rows,
    )

    logger.info(f"Supervisor mapping prompt: payload={dumps(prompt)}")

    full_response: dict = supervisor_mapper_llm.invoke(prompt)
    response: MeasurementMappingTable = full_response["parsed"]
    response_message: AIMessage = full_response["raw"]
    parsing_error: Optional[BaseException] = full_response["parsing_error"]
    if parsing_error:
        logger.error(f"Error parsing supervisor mapping response: {parsing_error}")
        raise parsing_error

    usage_metadata = response_message.usage_metadata
    logger.info(f"Supervisor mapping usage metadata: payload={response_message.usage_metadata}")
    cost = usage_metadata_to_cost(supervisor_mapper_llm.config["model"], usage_metadata)
    task.cost += cost
    logger.info(f"Supervisor mapping cost: {cost:.7f}")

    logger.info(f"Supervisor mapping llm response: payload={response.model_dump_json()}")

    # Add to the table the canonicals as well.
    # If the report contains verbatim canonical descriptions
    # We need to set the proper id on them as well
    response.entries = response.entries + [
        MeasurementMappingEntry(
            raw_description=m.name,
            mapped_to_canonical_id=m.id,
        )
        for m in task.request.measurements
    ]

    # Remove entries which do not map to a valid id
    valid_canonical_ids = set(m.id for m in task.request.measurements)
    response.entries = [e for e in response.entries if e.mapped_to_canonical_id in valid_canonical_ids]

    response_as_json_dump = response.model_dump_json()
    cache.put(cache_key, response_as_json_dump)
    logger.info(f"Supervisor mapping final result: payload={response_as_json_dump}")
    return response


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


def extract(task: Task, image_artifacts: list[ImageArtifact]):
    res_expert_1 = extract_from_images(anthropic_analysis_expert_llm, task, image_artifacts)
    res_expert_2 = extract_from_images(gemini_analysis_expert_llm, task, image_artifacts)

    consolidated_report: ConsolidatedReport = supervisor_consolidation(task, [res_expert_1, res_expert_2])
    # print_report_formatted(task, consolidated_report)

    mapping_table = supervisor_mapping(task, consolidated_report)
    # print_mapping_table(mapping_table)

    extraction_result = generate_extraction_result(task, consolidated_report, mapping_table)

    logger.info(f"Total extraction cost: {task.cost:.7f}")

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
