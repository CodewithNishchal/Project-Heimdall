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

from sqlalchemy import func

router = APIRouter(prefix="/api/social-posts", tags=["Social Posts"])

@router.get("/")
def get_social_posts(platform: Optional[str] = None, keyword: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(SocialPostSnapshot)
    if platform and platform.lower() != 'all':
        query = query.filter(func.lower(SocialPostSnapshot.platform).contains(platform.lower()))
    if keyword:
        query = query.filter(SocialPostSnapshot.keyword_matched == keyword)
    
    posts = query.order_by(SocialPostSnapshot.created_at.desc(), SocialPostSnapshot.published_at.desc()).all()
    return posts

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
    from backend.pipeline.social_classifier import batch_classify_social_intent
    import logging
    logger = logging.getLogger("SocialPosts")
    
    # Process only a batch to save tokens/time if we got too many
    max_to_process = 60
    posts_to_process = new_posts[:max_to_process]
    
    batch_size = 20
    
    for i in range(0, len(posts_to_process), batch_size):
        batch = posts_to_process[i:i+batch_size]
        try:
            relevant_posts = await batch_classify_social_intent(batch)
            
            for p in relevant_posts:
                url_key = p["post_url"]
                existing = db.query(SocialPostSnapshot).filter(SocialPostSnapshot.post_url == url_key).first()
                if not existing:
                    db_post = SocialPostSnapshot(
                        id=str(uuid.uuid4()),
                        platform=p["platform"],
                        author_name=p["author_name"],
                        author_handle=p["author_handle"],
                        content=p["content"],
                        post_url=p["post_url"],
                        keyword_matched=p.get("service_category") or p.get("keyword_matched", "intent signal"),
                        company_name=p["company_name"],
                        summary=p.get("summary"),
                        published_at=p["published_at"]
                    )
                    db.add(db_post)
                    saved_count += 1
        except Exception as e:
            logger.error(f"Batch processing failed for chunk: {e}")
            continue

    logger.info(f"Saving {saved_count} new high-intent posts to the database out of {len(new_posts)} fetched posts.")
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

