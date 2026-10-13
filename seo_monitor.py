#!/usr/bin/env python3
"""Read-only technical SEO and known-backlink audit for An Phuoc Realty."""
import csv
import json
import os
import time
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit

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

def normalized_url(value):
    """Normalize only URL formatting, not distinct slugs or file extensions."""
    try:
        parts = urlsplit(value)
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                          parts.path.rstrip("/") or "/", "", ""))
    except Exception:
        return value

def render_markdown(pages, backlinks):
    lines = ["# Báo cáo SEO An Phước Realty", "",
             "Báo cáo máy tự động; cần kiểm chứng các cảnh báo trước khi sửa website.", "",
             "## Các URL cần xử lý", ""]
    flagged = [p for p in pages if p["issues"]]
    if not flagged:
        lines.append("Không phát hiện vấn đề theo bộ tiêu chí hiện tại.")
    for p in flagged:
        lines.extend([f"### {p['url']}", f"- HTTP: {p['status']}",
                      f"- Vấn đề: {p['issues']}", ""])
    lines.extend(["## Backlink", "",
                  f"Đã kiểm tra {len(backlinks)} backlink được khai báo. "
                  "Danh sách trống không có nghĩa website không có backlink.", ""])
    return "\n".join(lines)

def discover_sitemap_urls(domain, limit=150):
    """Find same-host HTML URLs in sitemap indexes and urlsets."""
    origin = f"https://{domain}"
    queue = [origin + "/sitemap.xml", origin + "/wp-sitemap.xml"]
    seen_maps = set()
    found = []
    found_set = set()
    errors = []
    while queue and len(seen_maps) < 20 and len(found) < limit:
        sitemap = queue.pop(0)
        if sitemap in seen_maps or urlparse(sitemap).netloc != domain:
            continue
        seen_maps.add(sitemap)
        status, _, body, error = fetch(sitemap)
        if status != 200:
            errors.append(f"{sitemap}: HTTP {status or error}")
            continue
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            errors.append(f"{sitemap}: invalid XML")
            continue
        tag = root.tag.rsplit("}", 1)[-1].lower()
        if tag == "sitemapindex":
            for item in root:
                if item.tag.rsplit("}", 1)[-1].lower() != "sitemap":
                    continue
                loc = next((node.text.strip() for node in item
                            if node.tag.rsplit("}", 1)[-1].lower() == "loc" and node.text), "")
                if loc and urlparse(loc).netloc == domain and loc not in seen_maps:
                    queue.append(loc)
        elif tag == "urlset":
            for item in root:
                if item.tag.rsplit("}", 1)[-1].lower() != "url":
                    continue
                loc = next((node.text.strip() for node in item
                            if node.tag.rsplit("}", 1)[-1].lower() == "loc" and node.text), "")
                if not loc:
                    continue
                parsed = urlparse(loc)
                if parsed.scheme not in ("https", "http") or parsed.netloc != domain:
                    continue
                if parsed.path.lower().endswith((".jpg", ".png", ".jpeg", ".webp", ".gif", ".pdf", ".xml")):
                    continue
                if loc not in found_set:
                    found_set.add(loc)
                    found.append(loc)
                    if len(found) >= limit:
                        break
        else:
            errors.append(f"{sitemap}: unsupported XML root {tag}")
    return found, errors, len(seen_maps)

def main():
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    targets = [row["url"].strip() for row in read_csv(ROOT / "data" / "target_urls.csv") if row.get("url", "").strip()]
    domain = urlparse(targets[0]).netloc if targets else "anphuocrealty.vn"
    max_pages = max(1, min(int(os.getenv("SEO_MAX_PAGES", "150")), 500))
    sitemap_urls, sitemap_errors, sitemaps_scanned = discover_sitemap_urls(domain, limit=max_pages)
    targets = list(dict.fromkeys(targets + sitemap_urls))[:max_pages]
    targets.extend([f"https://{domain}/robots.txt", f"https://{domain}/sitemap.xml"])
    print(f"Discovered {len(sitemap_urls)} URLs in {sitemaps_scanned} sitemaps; errors: {len(sitemap_errors)}")
    pages = []
    for url in dict.fromkeys(targets):
        time.sleep(0.15)
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
                issues.append("JS loading placeholder in HTML; verify rendered content")
            if "không tìm thấy bài viết" in html.lower():
                issues.append("Not-found phrase in HTML; verify visibility before treating as soft 404")
            if parser.canonical and normalized_url(urljoin(final_url, parser.canonical)) != normalized_url(final_url):
                issues.append("Canonical differs from requested URL; verify intended canonical")
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
        "sitemap_urls_found": len(sitemap_urls),
        "sitemaps_scanned": sitemaps_scanned,
        "sitemap_errors": sitemap_errors,
        "page_limit": max_pages,
        "pages_with_issues": sum(bool(page["issues"]) for page in pages),
        "backlinks_checked": len(backlinks),
        "backlinks_found": sum(row["link_found"] for row in backlinks),
    }
    (reports / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (reports / "seo_findings.md").write_text(render_markdown(pages, backlinks), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
