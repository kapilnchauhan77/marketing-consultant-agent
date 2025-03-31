import asyncio
import logging
import uuid

from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)

async def run_interaction_loop(app):
    logger.info("Starting AI Marketing Media Plan Generator (LangGraph).")
    print("\nWelcome to the AI Marketing Media Plan Generator!")
    print("Please provide the URL of the business website.")

    initial_url = await asyncio.to_thread(input, "User URL: ")
    if not initial_url:
        print("No URL provided. Exiting.")
        return

    thread_id = str(uuid.uuid4())  
    config = {"configurable": {"thread_id": thread_id}}
    logger.info(f"Using thread_id: {thread_id}")

    current_input = f"Generate a marketing media plan for the website: {initial_url}"
    final_plan_generated = False

    while True:
        try:
            graph_input = {"messages": [HumanMessage(content=current_input)]}

            async for event in app.astream(graph_input, config=config, stream_mode="values"):
                current_messages = event.get("messages", [])
                if current_messages:

                    last_message = current_messages[-1]
                    if isinstance(last_message, AIMessage) and not last_message.tool_calls:
                        if last_message.name == "FinalPlanOutput":
                            print("\n--- Final Plan ---")
                            print(last_message.content)
                            final_plan_generated = True
                        else:
                            print(f"\nAI: {last_message.content}")

            if final_plan_generated:
                print("\nMarketing plan generation complete.")
                break

            next_input = await asyncio.to_thread(input, "User: ")
            if next_input.lower() in ["quit", "exit", "stop"]:
                logger.info("User requested exit.")
                break
            current_input = next_input

        except Exception as e:
            logger.error(f"Error during graph execution: {e}", exc_info=True)
            print(f"\nAI: An unexpected error occurred: {e}. Please try rephrasing or restart.")
            break

    if not final_plan_generated:
        logger.warning("Interaction ended without final plan.")
        print("\nInteraction ended without final plan.")
