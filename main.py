import asyncio
import logging

from config import OPENAI_API_KEY, TAVILY_API_KEY, LLM_MODEL
from graph_builder import build_graph
from run_interaction import run_interaction_loop

from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults

from tools import analyze_business_website, google_trends_analyzer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_llm(api_key: str) -> ChatOpenAI:
    """
    Initializes the LLM with provided API key.
    """
    if not api_key:
        raise ValueError("OpenAI API key is not configured.")
    return ChatOpenAI(model=LLM_MODEL, temperature=0.0, openai_api_key=api_key, streaming=True)

def create_tools(tavily_api_key: str):
    """
    Initializes and returns a list of tools.
    """
    if not tavily_api_key:
        raise ValueError("Tavily API key is not configured.")

    tavily_search = TavilySearchResults(max_results=5, api_key=tavily_api_key)

    return [analyze_business_website, google_trends_analyzer, tavily_search]

async def main():
    if not OPENAI_API_KEY or not TAVILY_API_KEY:
        logger.error("Missing OPENAI_API_KEY or TAVILY_API_KEY in environment variables.")
        return

    llm = create_llm(OPENAI_API_KEY)
    tools = create_tools(TAVILY_API_KEY)
    app = build_graph(llm, tools)
    logger.info("Graph compiled. Starting run_interaction_loop...")

    await run_interaction_loop(app)

if __name__ == "__main__":
    asyncio.run(main())
