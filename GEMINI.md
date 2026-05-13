# Gemini API 整合技術指南 (StockVision AI)

本文檔詳細說明本系統如何在高負載股票分析場景中優化 Gemini API 的使用。

## 1. 提示詞架構 (Prompt Strategy)
* **核心邏輯**: 結合 `rules/global.txt` 與個股專屬規則，強制模型擔任「專業技術分析師」。
* **多模態對齊**: 利用 Gemini 1.5 對高解析度圖表 (400 DPI) 的理解能力，進行 K 線與趨勢分析。

## 2. 效能優化與併發
* **批次處理**: `batch_processor.py` 循序處理 100 檔股票，建議在 API 配額允許下改用 `asyncio.gather` 以加速。
* **模型選擇**: 
    * 每日例行掃描建議使用 **1.5 Flash** (平衡速度與成本)。
    * 深度追問或複雜技術面分析可手動切換至 **1.5 Pro**。

## 3. 圖像規格
* **解析度**: 系統強制執行 400 DPI 縮放 (`scale_factor=4.16`)，確保 Finviz 上的細微價格標記清晰可見。
* **偽裝策略**: 透過隨機 User-Agent 與延遲渲染，模仿人為瀏覽以維持擷取成功率。

## 4. 互動對話 (Context Management)
* **Streamlit Chat**: 每次追問都會將「原始分析報告」與「原始圖表」作為上下文傳遞，實現精準的追問功能。

## 5. 擴充建議
* **Context Caching**: 若個股規則庫 (`rules/tickers/`) 變得極大，應考慮啟用 Gemini 的 Context Caching 功能以節省 Token 成本。

## 6. Excel 格式規範 (Output Style)
* **字體**: 所有寫入 Excel 的內容必須使用 **Georgia** 字體。
* **對齊**: 儲存格內容必須設定為 **水平置中 (Center)** 與 **垂直置中 (Middle)**。
