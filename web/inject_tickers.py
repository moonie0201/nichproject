#!/usr/bin/env python3
"""
inject_tickers.py — idempotently adds `tickers: [...]` frontmatter to:
  1. Tool pages: dividend-calculator/<ticker>.md (single ticker from `ticker:`)
                 compare/<a>-vs-<b>/index.md    (both tickers from ticker_a/ticker_b)
  2. Study pages: if title/description/keywords/body mention any of the known tickers

Run from web/ directory or anywhere; uses absolute paths.
"""

import os
import re
import sys

CONTENT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content")

KNOWN_TICKERS = ["SCHD", "JEPI", "JEPQ", "QYLD", "VYM", "VOO", "SPY"]
# Word-boundary regex for each ticker
TICKER_RE = {t: re.compile(r'\b' + re.escape(t) + r'\b', re.IGNORECASE) for t in KNOWN_TICKERS}


def parse_frontmatter(text):
    """Return (fm_str, body_str) where fm_str is the raw yaml between --- markers."""
    m = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n?(.*)', text, re.DOTALL)
    if not m:
        return None, text
    return m.group(1), m.group(2)


def has_tickers_key(fm_str):
    return re.search(r'^tickers\s*:', fm_str, re.MULTILINE) is not None


def insert_tickers(fm_str, tickers):
    """Insert `tickers: [T1, T2]` after the last frontmatter line that starts a known field."""
    ticker_line = "tickers: [" + ", ".join(tickers) + "]"
    # Insert before the closing --- by appending to fm
    return fm_str.rstrip() + "\n" + ticker_line


def rewrite(path, tickers):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    fm, body = parse_frontmatter(text)
    if fm is None:
        return False
    if has_tickers_key(fm):
        return False  # already present, skip
    new_fm = insert_tickers(fm, tickers)
    new_text = "---\n" + new_fm + "\n---\n" + body
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_text)
    return True


def process_tool_pages():
    changed = 0
    for root, dirs, files in os.walk(CONTENT_ROOT):
        for fname in files:
            if not fname.endswith(".md"):
                continue
            path = os.path.join(root, fname)
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            fm, _ = parse_frontmatter(text)
            if fm is None:
                continue
            # Only tool pages
            if not re.search(r'^type\s*:\s*["\']?tools["\']?', fm, re.MULTILINE):
                continue

            tickers = []

            # dividend-calculator: single ticker: field
            m_tick = re.search(r'^ticker\s*:\s*["\']?(\w+)["\']?', fm, re.MULTILINE)
            if m_tick:
                t = m_tick.group(1).upper()
                if t in KNOWN_TICKERS:
                    tickers = [t]

            # compare: ticker_a + ticker_b
            m_a = re.search(r'^ticker_a\s*:\s*["\']?(\w+)["\']?', fm, re.MULTILINE)
            m_b = re.search(r'^ticker_b\s*:\s*["\']?(\w+)["\']?', fm, re.MULTILINE)
            if m_a and m_b:
                ta = m_a.group(1).upper()
                tb = m_b.group(1).upper()
                tickers = [t for t in [ta, tb] if t in KNOWN_TICKERS]

            if tickers and rewrite(path, tickers):
                print(f"  TOOL  {path}  -> tickers: {tickers}")
                changed += 1
    return changed


def process_study_pages():
    changed = 0
    for root, dirs, files in os.walk(CONTENT_ROOT):
        # Only study directories
        if "study" not in root.split(os.sep):
            continue
        for fname in files:
            if not fname.endswith(".md") or fname == "_index.md":
                continue
            path = os.path.join(root, fname)
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            fm, body = parse_frontmatter(text)
            if fm is None:
                continue
            # Skip tool type pages (shouldn't be in study/ but guard anyway)
            if re.search(r'^type\s*:\s*["\']?tools["\']?', fm, re.MULTILINE):
                continue

            # Build search corpus from title + description + keywords + first 2000 chars of body
            corpus = fm + "\n" + body[:2000]
            found = [t for t in KNOWN_TICKERS if TICKER_RE[t].search(corpus)]

            if found and rewrite(path, found):
                print(f"  STUDY {path}  -> tickers: {found}")
                changed += 1
    return changed


if __name__ == "__main__":
    print("=== Tool pages ===")
    tc = process_tool_pages()
    print(f"  {tc} tool pages updated")

    print("=== Study pages ===")
    sc = process_study_pages()
    print(f"  {sc} study pages updated")

    print(f"\nTotal: {tc + sc} files updated")
