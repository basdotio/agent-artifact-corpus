import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from src.prompt import summarize_prompt
from tools.combined import run_combined_search

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=GEMINI_API_KEY,
    temperature=0.3,
    max_output_tokens=1000
)

processing_chain = (
    {
        "query": RunnablePassthrough(),
        "results": run_combined_search
    }
    | summarize_prompt
    | llm
)

# 4. Example usage
query = "What are the best places to visit in Nepal?"
final_output = processing_chain.invoke(query)
print(final_output.content)



