from typing import Optional, List, Dict, TypedDict, Sequence, Annotated
import operator

from pydantic import BaseModel, Field


class WebsiteAnalysisInput(BaseModel):
    url: str = Field(description="The URL of the business website to analyze.")

class GoogleTrendsInput(BaseModel):
    keywords: List[str] = Field(description="A list of keywords or topics to check trends for.")
    timeframe: str = Field(
        default="today 3-m",
        description="Timeframe for trends (e.g., 'today 5-y', 'today 12-m', 'today 3-m', 'now 7-d'). Defaults to 'today 3-m'."
    )

class BusinessOverview(BaseModel):
    industry: Optional[str] = Field(None, description="The confirmed industry of the business.")
    products: Optional[List[str]] = Field(None, description="List of main products or services offered.")
    target_audience: Optional[str] = Field(None, description="Description of the primary target audience.")
    existing_marketing: Optional[str] = Field(
        None,
        description="Summary of current marketing activities observed or mentioned (e.g., social media presence, ad platforms used)."
    )

class CompetitorInsight(BaseModel):
    competitor_name: str = Field(description="Name of the competitor.")
    ad_platforms: Optional[List[str]] = Field(None, description="Potential advertising platforms used by the competitor.")
    audience: Optional[str] = Field(None, description="Estimated or observed target audience of the competitor.")
    budget_estimate: Optional[str] = Field(None, description="Rough textual estimate of the competitor's ad spend.")

class AdCreative(BaseModel):
    platform: str = Field(description="The recommended advertising platform (e.g., Google Search Ads, Instagram, LinkedIn).")
    ad_type: str = Field(description="The suggested type of ad format (e.g., Product listings, Carousel, Video Ad, etc.).")
    creative: str = Field(description="A brief description or theme for the ad creative content.")

class UserInputSummary(BaseModel):
    budget: Optional[str] = Field(None, description="Monthly marketing budget (as a string).")
    start_date: Optional[str] = Field(None, description="Desired campaign start date or timeline.")
    expectations: Optional[str] = Field(None, description="Specific goals or expectations mentioned by the user.")

class MarketingMediaPlan(BaseModel):
    """
    Structure for the final Marketing Media Plan, matching the user specification.
    """
    business_overview: Optional[BusinessOverview] = Field(None, description="Comprehensive overview of the business.")
    competitor_insights: Optional[List[CompetitorInsight]] = Field(None, description="Insights about key competitors.")
    recommended_channels: Optional[List[str]] = Field(None, description="Recommended marketing channels.")
    budget_allocation: Optional[Dict[str, int]] = Field(None, description="Budget allocation percentages per channel.")
    suggested_ad_creatives: Optional[List[AdCreative]] = Field(None, description="Specific suggestions for ad creatives.")
    user_input: Optional[UserInputSummary] = Field(None, description="Summary of key user-provided inputs.")
    industry_trends_keywords: Optional[str] = Field(None, description="Summary of relevant industry trends and keywords.")
    online_presence_analysis: Optional[str] = Field(None, description="Analysis of the business's current online presence.")
    timeline_suggestion: Optional[str] = Field(None, description="Suggested campaign timeline or duration.")
    data_source_notes: Optional[str] = Field(None, description="Notes on any data limitations or tool failures.")

class GraphState(TypedDict):
    messages: Annotated[Sequence, operator.add]
