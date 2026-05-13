import os
import PIL.Image
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# 設定 API Key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def get_model(model_name="gemini-1.5-flash"):
    """取得 Gemini 模型實例"""
    return genai.GenerativeModel(model_name)

def load_rules(ticker=None):
    """讀取全域與特定個股規則"""
    rules = ""
    # 讀取全域規則
    global_rules_path = "rules/global.txt"
    if os.path.exists(global_rules_path):
        with open(global_rules_path, "r", encoding="utf-8") as f:
            rules += f"【全域分析規則】\n{f.read()}\n\n"
    
    # 讀取個股規則
    if ticker:
        ticker_rules_path = f"rules/tickers/{ticker}.txt"
        if os.path.exists(ticker_rules_path):
            with open(ticker_rules_path, "r", encoding="utf-8") as f:
                rules += f"【{ticker} 特定觀察規則】\n{f.read()}\n\n"
    
    return rules

async def analyze_stock(ticker, image_path, model_name="gemini-1.5-flash"):
    """
    分析單一股票
    """
    if not os.path.exists(image_path):
        return f"錯誤：找不到圖片 {image_path}"

    model = get_model(model_name)
    rules = load_rules(ticker)
    
    img = PIL.Image.open(image_path)
    
    prompt = f"""
    請根據提供的股票圖表與以下規則進行深度分析：
    
    股票代號：{ticker}
    
    {rules}
    
    請直接輸出分析報告。
    """
    
    response = await model.generate_content_async([prompt, img])
    return response.text

if __name__ == "__main__":
    # 簡單測試用
    # import asyncio
    # asyncio.run(analyze_stock("2330", "captures/2330_1D.png"))
    pass
