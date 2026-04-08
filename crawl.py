#!/usr/bin/env python3
"""
Fetch GitHub Trending for selected languages/time ranges and build an HTML report.

Filters covered:
- Languages: Any, C, C++, Python
- Date ranges: today, this week, this month

Dependencies: requests, beautifulsoup4
Usage: python crawl.py --output report.html
"""

from __future__ import annotations

import argparse
import datetime as dt
import html as html_utils
import re
import shutil
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://github.com/trending"
BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = BASE_DIR / "assets"
REPORT_CSS_FILENAME = "report.css"
REPORT_JS_FILENAME = "report.js"
HEADERS = {
    # Use a typical browser UA to mirror normal browsing behavior.
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

LANGUAGES = ["Any", "C", "C++", "Python"]
SINCE_OPTIONS = [
    ("daily", "Today"),
    ("weekly", "This Week"),
    ("monthly", "This Month"),
]


@dataclass
class Repo:
    name: str
    url: str
    description: str
    language: Optional[str]
    stars: int
    forks: int
    stars_period: int


def normalize_description(text: str) -> str:
    """Normalize and filter low-signal fallback description text."""
    cleaned = " ".join(text.split()).strip()
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if lowered.startswith("contribute to ") and " by creating an account on github" in lowered:
        return ""
    if lowered.startswith("github is where"):
        return ""
    return cleaned


def fetch_repo_description(url: str, session: requests.Session, cache: Dict[str, str]) -> str:
    """Fetch description from the repository page metadata as a fallback."""
    cached = cache.get(url)
    if cached is not None:
        return cached

    description = ""
    try:
        response = session.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for selector in (
            "meta[property='og:description']",
            "meta[name='description']",
            "p.f4.my-3",
        ):
            tag = soup.select_one(selector)
            if not tag:
                continue
            text = tag.get("content", "").strip() if tag.name == "meta" else tag.get_text(" ", strip=True)
            description = normalize_description(text)
            if description:
                break
    except requests.RequestException:
        description = ""

    cache[url] = description
    return description


def extract_article_description(article) -> str:
    """Extract repository description from a trending card."""
    desc_tag = (
        article.select_one("p.col-9.color-fg-muted.my-1.pr-4")
        or article.select_one("p.col-9.color-fg-muted.my-1.tmp-pr-4")
        or article.select_one("p.col-9.color-fg-muted.my-1")
        or article.select_one("p.color-fg-muted.my-1")
        or article.select_one("p.my-1")
    )
    if not desc_tag:
        desc_tag = next((p for p in article.find_all("p") if p.get_text(" ", strip=True)), None)
    return normalize_description(desc_tag.get_text(" ", strip=True) if desc_tag else "")


def parse_count(raw: str) -> int:
    """Convert GitHub-style number strings (e.g. 1.2k, 900) to integers."""
    if not raw:
        return 0
    match = re.search(r"([\d,.]+)([kKmM]?)", raw.replace(",", "").strip())
    if not match:
        return 0
    number = float(match.group(1))
    suffix = match.group(2).lower()
    if suffix == "k":
        number *= 1_000
    elif suffix == "m":
        number *= 1_000_000
    return int(number)


def fetch_trending(
    language: str,
    since: str,
    session: requests.Session,
    limit: Optional[int],
    description_cache: Dict[str, str],
) -> List[Repo]:
    params = {"since": since}
    if language != "Any":
        params["l"] = language
    response = session.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    repos: List[Repo] = []

    for article in soup.select("article.Box-row"):
        name_link = article.h2.find("a")
        repo_path = name_link["href"].strip()
        repo_name = repo_path.lstrip("/")
        url = urllib.parse.urljoin("https://github.com", repo_path)

        description = extract_article_description(article)
        if not description:
            description = fetch_repo_description(url, session, description_cache)

        language_tag = article.find("span", itemprop="programmingLanguage")
        repo_language = language_tag.get_text(strip=True) if language_tag else None

        star_tag = article.find("a", href=lambda href: href and href.endswith("/stargazers"))
        fork_tag = article.find("a", href=lambda href: href and href.endswith("/network/members"))
        period_tag = article.find("span", class_=lambda c: c and "float-sm-right" in c)

        stars = parse_count(star_tag.get_text(strip=True)) if star_tag else 0
        forks = parse_count(fork_tag.get_text(strip=True)) if fork_tag else 0

        stars_period = 0
        if period_tag:
            stars_period = parse_count(period_tag.get_text())

        repos.append(
            Repo(
                name=repo_name,
                url=url,
                description=description,
                language=repo_language,
                stars=stars,
                forks=forks,
                stars_period=stars_period,
            )
        )

        if limit and len(repos) >= limit:
            break

    return repos


def copy_report_assets(output_path: Path) -> None:
    """Copy static report assets next to the generated HTML file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    for filename in (REPORT_CSS_FILENAME, REPORT_JS_FILENAME):
        source = ASSET_DIR / filename
        if not source.exists():
            raise FileNotFoundError(f"Missing asset file: {source}")
        shutil.copy2(source, output_path.parent / filename)


def render_report(
    results: Dict[str, Dict[str, List[Repo]]],
    generated_at: dt.datetime,
    stylesheet_href: str = REPORT_CSS_FILENAME,
    script_src: str = REPORT_JS_FILENAME,
) -> str:
    def anchor_id(since: str, language: str) -> str:
        raw = f"{since}-{language}".lower().replace("+", "plus").replace(" ", "-")
        return re.sub(r"[^a-z0-9-]", "", raw)

    def render_repo(repo: Repo) -> str:
        safe_url = html_utils.escape(repo.url, quote=True)
        safe_name = html_utils.escape(repo.name)
        meta_parts = [
            f"⭐ {repo.stars}",
            f"🍴 {repo.forks}",
            f"⬆ {repo.stars_period} this period",
        ]
        if repo.language:
            meta_parts.append(html_utils.escape(repo.language))

        description_text = repo.description or "No description provided."
        description_html = f"<div class='description'>{html_utils.escape(description_text)}</div>"
        return (
            "<li>"
            f"<a href='{safe_url}'>{safe_name}</a>"
            f"<div class='meta'>{' • '.join(meta_parts)}</div>"
            f"{description_html}"
            "</li>"
        )

    generated_str = generated_at.strftime("%Y-%m-%d %H:%M:%S %Z").strip()
    sidebar_links = []
    safe_stylesheet_href = html_utils.escape(stylesheet_href, quote=True)
    safe_script_src = html_utils.escape(script_src, quote=True)
    html_parts = [
        "<!doctype html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='utf-8' />",
        "<meta name='viewport' content='width=device-width, initial-scale=1' />",
        "<title>GitHub Trending Report</title>",
        f"<link rel='stylesheet' href='{safe_stylesheet_href}' />",
        "</head>",
        "<body>",
        "<h1>GitHub Trending Report</h1>",
        f"<div class='generated'>Generated at {generated_str}</div>",
        "<button id='sidebar-toggle' class='toggle-btn' aria-expanded='false'>☰ Categories</button>",
        "<div class='layout'>",
        "<aside class='sidebar' id='sidebar'>",
        "<div class='sidebar-title'>Jump to</div>",
        "<ul>",
    ]

    for since, label in SINCE_OPTIONS:
        group_id = f"group-{since}"
        html_parts.append("<li class='group'>")
        html_parts.append(f"<button class='group-toggle' data-group='{group_id}' aria-expanded='true'>{label}<span class='caret'>▾</span></button>")
        html_parts.append(f"<ul id='{group_id}' class='submenu'>")
        for language in LANGUAGES:
            display_language = "All languages" if language == "Any" else language
            section_id = anchor_id(since, language)
            html_parts.append(f"<li><a href='#{section_id}' data-target='{section_id}' data-group='{group_id}'>{display_language}</a></li>")
            sidebar_links.append((label, display_language, section_id, group_id))
        html_parts.append("</ul>")
        html_parts.append("</li>")

    html_parts.extend(
        [
            "</ul>",
            "</aside>",
            "<main class='content'>",
        ]
    )

    for since, label in SINCE_OPTIONS:
        html_parts.append(f"<h2 id='{since}'>{label}</h2>")
        for language in LANGUAGES:
            display_language = "All languages" if language == "Any" else language
            section_id = anchor_id(since, language)
            repos = results.get(since, {}).get(language, [])
            html_parts.append(f"<div class='lang-section' id='{section_id}'>")
            html_parts.append(f"<div class='lang-title'>{display_language}</div>")
            if repos:
                html_parts.append("<ul>")
                html_parts.extend(render_repo(repo) for repo in repos)
                html_parts.append("</ul>")
            else:
                html_parts.append("<div class='empty'>No repositories found.</div>")
            html_parts.append("</div>")

    html_parts.extend(
        [
            "</main>",
            "</div>",
            f"<script src='{safe_script_src}' defer></script>",
            "</body>",
            "</html>",
        ]
    )
    return "\n".join(html_parts)


def build_report(output: str, limit: Optional[int], pause: float) -> None:
    session = requests.Session()
    results: Dict[str, Dict[str, List[Repo]]] = {}
    description_cache: Dict[str, str] = {}
    output_path = Path(output)

    for since, _ in SINCE_OPTIONS:
        results[since] = {}
        for language in LANGUAGES:
            repos = fetch_trending(language, since, session, limit, description_cache)
            results[since][language] = repos
            if pause:
                time.sleep(pause)

    copy_report_assets(output_path)
    html = render_report(results, dt.datetime.now())
    with output_path.open("w", encoding="utf-8") as fp:
        fp.write(html)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an HTML report of GitHub Trending repositories.")
    parser.add_argument("--output", "-o", default="trending-report.html", help="Path to write the HTML report.")
    parser.add_argument("--limit", "-n", type=int, default=25, help="Max repos per language/time range (default: 25).")
    parser.add_argument("--pause", "-p", type=float, default=0.5, help="Seconds to pause between requests.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        build_report(args.output, args.limit, args.pause)
    except requests.RequestException as exc:
        raise SystemExit(f"Failed to fetch Trending data: {exc}")
    print(f"Wrote report to {args.output}")


if __name__ == "__main__":
    main()
