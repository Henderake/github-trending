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
import re
import time
import urllib.parse
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://github.com/trending"
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


def fetch_trending(language: str, since: str, session: requests.Session, limit: Optional[int]) -> List[Repo]:
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

        # GitHub regularly changes the exact class list/order on description paragraphs.
        # Prefer resilient CSS selectors and fall back to the first non-empty <p>.
        desc_tag = (
            article.select_one("p.col-9.color-fg-muted.my-1.pr-4")
            or article.select_one("p.col-9.color-fg-muted.my-1")
            or article.select_one("p.color-fg-muted.my-1")
            or article.select_one("p.my-1")
        )
        if not desc_tag:
            desc_tag = next((p for p in article.find_all("p") if p.get_text(" ", strip=True)), None)
        description = desc_tag.get_text(" ", strip=True) if desc_tag else ""

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


def render_report(results: Dict[str, Dict[str, List[Repo]]], generated_at: dt.datetime) -> str:
    def anchor_id(since: str, language: str) -> str:
        raw = f"{since}-{language}".lower().replace("+", "plus").replace(" ", "-")
        return re.sub(r"[^a-z0-9-]", "", raw)

    def render_repo(repo: Repo) -> str:
        meta_parts = [
            f"⭐ {repo.stars}",
            f"🍴 {repo.forks}",
            f"⬆ {repo.stars_period} this period",
        ]
        if repo.language:
            meta_parts.append(repo.language)

        description_html = f"<div class='description'>{repo.description}</div>" if repo.description else ""
        return (
            "<li>"
            f"<a href='{repo.url}'>{repo.name}</a>"
            f"<div class='meta'>{' • '.join(meta_parts)}</div>"
            f"{description_html}"
            "</li>"
        )

    generated_str = generated_at.strftime("%Y-%m-%d %H:%M:%S %Z").strip()
    sidebar_links = []
    html_parts = [
        "<!doctype html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='utf-8' />",
        "<meta name='viewport' content='width=device-width, initial-scale=1' />",
        "<title>GitHub Trending Report</title>",
        "<style>",
        "html { scroll-behavior: smooth; }",
        "body { font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; margin: 0 auto; max-width: 1280px; padding: 24px; background: #0b1726; color: #e2e8f0; position: relative; overflow-x: hidden; }",
        "body::before { content: ''; position: fixed; inset: 0; pointer-events: none; background: radial-gradient(110% 130% at 18% 18%, rgba(0,194,255,0.1), transparent 42%), linear-gradient(160deg, rgba(11,28,44,0.98) 0%, rgba(15,39,58,0.96) 45%, rgba(11,23,38,0.94) 100%); z-index: -1; }",
        "h1 { margin-bottom: 0; letter-spacing: 0.02em; color: #f8fafc; }",
        "h2 { margin-top: 32px; border-bottom: 2px solid #102a44; padding-bottom: 6px; color: #c2e6ff; text-shadow: 0 0 12px rgba(0,194,255,0.25); }",
        ".generated { color: #94a3b8; margin-bottom: 16px; }",
        ".lang-section { margin-bottom: 20px; padding: 12px; border: 1px solid #112233; border-radius: 10px; background: linear-gradient(135deg, rgba(16,42,68,0.95), rgba(12,26,44,0.9)); box-shadow: inset 0 0 0 1px rgba(255,255,255,0.03), 0 12px 30px rgba(0,0,0,0.35); }",
        ".lang-title { font-weight: 700; margin: 12px 0 6px; color: #cbd5e1; letter-spacing: 0.01em; }",
        "ul { list-style: none; padding: 0; margin: 0; }",
        "li { background: rgba(17,34,51,0.55); border: 1px solid #1b2f47; border-radius: 10px; padding: 12px; margin-bottom: 10px; box-shadow: 0 10px 28px rgba(0,0,0,0.35); }",
        "li a { font-weight: 700; color: #75d7ff; text-decoration: none; text-shadow: 0 0 10px rgba(0,194,255,0.2); }",
        "li a:hover { color: #a8e7ff; }",
        ".meta { color: #94a3b8; font-size: 14px; margin-top: 4px; }",
        ".description { margin-top: 6px; color: #cbd5e1; }",
        ".empty { color: #718096; font-style: italic; }",
        ".layout { display: grid; grid-template-columns: 280px 1fr; gap: 20px; align-items: start; }",
        ".sidebar { position: sticky; top: 16px; border-radius: 12px; padding: 14px; background: linear-gradient(180deg, #0f1d2d 0%, #0b1726 100%); box-shadow: 0 18px 40px rgba(0,0,0,0.45), inset 0 0 0 1px #15263a; border: 1px solid #0a1929; max-height: calc(100vh - 32px); overflow-y: auto; }",
        ".sidebar-title { font-weight: 800; margin-bottom: 12px; letter-spacing: 0.08em; text-transform: uppercase; font-size: 12px; color: #8ab7d8; display: flex; align-items: center; gap: 8px; }",
        ".sidebar-title::before { content: '●'; color: #00c2ff; text-shadow: 0 0 12px #00c2ff; }",
        ".sidebar ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }",
        ".group { display: grid; gap: 6px; }",
        ".group-toggle { width: 100%; background: linear-gradient(90deg, rgba(13,32,50,0.95), rgba(18,46,72,0.9)); border: 1px solid #1b3048; color: #e2e8f0; padding: 10px 12px; border-radius: 10px; text-align: left; font-weight: 800; letter-spacing: 0.04em; cursor: pointer; display: flex; align-items: center; justify-content: space-between; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02); transition: border-color 140ms ease, color 140ms ease, transform 120ms ease; }",
        ".group-toggle:hover { border-color: #1f3a55; transform: translateX(2px); }",
        ".group-toggle .caret { color: #00c2ff; text-shadow: 0 0 10px rgba(0,194,255,0.3); }",
        ".submenu { list-style: none; margin: 0; padding: 0 0 0 4px; display: grid; gap: 6px; max-height: 800px; overflow: hidden; transition: max-height 180ms ease; }",
        ".submenu.closed { max-height: 0; }",
        ".sidebar a { color: #cbd5e1; text-decoration: none; font-size: 14px; display: block; padding: 10px 12px; border-radius: 10px; border: 1px solid #142437; background: linear-gradient(90deg, rgba(13,32,50,0.9), rgba(12,26,44,0.85)); box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02); transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease, color 140ms ease; }",
        ".sidebar a:hover { transform: translateX(2px); border-color: #1f3a55; color: #e8f4ff; box-shadow: 0 8px 20px rgba(0,194,255,0.15); }",
        ".sidebar a.active { border-color: #00c2ff; box-shadow: 0 12px 28px rgba(0,194,255,0.25), inset 0 0 0 1px rgba(0,194,255,0.25); color: #f8fbff; background: linear-gradient(90deg, rgba(0,194,255,0.25), rgba(10,102,194,0.35)); }",
        ".toggle-btn { display: none; margin: 12px 0; padding: 11px 16px; border-radius: 10px; border: 1px solid #102a44; background: linear-gradient(135deg, #12345a, #0d2a46); color: #e2e8f0; font-weight: 700; cursor: pointer; box-shadow: 0 10px 24px rgba(0,0,0,0.35); }",
        ".toggle-btn:active { transform: translateY(1px); }",
        ".content { backdrop-filter: blur(4px); }",
        "@media (max-width: 900px) {",
        "  .layout { grid-template-columns: 1fr; }",
        "  .sidebar { display: none; position: static; max-height: 70vh; }",
        "  .sidebar.open { display: block; }",
        "  .toggle-btn { display: inline-flex; align-items: center; gap: 8px; }",
        "}",
        "</style>",
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
            "<script>",
            "const toggleBtn = document.getElementById('sidebar-toggle');",
            "const sidebar = document.getElementById('sidebar');",
            "let lockHighlightUntil = 0;",
            "let lockTimer;",
            "toggleBtn?.addEventListener('click', () => {",
            "  const open = sidebar.classList.toggle('open');",
            "  toggleBtn.setAttribute('aria-expanded', String(open));",
            "});",
            "const links = Array.from(document.querySelectorAll('.sidebar a[data-target]'));",
            "const sections = links.map(l => document.getElementById(l.dataset.target)).filter(Boolean);",
            "const groupToggles = Array.from(document.querySelectorAll('.group-toggle'));",
            "const setActive = id => {",
            "  links.forEach(l => {",
                "    const isActive = l.dataset.target === id;",
                "    l.classList.toggle('active', isActive);",
                "    if (isActive) {",
                "      const groupId = l.dataset.group;",
                "      const submenu = document.getElementById(groupId);",
                "      const btn = document.querySelector(`.group-toggle[data-group='${groupId}']`);",
                "      submenu?.classList.remove('closed');",
                "      btn?.setAttribute('aria-expanded', 'true');",
                "      const caret = btn?.querySelector('.caret');",
                "      if (caret) caret.textContent = '▾';",
                "    }",
                "  });",
            "};",
            "groupToggles.forEach(btn => {",
                "  const target = document.getElementById(btn.dataset.group);",
                "  const caret = btn.querySelector('.caret');",
                "  btn.addEventListener('click', () => {",
                "    const closed = target.classList.toggle('closed');",
                "    btn.setAttribute('aria-expanded', String(!closed));",
                "    if (caret) caret.textContent = closed ? '▸' : '▾';",
                "  });",
            "});",
            "document.querySelectorAll('.sidebar a').forEach(link => {",
                "  link.addEventListener('click', () => {",
                "    const targetId = link.dataset.target;",
                "    setActive(targetId);",
                "    lockHighlightUntil = Date.now() + 1500; // keep highlight fixed during smooth scroll",
                "    clearTimeout(lockTimer);",
                "    lockTimer = setTimeout(() => { lockHighlightUntil = 0; updateActiveByScroll(); }, 1550);",
                "    sidebar.classList.remove('open');",
                "    toggleBtn.setAttribute('aria-expanded', 'false');",
                "  });",
            "});",
            "const updateActiveByScroll = () => {",
            "  if (Date.now() < lockHighlightUntil) return;",
            "  const targetLine = window.innerHeight * 0.35;",
            "  let bestId = sections[0]?.id;",
            "  let bestScore = Infinity;",
            "  sections.forEach(sec => {",
            "    const rect = sec.getBoundingClientRect();",
            "    const withinView = rect.bottom > 60 && rect.top < window.innerHeight * 0.75;",
            "    if (withinView) {",
            "      const score = Math.abs(rect.top - targetLine);",
            "      if (score < bestScore) {",
            "        bestScore = score;",
            "        bestId = sec.id;",
            "      }",
            "    }",
            "  });",
            "  if (bestId) setActive(bestId);",
            "};",
            "window.addEventListener('scroll', updateActiveByScroll, { passive: true });",
            "window.addEventListener('resize', updateActiveByScroll);",
            "updateActiveByScroll();",
            "</script>",
            "</body>",
            "</html>",
        ]
    )
    return "\n".join(html_parts)


def build_report(output: str, limit: Optional[int], pause: float) -> None:
    session = requests.Session()
    results: Dict[str, Dict[str, List[Repo]]] = {}

    for since, _ in SINCE_OPTIONS:
        results[since] = {}
        for language in LANGUAGES:
            repos = fetch_trending(language, since, session, limit)
            results[since][language] = repos
            if pause:
                time.sleep(pause)

    html = render_report(results, dt.datetime.now())
    with open(output, "w", encoding="utf-8") as fp:
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
