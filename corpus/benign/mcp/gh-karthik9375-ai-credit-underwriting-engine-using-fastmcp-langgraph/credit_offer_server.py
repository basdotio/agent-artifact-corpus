from fastmcp import FastMCP
from state import CreditState
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from pydantic import BaseModel, Field
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

mcp = FastMCP(name="Credit Offer Server")

llm = ChatOpenAI(model_name="gpt-4o-mini", api_key=OPENAI_API_KEY, temperature=0.7)

class CreditOfferSchema(BaseModel):
    interest_rate: float = Field(..., le=0.1, gt=0.0, description="Interest rate of the credit offer.")
    tenure: int = Field(..., description="Tenure of the credit offer in months.")
    credit_limit: float = Field(..., description="Credit limit of the credit offer.")
    
structured_llm = llm.with_structured_output(CreditOfferSchema)

@mcp.tool()
def make_credit_offer(credit_state: CreditState):
    """    
        Generates a personalized and financially viable credit offer to the applicant for a credit decision based on the provided credit state.
    """
    credit_data_summary = credit_state.model_dump()

    prompt_template = ChatPromptTemplate.from_messages([
        HumanMessagePromptTemplate.from_template(
            "You are a financial credit advisor AI. Given the applicant's profile and computed metrics: {data_summary}, "
            "if the decision is APPROVED or SUBJECT TO HUMAN REVIEW, generate a dynamic credit offer including interest rate, tenure, and credit limit "
            "that is reasonable and risk-adjusted. Return the offer strictly as JSON only in the following format: "
            "{{'interest_rate': <interest_rate>, 'tenure': <tenure>, 'credit_limit': <credit_limit>}}. "
            "Do NOT generate any explanation here."
        )
    ])
    
    prompt = prompt_template.format(data_summary=credit_data_summary)
    credit_offer = structured_llm.invoke(prompt)
    return {"credit_offer": credit_offer.dict()}

if __name__ == "__main__":
    mcp.run()