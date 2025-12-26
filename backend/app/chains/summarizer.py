"""Summarization chain for individual sources."""

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

SUMMARIZE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a research assistant that creates concise, accurate summaries.

Your task is to summarize the following article content. Focus on:
- Key facts and findings
- Main arguments or conclusions
- Relevant data or statistics
- Notable quotes or expert opinions

Keep the summary factual and objective. Do not add interpretation or speculation.
Aim for 3-5 paragraphs maximum.""",
    ),
    (
        "human",
        """Topic: {topic}

Source: {title}
URL: {url}

Content:
{content}

Provide a focused summary of this source as it relates to the research topic.""",
    ),
])


class SummarizerChain:
    """Chain for summarizing individual source content."""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        self.chain = SUMMARIZE_PROMPT | llm | StrOutputParser()

    async def summarize(
        self,
        topic: str,
        title: str,
        url: str,
        content: str,
    ) -> str:
        """Summarize a single source."""
        if not content or content.startswith("[Error"):
            return "[Unable to summarize: content extraction failed]"

        # Truncate content if too long for context window
        max_content = 12000
        if len(content) > max_content:
            content = content[:max_content] + "\n\n[Content truncated for summarization]"

        result = await self.chain.ainvoke({
            "topic": topic,
            "title": title,
            "url": url,
            "content": content,
        })

        return result.strip()

    async def summarize_batch(
        self,
        topic: str,
        sources: list[dict],
    ) -> list[dict]:
        """Summarize multiple sources."""
        import asyncio

        async def summarize_one(source: dict) -> dict:
            summary = await self.summarize(
                topic=topic,
                title=source.get("title", "Untitled"),
                url=source.get("url", ""),
                content=source.get("content", ""),
            )
            return {**source, "summary": summary}

        tasks = [summarize_one(s) for s in sources]
        results = await asyncio.gather(*tasks)

        return list(results)

