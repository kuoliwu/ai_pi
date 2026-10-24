"""大盤溫度計、極端漲跌 / 強於大盤族群、細產業資金流向圖"""
import os
import time
import random

import pandas as pd
import matplotlib.pyplot as plt

from config import *
from stock_ai import fmt_stock


def plot_price_change_distribution(df, output_dir, today_str, dist_days, dist_thresholds, market_changes=None):
    """繪製大盤個股多日漲跌幅分佈直方圖"""
    print(f"\n🎨 開始產生大盤溫度計分佈圖表...")
    for idx, d in enumerate(dist_days):
        col_name = f"漲幅_{d}日%"
        if df.empty or col_name not in df.columns: continue
        
        threshold = dist_thresholds[idx] if idx < len(dist_thresholds) else 9.9
        hist_limit = int(round(threshold))
        
        rounded_pct = df[col_name].round().clip(lower=-hist_limit, upper=hist_limit)
        dist = rounded_pct.value_counts().sort_index(ascending=False)
        max_count = dist.max() if not dist.empty else 1
        
        try:
            x_labels = list(range(-hist_limit, hist_limit + 1))
            dist_asc = rounded_pct.value_counts().sort_index()
            y_values = [dist_asc.get(x, 0) for x in x_labels]
            colors = ['#2ca02c' if x < 0 else '#d62728' if x > 0 else '#7f7f7f' for x in x_labels]
            
            fig_width = max(12, len(x_labels) * 0.35)
            fig, ax = plt.subplots(figsize=(fig_width, 6))
            
            bars = ax.bar(x_labels, y_values, color=colors, alpha=0.85, edgecolor='black', linewidth=0.5)
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height + (max_count * 0.01), f'{int(height)}', ha='center', va='bottom', fontsize=10, fontweight='bold')
            
            if market_changes and d in market_changes:
                m_change = market_changes[d]
                m_change_clipped = max(-hist_limit, min(hist_limit, m_change))
                ax.axvline(x=m_change_clipped, color='#0056b3', linestyle='-.', linewidth=2.5, alpha=0.9)
                align = 'left' if m_change_clipped <= 0 else 'right'
                offset = 0.2 if m_change_clipped <= 0 else -0.2
                bbox_props = dict(boxstyle="round,pad=0.3", fc="#cce5ff", ec="#0056b3", alpha=0.8)
                ax.text(m_change_clipped + offset, max_count * 0.95, f"大盤\n{m_change}%", 
                        color='#0056b3', fontweight='bold', fontsize=11,
                        ha=align, va='top', bbox=bbox_props)

            ax.set_title(f"【大盤溫度計】台股個股 {d} 日漲跌幅分佈 ({today_str})", fontsize=16, fontweight='bold', pad=15)
            ax.set_xlabel("漲跌幅 (%)", fontsize=12, fontweight='bold')
            ax.set_ylabel("股票檔數", fontsize=12, fontweight='bold')
            ax.set_xticks(x_labels)
            
            xticklabels = [f"≦-{hist_limit}%" if x == -hist_limit else f"≧{hist_limit}%" if x == hist_limit else f"{x}%" for x in x_labels]
            if len(x_labels) > 25:
                ax.set_xticklabels(xticklabels, rotation=45, fontsize=10)
            else:
                ax.set_xticklabels(xticklabels, fontsize=12)
                
            ax.grid(axis='y', linestyle='--', alpha=0.5)
            ax.set_ylim(0, max_count * 1.1)
            
            img_path = os.path.join(output_dir, f"Market_Temperature_{d}D_{today_str}.png")
            plt.savefig(img_path, bbox_inches="tight", dpi=300, facecolor='white')
            plt.close('all')
            print(f"🖼️ {d} 日大盤溫度計儲存至: {img_path}")
        except Exception as e: print(f"❌ 生成 {d} 日分佈圖失敗。錯誤訊息: {e}")

def get_optimal_col_ratios(df_to_draw, max_stocks_in_row):
    """計算最適合的欄寬比例"""
    max_stocks_in_row = max(1, max_stocks_in_row)
    max_ind_chars = df_to_draw['細產業'].astype(str).str.len().max() if not df_to_draw.empty else 4
    
    col0_abs_width = max(1.5, max_ind_chars * 0.25)
    col1_abs_width = 0.6                            
    col2_abs_width = max_stocks_in_row * 1.5 + 1.0  
    
    fig_width = max(12.0, col0_abs_width + col1_abs_width + col2_abs_width)
    
    col0_ratio = col0_abs_width / fig_width
    col1_ratio = col1_abs_width / fig_width
    col2_ratio = 1.0 - col0_ratio - col1_ratio
    
    return fig_width, col0_ratio, col1_ratio, col2_ratio

def generate_market_extremes_industry_image(df_full, output_dir, today_str, dist_days, dist_thresholds):
    """繪製大盤極端漲跌幅的細產業分佈圖"""
    print(f"\n🎨 開始繪製大盤極端漲跌幅細產業分佈圖...")
    
    for idx, d in enumerate(dist_days):
        col_name = f"漲幅_{d}日%"
        if col_name not in df_full.columns: continue
        
        threshold = dist_thresholds[idx] if idx < len(dist_thresholds) else 9.9
        up_df = df_full[df_full[col_name] >= threshold].copy()
        down_df = df_full[df_full[col_name] <= -threshold].copy()
        if up_df.empty and down_df.empty: 
            continue
        
        cell_text = []; colors_map = {}; row_idx = 1
        max_stocks_in_row = 0
        combined_df = pd.concat([up_df, down_df])
        
        if not up_df.empty:
            up_df['細產業'] = up_df['細產業'].replace('', '未分類').fillna('未分類')
            group_sizes = up_df.groupby('細產業').size().reset_index(name='count').sort_values(by=['count', '細產業'], ascending=[False, True])
            
            cell_text.append([f"🚀 {d}日累積漲幅 ≧ {threshold}%", "", ""])
            colors_map[(row_idx, 0)] = '#f8d7da'; colors_map[(row_idx, 1)] = '#f8d7da'; colors_map[(row_idx, 2)] = '#f8d7da'; row_idx += 1
            
            for _, r in group_sizes.iterrows():
                ind = r['細產業']; cnt = r['count']
                group = up_df[up_df['細產業'] == ind]
                items = [fmt_stock(sid, sname) for sid, sname in zip(group['股號'], group['股名'])]
                chunks = [items[i:i+MAX_COL_STOCK_NUMBER] for i in range(0, len(items), MAX_COL_STOCK_NUMBER)]
                for idx_chunk, chunk in enumerate(chunks):
                    max_stocks_in_row = max(max_stocks_in_row, len(chunk))
                    chunk_str = '  '.join(chunk)
                    if idx_chunk == 0: cell_text.append([ind, str(cnt), chunk_str])
                    else: cell_text.append(["", "", chunk_str]) 
                    row_idx += 1

        if not down_df.empty:
            down_df['細產業'] = down_df['細產業'].replace('', '未分類').fillna('未分類')
            group_sizes = down_df.groupby('細產業').size().reset_index(name='count').sort_values(by=['count', '細產業'], ascending=[False, True])
            
            cell_text.append([f"🩸 {d}日累積跌幅 ≦ -{threshold}%", "", ""])
            colors_map[(row_idx, 0)] = '#d1ecf1'; colors_map[(row_idx, 1)] = '#d1ecf1'; colors_map[(row_idx, 2)] = '#d1ecf1'; row_idx += 1
            
            for _, r in group_sizes.iterrows():
                ind = r['細產業']; cnt = r['count']
                group = down_df[down_df['細產業'] == ind]
                items = [fmt_stock(sid, sname) for sid, sname in zip(group['股號'], group['股名'])]
                chunks = [items[i:i+MAX_COL_STOCK_NUMBER] for i in range(0, len(items), MAX_COL_STOCK_NUMBER)]
                for idx_chunk, chunk in enumerate(chunks):
                    max_stocks_in_row = max(max_stocks_in_row, len(chunk))
                    chunk_str = '  '.join(chunk)
                    if idx_chunk == 0: cell_text.append([ind, str(cnt), chunk_str])
                    else: cell_text.append(["", "", chunk_str])
                    row_idx += 1
                    
        try:
            fig_width, col0_ratio, col1_ratio, col2_ratio = get_optimal_col_ratios(combined_df, max_stocks_in_row)
            fig_height = max(4.0, 2.0 + len(cell_text) * 0.45)
            
            fig, ax = plt.subplots(figsize=(fig_width, fig_height)); ax.axis('tight'); ax.axis('off')
            title_text = f"【大盤極端漲跌族群分佈 - {d}日】 {today_str}"; ax.set_title(title_text, fontweight="bold", fontsize=18, pad=15)
            col_labels = ["狀態 / 細產業", "檔數", "股票清單"]
            
            table = ax.table(cellText=cell_text, colLabels=col_labels, loc='center', cellLoc='left'); table.auto_set_font_size(False); table.set_fontsize(12); table.scale(1.0, 2.0)
            for key, cell in table.get_celld().items():
                row, col = key
                if row == 0: 
                    cell.set_facecolor('#e2efda'); cell.set_text_props(weight='bold', ha='center', fontsize=14)
                else:
                    if key in colors_map: 
                        cell.set_facecolor(colors_map[key]); cell.set_text_props(weight='bold', fontsize=14, ha='left')
                    else: 
                        cell.set_facecolor('#ffffff')
                        if col == 0: cell.set_text_props(ha='left', weight='bold')
                        elif col == 1: cell.set_text_props(ha='center', weight='bold')
                        else: cell.set_text_props(ha='left')
                
                cell.PAD = 0.015
                if col == 0: cell.set_width(col0_ratio)
                elif col == 1: cell.set_width(col1_ratio)
                else: cell.set_width(col2_ratio)
                
            img_path = os.path.join(output_dir, f"Market_Extremes_Industry_{d}D_{today_str}.png")
            plt.savefig(img_path, bbox_inches="tight", dpi=300, facecolor='white')
            plt.close('all')
            print(f"🖼️ {d}日大盤極端漲跌族群圖儲存至: {img_path}")
        except Exception as e: print(f"❌ 生成 {d}日大盤極端漲跌族群圖失敗。錯誤訊息: {e}")

def generate_outperform_market_industry_image(df_full, output_dir, today_str, dist_days, market_changes):
    """繪製強於大盤的細產業分佈圖"""
    print(f"\n🎨 開始繪製強於大盤族群分佈圖...")
    
    for d in dist_days:
        col_name = f"漲幅_{d}日%"
        if col_name not in df_full.columns or market_changes is None or d not in market_changes: 
            continue
        
        m_change = market_changes[d]
        outperform_df = df_full[df_full[col_name] > m_change].copy()
        
        if outperform_df.empty: 
            continue
        
        cell_text = []; colors_map = {}; row_idx = 1
        max_stocks_in_row = 0
        
        outperform_df['細產業'] = outperform_df['細產業'].replace('', '未分類').fillna('未分類')
        group_sizes = outperform_df.groupby('細產業').size().reset_index(name='count').sort_values(by=['count', '細產業'], ascending=[False, True])
        
        cell_text.append([f"🔥 {d}日漲幅強於大盤 (> {m_change}%)", "", ""])
        colors_map[(row_idx, 0)] = '#fff3cd'; colors_map[(row_idx, 1)] = '#fff3cd'; colors_map[(row_idx, 2)] = '#fff3cd'; row_idx += 1
        
        for _, r in group_sizes.iterrows():
            ind = r['細產業']; cnt = r['count']
            group = outperform_df[outperform_df['細產業'] == ind]
            items = [fmt_stock(sid, sname) for sid, sname in zip(group['股號'], group['股名'])]
            chunks = [items[i:i+MAX_COL_STOCK_NUMBER] for i in range(0, len(items), MAX_COL_STOCK_NUMBER)]
            for idx_chunk, chunk in enumerate(chunks):
                max_stocks_in_row = max(max_stocks_in_row, len(chunk))
                chunk_str = '  '.join(chunk)
                if idx_chunk == 0: cell_text.append([ind, str(cnt), chunk_str])
                else: cell_text.append(["", "", chunk_str]) 
                row_idx += 1

        try:
            fig_width, col0_ratio, col1_ratio, col2_ratio = get_optimal_col_ratios(outperform_df, max_stocks_in_row)
            fig_height = max(4.0, 2.0 + len(cell_text) * 0.45)
            
            fig, ax = plt.subplots(figsize=(fig_width, fig_height)); ax.axis('tight'); ax.axis('off')
            title_text = f"【強於大盤族群分佈 - {d}日】 {today_str}"
            ax.set_title(title_text, fontweight="bold", fontsize=18, pad=15)
            col_labels = ["狀態 / 細產業", "檔數", "股票清單"]
            
            table = ax.table(cellText=cell_text, colLabels=col_labels, loc='center', cellLoc='left'); table.auto_set_font_size(False); table.set_fontsize(12); table.scale(1.0, 2.0)
            for key, cell in table.get_celld().items():
                row, col = key
                if row == 0: 
                    cell.set_facecolor('#e2efda'); cell.set_text_props(weight='bold', ha='center', fontsize=14)
                else:
                    if key in colors_map: 
                        cell.set_facecolor(colors_map[key]); cell.set_text_props(weight='bold', fontsize=14, ha='left')
                    else: 
                        cell.set_facecolor('#ffffff')
                        if col == 0: cell.set_text_props(ha='left', weight='bold')
                        elif col == 1: cell.set_text_props(ha='center', weight='bold')
                        else: cell.set_text_props(ha='left')
                
                cell.PAD = 0.015
                if col == 0: cell.set_width(col0_ratio)
                elif col == 1: cell.set_width(col1_ratio)
                else: cell.set_width(col2_ratio)
                
            img_path = os.path.join(output_dir, f"Market_Outperform_Industry_{d}D_{today_str}.png")
            plt.savefig(img_path, bbox_inches="tight", dpi=300, facecolor='white')
            plt.close('all')
            print(f"🖼️ {d}日強於大盤族群圖儲存至: {img_path}")
        except Exception as e: print(f"❌ 生成 {d}日強於大盤族群圖失敗。錯誤訊息: {e}")

def generate_industry_capital_flow_image(df_full, output_dir, today_str, top_n=20):
    """繪製細產業的總資金(成交值)流向排行榜"""
    print(f"\n📊 開始繪製【細產業資金流向分佈圖】...")
    if df_full.empty or "成交值(億)" not in df_full.columns:
        return
        
    temp_df = df_full.copy()
    temp_df['細產業'] = temp_df['細產業'].replace('', '未分類').fillna('未分類')
    temp_df = temp_df[temp_df['細產業'] != '未分類']
    
    flow_df = temp_df.groupby('細產業')['成交值(億)'].sum().reset_index()
    flow_df = flow_df.sort_values(by='成交值(億)', ascending=False)
    
    total_market_vol = flow_df['成交值(億)'].sum()
    if total_market_vol <= 0: return
    
    top_df = flow_df.head(top_n).copy()
    other_industries_df = flow_df.iloc[top_n:].copy()
    other_vol = other_industries_df['成交值(億)'].sum()
    
    if not other_industries_df.empty:
        other_list_path = os.path.join(output_dir, f"Capital_Flow_Other_Industry_Summary_{today_str}.csv")
        other_industries_df.to_csv(other_list_path, index=False, encoding='utf-8-sig')
        
        other_industry_names = other_industries_df['細產業'].tolist()
        other_stocks_df = temp_df[temp_df['細產業'].isin(other_industry_names)].copy()
        other_stocks_df = other_stocks_df[['股號', '股名', '細產業', 'Close', '漲幅%', '成交值(億)', '今日量(張)']]
        other_stocks_df = other_stocks_df.sort_values(by='成交值(億)', ascending=False)
        detail_list_path = os.path.join(output_dir, f"Capital_Flow_Other_Stock_Details_{today_str}.csv")
        other_stocks_df.to_csv(detail_list_path, index=False, encoding='utf-8-sig')
        print(f"📄 已匯出被歸類為「其他」的【產業總和】與【個股明細】至大盤資料夾")
        
        try:
            plot_other_df = other_industries_df.head(top_n).copy()
            total_other_vol = other_industries_df['成交值(億)'].sum()
            plot_other_df['資金佔比(%)'] = (plot_other_df['成交值(億)'] / total_other_vol) * 100
            plot_other_df = plot_other_df.sort_values(by='成交值(億)', ascending=True)
            
            fig_other, ax_other = plt.subplots(figsize=(12, 10))
            colors_other = ['#ced4da'] * len(plot_other_df)
            if len(plot_other_df) >= 1: colors_other[-1] = '#d62728'
            if len(plot_other_df) >= 2: colors_other[-2] = '#ff7f0e'
            if len(plot_other_df) >= 3: colors_other[-3] = '#1f77b4'
            
            bars_other = ax_other.barh(plot_other_df['細產業'], plot_other_df['成交值(億)'], color=colors_other, edgecolor='black', alpha=0.85)
            
            for bar, pct in zip(bars_other, plot_other_df['資金佔比(%)']):
                width = bar.get_width()
                ax_other.text(width + (total_other_vol * 0.005), bar.get_y() + bar.get_height()/2, 
                         f"{width:,.1f}億 ({pct:.1f}%)", 
                         va='center', ha='left', fontsize=11, fontweight='bold', color='#333333')
            
            ax_other.set_title(f"【台股『其他』內部細產業資金流向排行】 {today_str}\n「其他」總成交值: {total_other_vol:,.1f}億", fontsize=18, fontweight='bold', pad=20)
            ax_other.set_xlabel("成交值 (億元)", fontsize=12, fontweight='bold')
            ax_other.set_ylabel("細產業", fontsize=12, fontweight='bold')
            ax_other.spines['top'].set_visible(False)
            ax_other.spines['right'].set_visible(False)
            ax_other.grid(axis='x', linestyle='--', alpha=0.5)
            plt.margins(y=0.02)
            ax_other.set_xlim(0, plot_other_df['成交值(億)'].max() * 1.25)
            
            img_path_other = os.path.join(output_dir, f"Capital_Flow_Other_Detail_{today_str}.png")
            plt.savefig(img_path_other, bbox_inches="tight", dpi=300, facecolor='white')
            plt.close('all')
            print(f"🖼️ 『其他』內部細產業資金流向圖儲存至: {img_path_other}")
        except Exception as e:
            print(f"❌ 生成『其他』資金流向圖失敗: {e}")

    if other_vol > 0:
        other_row = pd.DataFrame([{'細產業': '其他', '成交值(億)': other_vol}])
        top_df = pd.concat([top_df, other_row], ignore_index=True)
        
    top_df['資金佔比(%)'] = (top_df['成交值(億)'] / total_market_vol) * 100
    
    try:
        fig, ax = plt.subplots(figsize=(12, 10))
        main_df = top_df[top_df['細產業'] != '其他'].sort_values(by='成交值(億)', ascending=True)
        other_df = top_df[top_df['細產業'] == '其他']
        plot_df = pd.concat([other_df, main_df], ignore_index=True)
        
        colors = ['#ced4da'] * len(plot_df)
        if len(main_df) >= 1: colors[-1] = '#d62728'
        if len(main_df) >= 2: colors[-2] = '#ff7f0e'
        if len(main_df) >= 3: colors[-3] = '#1f77b4'
            
        bars = ax.barh(plot_df['細產業'], plot_df['成交值(億)'], color=colors, edgecolor='black', alpha=0.85)
        
        for bar, pct in zip(bars, plot_df['資金佔比(%)']):
            width = bar.get_width()
            ax.text(width + (total_market_vol * 0.005), bar.get_y() + bar.get_height()/2, 
                     f"{width:,.1f}億 ({pct:.1f}%)", 
                     va='center', ha='left', fontsize=11, fontweight='bold', color='#333333')
                     
        ax.set_title(f"【台股細產業資金流向分佈】 {today_str}\n總成交值(已排除未分類): {total_market_vol:,.1f}億", fontsize=18, fontweight='bold', pad=20)
        ax.set_xlabel("成交值 (億元)", fontsize=12, fontweight='bold')
        ax.set_ylabel("細產業", fontsize=12, fontweight='bold')
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='x', linestyle='--', alpha=0.5)
        plt.margins(y=0.02)
        ax.set_xlim(0, top_df['成交值(億)'].max() * 1.25)
        
        img_path = os.path.join(output_dir, f"Capital_Flow_Industry_{today_str}.png")
        plt.savefig(img_path, bbox_inches="tight", dpi=300, facecolor='white')
        plt.close('all')
        print(f"🖼️ 細產業資金流向圖(主圖)儲存至: {img_path}")
    except Exception as e:
        print(f"❌ 生成主資金流向圖失敗: {e}")
