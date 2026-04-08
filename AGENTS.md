# Repository Guidelines

## 專案結構與模組說明

此 repo 以單一 Python crawler 為核心，結構保持精簡：

- `crawl.py`：抓取 GitHub Trending、組裝 HTML、複製靜態資產。
- `assets/report.css`：報表樣式。
- `assets/report.js`：前端互動與本地時區時間顯示。
- `requirements.txt`：Python 相依套件。
- `.github/workflows/deploy-github-pages.yml`：GitHub Pages 自動部署流程。
- `dist/`：產生後的靜態輸出，包含 `index.html`、`report.css`、`report.js`，不應提交。

目前沒有獨立 `tests/` 目錄；驗證以本地 smoke test 為主。

## 建置、測試與開發指令

建立本地環境：

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

產生完整報表：

```bash
python crawl.py --output dist/index.html
```

快速驗證：

```bash
python crawl.py --output dist/index.html --limit 1 --pause 0
python -m py_compile crawl.py
```

第一個指令檢查語法，第二個指令確認 `dist/` 內的靜態檔可正常產生。

## 程式風格與命名慣例

- Python 使用 4 個空白縮排。
- 函式與變數使用 `snake_case`。
- 常數使用 `UPPER_SNAKE_CASE`。
- 優先延續現有的簡單函式拆分，不引入不必要抽象。
- CSS / JS 維持原生靜態檔，不為小改動加入框架或打包工具。

目前沒有 formatter 或 linter 設定；提交前至少確保語法可編譯、輸出可生成。

## 測試指南

目前沒有 pytest 或單元測試框架，也沒有 coverage 門檻。提交前至少完成：

- 執行 `python -m py_compile crawl.py`
- 執行一次本地生成到 `dist/`
- 檢查側邊欄互動、時間顯示、CSS/JS 載入是否正常

如果修改抓取邏輯，請至少用 `--limit 1 --pause 0` 做一次快速 smoke test。

## Commit 與 Pull Request 規範

既有 commit 訊息偏向簡短祈使句，例如 `Fix description`、`Add GitHub Pages deployment workflow`。請遵循：

- 標題簡短，聚焦單一變更
- crawler、部署、文件變更盡量分開提交
- PR 需說明使用者可見影響與部署影響
- 若有 UI 變動，附上截圖

## 安全與設定提醒

不要提交 token、密碼、私鑰或產生物。一般 GitHub Pages 發佈不需要把 credentials 寫進 repo；敏感資料一律放在 GitHub Secrets 或本機環境中。
