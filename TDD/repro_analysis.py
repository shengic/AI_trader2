import asyncio
import os
from core_analyzer import analyze_stock

async def test_aapl_analysis():
    ticker = "AAPL"
    image_path = "captures/20260515/AAPL_1_year.png"
    model_name = "gemini-2.5-flash"
    
    if not os.path.exists(image_path):
        print(f"Image not found: {image_path}")
        return

    print(f"Analyzing {ticker} with {model_name}...")
    try:
        result = await analyze_stock(ticker, image_path, model_name=model_name)
        print("--- Result ---")
        print(result)
        print("--------------")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_aapl_analysis())
