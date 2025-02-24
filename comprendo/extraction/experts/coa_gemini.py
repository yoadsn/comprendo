from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import ChatVertexAI

from comprendo.configuration import app_config
from comprendo.integration.vertexai.credentials import load_google_auth_credentials, is_google_auth_configured

gemini_expert_model_name = "gemini-1.5-flash"
gemini_analysis_expert_llm = ChatGoogleGenerativeAI(
    model=gemini_expert_model_name,
    temperature=0,
    max_tokens=1024,
    timeout=None,
    max_retries=1,
    api_key=app_config.str("GEMINI_API_KEY", None),
).with_config({"model": gemini_expert_model_name})

vertextai_gemini_analysis_expert_llm = None
# Will crash with credentials - so only create if credentials are configured
if is_google_auth_configured():
    vertextai_gemini_analysis_expert_llm = ChatVertexAI(
        model=gemini_expert_model_name,
        temperature=0,
        max_tokens=1024,
        timeout=None,
        max_retries=1,
        # Credentials loaded from env-var
        credentials=load_google_auth_credentials(),
    ).with_config({"model": gemini_expert_model_name, "provider": "vertexai"})
