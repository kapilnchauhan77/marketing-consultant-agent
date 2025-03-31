import json
import asyncio
import logging

import httpx
from bs4 import BeautifulSoup
from typing import List

from langchain_core.tools import tool

try:
    from pytrends.request import TrendReq
    import pandas as pd
except ImportError:
    TrendReq = None
    pd = None

from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from models import WebsiteAnalysisInput, GoogleTrendsInput

logger = logging.getLogger(__name__)

RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.HTTPStatusError
)

RETRY_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 2
HTTP_TIMEOUT = 20

@retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_fixed(RETRY_WAIT_SECONDS),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    reraise=True
)
async def _execute_request_async(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> httpx.Response:
    logger.debug(f"Executing async {method.upper()} request to {url}")
    response = await client.request(method, url, timeout=HTTP_TIMEOUT, **kwargs)
    response.raise_for_status()
    return response

@tool(args_schema=WebsiteAnalysisInput)
async def analyze_business_website(url: str) -> str:
    """
    Asynchronously analyzes web content from a URL to extract potential industry, products/services,
    audience hints, and social links. Handles errors gracefully. Returns a JSON string summary.
    """
    headers = {'User-Agent': 'Mozilla/5.0'}
    result_dict = {"url": url, "status": "success"}
    logger.info(f"Analyzing website: {url}")

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await _execute_request_async(client, "GET", url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            title = soup.find('title').string if soup.find('title') else "Not found"
            description_tag = soup.find('meta', attrs={'name': 'description'})
            meta_description = description_tag['content'] if description_tag else "Not found"
            headings = [h.text.strip() for h in soup.find_all(['h1', 'h2', 'h3'], limit=10)]
            paragraphs = [p.text.strip() for p in soup.find_all('p', limit=10)]
            text_content = " ".join(paragraphs)
            social_links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                if isinstance(href, str) and any(domain in href for domain in [
                    "facebook.com/", "twitter.com/", "instagram.com/", "linkedin.com/company/",
                    "linkedin.com/in/", "youtube.com/channel/", "youtube.com/user/"
                ]):
                    if href not in social_links and len(href) > 15:
                        social_links.append(href)

            result_dict.update({
                "title": title,
                "meta_description": meta_description,
                "headings_sample": headings or ["Not found"],
                "text_content_sample": text_content[:500] + ("..." if len(text_content) > 500 else "") or "Not found",
                "detected_social_links": social_links or ["None found"],
                "initial_guessed_industry": "Unknown - Requires LLM interpretation or user confirmation"
            })
            logger.info(f"Website analysis successful for {url}")

    except httpx.RequestError as e:
        logger.error(f"HTTP error fetching {url}: {e}")
        result_dict.update({"status": "error", "error": f"Network/HTTP error analyzing {url}: {str(e)}"})
    except Exception as e:
        logger.error(f"Failed to parse {url}: {e}", exc_info=True)
        result_dict.update({"status": "error", "error": f"Failed to parse content from {url}: {str(e)}"})

    return json.dumps(result_dict, default=str)

@tool(args_schema=GoogleTrendsInput)
async def google_trends_analyzer(keywords: List[str], timeframe: str = "today 3-m") -> str:
    """
    Asynchronously analyzes Google Trends for keywords using pytrends library.
    Returns a JSON string summary of interest over time data or errors encountered.
    """
    logger.info(f"Analyzing Google Trends for: {keywords} (Timeframe: {timeframe})")
    result_dict = {"keywords": keywords, "timeframe": timeframe, "status": "success"}

    def _fetch_trends_sync(_keywords: List[str], _timeframe: str):
        """Synchronous pytrends logic, run in a thread."""
        if not TrendReq or not pd:
            raise ImportError(
                "Pytrends library or pandas is not available. "
                "Install with: pip install pytrends pandas."
            )

        try:
            pytrends = TrendReq(hl='en-US', tz=360)
            pytrends.build_payload(kw_list=_keywords, cat=0, timeframe=_timeframe, geo='', gprop='')
            interest_over_time_df = pytrends.interest_over_time()
        except Exception as e:
            logger.error(f"Pytrends API call failed: {e}", exc_info=True)
            return {"error": f"Pytrends API error: {str(e)}"}

        if not isinstance(interest_over_time_df, pd.DataFrame) or interest_over_time_df.empty:
            return {
                "interest_over_time_summary": "No interest over time data found.",
                "warning": "Received empty or invalid data from Pytrends."
            }

        if 'isPartial' in interest_over_time_df.columns:
            interest_over_time_df = interest_over_time_df.drop(columns=['isPartial'], errors='ignore')

        summary_points = {}
        processed_keywords = [
            kw for kw in _keywords
            if kw in interest_over_time_df.columns
        ]

        if not processed_keywords:
            return {
                "interest_over_time_summary": "No data found for the specified keywords in the dataframe."
            }

        for kw in processed_keywords:
            numeric_series = pd.to_numeric(interest_over_time_df[kw], errors='coerce').dropna()
            if not numeric_series.empty:
                first_val = numeric_series.iloc[0]
                last_val = numeric_series.iloc[-1]
                change = "Stable"
                if last_val > first_val * 1.05:
                    change = "Increasing"
                elif first_val > last_val * 1.05:
                    change = "Decreasing"
                summary_points[kw] = (
                    f"{change} trend (relative score: first={first_val:.1f}, last={last_val:.1f})"
                )
            else:
                summary_points[kw] = "Insufficient numeric data"

        iot_summary = f"Interest over time summary: {summary_points}"
        return {"interest_over_time_summary": iot_summary}

    try:
        trends_data = await asyncio.to_thread(_fetch_trends_sync, keywords, timeframe)
        result_dict.update(trends_data)
        if "error" in trends_data:
            logger.warning(f"Google Trends error: {trends_data['error']}")
            result_dict["status"] = "error"
        else:
            logger.info("Google Trends analysis succeeded.")
    except ImportError as e:
        logger.error(f"Pytrends/Pandas import error: {e}")
        result_dict.update({"status": "error", "error": str(e)})
    except Exception as e:
        logger.error(f"Unexpected error in google_trends_analyzer: {e}", exc_info=True)
        result_dict.update({"status": "error", "error": f"Failed to get Google Trends data: {str(e)}"})

    return json.dumps(result_dict, default=str)
