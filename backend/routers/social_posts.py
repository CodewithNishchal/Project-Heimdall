from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from backend.database import get_db
from backend.models import SocialPostSnapshot
from backend.pipeline.social_discovery import fetch_social_micro_intent
from backend.config import settings
import json

from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/api/social-posts", tags=["Social Posts"])

@router.get("/")
def get_social_posts(platform: Optional[str] = None, keyword: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(SocialPostSnapshot)
    if platform:
        query = query.filter(SocialPostSnapshot.platform == platform)
    if keyword:
        query = query.filter(SocialPostSnapshot.keyword_matched == keyword)
    
    posts = query.order_by(SocialPostSnapshot.created_at.desc()).all()

    # Enforce strict 30-day freshness filter (drop any thread > 30 days old)
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    fresh_posts = []
    for post in posts:
        is_fresh = True
        if post.published_at:
            try:
                dt_str = post.published_at.replace("Z", "+00:00")
                pub_dt = datetime.fromisoformat(dt_str)
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                if pub_dt < cutoff:
                    is_fresh = False
            except Exception:
                pass
        if is_fresh:
            fresh_posts.append(post)

    return fresh_posts

@router.get("/test-badger")
def test_badger_endpoint():
    from scrapebadger import ScrapeBadger
    client = ScrapeBadger(api_key="test")
    return {"client_dir": dir(client)}




@router.delete("/{post_id}")
def delete_social_post(post_id: str, db: Session = Depends(get_db)):
    post = db.query(SocialPostSnapshot).filter(SocialPostSnapshot.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    db.delete(post)
    db.commit()
    return {"status": "success", "id": post_id}


@router.post("/fetch")
async def trigger_fetch_social_posts(db: Session = Depends(get_db)):
    try:
        from backend.config_manager import load_intent_config
        config = load_intent_config()
        triggers = config.get("social_triggers", [])
        topics = config.get("social_topics", [])
    except Exception:
        triggers = ["looking for"]
        topics = ["marketing agency"]

    new_posts = await fetch_social_micro_intent(triggers, topics)
    
    saved_count = 0
    from backend.pipeline.social_classifier import classify_social_intent
    from backend.models import ScrapeCache
    import logging
    logger = logging.getLogger("SocialPosts")
    
    # Process only a batch to save tokens/time if we got too many
    max_to_process = 40
    posts_processed = 0

    for p in new_posts:
        if posts_processed >= max_to_process:
            break

        url_key = p["post_url"]
        
        # 1. Deduplicate globally across scheduled runs (ScrapeCache)
        # TEMPORARILY BYPASSED FOR TESTING:
        # if db.query(ScrapeCache).filter(ScrapeCache.post_url == url_key).first():
        #     continue
        #     
        # # Add to cache so we don't process it again next run
        # db.add(ScrapeCache(id=str(uuid.uuid4()), post_url=url_key))
        # db.commit()

        # 2. Extract 2-5 lines for Groq to save tokens
        short_content = "\n".join(p["content"].split("\n")[:5])[:300]
        
        # 3. Classify posts with Qwen
        classification = await classify_social_intent(short_content, author_bio="")
        logger.info(f"[OpenRouter Qwen2.5-7B Result] {classification} for text: {short_content[:100]}...")
        
        posts_processed += 1

        if classification.get("intent") == "seeking_provider" and classification.get("confidence", 0) > 0.6:
            # Check if it was saved by another thread or previously
            existing = db.query(SocialPostSnapshot).filter(SocialPostSnapshot.post_url == url_key).first()
            if not existing:
                db_post = SocialPostSnapshot(
                    id=str(uuid.uuid4()),
                    platform=p["platform"],
                    author_name=p["author_name"],
                    author_handle=p["author_handle"],
                    content=p["content"],
                    post_url=p["post_url"],
                    keyword_matched=classification.get("service_category", p.get("keyword_matched")) if classification else p.get("keyword_matched"),
                    company_name=p["company_name"],
                    published_at=p["published_at"]
                )
                db.add(db_post)
                saved_count += 1
                
    db.commit()
    return {
        "status": "success", 
        "fetched_count": len(new_posts), 
        "saved_new": saved_count
    }


@router.get("/test-monid")
async def test_monid_connection():
    from backend.pipeline.monid_service import monid_client
    key = monid_client.api_key
    if not key:
        return {"status": "error", "message": "MONID_API_KEY is missing in backend/.env"}

    tools = await monid_client.discover_tools("twitter posts")
    return {
        "status": "connected" if isinstance(tools, list) and len(tools) > 0 else "response_received",
        "api_key_prefix": f"{key[:10]}...",
        "discovered_tools_count": len(tools) if isinstance(tools, list) else 0,
        "raw_response": tools[:2] if isinstance(tools, list) else tools
    }

