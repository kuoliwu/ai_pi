"""台股價量分析套件：匯入時統一設定警告過濾與中文字體"""
import os
import warnings

import matplotlib
matplotlib.use("Agg")  # 不開視窗，只輸出圖檔 (多程序繪圖也需要)
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# === 忽略 Pandas 與 Matplotlib 的警告 ===
warnings.filterwarnings('ignore', category=UserWarning, message=".*Could not infer format.*")
warnings.filterwarnings('ignore', category=UserWarning, message=".*Glyph.*")
warnings.filterwarnings('ignore', category=DeprecationWarning)

# === 載入微軟正黑體與 Emoji 字體 (Windows 原生路徑 / WSL 掛載路徑) ===
font_paths = [
    r"C:\Windows\Fonts\msjh.ttc", r"C:\Windows\Fonts\seguiemj.ttf",
    "/mnt/c/Windows/Fonts/msjh.ttc", "/mnt/c/Windows/Fonts/seguiemj.ttf",
]
for font_path in font_paths:
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)

plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Segoe UI Emoji']
plt.rcParams['axes.unicode_minus'] = False


def fmt_stock(sid, sname):
    """族群圖中單檔股票的顯示文字"""
    from config import ITALIC_STOCK_ID
    return f"$\\mathit{{{sid}}}$ {sname}" if ITALIC_STOCK_ID else f"{sid} {sname}"
