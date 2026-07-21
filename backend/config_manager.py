import json
import os
from pathlib import Path
import logging

logger = logging.getLogger("ConfigManager")

CONFIG_PATH = Path(__file__).parent / "intent_config.json"

DEFAULT_CONFIG = {
    "news_queries": [
        "SaaS startup raises funding",
        "B2B seed round",
        "series A funding startup",
        "startup hiring SDR sales"
    ],
    "serper_queries": [
        "site:linkedin.com/company \"hiring SDR\" OR \"hiring BDR\""
    ],
    "jobspy_search_term": "Sales Development Representative",
    "news_signals_query_template": "\"{company_name}\" AND (startup OR funding OR expansion OR hiring)",
    "extraction_keywords": [
        "raised", "funding", "hired", "expanded", "launched", "SDR",
        "hiring", "growth", "series", "seed", "round"
    ]
}

def load_intent_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load intent config: {e}")
        return DEFAULT_CONFIG.copy()

def save_intent_config(config: dict) -> bool:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save intent config: {e}")
        return False
