#mcp_server.py
import asyncio
from mcp.server.fastmcp import FastMCP
import rag
import search
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="web_search",
    version="1.0.0",
    description="web search capability using the Exe API, Firecrawl_API that provides real-time data"
)

@mcp.tool()
async def search_web_tool(query:str) -> str:
    """
    Search the web for the given query and return the results.
    """
    logger.info(f"Searching the web for: {query}")
    formatted_results, raw_results = await search.search_web(query)
 
    if not raw_results:
        return "No results found."

    urls = [result['url'] for result in raw_results if hasattr(result, 'url')]
    if not urls:
        return "No URLs found in the results."
    vectorstore = await rag.create_rag(urls)
    rag_results = await rag.search_rag(query, vectorstore)
    
    full_results = f'{formatted_results}\n\nRAG Results:\n'
    full_results += '\n---\n'.join(doc.page_content for doc in rag_results)
    
    return full_results

async def get_web_content_tool(url:str) -> str:
    """
    Get the content of the given URL.
    """
    try:
        documents = await asyncio.wait_for(search.get_web_content(url), timeout=10)
        if documents:
            return '\n\n'.join(doc.page_content for doc in documents)
        return "Unable to retrieve content from the URL."
    except asyncio.TimeoutError:
        return "Request timed out. Please try again later."
    except Exception as e:
        return f"An error occurred: {str(e)}"
    


async def create_rag(links:list[str]) -> FAISS:
    """
    Create a RAG (Retrieval-Augmented Generation) model using the provided links.
    """
    try:
        model_name = os.getenv("Model", "your model name")
        embeddings = MistralAIEmbeddings(
            model_name=model_name
            )
        documents = []
        tasks = [search.get_web_content(url) for url in links]
        results = await asyncio.gather(*tasks)
        for resultt in results:
            documents.extend(resultt)
        text-splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=0,
            length_function=len,
            ls_separator_regex=False,
            )
        split_documents = text_splitter.split_documents(documents)
        vectorstore = FAISS.from_documents(documents=split_documents, embeddings=embeddings)
        return vectorstore
    except Exception as e:
        print(f"Error creating RAG: {e}")
        raise
    
async def create_rag_from_documents(documents:list[Document])-> FAISS:
    """
    Create a RAG (Retrieval-Augmented Generation) model using the provided documents.
    """
    try:
        model_name = os.getenv("Model")
        embeddings = MistralAIEmbeddings(
            model=model_name,
            chunk_size=64
            )
        text-splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=500,
            length_function=len,
            ls_separator_regex=False,
            )
        split_documents = text_splitter.split_documents(documents)
        vectorstore = FAISS.from_documents(documents=split_documents, embeddings=embeddings)
        return vectorstore
    except Exception as e:
        print(f"Error creating RAG: {e}")
        raise

exa_api_key = os.getenv("EXA_API_KEY","")
exa = Exa(api_key=exa_api_key)

os.environ["FIRECRAWL_API_KEY"] = os.getenv("FIRECRAWL_API_KEY", "your firecrawl api key")

websearch_config={
    "parameters":{
        "default_search_engine":"google",
        "default_num_results":5,
        "include_domain":[]
    }
}

MAX_RETRIES = 3
FIRECRAWL_TIMEOUT =30

async def search_web(query: str, num_results: int =None) -> Tuple[str, list]:
    """
    Search the web for the given query and return the results.
    """
    try:
        search_args={
            "num_results": num_results or websearch_config["parameters"]["default_num_results"],
            
        }
        search_results = exa.search_web_contents(
            query,
            summary={"query: Main points and kwy takeaways"}
            **search_args
        )
        formatted_results = format_search_results(search_results)
        return formatted_results, search_results.results
    except Exception as e:
        return f"An error occured while searching eith Exa: {str(e)}", []   
    
def format_search_results(search_results):
    if not search_results:
        return "No results found."
    markdown_results = "### Seacrh Results\n"
    for idx, result in enumerate(search_results. results, 1):
        title = result.titlr if hasattr(result, 'title') and result.title else "No title"
        url = result.url
        published_date = result.published_date if hasattr(result, 'published_date') and result.published_date else "No published date"
        markdown_results += f"**{idx}.** [{title}]({url}){published_date}\n"
        
        if hasattr(result, 'summary') and result.summary:
            markdown_results += f"Summary: {result.summary}\n"
        else: 
            markdown_results += "No summary available.\n"
    return markdown_results

async def get_web_content(url: str) -> list:
    """
    Get the content of the given URL.
    """
    for attempt in range(MAX_RETRIES):
        try:
            loader = FireCrawlLoader(
                url=url,
                mode = "scrape"
            )
            
            document = await asyncio.wait_for(loader.aload(), timeout= FIRECRAWL_TIMEOUT)
            if document and len(document) > 0:
                return document
            print(f"NO documents retriebved from {url} (attempt {attempt + 1})/{MAX_RETRIES}")
            
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(1)
                continue
        except asyncio.exceptions.HTTPError as e:
            if "Website Not Supported" in str(e):
                print(f"Website not supported by firecrawl:{url}")
                content = f"Content fromo {url} is not supported by Firecrawl."
                return [Document(page_content=content, metadata={"source": url, "error": "Website Not Supported"})]
            else:
                print(f"HTTP error retrieving content form {url}: {str(e)} (attempt {attempt + 1})/{MAX_RETRIES}")
                
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(1)
                continue
            raise
        
        except Exception as e:
            print(f"Error retrieving content from {url}: {str(e)} (attempt {attempt + 1})/{MAX_RETRIES}")
            
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(1)
                continue
            raise
        return []
    
    
async def main():
    if len(sys.argv)>1:
        query = "".join(sys.argv[1:])
    else:
        query = input("Enter your query: ")
    print(f"Searching for: {query}")
    
    try:
        formatted_results, raw_results = await search.search_web(query)
        if not raw_results:
            print("No results found.")
            return
        print(f"Found{len(raw_results)} search results.")
        
        urls = [result['url'] for result in raw_results if hasattr(result, 'url')]
        if not urls:
            print("No URLs found in the results.")
            return
        print(f"Processing {len(urls)} URLs...")
        
        vectorstore = await rag.create_rag(urls)
        rag_results = await rag.search_rag(query, vectorstore)
        
        print("\n=== Search Results ===")
        print(formatted_results)
        
        for doc in rag_results:
            print(f"\n---\n"{doc.page_content})
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
