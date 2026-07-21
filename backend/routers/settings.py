from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from backend.config_manager import load_intent_config, save_intent_config

router = APIRouter(prefix="/api/settings", tags=["Settings"])

class IntentConfigModel(BaseModel):
    news_queries: List[str]
    serper_queries: List[str]
    jobspy_search_term: str
    news_signals_query_template: str
    extraction_keywords: List[str]

@router.get("/intents", response_model=IntentConfigModel)
def get_intents():
    config = load_intent_config()
    return config

@router.post("/intents", response_model=IntentConfigModel)
def update_intents(payload: IntentConfigModel):
    save_intent_config(payload.model_dump())
    return payload
