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
    """Export research briefing as PDF using ReportLab."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.colors import HexColor
        import html2text
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="PDF export dependencies not installed. Run: pip install reportlab markdown html2text"
        )
    
    try:
        # Convert markdown to plain text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.body_width = 0  # Don't wrap lines
        
        # Convert markdown to HTML first, then to text
        import markdown
        md = markdown.Markdown(extensions=['tables', 'fenced_code'])
        html_content = md.convert(data.briefing)
        text_content = h.handle(html_content)
        
        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Get styles and create custom styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=HexColor('#1a1a1a'),
            spaceAfter=12,
            spaceBefore=0,
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=HexColor('#2d2d2d'),
            spaceAfter=12,
            spaceBefore=24,
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            spaceAfter=6,
        )
        
        metadata_style = ParagraphStyle(
            'Metadata',
            parent=styles['Normal'],
            fontSize=9,
            textColor=HexColor('#666666'),
            spaceAfter=12,
        )
        
        # Build story (content)
        story = []
        
        # Title
        story.append(Paragraph(f"<b>Research Briefing: {data.topic}</b>", title_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Metadata
        metadata_text = (
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}<br/>"
            f"Model: {data.model_used} | Time: {data.total_time_seconds:.1f}s | Sources: {len(data.sources)}"
        )
        story.append(Paragraph(metadata_text, metadata_style))
        story.append(Spacer(1, 0.3 * inch))
        
        # Add briefing content
        # Split by lines and process
        lines = text_content.split('\n')
        current_section = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_section:
                    # Join current section and add as paragraph
                    para_text = ' '.join(current_section)
                    if para_text:
                        # Escape HTML special characters for ReportLab
                        para_text = para_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        story.append(Paragraph(para_text, normal_style))
                    current_section = []
                continue
            
            # Check if it's a heading
            if line.startswith('#'):
                # Add any pending content first
                if current_section:
                    para_text = ' '.join(current_section)
                    if para_text:
                        para_text = para_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        story.append(Paragraph(para_text, normal_style))
                    current_section = []
                
                # Process heading
                heading_text = line.lstrip('#').strip()
                if heading_text:
                    heading_text = heading_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    story.append(Paragraph(f"<b>{heading_text}</b>", heading_style))
            else:
                current_section.append(line)
        
        # Add any remaining content
        if current_section:
            para_text = ' '.join(current_section)
            if para_text:
                para_text = para_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(para_text, normal_style))
        
        # Add sources section
        story.append(PageBreak())
        story.append(Paragraph("<b>Sources</b>", heading_style))
        
        for i, source in enumerate(data.sources, 1):
            source_text = (
                f"<b>[{i}] {source.title}</b><br/>"
                f"URL: {source.url}<br/>"
                f"Credibility Score: {source.credibility_score:.0%}"
            )
            story.append(Paragraph(source_text, normal_style))
            story.append(Spacer(1, 0.1 * inch))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Generate filename
        safe_topic = "".join(c if c.isalnum() else "_" for c in data.topic[:50])
        filename = f"research_{safe_topic}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
        
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        import traceback
        print(f"PDF export error: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"PDF export failed: {str(e)}"
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
