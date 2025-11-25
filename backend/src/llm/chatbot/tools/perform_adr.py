from langchain.tools import tool
from src.llm.chatbot.tools.tool_context_handler import ToolReg


async def _perform_adr_body(symptom_description: str, medicine_name: str, since_when: str) -> str:
    # This tool is marked for frontend execution
    # The actual ADR report creation will be handled by the frontend
    # which will call the appropriate API endpoint with user confirmation
    return f"ADR report done for medicine '{medicine_name}' with symptoms: {symptom_description} since {since_when}"

@tool
@ToolReg.need_confirmation
@ToolReg.frontend_execution
async def perform_adr(symptom_description: str, medicine_name: str, since_when: str) -> str:
    """
    Initiates an Adverse Drug Reaction (ADR) report for the patient.
    Use this when the patient reports experiencing side effects or adverse reactions to a medication.
    """
    try:
        return await _perform_adr_body(symptom_description, medicine_name, since_when)
    except Exception as e:
        return f"Error initiating ADR report: {str(e)}"
