import asyncio
import os
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

async def test_groq():
    api_key = os.getenv("GROQ_API_KEY")
    print(f"API Key present: {bool(api_key)}")
    if api_key:
        print(f"API Key prefix: {api_key[:5]}...")
    
    # Model from config
    model = "llama-3.3-70b-versatile" 
    # model = "llama-3.3-70b-versatile" # Fallback
    
    print(f"Testing model: {model}")
    
    try:
        client = AsyncGroq(api_key=api_key)
        response = await client.chat.completions.create(
            messages=[{"role": "user", "content": "ping"}],
            model=model,
            max_tokens=10
        )
        print("Success!")
        print(response.choices[0].message.content)
        await client.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_groq())
