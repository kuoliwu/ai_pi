# ai_pi — 台股價量分析

每日抓取台股上市櫃（約 2,000 檔）歷史報價，計算均線 / 均量 / 漲跌幅等指標，依多種選股策略篩選，並輸出圖表與 Excel 報表。

## 安裝與執行

```bash
pip install -r requirements.txt
python code_artifact.py
```

- 字體：圖表使用「微軟正黑體」與「Segoe UI Emoji」。Windows 直接可用；WSL 會自動讀取 `/mnt/c/Windows/Fonts`。
- 同一天重複執行時，已下載且完整的股票不會重抓。

## 資料夾結構

```
ai_pi/
├── code_artifact.py        # 主程式入口：串接所有步驟、平行產出報表
├── config.py               # ★ 所有可調參數 (路徑、下載、均線、策略條件…)
├── requirements.txt
├── data/                   # 使用者提供的輸入檔
│   ├── stock_list.xlsx     # 細產業對照表 (欄位: 股號, 股名, 產業類別, 細分類, 備註)
│   └── stock_SB/           # 自訂名單：每個 txt 一行一個股號，檔名 = 日期/標籤
├── stock_ai/               # 程式模組
│   ├── __init__.py         # 警告過濾、中文字體設定
│   ├── data_fetch.py       # 股票清單、產業對照、批次下載、大盤指數、CSV 讀取快取
│   ├── indicators.py       # 每檔技術指標與策略 1/2 判斷條件
│   ├── charts_market.py    # 大盤溫度計、極端漲跌 / 強於大盤族群、資金流向
│   ├── charts_strategy.py  # 選股清單圖、族群圖、K 線圖 (策略共用)
│   ├── strategies.py       # 策略 2 ~ 4
│   ├── charts_volume.py    # 量增 / 量縮排行、價量四象限
│   ├── charts_price.py     # 價位強弱排行
│   └── report_custom.py    # 自訂名單乖離率監控 Excel
└── stock_data/             # 輸出 (已加入 .gitignore)
    └── YYYY-MM-DD/
        ├── source/                     # 每檔原始日 K (CSV)
        ├── TW_Stock_Report_*.xlsx      # 全市場主報表
        ├── 自訂名單_技術指標監控表_*.xlsx  # 分頁: 技術指標監控 / 進出場機會 / 族群強弱追蹤
        ├── 大盤/        # Market_Temperature / Market_Extremes / Market_Outperform / Capital_Flow
        ├── 量能/        # Volume_Surge_Rank / Volume_Shrink_Rank / Volume_Matrix / Volume_Price_Quadrant
        ├── 價位/        # Price_Strong_Rank / Price_Weak_Rank / Price_Matrix_Dashboard
        ├── 策略1/  策略2-均線/  策略3-長紅爆量/  策略4-均線糾結突破/   # 選股清單、族群圖、K 線圖
```

## 執行流程

1. **取得清單**：TWSE / TPEx OpenAPI 取得上市櫃代號與名稱；`data/stock_list.xlsx` 取得細產業。
2. **下載資料**：yfinance 批次下載（`DOWNLOAD_CHUNK_SIZE` 檔一批、`DOWNLOAD_WORKERS` 路並行，可輪替 `PROXIES`），失敗或最後一天不完整者逐檔重試。
   - **休市日處理**：Yahoo 會在休市日補一筆「量=0、價=前收」的假資料。程式把 ^TWII 存成 `source/^TWII.csv` 當交易日曆，讀檔時剔除「不在日曆內且量=0」的列；最新資料日落後的股票（停牌）不納入策略與排行，只保留在主報表。
3. **計算指標**：MA、MV、N 日漲幅、趨勢、策略 1/2 條件。
4. **大盤基準**：^TWII 的 N 日漲跌幅。
5. **平行產出報表**：以下任務互不相依，用 `PLOT_WORKERS` 個程序同時執行。

| 類別 | 內容 |
|---|---|
| 大盤 | 漲跌幅分佈溫度計、極端漲跌族群、強於大盤族群、細產業資金流向 |
| 策略1 | 量增、量能多頭、站上所有 MA、成交值 > 2 億、收紅（條件可在 `STRATEGY1_CONDITIONS` 勾選） |
| 策略2-均線 | 均線趨勢向上、成交值門檻、站上且接近最大均線 |
| 策略3-長紅爆量 | 實體長紅 > 4%、量 > 昨量 2 倍、幾乎收最高、成交值 > 1 億 |
| 策略4-均線糾結突破 | 5/10/20MA 糾結 < 2.5%、量 > 5 日均量 1.5 倍、漲幅 1.5%~6.5%、成交值 > 1.5 億 |
| 量能 | 1/3/5/10/20 日量增、量縮排行，價量四象限儀表板 |
| 價位 | 1/3/5/20 日強勢、弱勢排行 |
| 自訂名單 | 讀取 `data/stock_SB/*.txt`，輸出乖離率、出現紀錄、族群強弱 Excel |

## 常用設定 (`config.py`)

| 參數 | 說明 |
|---|---|
| `DOWNLOAD_CHUNK_SIZE` / `DOWNLOAD_WORKERS` | 每批檔數 / 同時批次數。常抓不到資料就調低 |
| `PROXIES` | proxy 清單，批次輪流使用，例如 `["http://user:pass@host:port", None]`（`None` = 直連） |
| `PLOT_WORKERS` | 平行繪圖程序數，設 `1` 依序執行（方便除錯） |
| `ITALIC_STOCK_ID` | 族群圖股號斜體；開啟後大型族群圖約慢 1 倍 |
| `MA_SETTINGS`、`TREND_SETTINGS`、`VOLUME_RANK_DAYS`… | 各指標天數 |
| `STRATEGY*_SETTINGS` | 各策略門檻 |

## 效能 (約 2,000 檔，16 核 WSL)

| 項目 | 重構前 | 重構後 |
|---|---|---|
| 下載 (全部重抓) | ~0.16 秒/檔 ≈ 5.5 分 | ~0.06 秒/檔 ≈ 1.5–2 分 |
| 計算 + 產出報表 (資料已在本機) | 2 分 33 秒 | 約 46–50 秒 |
