import os
import pathlib

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from comprendo.caching.cache import SimpleFileCache
from comprendo.types.consolidated_report import ConsolidatedReport
from comprendo.types.extraction_result import ExtractionResult
from comprendo.types.image_artifact import ImageArtifact
from comprendo.types.measurement_mapping import MeasurementMappingTable
from comprendo.types.task import Task

base_cache_dir = pathlib.Path("analysis_cache")


def get_experts_cache_dir(task: Task) -> pathlib.Path:
    return base_cache_dir / task.id / "experts"


def get_supervisor_consolidation_cache_dir(task: Task) -> pathlib.Path:
    return base_cache_dir / task.id / "supervisor_consolidation"


def get_supervisor_mapping_cache_dir(task: Task) -> pathlib.Path:
    return base_cache_dir / task.id / "supervisor_mapping"


gemini_analysis_expert_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0,
    max_tokens=1024,
    timeout=None,
    max_retries=2,
    api_key=os.environ["GEMINI_API_KEY"],
)

anthropic_analysis_expert_llm = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",
    temperature=0,
    max_tokens=1024,
    timeout=None,
    max_retries=2,
)


supervisor_consolidator_llm = ChatOpenAI(
    model="gpt-4o", temperature=0, max_tokens=None, timeout=None, max_retries=2, streaming=False
).with_structured_output(ConsolidatedReport, method="json_schema")

supervisor_mapper_llm = ChatOpenAI(
    model="gpt-4o", temperature=0, max_tokens=None, timeout=None, max_retries=2, streaming=False
).with_structured_output(MeasurementMappingTable, method="json_schema")


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
    # measurements_description = "\n".join(
    #     [f'{m.name}{" (qualitative)" if m.qualitative else ""}' for m in task.request.measurements]
    # )

    cache = SimpleFileCache(get_experts_cache_dir(task), experts_cache_context)
    cache_key = f"expert_response_{expert_llm._llm_type}"
    cached_response = cache.get(cache_key)
    if cached_response:
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

    extraction_message: ConsolidatedReport = expert_llm.invoke(prompt)
    print(extraction_message.usage_metadata)

    cache.put(cache_key, extraction_message.content)
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

supervisor_consolidation_cache_context = ["1", supervisor_system_prompt, supervisor_consolidation_query_prompt]


def supervisor_consolidation(task: Task, expert_results: list[str]) -> ConsolidatedReport:
    cache = SimpleFileCache(get_supervisor_consolidation_cache_dir(task), supervisor_consolidation_cache_context)
    cache_key = "supervisor"
    supervisor_cached_response = cache.get(cache_key)
    if supervisor_cached_response:
        output_as_json = supervisor_cached_response
        return ConsolidatedReport.model_validate_json(output_as_json)

    expert_responses_inputs = "\n".join(
        [expert_input_template.format(expert_id=i, expert_input=result) for i, result in enumerate(expert_results)]
    )

    prompt = supervisor_consolidation_prompt_template.format_messages(
        expert_inputs=expert_responses_inputs,
    )

    print(prompt[1].content)

    response: ConsolidatedReport = supervisor_consolidator_llm.invoke(prompt)

    cache.put(cache_key, response.model_dump_json())
    return response


supervisor_measurement_mapping_query_prompt = """Here is a list of measurement descriptions coming from analysis reports:

# Raw Measurement Descriptions
{raw_measurement_descriptions}

# Your Task - Map each to the canonical measurement id

Below is the canonical list of measurements in use.
Please consider the meaning of the description and match to each raw description the proper a canonical measurement id.
If no obvious matching canonical measurement id is found - Use "?" as the id to mark "no match".

# Canonical Measurements
{canonical_measurement_list}
"""

supervisor_measurement_mapping_prompt_template = ChatPromptTemplate(
    [SystemMessage(content=supervisor_system_prompt), supervisor_measurement_mapping_query_prompt]
)

supervisor_mapping_cache_context = ["1", supervisor_system_prompt, supervisor_measurement_mapping_query_prompt]


def supervisor_mapping(task: Task, consolidated_report: ConsolidatedReport) -> MeasurementMappingTable:
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

    print(prompt[1].content)

    response: MeasurementMappingTable = supervisor_mapper_llm.invoke(prompt)

    cache.put(cache_key, response.model_dump_json())
    return response


def extract(task: Task, image_artifacts: list[ImageArtifact]):
    res_expert_1 = extract_from_images(anthropic_analysis_expert_llm, task, image_artifacts)
    print(res_expert_1)
    print(f"<-{'-' * 40}->")
    res_expert_2 = extract_from_images(gemini_analysis_expert_llm, task, image_artifacts)
    print(res_expert_2)
    print(f"<-{'-' * 40}->")

    consolidated_report: ConsolidatedReport = supervisor_consolidation(task, [res_expert_1, res_expert_2])
    print_report_formatted(task, consolidated_report)

    mapping_table = supervisor_mapping(task, consolidated_report)
    print_mapping_table(mapping_table)

    extraction_result = ExtractionResult(measurements_mapping=mapping_table, consolidated_report=consolidated_report)
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


def print_mapping_table(mapping_table: MeasurementMappingTable) -> None:
    print("=== Measurement Mapping Table ===")
    for entry in mapping_table.entries:
        print(f"{entry.mapped_to_id}: {entry.description}")