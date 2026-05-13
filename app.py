import streamlit as st
import os
import asyncio
import datetime
import pandas as pd
from batch_processor import process_from_excel, process_single_stock, PERIOD_MAPPING
from core_analyzer import get_model, load_rules
import PIL.Image

st.set_page_config(page_title="StockVision AI", layout="wide")

# 加入 CSS 穩定版面
st.markdown("""
    <style>
    .stApp {
        overflow-anchor: none;
    }
    /* 預留圖片區域高度以防止抖動 */
    div[data-testid="stVerticalBlock"] > div:has(div.stImage) {
        min-height: 400px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📈 StockVision AI: 股票自動化分析系統")

# 快取檔案列表與 Excel 讀取
@st.cache_data(ttl=60)
def get_report_data(report_dir, excel_path):
    if not os.path.exists(report_dir):
        return pd.DataFrame(), []
    
    report_files = sorted([f for f in os.listdir(report_dir) if f.endswith(".md")])
    active_configs = []
    
    if os.path.exists(excel_path):
        try:
            df_excel = pd.read_excel(excel_path, header=None)
            for idx, row in df_excel.iterrows():
                if idx == 0: continue
                t = str(row.iloc[0]).strip().upper()
                p = str(row.iloc[1]).strip().lower() if not pd.isna(row.iloc[1]) else "1 year"
                if t and t != "NAN":
                    active_configs.append({"ticker": t, "period": p})
        except:
            pass

    data_structure = []
    for config in active_configs:
        ticker = config["ticker"]
        period = config["period"]
        filename = f"{ticker}_{period.replace(' ', '_')}.md"
        if filename in report_files:
            data_structure.append({
                "ticker": ticker, "period": period, "filename": filename, "label": f"{ticker} ({period})"
            })
    
    return pd.DataFrame(data_structure), active_configs

# 定義彈窗函數
@st.dialog("圖表放大檢視", width="large")
def show_full_image(img_path, title):
    st.image(img_path, width="stretch", caption=title)

# 側邊欄：設定與上傳
with st.sidebar:
    st.header("系統設定")
    api_key = st.text_input("Gemini API Key", type="password", value=os.getenv("GEMINI_API_KEY", ""))
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key
    
    model_choice = st.selectbox("選擇模型", ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"])
    
    st.divider()
    st.header("批次處理")
    
    LOCAL_EXCEL_PATH = r"K:\AI_trader2\Stocks.xlsx"
    
    if os.path.exists(LOCAL_EXCEL_PATH):
        st.success(f"已偵測到本地名單: Stocks.xlsx")
    else:
        st.error(f"找不到檔案: {LOCAL_EXCEL_PATH}")
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        start_capture = st.button("僅執行截圖")
    with col_btn2:
        start_analysis = st.button("啟動完整分析")
    
    if (start_capture or start_analysis) and os.path.exists(LOCAL_EXCEL_PATH):
        mode_text = "截圖" if start_capture else "完整分析"
        with st.status(f"正在執行{mode_text}...", expanded=True) as status:
            results = asyncio.run(process_from_excel(
                LOCAL_EXCEL_PATH, 
                model_name=model_choice, 
                capture_only=start_capture
            ))
            status.update(label=f"{mode_text}完成！", state="complete", expanded=False)
        st.cache_data.clear() # 清除快取以載入新檔案
        st.rerun()

# 初始化 Session State
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = ""
if "selected_period" not in st.session_state:
    st.session_state.selected_period = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}

# 主要介面
st.header("📊 分析結果瀏覽")

report_dates = sorted([d for d in os.listdir("reports") if os.path.isdir(f"reports/{d}")], reverse=True) if os.path.exists("reports") else []

if not report_dates:
    st.info("目前尚無分析報告，請先點擊側邊欄按鈕啟動掃描。")
else:
    selected_date = st.selectbox("選擇日期", report_dates, index=0)
    report_dir = f"reports/{selected_date}"
    capture_dir = f"captures/{selected_date}"
    
    # 讀取數據 (使用快取)
    df_reports, active_configs = get_report_data(report_dir, LOCAL_EXCEL_PATH)
    
    if df_reports.empty:
        st.warning(f"⚠️ 日期 {selected_date} 尚無與 Excel 設定相符的報告。")
    else:
        if not st.session_state.selected_ticker or st.session_state.selected_ticker not in df_reports["ticker"].values:
            st.session_state.selected_ticker = df_reports["ticker"].iloc[0]
            st.session_state.selected_period = df_reports["period"].iloc[0]

        tab1, tab2 = st.tabs(["🔍 詳細分析", "📋 股票清單總覽"])
        
        with tab1:
            # 穩定下拉選單容器
            control_container = st.container()
            with control_container:
                col_sel_main, col_rule = st.columns([1, 2])
                
                options = sorted(df_reports["label"].tolist())
                current_label = f"{st.session_state.selected_ticker} ({st.session_state.selected_period})"
                try:
                    current_idx = options.index(current_label)
                except ValueError:
                    current_idx = 0

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
                    try:
                        df_rule_lookup = pd.read_excel(LOCAL_EXCEL_PATH, header=None)
                        rule_match = df_rule_lookup[df_rule_lookup[0].astype(str).str.upper() == selected_ticker]
                        if not rule_match.empty and len(rule_match.columns) > 2:
                            val = rule_match.iloc[0, 2]
                            local_rule = str(val) if not pd.isna(val) else ""
                    except:
                        pass
                    if local_rule:
                        st.info(f"📌 **{selected_ticker} 本地觀察規則**：\n{local_rule}")
            
            st.divider()

            # 顯示圖片與內容
            selected_ticker = st.session_state.selected_ticker
            selected_period = st.session_state.selected_period
            match_rows = df_reports[(df_reports["ticker"] == selected_ticker) & (df_reports["period"] == selected_period)]
            
            if not match_rows.empty:
                selected_filename = match_rows.iloc[0]["filename"]
                ticker_period_key = selected_filename.replace(".md", "")
                
                col_img, col_rep = st.columns([1, 2])
                with col_img:
                    img_path = f"{capture_dir}/{ticker_period_key}.png"
                    if os.path.exists(img_path):
                        if st.button("🔎 點擊放大圖表", width="stretch"):
                            show_full_image(img_path, f"{selected_ticker} ({selected_period})")
                        st.image(img_path, width="stretch", caption=f"{selected_ticker} ({selected_period})")
                    else:
                        st.warning("找不到圖片")
                
                with col_rep:
                    report_path = f"{report_dir}/{selected_filename}"
                    with open(report_path, "r", encoding="utf-8") as f:
                        st.markdown(f.read())
                    
                    # 追問區塊
                    st.divider()
                    st.subheader(f"💬 針對 {selected_ticker} 追問")
                    chat_id = f"{selected_ticker}_{selected_period.replace(' ', '_')}"
                    if chat_id not in st.session_state.chat_history:
                        st.session_state.chat_history[chat_id] = []

                    for message in st.session_state.chat_history[chat_id]:
                        with st.chat_message(message["role"]):
                            st.markdown(message["content"])

                    if prompt := st.chat_input("輸入問題...", key=f"input_{chat_id}"):
                        with st.chat_message("user"):
                            st.markdown(prompt)
                        st.session_state.chat_history[chat_id].append({"role": "user", "content": prompt})
                        with st.chat_message("assistant"):
                            model = get_model(model_choice)
                            img = PIL.Image.open(img_path)
                            # 讀取報告內容作為上下文
                            with open(report_path, "r", encoding="utf-8") as rf:
                                ctx = rf.read()
                            response = model.generate_content([f"分析報告：\n{ctx}\n\n問：{prompt}", img])
                            st.markdown(response.text)
                            st.session_state.chat_history[chat_id].append({"role": "assistant", "content": response.text})

        with tab2:
            st.subheader("📋 分析清單總覽")
            options = sorted(df_reports["label"].tolist())
            def on_quick_select():
                label = st.session_state.quick_select
                match = df_reports[df_reports["label"] == label].iloc[0]
                st.session_state.selected_ticker = match["ticker"]
                st.session_state.selected_period = match["period"]
            
            col_q1, _ = st.columns([1, 2])
            with col_q1:
                st.selectbox("快速跳轉", options, key="quick_select", on_change=on_quick_select)
            
            st.divider()
            display_df = df_reports[["ticker", "period"]].sort_values("ticker")
            display_df.columns = ["股票代號", "分析週期"]
            st.dataframe(display_df, width="stretch", hide_index=True)
