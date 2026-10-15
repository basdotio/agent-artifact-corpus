from typing_extensions import TypedDict, List, Dict
from pydantic import BaseModel, Field

class State(TypedDict, total=False):
    state: Dict

class Configurable(TypedDict, total=False):
    thread_id: str # uniquely identifies the session
    planner_model: str
    writer_model: str
    subtopics: List
    feedback: str
    findings: List
    report: str

class Subtopics(BaseModel):
    """Schema for Subtopics"""
    title: str = Field(description="Title for the subtopic to search")
    objective: str = Field(description="Reasoning for choosing this subtopic")

class PlannerSchema(BaseModel):
    """Always use this tool to structure your plans."""
    think: str = Field(default="", description="This is your thinking area. Use this to create a good approach")
    subtopics: List[Subtopics] = Field(description="List of top 3 specific subtopics that can be researched")