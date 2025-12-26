"""Synthesis chain for creating research briefings."""

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

SYNTHESIZE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a senior research analyst creating executive briefing documents.

Your task is to synthesize multiple source summaries into a coherent research briefing with proper citations.

Structure your briefing as follows:

## Executive Summary
A 2-3 sentence overview of the key findings. Include citation numbers in brackets (e.g., [1], [2]) when referencing specific sources.

## Key Findings
Bullet points of the most important discoveries. Each finding MUST include a citation number [N] linking to the source.

## Analysis
A detailed analysis synthesizing information across sources. Include inline citations [N] for all claims. Identify:
- Points of consensus across sources (cite relevant sources)
- Conflicting information or perspectives (cite opposing sources)
- Knowledge gaps

## References
List all sources as clickable markdown links in this exact format:
[1] [Source Title](URL)
[2] [Source Title](URL)
...

CITATION RULES:
1. Use numbered citations in square brackets: [1], [2], [3], etc.
2. Citations must match the source numbers provided in the input
3. Every factual claim must have at least one citation
4. The References section must list ALL sources with clickable markdown links
5. Format links as: [N] [Title](URL)

Guidelines:
- Be objective and factual
- ALWAYS cite sources with [N] when making claims
- Highlight uncertainty where it exists
- Use clear, professional language
- Format using Markdown""",
    ),
    (
        "human",
        """Research Topic: {topic}

Sources (use these numbers for citations):
{summaries}

Create a comprehensive research briefing with inline citations [1], [2], etc. and a References section with clickable links.""",
    ),
])


class SynthesizerChain:
    """Chain for synthesizing source summaries into a briefing."""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        self.chain = SYNTHESIZE_PROMPT | llm | StrOutputParser()

    async def synthesize(
        self,
        topic: str,
        sources: list[dict],
    ) -> str:
        """Synthesize source summaries into a research briefing."""
        if not sources:
            return "No sources available to synthesize."

        # Format summaries for the prompt with clear citation numbers
        summaries_text = ""
        for i, source in enumerate(sources, 1):
            url = source.get('url', 'N/A')
            title = source.get('title', 'Untitled')
            summaries_text += f"""
### [Source {i}] {title}
- URL: {url}
- Credibility Score: {source.get('credibility_score', 'N/A')}
- Citation format: [{i}] [{title}]({url})

Summary:
{source.get('summary', 'No summary available.')}

---
"""

        result = await self.chain.ainvoke({
            "topic": topic,
            "summaries": summaries_text.strip(),
        })

        # Post-process to ensure references are properly formatted
        briefing = result.strip()
        
        # If no References section exists, add one
        if "## References" not in briefing and "## Sources" not in briefing:
            references = "\n\n## References\n"
            for i, source in enumerate(sources, 1):
                url = source.get('url', '#')
                title = source.get('title', 'Untitled')
                references += f"[{i}] [{title}]({url})\n"
            briefing += references

        return briefing
