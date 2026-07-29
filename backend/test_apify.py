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

    # Using the exact Apify actor ID from the screenshot (in REST API, use ~ instead of /)
    ACTOR_ID = "signalbase~signalbase-api" 
    
    print(f"🚀 Testing Apify Actor: {ACTOR_ID}")
    print("Using APIFY_API_KEY from .env...")
    
    # Define the input payload using the confirmed SignalBase companies schema
    payload = {
        "signalType": "companies",
        "countries": "US",
        "industry": "Marketing and Advertising",
        "employee_count_gte": 10,
        "employee_count_lte": 200,
        "founded_year_gte": 2015,
        "sort_by": "employee_count",
        "sort_order": "desc",
        "page": 1,
        "limit": 50,
        "count": True  # Set count: True to verify filters for FREE without burning credits
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
        print("Waiting for the run to finish... (this may take a minute or two)")
        
        # 2. Poll for completion
        status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_API_KEY}"
        while True:
            status_res = requests.get(status_url)
            status_res.raise_for_status()
            
            status = status_res.json().get("data", {}).get("status")
            print(f"Current status: {status}...")
            
            if status == "SUCCEEDED":
                print("✅ Run finished!")
                # Fetch actor logs to see internal execution details
                log_url = f"https://api.apify.com/v2/logs/{run_id}?token={APIFY_API_KEY}"
                log_res = requests.get(log_url)
                if log_res.status_code == 200:
                    print("\n--- ACTOR RUN LOGS ---")
                    print(log_res.text)
                break
            elif status in ["FAILED", "ABORTING", "ABORTED", "TIMED-OUT"]:
                print(f"❌ Run failed or was aborted. Final status: {status}")
                # Try to fetch logs if it failed
                log_url = f"https://api.apify.com/v2/logs/{run_id}?token={APIFY_API_KEY}"
                log_res = requests.get(log_url)
                if log_res.status_code == 200:
                    print("\n--- ACTOR LOGS ---")
                    print(log_res.text)
                return
                
            time.sleep(5) # Poll every 5 seconds
            
        # 3. Fetch the results from the dataset
        print("\nFetching results from the dataset...")
        dataset_url = f"https://api.apify.com/v2/datasets/{default_dataset_id}/items?token={APIFY_API_KEY}"
        
        items_res = requests.get(dataset_url)
        items_res.raise_for_status()
        
        items = items_res.json()
        
        print("\n" + "="*70)
        print("🎉 RESULTS FROM APIFY SIGNAL BASE")
        print("="*70)
        
        # Output directly to terminal logs as requested
        print(json.dumps(items, indent=2))
        
        print("="*70)
        print(f"Total items retrieved: {len(items)}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ API Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response details: {e.response.text}")
            
        print("\nNOTE: Make sure the ACTOR_ID is completely correct. If it throws a 'not found' or 'Unauthorized', double check the Actor ID from your Apify account.")

if __name__ == "__main__":
    main()
