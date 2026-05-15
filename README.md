# StockVision AI: 專業股票多模態自動化分析系統 (v1.1.0)

StockVision AI 是一款專為量化交易者設計的端到端自動化股票分析平台。它結合了現代非同步程式設計、多模態大語言模型 (Gemini 2.5) 以及專業的量價理論，能夠在數分鐘內完成上百檔股票的高清圖表分析並生成專業報告。

## 🏛️ 系統架構 (System Architecture)
本系統採模組化設計，確保高度可擴展性與穩定性：
*   **前端介面 (UI Layer)**: 使用 `Streamlit` 構建，提供即時進度追蹤 (st.status)、圖表瀏覽與 AI 追問功能。
*   **核心處理器 (Batch Processor)**: 基於 `asyncio` 與 `Playwright` 的非同步引擎，支援 400 DPI 高清截圖與併發處理。
*   **AI 分析引擎 (Intelligence Layer)**: 整合 `Google Gemini 2.5/2.0` API，利用內容快取 (CachedContent) 優化全域規則處理。
*   **資料持久化 (Persistence Layer)**: 
    *   **Excel**: 作為名單管理與輕量化摘要輸出 (`Stocks.xlsx`)。
    *   **MySQL**: 儲存結構化報告內容與二進位圖片檔案 (`stock_reports` 資料表)。
    *   **Filesystem**: 儲存原始截圖 (.png) 與 Markdown 報告 (.md)。

## 🚀 核心功能特色
*   **量價八階律 (The 8-Stage Cycle)**: 內建專業級量價判定邏輯，自動識別「築底、突破、主升、背離、頂部、跌勢、主跌、末期」。
*   **多模態深度分析**: AI 直接讀取 Finviz 高清圖表，分析 K 線形態、移動平均線 (SMA) 以及 RSI 超買超賣狀態。
*   **即時進度追蹤**: 採用非同步回呼機制，在介面端顯示「擷取圖表、初始化快取、分析中」等細部狀態，拒絕頁面卡頓。
*   **智慧快取技術**: 自動將龐大的全域規則預載至 Gemini 雲端快取，顯著提升長文本分析的反應速度並節省 Token。
*   **Excel 自動美化**: 寫回摘要時自動套用 **Georgia** 專業字體，並執行水平與垂直置中排版。

## 🛠️ 環境架構與部署
### 1. 軟體需求
*   Python 3.10+
*   MySQL 8.0+
*   Playwright (Chromium)

### 2. 安裝步驟
```bash
# 克隆專案並進入資料夾
pip install -r requirements.txt
playwright install chromium
```

### 3. 環境變數 (.env)
建立 `.env` 檔案並設定以下內容：
```env
GEMINI_API_KEY=你的API金鑰
DB_HOST=localhost
DB_USER=你的帳號
DB_PASSWORD=你的密碼
DB_NAME=ai_trader
```

### 4. 啟動指令
```bash
streamlit run app.py
```

## 📂 資料夾與檔案說明
*   `app.py`: 系統主入口，處理 Streamlit UI 邏輯。
*   `batch_processor.py`: 非同步批次處理引擎，負責截圖與流程控管。
*   `core_analyzer.py`: AI 分析核心，定義 Prompt 與快取邏輯。
*   `db_manager.py`: 資料庫連線與 SQL 操作。
*   `rules/global.txt`: 全域量價分析規則設定檔。
*   `rules/tickers/*.txt`: 個股專屬觀察規則。
*   `Stocks.xlsx`: 分析目標清單與摘要輸出。

## 📊 Excel 欄位定義
| 欄位 | 名稱 | 說明 |
| :--- | :--- | :--- |
| A | Stock Name | 股票代號 (如: AAPL, QQQ) |
| B | Period | 分析週期 (如: 1 year, 6 month) |
| C | Local Rule | 個股專屬規則 (將與 global.txt 合併傳給 AI) |
| D | AI_Analysis | 系統寫回的 Stage 判定與分析摘要 |
| E | Last_Update | 最後更新時間 |

---
*Developed by Albert Sheng | v1.1.0 Optimized for Gemini 2.5*
