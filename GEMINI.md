# Gemini API 整合技術指南 (StockVision AI 專業版)

本文件專為 AI 開發者與系統架構師設計，詳述如何在高負載環境下利用 Gemini 多模態 API 構建精準的股票分析系統。

## 1. 視覺理解與擷取標準 (Vision Standards)
為了讓 Gemini 模型能精確識別 K 線圖中的微小標記 (如十字星、缺口或均線交會)，系統必須遵循以下規格：
*   **高清擷取**: 使用 `device_scale_factor=4.166` (400 DPI) 進行截圖。這是識別 Finviz 圖表中細小字體與趨勢線的關鍵。
*   **Viewport 設定**: 寬度固定為 `1280px`，高度動態調整（預設 `1500px`），以捕捉包含完整財務數據的視圖。
*   **模型支援**: 必須使用支援 `multimodal` 輸入的模型，首選 `gemini-2.5-flash` 或 `gemini-2.0-flash`。

## 2. 內容快取策略 (Content Caching)
由於「全域分析規則」(`rules/global.txt`) 內容龐大且在批次分析中保持不變，我們使用 `caching.CachedContent`：
*   **快取對象**: 全域量價規則 + 專業角色設定。
*   **生命週期 (TTL)**: 預設為 60 分鐘，足以覆蓋單次完整的批次掃描。
*   **模型掛載**: 在 `batch_processor.py` 初始化時建立一次快取，後續所有個股分析均使用 `from_cached_content` 載入模型，顯著減少 API 延遲。

## 3. 提示詞工程邏輯 (Prompt Engineering)
系統採用「結構化引導」與「專家矩陣」混合提示詞：
*   **第一步：核心判定**: 強制模型優先比對「量價八階律」中的 Stage 1-8。
*   **第二步：三維特徵提取**: 提取「位階」、「價格動能」、「量能變化」。
*   **第三步：交叉驗證**: 將上述特徵帶入「價量關係決策矩陣」進行查表。
*   **輸出格式控制**: 嚴格要求輸出 `## 📌 量價階段判定：【第 X 階段 - 名稱】` 格式，以便於前端解析。

## 4. 非同步與併發控管 (Concurrency Control)
在高負載批次處理下，系統透過以下方式保證穩定性：
*   **非同步訊號量 (Semaphore)**: 固定 `asyncio.Semaphore(5)`，限制同時執行的 Playwright 與 API 呼叫數量，避免觸發 Finviz 的 WAF 或 Gemini 的 Rate Limit。
*   **回呼進度條 (Callback Pattern)**: `process_from_excel` 支援傳入 `progress_callback` 函式，用於在 UI 層級即時更新 `st.status` 狀態。

## 5. 資料存儲與回讀規格
### MySQL Schema: `stock_reports`
| 欄位名 | 類型 | 說明 |
| :--- | :--- | :--- |
| `ticker` | VARCHAR | 股票代號 (索引) |
| `period` | VARCHAR | 分析週期 |
| `analysis_date` | DATE | 掃描日期 (索引) |
| `report_content` | LONGTEXT | Markdown 分析內文 |
| `image_data` | LONGBLOB | 截圖二進位數據 (用於追問功能) |

### Excel 回寫規範 (Openpyxl)
*   所有內容必須套用 `Font(name="Georgia")`。
*   對齊方式必須為 `Alignment(horizontal="center", vertical="center", wrap_text=True)`。
*   摘要內容擷取報告的第一部分 (Stage 判定)。

## 6. 核心分析邏輯參考 (The 8-Stage Law)
開發者應確保 `global.txt` 包含以下邏輯節點：
1.  **Stage 1 (築底)**: 底部 + 價平 + 量增
2.  **Stage 2 (突破)**: 底部/上漲 + 價漲 + 量增
3.  **Stage 3 (主升)**: 上漲 + 價漲 + 量平
4.  **Stage 4 (背離)**: 頂部 + 價漲 + 量縮
5.  **Stage 5 (頂部)**: 頂部 + 價平 + 量縮
6.  **Stage 6 (跌勢)**: 頂部/下跌 + 價跌 + 量縮
7.  **Stage 7 (主跌)**: 下跌 + 價跌 + 量平
8.  **Stage 8 (末期)**: 底部 + 價跌 + 量增

---
*Technical Specification for StockVision AI AI-to-AI Collaboration*
