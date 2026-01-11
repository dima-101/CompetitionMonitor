import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"

print(f"🔑 API Key: {API_KEY[:20]}..." if API_KEY else "❌ Ключ не найден!")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "sonar-pro",
    "messages": [
        {"role": "user", "content": "What are the main competitors of Figma in design tools?"}
    ],
    "temperature": 0.7,
    "max_tokens": 800
}

print("🚀 Отправляю запрос к Perplexity...")
try:
    response = requests.post(PERPLEXITY_URL, json=payload, headers=headers, timeout=30)
    print(f"✅ Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"\n📊 Ответ от Perplexity:\n{content[:500]}")
    else:
        print(f"❌ Error: {response.text}")
except Exception as e:
    print(f"❌ Exception: {str(e)}")
