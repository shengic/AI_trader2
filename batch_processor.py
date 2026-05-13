import asyncio
import os
import datetime
import random
import pandas as pd
from playwright.async_api import async_playwright
from core_analyzer import analyze_stock

# Finviz 週期對照表
PERIOD_MAPPING = {
    "1 month": {"p": "d", "r": "m1"},
    "3 month": {"p": "d", "r": "m3"},
    "6 month": {"p": "d", "r": "m6"},
    "year to date": {"p": "d", "r": "ytd"},
    "1 year": {"p": "d", "r": "y1"},
    "2 year": {"p": "w", "r": "y2"},
    "5 year": {"p": "m", "r": "y5"},
    "max": {"p": "m", "r": "max"}
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
]

async def internal_capture(url, output_path, selector=None, height=1500):
    """複刻 capture.py 的核心邏輯，確保參數一致"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        scale_factor = 4.166666666666667 # 400 DPI
        user_agent = random.choice(USER_AGENTS)
        
        context = await browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1280, "height": int(height)},
            device_scale_factor=scale_factor,
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9,zh-TW;q=0.8,zh;q=0.7",
                "Referer": "https://www.google.com/"
            }
        )
        
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5) # 等待渲染
            
            if selector:
                element = await page.query_selector(selector)
                if element:
                    await element.screenshot(path=output_path)
                else:
                    await page.screenshot(path=output_path, full_page=False)
            else:
                await page.screenshot(path=output_path, full_page=False)
        finally:
            await browser.close()

def get_finviz_url(ticker, period_str):
    """根據 ticker 與週期字串生成 Finviz URL"""
    mapping = PERIOD_MAPPING.get(period_str.lower())
    if not mapping:
        mapping = PERIOD_MAPPING["1 year"]
    
    p = mapping["p"]
    r = mapping["r"]
    # 使用 quote.ashx 確保參數正確傳遞
    return f"https://finviz.com/quote.ashx?t={ticker}&p={p}&r={r}"

async def process_single_stock(ticker, period, model_name="gemini-1.5-flash", capture_only=False):
    """
    處理單一股票的截圖與分析 (供 UI 直接調用)
    """
    ticker = str(ticker).strip().upper()
    period = str(period).strip().lower()
    today = datetime.datetime.now().strftime("%Y%m%d")
    
    os.makedirs(f"captures/{today}", exist_ok=True)
    os.makedirs(f"reports/{today}", exist_ok=True)
    
    url = get_finviz_url(ticker, period)
    period_suffix = period.replace(' ', '_')
    image_path = f"captures/{today}/{ticker}_{period_suffix}.png"
    
    try:
        await internal_capture(url, image_path, height=1500)
        
        report_path = f"reports/{today}/{ticker}_{period_suffix}.md"
        if not capture_only:
            report = await analyze_stock(ticker, image_path, model_name)
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report)
        else:
            if not os.path.exists(report_path):
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(f"# {ticker} ({period}) 分析報告\n\n(等待 AI 分析中...)")
        return {"status": "success", "image_path": image_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def process_from_excel(excel_path, model_name="gemini-1.5-flash", capture_only=False, max_concurrent=5):
    """
    從 Excel 讀取名單並併發處理
    """
    if not os.path.exists(excel_path):
        return {}

    # 讀取 Excel (不設標題，手動處理)
    df = pd.read_excel(excel_path, header=None) 

    results = {}
    today = datetime.datetime.now().strftime("%Y%m%d")

    os.makedirs(f"captures/{today}", exist_ok=True)
    os.makedirs(f"reports/{today}", exist_ok=True)

    semaphore = asyncio.Semaphore(max_concurrent)

    async def sem_process_stock(ticker, period, row_idx):
        async with semaphore:
            return await process_single_stock_internal(ticker, period, today, model_name, capture_only, row_idx)

    tasks = []
    for index, row in df.iterrows():
        # 跳過第一行 (標題) 或空白行
        if index == 0: continue

        ticker = row.iloc[0]
        period = row.iloc[1] if len(row) > 1 else None

        # 嚴格過濾無效 Ticker
        if pd.isna(ticker) or str(ticker).strip().lower() in ["nan", "stock name", ""]: 
            continue

        ticker = str(ticker).strip().upper()
        # 處理 Period 為 NaN 或 "nan" 字串的情況
        if pd.isna(period) or str(period).strip().lower() in ["nan", ""]:
            period = "1 year" 
        else:
            period = str(period).strip().lower()
        
        tasks.append(sem_process_stock(ticker, period, index))

    # 執行併發任務
    task_results = await asyncio.gather(*tasks)
    
    for res in task_results:
        if res:
            results[res["ticker"]] = res

    # 寫入 Excel 結果 (待實作)
    if not capture_only:
        await write_results_to_excel(excel_path, task_results)

    return results

async def process_single_stock_internal(ticker, period, date_str, model_name, capture_only, row_idx):
    """
    內部處理邏輯，支援併發
    """
    url = get_finviz_url(ticker, period)
    period_suffix = period.replace(' ', '_')
    image_path = f"captures/{date_str}/{ticker}_{period_suffix}.png"
    backup_path = f"captures/{date_str}/{ticker}_{period_suffix}_old.png"
    
    try:
        temp_image_path = f"captures/{date_str}/temp_{ticker}_{period_suffix}_{row_idx}.png"
        print(f"正在擷取: {ticker} ({period})")
        await internal_capture(url, temp_image_path, height=1500)
        
        report_path = f"reports/{date_str}/{ticker}_{period_suffix}.md"
        capture_failed = False
        
        if os.path.exists(temp_image_path):
            # 擷取成功：直接覆蓋舊檔案
            if os.path.exists(image_path):
                os.remove(image_path)
            os.rename(temp_image_path, image_path)
        else:
            # 擷取失敗
            if os.path.exists(image_path):
                capture_failed = True
            else:
                raise Exception("截圖檔案未產生且無舊圖")

        report_content = ""
        if not capture_only:
            report_content = await analyze_stock(ticker, image_path, model_name)
            
            # 如果擷取失敗但有舊圖，在報告頂部加入註記
            if capture_failed:
                file_time = datetime.datetime.fromtimestamp(os.path.getmtime(image_path)).strftime("%Y-%m-%d %H:%M:%S")
                warning_msg = f"> ⚠️ **注意**：今日截圖失敗，目前顯示的是舊有圖片（擷取時間：{file_time}）。\n\n"
                report_content = warning_msg + report_content
                
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
        else:
            if not os.path.exists(report_path):
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(f"# {ticker} ({period}) 分析報告\n\n(等待 AI 分析中...)")
        
        return {
            "ticker": ticker,
            "status": "success",
            "report_path": report_path,
            "image_path": image_path,
            "row_idx": row_idx,
            "summary": report_content[:100].replace("\n", " ") + "..." if report_content else ""
        }
    except Exception as e:
        print(f"處理 {ticker} 時發生錯誤: {e}")
        return {
            "ticker": ticker,
            "status": "error",
            "message": str(e),
            "row_idx": row_idx
        }

async def write_results_to_excel(excel_path, task_results):
    """
    將分析結果寫回 Excel，並套用 Georgia 字體與置中對齊
    """
    from openpyxl import load_workbook
    from openpyxl.styles import Font, Alignment

    wb = load_workbook(excel_path)
    ws = wb.active

    # 確保有標題行
    if ws.cell(row=1, column=4).value != "AI_Analysis":
        ws.cell(row=1, column=4).value = "AI_Analysis"
        ws.cell(row=1, column=5).value = "Last_Update"

    georgia_font = Font(name="Georgia", size=11)
    center_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for res in task_results:
        row = res["row_idx"] + 1 # openpyxl is 1-indexed
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        if res["status"] == "success":
            ws.cell(row=row, column=4).value = res["summary"]
            ws.cell(row=row, column=5).value = current_time
        else:
            ws.cell(row=row, column=4).value = f"Error: {res.get('message', 'Unknown')}"
            ws.cell(row=row, column=5).value = current_time

        # 套用格式
        for col in range(1, 6):
            cell = ws.cell(row=row, column=col)
            cell.font = georgia_font
            cell.alignment = center_alignment

    # 套用標題格式
    for col in range(1, 6):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(name="Georgia", bold=True)
        cell.alignment = center_alignment

    wb.save(excel_path)


if __name__ == "__main__":
    # 測試代碼
    # asyncio.run(process_from_excel("stocks.xlsx"))
    pass
