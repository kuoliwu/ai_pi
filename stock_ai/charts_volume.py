"""量增 / 量縮排行榜、價量四象限儀表板"""
import os
import time
import random

import pandas as pd
import matplotlib.pyplot as plt

from config import *
from stock_ai.data_fetch import read_price_csv
from stock_ai import fmt_stock


def generate_volume_surge_ranking(tickers, ticker_map, industry_map, source_dir, output_dir, today_str, vol_days=[1, 5, 20], top_n=20, min_turnover=1.0):
    """產出量增排行榜"""
    print(f"\n📊 開始計算量增排行榜 (比較天數: {vol_days}, 取前 {top_n} 名, 需滿足成交值 > {min_turnover}億)...")
    results = {d: [] for d in vol_days}; total = len(tickers)
    for i, ticker in enumerate(tickers):
        file_path = os.path.join(source_dir, f"{ticker}.csv")
        if not os.path.exists(file_path): continue
        try:
            df = read_price_csv(file_path)
            if df.empty or 'Volume' not in df.columns or 'Close' not in df.columns: continue
            v = pd.to_numeric(df['Volume'].dropna(), errors='coerce'); c = pd.to_numeric(df['Close'].dropna(), errors='coerce')
            if len(v) < max(vol_days) + 1: continue
            today_vol = float(v.iloc[-1]); today_vol_lots = today_vol / 1000; close_price = float(c.iloc[-1])
            turnover_100m = (close_price * today_vol) / 100000000
            if turnover_100m < min_turnover: continue
            stock_id = ticker.split('.')[0]; stock_name = ticker_map.get(ticker, "未知"); industry_name = industry_map.get(ticker, "")
            for d in vol_days:
                if d == 1:
                    prev_vol = float(v.iloc[-2]); ratio = (today_vol / prev_vol) if prev_vol > 0 else 0; ref_vol_lots = prev_vol / 1000; ref_col_name = "昨日量(張)"
                else:
                    d_avg_vol = float(v.iloc[-d:].mean()); ratio = (today_vol / d_avg_vol) if d_avg_vol > 0 else 0; ref_vol_lots = d_avg_vol / 1000; ref_col_name = f"{d}日均量(張)"
                results[d].append({"股號": stock_id, "股名": stock_name, "細產業": industry_name, "收盤價": round(close_price, 2), "成交值(億)": round(turnover_100m, 2), "今日量(張)": round(today_vol_lots, 1), ref_col_name: round(ref_vol_lots, 1), "量增倍數": round(ratio, 2)})
        except Exception: continue
        if (i+1) % 500 == 0: print(f"量增計算進度: {i+1}/{total}...", end="\r")
    print("\n✅ 量增計算完成，開始繪製個別 N 日圖表...")
    for d in vol_days:
        if not results[d]: continue
        df_rank = pd.DataFrame(results[d]); df_rank = df_rank.sort_values(by="量增倍數", ascending=False).head(top_n).reset_index(drop=True)
        fig, ax = plt.subplots(figsize=(9.5, 1.5 + len(df_rank) * 0.4)); ax.axis('tight'); ax.axis('off')
        title_text = f"【🔥量增排行榜 - 取前 {top_n} 名】 {today_str}\n比較基準: {'今日量 / 昨日量' if d == 1 else f'今日量 / {d}日均量'} (成交值 > {min_turnover}億)"; ax.set_title(title_text, fontweight="bold", fontsize=14, pad=15)
        plot_df = df_rank.drop(columns=["細產業"], errors='ignore')
        table = ax.table(cellText=plot_df.values, colLabels=plot_df.columns, loc='center', cellLoc='center'); table.auto_set_font_size(False); table.set_fontsize(11); table.scale(1.2, 1.8)
        for j in range(len(plot_df.columns)): table[(0, j)].set_facecolor('#fff3cd'); table[(0, j)].set_text_props(weight='bold')
        img_path = os.path.join(output_dir, f"Volume_Surge_Rank_{d}D_{today_str}.png")
        plt.savefig(img_path, bbox_inches="tight", dpi=300, facecolor='white')
        plt.close('all')
    return results

def generate_volume_shrink_ranking(tickers, ticker_map, industry_map, source_dir, output_dir, today_str, vol_days=[1, 5, 20], top_n=20, min_turnover=1.0):
    """產出量縮排行榜"""
    print(f"\n📊 開始計算並繪製量縮排行榜 (比較天數: {vol_days}, 取前 {top_n} 名, 需滿足成交值 > {min_turnover}億)...")
    results = {d: [] for d in vol_days}; total = len(tickers)
    for i, ticker in enumerate(tickers):
        file_path = os.path.join(source_dir, f"{ticker}.csv")
        if not os.path.exists(file_path): continue
        try:
            df = read_price_csv(file_path)
            if df.empty or 'Volume' not in df.columns or 'Close' not in df.columns: continue
            v = pd.to_numeric(df['Volume'].dropna(), errors='coerce'); c = pd.to_numeric(df['Close'].dropna(), errors='coerce')
            if len(v) < max(vol_days) + 1: continue
            today_vol = float(v.iloc[-1]); today_vol_lots = today_vol / 1000; close_price = float(c.iloc[-1])
            turnover_100m = (close_price * today_vol) / 100000000
            if turnover_100m < min_turnover: continue
            stock_id = ticker.split('.')[0]; stock_name = ticker_map.get(ticker, "未知"); industry_name = industry_map.get(ticker, "")
            for d in vol_days:
                if d == 1:
                    prev_vol = float(v.iloc[-2]); ratio = (today_vol / prev_vol) if prev_vol > 0 else float('inf'); ref_vol_lots = prev_vol / 1000; ref_col_name = "昨日量(張)"
                else:
                    d_avg_vol = float(v.iloc[-d:].mean()); ratio = (today_vol / d_avg_vol) if d_avg_vol > 0 else float('inf'); ref_vol_lots = d_avg_vol / 1000; ref_col_name = f"{d}日均量(張)"
                if ratio == 0: continue
                results[d].append({"股號": stock_id, "股名": stock_name, "細產業": industry_name, "收盤價": round(close_price, 2), "成交值(億)": round(turnover_100m, 2), "今日量(張)": round(today_vol_lots, 1), ref_col_name: round(ref_vol_lots, 1), "量縮比例": round(ratio, 2)})
        except Exception: continue
        if (i+1) % 500 == 0: print(f"量縮計算進度: {i+1}/{total}...", end="\r")
    print("\n✅ 量縮計算完成，開始繪製個別 N 日圖表...")
    for d in vol_days:
        if not results[d]: continue
        df_rank = pd.DataFrame(results[d]); df_rank = df_rank.sort_values(by="量縮比例", ascending=True).head(top_n).reset_index(drop=True)
        fig, ax = plt.subplots(figsize=(9.5, 1.5 + len(df_rank) * 0.4)); ax.axis('tight'); ax.axis('off')
        title_text = f"【🧊量縮排行榜 - 取前 {top_n} 名】 {today_str}\n比較基準: {'今日量 / 昨日量' if d == 1 else f'今日量 / {d}日均量'} (成交值 > {min_turnover}億)"; ax.set_title(title_text, fontweight="bold", fontsize=14, pad=15)
        plot_df = df_rank.drop(columns=["細產業"], errors='ignore')
        table = ax.table(cellText=plot_df.values, colLabels=plot_df.columns, loc='center', cellLoc='center'); table.auto_set_font_size(False); table.set_fontsize(11); table.scale(1.2, 1.8)
        for j in range(len(plot_df.columns)): table[(0, j)].set_facecolor('#d1ecf1'); table[(0, j)].set_text_props(weight='bold')
        img_path = os.path.join(output_dir, f"Volume_Shrink_Rank_{d}D_{today_str}.png")
        plt.savefig(img_path, bbox_inches="tight", dpi=300, facecolor='white')
        plt.close('all')
    return results

def generate_volume_matrix_image(surge_res, shrink_res, output_dir, today_str, top_n=20):
    """將 5日/20日 的量增與量縮名單繪製成左右對稱的「三層式」大盤儀表板"""
    print(f"\n🎨 開始產生量能變化焦點儀表板 (三層式架構)...")
    def get_rank_cols(res_list, sort_key, asc):
        if not res_list: return [""] * top_n, [""] * top_n, [""] * top_n
        df = pd.DataFrame(res_list).sort_values(by=sort_key, ascending=asc).head(top_n)
        ids = [str(row['股號']) for _, row in df.iterrows()]; names = [str(row['股名']) for _, row in df.iterrows()]; inds = [str(row.get('細產業', '')) for _, row in df.iterrows()]
        ids += [""] * (top_n - len(ids)); names += [""] * (top_n - len(names)); inds += [""] * (top_n - len(inds))
        return ids, names, inds
    su5_id, su5_n, su5_i = get_rank_cols(surge_res.get(5, []), "量增倍數", False); su20_id, su20_n, su20_i = get_rank_cols(surge_res.get(20, []), "量增倍數", False)
    sh5_id, sh5_n, sh5_i = get_rank_cols(shrink_res.get(5, []), "量縮比例", True); sh20_id, sh20_n, sh20_i = get_rank_cols(shrink_res.get(20, []), "量縮比例", True)
    cell_text = []
    for i in range(top_n): cell_text.append([su5_id[i], su5_n[i], su5_i[i], su20_id[i], su20_n[i], su20_i[i], sh5_id[i], sh5_n[i], sh5_i[i], sh20_id[i], sh20_n[i], sh20_i[i]])
    col_labels = ["股號", "股名", "細產業"] * 4
    try:
        fig, ax = plt.subplots(figsize=(18, 2.0 + top_n * 0.35)); ax.axis('tight'); ax.axis('off')
        ax.set_title(f"【量能變化焦點儀表板】 {today_str}", fontweight="bold", fontsize=18, pad=65)
        ax.text(0.25, 0.98, "🔥 量增 (攻擊 / 湧入)", fontsize=16, fontweight='bold', ha='center', va='top', transform=ax.transAxes, color='#d62728', bbox=dict(facecolor='#fff3cd', edgecolor='none', boxstyle='round,pad=0.5'))
        ax.text(0.75, 0.98, "🧊 量縮 (洗盤 / 沉澱)", fontsize=16, fontweight='bold', ha='center', va='top', transform=ax.transAxes, color='#1f77b4', bbox=dict(facecolor='#d1ecf1', edgecolor='none', boxstyle='round,pad=0.5'))
        ax.text(0.125, 0.92, "周均 (5日)", fontsize=14, fontweight='bold', ha='center', va='top', transform=ax.transAxes); ax.text(0.375, 0.92, "月均 (20日)", fontsize=14, fontweight='bold', ha='center', va='top', transform=ax.transAxes)
        ax.text(0.625, 0.92, "周均 (5日)", fontsize=14, fontweight='bold', ha='center', va='top', transform=ax.transAxes); ax.text(0.875, 0.92, "月均 (20日)", fontsize=14, fontweight='bold', ha='center', va='top', transform=ax.transAxes)
        ax.plot([0.5, 0.5], [0, 1.0], color='black', lw=3.0, transform=ax.transAxes, clip_on=False); ax.plot([0.25, 0.25], [0, 0.94], color='gray', lw=1.5, linestyle='--', transform=ax.transAxes, clip_on=False); ax.plot([0.75, 0.75], [0, 0.94], color='gray', lw=1.5, linestyle='--', transform=ax.transAxes, clip_on=False)
        table = ax.table(cellText=cell_text, colLabels=col_labels, loc='center', cellLoc='center', bbox=[0, 0, 1, 0.88]); table.auto_set_font_size(False); table.set_fontsize(12)
        for key, cell in table.get_celld().items():
            row, col = key
            if row == 0: cell.set_facecolor('#fff3cd' if col < 6 else '#d1ecf1'); cell.set_text_props(weight='bold', fontsize=12)
            else: cell.set_facecolor('#ffffff')
            if col in [0, 3, 6, 9]: cell.set_width(0.04)
            elif col in [1, 4, 7, 10]: cell.set_width(0.07)
            else: cell.set_width(0.14)
        img_path = os.path.join(output_dir, f"Volume_Matrix_Dashboard_{today_str}.png")
        plt.savefig(img_path, bbox_inches="tight", dpi=300, facecolor='white')
        plt.close('all')
    except Exception as e: print(f"❌ 生成量能矩陣圖失敗。錯誤訊息: {e}")

def generate_price_volume_quadrant_dashboard(df_full, output_dir, today_str, quadrant_days=[1, 5, 10, 20], top_n=20):
    """產出價量四象限分析儀表板"""
    print(f"\n🎨 開始產生價量四象限儀表板 (個股清單)...")
    df_valid = df_full[df_full["成交值(億)"] >= MIN_TURNOVER_100M].copy()
    cell_text = []; colors_map = {}; row_idx = 1
    periods = []
    for d in quadrant_days:
        price_col = f"漲幅_{d}日%" if d > 1 else "漲幅_1日%"; vol_col = "昨日量(張)" if d == 1 else f"{d}MV(張)"; periods.append((d, price_col, vol_col))
    for n, price_col, vol_col in periods:
        if price_col not in df_valid.columns or vol_col not in df_valid.columns: continue
        df_period = df_valid.dropna(subset=[price_col, vol_col, "今日量(張)"]).copy(); df_period = df_period[df_period[vol_col] > 0] 
        df_period["vol_ratio"] = df_period["今日量(張)"] / df_period[vol_col]
        df_up = df_period[df_period[price_col] > 0]; df_down = df_period[df_period[price_col] < 0]
        q1 = df_up.sort_values(by="vol_ratio", ascending=False).head(top_n); q2 = df_down.sort_values(by="vol_ratio", ascending=False).head(top_n)
        q3 = df_up.sort_values(by="vol_ratio", ascending=True).head(top_n); q4 = df_down.sort_values(by="vol_ratio", ascending=True).head(top_n)
        def extract_cols(df):
            ids = [str(x) for x in df["股號"].tolist()]; names = [str(x) for x in df["股名"].tolist()]; inds = [str(x) for x in df["細產業"].tolist()]
            ids += [""] * (top_n - len(ids)); names += [""] * (top_n - len(names)); inds += [""] * (top_n - len(inds))
            return ids, names, inds
        q1_id, q1_n, q1_i = extract_cols(q1); q2_id, q2_n, q2_i = extract_cols(q2); q3_id, q3_n, q3_i = extract_cols(q3); q4_id, q4_n, q4_i = extract_cols(q4)
        cell_text.append(["", f"【 {n}日變化 】", ""] * 4)
        for c in range(12): colors_map[(row_idx, c)] = '#e2efda'
        row_idx += 1
        for i in range(top_n): cell_text.append([q1_id[i], q1_n[i], q1_i[i], q2_id[i], q2_n[i], q2_i[i], q3_id[i], q3_n[i], q3_i[i], q4_id[i], q4_n[i], q4_i[i]]); row_idx += 1
    if not cell_text: return
    col_labels = ["股號", "股名", "細產業"] * 4
    try:
        fig, ax = plt.subplots(figsize=(24, 2.0 + len(cell_text) * 0.35)); ax.axis('tight'); ax.axis('off')
        ax.set_title(f"【價量四象限分析儀表板】 {today_str}", fontweight="bold", fontsize=22, pad=65)
        ax.text(0.125, 0.98, "🚀 價漲量增 (攻擊)", fontsize=16, fontweight='bold', ha='center', va='top', transform=ax.transAxes, color='white', bbox=dict(facecolor='#d62728', edgecolor='none', boxstyle='round,pad=0.5'))
        ax.text(0.375, 0.98, "🩸 價跌量增 (宣洩)", fontsize=16, fontweight='bold', ha='center', va='top', transform=ax.transAxes, color='white', bbox=dict(facecolor='#2ca02c', edgecolor='none', boxstyle='round,pad=0.5'))
        ax.text(0.625, 0.98, "⚠️ 價漲量縮 (背離)", fontsize=16, fontweight='bold', ha='center', va='top', transform=ax.transAxes, color='black', bbox=dict(facecolor='#ff7f0e', edgecolor='none', boxstyle='round,pad=0.5'))
        ax.text(0.875, 0.98, "🧱 價跌量縮 (築底)", fontsize=16, fontweight='bold', ha='center', va='top', transform=ax.transAxes, color='white', bbox=dict(facecolor='#1f77b4', edgecolor='none', boxstyle='round,pad=0.5'))
        ax.plot([0.25, 0.25], [0, 1.0], color='black', lw=2.0, transform=ax.transAxes, clip_on=False); ax.plot([0.50, 0.50], [0, 1.0], color='black', lw=3.0, transform=ax.transAxes, clip_on=False); ax.plot([0.75, 0.75], [0, 1.0], color='black', lw=2.0, transform=ax.transAxes, clip_on=False)
        table = ax.table(cellText=cell_text, colLabels=col_labels, loc='center', cellLoc='center', bbox=[0, 0, 1, 0.92]); table.auto_set_font_size(False); table.set_fontsize(11)
        for key, cell in table.get_celld().items():
            row, col = key
            if row == 0:
                if col < 3: cell.set_facecolor('#f8d7da')
                elif col < 6: cell.set_facecolor('#d4edda')
                elif col < 9: cell.set_facecolor('#fff3cd')
                else: cell.set_facecolor('#d1ecf1')
                cell.set_text_props(weight='bold', fontsize=12)
            else:
                if key in colors_map: cell.set_facecolor(colors_map[key]); cell.set_text_props(weight='bold', fontsize=12, color='blue')
                else: cell.set_facecolor('#ffffff')
            if col % 3 == 0: cell.set_width(0.04)
            elif col % 3 == 1: cell.set_width(0.07)
            else: cell.set_width(0.14)
        img_path = os.path.join(output_dir, f"Volume_Price_Quadrant_Dashboard_{today_str}.png")
        plt.savefig(img_path, bbox_inches="tight", dpi=300, facecolor='white')
        plt.close('all')
    except Exception as e: print(f"❌ 生成價量四象限圖失敗: {e}")

def generate_price_volume_quadrant_industry_dashboard(df_full, output_dir, today_str, quadrant_days=[1, 5, 10, 20], top_n=20):
    """將價量四象限結果依細產業分組 (含檔數遞減排序)"""
    print(f"\n🎨 開始產生價量四象限儀表板 (細產業族群分類)...")
    df_valid = df_full[df_full["成交值(億)"] >= MIN_TURNOVER_100M].copy()
    cell_text = []; colors_map = {}; row_idx = 1
    periods = []
    for d in quadrant_days:
        price_col = f"漲幅_{d}日%" if d > 1 else "漲幅_1日%"; vol_col = "昨日量(張)" if d == 1 else f"{d}MV(張)"; periods.append((d, price_col, vol_col))
    
    def group_by_industry(df):
        if df.empty: return []
        temp = df.copy(); temp['細產業'] = temp['細產業'].replace('', '未分類').fillna('未分類')
        group_sizes = temp.groupby('細產業').size().reset_index(name='count').sort_values(by=['count', '細產業'], ascending=[False, True])
        res = []
        for _, r in group_sizes.iterrows():
            ind = r['細產業']; cnt = r['count']
            group = temp[temp['細產業'] == ind]
            items = [fmt_stock(sid, sname) for sid, sname in zip(group['股號'], group['股名'])]
            chunks = [items[i:i+4] for i in range(0, len(items), 4)] 
            for idx_chunk, chunk in enumerate(chunks):
                chunk_str = '  '.join(chunk)
                if idx_chunk == 0: res.append([ind, str(cnt), chunk_str])
                else: res.append(["", "", chunk_str])
        return res
        
    def pad_list(lst, length): return lst + [["", "", ""]] * (length - len(lst))
    
    for n, price_col, vol_col in periods:
        if price_col not in df_valid.columns or vol_col not in df_valid.columns: continue
        df_period = df_valid.dropna(subset=[price_col, vol_col, "今日量(張)"]).copy(); df_period = df_period[df_period[vol_col] > 0] 
        df_period["vol_ratio"] = df_period["今日量(張)"] / df_period[vol_col]
        df_up = df_period[df_period[price_col] > 0]; df_down = df_period[df_period[price_col] < 0]
        q1 = df_up.sort_values(by="vol_ratio", ascending=False).head(top_n); q2 = df_down.sort_values(by="vol_ratio", ascending=False).head(top_n)
        q3 = df_up.sort_values(by="vol_ratio", ascending=True).head(top_n); q4 = df_down.sort_values(by="vol_ratio", ascending=True).head(top_n)
        q1_grp = group_by_industry(q1); q2_grp = group_by_industry(q2); q3_grp = group_by_industry(q3); q4_grp = group_by_industry(q4)
        max_rows = max(len(q1_grp), len(q2_grp), len(q3_grp), len(q4_grp))
        if max_rows == 0: continue 
        q1_grp = pad_list(q1_grp, max_rows); q2_grp = pad_list(q2_grp, max_rows); q3_grp = pad_list(q3_grp, max_rows); q4_grp = pad_list(q4_grp, max_rows)
        cell_text.append([f"【 {n}日變化 】", "", ""] * 4)
        for c in range(12): colors_map[(row_idx, c)] = '#e2efda'
        row_idx += 1
        for i in range(max_rows): cell_text.append(q1_grp[i] + q2_grp[i] + q3_grp[i] + q4_grp[i]); row_idx += 1
        
    if not cell_text: return
    col_labels = ["細產業", "檔數", "精選股名"] * 4
    
    try:
        max_ind_chars = df_valid['細產業'].astype(str).str.len().max() if not df_valid.empty else 4
        col0_abs = max(1.2, max_ind_chars * 0.28)
        col1_abs = 0.6  
        col2_abs = 4 * 1.55 
        pair_width = col0_abs + col1_abs + col2_abs
        fig_width = max(24.0, pair_width * 4 + 1.0)
        col0_ratio = col0_abs / (pair_width * 4)
        col1_ratio = col1_abs / (pair_width * 4)
        col2_ratio = 0.25 - col0_ratio - col1_ratio

        fig, ax = plt.subplots(figsize=(fig_width, max(4.0, 2.0 + len(cell_text) * 0.35))); ax.axis('tight'); ax.axis('off')
        ax.set_title(f"【價量四象限 - 細產業族群分佈總表】 {today_str}", fontweight="bold", fontsize=22, pad=65)
        ax.text(0.125, 0.98, "🚀 價漲量增 (攻擊)", fontsize=16, fontweight='bold', ha='center', va='top', transform=ax.transAxes, color='white', bbox=dict(facecolor='#d62728', edgecolor='none', boxstyle='round,pad=0.5'))
        ax.text(0.375, 0.98, "🩸 價跌量增 (宣洩)", fontsize=16, fontweight='bold', ha='center', va='top', transform=ax.transAxes, color='white', bbox=dict(facecolor='#2ca02c', edgecolor='none', boxstyle='round,pad=0.5'))
        ax.text(0.625, 0.98, "⚠️ 價漲量縮 (背離)", fontsize=16, fontweight='bold', ha='center', va='top', transform=ax.transAxes, color='black', bbox=dict(facecolor='#ff7f0e', edgecolor='none', boxstyle='round,pad=0.5'))
        ax.text(0.875, 0.98, "🧱 價跌量縮 (築底)", fontsize=16, fontweight='bold', ha='center', va='top', transform=ax.transAxes, color='white', bbox=dict(facecolor='#1f77b4', edgecolor='none', boxstyle='round,pad=0.5'))
        ax.plot([0.25, 0.25], [0, 1.0], color='black', lw=2.0, transform=ax.transAxes, clip_on=False); ax.plot([0.50, 0.50], [0, 1.0], color='black', lw=3.0, transform=ax.transAxes, clip_on=False); ax.plot([0.75, 0.75], [0, 1.0], color='black', lw=2.0, transform=ax.transAxes, clip_on=False)
        table = ax.table(cellText=cell_text, colLabels=col_labels, loc='center', cellLoc='center', bbox=[0, 0, 1, 0.92]); table.auto_set_font_size(False); table.set_fontsize(11)
        for key, cell in table.get_celld().items():
            row, col = key
            if row == 0:
                if col < 3: cell.set_facecolor('#f8d7da')
                elif col < 6: cell.set_facecolor('#d4edda')
                elif col < 9: cell.set_facecolor('#fff3cd')
                else: cell.set_facecolor('#d1ecf1')
                cell.set_text_props(weight='bold', fontsize=12, ha='center')
            else:
                if key in colors_map: 
                    cell.set_facecolor(colors_map[key]); cell.set_text_props(weight='bold', fontsize=12, color='blue', ha='left')
                else: 
                    cell.set_facecolor('#ffffff'); 
                    if col % 3 == 0: cell.set_text_props(ha='left', weight='bold')
                    elif col % 3 == 1: cell.set_text_props(ha='center', weight='bold')
                    else: cell.set_text_props(ha='left')
            
            cell.PAD = 0.015
            if col % 3 == 0: cell.set_width(col0_ratio)
            elif col % 3 == 1: cell.set_width(col1_ratio)
            else: cell.set_width(col2_ratio)
            
        img_path = os.path.join(output_dir, f"Volume_Price_Quadrant_Industry_All_{today_str}.png")
        plt.savefig(img_path, bbox_inches="tight", dpi=300, facecolor='white')
        plt.close('all')
    except Exception as e: print(f"❌ 生成價量四象限細產業圖失敗: {e}")
