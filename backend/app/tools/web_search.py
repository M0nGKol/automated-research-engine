"""Web search tool using Google Custom Search API."""

import asyncio
from typing import Any

import httpx
from langchain_core.tools import BaseTool
from pydantic import Field

from app.config import get_settings
from app.models import Source


class WebSearchTool(BaseTool):
    """Tool for performing web searches using Google Custom Search API."""

    name: str = "web_search"
    description: str = (
        "Search the web for information on a given topic. "
        "Returns a list of relevant URLs with titles and snippets."
    )
    max_results: int = Field(default=10)

    def _run(self, query: str) -> list[dict[str, Any]]:
        """Synchronous search execution."""
        return asyncio.run(self._arun(query))

    async def _arun(self, query: str) -> list[dict[str, Any]]:
        """Async search execution using Google Custom Search API."""
        settings = get_settings()
        results = []

        # Check if Google API is configured
        if not settings.google_api_key or not settings.google_cse_id:
            print("⚠️ Google Custom Search API not configured. Set GOOGLE_API_KEY and GOOGLE_CSE_ID in .env")
            return results

        try:
            print(f"🔍 Searching Google for: {query}")

            # Google Custom Search API endpoint
            url = "https://www.googleapis.com/customsearch/v1"
            
            # Parameters (Google limits to 10 results per request)
            params = {
                "key": settings.google_api_key,
                "cx": settings.google_cse_id,
                "q": query,
                "num": min(self.max_results, 10),  # Max 10 per request
            }

            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    error_data = response.json().get("error", {})
                    error_msg = error_data.get("message", "Unknown error")
                    error_details = error_data.get("details", [])
                    print(f"❌ Google API error ({response.status_code}): {error_msg}")
                    if error_details:
                        for detail in error_details:
                            print(f"   Detail: {detail}")
                    print(f"   API Key (first 10 chars): {settings.google_api_key[:10]}..." if settings.google_api_key else "   API Key: NOT SET")
                    print(f"   CSE ID: {settings.google_cse_id}" if settings.google_cse_id else "   CSE ID: NOT SET")
                    return results
                
                data = response.json()
                search_results = data.get("items", [])
                
                print(f"📊 Google returned {len(search_results)} results")
                
                if not search_results:
                    print(f"⚠️ Google returned no results for: {query}")
                    return results

                for item in search_results:
                    # Only add results with valid URL and title
                    if item.get("link") and item.get("title"):
                        results.append({
                            "url": item.get("link", ""),
                            "title": item.get("title", ""),
                            "snippet": item.get("snippet", "")[:500],  # Limit snippet length
                        })
                
                print(f"✓ Processed {len(results)} valid results")

        except httpx.TimeoutException:
            print(f"❌ Google search timeout for: {query}")
            return []
        except httpx.RequestError as e:
            print(f"❌ Google search request error: {type(e).__name__}: {str(e)}")
            return []
        except Exception as e:
            print(f"❌ Google search error: {type(e).__name__}: {str(e)}")
            return []

        return results

    async def search(self, query: str) -> list[Source]:
        """Perform search and return Source objects."""
        raw_results = await self._arun(query)
        sources = []

        for result in raw_results:
            if result.get("url"):
                sources.append(
                    Source(
                        url=result["url"],
                        title=result["title"],
                        snippet=result["snippet"],
                    )
                )

        print(f"✓ Returning {len(sources)} sources")
        return sources
