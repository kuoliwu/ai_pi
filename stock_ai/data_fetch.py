"""取得股票清單、產業對照、下載歷史報價、大盤指數"""
import os
import time
import random

import pandas as pd
import matplotlib.pyplot as plt

from config import *
import requests
import yfinance as yf
from datetime import datetime, timedelta


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

# ================= 輔助函數 =================

def get_all_taiwan_tickers():
    """取得台股上市櫃代號與名稱字典"""
    ticker_map = {}
    print("正在取得台股上市櫃清單與股票名稱...")
    try:
        res = requests.get("https://openapi.twse.com.tw/v1/exchange_report/STOCK_DAY_ALL", headers=HEADERS, timeout=15)
        if res.status_code == 200:
            for item in res.json():
                if len(item.get('Code', '')) == 4:
                    ticker_map[f"{item['Code']}.TW"] = item['Name']
    except Exception as e: print(f"上市清單取得失敗: {e}")
        
    try:
        res = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes", headers=HEADERS, timeout=15)
        if res.status_code == 200:
            for item in res.json():
                code = item.get('SecuritiesCompanyCode')
                name = item.get('CompanyName')
                if code and len(code) == 4:
                    ticker_map[f"{code}.TWO"] = name
    except Exception as e: print(f"上櫃清單取得失敗: {e}")
    return ticker_map

def get_industry_map(file_path="stock_list.xlsx"):
    """取得台股上市櫃『細分類』對應表"""
    ind_map = {}
    print(f"正在從 {file_path} 讀取細產業資料...")
    try:
        if os.path.exists(file_path):
            df = pd.read_excel(file_path, dtype={'股號': str})
        elif os.path.exists("stock_list.csv"):
            df = pd.read_csv("stock_list.csv", dtype={'股號': str})
        else:
            print(f"⚠️ 找不到 {file_path} 或 stock_list.csv，請確認檔案與程式在同一資料夾內。將以空白取代。")
            return ind_map
            
        if '股號' in df.columns and '細分類' in df.columns:
            for _, row in df.iterrows():
                code = str(row['股號']).strip()
                detail_ind = str(row['細分類']).strip()
                if detail_ind and detail_ind != 'nan' and detail_ind != 'None':
                    ind_map[f"{code}.TW"] = detail_ind
                    ind_map[f"{code}.TWO"] = detail_ind
        print(f"✅ 成功載入 {len(ind_map)//2} 筆細產業資料！")
    except Exception as e: print(f"❌ 讀取細產業資料失敗: {e}")
    return ind_map

_price_cache = {}
_calendar_cache = {}
CALENDAR_FILE = "^TWII.csv"   # 存在 source 資料夾內，作為交易日曆

def _load_trading_days(source_dir):
    """以大盤指數 ^TWII 有資料的日期作為交易日曆 (找不到檔案則回傳 None)"""
    if source_dir not in _calendar_cache:
        path = os.path.join(source_dir, CALENDAR_FILE)
        days = None
        if os.path.exists(path):
            idx = pd.to_datetime(pd.read_csv(path, index_col=0).index, errors='coerce')
            days = set(idx.dropna().normalize())
        _calendar_cache[source_dir] = days
    return _calendar_cache[source_dir]

def _drop_closed_days(df, trading_days):
    """移除休市日的假資料 (Yahoo 會在休市日補一筆 量=0、價=前收 的資料)"""
    dates = pd.to_datetime(df.index, errors='coerce').normalize()
    vol = pd.to_numeric(df['Volume'], errors='coerce') if 'Volume' in df.columns else pd.Series(0, index=df.index)
    fake = dates.notna() & ~dates.isin(trading_days) & (vol.fillna(0).values == 0)
    return df[~fake]

def read_price_csv(file_path):
    """讀取單檔報價 CSV，並剔除休市日 (同一次執行中只讀一次硬碟，之後回傳記憶體副本)"""
    if file_path not in _price_cache:
        df = pd.read_csv(file_path, index_col=0)
        trading_days = _load_trading_days(os.path.dirname(file_path))
        if trading_days: df = _drop_closed_days(df, trading_days)
        _price_cache[file_path] = df
    return _price_cache[file_path].copy()

def download_trading_calendar(source_dir, start_date, end_date):
    """下載 ^TWII 存成交易日曆，供 read_price_csv 剔除休市日"""
    try:
        df = yf.download("^TWII", start=start_date, end=end_date, progress=False)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
            df.to_csv(os.path.join(source_dir, CALENDAR_FILE))
            print(f"📅 交易日曆更新完成，最後交易日: {df.index[-1].strftime('%Y-%m-%d')}")
            return
    except Exception as e: print(f"⚠️ 交易日曆下載失敗: {e}")
    print("⚠️ 無交易日曆，將無法自動剔除休市日資料")

def _make_session(proxy):
    """建立 yfinance 使用的連線 (可指定 proxy)"""
    if not proxy: return None
    from curl_cffi import requests as cffi_requests
    return cffi_requests.Session(impersonate="chrome", proxies={"http": proxy, "https": proxy})

def _needs_download(file_path):
    """檔案不存在、或最後一天有缺值，就需要重新下載"""
    if not os.path.exists(file_path): return True
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        return len(lines) > 1 and "NaN" in lines[-1]
    except Exception: return True

def _download_chunk(chunk, source_dir, start_date, end_date, proxy):
    """一次下載一批股票並各自存成 CSV，回傳 (失敗清單, 最後一天不完整清單)"""
    failed, incomplete = [], []
    try:
        data = yf.download(chunk, start=start_date, end=end_date, progress=False, threads=True,
                           group_by="ticker", session=_make_session(proxy))
    except Exception:
        return list(chunk), incomplete
    for ticker in chunk:
        try:
            df = data[ticker] if isinstance(data.columns, pd.MultiIndex) else data
            df = df.dropna(how="all")
        except KeyError:
            failed.append(ticker); continue
        if df.empty:
            failed.append(ticker); continue
        if df.iloc[-1].isna().any(): incomplete.append(ticker)
        df.to_csv(os.path.join(source_dir, f"{ticker}.csv"))
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
    return failed, incomplete

def download_missing_stocks(tickers, source_dir, max_period):
    """下載歷史報價檔案 (批次 + 多執行緒 + 可選 proxy 輪替，失敗者逐檔重試)"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    needed_days = max(180, int(max_period / 20 * 30 * 1.5))
    end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=needed_days)).strftime("%Y-%m-%d")
    print(f"檢查下載進度... (強制抓取範圍: {start_date} 到 {end_date})")
    download_trading_calendar(source_dir, start_date, end_date)

    todo = [t for t in tickers if _needs_download(os.path.join(source_dir, f"{t}.csv"))]
    print(f"需下載 {len(todo)} / {len(tickers)} 檔 (每批 {DOWNLOAD_CHUNK_SIZE} 檔, {DOWNLOAD_WORKERS} 路並行, proxy 數: {len(PROXIES)})")
    proxies = PROXIES or [None]
    chunks = [todo[i:i + DOWNLOAD_CHUNK_SIZE] for i in range(0, len(todo), DOWNLOAD_CHUNK_SIZE)]

    failed, incomplete = [], []
    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as ex:
        futures = [ex.submit(_download_chunk, c, source_dir, start_date, end_date, proxies[i % len(proxies)]) for i, c in enumerate(chunks)]
        for done, fut in enumerate(as_completed(futures), 1):
            f, inc = fut.result(); failed += f; incomplete += inc
            print(f"批次進度: {done}/{len(chunks)}", end="\r")

    # 批次失敗或資料不完整者，逐檔重試 (換下一個 proxy)
    retry = sorted(set(failed + incomplete))
    if retry: print(f"\n🔁 {len(retry)} 檔需逐檔重試...")
    incomplete, failed = [], []
    for i, ticker in enumerate(retry):
        for attempt in range(DOWNLOAD_RETRY):
            f, inc = _download_chunk([ticker], source_dir, start_date, end_date, proxies[(i + attempt + 1) % len(proxies)])
            if not f and not inc: break
            time.sleep(random.uniform(1.5, 2.5))
        else:
            (incomplete if inc else failed).append(ticker)

    print("\n" + "="*50)
    if failed:
        print(f"⚠️ {len(failed)} 檔完全抓不到資料 (可能已下市 / 被限流，可調低 DOWNLOAD_WORKERS 或設定 PROXIES)：")
        print(", ".join(failed))
    if incomplete:
        print(f"⚠️ 注意：發現 {len(incomplete)} 檔股票最新一日資料不齊全：")
        print(", ".join(incomplete))
    else: print("✅ 所有檢查的股票最新一日資料皆完整無缺漏。")

def get_market_index_changes(dist_days, max_period):
    """取得大盤(^TWII)的 N 日漲跌幅"""
    print(f"\n📈 正在取得大盤(^TWII)資料以計算基準漲跌幅...")
    market_changes = {}
    needed_days = max(30, int(max_period * 1.5))
    end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=needed_days)).strftime("%Y-%m-%d")
    
    try:
        twii_df = yf.download("^TWII", start=start_date, end=end_date, progress=False)
        if not twii_df.empty:
            if isinstance(twii_df.columns, pd.MultiIndex):
                twii_df.columns = twii_df.columns.droplevel(1)
            twii_c = pd.to_numeric(twii_df['Close'], errors='coerce').dropna()
            
            if len(twii_c) > 0:
                latest_twii = float(twii_c.iloc[-1])
                for d in dist_days:
                    if len(twii_c) > d:
                        past_twii = float(twii_c.iloc[-(d + 1)])
                        market_changes[d] = round(((latest_twii - past_twii) / past_twii) * 100, 2)
                    else:
                        market_changes[d] = 0.0
                print(f"✅ 大盤基準漲跌幅: {market_changes}")
            else:
                print("⚠️ 大盤資料為空。")
        else:
            print("⚠️ 大盤資料為空。")
    except Exception as e:
        print(f"❌ 取得大盤指數失敗: {e}")
        
    return market_changes
