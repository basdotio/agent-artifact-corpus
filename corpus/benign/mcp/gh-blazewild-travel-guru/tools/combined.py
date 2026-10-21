from google.generativeai import configure, GenerativeModel
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool
import os
from tools.exa_tools import search_and_contents, find_similar_and_contents
from tools.pdf_rag import search_pdf_docs

configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini = GenerativeModel("gemini-2.0-flash")

@tool
def run_combined_search(query: str) -> str:
    """Run both web+PDF RAG and generate an answer."""
    raw_rag_response = search_pdf_docs(query)
    exa_web_search = search_and_contents(query)
    #extract urls from the web results to find similar content
    urls = [line.split("URL:")[1].strip() for line in exa_web_search.split("\n") if "URL:" in line]
    exa_similar_content = ""
    for url in urls[:3]: #process first 3 urls
        try:
            exa_similar_content += find_similar_and_contents(url)
        except Exception as e:
            print(f"Error finding similar content for {url}: {str(e)}")
    
    return exa_web_search + "\n" + exa_similar_content + "\n" + raw_rag_response
