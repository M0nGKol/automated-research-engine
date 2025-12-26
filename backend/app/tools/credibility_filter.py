"""Credibility filtering tool for sources."""

import re
from urllib.parse import urlparse

from langchain_core.tools import BaseTool
from pydantic import Field

from app.models import Source


# Domain credibility scores (higher = more credible)
CREDIBILITY_SCORES = {
    # Academic & Research - Highest credibility
    ".edu": 0.9,
    ".ac.uk": 0.9,  # UK academic
    ".ac.jp": 0.9,  # Japan academic
    ".gov": 0.85,
    ".mil": 0.85,
    
    # Academic Databases & Preprint Servers
    "arxiv.org": 0.92,
    "semanticscholar.org": 0.88,
    "scholar.google.com": 0.85,
    "pubmed.ncbi.nlm.nih.gov": 0.92,
    "ncbi.nlm.nih.gov": 0.9,
    "doi.org": 0.88,
    "researchgate.net": 0.8,
    "academia.edu": 0.75,
    
    # Top Scientific Journals
    "nature.com": 0.95,
    "science.org": 0.95,
    "sciencedirect.com": 0.9,
    "springer.com": 0.88,
    "wiley.com": 0.88,
    "cell.com": 0.92,
    "pnas.org": 0.9,
    "plos.org": 0.85,
    
    # Tech & Engineering
    "ieee.org": 0.9,
    "acm.org": 0.9,
    "openai.com": 0.85,
    "deepmind.com": 0.85,
    
    # Major News
    "reuters.com": 0.85,
    "apnews.com": 0.85,
    "bbc.com": 0.8,
    "bbc.co.uk": 0.8,
    "nytimes.com": 0.8,
    "washingtonpost.com": 0.8,
    "theguardian.com": 0.75,
    "npr.org": 0.8,
    "economist.com": 0.8,
    
    # General .org (lower than specific)
    ".org": 0.7,
    
    # Tech Sources
    "github.com": 0.7,
    "stackoverflow.com": 0.7,
    "huggingface.co": 0.75,
    
    # Wikipedia (useful but verify)
    "wikipedia.org": 0.65,
    
    # Known lower-quality patterns
    "blogspot.com": 0.3,
    "medium.com": 0.5,  # Variable quality
    "reddit.com": 0.4,  # Discussion, not primary source
    "quora.com": 0.4,
    "twitter.com": 0.35,
    "x.com": 0.35,
}

# Red flags in URLs
RED_FLAGS = [
    r"spam",
    r"fake",
    r"clickbait",
    r"[0-9]{8,}",  # Long number strings often indicate low-quality
    r"ad[s]?\b",
    r"promo",
]


class CredibilityFilterTool(BaseTool):
    """Tool for assessing and filtering sources by credibility."""

    name: str = "credibility_filter"
    description: str = (
        "Assess the credibility of a source based on domain reputation "
        "and URL patterns. Returns a score between 0 and 1."
    )
    min_credibility: float = Field(default=0.4)

    def _run(self, url: str) -> float:
        """Calculate credibility score for a URL."""
        return self._calculate_score(url)

    async def _arun(self, url: str) -> float:
        """Async version (same as sync for this tool)."""
        return self._calculate_score(url)

    def _calculate_score(self, url: str) -> float:
        """Calculate credibility score based on URL analysis."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            full_url = url.lower()
        except Exception:
            return 0.3  # Default low score for unparseable URLs

        score = 0.5  # Base score

        # Check for domain-specific scoring first (more specific = higher priority)
        for known_domain, domain_score in CREDIBILITY_SCORES.items():
            if not known_domain.startswith(".") and known_domain in domain:
                score = domain_score
                break
        else:
            # Check for TLD-based scoring if no specific domain matched
            for tld, tld_score in CREDIBILITY_SCORES.items():
                if tld.startswith(".") and domain.endswith(tld):
                    score = max(score, tld_score)
                    break

        # Apply red flag penalties
        for pattern in RED_FLAGS:
            if re.search(pattern, full_url):
                score *= 0.7

        # HTTPS bonus
        if parsed.scheme == "https":
            score = min(1.0, score + 0.03)

        # Length penalty (very long URLs are often low quality)
        if len(url) > 200:
            score *= 0.9

        return round(min(1.0, max(0.0, score)), 2)

    def filter_sources(
        self, sources: list[Source], min_score: float | None = None
    ) -> list[Source]:
        """Filter and score a list of sources."""
        min_score = min_score or self.min_credibility
        scored_sources = []

        for source in sources:
            # Preserve existing high credibility scores (from academic search)
            if source.credibility_score > 0.8:
                score = source.credibility_score
            else:
                score = self._calculate_score(source.url)
            
            source.credibility_score = score

            if score >= min_score:
                scored_sources.append(source)

        # Sort by credibility (highest first)
        scored_sources.sort(key=lambda s: s.credibility_score, reverse=True)

        return scored_sources
