# StockVision AI: 本地化股票自動分析系統

這是為了解決每日批次股票分析需求而設計的專業方案。本系統結合 Playwright 高清截圖、Excel 自動化管理、Gemini 多模態 API 併發分析，並提供穩定且流暢的 Streamlit 互動介面。

## 核心功能
* **Excel 雙向同步**：透過 Excel 管理名單，系統分析後會自動寫回摘要，並套用 Georgia 專業字體與排版。
* **高清併發擷取**：模擬真實瀏覽器行為 (400 DPI) 併行抓取 Finviz 圖表，效率提升 5 倍以上。
* **智慧報告管理**：嚴格對齊 Excel 目前設定，自動隱藏過時報告，並在擷取失敗時自動標記舊圖提示。
* **互動式 UI**：單一選單快速切換、本地規則即時顯示、支援對圖表的 AI 深度追問。

## 支援的分析週期
在 Excel 的第二欄輸入以下字串即可自動切換圖表週期：
* `1 month` / `3 month` / `6 month`
* `year to date` / `1 year` (預設)
* `2 year` / `5 year` / `max`

## 快速開始
1. **安裝環境**：
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
2. **API 設定**：在介面側邊欄輸入你的 `Gemini API Key`。
3. **啟動系統**：
   ```bash
   streamlit run app.py
   ```

## 資料夾結構
* `/rules`: 存放 `global.txt` (全域規則) 與 `/tickers` (個股專屬規則)。
* `/captures`: 存放今日擷取的股票圖表。
* `/reports`: 存放 AI 生成的 Markdown 分析報告。

## Excel 格式要求
* **第一欄**：股票代號 (e.g., QQQ)
* **第二欄**：分析週期 (e.g., 6 month)
* **第三欄**：本地觀察規則 (選填，會顯示在 UI 右側)
* **第四欄起**：系統會自動填入 `AI_Analysis` 與 `Last_Update`。
