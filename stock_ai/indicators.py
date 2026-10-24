"""計算每檔股票的技術指標與策略判斷條件"""
import os
import time
import random

import pandas as pd
import matplotlib.pyplot as plt

from config import *
from stock_ai.data_fetch import read_price_csv


def calculate_stock_reports(tickers, ticker_map, industry_map, source_dir, ma_windows, mv_windows, trend_windows, dist_days, quadrant_days):
    """計算並產出最終報表字典"""
    results = []
    total = len(tickers)
    s2_ma = STRATEGY2_SETTINGS["均線陣列"]
    all_all_days = ma_windows + mv_windows + trend_windows + dist_days + PRICE_RANK_DAYS + quadrant_days + s2_ma
    max_param = max(all_all_days) + 1 if all_all_days else 120
    print(f"\n開始整合技術指標與量能資料...")
    
    for i, ticker in enumerate(tickers):
        file_path = os.path.join(source_dir, f"{ticker}.csv")
        if os.path.exists(file_path):
            try:
                df = read_price_csv(file_path)
                df.index = pd.to_datetime(df.index, errors='coerce')
                df = df[df.index.notnull()].sort_index()

                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)

                required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                for col in required_cols:
                    if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df = df.dropna(subset=required_cols)
                if df.empty or len(df) < 2: continue

                c = df['Close']; h = df['High']; l = df['Low']; o = df['Open']; v = df['Volume']

                latest_p = float(c.iloc[-1]); prev_p = float(c.iloc[-2])
                change_pct = ((latest_p - prev_p) / prev_p) * 100
                raw_vol = float(v.iloc[-1]) 
                today_vol_lots = round(raw_vol / 1000, 2); yesterday_vol_lots = round(float(v.iloc[-2]) / 1000, 2)
                turnover_100m = round((latest_p * raw_vol) / 100000000, 2)

                if len(c) < max_param:
                    needed = max_param - len(c)
                    temp_c = pd.Series([c.iloc[0]] * needed + c.tolist())
                    temp_v = pd.Series([v.iloc[0] / 1000] * needed + (v / 1000).tolist())
                else:
                    temp_c = c.copy(); temp_v = v.copy() / 1000  

                stock_data = {
                    "完整股號": ticker, "股號": ticker.split('.')[0],
                    "股名": ticker_map.get(ticker, "未知"), "細產業": industry_map.get(ticker, ""),
                    "Close": round(latest_p, 2), "High": round(float(h.iloc[-1]), 2),
                    "Low": round(float(l.iloc[-1]), 2), "Open": round(float(o.iloc[-1]), 2),
                    "漲幅%": round(change_pct, 2), "成交值(億)": turnover_100m,
                    "今日量(張)": today_vol_lots, "昨日量(張)": yesterday_vol_lots
                }
                
                # 基礎均線與量能計算 (策略1用)
                ma_vals_s1 = []
                for w in ma_windows:
                    val = round(float(temp_c.rolling(w).mean().iloc[-1]), 2)
                    stock_data[f"{w}MA"] = val; ma_vals_s1.append(val)
                
                mv_vals_s1 = []
                for w in mv_windows:
                    val = round(float(temp_v.rolling(w).mean().iloc[-1]), 2)
                    stock_data[f"{w}MV(張)"] = val; mv_vals_s1.append(val)

                # 策略2 特定均線計算
                s2_ma_windows = STRATEGY2_SETTINGS["均線陣列"]
                s2_ma_today = []; s2_ma_yesterday = []
                for w in s2_ma_windows:
                    ma_serie = temp_c.rolling(w).mean()
                    val_today = round(float(ma_serie.iloc[-1]), 2); val_yesterday = round(float(ma_serie.iloc[-2]), 2)
                    s2_ma_today.append(val_today); s2_ma_yesterday.append(val_yesterday)
                    if f"{w}MA" not in stock_data: stock_data[f"{w}MA"] = val_today

                # ================= 策略1 條件判斷 =================
                cond3_above_ma_s1 = all(latest_p > val for val in ma_vals_s1) if ma_vals_s1 else False
                cond4_ma_bullish_s1 = all(ma_vals_s1[j] > ma_vals_s1[j+1] for j in range(len(ma_vals_s1)-1)) if len(ma_vals_s1) >= 2 else False
                cond2_mv_bullish_s1 = all(mv_vals_s1[j] > mv_vals_s1[j+1] for j in range(len(mv_vals_s1)-1)) if len(mv_vals_s1) >= 2 else False

                stock_data["Cond1_今日量增"] = today_vol_lots > yesterday_vol_lots
                stock_data["Cond2_量能多頭"] = cond2_mv_bullish_s1
                stock_data["Cond3_站上所有MA"] = cond3_above_ma_s1
                stock_data["Cond4_MA多頭排列"] = cond4_ma_bullish_s1
                stock_data["Cond5_成交值大於2億"] = turnover_100m > 2.0
                stock_data["Cond6_今日收紅漲幅"] = change_pct > 0

                # ================= 策略2 條件判斷 =================
                max_ma_s2 = max(s2_ma_today) if s2_ma_today else 0
                
                cond1_s2_trend_match = True
                req_trends = STRATEGY2_SETTINGS["判斷1_所有均線趨勢上"]
                if s2_ma_today and len(s2_ma_today) == len(req_trends):
                    for j in range(len(s2_ma_today)):
                        t = s2_ma_today[j]
                        y = s2_ma_yesterday[j]
                        req = req_trends[j]
                        if req == 1 and t <= y:          cond1_s2_trend_match = False; break
                        elif req == -1 and t >= y:       cond1_s2_trend_match = False; break
                        elif req == 0 and t != y:        cond1_s2_trend_match = False; break
                else: cond1_s2_trend_match = False

                cond2_s2_turnover = turnover_100m > STRATEGY2_SETTINGS["策略2_成交值門檻"]
                cond3_s2_above_max = latest_p > max_ma_s2
                prox_threshold = STRATEGY2_SETTINGS["策略2_MAX均接近門檻%"] / 100
                prox_val = abs(latest_p - max_ma_s2) / latest_p if latest_p > 0 else float('inf')
                cond4_s2_prox = prox_val < prox_threshold

                stock_data["S2_Cond1_均線趨勢上"] = cond1_s2_trend_match
                stock_data["S2_Cond2_成交值門檻"] = cond2_s2_turnover
                stock_data["S2_Cond3_站上MAX均"] = cond3_s2_above_max
                stock_data["S2_Cond4_接近MAX均"] = cond4_s2_prox

                # ================= 其他指標計算 =================
                unique_days = sorted(list(set(dist_days + PRICE_RANK_DAYS + quadrant_days)))
                for d in unique_days:
                    if len(temp_c) > d:
                        past_price = float(temp_c.iloc[-(d + 1)])
                        d_pct = ((latest_p - past_price) / past_price) * 100
                        stock_data[f"漲幅_{d}日%"] = round(d_pct, 2)
                    else: stock_data[f"漲幅_{d}日%"] = 0.0
                    
                for d in quadrant_days:
                    if d > 1 and f"{d}MV(張)" not in stock_data:
                        stock_data[f"{d}MV(張)"] = round(float(temp_v.rolling(d).mean().iloc[-1]), 2)

                for days in trend_windows:
                    past_price = float(temp_c.iloc[-(days + 1)])
                    col_name = f"{days}日趨勢"
                    if latest_p > past_price: stock_data[col_name] = "⬆️"
                    elif latest_p < past_price: stock_data[col_name] = "⬇️"
                    else: stock_data[col_name] = "平"

                stock_data["量增"] = "🚀" if stock_data["Cond1_今日量增"] else ""
                stock_data["站上所有MA"] = "🎯是" if cond3_above_ma_s1 else ""
                stock_data["多頭排列"] = "🔥強勢" if (cond4_ma_bullish_s1 and cond3_above_ma_s1) else ("✅排列" if cond4_ma_bullish_s1 else "")
                stock_data["量能多頭"] = "☀️" if cond2_mv_bullish_s1 else ""
                stock_data["資料日期"] = df.index[-1].strftime('%Y-%m-%d')
                
                results.append(stock_data)
                
                if (i+1) % 100 == 0 or (i+1) == total: print(f"已處理 {i+1}/{total} 檔...", end="\r")
            except Exception: continue
    print("\n所有指標計算完成！")
    return results
