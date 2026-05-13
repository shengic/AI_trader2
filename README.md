# StockVision AI: 本地化股票自動分析系統

這是為了解決每日批次股票分析需求而設計的專業方案。本系統結合 Python 截圖、Excel 管理、Gemini 1.5 API 批次分析，並提供 Streamlit 互動介面。

## 核心功能
* **Excel 驅動**：透過 Excel 管理股票清單與分析週期 (e.g., 5 year, 1 year)。
* **自動化截圖**：模擬真實瀏覽器行為 (Random User-Agent, 400 DPI) 抓取 Finviz 專業圖表。
* **多模態分析**：Gemini 1.5 結合圖片像素與自定義 Markdown 規則進行技術面分析。
* **互動式 UI**：支援報告瀏覽、圖表顯示與即時 AI 追問。

## 快速開始
1. **安裝依賴**：
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
2. **設定環境變數**：在 `.env` 中加入 `GEMINI_API_KEY=your_key_here`。
3. **啟動系統**：
   ```bash
   streamlit run app.py
   ```

## 資料夾結構
* `/rules`: 存放 `global.txt` 全域規則與 `/tickers` 特定個股規則。
* `/captures`: 每日圖表截圖 (按日期存放)。
* `/reports`: AI 分析報告 (Markdown 格式)。

## Excel 格式
Excel 檔案需包含兩欄（無需標題）：
* 第一欄：股票代號 (Ticker, e.g., AAPL)
* 第二欄：分析週期 (Period, e.g., 1 year, 5 year)
