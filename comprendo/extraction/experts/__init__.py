import logging

from comprendo.configuration import app_config
from comprendo.extraction.experts.coa_claude import anthropic_analysis_expert_llm
from comprendo.extraction.experts.coa_gemini import (
    gemini_analysis_expert_llm,
    vertextai_gemini_analysis_expert_llm,
)

logger = logging.getLogger(__name__)

available_coa_experts = {
    "anthropic-claude-3-5-sonnet": anthropic_analysis_expert_llm,
    "gemini-1-5-flash": gemini_analysis_expert_llm,
    "vertexai-gemini-1-5-flash": vertextai_gemini_analysis_expert_llm,
}

_added_coa_experts = set()
enabled_coa_experts = []
for coa_expert_idx in range(10):
    coa_expert_name = app_config.str(f"COA_EXPERT_{coa_expert_idx}", None)
    if coa_expert_name is not None:
        if coa_expert_name in available_coa_experts:
            if coa_expert_name not in _added_coa_experts and available_coa_experts[coa_expert_name]:
                _added_coa_experts.add(coa_expert_name)
                enabled_coa_experts.append(available_coa_experts[coa_expert_name])
                logger.info(f"Enabled COA expert: {coa_expert_name}")
            else:
                logger.warning(f"COA expert {coa_expert_name} already chosen - skipping")
        else:
            logger.warning(f"COA expert {coa_expert_name} not available/configured or not found")
