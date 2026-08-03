import os
import json
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestIndexedNewsPipeline")

def format_indexed_evidence(harvested_sources: List[Dict[str, Any]]) -> tuple[str, Dict[str, str]]:
    """
    Formats raw harvested sources into a clean indexed text block ([S1], [S2], [S3]...)
    and returns a lookup dictionary mapping source IDs back to full URLs.
    """
    url_index_map = {}
    formatted_text = ""

    for idx, src in enumerate(harvested_sources, start=1):
        source_id = f"S{idx}"
        url = src.get("url", "")
        title = src.get("title", "No Title")
        summary = src.get("summary", "")
        published_date = src.get("published_date", "")

        url_index_map[source_id] = url

        formatted_text += f"\n--- [{source_id}] {title} ({url}) Date: {published_date} ---\n"
        if summary:
            formatted_text += f"SUMMARY: {summary}\n"

    return formatted_text, url_index_map

if __name__ == "__main__":
    # Test loading cached Augment Code harvested sources
    sample_file = os.path.join(os.path.dirname(__file__), "test_exa_news_results_augmentcode_com.json")
    if os.path.exists(sample_file):
        with open(sample_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            sources = data.get("harvested_sources", [])

        indexed_text, url_map = format_indexed_evidence(sources)
        print("=================================================================")
        print("INDEXED EVIDENCE TEXT PREVIEW:")
        print("=================================================================")
        print(indexed_text[:1500])
        print("=================================================================")
        print("URL INDEX LOOKUP MAP:")
        print("=================================================================")
        print(json.dumps(url_map, indent=2))
