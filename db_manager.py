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
    
    # 建立資料表
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
    
    conn.commit()
    cursor.close()
    conn.close()
    print("資料庫初始化成功")

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
