import asyncio
from batch_processor import process_from_excel

async def main():
    print("Starting test batch...")
    results = await process_from_excel("K:/AI_trader2/Stocks.xlsx", capture_only=True)
    print(f"Results: {results}")

if __name__ == "__main__":
    asyncio.run(main())
