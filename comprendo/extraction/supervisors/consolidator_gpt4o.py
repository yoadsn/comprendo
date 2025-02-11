from langchain_openai import ChatOpenAI

from comprendo.types.consolidated_report import ConsolidatedReport

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
