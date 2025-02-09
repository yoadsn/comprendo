from langchain_anthropic import ChatAnthropic

anthropic_expert_model_name = "claude-3-5-sonnet-20240620"
anthropic_analysis_expert_llm = ChatAnthropic(
    model=anthropic_expert_model_name,
    temperature=0,
    max_tokens=1024,
    timeout=None,
    max_retries=1,
).with_config({"model": anthropic_expert_model_name})
