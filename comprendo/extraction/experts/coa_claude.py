from langchain_anthropic import ChatAnthropic

anthropic_legacy_expert_model_name = "claude-3-5-sonnet-20240620"
anthropic_claude_3_5_analysis_expert_llm = ChatAnthropic(
    model=anthropic_legacy_expert_model_name,
    temperature=0,
    max_tokens=1024,
    timeout=None,
    max_retries=1,
).with_config({"model": anthropic_legacy_expert_model_name})


anthropic_expert_model_name = "claude-3-7-sonnet-20250219"
anthropic_analysis_expert_llm = ChatAnthropic(
    model=anthropic_expert_model_name,
    temperature=0,
    max_tokens=1024,
    timeout=None,
    max_retries=1,
).with_config({"model": anthropic_expert_model_name})
