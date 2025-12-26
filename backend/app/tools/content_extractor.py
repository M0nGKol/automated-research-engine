"""Content extraction tool for web pages."""

import asyncio
from typing import Optional

import httpx
from bs4 import BeautifulSoup
import html2text
from langchain_core.tools import BaseTool
from pydantic import Field


class ContentExtractorTool(BaseTool):
    """Tool for extracting clean text content from web pages."""

    name: str = "content_extractor"
    description: str = (
        "Extract the main textual content from a web page URL. "
        "Returns clean, readable text suitable for analysis."
    )
    timeout: float = Field(default=15.0)
    max_content_length: int = Field(default=15000)

    def _run(self, url: str) -> str:
        """Synchronous content extraction."""
        return asyncio.run(self._arun(url))

    async def _arun(self, url: str) -> str:
        """Async content extraction using beautifulsoup4."""
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                html = response.text

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Get text and convert to markdown
            h = html2text.HTML2Text()
            h.ignore_links = True
            h.ignore_images = True
            content = h.handle(str(soup))

            if not content:
                return ""

            # Truncate if too long
            if len(content) > self.max_content_length:
                content = content[: self.max_content_length] + "\n\n[Content truncated...]"

            return content.strip()

        except httpx.TimeoutException:
            return f"[Error: Request timed out for {url}]"
        except httpx.HTTPStatusError as e:
            return f"[Error: HTTP {e.response.status_code} for {url}]"
        except Exception as e:
            return f"[Error extracting content: {str(e)}]"

    async def extract_batch(
        self, urls: list[str], max_concurrent: int = 5
    ) -> dict[str, str]:
        """Extract content from multiple URLs concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def extract_with_semaphore(url: str) -> tuple[str, str]:
            async with semaphore:
                content = await self._arun(url)
                return url, content

        tasks = [extract_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        content_map = {}
        for result in results:
            if isinstance(result, tuple):
                url, content = result
                content_map[url] = content

        return content_map