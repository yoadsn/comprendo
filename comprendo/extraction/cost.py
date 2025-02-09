import re

from langchain_core.messages.ai import UsageMetadata
from langchain_community.callbacks.openai_info import (
    get_openai_token_cost_for_model,
    MODEL_COST_PER_1K_TOKENS as OPENAI_MODEL_COST_PER_1K_TOKENS,
    TokenType,
)
from langchain_community.callbacks.bedrock_anthropic_callback import (
    MODEL_COST_PER_1K_INPUT_TOKENS as BEDROCK_ANTHROPIC_MODEL_COST_PER_1K_INPUT_TOKENS,
    MODEL_COST_PER_1K_OUTPUT_TOKENS as BEDROCK_ANTHROPIC_MODEL_COST_PER_1K_OUTPUT_TOKENS,
)


def standardize_anthropic_model_name(model_name: str) -> str:
    # I don't like this hack - but hardcoding is even worse
    return re.sub("-v\d+$", "", model_name.split(":")[0].removeprefix("anthropic."))


# Remove the bedrock part from the model name
ANTHROPIC_MODEL_COST_PER_1K_INPUT_TOKENS = {
    standardize_anthropic_model_name(k): v for k, v in BEDROCK_ANTHROPIC_MODEL_COST_PER_1K_INPUT_TOKENS.items()
}
ANTHROPIC_MODEL_COST_PER_1K_OUTPUT_TOKENS = {
    standardize_anthropic_model_name(k): v for k, v in BEDROCK_ANTHROPIC_MODEL_COST_PER_1K_OUTPUT_TOKENS.items()
}

GEMINI_MODEL_COST_PER_1K_INPUT_TOKENS = {
    "gemini-1.5-flash": 0.075 / 1000,
    "gemini-1.5-flash-long": 0.15 / 1000,
    "gemini-1.5-pro": 1.25 / 1000,
    "gemini-1.5-pro-long": 2.5 / 1000,
}
GEMINI_MODEL_COST_PER_1K_OUTPUT_TOKENS = {
    "gemini-1.5-flash": 0.30 / 1000,
    "gemini-1.5-flash-long": 0.60 / 1000,
    "gemini-1.5-pro": 5.0 / 1000,
    "gemini-1.5-pro-long": 10.00 / 1000,
}


# Gemini 1.5 Pricing counts in characters. Assume about 4 chars per token
VERTEX_AI_TOKEN_CHARS_RATIO = 4
VERTEXAI_GEMINI_MODEL_COST_PER_1_INPUT_IMAGES = {"vertexai-gemini-1.5-flash": 0.00002}
VERTEXAI_GEMINI_MODEL_COST_PER_1K_INPUT_TOKENS = {"vertexai-gemini-1.5-flash": 0.00001875 * VERTEX_AI_TOKEN_CHARS_RATIO}
VERTEXAI_GEMINI_MODEL_COST_PER_1K_OUTPUT_TOKENS = {"vertexai-gemini-1.5-flash": 0.000075 * VERTEX_AI_TOKEN_CHARS_RATIO}


def usage_metadata_to_cost(
    model_name: str, usage_metadata: UsageMetadata, model_provider: str = None, input_images_count: int = 0
) -> float:
    cost_lookup_key = model_name
    if model_provider is not None:
        cost_lookup_key = f"{model_provider}-{model_name}"
    completion_tokens = usage_metadata["output_tokens"]
    prompt_tokens = usage_metadata["input_tokens"]
    prompt_tokens_cached = 0
    if "cache_read" in usage_metadata.get("input_token_details", {}):
        prompt_tokens_cached = usage_metadata["input_token_details"]["cache_read"]
    reasoning_tokens = 0
    if "reasoning" in usage_metadata.get("output_token_details", {}):
        reasoning_tokens = usage_metadata["output_token_details"]["reasoning"]
    uncached_prompt_tokens = prompt_tokens - prompt_tokens_cached

    if cost_lookup_key in OPENAI_MODEL_COST_PER_1K_TOKENS:
        uncached_prompt_cost = get_openai_token_cost_for_model(
            cost_lookup_key, uncached_prompt_tokens, token_type=TokenType.PROMPT
        )
        cached_prompt_cost = get_openai_token_cost_for_model(
            cost_lookup_key, prompt_tokens_cached, token_type=TokenType.PROMPT_CACHED
        )
        prompt_cost = uncached_prompt_cost + cached_prompt_cost
        completion_cost = get_openai_token_cost_for_model(
            cost_lookup_key, completion_tokens, token_type=TokenType.COMPLETION
        )
        return prompt_cost + completion_cost

    elif cost_lookup_key in ANTHROPIC_MODEL_COST_PER_1K_INPUT_TOKENS:
        return (prompt_tokens / 1000) * ANTHROPIC_MODEL_COST_PER_1K_INPUT_TOKENS[cost_lookup_key] + (
            completion_tokens / 1000
        ) * ANTHROPIC_MODEL_COST_PER_1K_OUTPUT_TOKENS[cost_lookup_key]

    elif cost_lookup_key in GEMINI_MODEL_COST_PER_1K_INPUT_TOKENS:
        return (prompt_tokens / 1000) * GEMINI_MODEL_COST_PER_1K_INPUT_TOKENS[cost_lookup_key] + (
            completion_tokens / 1000
        ) * GEMINI_MODEL_COST_PER_1K_OUTPUT_TOKENS[cost_lookup_key]

    elif cost_lookup_key in VERTEXAI_GEMINI_MODEL_COST_PER_1K_OUTPUT_TOKENS:
        return (
            (prompt_tokens / 1000) * VERTEXAI_GEMINI_MODEL_COST_PER_1K_INPUT_TOKENS[cost_lookup_key]
            + (input_images_count) * VERTEXAI_GEMINI_MODEL_COST_PER_1_INPUT_IMAGES[cost_lookup_key]
            + (completion_tokens / 1000) * VERTEXAI_GEMINI_MODEL_COST_PER_1K_OUTPUT_TOKENS[cost_lookup_key]
        )
    else:
        return 0
