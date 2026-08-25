#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Paperclip project reporter -> Discord via Bot API."""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime

PROJECT_NAME = "NichProject"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ENV_FILE = os.path.join(PROJECT_DIR, ".env")
HERMES_ENV_FILE = os.path.expanduser("~/.hermes/.env")
REPORTS_DIR = os.path.join(PROJECT_DIR, "reports")
DEFAULT_PAPERCLIP_COMPANY_ID = "ccd0c00a-d565-4fc4-910f-9d823665313b"


def load_env_file(path):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"'")
            if key and key not in os.environ:
                os.environ[key] = value


load_env_file(PROJECT_ENV_FILE)
load_env_file(HERMES_ENV_FILE)
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_ID = os.environ.get("DISCORD_HOME_CHANNEL", "1492927950306283651")
DISCORD_MAX_CONTENT_LENGTH = 1900
PAPERCLIP_API_BASE = (
    os.environ.get("PAPERCLIP_API_URL")
    or os.environ.get("PAPERCLIP_API_BASE")
    or "http://127.0.0.1:3100"
).rstrip("/")
PAPERCLIP_COMPANY_ID = os.environ.get("PAPERCLIP_COMPANY_ID", DEFAULT_PAPERCLIP_COMPANY_ID)
PAPERCLIP_API_KEY = os.environ.get("PAPERCLIP_API_KEY", "")
PAPERCLIP_PAGE_LIMIT = 500
REPORT_ISSUE_STATUSES = ("todo", "in_progress", "in_review", "blocked", "done")
MAX_DONE_ITEMS = int(os.environ.get("HERMES_REPORT_MAX_DONE_ITEMS", "40"))


def load_json(filename):
    path = os.path.join(PROJECT_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def paperclip_get(path, params=None):
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params)
    url = f"{PAPERCLIP_API_BASE}{path}{query}"
    headers = {"User-Agent": "NichProjectHermesReporter/1.1"}
    if PAPERCLIP_API_KEY:
        headers["Authorization"] = f"Bearer {PAPERCLIP_API_KEY}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_live_issues():
    issues = []
    offset = 0
    while True:
        page = paperclip_get(
            f"/api/companies/{PAPERCLIP_COMPANY_ID}/issues",
            {
                "status": ",".join(REPORT_ISSUE_STATUSES),
                "limit": PAPERCLIP_PAGE_LIMIT,
                "offset": offset,
            },
        )
        if not isinstance(page, list):
            raise RuntimeError("Paperclip issues API returned a non-list response")
        issues.extend(page)
        if len(page) < PAPERCLIP_PAGE_LIMIT:
            break
        offset += PAPERCLIP_PAGE_LIMIT
    return issues


def fetch_live_agents():
    agents = paperclip_get(f"/api/companies/{PAPERCLIP_COMPANY_ID}/agents")
    if not isinstance(agents, list):
        raise RuntimeError("Paperclip agents API returned a non-list response")
    return agents


def load_report_data():
    agents = load_json("agents.json")
    try:
        live_issues = fetch_live_issues()
        try:
            agents = fetch_live_agents()
            source = f"Paperclip API ({PAPERCLIP_API_BASE})"
        except Exception as exc:
            source = f"Paperclip API issues + local agents snapshot ({exc})"
        return agents, live_issues, source
    except Exception as exc:
        return agents, load_json("issues.json"), f"local JSON snapshot (Paperclip API unavailable: {exc})"


def build_report():
    agents, issues, data_source = load_report_data()
    timestamp = datetime.now()
    now = timestamp.strftime("%Y-%m-%d %H:%M")

    running = [a for a in agents if a.get("status") == "running"]
    idle = [a for a in agents if a.get("status") == "idle"]

    done = [i for i in issues if i.get("status") == "done"]
    in_progress = [i for i in issues if i.get("status") == "in_progress"]
    in_review = [i for i in issues if i.get("status") == "in_review"]
    blocked = [i for i in issues if i.get("status") == "blocked"]

    lines = []
    lines.append(f"## {PROJECT_NAME} -- {now}\n")
    lines.append(f"Data source: {data_source}")
    lines.append(f"Agent: {len(running)} active / {len(idle)} idle")
    lines.append(
        f"Issues: {len(done)} done | {len(in_progress)} in_progress | "
        f"{len(in_review)} in_review | {len(blocked)} blocked\n"
    )

    needs_attention = in_review + blocked
    if needs_attention:
        lines.append("**Action needed:**")
        for issue in needs_attention:
            ident = issue.get("identifier", "?")
            title = issue.get("title", "")[:50]
            status = issue.get("status", "")
            lines.append(f"- {ident}: {title} -> {status}")
        lines.append("")

    if done:
        lines.append("**Done:**")
        for issue in done[:MAX_DONE_ITEMS]:
            ident = issue.get("identifier", "?")
            title = issue.get("title", "")[:50]
            lines.append(f"- {ident}: {title}")
        if len(done) > MAX_DONE_ITEMS:
            lines.append(f"- ... {len(done) - MAX_DONE_ITEMS} more done issues omitted")
        lines.append("")

    if in_progress:
        lines.append("**In progress:**")
        for issue in in_progress:
            ident = issue.get("identifier", "?")
            title = issue.get("title", "")[:50]
            lines.append(f"- {ident}: {title}")

    return "\n".join(lines), timestamp


def save_report(report, timestamp):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    filename = timestamp.strftime("%Y-%m-%d-%H.md")
    path = os.path.join(REPORTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
        if not report.endswith("\n"):
            f.write("\n")
    return path


def send_via_bot(message):
    statuses = []
    for chunk in split_message(message):
        statuses.append(send_message_chunk(chunk))
    return statuses


def split_message(message, max_length=DISCORD_MAX_CONTENT_LENGTH):
    chunks = []
    current = ""
    for line in message.splitlines(keepends=True):
        if len(line) > max_length:
            if current:
                chunks.append(current.rstrip())
                current = ""
            for start in range(0, len(line), max_length):
                chunks.append(line[start : start + max_length].rstrip())
            continue
        if current and len(current) + len(line) > max_length:
            chunks.append(current.rstrip())
            current = ""
        current += line
    if current:
        chunks.append(current.rstrip())
    return chunks or [message[:max_length]]


def send_message_chunk(message):
    url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages"
    data = json.dumps({"content": message}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "PaperclipReporter/1.0",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status


def main():
    report, timestamp = build_report()
    report_path = save_report(report, timestamp)
    print(report)
    print(f"Saved report: {report_path}")
    print("---")

    if DISCORD_BOT_TOKEN:
        statuses = send_via_bot(report)
        print(f"Sent via Bot API: {', '.join(str(status) for status in statuses)}")
    else:
        print("No DISCORD_BOT_TOKEN set.")
        sys.exit(1)


if __name__ == "__main__":
    main()
