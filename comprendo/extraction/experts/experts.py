import asyncio
import json
import logging
import pathlib
import time

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from comprendo.caching.cache import SimpleFileCache
from comprendo.extraction.caching import get_namespace_cache_dir
from comprendo.extraction.cost import usage_metadata_to_cost
from comprendo.extraction.experts import enabled_coa_experts
from comprendo.types.image_artifact import ImageArtifact
from comprendo.types.task import Task

logger = logging.getLogger(__name__)


def get_experts_cache_dir(task: Task) -> pathlib.Path:
    return get_namespace_cache_dir(task, "experts")


expert_system_prompt = "You are an expert in the field of material quality analysis and inspection. You output Markdown"

expert_query_prompt = """Please extract the inspection result values and identifying data from the provided document.
Only report results never ranges. Only report results based on the actual content.
Report results for each batch (when absent use lot number) separately.
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


async def extract_from_images_using_expert(expert_llm: BaseChatModel, task: Task, image_artifacts: list[ImageArtifact]):
    logger.info(
        f"Extraction started: model={expert_llm.config['model']}",
        extra={
            "model": expert_llm.config["model"],
            "provider": expert_llm.config.get("provider", ""),
        },
    )
    cache = SimpleFileCache(get_experts_cache_dir(task), experts_cache_context)
    cache_key = f"expert_response_{expert_llm.config['model']}_{expert_llm.config.get('provider', 'default')}"
    cached_response = cache.get(cache_key)
    if cached_response:
        logger.info(f"Using cached response: model={expert_llm.config['model']}, payload={json.dumps(cached_response)}")
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

    invoke_start_time = time.time()
    extraction_message: AIMessage = await expert_llm.ainvoke(prompt)
    invoke_total_time = time.time() - invoke_start_time

    cache.put(cache_key, extraction_message.content)
    logger.info(
        f"Extracted content: model={expert_llm.config['model']}, payload={json.dumps(extraction_message.content)}, time={invoke_total_time:.2f}s",
        extra={
            "time": invoke_total_time,
            "model": expert_llm.config["model"],
            "provider": expert_llm.config.get("provider", ""),
        },
    )

    usage_metadata = extraction_message.usage_metadata
    logger.info(
        f"Extraction usage metadata: model={expert_llm.config['model']}, payload={json.dumps(extraction_message.usage_metadata)}"
    )
    cost = usage_metadata_to_cost(
        expert_llm.config["model"],
        usage_metadata,
        input_images_count=len(image_artifacts),
        model_provider=expert_llm.config.get("provider", ""),
    )
    task.cost += cost
    logger.info(f"Extraction usage cost: model={expert_llm.config['model']}, cost={cost:.7f}")

    return extraction_message.content


async def expert_extraction_from_images(task: Task, image_artifacts: list[ImageArtifact]):
    expert_results = []
    for expert_llm in enabled_coa_experts:
        res_expert_task = extract_from_images_using_expert(expert_llm, task, image_artifacts)
        expert_results.append(res_expert_task)
    expert_results = await asyncio.gather(*expert_results)
    return expert_results
