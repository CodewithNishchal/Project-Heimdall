from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from backend.database import get_db
from backend.models import SocialPostSnapshot
from backend.pipeline.social_discovery import fetch_social_micro_intent
from backend.config import settings
import json

router = APIRouter(prefix="/api/social-posts", tags=["Social Posts"])

@router.get("/")
def get_social_posts(platform: Optional[str] = None, keyword: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(SocialPostSnapshot)
    if platform:
        query = query.filter(SocialPostSnapshot.platform == platform)
    if keyword:
        query = query.filter(SocialPostSnapshot.keyword_matched == keyword)
    
    posts = query.order_by(SocialPostSnapshot.created_at.desc()).all()
    return posts

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
        with open("backend/intent_config.json", "r") as f:
            config = json.load(f)
            keywords = config.get("social_keywords", [
                "looking for marketing agency",
                "recommend Google Ads agency",
                "need fractional CMO"
            ])
    except Exception:
        keywords = ["looking for marketing agency"]

    new_posts = await fetch_social_micro_intent(keywords)
    
    saved_count = 0
    for p in new_posts:
        # Check if URL exists to avoid duplicates
        existing = db.query(SocialPostSnapshot).filter(SocialPostSnapshot.post_url == p["post_url"]).first()
        if not existing:
            db_post = SocialPostSnapshot(
                id=str(uuid.uuid4()),
                platform=p["platform"],
                author_name=p["author_name"],
                author_handle=p["author_handle"],
                content=p["content"],
                post_url=p["post_url"],
                keyword_matched=p["keyword_matched"],
                company_name=p["company_name"],
                published_at=p["published_at"]
            )
            db.add(db_post)
            saved_count += 1
            
    db.commit()
    return {"status": "success", "fetched_count": len(new_posts), "saved_new": saved_count}
