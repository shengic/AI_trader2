import mysql.connector
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """取得資料庫連線"""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

def init_db():
    """初始化資料表"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 建立股票報告表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_reports (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ticker VARCHAR(20) NOT NULL,
        period VARCHAR(50) NOT NULL,
        analysis_date DATE NOT NULL,
        report_content LONGTEXT,
        image_data LONGBLOB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY unique_report (ticker, period, analysis_date)
    )
    """)

    # 建立監控清單表 (DEAL 模式核心)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS watchlist (
        ticker VARCHAR(20) PRIMARY KEY,
        local_rule TEXT,
        period VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 檢查是否需要新增 period 欄位 (針對現有資料庫)
    try:
        cursor.execute("ALTER TABLE watchlist ADD COLUMN period VARCHAR(50) AFTER local_rule")
    except:
        pass # 欄位已存在

    # 建立系統設定表 (存儲全域規則)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        setting_key VARCHAR(50) PRIMARY KEY,
        setting_value LONGTEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("資料庫初始化成功")

def get_global_rule():
    """從資料庫取得全域規則"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT setting_value FROM settings WHERE setting_key = 'global_rule'")
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else None

def save_global_rule(rule_text):
    """將全域規則存入資料庫"""
    conn = get_connection()
    cursor = conn.cursor()
    sql = """
    INSERT INTO settings (setting_key, setting_value) 
    VALUES ('global_rule', %s)
    ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
    """
    try:
        cursor.execute(sql, (rule_text,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def get_watchlist_data():
    """
    取得 DEAL 模式所需的完整數據清單。
    包含：代號、本地規則、最新分析日期、最新判定階段、最新報告摘要。
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 使用子查詢抓取每檔股票最新的一筆報告
    sql = """
    SELECT 
        w.ticker, 
        w.local_rule, 
        w.period as default_period,
        w.created_at,
        r.analysis_date,
        r.period as last_report_period,
        r.report_content
    FROM watchlist w
    LEFT JOIN (
        SELECT ticker, period, analysis_date, report_content
        FROM stock_reports
        WHERE (ticker, analysis_date) IN (
            SELECT ticker, MAX(analysis_date)
            FROM stock_reports
            GROUP BY ticker
        )
    ) r ON w.ticker = r.ticker
    ORDER BY w.created_at DESC
    """
    
    cursor.execute(sql)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

def add_to_watchlist(tickers):
    """批量新增股票到監控清單"""
    if not tickers:
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    sql = "INSERT IGNORE INTO watchlist (ticker) VALUES (%s)"
    
    try:
        cursor.executemany(sql, [(t,) for t in tickers])
        conn.commit()
    except Exception as e:
        print(f"批量新增失敗: {e}")
    finally:
        cursor.close()
        conn.close()

def update_watchlist_settings(ticker, local_rule, period):
    """更新特定股票的本地規則與預設週期"""
    conn = get_connection()
    cursor = conn.cursor()
    sql = "UPDATE watchlist SET local_rule = %s, period = %s WHERE ticker = %s"
    try:
        cursor.execute(sql, (local_rule, period, ticker))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def update_watchlist_rule(ticker, local_rule):
    """更新特定股票的本地規則"""
    conn = get_connection()
    cursor = conn.cursor()
    sql = "UPDATE watchlist SET local_rule = %s WHERE ticker = %s"
    try:
        cursor.execute(sql, (local_rule, ticker))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def delete_from_watchlist(tickers):
    """批量從監控清單刪除"""
    if not tickers:
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    # 這裡使用格式化字串處理 IN 語法，並小心處理 SQL 注入
    format_strings = ','.join(['%s'] * len(tickers))
    sql = f"DELETE FROM watchlist WHERE ticker IN ({format_strings})"
    
    try:
        cursor.execute(sql, tuple(tickers))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def save_report_to_db(ticker, period, report_content, image_path):
    """將分析結果存入資料庫"""
    if not os.path.exists(image_path):
        print(f"找不到圖片: {image_path}, 跳過資料庫儲存")
        return

    # 讀取圖片為二進位數據
    with open(image_path, "rb") as f:
        image_blob = f.read()

    today = datetime.date.today()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = """
    INSERT INTO stock_reports (ticker, period, analysis_date, report_content, image_data)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE 
    report_content = VALUES(report_content),
    image_data = VALUES(image_data)
    """
    
    try:
        cursor.execute(sql, (ticker, period, today, report_content, image_blob))
        conn.commit()
    except Exception as e:
        print(f"存入資料庫時發生錯誤: {e}")
    finally:
        cursor.close()
        conn.close()

def get_available_dates():
    """取得所有有紀錄的日期"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT analysis_date FROM stock_reports ORDER BY analysis_date DESC")
    dates = [row[0].strftime("%Y%m%d") for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return dates

def get_reports_by_date(date_str):
    """取得特定日期的所有報告清單 (不含圖片數據，加速讀取)"""
    # 轉換日期格式
    date_obj = datetime.datetime.strptime(date_str, "%Y%m%d").date()
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT ticker, period, report_content 
        FROM stock_reports 
        WHERE analysis_date = %s
    """, (date_obj,))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

def get_ticker_history(ticker):
    """取得特定股票的所有歷史分析記錄"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT period, analysis_date 
        FROM stock_reports 
        WHERE ticker = %s 
        ORDER BY analysis_date DESC
    """, (ticker,))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

def get_full_report(ticker, period, date_str):
    """取得完整報告與圖片數據"""
    date_obj = datetime.datetime.strptime(date_str, "%Y%m%d").date()
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT report_content, image_data 
        FROM stock_reports 
        WHERE ticker = %s AND period = %s AND analysis_date = %s
    """, (ticker, period, date_obj))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result

if __name__ == "__main__":
    # 測試初始化
    try:
        init_db()
    except Exception as e:
        print(f"請確保已手動建立資料庫並於 .env 設定正確資訊。錯誤: {e}")
