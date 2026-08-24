#!/usr/bin/env python3
"""
fetch_publications.py

Fetches the RSS feed of a person's publications from a Pure/Elsevier
research-portal instance (e.g. University of Bath's Research Portal) and
generates an org-mode source file listing them, grouped by year, newest
first.

Usage:
    python3 fetch_publications.py \
        --feed-url "https://researchportal.bath.ac.uk/en/persons/guy-mccusker/publications/?format=rss" \
        --out publications.org \
        --highlight-name "McCusker"

For local testing without network access, pass --feed-file pointing at a
saved copy of the RSS XML instead of --feed-url.
"""

import argparse
import html
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime

from bs4 import BeautifulSoup

NS = {"dc": "http://purl.org/dc/elements/1.1/"}


def fetch_feed_text(feed_url=None, feed_file=None, timeout=20):
    if feed_file:
        with open(feed_file, "r", encoding="utf-8") as f:
            return f.read()
    if feed_url:
        import urllib.request

        req = urllib.request.Request(
            feed_url, headers={"User-Agent": "publications-sync/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    raise ValueError("Provide either feed_url or feed_file")


def parse_items(xml_text):
    """Parse the RSS XML text into a list of raw item dicts."""
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    items = []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description_raw = item.findtext("description") or ""
        pub_date = (item.findtext("pubDate") or "").strip()
        dc_date = (item.findtext("dc:date", namespaces=NS) or "").strip()
        items.append(
            {
                "title": title,
                "link": link,
                "description_html": html.unescape(description_raw),
                "pub_date": pub_date,
                "dc_date": dc_date,
            }
        )
    return items


def year_from_dc_date(dc_date, fallback_pub_date):
    for candidate in (dc_date, fallback_pub_date):
        if not candidate:
            continue
        m = re.search(r"(\d{4})", candidate)
        if m:
            return int(m.group(1))
    return 0


def sort_key(dc_date, fallback_pub_date):
    for candidate, fmt_list in (
        (dc_date, ["%Y-%m-%dT%H:%M:%SZ"]),
        (fallback_pub_date, ["%a, %d %b %Y %H:%M:%S %Z"]),
    ):
        if not candidate:
            continue
        for fmt in fmt_list:
            try:
                return datetime.strptime(candidate, fmt)
            except ValueError:
                continue
    return datetime.min


def org_escape(text):
    """Escape characters that are structurally meaningful in org syntax."""
    return text.replace("[", "(").replace("]", ")")


def _tidy(text):
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return text.strip(" ,")


def extract_authors_and_venue(description_html, title):
    """
    Parse the Pure-generated citation blob embedded in <description>.

    Returns (authors_org, date_text, venue_org, type_label) where authors_org
    and venue_org are already-formatted org-mode text fragments (with
    [[..][..]] links where the portal provided them), date_text is the
    human-readable date string Pure supplies (e.g. "29 Apr 2026"), and
    type_label is a short human string like "Article" or "Book chapter".
    """
    soup = BeautifulSoup(description_html, "html.parser")
    container = soup.find("div", class_="rendering")
    if container is None:
        return "", "", "", ""

    h3 = container.find("h3", class_="title")
    type_p = container.find("p", class_="type")
    date_span = container.find("span", class_="date")

    # --- authors: text/links between the </h3> and the first <span class="date">
    author_parts = []
    node = h3.next_sibling if h3 else container.contents[0]
    while node is not None and node is not date_span:
        if getattr(node, "name", None) == "a" and "person" in (node.get("class") or []):
            name = org_escape(node.get_text(strip=True))
            href = node.get("href", "")
            author_parts.append(f"[[{href}][*{name}*]]" if href else f"*{name}*")
        elif getattr(node, "name", None) == "a":
            author_parts.append(org_escape(node.get_text(strip=True)))
        else:
            text = str(node) if isinstance(node, str) else node.get_text()
            author_parts.append(org_escape(text))
        node = node.next_sibling
    authors_org = _tidy("".join(author_parts))

    date_text = date_span.get_text(strip=True) if date_span else ""

    # --- venue / publication details: everything after the date span, minus the type paragraph
    venue_parts = []
    node = date_span.next_sibling if date_span else None
    while node is not None and node is not type_p:
        if getattr(node, "name", None) == "em":
            venue_parts.append(f"/{org_escape(node.get_text(strip=True))}/ ")
        elif getattr(node, "name", None) == "a":
            venue_parts.append(org_escape(node.get_text(strip=True)))
        else:
            text = str(node) if isinstance(node, str) else node.get_text()
            venue_parts.append(org_escape(text))
        node = node.next_sibling
    venue_org = _tidy("".join(venue_parts))
    # drop a leading comma/period left over from stripping the date span
    venue_org = re.sub(r"^[,.\s]+", "", venue_org)

    # --- type label
    type_label = ""
    if type_p is not None:
        parent = type_p.find("span", class_="type_classification_parent")
        classifications = type_p.find_all("span", class_="type_classification")
        bits = []
        if parent is not None:
            bits.append(parent.get_text(strip=True).split("›")[0].strip())
        if classifications:
            bits.append(classifications[0].get_text(strip=True))
        type_label = " — ".join(b for b in bits if b)

    return authors_org, date_text, venue_org, type_label


RSS_ICON_SVG = (
    '<svg width="14" height="14" viewBox="0 0 448 512" aria-hidden="true" '
    'focusable="false"><path fill="currentColor" d="M0 64C0 46.3 14.3 32 32 '
    '32c229.8 0 416 186.2 416 416c0 17.7-14.3 32-32 32s-32-14.3-32-32C384 '
    '253.6 226.4 96 32 96C14.3 96 0 81.7 0 64zM0 416a64 64 0 1 1 128 0A64 '
    "64 0 1 1 0 416zM0 192c0-17.7 14.3-32 32-32c123.7 0 224 100.3 224 224c0 "
    "17.7-14.3 32-32 32s-32-14.3-32-32c0-88.4-71.6-160-160-160c-17.7 "
    '0-32-14.3-32-32z"/></svg>'
)


def build_org(items, highlight_name, title_heading="Publications", feed_link=None):
    parsed = []
    for it in items:
        authors, date_text, venue, type_label = extract_authors_and_venue(
            it["description_html"], it["title"]
        )
        if not date_text:
            date_text = it["dc_date"] or it["pub_date"]
        year = year_from_dc_date(it["dc_date"], it["pub_date"])
        key = sort_key(it["dc_date"], it["pub_date"])
        parsed.append(
            {
                "title": it["title"],
                "link": it["link"],
                "authors": authors,
                "date_text": date_text,
                "venue": venue,
                "type_label": type_label,
                "year": year,
                "sort_key": key,
            }
        )

    parsed.sort(key=lambda p: p["sort_key"], reverse=True)

    by_year = defaultdict(list)
    for p in parsed:
        by_year[p["year"]].append(p)

    lines = []
    lines.append(f"#+TITLE: {title_heading}")
    lines.append("#+OPTIONS: toc:nil num:nil")
    lines.append("# This file is generated automatically by fetch_publications.py")
    lines.append("# from the Bath Research Portal RSS feed. Do not hand-edit; changes")
    lines.append("# will be overwritten on the next run.")
    lines.append("")

    if feed_link:
        lines.append(
            f'@@html:<p class="rss-link"><a href="{feed_link}">{RSS_ICON_SVG} '
            'Subscribe via RSS</a></p>@@'
        )
        lines.append("")

    for year in sorted(by_year.keys(), reverse=True):
        lines.append(f"* {year if year else 'Undated'}")
        lines.append(":PROPERTIES:")
        lines.append(":HTML_CONTAINER_CLASS: pub-year")
        lines.append(":END:")
        lines.append("")
        for p in by_year[year]:
            lines.append(f"** [[{p['link']}][{org_escape(p['title'])}]]")
            lines.append(":PROPERTIES:")
            if p["type_label"]:
                specific = p["type_label"].split(" — ")[-1]
                slug = re.sub(r"[^a-z]+", "-", specific.lower()).strip("-")
                lines.append(f":HTML_CONTAINER_CLASS: pub-entry pub-{slug}")
            lines.append(":END:")

            citation_bits = []
            if p["authors"]:
                citation_bits.append(p["authors"])
            if p["date_text"]:
                citation_bits.append(p["date_text"])
            citation = ", ".join(citation_bits)
            if p["venue"]:
                citation = f"{citation}. {p['venue']}" if citation else p["venue"]
            bare = citation.rstrip("/*_")
            if bare and not bare.endswith("."):
                citation += "."
            if citation:
                lines.append(citation)
            if p["type_label"]:
                lines.append(f"# type: {p['type_label']}")
            lines.append("")

    return "\n".join(lines)


DEFAULT_FEED_LINK = (
    "https://researchportal.bath.ac.uk/en/persons/guy-mccusker/publications/"
    "?format=rss"
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feed-url")
    parser.add_argument("--feed-file")
    parser.add_argument("--out", default="publications.org")
    parser.add_argument("--highlight-name", default="McCusker")
    parser.add_argument(
        "--feed-link",
        default=DEFAULT_FEED_LINK,
        help="URL shown as the on-page 'Subscribe via RSS' link. Defaults to "
        "the real feed URL regardless of --feed-file, so local testing "
        "still points readers at the live feed. Pass an empty string to "
        "omit the link entirely.",
    )
    args = parser.parse_args()

    if not args.feed_url and not args.feed_file:
        parser.error("one of --feed-url or --feed-file is required")

    xml_text = fetch_feed_text(feed_url=args.feed_url, feed_file=args.feed_file)
    items = parse_items(xml_text)
    org_text = build_org(items, args.highlight_name, feed_link=args.feed_link)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(org_text)

    print(f"Wrote {len(items)} publications to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
