import uvicorn
import asyncio
import uuid
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph

# Import your existing modules
from config import OPENAI_API_KEY, TAVILY_API_KEY
from graph_builder import build_graph
from models import GraphState

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define a Pydantic model for incoming requests to /chat
class ChatRequest(BaseModel):
    session_id: str
    user_message: str

# Global FastAPI app
app = FastAPI()

# A dictionary to track user sessions in-memory:
#   sessions_data[session_id] = {"thread_id": <some_uuid>}
sessions_data = {}

# We'll store the compiled graph in a global variable so we can reuse it
langgraph_app: StateGraph = None

@app.on_event("startup")
async def on_startup():
    """
    Called when FastAPI starts. Build the LangGraph app with your LLM and tools.
    """
    global langgraph_app

    if not OPENAI_API_KEY or not TAVILY_API_KEY:
        logger.error("Missing OPENAI_API_KEY or TAVILY_API_KEY in environment variables.")
        raise RuntimeError("Missing API keys in environment variables.")

    # The "build_graph" function requires an LLM and list of tools.
    # Typically you do something like:
    from langchain_openai import ChatOpenAI
    from langchain_community.tools.tavily_search import TavilySearchResults
    from tools import analyze_business_website, google_trends_analyzer

    def create_llm(api_key: str):
        return ChatOpenAI(model="gpt-4o", temperature=0.0, openai_api_key=api_key, streaming=True)

    def create_tools(tavily_api_key: str):
        # Here you might pass TAVILY_MAX_RESULTS, etc. from config, but keep it simple for now.
        tavily_search = TavilySearchResults(max_results=5, api_key=tavily_api_key)
        return [analyze_business_website, google_trends_analyzer, tavily_search]

    llm = create_llm(OPENAI_API_KEY)
    tools = create_tools(TAVILY_API_KEY)

    # Build the LangGraph app
    langgraph_app = build_graph(llm, tools)
    logger.info("LangGraph app built successfully for FastAPI deployment.")

@app.post("/start")
async def start_session():
    """
    Start a new chatbot session and return a unique session_id.
    """
    session_id = str(uuid.uuid4())
    # For each session, we also create a unique thread_id for memory state
    thread_id = str(uuid.uuid4())
    sessions_data[session_id] = {"thread_id": thread_id}

    logger.info(f"Created new session_id: {session_id}, thread_id: {thread_id}")
    return {"session_id": session_id}

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Send a message from the user to the chatbot and get the AI's response.
    The conversation state is tracked using 'thread_id' from sessions_data.
    """
    if request.session_id not in sessions_data:
        raise HTTPException(status_code=400, detail="Invalid session_id. Start a session first.")

    # Get the existing memory thread_id for this session
    thread_id = sessions_data[request.session_id]["thread_id"]

    # Build the new messages input
    graph_input = {
        "messages": [HumanMessage(content=request.user_message)]
    }

    # We'll store final output after we consume the astream
    final_state_messages = []

    # The config must pass the thread_id so MemorySaver knows which conversation to continue
    config = {"configurable": {"thread_id": thread_id}}

    # Run the graph in streaming mode
    try:
        async for event in langgraph_app.astream(graph_input, config=config, stream_mode="values"):
            current_messages = event.get("messages", [])
            if current_messages:
                final_state_messages = current_messages
        # After a complete turn, final_state_messages should have the new agent response
    except Exception as e:
        logger.error(f"Error in chat processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    if not final_state_messages:
        # No messages from the agent?
        raise HTTPException(status_code=500, detail="No AI response was generated.")

    last_message = final_state_messages[-1]

    # If the last message is the final JSON plan, we can return it directly,
    # or indicate some "final" flag in the response. Let's keep it simple:
    is_final = (getattr(last_message, "name", "") == "FinalPlanOutput")

    return {
        "ai_message": last_message.content,
        "final_plan": is_final
    }


# Optional: if you want to run with `python fastapi_app.py` directly:
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

