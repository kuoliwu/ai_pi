"""價位強弱排行榜"""
import os
import time
import random

import pandas as pd
import matplotlib.pyplot as plt

from config import *


def generate_price_rankings(df_full, output_dir, today_str, price_days=[1, 3, 5, 20], top_n=20):
    """產出價位漲跌幅排行榜圖表"""
    print(f"\n📊 開始計算價位漲跌排行榜 (比較天數: {price_days}, 取前 {top_n} 名)...")
    price_results = {"strong": {}, "weak": {}}
    for d in price_days:
        col_name = f"漲幅_{d}日%" if d > 1 else "漲幅_1日%"
        if col_name not in df_full.columns: continue
        df_strong = df_full.sort_values(by=col_name, ascending=False).head(top_n).copy(); df_weak = df_full.sort_values(by=col_name, ascending=True).head(top_n).copy()
        price_results["strong"][d] = df_strong.to_dict('records'); price_results["weak"][d] = df_weak.to_dict('records')
        for trend_type, data_list, title_prefix, color in [("Strong", df_strong, "🔥強勢漲幅", "#f8d7da"), ("Weak", df_weak, "❄️弱勢跌幅", "#d1ecf1")]:
            plot_df = data_list[["股號", "股名", "細產業", "Close", col_name, "成交值(億)"]]
            fig, ax = plt.subplots(figsize=(10, 1.5 + len(plot_df) * 0.4)); ax.axis('tight'); ax.axis('off'); ax.set_title(f"【{title_prefix}排行榜 - {d}日】 {today_str}", fontweight="bold", fontsize=14, pad=15)
            table = ax.table(cellText=plot_df.values, colLabels=plot_df.columns, loc='center', cellLoc='center'); table.auto_set_font_size(False); table.set_fontsize(11); table.scale(1.2, 1.8)
            for j in range(len(plot_df.columns)): table[(0, j)].set_facecolor(color); table[(0, j)].set_text_props(weight='bold')
            img_path = os.path.join(output_dir, f"Price_{trend_type}_Rank_{d}D_{today_str}.png")
            plt.savefig(img_path, bbox_inches="tight", dpi=300)
            plt.close('all')
    return price_results

def generate_price_matrix_dashboard(price_res, output_dir, today_str, top_n=20):
    """將 5日/20日 的漲跌幅名單繪製成「價位焦點儀表板」"""
    print(f"\n🎨 開始產生價位變化焦點儀表板...")
    def get_rank_cols(data_list):
        if not data_list: return [""]*top_n, [""]*top_n, [""]*top_n
        ids = [str(r['股號']) for r in data_list]; names = [str(r['股名']) for r in data_list]; inds = [str(r.get('細產業', '')) for r in data_list]
        return ids + [""]*(top_n-len(ids)), names + [""]*(top_n-len(names)), inds + [""]*(top_n-len(inds))
    s5_id, s5_n, s5_i = get_rank_cols(price_res["strong"].get(5, [])); s20_id, s20_n, s20_i = get_rank_cols(price_res["strong"].get(20, [])); w5_id, w5_n, w5_i = get_rank_cols(price_res["weak"].get(5, [])); w20_id, w20_n, w20_i = get_rank_cols(price_res["weak"].get(20, []))
    cell_text = []
    for i in range(top_n): cell_text.append([s5_id[i], s5_n[i], s5_i[i], s20_id[i], s20_n[i], s20_i[i], w5_id[i], w5_n[i], w5_i[i], w20_id[i], w20_n[i], w20_i[i]])
    col_labels = ["股號", "股名", "細產業"] * 4
    try:
        fig, ax = plt.subplots(figsize=(18, 2.0 + top_n * 0.35)); ax.axis('tight'); ax.axis('off'); ax.set_title(f"【價位變化焦點儀表板】 {today_str}", fontweight="bold", fontsize=18, pad=65)
        ax.text(0.25, 0.98, "🚀 強勢多頭 (累積漲幅)", fontsize=16, fontweight='bold', ha='center', va='top', transform=ax.transAxes, color='#d62728', bbox=dict(facecolor='#f8d7da', edgecolor='none', boxstyle='round,pad=0.5'))
        ax.text(0.75, 0.98, "📉 弱勢空頭 (累積跌幅)", fontsize=16, fontweight='bold', ha='center', va='top', transform=ax.transAxes, color='#1f77b4', bbox=dict(facecolor='#d1ecf1', edgecolor='none', boxstyle='round,pad=0.5'))
        ax.text(0.125, 0.92, "週累積 (5日)", fontsize=14, fontweight='bold', ha='center', va='top', transform=ax.transAxes); ax.text(0.375, 0.92, "月累積 (20日)", fontsize=14, fontweight='bold', ha='center', va='top', transform=ax.transAxes)
        ax.text(0.625, 0.92, "週累積 (5日)", fontsize=14, fontweight='bold', ha='center', va='top', transform=ax.transAxes); ax.text(0.875, 0.92, "月累積 (20日)", fontsize=14, fontweight='bold', ha='center', va='top', transform=ax.transAxes)
        ax.plot([0.5, 0.5], [0, 1.0], color='black', lw=3.0, transform=ax.transAxes, clip_on=False); ax.plot([0.25, 0.25], [0, 0.94], color='gray', lw=1.5, linestyle='--', transform=ax.transAxes, clip_on=False); ax.plot([0.75, 0.75], [0, 0.94], color='gray', lw=1.5, linestyle='--', transform=ax.transAxes, clip_on=False)
        table = ax.table(cellText=cell_text, colLabels=col_labels, loc='center', cellLoc='center', bbox=[0, 0, 1, 0.88]); table.auto_set_font_size(False); table.set_fontsize(11)
        for key, cell in table.get_celld().items():
            row, col = key
            if row == 0: cell.set_facecolor('#f8d7da' if col < 6 else '#d1ecf1'); cell.set_text_props(weight='bold')
            if col in [0, 3, 6, 9]: cell.set_width(0.04)
            elif col in [1, 4, 7, 10]: cell.set_width(0.07)
            else: cell.set_width(0.14)
        img_path = os.path.join(output_dir, f"Price_Matrix_Dashboard_{today_str}.png")
        plt.savefig(img_path, bbox_inches="tight", dpi=300)
        plt.close('all')
    except Exception as e: print(f"❌ 生成價位矩陣圖失敗: {e}")
