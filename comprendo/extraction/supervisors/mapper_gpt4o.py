from langchain_openai import ChatOpenAI

from comprendo.types.measurement_mapping import MeasurementMappingTable

supervisor_mapper_model_name = "gpt-4o"
supervisor_mapper_llm = (
    ChatOpenAI(
        model=supervisor_mapper_model_name, temperature=0, max_tokens=None, timeout=None, max_retries=2, streaming=False
    )
    .with_structured_output(MeasurementMappingTable, method="json_schema", include_raw=True)
    .with_config({"run_name": "supervisor_mapper", "model": supervisor_mapper_model_name})
)
