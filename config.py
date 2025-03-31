import os
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

LLM_MODEL = "gpt-4o"
TAVILY_MAX_RESULTS = 5
HTTP_TIMEOUT = 20
RETRY_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 2
