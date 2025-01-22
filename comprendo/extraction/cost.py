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


def usage_metadata_to_cost(model_name: str, usage_metadata: UsageMetadata) -> float:
    token_usage = {"total_tokens": usage_metadata["total_tokens"]}
    completion_tokens = usage_metadata["output_tokens"]
    prompt_tokens = usage_metadata["input_tokens"]
    prompt_tokens_cached = 0
    if "cache_read" in usage_metadata.get("input_token_details", {}):
        prompt_tokens_cached = usage_metadata["input_token_details"]["cache_read"]
    reasoning_tokens = 0
    if "reasoning" in usage_metadata.get("output_token_details", {}):
        reasoning_tokens = usage_metadata["output_token_details"]["reasoning"]
    uncached_prompt_tokens = prompt_tokens - prompt_tokens_cached
    if model_name in OPENAI_MODEL_COST_PER_1K_TOKENS:
        uncached_prompt_cost = get_openai_token_cost_for_model(
            model_name, uncached_prompt_tokens, token_type=TokenType.PROMPT
        )
        cached_prompt_cost = get_openai_token_cost_for_model(
            model_name, prompt_tokens_cached, token_type=TokenType.PROMPT_CACHED
        )
        prompt_cost = uncached_prompt_cost + cached_prompt_cost
        completion_cost = get_openai_token_cost_for_model(
            model_name, completion_tokens, token_type=TokenType.COMPLETION
        )
        return prompt_cost + completion_cost
    elif model_name in ANTHROPIC_MODEL_COST_PER_1K_INPUT_TOKENS:
        return (prompt_tokens / 1000) * ANTHROPIC_MODEL_COST_PER_1K_INPUT_TOKENS[model_name] + (
            completion_tokens / 1000
        ) * ANTHROPIC_MODEL_COST_PER_1K_OUTPUT_TOKENS[model_name]
    elif model_name in GEMINI_MODEL_COST_PER_1K_INPUT_TOKENS:
        return (prompt_tokens / 1000) * GEMINI_MODEL_COST_PER_1K_INPUT_TOKENS[model_name] + (
            completion_tokens / 1000
        ) * GEMINI_MODEL_COST_PER_1K_OUTPUT_TOKENS[model_name]
    else:
        return 0
