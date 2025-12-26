"""API routes for the research agent."""

import json
from datetime import datetime
from io import BytesIO
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.agents import ResearchAgent
from app.auth import get_current_user_id, get_optional_user_id
from app.cache import get_cache
from app.config import get_settings
from app.db import Conversation, Message, get_db
from app.llm import check_llm_health, get_llm
from app.models import (
    ConversationCreate,
    ConversationListItem,
    ConversationResponse,
    ConversationUpdate,
    PDFExportRequest,
    ResearchProgress,
    ResearchRequest,
    ResearchResult,
)

router = APIRouter()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


# ============================================================================
# Research Endpoints
# ============================================================================

async def stream_research(
    topic: str,
    depth: str,
    include_academic: bool = False,
) -> AsyncGenerator[dict, None]:
    """Stream research progress as SSE events."""
    settings = get_settings()
    cache = get_cache()
    
    # Check cache first
    cached_result = cache.get(topic, depth, include_academic)
    if cached_result:
        # Return cached result immediately
        yield {
            "event": "progress",
            "data": json.dumps({
                "status": "completed",
                "message": "Retrieved from cache",
                "progress": 1.0,
                "sources_found": len(cached_result.get("sources", [])),
                "sources_processed": len(cached_result.get("sources", [])),
            }),
        }
        
        # Remove cache metadata before returning
        result_data = {k: v for k, v in cached_result.items() if k not in ["cached_at", "cache_key"]}
        yield {
            "event": "result",
            "data": json.dumps(result_data),
        }
        return
    
    llm = get_llm()

    agent = ResearchAgent(
        llm=llm,
        max_sources=settings.max_sources_to_process,
        min_credibility=0.4,
    )

    final_result = None

    try:
        async for event in agent.research(
            topic=topic, 
            depth=depth,
            include_academic=include_academic,
        ):
            if isinstance(event, ResearchProgress):
                yield {
                    "event": "progress",
                    "data": json.dumps(event.model_dump()),
                }
            elif isinstance(event, ResearchResult):
                final_result = event.model_dump()
                yield {
                    "event": "result",
                    "data": json.dumps(final_result),
                }
    except Exception as e:
        yield {
            "event": "error",
            "data": json.dumps({"message": str(e)}),
        }
        return
    
    # Cache the successful result
    if final_result:
        cache.set(topic, depth, final_result, include_academic)


@router.post("/research")
@limiter.limit("10/minute")
@limiter.limit("100/hour")
async def start_research(
    request: Request,
    research_request: ResearchRequest,
    user_id: Optional[str] = Depends(get_optional_user_id),
):
    """
    Start a research task and stream progress updates.
    
    Rate limits:
    - 10 requests per minute
    - 100 requests per hour
    
    Returns Server-Sent Events (SSE) with:
    - progress: Status updates during research
    - result: Final research briefing
    - error: Any errors that occurred
    """
    return EventSourceResponse(
        stream_research(
            topic=research_request.topic, 
            depth=research_request.depth,
            include_academic=research_request.include_academic,
        )
    )


# ============================================================================
# Cache Endpoints
# ============================================================================

@router.get("/cache/stats")
async def cache_stats():
    """Get cache statistics."""
    cache = get_cache()
    return cache.stats()


@router.post("/cache/clear")
async def clear_cache():
    """Clear all cached research results."""
    cache = get_cache()
    count = cache.clear()
    return {"status": "cleared", "entries_removed": count}


@router.delete("/cache/{topic}")
async def invalidate_cache(topic: str, depth: str = "standard", include_academic: bool = False):
    """Invalidate a specific cache entry."""
    cache = get_cache()
    invalidated = cache.invalidate(topic, depth, include_academic)
    return {"status": "invalidated" if invalidated else "not_found", "topic": topic}


# ============================================================================
# Conversation Endpoints (Authenticated)
# ============================================================================

@router.get("/conversations", response_model=list[ConversationListItem])
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations for the current user with message counts."""
    import traceback
    
    try:
        print(f"📋 Listing conversations for user: {user_id}")
        
        # Query conversations with message count, filtered by user_id
        stmt = (
            select(
                Conversation,
                func.count(Message.id).label("message_count"),
            )
            .outerjoin(Message, Conversation.id == Message.conversation_id)
            .where(Conversation.user_id == user_id)
            .group_by(Conversation.id)
            .order_by(Conversation.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        rows = result.all()
        
        print(f"✓ Found {len(rows)} conversations")
        
        return [
            ConversationListItem(
                id=conv.id,
                topic=conv.topic,
                depth=conv.depth,
                created_at=conv.created_at,
                message_count=msg_count or 0,
            )
            for conv, msg_count in rows
        ]
    except Exception as e:
        print(f"❌ Error listing conversations: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation for the current user."""
    conversation = Conversation(
        user_id=user_id,
        topic=data.topic,
        depth=data.depth,
    )
    
    # Add initial messages if provided
    for msg in data.messages:
        message = Message(
            role=msg.role,
            content=msg.content,
        )
        conversation.messages.append(message)
    
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    
    # Reload with messages
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation.id)
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one()
    
    return conversation


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a conversation by ID with all messages. Must belong to current user."""
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Verify ownership
    if conversation.user_id != user_id:
        raise HTTPException(status_code=403, detail="You don't have access to this conversation")
    
    return conversation


@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a conversation with research results and new messages. Must belong to current user."""
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Verify ownership
    if conversation.user_id != user_id:
        raise HTTPException(status_code=403, detail="You don't have access to this conversation")
    
    # Update fields
    if data.briefing is not None:
        conversation.briefing = data.briefing
    if data.sources_json is not None:
        conversation.sources_json = data.sources_json
    if data.total_time_seconds is not None:
        conversation.total_time_seconds = data.total_time_seconds
    if data.model_used is not None:
        conversation.model_used = data.model_used
    
    # Add new messages
    for msg in data.messages:
        message = Message(
            role=msg.role,
            content=msg.content,
            conversation_id=conversation.id,
        )
        db.add(message)
    
    await db.commit()
    await db.refresh(conversation)
    
    # Reload with messages
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation.id)
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one()
    
    return conversation


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and all its messages. Must belong to current user."""
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Verify ownership
    if conversation.user_id != user_id:
        raise HTTPException(status_code=403, detail="You don't have access to this conversation")
    
    await db.delete(conversation)
    await db.commit()
    
    return {"status": "deleted", "id": conversation_id}


# ============================================================================
# PDF Export Endpoint
# ============================================================================

@router.post("/export/pdf")
async def export_pdf(
    data: PDFExportRequest,
    user_id: Optional[str] = Depends(get_optional_user_id),
):
    """Export research briefing as PDF."""
    try:
        import markdown
        from weasyprint import HTML
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="PDF export dependencies not installed. Run: pip install weasyprint markdown"
        )
    
    # Convert markdown to HTML
    md = markdown.Markdown(extensions=['tables', 'fenced_code'])
    briefing_html = md.convert(data.briefing)
    
    # Build sources list
    sources_html = "<ul>"
    for i, source in enumerate(data.sources, 1):
        sources_html += f'<li><a href="{source.url}">[{i}] {source.title}</a> (Credibility: {source.credibility_score:.0%})</li>'
    sources_html += "</ul>"
    
    # Build full HTML document
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 40px;
            }}
            h1 {{ color: #1a1a1a; border-bottom: 2px solid #5865f2; padding-bottom: 10px; }}
            h2 {{ color: #2d2d2d; margin-top: 30px; }}
            h3 {{ color: #404040; }}
            a {{ color: #5865f2; }}
            code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 4px; }}
            pre {{ background: #f4f4f4; padding: 16px; border-radius: 8px; overflow-x: auto; }}
            blockquote {{ border-left: 4px solid #5865f2; padding-left: 16px; color: #666; }}
            ul, ol {{ padding-left: 24px; }}
            .metadata {{ color: #666; font-size: 0.9em; margin-bottom: 30px; }}
            .sources {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; }}
        </style>
    </head>
    <body>
        <h1>Research Briefing: {data.topic}</h1>
        <div class="metadata">
            <p>Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
            <p>Model: {data.model_used} | Time: {data.total_time_seconds:.1f}s | Sources: {len(data.sources)}</p>
        </div>
        
        {briefing_html}
        
        <div class="sources">
            <h2>Sources</h2>
            {sources_html}
        </div>
    </body>
    </html>
    """
    
    # Generate PDF
    pdf_buffer = BytesIO()
    HTML(string=html_content).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    
    # Generate filename
    safe_topic = "".join(c if c.isalnum() else "_" for c in data.topic[:50])
    filename = f"research_{safe_topic}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ============================================================================
# Health & Config Endpoints
# ============================================================================

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/health/llm")
async def llm_health_check():
    """Check LLM provider connectivity."""
    return check_llm_health()


@router.get("/config")
async def get_config():
    """Get current configuration (non-sensitive)."""
    settings = get_settings()
    return {
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "max_sources": settings.max_sources_to_process,
        "max_search_results": settings.max_search_results,
    }
