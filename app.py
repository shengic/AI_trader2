import streamlit as st
import os
import asyncio
import datetime
import pandas as pd
import re
import PIL.Image
import io
from batch_processor import process_from_db, get_finviz_url
from core_analyzer import get_model, load_rules
from db_manager import (
    init_db, get_watchlist_data, add_to_watchlist, 
    update_watchlist_rule, delete_from_watchlist,
    get_full_report, save_report_to_db,
    get_global_rule, save_global_rule, get_ticker_history,
    update_watchlist_settings
)

st.set_page_config(page_title="StockVision AI | DEAL", layout="wide")

# 初始化資料庫
init_db()

# CSS 優化
st.markdown("""
    <style>
    .stApp { overflow-anchor: none; }
    .stDataFrame { border-radius: 10px; }
    .report-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #ff4b4b; }
    </style>
""", unsafe_allow_html=True)

# 輔助函式
def parse_stage_and_summary(report_content):
    if not report_content or "(等待 AI 分析中...)" in report_content:
        return "N/A", "尚未分析"
    
    stage_match = re.search(r"[【\[](第?\s*\d+\s*階段?\s*[-–—:：]\s*[^】\]]+)[】\]]", report_content)
    if not stage_match:
        stage_match = re.search(r"(第\s*\d+\s*階段\s*[-–—:：]\s*[^\n#]+)", report_content)
    
    stage = stage_match.group(1).strip() if stage_match else "未知"
    stage = re.sub(r".*量價階段判定[：:]\s*", "", stage)
    
    filler_prefixes = ["作為一名", "根據", "好的", "這是一份", "以下是", "我將", "感謝"]
    lines = [l.strip() for l in report_content.split('\n') if l.strip() and not l.startswith('#')]
    
    summary = "尚未分析"
    for line in lines:
        is_filler = any(line.startswith(p) for p in filler_prefixes)
        if not is_filler:
            summary = line[:100] + "..." if len(line) > 100 else line
            break
            
    return stage, summary

def get_stage_color(stage):
    if "突破" in stage or "主升" in stage: return "🟢"
    if "跌" in stage: return "🔴"
    if "頂" in stage or "背離" in stage: return "🟡"
    if "築底" in stage: return "🔵"
    return "⚪"

# 初始化導覽狀態
if "menu" not in st.session_state:
    st.session_state.menu = "📊 Portfolio Hub"

# 側邊欄導覽
with st.sidebar:
    st.title("🎯 StockVision AI")
    st.subheader("功能導覽")
    
    # 建立按鈕選單
    if st.button("📊 Portfolio Hub", use_container_width=True, type="primary" if st.session_state.menu == "📊 Portfolio Hub" else "secondary"):
        st.session_state.menu = "📊 Portfolio Hub"
        st.rerun()
        
    if st.button("📜 Global Rules", use_container_width=True, type="primary" if st.session_state.menu == "📜 Global Rules" else "secondary"):
        st.session_state.menu = "📜 Global Rules"
        st.rerun()
    
    ticker_rules_dir = "rules/tickers"
    if not os.path.exists(ticker_rules_dir):
        os.makedirs(ticker_rules_dir)
    
    ticker_rule_files = [f.replace(".txt", "") for f in os.listdir(ticker_rules_dir) if f.endswith(".txt")]
    if ticker_rule_files:
        st.divider()
        st.subheader("🔍 個股特定規則")
        for ticker in ticker_rule_files:
            if st.button(f"📄 {ticker} Rule", use_container_width=True, type="primary" if st.session_state.menu == f"rule_{ticker}" else "secondary"):
                st.session_state.menu = f"rule_{ticker}"
                st.rerun()

    st.divider()
    st.subheader("⚙️ 系統設定")
    model_choice = st.selectbox("選擇 AI 模型", ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"])
    st.divider()

# --- 彈出視窗實作 ---
@st.dialog("📄 完整分析報告", width="large")
def show_report_modal(content):
    st.markdown(content)

@st.dialog("🖼️ K 線圖高清檢視", width="large")
def show_image_modal(image_data):
    st.image(image_data, use_container_width=True)

@st.dialog("🚀 啟動 AI 批次分析")
def run_analysis_dialog(tickers):
    if not tickers:
        st.warning("⚠️ 請先在表格中勾選至少一檔股票！")
        if st.button("關閉"): st.rerun()
        return
        
    st.write(f"準備分析以下 {len(tickers)} 檔股票：")
    st.code(", ".join(tickers))
    p_choice = st.selectbox("若個股未設定週期，則預設使用：", ["1 year", "6 month", "3 month", "2 year"])
    if st.button("確認並啟動分析", type="primary", use_container_width=True):
        st.session_state.analysis_running = True
        st.session_state.target_tickers = tickers
        st.session_state.target_period = p_choice
        st.rerun()

# --- 頁面路由控制 ---
if st.session_state.menu == "📊 Portfolio Hub":
    st.title("📈 StockVision AI: Portfolio Hub")
    
    raw_data = get_watchlist_data()
    selected_ticker_from_table = None

    # 1. ADD: 批量匯入區
    with st.expander("➕ 批量管理清單 (Add/Manage Stocks)", expanded=False):
        current_tickers = "\n".join([item['ticker'] for item in raw_data])
        input_text = st.text_area("編輯監控代號 (每行一個)", value=current_tickers, height=200)
        if st.button("同步清單", type="primary"):
            new_tickers = list(set(re.findall(r'[A-Z0-9]+', input_text.upper())))
            old_tickers = [item['ticker'] for item in raw_data]
            to_add = [t for t in new_tickers if t not in old_tickers]
            to_delete = [t for t in old_tickers if t not in new_tickers]
            if to_add: add_to_watchlist(to_add)
            if to_delete: delete_from_watchlist(to_delete)
            if to_add or to_delete:
                st.success("清單同步完成！")
                st.rerun()

    # 2. LIST & SELECTION
    st.subheader("📋 監控清單 (Watchlist)")
    df_display = []
    for item in raw_data:
        stage, summary = parse_stage_and_summary(item['report_content'])
        color = get_stage_color(stage)
        display_summary = summary if summary != "尚未分析" else "⚪ 尚未進行 AI 分析"
        if summary != "尚未分析":
            display_summary = f"{color} {stage}: {summary}"

        df_display.append({
            "Ticker": item['ticker'],
            "Local Rule": item['local_rule'] if item['local_rule'] and item['local_rule'].strip() else "N/A",
            "Period": item['default_period'] or "N/A",
            "Summary": display_summary,
            "Last Analyzed": item['analysis_date'].strftime("%Y-%m-%d") if item['analysis_date'] else "N/A"
        })
    df = pd.DataFrame(df_display)

    if df.empty:
        st.info("目前清單為空。")
    else:
        # 使用 st.dataframe 實作原生多選
        table_height = min(400, (len(df) + 1) * 35 + 3)
        df_for_table = df.set_index("Ticker")
        
        selection = st.dataframe(
            df_for_table,
            hide_index=False,
            width="stretch",
            height=table_height,
            column_config={
                "Local Rule": st.column_config.TextColumn("本地規則", width=200),
                "Period": st.column_config.TextColumn("預設週期", width="small"),
                "Summary": st.column_config.TextColumn("📈 分析摘要 (點擊選取)", width=450),
                "Last Analyzed": st.column_config.TextColumn("上次分析", width="small")
            },
            key="watchlist_table_v11",
            on_select="rerun",
            selection_mode="multi-row"
        )

        selected_tickers = []
        if "watchlist_table_v11" in st.session_state and st.session_state.watchlist_table_v11.get("selection"):
            selected_rows = st.session_state.watchlist_table_v11["selection"]["rows"]
            selected_tickers = [df.iloc[idx]["Ticker"] for idx in selected_rows]
            if selected_rows:
                selected_ticker_from_table = df.iloc[selected_rows[-1]]["Ticker"]

        # --- 啟動批次分析按鈕 ---
        st.write("")
        if st.button(f"🚀 啟動 AI 批次分析 ({len(selected_tickers)} 筆)", use_container_width=True, type="primary"):
            run_analysis_dialog(selected_tickers)

        # 處理背景分析邏輯
        if st.session_state.get("analysis_running"):
            with st.status("🚀 正在執行批次分析...") as status:
                def update_progress(current, total, ticker, status_type, msg):
                    status.update(label=f"📊 {ticker} ({current}/{total}): {msg}")
                asyncio.run(process_from_db(model_name=model_choice, target_period=st.session_state.target_period, progress_callback=update_progress, tickers=st.session_state.target_tickers))
            st.session_state.analysis_running = False
            st.success("分析完成！")
            st.rerun()

    # 3. 詳情查看
    st.divider()
    
    ticker_list = ["請選擇"] + df["Ticker"].tolist() if not df.empty else ["請選擇"]
    default_idx = 0
    if selected_ticker_from_table and selected_ticker_from_table in ticker_list:
        default_idx = ticker_list.index(selected_ticker_from_table)
        
    selected_ticker = st.selectbox("🔍 選擇股票以查看詳情與管理", ticker_list, index=default_idx)
    
    if selected_ticker != "請選擇":
        item_data = next(item for item in raw_data if item['ticker'] == selected_ticker)
        
        with st.expander(f"🛠️ 管理 {selected_ticker}", expanded=False):
            c1, c2 = st.columns([3, 1])
            with c1:
                new_local_rule = st.text_input("修改本地規則", value=item_data['local_rule'] or "", key=f"edit_rule_{selected_ticker}")
                p_opts = ["1 year", "6 month", "3 month", "2 year", "5 year", "max"]
                curr_p = item_data['default_period'] or "1 year"
                if curr_p not in p_opts: curr_p = "1 year"
                new_period = st.selectbox("分析週期", p_opts, index=p_opts.index(curr_p), key=f"edit_period_{selected_ticker}")
                
                if st.button(f"💾 儲存 {selected_ticker} 設定", use_container_width=True):
                    update_watchlist_settings(selected_ticker, new_local_rule, new_period)
                    st.success(f"{selected_ticker} 設定已更新！")
                    st.rerun()
            with c2:
                st.write("危險區域")
                if st.button(f"🗑️ 刪除 {selected_ticker}", type="primary", use_container_width=True):
                    delete_from_watchlist([selected_ticker])
                    st.warning(f"已移除 {selected_ticker}")
                    st.rerun()

        st.divider()

        history = get_ticker_history(selected_ticker)
        if not history:
            st.warning(f"尚未有 {selected_ticker} 的分析紀錄。")
        else:
            history_options = [f"{item['analysis_date'].strftime('%Y-%m-%d')} ({item['period']})" for item in history]
            selected_history_str = st.selectbox("📅 選擇歷史報告日期", history_options)
            
            selected_idx = history_options.index(selected_history_str)
            selected_record = history[selected_idx]
            target_date_str = selected_record['analysis_date'].strftime("%Y%m%d")
            target_period = selected_record['period']
            
            full_report = get_full_report(selected_ticker, target_period, target_date_str)
            
            if full_report:
                # [stock] [time period] [yyyy-mm-dd] 的分析報告:
                st.subheader(f"📊 {selected_ticker} ({target_period}) {selected_record['analysis_date'].strftime('%Y-%m-%d')} 的分析報告:")
                
                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    if st.button("🖼️ 放大查看 K 線圖", use_container_width=True):
                        show_image_modal(full_report['image_data'])
                with col_btn2:
                    if st.button("📄 全螢幕閱讀報告", use_container_width=True):
                        show_report_modal(full_report['report_content'])

                st.divider()
                c1, c2 = st.columns([1, 1])
                with c1: 
                    st.image(full_report['image_data'], use_container_width=True)
                    # 顯示擷取來源 URL
                    capture_url = get_finviz_url(selected_ticker, target_period)
                    st.caption(f"🔗 擷取來源: {capture_url}")
                with c2: 
                    st.markdown(full_report['report_content'])
            else:
                st.error("無法載入報告內容。")

elif st.session_state.menu == "📜 Global Rules":
    st.title("📜 全域量價分析規則管理")
    st.markdown("在這裡編輯 AI 分析股票時遵循的核心邏輯。修改後將立即套用於下一次分析。")
    current_global_rule = get_global_rule()
    if not current_global_rule or "DB_RULE_STAMP" in current_global_rule:
        source_files = ["Dee's generalized stock rule.md", "rules/global.txt"]
        for fpath in source_files:
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    current_global_rule = f.read()
                save_global_rule(current_global_rule)
                break
    new_rule = st.text_area("編輯全域規則 (Markdown 格式)", value=current_global_rule, height=600)
    if st.button("💾 儲存全域規則", type="primary", use_container_width=True):
        save_global_rule(new_rule)
        st.success("✅ 全域規則已成功儲存至資料庫！下一次分析將採用新規則。")
        st.balloons()
