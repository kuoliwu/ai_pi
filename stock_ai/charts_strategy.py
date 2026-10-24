"""選股清單圖、族群分佈圖、K 線圖 (策略共用)"""
import os
import time
import random

import pandas as pd
import matplotlib.pyplot as plt

from config import *
from stock_ai.data_fetch import read_price_csv
from stock_ai import fmt_stock
from stock_ai.charts_market import get_optimal_col_ratios
import mplfinance as mpf


def generate_pick_list_image(df, output_dir, today_str, strategy_dict, trend_windows):
    """【策略1】過濾策略條件，輸出圖片"""
    print(f"\n🔍 開始進行策略1條件篩選 ({today_str})...")
    pick_df = df.copy()
    active_labels = []
    if strategy_dict.get("判斷1_今日量增"): pick_df = pick_df[pick_df["Cond1_今日量增"] == True]; active_labels.append("量增🚀")
    if strategy_dict.get("判斷2_量能多頭"): pick_df = pick_df[pick_df["Cond2_量能多頭"] == True]; active_labels.append("量能多頭☀️")
    if strategy_dict.get("判斷3_站上所有MA"): pick_df = pick_df[pick_df["Cond3_站上所有MA"] == True]; active_labels.append("站上所有MA🎯")
    if strategy_dict.get("判斷4_MA多頭排列"): pick_df = pick_df[pick_df["Cond4_MA多頭排列"] == True]; active_labels.append("MA多頭🔥")
    if strategy_dict.get("判斷5_成交值大於2億"): pick_df = pick_df[pick_df["Cond5_成交值大於2億"] == True]; active_labels.append("成交值>2億💰")
    if strategy_dict.get("判斷6_今日收紅漲幅"): pick_df = pick_df[pick_df["Cond6_今日收紅漲幅"] == True]; active_labels.append("收紅📈")

    num_picks = len(pick_df)
    if num_picks == 0: print("⚠️ 策略1今日無符合條件之股票。"); return pick_df 

    print(f"✅ 策略1篩選完成！共 {num_picks} 檔符合條件，正在繪製精選清單圖片...")
    trend_cols = [f"{days}日趨勢" for days in trend_windows]
    plot_cols = ["股號", "股名", "細產業", "Close", "漲幅%", "成交值(億)", "今日量(張)"] + trend_cols
    plot_df = pick_df[plot_cols].copy()

    try:
        fig, ax = plt.subplots(figsize=(12.5, 1.5 + num_picks * 0.4)); ax.axis('tight'); ax.axis('off')
        conditions_str = " + ".join(active_labels) if active_labels else "無限制"
        title_text = f"【策略1-強勢價量精選清單】 {today_str}\n觸發條件：{conditions_str}"; ax.set_title(title_text, fontweight="bold", fontsize=14, pad=15)
        table = ax.table(cellText=plot_df.values, colLabels=plot_df.columns, loc='center', cellLoc='center'); table.auto_set_font_size(False); table.set_fontsize(11); table.scale(1.2, 1.8)
        for j in range(len(plot_df.columns)): table[(0, j)].set_facecolor('#d9edf7'); table[(0, j)].set_text_props(weight='bold')
        img_path = os.path.join(output_dir, f"Strategy1_Picks_{today_str}.png")
        plt.savefig(img_path, bbox_inches="tight", dpi=300, facecolor='white')
        plt.close('all')
        print(f"🖼️ 策略1清單圖片儲存至: {img_path}")
    except Exception as e: print(f"❌ 生成策略1清單圖片失敗。錯誤訊息: {e}")
    return pick_df

def generate_industry_group_image(pick_df, output_dir, today_str, strategy_name="策略1"):
    """將策略選出的股票依據『細產業』進行分組並繪製成表格圖"""
    if pick_df.empty: return
    print(f"\n🎨 開始繪製 {strategy_name} 精選細產業分類圖...")
    
    temp_df = pick_df.copy(); temp_df['細產業'] = temp_df['細產業'].replace('', '未分類').fillna('未分類')
    
    group_sizes = temp_df.groupby('細產業').size().reset_index(name='count')
    group_sizes = group_sizes.sort_values(by=['count', '細產業'], ascending=[False, True])
    
    cell_text = []
    max_stocks_in_row = 0
    
    for _, r in group_sizes.iterrows():
        ind = r['細產業']; cnt = r['count']
        group = temp_df[temp_df['細產業'] == ind]
        items = [fmt_stock(sid, sname) for sid, sname in zip(group['股號'], group['股名'])]
        chunks = [items[i:i+MAX_COL_STOCK_NUMBER] for i in range(0, len(items), MAX_COL_STOCK_NUMBER)]
        for idx, chunk in enumerate(chunks):
            max_stocks_in_row = max(max_stocks_in_row, len(chunk))
            chunk_str = '  '.join(chunk)
            if idx == 0: cell_text.append([ind, str(cnt), chunk_str])
            else: cell_text.append(["", "", chunk_str])
            
    try:
        fig_width, col0_ratio, col1_ratio, col2_ratio = get_optimal_col_ratios(temp_df, max_stocks_in_row)
        fig_height = max(4.0, 2.0 + len(cell_text) * 0.45)
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height)); ax.axis('tight'); ax.axis('off')
        title_text = f"【{strategy_name}強勢精選 - 細產業族群分佈】 {today_str}"; ax.set_title(title_text, fontweight="bold", fontsize=16, pad=15)
        col_labels = ['細產業', '檔數', '精選股名']
        
        table = ax.table(cellText=cell_text, colLabels=col_labels, loc='center', cellLoc='left'); table.auto_set_font_size(False); table.set_fontsize(12); table.scale(1.0, 2.0) 
        for key, cell in table.get_celld().items():
            row, col = key
            if row == 0: 
                cell.set_facecolor('#e2efda'); cell.set_text_props(weight='bold', ha='center', fontsize=13)
            else:
                cell.set_facecolor('#ffffff')
                if col == 0: cell.set_text_props(ha='left', weight='bold') 
                elif col == 1: cell.set_text_props(ha='center', weight='bold') 
                else: cell.set_text_props(ha='left')   
            
            cell.PAD = 0.015
            if col == 0: cell.set_width(col0_ratio) 
            elif col == 1: cell.set_width(col1_ratio) 
            else: cell.set_width(col2_ratio) 
            
        img_path = os.path.join(output_dir, f"{strategy_name}_Industry_Group_{today_str}.png")
        plt.savefig(img_path, bbox_inches="tight", dpi=300, facecolor='white')
        plt.close('all')
        print(f"🖼️ {strategy_name}細產業族群分佈圖儲存至: {img_path}")
    except Exception as e: print(f"❌ 生成{strategy_name}細產業分類圖失敗。錯誤訊息: {e}")

def plot_kline_charts(pick_df, source_dir, output_dir, ma_windows, strategy_name="策略1"):
    """為篩選出的股票繪製 K 線圖與均線"""
    if pick_df.empty: return
    print(f"\n📈 開始為 {len(pick_df)} 檔 {strategy_name} 精選股票繪製 K 線圖...")
    
    success_count = 0
    mc = mpf.make_marketcolors(up='r', down='g', edge='inherit', wick='inherit', volume='inherit')
    custom_style = mpf.make_mpf_style(
        marketcolors=mc, gridstyle='--', gridcolor='#e0e0e0', base_mpf_style='yahoo', 
        rc={'font.family': ['Microsoft JhengHei', 'Segoe UI Emoji', 'sans-serif'], 'axes.unicode_minus': False, 'axes.titlesize': 18, 'axes.labelsize': 12, 'axes.linewidth': 2.5}
    )
    ma_colors = ['#1f77b4', '#ff7f0e', '#9467bd', '#ced4da', '#2ca02c'] 
    
    for _, row in pick_df.iterrows():
        full_ticker = row['完整股號']; stock_id = row['股號']; stock_name = row['股名']
        industry_name = row.get('細產業', '').strip()  
        if industry_name == 'nan' or not industry_name:
            industry_name = "未分類"
            
        file_path = os.path.join(source_dir, f"{full_ticker}.csv")
        
        if not os.path.exists(file_path): 
            continue
            
        try:
            df = read_price_csv(file_path)
            df.index = pd.to_datetime(df.index, errors='coerce')
            df = df[df.index.notnull()].sort_index()
            
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.droplevel(1)
            
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns: 
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
            
            if len(df) < 10: 
                continue

            for w in ma_windows: 
                df[f'MA{w}'] = df['Close'].rolling(window=w).mean()
            
            plot_df = df.tail(120).copy()
            plot_df.index.name = 'Date' 

            apds = []
            for i, w in enumerate(ma_windows):
                if not plot_df[f'MA{w}'].isna().all():
                    color_idx = i % len(ma_colors)
                    l_style = '--' if i == len(ma_windows) - 1 else '-'
                    l_width = 1.0 if i == len(ma_windows) - 1 else 1.2
                    apds.append(mpf.make_addplot(plot_df[f'MA{w}'], panel=0, color=ma_colors[color_idx], linestyle=l_style, width=l_width ))

            last_close = plot_df['Close'].iloc[-1]
            safe_stock_name = "".join(c for c in stock_name if c.isalnum() or c in [' ', '_', '-']).strip()
            save_path = os.path.join(output_dir, f"{stock_id}_{safe_stock_name}_KLine.png")
            
            chart_title = f"{stock_id} {stock_name} [{industry_name}] ({strategy_name})"
            
            fig, axes = mpf.plot(
                plot_df, type='candle', volume=True, addplot=apds, style=custom_style, 
                title=chart_title, 
                ylabel='價格 (TWD)', ylabel_lower='成交量 (張)', 
                hlines=dict(hlines=[last_close], colors=['#adb5bd'], linestyle='--', alpha=0.5), 
                savefig=dict(fname=save_path, dpi=200, bbox_inches='tight'), 
                figratio=(14, 9), figscale=1.2, returnfig=True
            )
            plt.close(fig) 
            success_count += 1
            print(f"📊 {stock_id} K線圖繪製完成 ({success_count}/{len(pick_df)})", end="\r")
        except Exception: 
            continue
            
    print(f"\n✅ {strategy_name} K 線圖繪製完畢！共成功產出 {success_count}/{len(pick_df)} 張圖。")
