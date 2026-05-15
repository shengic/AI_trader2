import os
import PIL.Image
import google.generativeai as genai
from google.generativeai import caching
import datetime
from dotenv import load_dotenv

load_dotenv()

# 設定 API Key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def get_model(model_name="gemini-2.5-flash"):
    """取得 Gemini 模型實例"""
    return genai.GenerativeModel(model_name)

def load_rules(ticker=None, include_global=True):
    """讀取全域與特定個股規則"""
    rules = ""
    if include_global:
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

def create_global_cache(model_name="gemini-2.5-flash"):
    """建立全域規則快取"""
    global_rules_path = "rules/global.txt"
    if not os.path.exists(global_rules_path):
        return None
    
    with open(global_rules_path, "r", encoding="utf-8") as f:
        global_content = f.read()

    # 建立快取 (有效期預設 1 小時)
    cache = caching.CachedContent.create(
        model=f"models/{model_name}",
        display_name="global_stock_rules",
        system_instruction=f"你是一位頂尖量化股市分析師。請嚴格遵守以下全域規則：\n\n{global_content}",
        ttl=datetime.timedelta(minutes=60),
    )
    return cache

async def analyze_stock(ticker, image_path, model_name="gemini-2.5-flash", extra_rules="", cache_name=None):
    """
    分析單一股票，支援快取掛載
    """
    if not os.path.exists(image_path):
        return f"錯誤：找不到圖片 {image_path}"

    if cache_name:
        # 使用快取模式
        cache = caching.CachedContent.get(cache_name)
        model = genai.GenerativeModel.from_cached_content(cached_content=cache)
        # 快取中已包含全域規則，此處僅讀取個股規則
        file_rules = load_rules(ticker, include_global=False)
    else:
        # 標準模式
        model = get_model(model_name)
        file_rules = load_rules(ticker, include_global=True)
    
    img = PIL.Image.open(image_path)
    
    prompt = f"""
    請擔任「頂尖量化股市分析師」，根據提供的股票圖表、全域規則以及個股規則進行深度分析。

    【個股資訊】
    股票代號：{ticker}
    當前日期：{datetime.date.today().strftime("%Y-%m-%d")}
    {f"【Excel 額外規則】：{extra_rules}" if extra_rules else ""}
    {file_rules}

    【執行指令】
    1. **核心判定 (最優先)**：對照全域規則中的「量價八階律」，確定目前處於哪一個階段 (Stage 1-8)。
    2. **參數解析**：從圖表中識別當前的「位階」(底部/上漲中/頂部/下跌中)、「價格動能」(漲/平/跌) 與「量能變化」(增/平/縮)。
    3. **時事結合**：結合當前日期與你掌握的財經時事進行綜合評論。
    4. **矩陣查表**：使用「價量關係決策矩陣」進行交叉驗證。
    5. **輸出報告**：請嚴格依照以下格式輸出繁體中文報告：

    ## 📌 量價階段判定：【第 X 階段 - 階段名稱】
    *(請務必放在報告第一行)*

    - **位階**: XXX
    - **價格動能**: XXX
    - **量能變化**: XXX

    ## 🌍 市場時事與產業環境分析
    ...
    ## 🔍 技術面細節分析
    ...
    ## 💡 決策矩陣交叉驗證
    ...
    ## 🚩 綜合操作建議 (機率分布)
    ...
    """

    
    response = await model.generate_content_async([prompt, img])
    return response.text

if __name__ == "__main__":
    # 簡單測試用
    # import asyncio
    # asyncio.run(analyze_stock("2330", "captures/2330_1D.png"))
    pass
