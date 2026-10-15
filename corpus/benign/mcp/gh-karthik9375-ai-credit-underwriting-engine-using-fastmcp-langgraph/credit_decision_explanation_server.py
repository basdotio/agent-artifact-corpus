from fastmcp import FastMCP
from state import CreditState
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

mcp = FastMCP(name="Credit Decision Explanation Server")

llm = ChatOpenAI(model_name="gpt-4o-mini", openai_api_key=OPENAI_API_KEY, temperature=0.6)

@mcp.tool()
def generate_explanation(credit_state: CreditState) -> dict:
    """   
        Generates a personalized and human-friendly credit decision explanation for a credit decision based on the provided credit state.
    """
    credit_data_summary = credit_state.model_dump()
    
    prompt_template = ChatPromptTemplate.from_messages([
        HumanMessagePromptTemplate.from_template(
            "You are a financial credit advisor AI. Given the applicant's profile and computed metrics: {data_summary}, "
            "generate a clear, professional, human-readable explanation of the credit decision. "
            "Do NOT generate the offer here."
        )
    ])
    
    prompt_text = prompt_template.format(data_summary=credit_data_summary)
    response = llm.invoke(prompt_text)
    explanation_text = response.content
    return {"explanation": explanation_text}

if __name__ == "__main__":
    mcp.run()