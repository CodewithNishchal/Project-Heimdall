import httpx
import json

res = httpx.post(
    'https://google.serper.dev/search',
    headers={'X-API-KEY': '219d2da7a049d5a9d821ff461295fc7ad9d6fbbf', 'Content-Type': 'application/json'},
    json={'q': 'site:linkedin.com/company "Venture to Funds"'}
)

print(json.dumps(res.json().get('organic', []), indent=2))
