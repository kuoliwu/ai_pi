"""台股價量分析主程式：python code_artifact.py"""
import os
import time
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

import pandas as pd

from config import *
from stock_ai.data_fetch import get_all_taiwan_tickers, get_industry_map, download_missing_stocks, get_market_index_changes
from stock_ai.indicators import calculate_stock_reports
from stock_ai.charts_market import (plot_price_change_distribution, generate_market_extremes_industry_image,
                                    generate_outperform_market_industry_image, generate_industry_capital_flow_image)
from stock_ai.charts_strategy import generate_pick_list_image, generate_industry_group_image, plot_kline_charts
from stock_ai.strategies import process_strategy2_logic, process_strategy3_logic, process_strategy4_logic
from stock_ai.charts_volume import (generate_volume_surge_ranking, generate_volume_shrink_ranking, generate_volume_matrix_image,
                                    generate_price_volume_quadrant_dashboard, generate_price_volume_quadrant_industry_dashboard)
from stock_ai.charts_price import generate_price_rankings, generate_price_matrix_dashboard
from stock_ai.report_custom import generate_custom_list_bias_excel


# ================= 組合任務 (有前後依賴的步驟包成一個任務，才能丟進平行程序) =================

def run_strategy1(df_full, out_dir, source_dir, today_str):
    pick_df = generate_pick_list_image(df_full, out_dir, today_str, STRATEGY1_CONDITIONS, TREND_SETTINGS)
    if pick_df is not None and not pick_df.empty:
        generate_industry_group_image(pick_df, out_dir, today_str, strategy_name="策略1")
        if PLOT_KLINE_CHARTS: plot_kline_charts(pick_df, source_dir, out_dir, MA_SETTINGS, strategy_name="策略1")

def run_volume_rankings(tickers, ticker_map, industry_map, source_dir, out_dir, today_str):
    surge = generate_volume_surge_ranking(tickers, ticker_map, industry_map, source_dir, out_dir, today_str, VOLUME_RANK_DAYS, TOP_N_STOCKS, MIN_TURNOVER_100M)
    shrink = generate_volume_shrink_ranking(tickers, ticker_map, industry_map, source_dir, out_dir, today_str, VOLUME_RANK_DAYS, TOP_N_STOCKS, MIN_TURNOVER_100M)
    generate_volume_matrix_image(surge, shrink, out_dir, today_str, TOP_N_STOCKS)

def run_price_rankings(df_full, out_dir, today_str):
    res = generate_price_rankings(df_full, out_dir, today_str, PRICE_RANK_DAYS, TOP_N_STOCKS)
    generate_price_matrix_dashboard(res, out_dir, today_str, TOP_N_STOCKS)

def export_main_excel(df_full, output_file):
    dist_cols = [f"漲幅_{d}日%" for d in DISTRIBUTION_DAYS]
    trend_cols = [f"{days}日趨勢" for days in TREND_SETTINGS]
    base_cols = ["股號", "股名", "細產業", "Close", "High", "Low", "Open", "漲幅%"]
    vol_cols = ["成交值(億)", "今日量(張)", "昨日量(張)", "量增", "量能多頭"]
    ma_cols = [f"{w}MA" for w in MA_SETTINGS]
    mv_cols = [f"{w}MV(張)" for w in MV_SETTINGS]
    other_cols = ["站上所有MA", "多頭排列"] + trend_cols + ["資料日期"]
    df_full[base_cols + dist_cols + vol_cols + ma_cols + mv_cols + other_cols].to_excel(output_file, index=False)

def _timed(name, func, *args, **kwargs):
    t = time.time()
    func(*args, **kwargs)
    return name, time.time() - t

def run_tasks(tasks):
    """平行執行互不相依的報表任務 (PLOT_WORKERS=1 時依序執行)"""
    if PLOT_WORKERS <= 1:
        for name, func, args, kwargs in tasks:
            print(f"⏱️ [{name}] 耗時: {_timed(name, func, *args, **kwargs)[1]:.2f} 秒\n")
        return
    with ProcessPoolExecutor(max_workers=PLOT_WORKERS) as ex:
        futures = {ex.submit(_timed, name, func, *args, **kwargs): name for name, func, args, kwargs in tasks}
        for fut in as_completed(futures):
            try:
                name, sec = fut.result()
                print(f"⏱️ [{name}] 耗時: {sec:.2f} 秒")
            except Exception as e:
                print(f"❌ [{futures[fut]}] 失敗: {e}")


# ================= 主程式執行 =================
if __name__ == "__main__":
    t_start_total = time.time()
    today_str = datetime.now().strftime("%Y-%m-%d")

    save_dir = os.path.join(OUTPUT_ROOT, today_str)
    source_dir = os.path.join(save_dir, "source")
    dirs = {name: os.path.join(save_dir, name) for name in ["策略1", "策略2-均線", "策略3-長紅爆量", "策略4-均線糾結突破", "量能", "大盤", "價位"]}
    for d in [source_dir, STOCK_SB_DIR, *dirs.values()]:
        os.makedirs(d, exist_ok=True)

    print(f"\n{'='*50}\n🚀 台股價量分析程式開始執行 ({today_str})\n{'='*50}")

    t_step = time.time()
    ticker_name_map = get_all_taiwan_tickers()
    industry_map = get_industry_map(STOCK_LIST_FILE)
    all_tickers = sorted(ticker_name_map.keys())
    print(f"⏱️ [步驟1:取得清單] 耗時: {time.time() - t_step:.2f} 秒\n")

    if not all_tickers:
        print("❌ 未取得股票清單，請檢查網路。")
        exit()

    all_params = MA_SETTINGS + MV_SETTINGS + TREND_SETTINGS + DISTRIBUTION_DAYS + VOLUME_RANK_DAYS + PRICE_RANK_DAYS + QUADRANT_DAYS + STRATEGY2_SETTINGS["均線陣列"]
    max_p = max(all_params)

    t_step = time.time()
    download_missing_stocks(all_tickers, source_dir, max_p)
    print(f"⏱️ [步驟2:下載資料] 耗時: {time.time() - t_step:.2f} 秒\n")

    t_step = time.time()
    final_results = calculate_stock_reports(all_tickers, ticker_name_map, industry_map, source_dir, MA_SETTINGS, MV_SETTINGS, TREND_SETTINGS, DISTRIBUTION_DAYS, QUADRANT_DAYS)
    print(f"⏱️ [步驟3:計算報表] 耗時: {time.time() - t_step:.2f} 秒\n")

    if not final_results:
        print("❌ 無任何有效股票資料可供計算。")
        exit()

    df_full = pd.DataFrame(final_results)
    df_full['股號'] = df_full['股號'].astype(str)
    df_full = df_full.sort_values(by="股號").reset_index(drop=True)
    df_report = df_full  # 主報表 Excel 保留全部股票

    # 最新資料日不是最後交易日 (停牌 / 資料延遲) 的股票，不納入策略與排行，避免用舊資料當今日
    latest_date = df_full['資料日期'].max()
    stale = df_full[df_full['資料日期'] != latest_date]
    if not stale.empty:
        print(f"⚠️ {len(stale)} 檔最新資料非 {latest_date}，不納入策略與排行：{', '.join(stale['股號'] + stale['股名'])}\n")
    df_full = df_full[df_full['資料日期'] == latest_date].reset_index(drop=True)
    fresh_tickers = df_full['完整股號'].tolist()

    t_step = time.time()
    market_changes = get_market_index_changes(DISTRIBUTION_DAYS, max_p)
    print(f"⏱️ [步驟4:取得大盤基準] 耗時: {time.time() - t_step:.2f} 秒\n")

    # 以下各報表互不相依，平行產出
    t_step = time.time()
    m_dir, v_dir = dirs["大盤"], dirs["量能"]
    output_file = os.path.join(save_dir, f"TW_Stock_Report_{today_str}.xlsx")
    tasks = [
        ("大盤溫度圖", plot_price_change_distribution, (df_full, m_dir, today_str, DISTRIBUTION_DAYS, DISTRIBUTION_THRESHOLDS, market_changes), {}),
        ("極端漲跌族群分佈圖", generate_market_extremes_industry_image, (df_full, m_dir, today_str, DISTRIBUTION_DAYS, DISTRIBUTION_THRESHOLDS), {}),
        # 強於大盤圖最耗時，按天數拆成多個任務
        *[(f"強於大盤族群分佈圖-{d}日", generate_outperform_market_industry_image, (df_full, m_dir, today_str, [d], market_changes), {}) for d in DISTRIBUTION_DAYS],
        ("細產業資金流向圖", generate_industry_capital_flow_image, (df_full, m_dir, today_str), {"top_n": 20}),
        ("策略1產出", run_strategy1, (df_full, dirs["策略1"], source_dir, today_str), {}),
        ("策略2均線產出", process_strategy2_logic, (df_full, dirs["策略2-均線"], source_dir, today_str), {}),
        ("策略3長紅爆量產出", process_strategy3_logic, (df_full, dirs["策略3-長紅爆量"], source_dir, today_str, MA_SETTINGS), {}),
        ("策略4均線糾結產出", process_strategy4_logic, (df_full, dirs["策略4-均線糾結突破"], source_dir, today_str, MA_SETTINGS), {}),
        ("輸出Excel", export_main_excel, (df_report, output_file), {}),
        ("量增量縮排行", run_volume_rankings, (fresh_tickers, ticker_name_map, industry_map, source_dir, v_dir, today_str), {}),
        ("價量四象限儀表板", generate_price_volume_quadrant_dashboard, (df_full, v_dir, today_str), {"quadrant_days": QUADRANT_DAYS, "top_n": QUADRANT_TOP_N}),
        ("價量四象限產業儀表板", generate_price_volume_quadrant_industry_dashboard, (df_full, v_dir, today_str), {"quadrant_days": QUADRANT_DAYS, "top_n": QUADRANT_TOP_N}),
        ("價位排行與儀表板", run_price_rankings, (df_full, dirs["價位"], today_str), {}),
        ("自訂名單乖離率Excel", generate_custom_list_bias_excel, (STOCK_SB_DIR, source_dir, save_dir, today_str, ticker_name_map, industry_map), {}),
    ]
    run_tasks(tasks)
    print(f"⏱️ [步驟5:平行產出所有圖表/報表 ({PLOT_WORKERS} 程序)] 耗時: {time.time() - t_step:.2f} 秒\n")

    mins, secs = divmod(time.time() - t_start_total, 60)
    print(f"{'='*50}")
    print(f"✅ 全部執行完成！")
    print(f"📊 成功產出主報表 Excel：{len(df_report)} 檔資料")
    print(f"🌟 總耗時：{int(mins)}分{int(secs)}秒")
    print(f"📂 總結報告：{save_dir} (含 自訂名單乖離率Excel)")
    for name, d in dirs.items():
        print(f"📂 {name}：{d}")
    print(f"{'='*50}")
