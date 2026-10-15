from fastmcp import FastMCP
from state import CreditState
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(model_name="gpt-4o-mini", openai_api_key=OPENAI_API_KEY, temperature=0.6)

mcp = FastMCP(name="Credit Decision Audit Server")

@mcp.tool()
def audit_credit_decision(credit_state: CreditState):
    """   
        Audits the credit decision and explanationcarefully and provides a detailed explanation of the decision and any potential issues.
    """
    credit_state_obj = CreditState.model_validate(credit_state)
    credit_data_summary = credit_state_obj.model_dump()
    
    prompt_template = ChatPromptTemplate.from_messages([
        HumanMessagePromptTemplate.from_template(
            """
            You are a financial risk auditing AI.

            Given the following credit decision data:

            {credit_data_summary}

            1. Audit the credit decision carefully.
            2. Identify potential issues, inconsistencies, or risk factors.
            3. Provide a human-readable audit report summarizing:
            - Overall creditworthiness
            - Fraud risk
            - Income stability
            - Market conditions
            - Any warnings or flags
            
            Return the audit as plain text only (no JSON or dict).
            """
        )
    ])
    
    prompt_text = prompt_template.format(credit_data_summary=credit_data_summary)
    response = llm.invoke(prompt_text)
    audit_text = response.content
    return {"audit_review": audit_text}

if __name__ == "__main__":
    mcp.run()
    