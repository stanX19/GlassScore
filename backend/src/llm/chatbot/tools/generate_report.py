from langchain.tools import tool
from src.llm.chatbot.tools.tool_context_handler import ToolReg


async def _generate_report_body() -> str:
    # This tool is marked for frontend execution with personal data confirmation
    # The frontend will handle PDF generation through the appropriate API endpoint
    return f"Report has been generated and user has been redirected"

@tool
@ToolReg.need_personal_data_confirmation
@ToolReg.frontend_execution
async def generate_report() -> str:
    """
    Generates a comprehensive medical report (PDF) for the patient.
    Use this when the patient requests a report of their medical history or ADR report.

    Returns:
        Confirmation that the report has been generated and is ready for download
    """
    try:
        return await _generate_report_body()
    except Exception as e:
        return f"Error generating report: {str(e)}"
