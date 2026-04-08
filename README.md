# GitHub Trending Report

這個專案會抓取 GitHub Trending 資料，產生靜態報表，並透過 GitHub Pages 發佈。

## 專案用途

目前會抓取以下語言的 Trending repositories：

- All languages
- C
- C++
- Python

並涵蓋以下時間範圍：

- Today
- This Week
- This Month

crawler 會輸出一組靜態網站檔案：

- `index.html`
- `report.css`
- `report.js`

這些產生物會放在 `dist/`，不應提交到版本控制。

## 本機使用方式

先建立虛擬環境、安裝相依套件，再產生報表：

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python crawl.py --output dist/index.html
```

產生完成後，檔案會寫入 `dist/`。

快速 smoke test：

```bash
python crawl.py --output dist/index.html --limit 1 --pause 0
python -m py_compile crawl.py
```

## GitHub Pages 部署

本 repo 已設定好 GitHub Actions workflow：

- `.github/workflows/deploy-github-pages.yml`

啟用方式如下：

1. 將這個 repo push 到 GitHub。
2. 打開 `Settings > Pages`。
3. 將 source 設為 `GitHub Actions`。
4. 到 `Actions` 頁面手動執行一次 `Deploy GitHub Pages`。

部署完成後，網站網址會是：

```text
https://<your-username>.github.io/github-trending/
```

## 自動更新

workflow 每天會在以下 UTC 時間自動執行：

```text
17 2 * * *
```

這個流程不會每天建立新的 commit，而是由 GitHub Actions：

1. 安裝相依套件
2. 執行 `crawl.py`
3. 上傳 `dist/` 產生物
4. 直接部署到 GitHub Pages

頁面上的 `Generated at` 會先以 UTC 寫入，再由瀏覽器轉換成訪客的本地時區顯示。

## 補充說明

- 如果你使用 GitHub Free，repo 需為 public 才能使用 GitHub Pages。
- 即使 repo 在付費方案下設為 private，公開的 GitHub Pages 網址通常仍然是對外可存取的，除非你使用 GitHub Enterprise 的受限可見性功能。
