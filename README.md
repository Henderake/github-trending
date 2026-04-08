# GitHub Trending Report

Generate a static GitHub Trending report and publish it with GitHub Pages.

## What This Repo Does

This project fetches GitHub Trending repositories for:

- All languages
- C
- C++
- Python

Across these time ranges:

- Today
- This Week
- This Month

The crawler outputs a static site:

- `index.html`
- `report.css`
- `report.js`

Generated files belong in `dist/` and should not be committed.

## Local Usage

Create a virtual environment, install dependencies, and generate a report:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python crawl.py --output dist/index.html
```

Generated files will be written to `dist/`.

Quick smoke test:

```bash
python crawl.py --output dist/index.html --limit 1 --pause 0
python -m py_compile crawl.py
```

## GitHub Pages Deployment

This repo is configured to deploy with GitHub Actions using:

- [.github/workflows/deploy-github-pages.yml](/home/henderake/github-trending/.github/workflows/deploy-github-pages.yml)

To enable it:

1. Push this repository to GitHub.
2. Open `Settings > Pages`.
3. Set the source to `GitHub Actions`.
4. Go to `Actions` and run `Deploy GitHub Pages` once manually.

After deployment, the site will be available at:

```text
https://<your-username>.github.io/github-trending/
```

## Automatic Updates

The workflow runs every day on this UTC schedule:

```text
17 2 * * *
```

It does not create a daily commit. Instead, GitHub Actions:

1. Installs dependencies
2. Runs `crawl.py`
3. Uploads the generated `dist/` folder
4. Deploys it directly to GitHub Pages

The `Generated at` label is stored in UTC and rendered in each visitor's local browser time zone.

## Notes

- Keep the repo public if you want to use GitHub Pages on GitHub Free.
- Even if the repository is private on a paid plan, the published Pages site is still public unless you are using GitHub Enterprise features for restricted visibility.
