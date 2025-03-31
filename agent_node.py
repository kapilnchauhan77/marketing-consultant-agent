import json
import logging
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from models import MarketingMediaPlan
from prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

async def agent_node(state: dict, llm: ChatOpenAI, tools):
    messages = list(state['messages'])

    if not messages or (messages and messages[0].content != SYSTEM_PROMPT):
        from langchain_core.messages import SystemMessage
        messages.insert(0, SystemMessage(content=SYSTEM_PROMPT))

    finalize_keywords = ["looks good", "finalize it", "yes", "correct", "approve", "looks correct", "that's right"]
    should_finalize = False

    if len(messages) > 2 and isinstance(messages[-1], HumanMessage):
        last_human_message = messages[-1].content.lower().strip()
        if isinstance(messages[-2], AIMessage) and not messages[-2].tool_calls:
            if any(keyword == last_human_message for keyword in finalize_keywords) or \
               any(last_human_message.startswith(keyword) for keyword in finalize_keywords):
                logger.info("User message suggests finalization. Attempting structured output.")
                should_finalize = True

    if should_finalize:
        llm_with_plan_structure = llm.with_structured_output(MarketingMediaPlan, include_raw=False)
        logger.info("Generating final structured marketing plan...")

        try:
            final_plan_object = await llm_with_plan_structure.ainvoke(messages)
            if isinstance(final_plan_object, MarketingMediaPlan):
                final_json_str = final_plan_object.model_dump_json(indent=2)
                logger.info("Structured output generated successfully.")
                return {"messages": [AIMessage(content=final_json_str, name="FinalPlanOutput")]}
            else:
                logger.error(f"LLM did not return a MarketingMediaPlan object. Got: {type(final_plan_object)}")
                return {"messages": [AIMessage(content="Error: Could not produce final plan. Please confirm again.")]}
        except (ValidationError, json.JSONDecodeError) as e:
            logger.error(f"Validation or JSON error: {e}", exc_info=True)
            return {"messages": [AIMessage(content=f"Error finalizing plan structure: {e}. Please confirm again.")]}
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return {"messages": [AIMessage(content=f"Unexpected error: {e}. Please try confirming again.")]}
    else:
        llm_with_tools = llm.bind_tools(tools)
        logger.info("Continuing conversation with tools...")
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}
