import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

EXA_API_KEY = os.getenv("EXA_API_KEY")
if not EXA_API_KEY or EXA_API_KEY == "your_exa_api_key_here":
    print("Error: Please set a valid EXA_API_KEY in your .env file.")
    exit(1)

def main():
    print("Searching using Exa AI (Free Tier REST API)...")
    
    # Directly load exa_query from backend/intent_config.json
    config_path = os.path.join(os.path.dirname(__file__), "intent_config.json")
    query = None
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                query = cfg.get("exa_query")
        except Exception as e:
            print(f"Warning: Could not read intent_config.json: {e}")

    if not query:
        query = "multi-location franchise, healthcare, home services, or B2B companies in the US that recently opened a new location, expanded operations, or scaled revenue to $5M-$20M without a listed in-house marketing director"

    print(f"\n[Exa AI Query]: {query}\n")
    
    url = "https://api.exa.ai/search"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": EXA_API_KEY
    }
    payload = {
        "query": query,
        "type": "neural",
        "useAutoprompt": False,
        "category": "company",
        "excludeDomains": ["clutch.co", "upcity.com", "designrush.com", "goodfirms.co", "42web.io", "byethost7.com", "zya.me"],
        "numResults": 100,
        "contents": {
            "text": True,
            "summary": True
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        print(f"Successfully fetched {len(results)} raw company candidates from Exa AI!")
        
        parsed_results = []
        for res in results:
            text_snippet = res.get("text", "")
            parsed_results.append({
                "title": res.get("title"),
                "url": res.get("url"),
                "summary": res.get("summary"),
                "text_snippet": text_snippet[:600] if text_snippet else None
            })
            
        output_file = os.path.join(os.path.dirname(__file__), "exa_free_tier_results.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(parsed_results, f, indent=2, ensure_ascii=False)
            
        print(f"\nFull candidate context saved to '{output_file}'.")
        
    except requests.exceptions.RequestException as e:
        print(f"Failed to search: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response body: {e.response.text}")

if __name__ == "__main__":
    main()
