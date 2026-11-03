import logging
from app.services.report_service import ReportService
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def report_generation_node(state: SimulationState) -> SimulationState:
    """
    LangGraph Node: Executive Report Generation
    Compiles executive summary, metrics comparison, impact breakdown, and action plan into the final report.
    """
    logger.info("[report_generation_node] Compiling executive report")
    state["current_node"] = "report_generation"
    service = ReportService()

    try:
        final_report = await service.generate_report(state)
        state["final_report"] = final_report
        state["status"] = "COMPLETED"
        logger.info(f"[report_generation_node] Executive report {final_report.get('report_id')} generated successfully")
    except Exception as exc:
        logger.error(f"[report_generation_node] Report generation error: {exc}")
        state["final_report"] = {
            "report_id": "ERR-REPORT",
            "title": "Failed Report Generation",
            "error": str(exc),
            "markdown_report": f"# Error Generating Report\n\n{exc}",
        }
        state["status"] = "FAILED"
        state["error"] = str(exc)

    return state
