from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List, Annotated
from langgraph.graph.message import add_messages

class ApplicantState(BaseModel):
    model_config = {"extra": "allow"}
    name: str = Field(..., description="Name of the applicant.")
    age: int = Field(..., ge=18, le=100, description="Age of the applicant.")
    location: str = Field(..., description="Location of the applicant.")
    annual_income: float = Field(..., ge=0.0, description="Annual income of the applicant.")
    total_debt: float = Field(..., ge=0.0, description="Total debt of the applicant.")
    credit_score: int = Field(..., ge=300, le=850, description="Credit score of the applicant.")
    credit_history_length: int = Field(..., ge=0, description="Credit history length of the applicant.")
    employment_status: str = Field(None, description="Employment status of the applicant.")
    employment_years: int = Field(..., ge=0, description="Employment years of the applicant.")

    @field_validator("employment_status")
    def validate_employment_status(cls, v):
        allowed = {"employed", "self-employed", "unemployed", "retired"}
        if v not in allowed:
            raise ValueError(f"employment_status must be one of {allowed}")
        return v
    
class CreditState(BaseModel):
    model_config = {"extra": "allow"}
    messages: Annotated[List[Any], add_messages] = Field(default_factory=list)
    applicant: ApplicantState = Field(..., description="Applicant financial information.")
    creditworthiness_score: Optional[float] = Field(None, gt=0.0, le=100.0, description="Creditworthiness assessment of the applicant.")
    fraud_risk_score: Optional[float] = Field(None, gt=0.0, le=100.0, description="Fraud risk assessment of the applicant.")
    income_stability_score: Optional[float] = Field(None, gt=0.0, le=100.0, description="Income stability assessment of the applicant.")
    market_conditions_score: Optional[float] = Field(None, gt=0.0, le=100.0, description="Market conditions at application time.")
    decision: Optional[str] = Field(None, description="Final decision on the credit application.")
    explanation: Optional[str] = Field(None, description="Explanation of the decision.")
    audit_review: Optional[str] = Field(None, description="A detailed audit report for the credit decision.")
    credit_offer: Optional[Dict[str, Any]] = Field(None, description="Credit offer for the applicant only if approved or subject to human review.")
