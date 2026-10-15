import os, asyncio, json, sys
from langgraph.graph import StateGraph, START, END
from state import CreditState
from langchain_mcp_adapters.client import MultiServerMCPClient
from graphviz import Digraph

graph = StateGraph(name="Credit Risk Underwriting Agent", state_schema=CreditState)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MCP_SERVERS = {
    "process_credit_application": {
        "transport": "stdio",
        "command": "python3",
        "args": [os.path.join(BASE_DIR, "credit_application_intake_server.py")],
        "env": {**os.environ, "PYTHONPATH": os.path.abspath(os.path.join(BASE_DIR, ".."))}
    },
    "check_creditworthiness": {
        "transport": "stdio",
        "command": "python3",
        "args": [os.path.join(BASE_DIR, "creditworthiness_scoring_server.py")],
        "env": {**os.environ, "PYTHONPATH": os.path.abspath(os.path.join(BASE_DIR, ".."))}
    },
    "analyze_fraud_risk": {
        "transport": "stdio",
        "command": "python3",
        "args": [os.path.join(BASE_DIR, "fraud_risk_server.py")],
        "env": {**os.environ, "PYTHONPATH": os.path.abspath(os.path.join(BASE_DIR, ".."))}
    },
    "determine_income_stability": {
        "transport": "stdio",
        "command": "python3",
        "args": [os.path.join(BASE_DIR, "income_stability_server.py")],
        "env": {**os.environ, "PYTHONPATH": os.path.abspath(os.path.join(BASE_DIR, ".."))}
    },
    "evaluate_macroeconomic_risk": {
        "transport": "stdio",
        "command": "python3",
        "args": [os.path.join(BASE_DIR, "macroeconomic_risk_server.py")],
        "env": {**os.environ, "PYTHONPATH": os.path.abspath(os.path.join(BASE_DIR, ".."))}
    },
    "make_credit_decision": {
        "transport": "stdio",
        "command": "python3",
        "args": [os.path.join(BASE_DIR, "credit_decision_engine_server.py")],
        "env": {**os.environ, "PYTHONPATH": os.path.abspath(os.path.join(BASE_DIR, ".."))}
    },
    "explain_credit_decision": {
        "transport": "stdio",
        "command": "python3",
        "args": [os.path.join(BASE_DIR, "credit_decision_explanation_server.py")],
        "env": {**os.environ, "PYTHONPATH": os.path.abspath(os.path.join(BASE_DIR, ".."))}
    },
    "audit_credit_decision": {
        "transport": "stdio",
        "command": "python3",
        "args": [os.path.join(BASE_DIR, "credit_decision_audit_server.py")],
        "env": {**os.environ, "PYTHONPATH": os.path.abspath(os.path.join(BASE_DIR, ".."))}
    },
    "offer_credit": {
        "transport": "stdio",
        "command": "python3",
        "args": [os.path.join(BASE_DIR, "credit_offer_server.py")],
        "env": {**os.environ, "PYTHONPATH": os.path.abspath(os.path.join(BASE_DIR, ".."))}
    }
}

mcp_client = MultiServerMCPClient(connections=MCP_SERVERS)

print("Attempting to load MCP tools...")
try:
    mcp_tools = asyncio.run(mcp_client.get_tools())
    print(f"Successfully loaded {len(mcp_tools)} tools")
except Exception as e:
    print(f"Error loading tools: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

tools_map = {tool.name: tool for tool in mcp_tools}
print(f"Tools loaded: {list(tools_map.keys())}")

def _parse_result(result):
    # Handle list of content blocks from MCP tools
    if isinstance(result, list):
        # If it's a list of content blocks like [{'type': 'text', 'text': '...'}]
        if len(result) > 0 and isinstance(result[0], dict) and "text" in result[0]:
            result = result[0]["text"]
        # If it's a list of Message objects
        elif len(result) > 0 and hasattr(result[0], "content"):
            result = result[0].content
            
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return result
    return result

# Define tool nodes for each MCP server
async def intake_node(state: CreditState):
    tool = tools_map["normalize_application"]
    result = await tool.ainvoke({"applicant": state.applicant.model_dump()})
    result = _parse_result(result)
    return {"applicant": result}

async def creditworthiness_node(state: CreditState):
    tool = tools_map["estimate_creditworthiness"]
    result = await tool.ainvoke({"applicant": state.applicant.model_dump()})
    result = _parse_result(result)
    return {"creditworthiness_score": result["creditworthiness_score"]}

async def fraud_node(state: CreditState):
    tool = tools_map["evaluate_fraud_risk"]
    result = await tool.ainvoke({"applicant": state.applicant.model_dump()})
    result = _parse_result(result)
    return {"fraud_risk_score": result["fraud_risk_score"]}

async def macro_node(state: CreditState):
    tool = tools_map["fetch_macro_risk"]
    result = await tool.ainvoke({"applicant": state.applicant.model_dump()})
    result = _parse_result(result)
    return {"market_conditions_score": result["market_conditions_score"]}

async def income_node(state: CreditState):
    tool = tools_map["assess_income_stability"]
    result = await tool.ainvoke({"applicant": state.applicant.model_dump()})
    result = _parse_result(result)
    return {"income_stability_score": result["income_stability_score"]}

async def decision_node(state: CreditState):
    tool = tools_map["make_decision"]
    result = await tool.ainvoke({"credit_state": state.model_dump()})
    result = _parse_result(result)
    return {"decision": result["decision"]}

async def explanation_node(state: CreditState):
    tool = tools_map["generate_explanation"]
    result = await tool.ainvoke({"credit_state": state.model_dump()})
    result = _parse_result(result)
    return {"explanation": result["explanation"]}

async def audit_node(state: CreditState):
    tool = tools_map["audit_credit_decision"]
    result = await tool.ainvoke({"credit_state": state.model_dump()})
    result = _parse_result(result)
    return {}

async def offer_node(state: CreditState):
    tool = tools_map["make_credit_offer"]
    result = await tool.ainvoke({"credit_state": state.model_dump()})
    result = _parse_result(result)
    return {"credit_offer": result["credit_offer"]}

# Add nodes to graph
graph.add_node("Credit Application Intake", intake_node)
graph.add_node("Creditworthiness Scoring", creditworthiness_node)
graph.add_node("Fraud Risk Evaluation", fraud_node)
graph.add_node("Macroeconomic Risk Evaluation", macro_node)
graph.add_node("Income Stability Evaluation", income_node)
graph.add_node("Credit Decision Engine", decision_node)
graph.add_node("Credit Decision Explanation", explanation_node)
graph.add_node("Credit Decision Audit", audit_node)
graph.add_node("Credit Offer", offer_node)

# Add edges between nodes
graph.add_edge(START, "Credit Application Intake")
graph.add_edge("Credit Application Intake", "Creditworthiness Scoring")
graph.add_edge("Credit Application Intake", "Fraud Risk Evaluation")
graph.add_edge("Credit Application Intake", "Macroeconomic Risk Evaluation")
graph.add_edge("Credit Application Intake", "Income Stability Evaluation")
graph.add_edge("Creditworthiness Scoring", "Credit Decision Engine")
graph.add_edge("Fraud Risk Evaluation", "Credit Decision Engine")
graph.add_edge("Macroeconomic Risk Evaluation", "Credit Decision Engine")
graph.add_edge("Income Stability Evaluation", "Credit Decision Engine")
graph.add_edge("Credit Decision Engine", "Credit Decision Explanation")
graph.add_edge("Credit Decision Explanation", "Credit Decision Audit")

def credit_offer_condition(state: CreditState) -> str:
    if state.decision == "APPROVED":
        return "Credit Offer"
    return END

graph.add_conditional_edges("Credit Decision Audit", credit_offer_condition)
graph.add_edge("Credit Offer", END)
graph.add_edge("Credit Decision Audit", END)

# Compile graph
workflow = graph.compile()

# Visualize graph
# Create a new directed graph
dot = Digraph(comment="Credit Underwriting Workflow", format='png')

nodes = [
    "START",
    "Credit Application Intake",
    "Creditworthiness Scoring",
    "Fraud Risk Evaluation",
    "Macroeconomic Risk Evaluation",
    "Income Stability Evaluation",
    "Credit Decision Engine",
    "Credit Decision Explanation",
    "Credit Decision Audit",
    "Credit Offer",
    "END"
]

edges = [
    ("START", "Credit Application Intake"),
    ("Credit Application Intake", "Creditworthiness Scoring"),
    ("Credit Application Intake", "Fraud Risk Evaluation"),
    ("Credit Application Intake", "Macroeconomic Risk Evaluation"),
    ("Credit Application Intake", "Income Stability Evaluation"),
    ("Creditworthiness Scoring", "Credit Decision Engine"),
    ("Fraud Risk Evaluation", "Credit Decision Engine"),
    ("Macroeconomic Risk Evaluation", "Credit Decision Engine"),
    ("Income Stability Evaluation", "Credit Decision Engine"),
    ("Credit Decision Engine", "Credit Decision Explanation"),
    ("Credit Decision Explanation", "Credit Decision Audit"),
    ("Credit Offer", "END"),
    ("Credit Decision Audit", "END")
]

for node in nodes:
    dot.node(node, node)

for start, end in edges:
    dot.edge(start, end)
    
# Conditional edge: only if decision=APPROVED
dot.edge("Credit Decision Audit", "Credit Offer", label="decision=APPROVED", style="dotted")

# Render and view
dot.render("credit_underwriting_workflow", view=False, cleanup=True, format="png")
    



