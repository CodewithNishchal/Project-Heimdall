import os
import sys
import json
import httpx
from dotenv import dotenv_values

ZHIPU_KEY = "4d1026c96ff2401689c8053dc8012009.2EpdDJ0n8P2JAcrD"

def test_glm4_flash():
    print("=" * 70)
    print("🚀 Z.AI / ZHIPU GLM-4 VALIDATION & CLASSIFICATION TEST")
    print("=" * 70)

    # Candidate endpoints & models from Z.AI docs
    endpoints = [
        "https://api.z.ai/api/paas/v4/chat/completions",
        "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    ]
    candidate_models = [
        "glm-4-32b-0414-128k",
        "glm-4-flash",
        "glm-4",
        "glm-4-air"
    ]

    print(f"Testing Key: {ZHIPU_KEY[:8]}...{ZHIPU_KEY[-4:]}\n")

    working_endpoint = None
    working_model = None

    with httpx.Client(timeout=20.0) as client:
        for ep in endpoints:
            for model_code in candidate_models:
                print(f"Testing [{ep.split('/')[2]}] -> Model [{model_code}]... ", end="", flush=True)
                headers = {
                    "Authorization": f"Bearer {ZHIPU_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model_code,
                    "messages": [
                        {"role": "user", "content": "Respond with 'OK'"}
                    ],
                    "max_tokens": 10
                }
                try:
                    resp = client.post(ep, headers=headers, json=payload)
                    if resp.status_code == 200:
                        print("✅ WORKING (200 OK)")
                        working_endpoint = ep
                        working_model = model_code
                        break
                    else:
                        print(f"❌ {resp.status_code} ({resp.text[:60]})")
                except Exception as e:
                    print(f"❌ Error: {e}")
            if working_endpoint:
                break

    if working_model:
        print(f"\n🎉 SUCCESS: Model '{working_model}' is active and working!")
    else:
        print("\n⚠️ No working model code found on this key.")

if __name__ == "__main__":
    test_glm4_flash()
