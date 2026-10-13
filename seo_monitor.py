#!/usr/bin/env python3
"""Read-only technical SEO and known-backlink audit for An Phuoc Realty."""
import csv
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parent
USER_AGENT = "AnPhuocSEOAudit/1.0 (+https://anphuocrealty.vn)"

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.h1 = []
        self.description = ""
        self.canonical = ""
        self.robots = ""
        self.links = []
        self._title = False
        self._h1 = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._title = True
        if tag == "h1":
            self._h1 = True
        if tag == "meta" and attrs.get("name", "").lower() == "description":
            self.description = attrs.get("content", "")
        if tag == "meta" and attrs.get("name", "").lower() == "robots":
            self.robots = attrs.get("content", "")
        if tag == "link" and "canonical" in attrs.get("rel", "").lower():
            self.canonical = attrs.get("href", "")
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._title = False
        if tag == "h1":
            self._h1 = False

    def handle_data(self, data):
        if self._title:
            self.title += data
        if self._h1 and data.strip():
            self.h1.append(data.strip())

def fetch(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xml,text/plain;q=0.9,*/*;q=0.1",
    })
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.geturl(), response.read(1200000).decode("utf-8", "replace"), ""
    except urllib.error.HTTPError as exc:
        return exc.code, url, "", str(exc)
    except Exception as exc:
        return None, url, "", str(exc)

def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def write_csv(path, records, columns):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)

def parse_html(html):
    parser = PageParser()
    try:
        parser.feed(html)
    except Exception:
        pass
    return parser

def main():
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    targets = [row["url"].strip() for row in read_csv(ROOT / "data" / "target_urls.csv") if row.get("url", "").strip()]
    domain = urlparse(targets[0]).netloc if targets else "anphuocrealty.vn"
    targets.extend([f"https://{domain}/robots.txt", f"https://{domain}/sitemap.xml"])
    pages = []
    for url in dict.fromkeys(targets):
        status, final_url, html, error = fetch(url)
        is_resource = urlparse(url).path.endswith((".txt", ".xml"))
        parser = parse_html(html) if html and not is_resource else PageParser()
        issues = []
        if status != 200:
            issues.append(f"HTTP {status or error}")
        if not is_resource and status == 200:
            if not parser.title.strip():
                issues.append("Missing title")
            if not parser.description.strip():
                issues.append("Missing meta description")
            if not parser.h1:
                issues.append("Missing H1")
            if "đang tải bài viết" in html.lower():
                issues.append("Potential JS-only article")
            if "không tìm thấy bài viết" in html.lower():
                issues.append("Soft 404 candidate")
            if "noindex" in parser.robots.lower():
                issues.append("Noindex")
        pages.append({
            "url": url, "status": status or "", "final_url": final_url,
            "title": parser.title.strip(), "h1": " | ".join(parser.h1),
            "description": parser.description, "canonical": parser.canonical,
            "issues": "; ".join(issues), "error": error,
        })

    backlinks = []
    for row in read_csv(ROOT / "data" / "backlinks.csv"):
        source = row.get("source_url", "").strip()
        target = row.get("target_url", "").strip()
        if not source:
            continue
        status, final_url, html, error = fetch(source)
        parser = parse_html(html) if html else PageParser()
        hrefs = {urljoin(final_url, href).split("#")[0].rstrip("/") for href in parser.links}
        present = bool(target and target.split("#")[0].rstrip("/") in hrefs)
        backlinks.append({
            "source_url": source, "target_url": target,
            "status": status or "", "link_found": present, "error": error,
        })

    write_csv(reports / "technical_audit.csv", pages,
              ["url", "status", "final_url", "title", "h1", "description", "canonical", "issues", "error"])
    write_csv(reports / "backlink_audit.csv", backlinks,
              ["source_url", "target_url", "status", "link_found", "error"])
    summary = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "pages_checked": len(pages),
        "pages_with_issues": sum(bool(page["issues"]) for page in pages),
        "backlinks_checked": len(backlinks),
        "backlinks_found": sum(row["link_found"] for row in backlinks),
    }
    (reports / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
