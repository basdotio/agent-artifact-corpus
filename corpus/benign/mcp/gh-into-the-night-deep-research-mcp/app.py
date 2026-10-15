from mcp.server.fastmcp import FastMCP
import mcp.types as types
from tools import planner, writer, researcher
from uuid import uuid4

from typing import Union, Any
from setup_logging import setup_logger
from schema import PlannerSchema

logger = setup_logger(__name__)

from dotenv import load_dotenv
load_dotenv()

# Create an MCP servermc
mcp = FastMCP("Deep-Research")

# Tool to generate research plan
@mcp.tool()
async def generate_plan(topic: str) -> Union[str, dict[str, Any]]:
    """Generate a draft plan for deep research
    
    Args:
        topic: Topic that is to be researched
    """
    try:
        configurable = {
            "thread_id": str(uuid4()),
            "planner_model": "deepseek-r1-distill-llama-70b",
            "writer_model": "llama-3.3-70b-versatile",
            "status": "awaiting_planner",
            "subtopics": [],
            "feedback": "",
            "findings": [],
            "report": ""
        }
        
        state = {
            "topic": topic,
            "configurable": configurable
        }

        # Use the wrapped state when invoking the tool
        plan = planner(state)
        logger.debug(f"This is plan {plan}")
        return plan
    except Exception as e:
        logger.debug(f"This is error: {e}")
        raise e


# Tool to execute plan
@mcp.tool()
async def execute_plan(plan: PlannerSchema) -> Union[str, dict[str, Any]]:
    """Execute the deep research plan
    
    Args:
        plan: Plan that is supposed to be executed
    """
    try:
        configurable = {
            "thread_id": str(uuid4()),
            "planner_model": "deepseek-r1-distill-llama-70b",
            "writer_model": "llama-3.3-70b-versatile",
            "status": "awaiting_research",
            "subtopics": plan.subtopics,
            "feedback": "",
            "findings": [],
            "report": ""
        }
        
        state = {
            "subtopics": plan.subtopics,
            "configurable": configurable
        }

        config = {"configurable": configurable}
        
        research = researcher(state, config)
        report = writer(research, config)
        logger.debug(f"This is report {report}")
        return report
    except Exception as e:
        logger.debug(f"This is error: {e}")
        raise e


if __name__ == "__main__":
    mcp.run(transport='stdio')