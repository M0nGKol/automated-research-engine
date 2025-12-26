"""Academic search tool for arXiv and Semantic Scholar."""

import asyncio
from typing import Any

import httpx
from langchain_core.tools import BaseTool
from pydantic import Field

from app.models import Source


class AcademicSearchTool(BaseTool):
    """Tool for searching academic papers on arXiv and Semantic Scholar."""

    name: str = "academic_search"
    description: str = (
        "Search academic papers on arXiv and Semantic Scholar. "
        "Returns papers with titles, abstracts, and URLs."
    )
    max_results: int = Field(default=10)
    timeout: float = Field(default=15.0)

    def _run(self, query: str) -> list[dict[str, Any]]:
        """Synchronous search execution."""
        return asyncio.run(self._arun(query))

    async def _arun(self, query: str) -> list[dict[str, Any]]:
        """Async search execution across academic sources."""
        # Search both sources concurrently
        arxiv_task = self._search_arxiv(query)
        semantic_task = self._search_semantic_scholar(query)
        
        arxiv_results, semantic_results = await asyncio.gather(
            arxiv_task, semantic_task, return_exceptions=True
        )
        
        results = []
        
        # Process arXiv results
        if isinstance(arxiv_results, list):
            results.extend(arxiv_results)
        
        # Process Semantic Scholar results
        if isinstance(semantic_results, list):
            results.extend(semantic_results)
        
        # Limit total results
        return results[:self.max_results]

    async def _search_arxiv(self, query: str) -> list[dict[str, Any]]:
        """Search arXiv API."""
        try:
            # Use arxiv library for cleaner API access
            import arxiv
            
            # Create search query
            search = arxiv.Search(
                query=query,
                max_results=self.max_results // 2,  # Split between sources
                sort_by=arxiv.SortCriterion.Relevance,
            )
            
            results = []
            for paper in search.results():
                results.append({
                    "url": paper.entry_id,
                    "title": paper.title,
                    "snippet": paper.summary[:500] + "..." if len(paper.summary) > 500 else paper.summary,
                    "source": "arxiv",
                    "authors": ", ".join(a.name for a in paper.authors[:3]),
                    "published": paper.published.strftime("%Y-%m-%d") if paper.published else None,
                })
            
            return results
            
        except Exception as e:
            return [{
                "url": "",
                "title": "arXiv Search Error",
                "snippet": f"Error searching arXiv: {str(e)}",
                "source": "arxiv",
            }]

    async def _search_semantic_scholar(self, query: str) -> list[dict[str, Any]]:
        """Search Semantic Scholar API."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://api.semanticscholar.org/graph/v1/paper/search",
                    params={
                        "query": query,
                        "limit": self.max_results // 2,
                        "fields": "title,abstract,url,authors,year",
                    },
                    headers={
                        "User-Agent": "ResearchAgent/1.0",
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for paper in data.get("data", []):
                    abstract = paper.get("abstract", "")
                    if abstract and len(abstract) > 500:
                        abstract = abstract[:500] + "..."
                    
                    authors = paper.get("authors", [])
                    author_names = ", ".join(a.get("name", "") for a in authors[:3])
                    
                    results.append({
                        "url": paper.get("url") or f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}",
                        "title": paper.get("title", "Untitled"),
                        "snippet": abstract or "No abstract available.",
                        "source": "semantic_scholar",
                        "authors": author_names,
                        "published": str(paper.get("year")) if paper.get("year") else None,
                    })
                
                return results
                
        except httpx.TimeoutException:
            return [{
                "url": "",
                "title": "Semantic Scholar Timeout",
                "snippet": "Request to Semantic Scholar timed out.",
                "source": "semantic_scholar",
            }]
        except Exception as e:
            return [{
                "url": "",
                "title": "Semantic Scholar Error",
                "snippet": f"Error searching Semantic Scholar: {str(e)}",
                "source": "semantic_scholar",
            }]

    async def search(self, query: str) -> list[Source]:
        """Perform search and return Source objects."""
        raw_results = await self._arun(query)
        sources = []

        for result in raw_results:
            if result.get("url"):
                # Academic sources get higher base credibility
                credibility = 0.85 if result.get("source") == "arxiv" else 0.8
                
                sources.append(
                    Source(
                        url=result["url"],
                        title=result["title"],
                        snippet=result["snippet"],
                        credibility_score=credibility,
                    )
                )

        return sources

