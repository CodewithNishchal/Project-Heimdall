import os
import requests
import json
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

APIFY_API_KEY = os.getenv("APIFY_API_KEY")

def main():
    if not APIFY_API_KEY:
        print("Error: APIFY_API_KEY is not set in .env")
        return

    # Using the exact Apify actor ID from HarvestAPI (in REST API, use ~ instead of /)
    ACTOR_ID = "harvestapi~linkedin-company" 
    
    print(f"🚀 Testing Apify Actor: {ACTOR_ID}")
    print("Using APIFY_API_KEY from .env...")
    
    # Input payload based on HarvestAPI schema
    payload = {
        "companies": [
            "https://www.linkedin.com/company/triomics"
        ]
    }

    # API Endpoint to start an Actor run
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={APIFY_API_KEY}"
    
    print(f"Starting actor run with payload: {json.dumps(payload)}")
    
    try:
        # 1. Start the Actor run
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        run_data = response.json().get("data", {})
        run_id = run_data.get("id")
        default_dataset_id = run_data.get("defaultDatasetId")
        
        print(f"✅ Run started successfully! Run ID: {run_id}")
        print("Waiting for the run to finish... (this usually takes 5-10 seconds)")
        
        # 2. Poll for completion
        status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_API_KEY}"
        while True:
            status_res = requests.get(status_url)
            status_res.raise_for_status()
            
            status = status_res.json().get("data", {}).get("status")
            print(f"Current status: {status}...")
            
            if status == "SUCCEEDED":
                print("✅ Run finished!")
                break
            elif status in ["FAILED", "ABORTING", "ABORTED", "TIMED-OUT"]:
                print(f"❌ Run failed or was aborted. Final status: {status}")
                # Fetch actor logs if it failed
                log_url = f"https://api.apify.com/v2/logs/{run_id}?token={APIFY_API_KEY}"
                log_res = requests.get(log_url)
                if log_res.status_code == 200:
                    print("\n--- ACTOR RUN LOGS ---")
                    print(log_res.text)
                return
                
            time.sleep(3) # Poll every 3 seconds
            
        # 3. Fetch the results from the dataset
        print("\nFetching results from the dataset...")
        dataset_url = f"https://api.apify.com/v2/datasets/{default_dataset_id}/items?token={APIFY_API_KEY}"
        
        items_res = requests.get(dataset_url)
        items_res.raise_for_status()
        
        items = items_res.json()
        
        print("\n" + "="*70)
        print("🎉 HARVESTAPI LINKEDIN COMPANY DETAILS RESULTS")
        print("="*70)
        
        # Print results directly into terminal log
        print(json.dumps(items, indent=2))
        
        print("="*70)
        print(f"Total items retrieved: {len(items)}")
        
        # Save output to JSON file for easy inspection
        output_file = "harvestapi_company_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        print(f"Saved full company infographics to '{output_file}'")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ API Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response details: {e.response.text}")

if __name__ == "__main__":
    main()
