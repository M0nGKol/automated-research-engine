"""Main research agent orchestrating the research workflow."""

import time
from typing import AsyncGenerator

from langchain_core.language_models import BaseChatModel

from app.chains import SummarizerChain, SynthesizerChain
from app.models import ResearchProgress, ResearchResult, ResearchStatus, Source
from app.tools import (
    AcademicSearchTool,
    ContentExtractorTool,
    CredibilityFilterTool,
    WebSearchTool,
)


class ResearchAgent:
    """
    Orchestrates the research workflow:
    1. Search for sources (web + optional academic)
    2. Filter by credibility
    3. Extract content
    4. Summarize each source
    5. Synthesize into briefing
    """

    def __init__(
        self,
        llm: BaseChatModel,
        max_sources: int = 5,
        min_credibility: float = 0.4,
    ):
        self.llm = llm
        self.max_sources = max_sources
        self.min_credibility = min_credibility

        # Initialize tools
        self.search_tool = WebSearchTool(max_results=max_sources * 2)
        self.academic_search_tool = AcademicSearchTool(max_results=max_sources)
        self.extractor_tool = ContentExtractorTool()
        self.credibility_tool = CredibilityFilterTool(min_credibility=min_credibility)

        # Initialize chains
        self.summarizer = SummarizerChain(llm)
        self.synthesizer = SynthesizerChain(llm)

    async def research(
        self,
        topic: str,
        depth: str = "standard",
        include_academic: bool = False,
    ) -> AsyncGenerator[ResearchProgress | ResearchResult, None]:
        """
        Execute research workflow with streaming progress updates.

        Args:
            topic: The research topic
            depth: Research depth (quick, standard, deep)
            include_academic: Whether to include academic sources (arXiv, Semantic Scholar)

        Yields:
            Progress updates and final result
        """
        start_time = time.time()

        # Adjust parameters based on depth
        max_sources = {
            "quick": 3,
            "standard": self.max_sources,
            "deep": self.max_sources + 3,
        }.get(depth, self.max_sources)

        # Step 1: Search
        search_message = f"Searching for sources on: {topic}"
        if include_academic:
            search_message += " (including academic papers)"
        
        yield ResearchProgress(
            status=ResearchStatus.SEARCHING,
            message=search_message,
            progress=0.1,
        )

        # Perform web search
        sources = await self.search_tool.search(topic)
        
        # Debug logging
        if not sources:
            print(f"⚠️ WARNING: Web search returned 0 sources for: {topic}")
            yield ResearchProgress(
                status=ResearchStatus.ERROR,
                message=f"Search failed: No sources found for '{topic}'. Please try a different query.",
                progress=0.0,
                sources_found=0,
            )
            return

        print(f"✓ Web search found {len(sources)} sources")
        
        # Add academic sources if requested
        if include_academic:
            yield ResearchProgress(
                status=ResearchStatus.SEARCHING,
                message="Searching academic databases (arXiv, Semantic Scholar)...",
                progress=0.15,
                sources_found=len(sources),
            )
            
            academic_sources = await self.academic_search_tool.search(topic)
            sources.extend(academic_sources)

        yield ResearchProgress(
            status=ResearchStatus.SEARCHING,
            message=f"Found {len(sources)} potential sources",
            progress=0.2,
            sources_found=len(sources),
        )

        # Step 2: Filter by credibility
        filtered_sources = self.credibility_tool.filter_sources(
            sources, min_score=self.min_credibility
        )

        # If all filtered out, lower threshold
        if not filtered_sources:
            print(f"⚠️ WARNING: All {len(sources)} sources filtered out by credibility (min={self.min_credibility})")
            filtered_sources = self.credibility_tool.filter_sources(
                sources, min_score=0.2  # Lower threshold
            )
            print(f"✓ After lowering threshold: {len(filtered_sources)} sources passed")

        # Limit to max sources
        filtered_sources = filtered_sources[:max_sources]

        yield ResearchProgress(
            status=ResearchStatus.EXTRACTING,
            message=f"Processing {len(filtered_sources)} credible sources",
            progress=0.3,
            sources_found=len(sources),
            sources_processed=0,
        )

        # Step 3: Extract content
        # For academic sources (arXiv), the snippet already contains the abstract
        # so we only extract content for non-academic URLs
        web_urls = [
            s.url for s in filtered_sources 
            if not any(domain in s.url for domain in ["arxiv.org", "semanticscholar.org"])
        ]
        
        content_map = await self.extractor_tool.extract_batch(web_urls) if web_urls else {}

        # Update sources with content
        for source in filtered_sources:
            if source.url in content_map:
                source.content = content_map.get(source.url, "")
            elif not source.content:
                # For academic sources, use the snippet as content if no content extracted
                source.content = source.snippet

        yield ResearchProgress(
            status=ResearchStatus.SUMMARIZING,
            message="Summarizing sources...",
            progress=0.5,
            sources_found=len(sources),
            sources_processed=len(filtered_sources),
        )

        # Step 4: Summarize each source
        sources_for_summary = [
            {
                "url": s.url,
                "title": s.title,
                "content": s.content or s.snippet,
                "credibility_score": s.credibility_score,
            }
            for s in filtered_sources
        ]

        summarized_sources = await self.summarizer.summarize_batch(
            topic=topic,
            sources=sources_for_summary,
        )

        # If summarization failed, use original sources
        if not summarized_sources:
            print(f"⚠️ WARNING: Summarization returned 0 sources")
            summarized_sources = sources_for_summary

        # Update source objects with summaries
        for i, source in enumerate(filtered_sources):
            if i < len(summarized_sources):
                source.summary = summarized_sources[i].get("summary", "")

        yield ResearchProgress(
            status=ResearchStatus.SYNTHESIZING,
            message="Synthesizing research briefing...",
            progress=0.8,
            sources_found=len(sources),
            sources_processed=len(filtered_sources),
        )

        # Step 5: Synthesize briefing
        briefing = await self.synthesizer.synthesize(
            topic=topic,
            sources=summarized_sources,
        )

        total_time = time.time() - start_time

        # Final result
        yield ResearchProgress(
            status=ResearchStatus.COMPLETED,
            message="Research complete!",
            progress=1.0,
            sources_found=len(sources),
            sources_processed=len(filtered_sources),
        )

        yield ResearchResult(
            topic=topic,
            briefing=briefing,
            sources=filtered_sources,
            total_time_seconds=round(total_time, 2),
            model_used=str(self.llm.model_name if hasattr(self.llm, "model_name") else "unknown"),
        )