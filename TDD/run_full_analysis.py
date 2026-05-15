import asyncio
from batch_processor import process_from_excel

async def main():
    print("Starting full batch analysis for AAPL, MSFT, QQQ...")
    results = await process_from_excel(
        "K:/AI_trader2/Stocks.xlsx", 
        model_name="gemini-2.5-flash", 
        capture_only=False,
        max_concurrent=3
    )
    for ticker, res in results.items():
        print(f"{ticker}: {res['status']} - {res.get('message', 'Success')}")

if __name__ == "__main__":
    asyncio.run(main())
