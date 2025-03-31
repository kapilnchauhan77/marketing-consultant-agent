import asyncio
import logging

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from models import GraphState
from agent_node import agent_node

logger = logging.getLogger(__name__)

def build_graph(llm, tools):
    graph = StateGraph(GraphState)

    graph.add_node("agent", lambda state: asyncio.run(agent_node(state, llm, tools)))
    tool_node = ToolNode(tools)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "agent")

    graph.add_conditional_edges(
        "agent", 
        tools_condition,
        {
            "tools": "tools",
            END: END
        }
    )

    graph.add_edge("tools", "agent")

    app = graph.compile(checkpointer=MemorySaver())
    return app
