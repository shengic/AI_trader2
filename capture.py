import asyncio
import argparse
import datetime
import os
import re
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright

async def capture_screenshot(url, output_path, selector=None, height=1500):
    async with async_playwright() as p:
        # 啟動瀏覽器，加入偽裝 User-Agent
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        browser = await p.chromium.launch(headless=True)
        
        # 調整解析度: 400 DPI 約為 4.16 倍縮放
        scale_factor = 4.166666666666667
        viewport_height = int(height)
        
        context = await browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1280, "height": viewport_height},
            device_scale_factor=scale_factor,
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9,zh-TW;q=0.8,zh;q=0.7",
                "Referer": "https://www.google.com/"
            }
        )
        
        page = await context.new_page()
        
        print(f"正在前往: {url}")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            print("等待頁面渲染...")
            await asyncio.sleep(5)
            
            if selector:
                print(f"正在擷取元素: {selector}")
                element = await page.query_selector(selector)
                if element:
                    await element.screenshot(path=output_path)
                    print(f"元素截圖成功！儲存於: {output_path}")
                else:
                    print(f"錯誤: 找不到元素 {selector}")
            else:
                print(f"正在擷取高度: {viewport_height}px (400 DPI 模式)")
                await page.screenshot(path=output_path, full_page=False)
                print(f"截圖成功！儲存於: {output_path}")
                
        except Exception as e:
            print(f"擷取失敗: {e}")
        finally:
            await browser.close()

def get_filename_from_url(url):
    """從 URL 中提取股票代號 (t) 和時間區間 (r) 作為檔名"""
    try:
        parsed_url = urlparse(url)
        params = parse_qs(parsed_url.query)
        ticker = params.get('t', [None])[0]
        period = params.get('r', [None])[0]
        
        if ticker and period:
            return f"{ticker.upper()}_{period}.png"
        elif ticker:
            return f"{ticker.upper()}.png"
    except Exception:
        pass
    return None

def main():
    parser = argparse.ArgumentParser(description="網頁螢幕截圖工具")
    parser.add_argument("url", help="要擷取的網頁 URL")
    parser.add_argument("-o", "--output", help="輸出檔案路徑")
    parser.add_argument("-s", "--selector", help="要擷取的 HTML 元素選擇器")
    parser.add_argument("-height", "--height", default=1500, help="要擷取的垂直高度 (預設: 1500)")
    
    args = parser.parse_args()
    
    url = args.url
    if not url.startswith("http"):
        url = "https://" + url
        
    if args.output:
        output_path = args.output
    else:
        # 嘗試從 URL 提取檔名 (Ticker_Period.png)
        filename = get_filename_from_url(url)
        if filename:
            output_path = filename
        else:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"screenshot_{timestamp}.png"
        
    asyncio.run(capture_screenshot(url, output_path, args.selector, args.height))

if __name__ == "__main__":
    main()
