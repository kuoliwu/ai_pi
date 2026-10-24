"""策略 2 ~ 4 的篩選與輸出"""
import os
import time
import random

import pandas as pd
import matplotlib.pyplot as plt

from config import *
from stock_ai.charts_strategy import generate_pick_list_image, generate_industry_group_image, plot_kline_charts


def process_strategy2_logic(df_full, output_dir, source_dir, today_str):
    """執行策略2的篩選、清單圖、產業圖、K線圖"""
    if not STRATEGY2_SETTINGS["啟用策略"]: return
    print(f"\n{'='*30}\n🔍 開始執行 【策略2-均線】 篩選...\n{'='*30}")
    s2_df = df_full.copy()
    active_labels = []
    set_s2 = STRATEGY2_SETTINGS

    if set_s2["判斷1_所有均線趨勢上"]:
        s2_df = s2_df[s2_df["S2_Cond1_均線趨勢上"] == True]
        trend_str = str(set_s2["判斷1_所有均線趨勢上"]).replace(" ", "")
        active_labels.append(f"趨勢{trend_str}📈")
    if set_s2["判斷2_成交值大於億"]:
        s2_df = s2_df[s2_df["S2_Cond2_成交值門檻"] == True]
        active_labels.append(f"成交值>{set_s2['策略2_成交值門檻']}億💰")
    if set_s2["判斷3_站上MAX均線"]:
        s2_df = s2_df[s2_df["S2_Cond3_站上MAX均"] == True]
        active_labels.append("站上MAX均🎯")
    if set_s2["判斷4_成交價接近MAX均內"]:
        s2_df = s2_df[s2_df["S2_Cond4_接近MAX均"] == True]
        active_labels.append(f"接近MAX均<{set_s2['策略2_MAX均接近門檻%']}%🧱")

    num_picks = len(s2_df)
    if num_picks == 0: print("⚠️ 策略2今日無符合條件之股票。"); return
    print(f"✅ 策略2篩選完成！共 {num_picks} 檔符合條件，正在產出相關圖表...")

    try:
        plot_cols = ["股號", "股名", "細產業", "Close", "漲幅%", "成交值(億)", "今日量(張)"]
        plot_df = s2_df[plot_cols].copy()
        fig, ax = plt.subplots(figsize=(12, 1.5 + num_picks * 0.4)); ax.axis('tight'); ax.axis('off')
        conditions_str = " + ".join(active_labels) if active_labels else "無限制"
        ma_str = ",".join(map(str, set_s2["均線陣列"]))
        title_text = f"【策略2-均線精選清單】 {today_str}\n均線：[{ma_str}]\n觸發條件：{conditions_str}"; ax.set_title(title_text, fontweight="bold", fontsize=14, pad=15)
        table = ax.table(cellText=plot_df.values, colLabels=plot_df.columns, loc='center', cellLoc='center'); table.auto_set_font_size(False); table.set_fontsize(11); table.scale(1.2, 1.8)
        for j in range(len(plot_df.columns)): table[(0, j)].set_facecolor('#fcf8e3'); table[(0, j)].set_text_props(weight='bold')
        img_path = os.path.join(output_dir, f"Strategy2_Picks_{today_str}.png")
        plt.savefig(img_path, bbox_inches="tight", dpi=300, facecolor='white')
        plt.close('all')
        print(f"🖼️ 策略2清單圖片儲存至: {img_path}")
    except Exception as e: print(f"❌ 生成策略2清單圖失敗: {e}")

    generate_industry_group_image(s2_df, output_dir, today_str, strategy_name="策略2")
    if PLOT_KLINE_CHARTS: plot_kline_charts(s2_df, source_dir, output_dir, set_s2["均線陣列"], strategy_name="策略2")

def process_strategy3_logic(df_full, output_dir, source_dir, today_str, ma_windows):
    """執行策略3(長紅爆量)的篩選、清單圖、產業圖、K線圖"""
    if not STRATEGY3_SETTINGS.get("啟用策略", False): return
    print(f"\n{'='*30}\n🔍 開始執行 【策略3-長紅爆量】 篩選...\n{'='*30}")
    s3_df = df_full.copy()
    active_labels = []
    set_s3 = STRATEGY3_SETTINGS

    if set_s3["判斷1_實體長紅"]:
        cond_red = (s3_df["Close"] > s3_df["Open"]) & (((s3_df["Close"] - s3_df["Open"]) / s3_df["Open"]) * 100 > set_s3["實體長紅門檻%"])
        s3_df = s3_df[cond_red]
        active_labels.append(f"實體>{set_s3['實體長紅門檻%']}%🔥")
    
    if set_s3["判斷2_今日爆量"]:
        cond_vol = s3_df["今日量(張)"] > (s3_df["昨日量(張)"] * set_s3["量增倍數門檻"])
        s3_df = s3_df[cond_vol]
        active_labels.append(f"量增>{set_s3['量增倍數門檻']}倍🚀")

    if set_s3["判斷3_幾乎收最高"]:
        cond_high = ((s3_df["High"] - s3_df["Close"]) / s3_df["Close"]) * 100 < set_s3["上影線容許%"]
        s3_df = s3_df[cond_high]
        active_labels.append(f"上影線<{set_s3['上影線容許%']}%🎯")

    if set_s3["判斷4_成交值門檻"]:
        s3_df = s3_df[s3_df["成交值(億)"] >= set_s3["成交值(億)門檻"]]
        active_labels.append(f"成交值>{set_s3['成交值(億)門檻']}億💰")

    num_picks = len(s3_df)
    if num_picks == 0: 
        print("⚠️ 策略3今日無符合條件之股票。")
        return
    
    print(f"✅ 策略3篩選完成！共 {num_picks} 檔符合條件，正在產出相關圖表...")

    try:
        plot_cols = ["股號", "股名", "細產業", "Open", "Close", "High", "漲幅%", "今日量(張)", "昨日量(張)", "成交值(億)"]
        plot_df = s3_df[plot_cols].copy()
        fig, ax = plt.subplots(figsize=(13, 1.5 + num_picks * 0.4)); ax.axis('tight'); ax.axis('off')
        conditions_str = " + ".join(active_labels) if active_labels else "無限制"
        title_text = f"【策略3-長紅爆量精選清單】 {today_str}\n觸發條件：{conditions_str}"
        ax.set_title(title_text, fontweight="bold", fontsize=14, pad=15)
        table = ax.table(cellText=plot_df.values, colLabels=plot_df.columns, loc='center', cellLoc='center')
        table.auto_set_font_size(False); table.set_fontsize(11); table.scale(1.2, 1.8)
        
        for j in range(len(plot_df.columns)): 
            table[(0, j)].set_facecolor('#f8d7da') 
            table[(0, j)].set_text_props(weight='bold')
            
        img_path = os.path.join(output_dir, f"Strategy3_Picks_{today_str}.png")
        plt.savefig(img_path, bbox_inches="tight", dpi=300, facecolor='white')
        plt.close('all')
        print(f"🖼️ 策略3清單圖片儲存至: {img_path}")
    except Exception as e: 
        print(f"❌ 生成策略3清單圖失敗: {e}")

    generate_industry_group_image(s3_df, output_dir, today_str, strategy_name="策略3")
    if PLOT_KLINE_CHARTS: 
        plot_kline_charts(s3_df, source_dir, output_dir, ma_windows, strategy_name="策略3")

def process_strategy4_logic(df_full, output_dir, source_dir, today_str, ma_windows):
    """執行策略4(均線糾結起漲)的篩選、清單圖、產業圖、K線圖"""
    if not STRATEGY4_SETTINGS.get("啟用策略", False): return
    print(f"\n{'='*30}\n🔍 開始執行 【策略4-均線糾結起漲】 篩選...\n{'='*30}")
    s4_df = df_full.copy()
    set_s4 = STRATEGY4_SETTINGS
    active_labels = []

    # 確保所需均線欄位齊全
    req_cols = ["5MA", "10MA", "20MA", "5MV(張)", "今日量(張)", "Close", "漲幅%", "成交值(億)"]
    if not all(col in s4_df.columns for col in req_cols):
        print("⚠️ 缺少均線或量能欄位，略過策略4。")
        return

    # 1. 均線糾結判斷：(max(5,10,20MA) - min(5,10,20MA)) / 20MA < 門檻
    max_ma = s4_df[["5MA", "10MA", "20MA"]].max(axis=1)
    min_ma = s4_df[["5MA", "10MA", "20MA"]].min(axis=1)
    ma_spread_pct = ((max_ma - min_ma) / s4_df["20MA"]) * 100
    cond_squeeze = ma_spread_pct <= set_s4["均線糾結門檻%"]
    s4_df = s4_df[cond_squeeze]
    active_labels.append(f"均線糾結<{set_s4['均線糾結門檻%']}%🌀")

    # 2. 收盤價站上糾結均線高點
    if set_s4["收盤站上均線"]:
        cond_above = s4_df["Close"] > max_ma.loc[s4_df.index]
        s4_df = s4_df[cond_above]
        active_labels.append("突破糾結MA🎯")

    # 3. 量能點火 (今日量 > 5MV * 倍數)
    cond_vol = s4_df["今日量(張)"] > (s4_df["5MV(張)"] * set_s4["今日量增倍數_vs5MV"])
    s4_df = s4_df[cond_vol]
    active_labels.append(f"量>5MV_{set_s4['今日量增倍數_vs5MV']}倍🚀")

    # 4. 漲幅區間 (剛起漲，不追高)
    low_pct, high_pct = set_s4["漲幅區間%"]
    cond_pct = (s4_df["漲幅%"] >= low_pct) & (s4_df["漲幅%"] <= high_pct)
    s4_df = s4_df[cond_pct]
    active_labels.append(f"漲幅{low_pct}%~{high_pct}%📈")

    # 5. 成交值門檻
    s4_df = s4_df[s4_df["成交值(億)"] >= set_s4["成交值(億)門檻"]]
    active_labels.append(f"成交值>{set_s4['成交值(億)門檻']}億💰")

    num_picks = len(s4_df)
    if num_picks == 0:
        print("⚠️ 策略4今日無符合條件之股票。")
        return

    print(f"✅ 策略4篩選完成！共 {num_picks} 檔符合條件，正在產出相關圖表...")

    try:
        plot_cols = ["股號", "股名", "細產業", "Close", "5MA", "10MA", "20MA", "漲幅%", "今日量(張)", "5MV(張)", "成交值(億)"]
        plot_df = s4_df[plot_cols].copy()
        fig, ax = plt.subplots(figsize=(14, 1.5 + num_picks * 0.4)); ax.axis('tight'); ax.axis('off')
        conditions_str = " + ".join(active_labels) if active_labels else "無限制"
        title_text = f"【策略4-均線糾結起漲精選清單】 {today_str}\n觸發條件：{conditions_str}"
        ax.set_title(title_text, fontweight="bold", fontsize=14, pad=15)
        table = ax.table(cellText=plot_df.values, colLabels=plot_df.columns, loc='center', cellLoc='center')
        table.auto_set_font_size(False); table.set_fontsize(11); table.scale(1.2, 1.8)
        
        # 策略4 清單使用粉紫色/柔和靛藍色標題背景
        for j in range(len(plot_df.columns)): 
            table[(0, j)].set_facecolor('#e8eaf6') 
            table[(0, j)].set_text_props(weight='bold')
            
        img_path = os.path.join(output_dir, f"Strategy4_Picks_{today_str}.png")
        plt.savefig(img_path, bbox_inches="tight", dpi=300, facecolor='white')
        plt.close('all')
        print(f"🖼️ 策略4清單圖片儲存至: {img_path}")
    except Exception as e: 
        print(f"❌ 生成策略4清單圖失敗: {e}")

    generate_industry_group_image(s4_df, output_dir, today_str, strategy_name="策略4")
    if PLOT_KLINE_CHARTS: 
        plot_kline_charts(s4_df, source_dir, output_dir, ma_windows, strategy_name="策略4")
