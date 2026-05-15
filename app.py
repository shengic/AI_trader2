import streamlit as st
import os
import asyncio
import datetime
import pandas as pd
from batch_processor import process_from_excel, PERIOD_MAPPING, read_excel_safely
from core_analyzer import get_model, load_rules
import PIL.Image
import io
from db_manager import get_available_dates, get_reports_by_date, get_full_report

st.set_page_config(page_title="StockVision AI", layout="wide")

# 加入 CSS 穩定版面
st.markdown("""
    <style>
    .stApp { overflow-anchor: none; }
    div[data-testid="stVerticalBlock"] > div:has(div.stImage) { min-height: 400px; }
    div[data-testid="stHorizontalBlock"] { margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 StockVision AI: 股票自動化分析系統")

def get_report_data_direct(date_str, excel_path):
    db_reports = get_reports_by_date(date_str)
    active_tickers = []
    df_excel = read_excel_safely(excel_path, header=None)
    if df_excel is not None:
        try:
            for idx, row in df_excel.iterrows():
                if idx == 0: continue
                t = str(row.iloc[0]).strip().upper()
                if t and t != "NAN": active_tickers.append(t)
        except: pass
    data_structure = []
    for rep in db_reports:
        ticker = rep["ticker"]
        if ticker in active_tickers:
            data_structure.append({
                "ticker": ticker, "period": rep["period"],
                "label": f"{ticker} ({rep['period']})", "is_active": True
            })
    return pd.DataFrame(data_structure)

@st.dialog("圖表放大檢視", width="large")
def show_full_image(img_data, title):
    st.image(img_data, width="stretch", caption=title)

@st.dialog("📜 全域量價分析規則", width="large")
def show_global_rules(content):
    st.markdown(content)

# 側邊欄
with st.sidebar:
    st.header("系統設定")
    model_choice = st.selectbox("選擇模型", ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-3.1-flash-lite", "deep-research-preview-04-2026"])
    st.divider()
    st.header("批次處理")
    LOCAL_EXCEL_PATH = r"K:\AI_trader2\Stocks.xlsx"
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1: start_capture = st.button("僅執行截圖")
    with col_btn2: start_analysis = st.button("啟動完整分析")
    
    if (start_capture or start_analysis) and os.path.exists(LOCAL_EXCEL_PATH):
        mode_text = "截圖" if start_capture else "完整分析"
        
        with st.status(f"🚀 正在啟動{mode_text}...", expanded=True) as status:
            progress_bar = st.progress(0)
            log_container = st.container()
            
            def update_progress(current, total, ticker, status_type, msg):
                progress = current / total
                progress_bar.progress(progress)
                icon = "✅" if status_type == "success" else "⏳" if status_type == "running" else "❌"
                log_container.write(f"{icon} **{ticker}**: {msg}")
                if ticker == "SYSTEM":
                    status.update(label=f"⚙️ 系統操作: {msg}", state="running")
                else:
                    status.update(label=f"📊 正在處理 {ticker} ({current}/{total})...", state="running")

            results = asyncio.run(process_from_excel(
                LOCAL_EXCEL_PATH, 
                model_name=model_choice, 
                capture_only=start_capture,
                progress_callback=update_progress
            ))
            status.update(label=f"✨ {mode_text}已完成！即將重新整理...", state="complete", expanded=False)
            st.success(f"{mode_text}任務成功執行。")
            st.rerun()
    
    st.divider()
    if st.button("📜 查看全域分析規則", width="stretch"):
        global_rules_path = "rules/global.txt"
        if os.path.exists(global_rules_path):
            with open(global_rules_path, "r", encoding="utf-8") as f: content = f.read()
            show_global_rules(content)
        else: st.error("找不到全域規則檔案")

# 初始化 Session State
if "selected_ticker" not in st.session_state: st.session_state.selected_ticker = ""
if "selected_period" not in st.session_state: st.session_state.selected_period = ""
if "chat_history" not in st.session_state: st.session_state.chat_history = {}
if "nav_radio" not in st.session_state: st.session_state.nav_radio = "🔍 詳細分析"

# 動態顯示標題
header_text = "📊 分析結果瀏覽"
if st.session_state.get("selected_ticker"):
    header_text = f"📊 {st.session_state.selected_ticker} 分析結果瀏覽"

st.header(header_text)
available_dates = get_available_dates()

if not available_dates:
    st.info("目前資料庫尚無紀錄，請先點擊側邊欄按鈕啟動掃描。")
else:
    # 預設選中最新的日期 (index=0)
    selected_date = st.selectbox("選擇日期", available_dates, index=0)
    
    df_reports = get_report_data_direct(selected_date, LOCAL_EXCEL_PATH)
    
    if df_reports.empty:
        st.warning(f"⚠️ 該日期尚未存入任何與 Excel 匹配的分析報告。")
    else:
        # 當資料載入後，如果 session state 中沒有或不合法，則預設選擇第一筆
        if not st.session_state.selected_ticker or st.session_state.selected_ticker not in df_reports["ticker"].values:
            st.session_state.selected_ticker = df_reports["ticker"].iloc[0]
            st.session_state.selected_period = df_reports["period"].iloc[0]

        tabs = ["🔍 詳細分析", "📋 股票清單總覽"]
        # 使用 index 手動管理導覽，避免 key 衝突
        current_nav = st.session_state.get("nav_radio", "🔍 詳細分析")
        try:
            nav_index = tabs.index(current_nav)
        except ValueError:
            nav_index = 0
            
        active_tab = st.radio("導覽", tabs, index=nav_index, horizontal=True, label_visibility="collapsed")
        st.session_state.nav_radio = active_tab

        if active_tab == "📋 股票清單總覽":
            st.subheader("📋 分析清單總覽")
            col_sel1, col_sel2 = st.columns([3, 1])
            with col_sel1: st.info("💡 勾選特定股票後，可執行針對性分析。")
            
            df_for_edit = df_reports[["ticker", "period"]].copy()
            df_for_edit.insert(0, "選擇", False)
            df_for_edit.columns = ["選擇", "股票代號", "分析週期"]
            
            edited_df = st.data_editor(df_for_edit, hide_index=True, width="stretch", disabled=["股票代號", "分析週期"], key="stock_selector")
            selected_tickers = edited_df[edited_df["選擇"] == True]["股票代號"].tolist()
            
            with col_sel2:
                if st.button("🚀 執行選中項目的 AI 分析", width="stretch", type="primary"):
                    if not selected_tickers: st.warning("請先勾選！")
                    else:
                        status_box = st.empty()
                        progress_bar = st.progress(0)
                        def update_selective(current, total, ticker, status, msg):
                            progress_bar.progress(current/total)
                            status_box.info(f"正在分析: {current}/{total} ({ticker})")
                        
                        asyncio.run(process_from_excel(
                            LOCAL_EXCEL_PATH, model_name=model_choice, 
                            tickers_to_process=selected_tickers, 
                            progress_callback=update_selective
                        ))
                        st.rerun()

            st.divider()
            options = sorted(df_reports["label"].tolist())
            
            col_q1, col_q2 = st.columns([2, 1])
            with col_q1:
                jump_target = st.selectbox("快速跳轉至詳細報告", options, key="quick_select_target")
            with col_q2:
                if st.button("跳轉", width="stretch"):
                    if jump_target:
                        match = df_reports[df_reports["label"] == jump_target].iloc[0]
                        st.session_state.selected_ticker = match["ticker"]
                        st.session_state.selected_period = match["period"]
                        st.session_state.nav_radio = "🔍 詳細分析"
                        st.rerun()

        else: # 🔍 詳細分析
            control_container = st.container()
            with control_container:
                col_sel_main, col_rule = st.columns([1, 2])
                options = sorted(df_reports["label"].tolist())
                current_label = f"{st.session_state.selected_ticker} ({st.session_state.selected_period})"
                try: current_idx = options.index(current_label)
                except: current_idx = 0

                with col_sel_main:
                    def on_main_select():
                        label = st.session_state.main_select
                        match = df_reports[df_reports["label"] == label].iloc[0]
                        st.session_state.selected_ticker = match["ticker"]
                        st.session_state.selected_period = match["period"]
                    st.selectbox("選擇分析報告", options, index=current_idx, key="main_select", on_change=on_main_select)
                
                with col_rule:
                    selected_ticker = st.session_state.selected_ticker
                    local_rule = ""
                    df_rule_lookup = read_excel_safely(LOCAL_EXCEL_PATH, header=None)
                    if df_rule_lookup is not None:
                        try:
                            rule_match = df_rule_lookup[df_rule_lookup[0].astype(str).str.upper() == selected_ticker]
                            if not rule_match.empty and len(rule_match.columns) > 2:
                                val = rule_match.iloc[0, 2]
                                local_rule = str(val) if not pd.isna(val) else ""
                        except: pass
                    if local_rule: st.info(f"📌 **{selected_ticker} 本地觀察規則**：\n{local_rule}")
            
            st.divider()
            full_data = get_full_report(st.session_state.selected_ticker, st.session_state.selected_period, selected_date)
            
            if full_data:
                report_content = full_data["report_content"]
                image_bytes = full_data["image_data"]
                col_img, col_rep = st.columns([1, 2])
                with col_img:
                    if image_bytes:
                        if st.button("🔎 點擊放大圖表", width="stretch"):
                            show_full_image(image_bytes, f"{st.session_state.selected_ticker} ({st.session_state.selected_period})")
                        st.image(image_bytes, width="stretch", caption=f"{st.session_state.selected_ticker} ({st.session_state.selected_period})")
                with col_rep:
                    st.markdown(report_content)
                    st.divider()
                    st.subheader(f"💬 針對 {st.session_state.selected_ticker} 追問")
                    chat_id = f"{st.session_state.selected_ticker}_{st.session_state.selected_period.replace(' ', '_')}_{selected_date}"
                    if chat_id not in st.session_state.chat_history: st.session_state.chat_history[chat_id] = []
                    for message in st.session_state.chat_history[chat_id]:
                        with st.chat_message(message["role"]): st.markdown(message["content"])
                    if prompt := st.chat_input("輸入問題...", key=f"input_{chat_id}"):
                        with st.chat_message("user"): st.markdown(prompt)
                        st.session_state.chat_history[chat_id].append({"role": "user", "content": prompt})
                        with st.chat_message("assistant"):
                            model = get_model(model_choice)
                            img = PIL.Image.open(io.BytesIO(image_bytes))
                            response = model.generate_content([f"參考分析報告：\n{report_content}\n\n問：{prompt}", img])
                            st.markdown(response.text)
                            st.session_state.chat_history[chat_id].append({"role": "assistant", "content": response.text})
