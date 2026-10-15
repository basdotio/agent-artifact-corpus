from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from typing import Dict, Any, List
from langchain_community.tools import TavilySearchResults
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from schema import PlannerSchema

from dotenv import load_dotenv
load_dotenv()

search_tool = TavilySearchResults()

planner_llm = ChatGroq(model="deepseek-r1-distill-llama-70b", temperature=0.5).with_structured_output(PlannerSchema)
writer_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)


from setup_logging import setup_logger

logger = setup_logger(__name__)


def planner(state: Dict[str, Any]) -> Dict[str, Any]:
    """Tool for planning research subtopics"""
    try:            
        topic = state["topic"]
        prompt = PromptTemplate.from_template("You are an expect researcher. Create a plan for research by breaking down the topic '{topic}' into 3 research subtopics.")
        plan_chain = prompt | planner_llm
        result = plan_chain.invoke({"topic": topic})
        
        result = result.model_dump()

        state["configurable"]["subtopics"] = result.get("subtopics")
        return {"subtopics": result.get("subtopics")}
    
    except Exception as e:
        logger.debug(f"This is planner error: {e}")
        raise
        

def researcher(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """Tool for researching planned subtopics"""

    try:
        subtopics = state.get("subtopics", [])
        findings = []
        for sub in subtopics:
            result = search_tool.invoke({"query": sub.title, "max_results": 3})
            findings.append({"subtopic": sub, "results": result})
        config["configurable"]["findings"] = findings
        config["configurable"]["status"] = "awaiting_writer"
        return {"findings": findings}

    except Exception as e:
        logger.debug(f"This is researcher error: {e}")
        raise


def writer(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """Tool for creating final report"""
    try:
        findings = config["configurable"]["findings"]
        formatted = "\n".join([f"- {f['subtopic']}: {f['results'][0]['content'][:200]}..." for f in findings])
        prompt = PromptTemplate.from_template("Using these notes, write a research summary:\n\n{formatted}")
        chain = prompt | writer_llm | StrOutputParser()
        report = chain.invoke({"formatted": formatted})
        config["configurable"]["report"] = report
        config["configurable"]["status"] = "report_done"
        return {"report": report}
    
    except Exception as e:
        logger.debug(f"This is writer error: {e}")
        raise