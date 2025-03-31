import asyncio
import streamlit as st
import uuid
import logging

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph

from config import OPENAI_API_KEY, TAVILY_API_KEY
from graph_builder import build_graph

from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from tools import analyze_business_website, google_trends_analyzer

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_llm(api_key: str) -> ChatOpenAI:
    if not api_key:
        raise ValueError("OpenAI API key is not configured.")
    return ChatOpenAI(model="gpt-4o", temperature=0.0, openai_api_key=api_key, streaming=True)

def create_tools(tavily_api_key: str):
    if not tavily_api_key:
        raise ValueError("Tavily API key is not configured.")
    tavily_search = TavilySearchResults(max_results=5, api_key=tavily_api_key)
    return [analyze_business_website, google_trends_analyzer, tavily_search]

async def run_graph_turn(langgraph_app: StateGraph, user_input: str, thread_id: str) -> list:
    graph_input = {"messages": [HumanMessage(content=user_input)]}
    config = {"configurable": {"thread_id": thread_id}}

    final_state_messages = []
    async for state in langgraph_app.astream(graph_input, config=config, stream_mode="values"):
        current_messages = state.get("messages", [])
        if current_messages:
            final_state_messages = current_messages

    return final_state_messages

def init_langgraph_app() -> StateGraph:
    llm = create_llm(OPENAI_API_KEY)
    tools = create_tools(TAVILY_API_KEY)
    return build_graph(llm, tools)

def main():
    st.set_page_config(page_title="AI Marketing Plan Chatbot", layout="wide")

    st.title("AI Marketing Media Plan Generator")
    st.caption("Interact with an AI assistant to generate a marketing media plan.")
    with st.chat_message("assistant"):
        st.write("Hello! Please provide the business website URL you'd like me to analyze for creating a marketing media plan.")

    if "langgraph_app" not in st.session_state:
        st.session_state.langgraph_app = init_langgraph_app()

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        if isinstance(msg, HumanMessage):
            with st.chat_message("user"):
                st.write(msg.content)
        elif isinstance(msg, AIMessage):
            if getattr(msg, "name", "") == "FinalPlanOutput":
                with st.chat_message("assistant"):
                    st.write("**Final Marketing Plan (JSON)**")
                    st.code(msg.content, language="json")
            else:
                with st.chat_message("assistant"):
                    st.write(msg.content)

    if user_input := st.chat_input(placeholder="Type your message here..."):
        human_msg = HumanMessage(content=user_input)
        st.session_state.messages.append(human_msg)

        with st.chat_message("user"):
            st.write(user_input)

        langgraph_app = st.session_state.langgraph_app
        thread_id = st.session_state.thread_id

        latest_messages = asyncio.run(run_graph_turn(langgraph_app, user_input, thread_id))

        if latest_messages:
            new_ai_message = latest_messages[-1]

            st.session_state.messages.append(new_ai_message)

            if isinstance(new_ai_message, AIMessage):
                if getattr(new_ai_message, "name", "") == "FinalPlanOutput":
                    with st.chat_message("assistant"):
                        st.write("**Final Marketing Plan (JSON)**")
                        st.code(new_ai_message.content, language="json")
                else:
                    with st.chat_message("assistant"):
                        st.write(new_ai_message.content)


if __name__ == "__main__":
    main()
