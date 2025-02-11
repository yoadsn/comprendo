import json
import logging
import pathlib
import time
from typing import Optional

from langchain_core.load import dumps
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_openai import ChatOpenAI

from comprendo.caching.cache import SimpleFileCache
from comprendo.extraction.caching import get_namespace_cache_dir
from comprendo.extraction.cost import usage_metadata_to_cost
from comprendo.types.consolidated_report import ConsolidatedReport
from comprendo.types.measurement_mapping import (
    MeasurementMappingEntry,
    MeasurementMappingTable,
)
from comprendo.extraction.supervisors.consolidator_gpt4o import supervisor_consolidator_llm
from comprendo.extraction.supervisors.mapper_gpt4o import supervisor_mapper_llm
from comprendo.types.task import Task

logger = logging.getLogger(__name__)


def get_supervisor_consolidation_cache_dir(task: Task) -> pathlib.Path:
    return get_namespace_cache_dir(task, "supervisor_consolidation")


def get_supervisor_mapping_cache_dir(task: Task) -> pathlib.Path:
    return get_namespace_cache_dir(task, "supervisor_mapping")


supervisor_system_prompt = "You are an inspection analysis process supervisor"
supervisor_consolidation_query_prompt = """Here are the same inspection results of multiple batches / materials by independent experts:

{expert_inputs}
# Your Task - Consolidate results

Please consolidate expert responses into a coherent analysis report.

Qualitative results should be reported as Boolean values: accept=True / reject=False
If there is a disagreement between experts - Flag the inspected value.
Sometimes no batch number is reported - use the lot number instead.
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

expert_input_template = PromptTemplate.from_template("# Expert {expert_id}\n\n{expert_input}\n\n")


async def supervisor_consolidation(task: Task, expert_results: list[str]) -> ConsolidatedReport:
    logger.info(
        f"Consolidating {len(expert_results)} expert results: model={supervisor_consolidator_llm.config['model']}"
    )
    cache = SimpleFileCache(get_supervisor_consolidation_cache_dir(task), supervisor_consolidation_cache_context)
    cache_key = "supervisor"
    supervisor_cached_response = cache.get(cache_key)
    if supervisor_cached_response:
        logger.info(
            f"Using cached supervisor consolidation response: model={supervisor_consolidator_llm.config['model']}, payload={supervisor_cached_response}"
        )
        output_as_json = supervisor_cached_response
        return ConsolidatedReport.model_validate_json(output_as_json)

    expert_responses_inputs = "\n".join(
        [expert_input_template.format(expert_id=i, expert_input=result) for i, result in enumerate(expert_results)]
    )

    prompt = supervisor_consolidation_prompt_template.format_messages(
        expert_inputs=expert_responses_inputs,
    )

    logger.info(
        f"Invoking supervisor consolidator with prompt: model={supervisor_consolidator_llm.config['model']}, payload={dumps(prompt)}"
    )

    invoke_start_time = time.time()
    full_response: dict = await supervisor_consolidator_llm.ainvoke(prompt)
    invoke_total_time = time.time() - invoke_start_time

    response: ConsolidatedReport = full_response["parsed"]
    response_message: AIMessage = full_response["raw"]
    parsing_error: Optional[BaseException] = full_response["parsing_error"]
    if parsing_error:
        logger.error(
            f"Error parsing supervisor consolidation response: model={supervisor_consolidator_llm.config['model']}, error={parsing_error}"
        )
        raise parsing_error

    usage_metadata = response_message.usage_metadata
    logger.info(
        f"Supervisor consolidation usage metadata: model={supervisor_consolidator_llm.config['model']}, payload={response_message.usage_metadata}"
    )
    cost = usage_metadata_to_cost(supervisor_consolidator_llm.config["model"], usage_metadata)
    task.cost += cost
    logger.info(
        f"Supervisor consolidation cost: model={supervisor_consolidator_llm.config['model']}, cost={cost:.7f}",
        extra={"model": supervisor_consolidator_llm.config["model"]},
    )

    response_as_json_dump = response.model_dump_json()
    cache.put(cache_key, response_as_json_dump)
    logger.info(
        f"Supervisor consolidation response: model={supervisor_consolidator_llm.config['model']}, payload={response_as_json_dump}, time={invoke_total_time:.2f}s",
        extra={"time": invoke_total_time, "model": supervisor_consolidator_llm.config["model"]},
    )

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


async def supervisor_mapping(task: Task, consolidated_report: ConsolidatedReport) -> MeasurementMappingTable:
    logger.info(f"Invoking supervisor mapping of consolidated report: model={supervisor_mapper_llm.config['model']}")
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

    logger.info(f"Supervisor mapping prompt: model={supervisor_mapper_llm.config['model']}, payload={dumps(prompt)}")

    invoke_start_time = time.time()
    full_response: dict = await supervisor_mapper_llm.ainvoke(prompt)
    invoke_total_time = time.time() - invoke_start_time

    response: MeasurementMappingTable = full_response["parsed"]
    response_message: AIMessage = full_response["raw"]
    parsing_error: Optional[BaseException] = full_response["parsing_error"]
    if parsing_error:
        logger.error(
            f"Error parsing supervisor mapping response: model={supervisor_mapper_llm.config['model']}, error={parsing_error}"
        )
        raise parsing_error

    usage_metadata = response_message.usage_metadata
    logger.info(
        f"Supervisor mapping usage metadata: model={supervisor_mapper_llm.config['model']}, payload={response_message.usage_metadata}"
    )
    cost = usage_metadata_to_cost(supervisor_mapper_llm.config["model"], usage_metadata)
    task.cost += cost
    logger.info(
        f"Supervisor mapping cost: model={supervisor_mapper_llm.config['model']}, cost={cost:.7f}",
        {"model": {supervisor_mapper_llm.config["model"]}},
    )

    logger.info(
        f"Supervisor mapping llm response: model={supervisor_mapper_llm.config['model']}, payload={response.model_dump_json()}, time={invoke_total_time:.2f}s",
        extra={"time": invoke_total_time, "model": supervisor_mapper_llm.config["model"]},
    )

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
    logger.info(
        f"Supervisor mapping final result: model={supervisor_mapper_llm.config['model']}, payload={response_as_json_dump}"
    )
    return response
