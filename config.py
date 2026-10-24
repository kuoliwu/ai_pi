"""所有可調整的參數集中於此"""
import os

# ================= 路徑設定 =================
INPUT_DIR = "data"                                      # 使用者提供的輸入檔
STOCK_LIST_FILE = f"{INPUT_DIR}/stock_list.xlsx"        # 細產業對照表 (欄位: 股號, 細分類)
STOCK_SB_DIR = f"{INPUT_DIR}/stock_SB"                  # 自訂名單 txt 資料夾
OUTPUT_ROOT = "stock_data"                              # 每日輸出根目錄 (stock_data/YYYY-MM-DD/...)

# ================= 下載 / 防擋機制設定 =================
DOWNLOAD_CHUNK_SIZE = 50    # 每次 yf.download 打包幾檔股票 (yfinance 內部會多執行緒抓)
DOWNLOAD_WORKERS = 4        # 同時下載幾個批次 (太大容易被 Yahoo 限流 / 回傳空資料)
DOWNLOAD_RETRY = 2          # 失敗 / 最後一天不完整的股票，逐檔重試次數
DELAY_MIN = 0.2             # 每個批次下載後最少暫停 (秒)
DELAY_MAX = 0.6             # 每個批次下載後最多暫停 (秒)
# 可選: proxy 清單，批次會輪流使用 (例: "http://user:pass@1.2.3.4:8080", "socks5://127.0.0.1:9050")
# 留空 = 直連。None 代表其中一路直連，可與 proxy 混用，例如 [None, "http://..."]
PROXIES = []

# ================= 效能設定 =================
PLOT_WORKERS = max(1, (os.cpu_count() or 2) - 1)   # 平行繪圖的程序數，設 1 = 依序執行 (除錯用)
ITALIC_STOCK_ID = False     # 族群圖中股號是否用斜體 (mathtext 渲染，會讓大型族群圖慢約 1 倍)

# ================= 設定區塊 =================
MA_SETTINGS = [5, 10, 20, 60]       # 均價設定 (Price Moving Average)
MV_SETTINGS = [1, 5, 20]            # 均量設定 (Volume Moving Average)
TREND_SETTINGS = [5, 20, 60, 120]   # 趨勢比較天數 (看當日收盤價與 N 日前的收盤價比較)

DISTRIBUTION_DAYS = [1, 3, 5]       # 大盤溫度計的繪製天數設定
DISTRIBUTION_THRESHOLDS = [9.9, 15.0, 20.0]  # 對應上述天數的漲跌極端門檻%

PLOT_KLINE_CHARTS = True            # 是否為篩選出的股票繪製 K 線圖？

VOLUME_RANK_DAYS = [1, 3, 5, 10, 20]    # 量增/量縮排行榜的比較天數
TOP_N_STOCKS = 20                   # 排行榜要取前幾名
MIN_TURNOVER_100M = 1.0             # 排行榜的最低今日成交值門檻 (單位: 億元)

PRICE_RANK_DAYS = [1, 3, 5, 20]     # 價位排行榜的比較天數 

QUADRANT_DAYS = [1, 5, 20]          # 價量四象限儀表板的比較天數
QUADRANT_TOP_N = 30                 # 價量四象限儀表板每個象限要取前幾名 

# === 圖片排版設定 ===
MAX_COL_STOCK_NUMBER = 15  # 每行最多顯示幾檔股票

# --- 策略1 條件勾選區 ---
STRATEGY1_CONDITIONS = {
    "判斷1_今日量增": True,
    "判斷2_量能多頭": True,
    "判斷3_站上所有MA": True,
    "判斷4_MA多頭排列": False,
    "判斷5_成交值大於2億": True,
    "判斷6_今日收紅漲幅": True
}

# --- 策略2-均線 條件設定區 ---
STRATEGY2_SETTINGS = {
    "啟用策略": True,
    "均線陣列": [5, 10, 20, 60],
    "判斷1_所有均線趨勢上": [1, 1, 1, 1],
    "判斷2_成交值大於億": True,        
    "策略2_成交值門檻": 2.0,
    "判斷3_站上MAX均線": True,
    "判斷4_成交價接近MAX均內": True,
    "策略2_MAX均接近門檻%": 1.0
}

# --- 策略3-長紅爆量 條件設定區 ---
STRATEGY3_SETTINGS = {
    "啟用策略": True,
    "判斷1_實體長紅": True,
    "實體長紅門檻%": 4.0,            # 收盤價高於開盤價 > 4%
    "判斷2_今日爆量": True,
    "量增倍數門檻": 2.0,             # 今日量 > 昨日量 * 2倍
    "判斷3_幾乎收最高": True,
    "上影線容許%": 1.5,              # (最高價-收盤價)/收盤價 < 1.5%
    "判斷4_成交值門檻": True,
    "成交值(億)門檻": 1.0            # 成交值大於1億
}

# --- 策略4-均線糾結起漲 條件設定區 (新增：高勝率波段起漲點) ---
STRATEGY4_SETTINGS = {
    "啟用策略": True,
    "均線糾結門檻%": 2.5,            # 5MA, 10MA, 20MA 最大差幅 / 20MA < 2.5%
    "今日量增倍數_vs5MV": 1.5,       # 今日量 > 5日均量 * 1.5 倍 (溫和放量)
    "收盤站上均線": True,            # 收盤價 > max(5MA, 10MA, 20MA)
    "漲幅區間%": [1.5, 6.5],         # 漲幅介於 1.5% ~ 6.5% (剛表態不追高)
    "成交值(億)門檻": 1.5            # 成交值大於 1.5 億元
}
