import asyncio
import streamlit as st
import uuid
import logging

# LangChain & LangGraph
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph

# Your existing modules
from config import OPENAI_API_KEY, TAVILY_API_KEY
from graph_builder import build_graph
from models import GraphState

# Tools or function to create LLM & Tools (same as in main.py)
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from tools import analyze_business_website, google_trends_analyzer

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# If the user is on Streamlit 1.22 or newer, we can use st.chat_message
# Otherwise, we can just do normal st.write for conversation display.

# Create the LLM and tools
def create_llm(api_key: str) -> ChatOpenAI:
    if not api_key:
        raise ValueError("OpenAI API key is not configured.")
    return ChatOpenAI(model="gpt-4o", temperature=0.0, openai_api_key=api_key, streaming=True)

def create_tools(tavily_api_key: str):
    if not tavily_api_key:
        raise ValueError("Tavily API key is not configured.")
    tavily_search = TavilySearchResults(max_results=5, api_key=tavily_api_key)
    return [analyze_business_website, google_trends_analyzer, tavily_search]

# --- Helper function to run one turn of the graph ---
# Because Streamlit is synchronous, we define a helper that calls asyncio.run internally.
async def run_graph_turn(langgraph_app: StateGraph, user_input: str, thread_id: str) -> list:
    """
    Feeds user_input to the graph (with the existing thread_id for memory),
    returns the latest list of messages after the agent node finishes.
    """
    graph_input = {"messages": [HumanMessage(content=user_input)]}
    config = {"configurable": {"thread_id": thread_id}}

    final_state_messages = []
    async for state in langgraph_app.astream(graph_input, config=config, stream_mode="values"):
        current_messages = state.get("messages", [])
        if current_messages:
            final_state_messages = current_messages

    return final_state_messages

def init_langgraph_app() -> StateGraph:
    """
    Create or load the LangGraph app (LLM, tools, compiled graph).
    """
    llm = create_llm(OPENAI_API_KEY)
    tools = create_tools(TAVILY_API_KEY)
    return build_graph(llm, tools)

def main():
    st.set_page_config(page_title="AI Marketing Plan Chatbot", layout="wide")

    st.title("AI Marketing Media Plan (Streamlit Chat)")
    st.caption("Interact with an AI assistant to generate a marketing media plan.")

    # Initialize session state variables
    if "langgraph_app" not in st.session_state:
        # Build the graph once
        st.session_state.langgraph_app = init_langgraph_app()

    if "thread_id" not in st.session_state:
        # Unique thread_id for memory-based state
        st.session_state.thread_id = str(uuid.uuid4())

    if "messages" not in st.session_state:
        # We'll store the entire conversation in this list
        st.session_state.messages = []

    # Display existing conversation
    for msg in st.session_state.messages:
        if isinstance(msg, HumanMessage):
            with st.chat_message("user"):
                st.write(msg.content)
        elif isinstance(msg, AIMessage):
            # If final plan JSON, we might display it differently
            if getattr(msg, "name", "") == "FinalPlanOutput":
                # This is the final structured plan. We can either show it raw
                # or parse JSON. Let's just show raw for now:
                with st.chat_message("assistant"):
                    st.write("**Final Marketing Plan (JSON)**")
                    st.code(msg.content, language="json")
            else:
                with st.chat_message("assistant"):
                    st.write(msg.content)

    # Provide a chat input widget (requires Streamlit >= 1.22)
    if user_input := st.chat_input(placeholder="Type your message here..."):
        # First, record the human message in session_state
        human_msg = HumanMessage(content=user_input)
        st.session_state.messages.append(human_msg)

        # Display it immediately in the UI
        with st.chat_message("user"):
            st.write(user_input)

        # Process with LangGraph
        langgraph_app = st.session_state.langgraph_app
        thread_id = st.session_state.thread_id

        # We have to run an async function from sync context. We'll do:
        latest_messages = asyncio.run(run_graph_turn(langgraph_app, user_input, thread_id))

        # The final messages from the graph contain the new AI message(s).
        if latest_messages:
            # Identify only the newly added ones vs. what's in session_state
            # Because we store the entire conversation in memory, a simpler approach:
            #   - We'll just look at the final item in `latest_messages`.
            new_ai_message = latest_messages[-1]

            st.session_state.messages.append(new_ai_message)

            # Display AI message in the chat
            if isinstance(new_ai_message, AIMessage):
                if getattr(new_ai_message, "name", "") == "FinalPlanOutput":
                    # It's the final JSON plan
                    with st.chat_message("assistant"):
                        st.write("**Final Marketing Plan (JSON)**")
                        st.code(new_ai_message.content, language="json")
                else:
                    with st.chat_message("assistant"):
                        st.write(new_ai_message.content)


if __name__ == "__main__":
    main()
