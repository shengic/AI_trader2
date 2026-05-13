# Gemini API 整合技術指南 (StockVision AI)

本文檔詳細說明本系統如何在高負載股票分析場景中優化 Gemini API 的使用。

## 1. 提示詞架構 (Prompt Strategy)
* **核心邏輯**: 結合 `rules/global.txt` 與個股專屬規則，強制模型擔任「專業技術分析師」。
* **多模態對齊**: 利用 Gemini 1.5/2.0+ 對高解析度圖表 (400 DPI) 的理解能力，進行 K 線與趨勢分析。

## 2. 效能優化與併發
* **併發處理**: `batch_processor.py` 使用 `asyncio.gather` 並配合 `asyncio.Semaphore(5)` 進行非同步並行處理，顯著提升掃描速度。
* **模型選擇**: 
    * 支援 **Gemini 2.0/2.5 Flash** (推薦，速度極快)。
    * 深度追問可手動切換至 **Pro** 系列模型。

## 3. 圖像規格與擷取
* **解析度**: 強制執行 400 DPI 縮放 (`scale_factor=4.16`)，確保 Finviz 細微標記清晰。
* **覆寫機制**: 擷取成功時會自動覆蓋舊圖；擷取失敗時保留舊圖並在報告中加入 `⚠️ 注意` 標註。

## 4. 週期轉換規則 (Finviz Mapping)
系統支援以下週期字串，會自動對應至 Finviz 參數：

| 名稱 (Excel 輸入) | Finviz Period (p) | Finviz Range (r) |
| :--- | :--- | :--- |
| **1 month** | daily | m1 |
| **3 month** | daily | m3 |
| **6 month** | daily | m6 |
| **year to date** | daily | ytd |
| **1 year** | daily | y1 |
| **2 year** | weekly | y2 |
| **5 year** | monthly | y5 |
| **max** | monthly | max |

## 5. Excel 格式規範 (Output Style)
* **字體**: 所有寫入 Excel 的內容必須使用 **Georgia** 字體。
* **對齊**: 儲存格內容必須設定為 **水平置中 (Center)** 與 **垂直置中 (Middle)**。
* **欄位**: 第四欄為 `AI_Analysis` (摘要)，第五欄為 `Last_Update` (時間)。
