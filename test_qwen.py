import asyncio
import logging
from backend.pipeline.social_classifier import classify_social_intent

logging.basicConfig(level=logging.INFO)

async def test_qwen():
    post_text = "We are an expanding SaaS company looking for a reliable performance marketing agency to manage our Google Ads."
    author_bio = "VP of Marketing @ Acme SaaS"
    print("\n--- Testing Qwen2.5-7B OpenRouter Intent Classifier ---")
    result = await classify_social_intent(post_text, author_bio)
    print("\n=== CLASSIFICATION RESULT ===")
    print(result)
    print("===============================\n")

if __name__ == "__main__":
    asyncio.run(test_qwen())
